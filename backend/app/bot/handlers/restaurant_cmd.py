import logging
import uuid
from enum import IntEnum, auto

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.database import SessionLocal
from app.models.restaurant import RestaurantSource
from app.schemas.restaurant import ManualRestaurantCreate
from app.services import restaurant_repo, user_repo

logger = logging.getLogger(__name__)

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class AddState(IntEnum):
    NAME = auto()
    PRICE = auto()
    CATEGORY = auto()
    CLOSED_DAYS = auto()
    CONFIRM = auto()


class EditState(IntEnum):
    SELECT_RESTAURANT = auto()
    SELECT_FIELD = auto()
    EDIT_VALUE = auto()
    EDIT_CLOSED_DAYS = auto()
    DELETE_CONFIRM = auto()


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    context.user_data["add_restaurant"] = {}
    await update.message.reply_text("What's the restaurant name?")
    return AddState.NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("Name must be under 100 characters. Try again")
        return AddState.NAME

    context.user_data["add_restaurant"]["name"] = name
    await update.message.reply_text("Approx. price per dish? (number or /skip)")
    return AddState.PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "/skip":
        context.user_data["add_restaurant"]["price"] = None
    else:
        try:
            price = int(text)
            if price <= 0:
                raise ValueError
            context.user_data["add_restaurant"]["price"] = price
        except ValueError:
            await update.message.reply_text("Please enter a number > 0 or /skip")
            return AddState.PRICE

    await update.message.reply_text("Restaurant type? (e.g. noodles, rice, etc.) or /skip")
    return AddState.CATEGORY


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "/skip":
        context.user_data["add_restaurant"]["category"] = None
    else:
        context.user_data["add_restaurant"]["category"] = text

    context.user_data["add_restaurant"]["closed_days"] = []
    keyboard = _build_closed_days_keyboard([])
    await update.message.reply_text("Which days is it closed? (select then 💾 Save) or /skip", reply_markup=keyboard)
    return AddState.CLOSED_DAYS


async def add_closed_days_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "add_days_save":
        return await _show_confirm(query, context)

    if data.startswith("add_day:"):
        day = int(data.split(":")[1])
        closed = context.user_data["add_restaurant"]["closed_days"]
        if day in closed:
            closed.remove(day)
        else:
            closed.append(day)

        keyboard = _build_closed_days_keyboard(closed)
        await query.edit_message_reply_markup(reply_markup=keyboard)

    return AddState.CLOSED_DAYS


async def add_closed_days_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["add_restaurant"]["closed_days"] = []
    data = context.user_data["add_restaurant"]
    text = _format_confirm_text(data)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="add_confirm:yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="add_confirm:no"),
        ]
    ])
    await update.message.reply_text(text, reply_markup=keyboard)
    return AddState.CONFIRM


async def _show_confirm(query, context) -> int:
    data = context.user_data["add_restaurant"]
    text = _format_confirm_text(data)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="add_confirm:yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="add_confirm:no"),
        ]
    ])
    await query.edit_message_text(text, reply_markup=keyboard)
    return AddState.CONFIRM


async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "add_confirm:no":
        await query.edit_message_text("Cancelled")
        return ConversationHandler.END

    telegram_id = str(query.from_user.id)
    data = context.user_data["add_restaurant"]

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, query.from_user.full_name or "Unknown")

        price_level = None
        if data.get("price"):
            if data["price"] <= 50:
                price_level = 1
            elif data["price"] <= 100:
                price_level = 2
            elif data["price"] <= 200:
                price_level = 3
            else:
                price_level = 4

        types = [data["category"]] if data.get("category") else []

        create_data = ManualRestaurantCreate(
            name=data["name"],
            price_level=price_level,
            types=types,
            closed_weekdays=data.get("closed_days") or [],
        )
        restaurant_repo.create_manual(db, create_data, user.id)

        await query.edit_message_text(f"Added \"{data['name']}\" successfully ✅")
    except Exception:
        logger.exception("Error saving restaurant")
        await query.edit_message_text("Something went wrong. Please try again")
    finally:
        db.close()

    return ConversationHandler.END


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.effective_user or not update.message:
        return ConversationHandler.END

    telegram_id = str(update.effective_user.id)

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, update.effective_user.full_name or "Unknown")
        all_restaurants, _ = restaurant_repo.list_all(db, page_size=200)
        manual_restaurants = [r for r in all_restaurants if r.added_by is not None]

        if not manual_restaurants:
            await update.message.reply_text("No manually added restaurants yet. Try /addrestaurant first")
            return ConversationHandler.END

        context.user_data["my_restaurants"] = {str(r.id): r.name for r in manual_restaurants[:10]}

        buttons = []
        for i, r in enumerate(manual_restaurants[:10]):
            buttons.append([InlineKeyboardButton(f"{i+1}. {r.name}", callback_data=f"edit_pick:{r.id}")])
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="edit_pick:cancel")])

        await update.message.reply_text("Select a restaurant to edit:", reply_markup=InlineKeyboardMarkup(buttons))
        return EditState.SELECT_RESTAURANT
    except Exception:
        logger.exception("Error in edit start")
        await update.message.reply_text("Something went wrong. Try again")
        return ConversationHandler.END
    finally:
        db.close()


async def edit_select_restaurant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "edit_pick:cancel":
        await query.edit_message_text("Cancelled")
        return ConversationHandler.END

    restaurant_id = data.split(":")[1]
    context.user_data["editing_restaurant_id"] = restaurant_id

    db = SessionLocal()
    try:
        r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
        if not r:
            await query.edit_message_text("Restaurant not found")
            return ConversationHandler.END

        text = _format_restaurant_details(r)
        keyboard = _build_edit_menu_keyboard(restaurant_id)
        await query.edit_message_text(text, reply_markup=keyboard)
        return EditState.SELECT_FIELD
    except Exception:
        logger.exception("Error selecting restaurant")
        await query.edit_message_text("Something went wrong")
        return ConversationHandler.END
    finally:
        db.close()


async def edit_select_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "edit_field:close":
        await query.edit_message_text("Closed")
        return ConversationHandler.END

    if data == "edit_field:delete":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Delete", callback_data="edit_delete:yes"),
                InlineKeyboardButton("❌ Keep", callback_data="edit_delete:no"),
            ]
        ])
        await query.edit_message_text("Are you sure you want to delete this restaurant?", reply_markup=keyboard)
        return EditState.DELETE_CONFIRM

    if data == "edit_field:closed_days":
        restaurant_id = context.user_data["editing_restaurant_id"]
        db = SessionLocal()
        try:
            r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
            current_days = r.closed_weekdays or [] if r else []
            context.user_data["edit_closed_days"] = list(current_days)
            keyboard = _build_edit_closed_days_keyboard(current_days)
            await query.edit_message_text("Select closed days:", reply_markup=keyboard)
            return EditState.EDIT_CLOSED_DAYS
        finally:
            db.close()

    field = data.split(":")[1]
    context.user_data["editing_field"] = field

    prompts = {
        "name": "Enter new name:",
        "price": "Enter new price (number):",
        "category": "Enter new category:",
    }
    await query.edit_message_text(prompts.get(field, "Enter new value:"))
    return EditState.EDIT_VALUE


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    field = context.user_data.get("editing_field")
    restaurant_id = context.user_data.get("editing_restaurant_id")

    db = SessionLocal()
    try:
        r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
        if not r:
            await update.message.reply_text("Restaurant not found")
            return ConversationHandler.END

        if field == "name":
            if not text or len(text) > 100:
                await update.message.reply_text("Name must be under 100 characters")
                return EditState.EDIT_VALUE
            r.name = text
        elif field == "price":
            try:
                price = int(text)
                if price <= 0:
                    raise ValueError
                if price <= 50:
                    r.price_level = 1
                elif price <= 100:
                    r.price_level = 2
                elif price <= 200:
                    r.price_level = 3
                else:
                    r.price_level = 4
            except ValueError:
                await update.message.reply_text("Please enter a number > 0")
                return EditState.EDIT_VALUE
        elif field == "category":
            r.types = [text]

        db.commit()

        details = _format_restaurant_details(r)
        keyboard = _build_edit_menu_keyboard(restaurant_id)
        await update.message.reply_text(f"Updated ✅\n\n{details}", reply_markup=keyboard)
        return EditState.SELECT_FIELD
    except Exception:
        logger.exception("Error editing restaurant")
        await update.message.reply_text("Something went wrong")
        return ConversationHandler.END
    finally:
        db.close()


async def edit_closed_days_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "edit_days_save":
        restaurant_id = context.user_data["editing_restaurant_id"]
        closed_days = context.user_data["edit_closed_days"]

        db = SessionLocal()
        try:
            r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
            if r:
                r.closed_weekdays = closed_days or None
                db.commit()

                details = _format_restaurant_details(r)
                keyboard = _build_edit_menu_keyboard(restaurant_id)
                await query.edit_message_text(f"Updated closed days ✅\n\n{details}", reply_markup=keyboard)
        finally:
            db.close()
        return EditState.SELECT_FIELD

    if data.startswith("edit_day:"):
        day = int(data.split(":")[1])
        closed = context.user_data["edit_closed_days"]
        if day in closed:
            closed.remove(day)
        else:
            closed.append(day)

        keyboard = _build_edit_closed_days_keyboard(closed)
        await query.edit_message_reply_markup(reply_markup=keyboard)

    return EditState.EDIT_CLOSED_DAYS


async def edit_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "edit_delete:no":
        restaurant_id = context.user_data["editing_restaurant_id"]
        db = SessionLocal()
        try:
            r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
            if r:
                details = _format_restaurant_details(r)
                keyboard = _build_edit_menu_keyboard(restaurant_id)
                await query.edit_message_text(details, reply_markup=keyboard)
                return EditState.SELECT_FIELD
        finally:
            db.close()
        await query.edit_message_text("Cancelled")
        return ConversationHandler.END

    restaurant_id = context.user_data["editing_restaurant_id"]
    db = SessionLocal()
    try:
        deleted = restaurant_repo.delete(db, uuid.UUID(restaurant_id))
        if deleted:
            await query.edit_message_text("Restaurant deleted 🗑️")
        else:
            await query.edit_message_text("Restaurant not found")
    except Exception:
        logger.exception("Error deleting restaurant")
        await query.edit_message_text("Something went wrong")
    finally:
        db.close()

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled")
    return ConversationHandler.END


def _build_closed_days_keyboard(selected: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, name in enumerate(DAY_NAMES):
        check = "🔴" if i in selected else "🟢"
        row.append(InlineKeyboardButton(f"{check} {name}", callback_data=f"add_day:{i}"))
        if len(row) == 3 or i == len(DAY_NAMES) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("💾 Save", callback_data="add_days_save")])
    return InlineKeyboardMarkup(buttons)


def _build_edit_closed_days_keyboard(selected: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, name in enumerate(DAY_NAMES):
        check = "🔴" if i in selected else "🟢"
        row.append(InlineKeyboardButton(f"{check} {name}", callback_data=f"edit_day:{i}"))
        if len(row) == 3 or i == len(DAY_NAMES) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("💾 Save", callback_data="edit_days_save")])
    return InlineKeyboardMarkup(buttons)


def _build_edit_menu_keyboard(restaurant_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Name", callback_data="edit_field:name"),
            InlineKeyboardButton("💰 Price", callback_data="edit_field:price"),
            InlineKeyboardButton("🍜 Type", callback_data="edit_field:category"),
        ],
        [
            InlineKeyboardButton("📅 Closed", callback_data="edit_field:closed_days"),
            InlineKeyboardButton("🗑️ Delete", callback_data="edit_field:delete"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="edit_field:close")],
    ])


def _format_restaurant_details(r) -> str:
    lines = [f"🍽️ {r.name}"]
    if r.price_level:
        price_text = {1: "≤50฿", 2: "51-100฿", 3: "101-200฿", 4: ">200฿"}.get(r.price_level, "?")
        lines.append(f"💰 Price: {price_text}")
    if r.types:
        lines.append(f"🍜 Type: {', '.join(r.types)}")
    if r.closed_weekdays:
        days = [DAY_NAMES[d] for d in r.closed_weekdays if d < len(DAY_NAMES)]
        lines.append(f"📅 Closed: {', '.join(days)}")
    return "\n".join(lines)


def _format_confirm_text(data: dict) -> str:
    lines = ["Confirm add restaurant?\n"]
    lines.append(f"📍 Name: {data['name']}")
    if data.get("price"):
        lines.append(f"💰 Price: ~{data['price']}฿")
    if data.get("category"):
        lines.append(f"🍜 Type: {data['category']}")
    if data.get("closed_days"):
        days = [DAY_NAMES[d] for d in data["closed_days"] if d < len(DAY_NAMES)]
        lines.append(f"📅 Closed: {', '.join(days)}")
    return "\n".join(lines)


def build_add_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("addrestaurant", add_start)],
        states={
            AddState.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            AddState.PRICE: [
                CommandHandler("skip", add_price),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_price),
            ],
            AddState.CATEGORY: [
                CommandHandler("skip", add_category),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_category),
            ],
            AddState.CLOSED_DAYS: [
                CallbackQueryHandler(add_closed_days_toggle, pattern=r"^add_day"),
                CommandHandler("skip", add_closed_days_skip),
            ],
            AddState.CONFIRM: [
                CallbackQueryHandler(add_confirm, pattern=r"^add_confirm:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
    )


def build_edit_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("editrestaurant", edit_start)],
        states={
            EditState.SELECT_RESTAURANT: [
                CallbackQueryHandler(edit_select_restaurant, pattern=r"^edit_pick:"),
            ],
            EditState.SELECT_FIELD: [
                CallbackQueryHandler(edit_select_field, pattern=r"^edit_field:"),
            ],
            EditState.EDIT_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value),
            ],
            EditState.EDIT_CLOSED_DAYS: [
                CallbackQueryHandler(edit_closed_days_toggle, pattern=r"^edit_day"),
            ],
            EditState.DELETE_CONFIRM: [
                CallbackQueryHandler(edit_delete_confirm, pattern=r"^edit_delete:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
    )
