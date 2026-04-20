import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestUserRepo:
    @pytest.fixture
    def db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        yield session
        session.close()

    def test_create_new_user(self, db):
        from app.services.user_repo import upsert_by_telegram_id

        user, is_new = upsert_by_telegram_id(db, "12345", "Alice")
        assert is_new is True
        assert user.telegram_id == "12345"
        assert user.name == "Alice"
        assert user.id is not None

    def test_existing_user_returns_false(self, db):
        from app.services.user_repo import upsert_by_telegram_id

        upsert_by_telegram_id(db, "12345", "Alice")
        user, is_new = upsert_by_telegram_id(db, "12345", "Alice Updated")
        assert is_new is False
        assert user.name == "Alice Updated"

    def test_different_telegram_ids(self, db):
        from app.services.user_repo import upsert_by_telegram_id

        u1, new1 = upsert_by_telegram_id(db, "111", "Alice")
        u2, new2 = upsert_by_telegram_id(db, "222", "Bob")
        assert new1 is True
        assert new2 is True
        assert u1.id != u2.id


class TestPairingRepo:
    @pytest.fixture
    def db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        yield session
        session.close()

    def _create_user(self, db):
        from app.models.user import User

        user = User(id=uuid.uuid4(), telegram_id="99999", name="Test")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_create_token(self, db):
        from app.services.pairing_repo import create_token

        user = self._create_user(db)
        token = create_token(db, user.id)
        assert token.token is not None
        assert token.user_id == user.id
        expires = token.expires_at.replace(tzinfo=timezone.utc) if token.expires_at.tzinfo is None else token.expires_at
        assert expires > datetime.now(timezone.utc)
        assert token.consumed_at is None

    def test_get_valid_token(self, db):
        from app.services.pairing_repo import create_token, get_valid_token

        user = self._create_user(db)
        token = create_token(db, user.id)
        found = get_valid_token(db, token.token)
        assert found is not None
        assert found.id == token.id

    def test_get_expired_token_returns_none(self, db):
        from app.models.pairing_token import PairingToken
        from app.services.pairing_repo import get_valid_token

        user = self._create_user(db)
        expired = PairingToken(
            id=uuid.uuid4(),
            token="expired-token",
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.add(expired)
        db.commit()
        assert get_valid_token(db, "expired-token") is None

    def test_get_consumed_token_returns_none(self, db):
        from app.models.pairing_token import PairingToken
        from app.services.pairing_repo import get_valid_token

        user = self._create_user(db)
        consumed = PairingToken(
            id=uuid.uuid4(),
            token="consumed-token",
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            consumed_at=datetime.now(timezone.utc),
        )
        db.add(consumed)
        db.commit()
        assert get_valid_token(db, "consumed-token") is None

    def test_get_nonexistent_token(self, db):
        assert __import__("app.services.pairing_repo", fromlist=["get_valid_token"]).get_valid_token(db, "nope") is None

    def test_consume_token(self, db):
        from app.services.pairing_repo import consume_token, create_token, get_valid_token

        user = self._create_user(db)
        token = create_token(db, user.id)
        consume_token(db, token)
        assert token.consumed_at is not None
        assert get_valid_token(db, token.token) is None

    def test_cleanup_expired(self, db):
        from app.models.pairing_token import PairingToken
        from app.services.pairing_repo import cleanup_expired, create_token

        user = self._create_user(db)
        create_token(db, user.id)
        expired = PairingToken(
            id=uuid.uuid4(),
            token="old-token",
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        db.add(expired)
        db.commit()
        count = cleanup_expired(db)
        assert count == 1
        assert db.query(PairingToken).count() == 1


class TestStartHandler:
    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.full_name = "Test User"
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_new_user_welcome(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.start.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.start.user_repo") as mock_user_repo,
            patch("app.bot.handlers.start.pairing_repo") as mock_pairing_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, True)

            mock_token = MagicMock()
            mock_token.token = "abc123"
            mock_pairing_repo.create_token.return_value = mock_token

            from app.bot.handlers.start import start_handler

            await start_handler(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "Welcome Test User" in call_args[0][0]
            assert "registered" in call_args[0][0]
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_existing_user_welcome_back(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.start.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.start.user_repo") as mock_user_repo,
            patch("app.bot.handlers.start.pairing_repo") as mock_pairing_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            mock_token = MagicMock()
            mock_token.token = "xyz789"
            mock_pairing_repo.create_token.return_value = mock_token

            from app.bot.handlers.start import start_handler

            await start_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            assert "Welcome back" in call_args[0][0]
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_pairing_link_in_keyboard(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.start.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.start.user_repo") as mock_user_repo,
            patch("app.bot.handlers.start.pairing_repo") as mock_pairing_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, True)

            mock_token = MagicMock()
            mock_token.token = "pairing123"
            mock_pairing_repo.create_token.return_value = mock_token

            from app.bot.handlers.start import start_handler

            await start_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            keyboard = call_args[1]["reply_markup"]
            button = keyboard.inline_keyboard[0][0]
            assert "pairing123" in button.url

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.start.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.start.user_repo") as mock_user_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user_repo.upsert_by_telegram_id.side_effect = Exception("DB error")

            from app.bot.handlers.start import start_handler

            await start_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            assert "Something went wrong" in call_args[0][0]
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_effective_user(self, mock_context):
        update = MagicMock()
        update.effective_user = None
        update.message = AsyncMock()

        from app.bot.handlers.start import start_handler

        await start_handler(update, mock_context)
        update.message.reply_text.assert_not_called()


class TestHelpHandler:
    @pytest.mark.asyncio
    async def test_help_message(self):
        update = MagicMock()
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        from app.bot.handlers.help import help_handler

        await help_handler(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        text = call_args[0][0]
        assert "/start" in text
        assert "/lunch" in text
        assert "/help" in text

    @pytest.mark.asyncio
    async def test_help_no_message(self):
        update = MagicMock()
        update.message = None
        context = MagicMock()

        from app.bot.handlers.help import help_handler

        await help_handler(update, context)


class TestUnknownHandler:
    @pytest.mark.asyncio
    async def test_unknown_command(self):
        update = MagicMock()
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        from app.bot.handlers.unknown import unknown_handler

        await unknown_handler(update, context)

        call_args = update.message.reply_text.call_args
        assert "Unknown command" in call_args[0][0]
        assert "/help" in call_args[0][0]


class TestWebhookEndpoint:
    @pytest.fixture
    def client(self):
        yield TestClient(app)

    def test_webhook_valid_request(self, client):
        with patch("app.api.telegram.get_application") as mock_get_app:
            mock_app = AsyncMock()
            mock_bot = MagicMock()
            mock_app.bot = mock_bot
            mock_get_app.return_value = mock_app

            with patch("app.api.telegram.Update") as mock_update_cls:
                mock_update_cls.de_json.return_value = MagicMock()

                resp = client.post(
                    "/webhook/telegram",
                    json={"update_id": 123, "message": {"text": "/start"}},
                )
                assert resp.status_code == 200
                assert resp.json() == {"ok": True}

    def test_webhook_invalid_secret(self, client):
        with patch("app.api.telegram.settings") as mock_settings:
            mock_settings.telegram_webhook_secret = "correct-secret"

            resp = client.post(
                "/webhook/telegram",
                json={"update_id": 123},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            )
            assert resp.status_code == 403

    def test_webhook_valid_secret(self, client):
        with (
            patch("app.api.telegram.settings") as mock_settings,
            patch("app.api.telegram.get_application") as mock_get_app,
            patch("app.api.telegram.Update") as mock_update_cls,
        ):
            mock_settings.telegram_webhook_secret = "correct-secret"

            mock_app = AsyncMock()
            mock_app.bot = MagicMock()
            mock_get_app.return_value = mock_app
            mock_update_cls.de_json.return_value = MagicMock()

            resp = client.post(
                "/webhook/telegram",
                json={"update_id": 123},
                headers={"X-Telegram-Bot-Api-Secret-Token": "correct-secret"},
            )
            assert resp.status_code == 200

    def test_webhook_no_secret_configured(self, client):
        with (
            patch("app.api.telegram.get_application") as mock_get_app,
            patch("app.api.telegram.Update") as mock_update_cls,
        ):
            mock_app = AsyncMock()
            mock_app.bot = MagicMock()
            mock_get_app.return_value = mock_app
            mock_update_cls.de_json.return_value = MagicMock()

            resp = client.post(
                "/webhook/telegram",
                json={"update_id": 123},
            )
            assert resp.status_code == 200
