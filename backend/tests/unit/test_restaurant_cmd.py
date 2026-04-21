import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.handlers.restaurant_cmd import (
    AddState,
    EditState,
    add_category,
    add_confirm,
    add_name,
    add_price,
    add_start,
    cancel,
    edit_delete_confirm,
    edit_select_field,
    edit_select_restaurant,
    edit_start,
    edit_value,
)


class TestAddRestaurant:
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
        ctx.user_data = {}
        return ctx

    @pytest.mark.asyncio
    async def test_add_start(self, mock_update, mock_context):
        result = await add_start(mock_update, mock_context)
        assert result == AddState.NAME
        assert "add_restaurant" in mock_context.user_data
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_name_valid(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {}
        mock_update.message.text = "ส้มตำนัว"
        result = await add_name(mock_update, mock_context)
        assert result == AddState.PRICE
        assert mock_context.user_data["add_restaurant"]["name"] == "ส้มตำนัว"

    @pytest.mark.asyncio
    async def test_add_name_too_long(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {}
        mock_update.message.text = "x" * 101
        result = await add_name(mock_update, mock_context)
        assert result == AddState.NAME

    @pytest.mark.asyncio
    async def test_add_price_valid(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {"name": "Test"}
        mock_update.message.text = "60"
        result = await add_price(mock_update, mock_context)
        assert result == AddState.CATEGORY
        assert mock_context.user_data["add_restaurant"]["price"] == 60

    @pytest.mark.asyncio
    async def test_add_price_skip(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {"name": "Test"}
        mock_update.message.text = "/skip"
        result = await add_price(mock_update, mock_context)
        assert result == AddState.CATEGORY
        assert mock_context.user_data["add_restaurant"]["price"] is None

    @pytest.mark.asyncio
    async def test_add_price_invalid(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {"name": "Test"}
        mock_update.message.text = "abc"
        result = await add_price(mock_update, mock_context)
        assert result == AddState.PRICE

    @pytest.mark.asyncio
    async def test_add_category_valid(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {"name": "Test", "price": 60}
        mock_update.message.text = "ก๋วยเตี๋ยว"
        result = await add_category(mock_update, mock_context)
        assert result == AddState.CLOSED_DAYS
        assert mock_context.user_data["add_restaurant"]["category"] == "ก๋วยเตี๋ยว"

    @pytest.mark.asyncio
    async def test_add_category_skip(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {"name": "Test", "price": 60}
        mock_update.message.text = "/skip"
        result = await add_category(mock_update, mock_context)
        assert result == AddState.CLOSED_DAYS
        assert mock_context.user_data["add_restaurant"]["category"] is None

    @pytest.mark.asyncio
    async def test_add_confirm_yes(self, mock_update, mock_context):
        mock_context.user_data["add_restaurant"] = {
            "name": "ร้านทดสอบ",
            "price": 60,
            "category": "ก๋วยเตี๋ยว",
            "closed_days": [0, 6],
        }

        query = AsyncMock()
        query.data = "add_confirm:yes"
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.from_user.full_name = "Test"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        mock_update.callback_query = query

        with (
            patch("app.bot.handlers.restaurant_cmd.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.restaurant_cmd.user_repo") as mock_user_repo,
            patch("app.bot.handlers.restaurant_cmd.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            result = await add_confirm(mock_update, mock_context)

            assert result == -1  # ConversationHandler.END
            mock_rest_repo.create_manual.assert_called_once()
            call_text = query.edit_message_text.call_args[0][0]
            assert "ร้านทดสอบ" in call_text
            assert "✅" in call_text

    @pytest.mark.asyncio
    async def test_add_confirm_cancel(self, mock_update, mock_context):
        query = AsyncMock()
        query.data = "add_confirm:no"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        mock_update.callback_query = query

        result = await add_confirm(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        query.edit_message_text.assert_called_with("Cancelled")


class TestEditRestaurant:
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
        ctx.user_data = {}
        return ctx

    @pytest.mark.asyncio
    async def test_edit_start_no_restaurants(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.restaurant_cmd.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.restaurant_cmd.user_repo") as mock_user_repo,
            patch("app.bot.handlers.restaurant_cmd.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)
            mock_rest_repo.list_all.return_value = ([], 0)

            result = await edit_start(mock_update, mock_context)
            assert result == -1  # ConversationHandler.END
            call_text = mock_update.message.reply_text.call_args[0][0]
            assert "haven't added" in call_text

    @pytest.mark.asyncio
    async def test_edit_start_with_restaurants(self, mock_update, mock_context):
        user_id = uuid.uuid4()

        with (
            patch("app.bot.handlers.restaurant_cmd.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.restaurant_cmd.user_repo") as mock_user_repo,
            patch("app.bot.handlers.restaurant_cmd.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            r1 = MagicMock()
            r1.id = uuid.uuid4()
            r1.name = "ร้านของฉัน"
            r1.added_by = user_id
            mock_rest_repo.list_all.return_value = ([r1], 1)

            result = await edit_start(mock_update, mock_context)
            assert result == EditState.SELECT_RESTAURANT

    @pytest.mark.asyncio
    async def test_edit_select_restaurant(self, mock_update, mock_context):
        restaurant_id = uuid.uuid4()
        mock_context.user_data = {}

        query = AsyncMock()
        query.data = f"edit_pick:{restaurant_id}"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        mock_update.callback_query = query

        with (
            patch("app.bot.handlers.restaurant_cmd.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.restaurant_cmd.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_r = MagicMock()
            mock_r.name = "ร้านทดสอบ"
            mock_r.price_level = 2
            mock_r.types = ["ก๋วยเตี๋ยว"]
            mock_r.closed_weekdays = None
            mock_rest_repo.get_by_id.return_value = mock_r

            result = await edit_select_restaurant(mock_update, mock_context)
            assert result == EditState.SELECT_FIELD
            assert mock_context.user_data["editing_restaurant_id"] == str(restaurant_id)

    @pytest.mark.asyncio
    async def test_edit_select_restaurant_cancel(self, mock_update, mock_context):
        query = AsyncMock()
        query.data = "edit_pick:cancel"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        mock_update.callback_query = query

        result = await edit_select_restaurant(mock_update, mock_context)
        assert result == -1
        query.edit_message_text.assert_called_with("Cancelled")

    @pytest.mark.asyncio
    async def test_edit_value_name(self, mock_update, mock_context):
        restaurant_id = uuid.uuid4()
        mock_context.user_data = {
            "editing_restaurant_id": str(restaurant_id),
            "editing_field": "name",
        }
        mock_update.message.text = "ชื่อใหม่"

        with (
            patch("app.bot.handlers.restaurant_cmd.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.restaurant_cmd.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_r = MagicMock()
            mock_r.name = "ชื่อเก่า"
            mock_r.price_level = 2
            mock_r.types = None
            mock_r.closed_weekdays = None
            mock_rest_repo.get_by_id.return_value = mock_r

            result = await edit_value(mock_update, mock_context)
            assert result == EditState.SELECT_FIELD
            assert mock_r.name == "ชื่อใหม่"

    @pytest.mark.asyncio
    async def test_edit_delete_confirm_yes(self, mock_update, mock_context):
        restaurant_id = uuid.uuid4()
        mock_context.user_data = {"editing_restaurant_id": str(restaurant_id)}

        query = AsyncMock()
        query.data = "edit_delete:yes"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        mock_update.callback_query = query

        with (
            patch("app.bot.handlers.restaurant_cmd.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.restaurant_cmd.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_rest_repo.delete.return_value = True

            result = await edit_delete_confirm(mock_update, mock_context)
            assert result == -1
            mock_rest_repo.delete.assert_called_once()
            call_text = query.edit_message_text.call_args[0][0]
            assert "deleted" in call_text

    @pytest.mark.asyncio
    async def test_edit_delete_confirm_no(self, mock_update, mock_context):
        restaurant_id = uuid.uuid4()
        mock_context.user_data = {"editing_restaurant_id": str(restaurant_id)}

        query = AsyncMock()
        query.data = "edit_delete:no"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        mock_update.callback_query = query

        with (
            patch("app.bot.handlers.restaurant_cmd.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.restaurant_cmd.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_r = MagicMock()
            mock_r.name = "ร้าน"
            mock_r.price_level = None
            mock_r.types = None
            mock_r.closed_weekdays = None
            mock_rest_repo.get_by_id.return_value = mock_r

            result = await edit_delete_confirm(mock_update, mock_context)
            assert result == EditState.SELECT_FIELD


class TestCancel:
    @pytest.mark.asyncio
    async def test_cancel(self):
        update = MagicMock()
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        result = await cancel(update, context)
        assert result == -1
        update.message.reply_text.assert_called_with("Cancelled")
