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

DAY_NAMES = ["จันทร์", "อังคาร", "พุธ", "พฤหัส", "ศุกร์", "เสาร์", "อาทิตย์"]


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
    await update.message.reply_text("ชื่อร้านอะไรครับ?")
    return AddState.NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name or len(name) > 100:
        await update.message.reply_text("ชื่อร้านต้องไม่เกิน 100 ตัวอักษร ลองใหม่")
        return AddState.NAME

    context.user_data["add_restaurant"]["name"] = name
    await update.message.reply_text("ราคาต่อจานประมาณเท่าไหร่? (พิมพ์ตัวเลข หรือ /skip)")
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
            await update.message.reply_text("กรุณาใส่ตัวเลขที่มากกว่า 0 หรือ /skip")
            return AddState.PRICE

    await update.message.reply_text("ประเภทร้าน? (เช่น ก๋วยเตี๋ยว, ข้าวแกง, อื่นๆ) หรือ /skip")
    return AddState.CATEGORY


async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "/skip":
        context.user_data["add_restaurant"]["category"] = None
    else:
        context.user_data["add_restaurant"]["category"] = text

    context.user_data["add_restaurant"]["closed_days"] = []
    keyboard = _build_closed_days_keyboard([])
    await update.message.reply_text("ร้านนี้ปิดวันไหนบ้าง? (กดเลือก แล้วกด 💾 Save) หรือ /skip", reply_markup=keyboard)
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
            InlineKeyboardButton("✅ ยืนยัน", callback_data="add_confirm:yes"),
            InlineKeyboardButton("❌ ยกเลิก", callback_data="add_confirm:no"),
        ]
    ])
    await update.message.reply_text(text, reply_markup=keyboard)
    return AddState.CONFIRM


async def _show_confirm(query, context) -> int:
    data = context.user_data["add_restaurant"]
    text = _format_confirm_text(data)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ยืนยัน", callback_data="add_confirm:yes"),
            InlineKeyboardButton("❌ ยกเลิก", callback_data="add_confirm:no"),
        ]
    ])
    await query.edit_message_text(text, reply_markup=keyboard)
    return AddState.CONFIRM


async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "add_confirm:no":
        await query.edit_message_text("ยกเลิกแล้ว")
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

        types = [data["category"]] if data.get("category") else None

        create_data = ManualRestaurantCreate(
            name=data["name"],
            price_level=price_level,
            types=types,
            closed_weekdays=data.get("closed_days") or None,
        )
        restaurant_repo.create_manual(db, create_data, user.id)

        await query.edit_message_text(f"เพิ่มร้าน \"{data['name']}\" เรียบร้อยแล้ว ✅")
    except Exception:
        logger.exception("Error saving restaurant")
        await query.edit_message_text("เกิดข้อผิดพลาด ลองใหม่อีกครั้ง")
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
        my_restaurants = [r for r in all_restaurants if r.added_by == user.id]

        if not my_restaurants:
            await update.message.reply_text("คุณยังไม่มีร้านที่เพิ่มเอง ลอง /addrestaurant ก่อน")
            return ConversationHandler.END

        context.user_data["my_restaurants"] = {str(r.id): r.name for r in my_restaurants[:10]}

        buttons = []
        for i, r in enumerate(my_restaurants[:10]):
            buttons.append([InlineKeyboardButton(f"{i+1}. {r.name}", callback_data=f"edit_pick:{r.id}")])
        buttons.append([InlineKeyboardButton("❌ ยกเลิก", callback_data="edit_pick:cancel")])

        await update.message.reply_text("เลือกร้านที่ต้องการแก้ไข:", reply_markup=InlineKeyboardMarkup(buttons))
        return EditState.SELECT_RESTAURANT
    except Exception:
        logger.exception("Error in edit start")
        await update.message.reply_text("เกิดข้อผิดพลาด ลองใหม่")
        return ConversationHandler.END
    finally:
        db.close()


async def edit_select_restaurant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "edit_pick:cancel":
        await query.edit_message_text("ยกเลิกแล้ว")
        return ConversationHandler.END

    restaurant_id = data.split(":")[1]
    context.user_data["editing_restaurant_id"] = restaurant_id

    db = SessionLocal()
    try:
        r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
        if not r:
            await query.edit_message_text("ไม่เจอร้านนี้แล้ว")
            return ConversationHandler.END

        text = _format_restaurant_details(r)
        keyboard = _build_edit_menu_keyboard(restaurant_id)
        await query.edit_message_text(text, reply_markup=keyboard)
        return EditState.SELECT_FIELD
    except Exception:
        logger.exception("Error selecting restaurant")
        await query.edit_message_text("เกิดข้อผิดพลาด")
        return ConversationHandler.END
    finally:
        db.close()


async def edit_select_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "edit_field:close":
        await query.edit_message_text("ปิดแล้ว")
        return ConversationHandler.END

    if data == "edit_field:delete":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ลบเลย", callback_data="edit_delete:yes"),
                InlineKeyboardButton("❌ ไม่ลบ", callback_data="edit_delete:no"),
            ]
        ])
        await query.edit_message_text("คุณแน่ใจที่จะลบร้านนี้?", reply_markup=keyboard)
        return EditState.DELETE_CONFIRM

    if data == "edit_field:closed_days":
        restaurant_id = context.user_data["editing_restaurant_id"]
        db = SessionLocal()
        try:
            r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
            current_days = r.closed_weekdays or [] if r else []
            context.user_data["edit_closed_days"] = list(current_days)
            keyboard = _build_edit_closed_days_keyboard(current_days)
            await query.edit_message_text("เลือกวันที่ร้านปิด:", reply_markup=keyboard)
            return EditState.EDIT_CLOSED_DAYS
        finally:
            db.close()

    field = data.split(":")[1]
    context.user_data["editing_field"] = field

    prompts = {
        "name": "พิมพ์ชื่อร้านใหม่:",
        "price": "พิมพ์ราคาต่อจานใหม่ (ตัวเลข):",
        "category": "พิมพ์ประเภทร้านใหม่:",
    }
    await query.edit_message_text(prompts.get(field, "พิมพ์ค่าใหม่:"))
    return EditState.EDIT_VALUE


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    field = context.user_data.get("editing_field")
    restaurant_id = context.user_data.get("editing_restaurant_id")

    db = SessionLocal()
    try:
        r = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
        if not r:
            await update.message.reply_text("ไม่เจอร้านนี้แล้ว")
            return ConversationHandler.END

        if field == "name":
            if not text or len(text) > 100:
                await update.message.reply_text("ชื่อต้องไม่เกิน 100 ตัวอักษร")
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
                await update.message.reply_text("กรุณาใส่ตัวเลขที่มากกว่า 0")
                return EditState.EDIT_VALUE
        elif field == "category":
            r.types = [text]

        db.commit()

        details = _format_restaurant_details(r)
        keyboard = _build_edit_menu_keyboard(restaurant_id)
        await update.message.reply_text(f"อัพเดทแล้ว ✅\n\n{details}", reply_markup=keyboard)
        return EditState.SELECT_FIELD
    except Exception:
        logger.exception("Error editing restaurant")
        await update.message.reply_text("เกิดข้อผิดพลาด")
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
                await query.edit_message_text(f"อัพเดทวันปิดแล้ว ✅\n\n{details}", reply_markup=keyboard)
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
        await query.edit_message_text("ยกเลิกแล้ว")
        return ConversationHandler.END

    restaurant_id = context.user_data["editing_restaurant_id"]
    db = SessionLocal()
    try:
        deleted = restaurant_repo.delete(db, uuid.UUID(restaurant_id))
        if deleted:
            await query.edit_message_text("ลบร้านเรียบร้อยแล้ว 🗑️")
        else:
            await query.edit_message_text("ไม่เจอร้านนี้แล้ว")
    except Exception:
        logger.exception("Error deleting restaurant")
        await query.edit_message_text("เกิดข้อผิดพลาด")
    finally:
        db.close()

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("ยกเลิกแล้ว")
    return ConversationHandler.END


def _build_closed_days_keyboard(selected: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, name in enumerate(DAY_NAMES):
        check = "✅" if i in selected else "❌"
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
        check = "✅" if i in selected else "❌"
        row.append(InlineKeyboardButton(f"{check} {name}", callback_data=f"edit_day:{i}"))
        if len(row) == 3 or i == len(DAY_NAMES) - 1:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton("💾 Save", callback_data="edit_days_save")])
    return InlineKeyboardMarkup(buttons)


def _build_edit_menu_keyboard(restaurant_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ ชื่อ", callback_data="edit_field:name"),
            InlineKeyboardButton("💰 ราคา", callback_data="edit_field:price"),
            InlineKeyboardButton("🍜 ประเภท", callback_data="edit_field:category"),
        ],
        [
            InlineKeyboardButton("📅 วันปิด", callback_data="edit_field:closed_days"),
            InlineKeyboardButton("🗑️ ลบร้าน", callback_data="edit_field:delete"),
        ],
        [InlineKeyboardButton("❌ ปิด", callback_data="edit_field:close")],
    ])


def _format_restaurant_details(r) -> str:
    lines = [f"🍽️ {r.name}"]
    if r.price_level:
        price_text = {1: "≤50฿", 2: "51-100฿", 3: "101-200฿", 4: ">200฿"}.get(r.price_level, "?")
        lines.append(f"💰 ราคา: {price_text}")
    if r.types:
        lines.append(f"🍜 ประเภท: {', '.join(r.types)}")
    if r.closed_weekdays:
        days = [DAY_NAMES[d] for d in r.closed_weekdays if d < len(DAY_NAMES)]
        lines.append(f"📅 วันปิด: {', '.join(days)}")
    return "\n".join(lines)


def _format_confirm_text(data: dict) -> str:
    lines = ["ยืนยันเพิ่มร้าน?\n"]
    lines.append(f"📍 ชื่อ: {data['name']}")
    if data.get("price"):
        lines.append(f"💰 ราคา: ~{data['price']}฿")
    if data.get("category"):
        lines.append(f"🍜 ประเภท: {data['category']}")
    if data.get("closed_days"):
        days = [DAY_NAMES[d] for d in data["closed_days"] if d < len(DAY_NAMES)]
        lines.append(f"📅 วันปิด: {', '.join(days)}")
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
