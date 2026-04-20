import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user_blacklist import BlacklistMode


class TestBlacklistHandler:
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
        ctx = MagicMock()
        ctx.args = []
        return ctx

    @pytest.mark.asyncio
    async def test_no_args_shows_help(self, mock_update, mock_context):
        mock_context.args = []

        from app.bot.handlers.blacklist import blacklist_handler

        await blacklist_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "/blacklist add" in call_args
        assert "/blacklist list" in call_args
        assert "/blacklist remove" in call_args

    @pytest.mark.asyncio
    async def test_add_no_name(self, mock_update, mock_context):
        mock_context.args = ["add"]

        from app.bot.handlers.blacklist import blacklist_handler

        await blacklist_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "กรุณาระบุชื่อร้าน" in call_args

    @pytest.mark.asyncio
    async def test_add_not_found(self, mock_update, mock_context):
        mock_context.args = ["add", "ร้านที่ไม่มี"]

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_rest_repo.list_all.return_value = ([], 0)

            from app.bot.handlers.blacklist import blacklist_handler

            await blacklist_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "ไม่เจอร้าน" in call_args

    @pytest.mark.asyncio
    async def test_add_single_match_shows_mode_keyboard(self, mock_update, mock_context):
        mock_context.args = ["add", "ส้มตำ"]

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_r = MagicMock()
            mock_r.id = uuid.uuid4()
            mock_r.name = "ส้มตำนัว"
            mock_rest_repo.list_all.return_value = ([mock_r], 1)

            from app.bot.handlers.blacklist import blacklist_handler

            await blacklist_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            assert "ส้มตำนัว" in call_args[0][0]
            assert call_args[1]["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_add_multiple_matches_shows_pick_keyboard(self, mock_update, mock_context):
        mock_context.args = ["add", "ร้าน"]

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            r1 = MagicMock()
            r1.id = uuid.uuid4()
            r1.name = "ร้านA"
            r2 = MagicMock()
            r2.id = uuid.uuid4()
            r2.name = "ร้านB"
            mock_rest_repo.list_all.return_value = ([r1, r2], 2)

            from app.bot.handlers.blacklist import blacklist_handler

            await blacklist_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            assert "2 ร้าน" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_update, mock_context):
        mock_context.args = ["list"]

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.user_repo") as mock_user_repo,
            patch("app.bot.handlers.blacklist.blacklist_repo") as mock_bl_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)
            mock_bl_repo.list_by_user.return_value = []

            from app.bot.handlers.blacklist import blacklist_handler

            await blacklist_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "blacklist" in call_args

    @pytest.mark.asyncio
    async def test_list_with_entries(self, mock_update, mock_context):
        mock_context.args = ["list"]

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.user_repo") as mock_user_repo,
            patch("app.bot.handlers.blacklist.blacklist_repo") as mock_bl_repo,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            entry1 = MagicMock()
            entry1.restaurant_id = uuid.uuid4()
            entry1.mode = BlacklistMode.PERMANENT
            entry2 = MagicMock()
            entry2.restaurant_id = uuid.uuid4()
            entry2.mode = BlacklistMode.TODAY
            mock_bl_repo.list_by_user.return_value = [entry1, entry2]

            r1 = MagicMock()
            r1.name = "ร้านPermanent"
            r2 = MagicMock()
            r2.name = "ร้านToday"
            mock_rest_repo.get_by_id.side_effect = lambda db, rid: r1 if rid == entry1.restaurant_id else r2

            from app.bot.handlers.blacklist import blacklist_handler

            await blacklist_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "ร้านPermanent" in call_args
            assert "ร้านToday" in call_args
            assert "ถาวร" in call_args
            assert "แค่วันนี้" in call_args

    @pytest.mark.asyncio
    async def test_remove_no_name(self, mock_update, mock_context):
        mock_context.args = ["remove"]

        from app.bot.handlers.blacklist import blacklist_handler

        await blacklist_handler(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "กรุณาระบุชื่อร้าน" in call_args

    @pytest.mark.asyncio
    async def test_remove_success(self, mock_update, mock_context):
        mock_context.args = ["remove", "ส้มตำ"]

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.user_repo") as mock_user_repo,
            patch("app.bot.handlers.blacklist.blacklist_repo") as mock_bl_repo,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            entry = MagicMock()
            entry.id = uuid.uuid4()
            entry.restaurant_id = uuid.uuid4()
            mock_bl_repo.list_by_user.return_value = [entry]
            mock_bl_repo.remove.return_value = True

            mock_r = MagicMock()
            mock_r.name = "ส้มตำนัว"
            mock_rest_repo.get_by_id.return_value = mock_r

            from app.bot.handlers.blacklist import blacklist_handler

            await blacklist_handler(mock_update, mock_context)

            mock_bl_repo.remove.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "ส้มตำนัว" in call_args
            assert "ลบ" in call_args


class TestBlacklistModeCallback:
    @pytest.mark.asyncio
    async def test_permanent_mode(self):
        restaurant_id = uuid.uuid4()
        query = AsyncMock()
        query.data = f"bl_mode:{restaurant_id}:permanent"
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.from_user.full_name = "Test"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.user_repo") as mock_user_repo,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
            patch("app.bot.handlers.blacklist.blacklist_repo") as mock_bl_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            mock_r = MagicMock()
            mock_r.name = "ร้านทดสอบ"
            mock_rest_repo.get_by_id.return_value = mock_r

            from app.bot.handlers.blacklist import blacklist_mode_callback

            await blacklist_mode_callback(update, context)

            mock_bl_repo.add.assert_called_once_with(mock_db, mock_user.id, restaurant_id, BlacklistMode.PERMANENT)
            call_text = query.edit_message_text.call_args[0][0]
            assert "ร้านทดสอบ" in call_text
            assert "ถาวร" in call_text

    @pytest.mark.asyncio
    async def test_today_mode(self):
        restaurant_id = uuid.uuid4()
        query = AsyncMock()
        query.data = f"bl_mode:{restaurant_id}:today"
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.from_user.full_name = "Test"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.user_repo") as mock_user_repo,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
            patch("app.bot.handlers.blacklist.blacklist_repo") as mock_bl_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            mock_r = MagicMock()
            mock_r.name = "ร้านวันนี้"
            mock_rest_repo.get_by_id.return_value = mock_r

            from app.bot.handlers.blacklist import blacklist_mode_callback

            await blacklist_mode_callback(update, context)

            mock_bl_repo.add.assert_called_once_with(mock_db, mock_user.id, restaurant_id, BlacklistMode.TODAY)
            call_text = query.edit_message_text.call_args[0][0]
            assert "แค่วันนี้" in call_text

    @pytest.mark.asyncio
    async def test_cancel(self):
        query = AsyncMock()
        query.data = "bl_mode:cancel"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        from app.bot.handlers.blacklist import blacklist_mode_callback

        await blacklist_mode_callback(update, context)

        query.edit_message_text.assert_called_with("ยกเลิกแล้ว")


class TestBlacklistPickCallback:
    @pytest.mark.asyncio
    async def test_pick_restaurant_shows_mode(self):
        restaurant_id = uuid.uuid4()
        query = AsyncMock()
        query.data = f"bl_pick:{restaurant_id}"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        with (
            patch("app.bot.handlers.blacklist.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.blacklist.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_r = MagicMock()
            mock_r.id = restaurant_id
            mock_r.name = "ร้านที่เลือก"
            mock_rest_repo.get_by_id.return_value = mock_r

            from app.bot.handlers.blacklist import blacklist_pick_callback

            await blacklist_pick_callback(update, context)

            call_args = query.edit_message_text.call_args
            assert "ร้านที่เลือก" in call_args[0][0]
            assert call_args[1]["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_pick_cancel(self):
        query = AsyncMock()
        query.data = "bl_pick:cancel"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        from app.bot.handlers.blacklist import blacklist_pick_callback

        await blacklist_pick_callback(update, context)

        query.edit_message_text.assert_called_with("ยกเลิกแล้ว")
