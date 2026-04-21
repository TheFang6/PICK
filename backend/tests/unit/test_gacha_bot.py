import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.poll import PollSession, PollStatus, PollVote
from app.models.restaurant import Restaurant, RestaurantSource
from app.models.user import User


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _create_user(db, telegram_id="12345", name="Test"):
    user = User(id=uuid.uuid4(), telegram_id=telegram_id, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_restaurant(db, name="Test Restaurant"):
    r = Restaurant(
        id=uuid.uuid4(),
        name=name,
        source=RestaurantSource.MANUAL,
        rating=4.0,
        price_level=2,
        lat=13.756,
        lng=100.501,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


class TestResetVotes:
    def test_reset_votes_clears_all(self, db):
        from app.services.poll_repo import cast_vote, create_poll, get_total_votes, reset_votes

        u1 = _create_user(db, "111", "A")
        u2 = _create_user(db, "222", "B")
        r = _create_restaurant(db)
        poll = create_poll(db, "chat1", [r.id], None, u1.id)

        cast_vote(db, poll.id, u1.id, r.id)
        cast_vote(db, poll.id, u2.id, r.id)
        assert get_total_votes(db, poll.id) == 2

        reset_votes(db, poll.id)
        assert get_total_votes(db, poll.id) == 0

    def test_reset_votes_empty_poll(self, db):
        from app.services.poll_repo import create_poll, get_total_votes, reset_votes

        user = _create_user(db)
        poll = create_poll(db, "chat1", [], None, user.id)

        reset_votes(db, poll.id)
        assert get_total_votes(db, poll.id) == 0


class TestGachaCallbackVoteReset:
    @pytest.mark.asyncio
    async def test_gacha_resets_votes(self):
        poll_id = uuid.uuid4()
        query = AsyncMock()
        query.data = f"gacha:{poll_id}"
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        r1 = MagicMock()
        r1.id = uuid.uuid4()
        r1.name = "New R1"
        r1.rating = 4.0
        r2 = MagicMock()
        r2.id = uuid.uuid4()
        r2.name = "New R2"
        r2.rating = 3.5
        r3 = MagicMock()
        r3.id = uuid.uuid4()
        r3.name = "New R3"
        r3.rating = 4.2

        with (
            patch("app.bot.handlers.poll_callbacks.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.poll_callbacks.poll_repo") as mock_poll_repo,
            patch("app.bot.handlers.poll_callbacks.user_repo"),
            patch("app.bot.handlers.poll_callbacks.restaurant_repo"),
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_poll = MagicMock()
            mock_poll.id = poll_id
            mock_poll.status = PollStatus.ACTIVE
            mock_poll.session_id = "sess1"
            mock_poll.candidates = [str(uuid.uuid4())]
            mock_poll_repo.get_poll.return_value = mock_poll

            with patch("app.bot.handlers.poll_callbacks.roll") as mock_roll:
                mock_roll.return_value = {
                    "candidates": [r1, r2, r3],
                    "remaining_rolls": 4,
                    "gacha_count": 1,
                }

                from app.bot.handlers.poll_callbacks import gacha_callback

                await gacha_callback(update, context)

                mock_poll_repo.reset_votes.assert_called_once_with(mock_db, poll_id)

    @pytest.mark.asyncio
    async def test_gacha_limit_exceeded(self):
        poll_id = uuid.uuid4()
        query = AsyncMock()
        query.data = f"gacha:{poll_id}"
        query.answer = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        with (
            patch("app.bot.handlers.poll_callbacks.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.poll_callbacks.poll_repo") as mock_poll_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_poll = MagicMock()
            mock_poll.id = poll_id
            mock_poll.status = PollStatus.ACTIVE
            mock_poll.session_id = "sess1"
            mock_poll_repo.get_poll.return_value = mock_poll

            from app.services.gacha import GachaLimitExceeded

            with patch("app.bot.handlers.poll_callbacks.roll", side_effect=GachaLimitExceeded()):
                from app.bot.handlers.poll_callbacks import gacha_callback

                await gacha_callback(update, context)

                query.answer.assert_called_with("Max gacha rolls reached (5).", show_alert=True)


class TestGachaSoloHandler:
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
    async def test_gacha_solo_success(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.gacha_solo.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.gacha_solo.user_repo") as mock_user_repo,
            patch("app.bot.handlers.gacha_solo.recommend") as mock_recommend,
            patch("app.bot.handlers.gacha_solo.history_repo") as mock_hist_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            mock_restaurant = MagicMock()
            mock_restaurant.id = uuid.uuid4()
            mock_restaurant.name = "ส้มตำนัว"
            mock_restaurant.rating = 4.5
            mock_restaurant.lat = 13.757
            mock_restaurant.lng = 100.502

            mock_recommend.return_value = {
                "candidates": [mock_restaurant],
                "session_id": "sess1",
                "pool": [],
                "remaining_rolls": 5,
            }

            from app.bot.handlers.gacha_solo import gacha_handler

            await gacha_handler(mock_update, mock_context)

            mock_hist_repo.log_lunch.assert_called_once_with(mock_db, mock_restaurant.id, [mock_user.id])
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "ส้มตำนัว" in call_args
            assert "Today's pick" in call_args

    @pytest.mark.asyncio
    async def test_gacha_solo_no_restaurants(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.gacha_solo.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.gacha_solo.user_repo") as mock_user_repo,
            patch("app.bot.handlers.gacha_solo.recommend") as mock_recommend,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            mock_recommend.return_value = {
                "candidates": [],
                "session_id": "sess1",
                "pool": [],
                "remaining_rolls": 5,
            }

            from app.bot.handlers.gacha_solo import gacha_handler

            await gacha_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "No restaurants found" in call_args

    @pytest.mark.asyncio
    async def test_gacha_solo_error(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.gacha_solo.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.gacha_solo.user_repo") as mock_user_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user_repo.upsert_by_telegram_id.side_effect = Exception("DB error")

            from app.bot.handlers.gacha_solo import gacha_handler

            await gacha_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Something went wrong" in call_args
