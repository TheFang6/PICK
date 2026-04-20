import logging
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database import SessionLocal
from app.models.restaurant import Restaurant
from app.models.user_blacklist import BlacklistMode
from app.services import blacklist_repo, restaurant_repo, user_repo

logger = logging.getLogger(__name__)


def _search_restaurants(db, query: str) -> list[Restaurant]:
    all_restaurants, _ = restaurant_repo.list_all(db, page_size=200)
    query_lower = query.lower()
    return [r for r in all_restaurants if query_lower in r.name.lower()]


async def blacklist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    args = context.args or []

    if not args:
        await update.message.reply_text(
            "📋 Blacklist commands:\n\n"
            "/blacklist add <ชื่อร้าน> — เพิ่มร้านเข้า blacklist\n"
            "/blacklist list — ดูร้านที่ blacklist\n"
            "/blacklist remove <ชื่อร้าน> — ลบร้านออกจาก blacklist"
        )
        return

    subcommand = args[0].lower()
    rest_args = " ".join(args[1:])

    if subcommand == "add":
        await _blacklist_add(update, context, rest_args)
    elif subcommand == "list":
        await _blacklist_list(update, context)
    elif subcommand == "remove":
        await _blacklist_remove(update, context, rest_args)
    else:
        await update.message.reply_text("ไม่เข้าใจคำสั่ง ลอง /blacklist add, /blacklist list, หรือ /blacklist remove")


async def _blacklist_add(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    if not query:
        await update.message.reply_text("กรุณาระบุชื่อร้าน เช่น /blacklist add ส้มตำ")
        return

    db = SessionLocal()
    try:
        matches = _search_restaurants(db, query)

        if not matches:
            await update.message.reply_text(f"ไม่เจอร้าน \"{query}\" ลองค้นใหม่")
            return

        if len(matches) == 1:
            restaurant = matches[0]
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🚫 ถาวร", callback_data=f"bl_mode:{restaurant.id}:permanent"),
                    InlineKeyboardButton("📅 แค่วันนี้", callback_data=f"bl_mode:{restaurant.id}:today"),
                ],
                [InlineKeyboardButton("❌ ยกเลิก", callback_data="bl_mode:cancel")],
            ])
            await update.message.reply_text(
                f"Blacklist \"{restaurant.name}\" แบบไหน?",
                reply_markup=keyboard,
            )
            return

        buttons = []
        for r in matches[:5]:
            buttons.append([InlineKeyboardButton(r.name, callback_data=f"bl_pick:{r.id}")])
        buttons.append([InlineKeyboardButton("❌ ยกเลิก", callback_data="bl_pick:cancel")])

        await update.message.reply_text(
            f"เจอ {len(matches)} ร้าน เลือกร้านที่ต้องการ:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception:
        logger.exception("Error in blacklist add")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()


async def _blacklist_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, update.effective_user.full_name or "Unknown")
        entries = blacklist_repo.list_by_user(db, user.id)

        if not entries:
            await update.message.reply_text("ยังไม่มีร้านใน blacklist")
            return

        permanent = []
        today_only = []
        for e in entries:
            r = restaurant_repo.get_by_id(db, e.restaurant_id)
            name = r.name if r else "Unknown"
            if e.mode == BlacklistMode.PERMANENT:
                permanent.append(name)
            else:
                today_only.append(name)

        lines = ["📋 Blacklist ของคุณ:\n"]
        if permanent:
            lines.append(f"🚫 ถาวร ({len(permanent)}):")
            for name in permanent:
                lines.append(f"  • {name}")
        if today_only:
            lines.append(f"\n📅 แค่วันนี้ ({len(today_only)}):")
            for name in today_only:
                lines.append(f"  • {name}")

        await update.message.reply_text("\n".join(lines))
    except Exception:
        logger.exception("Error in blacklist list")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()


async def _blacklist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    if not query:
        await update.message.reply_text("กรุณาระบุชื่อร้าน เช่น /blacklist remove ส้มตำ")
        return

    telegram_id = str(update.effective_user.id)

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, update.effective_user.full_name or "Unknown")
        entries = blacklist_repo.list_by_user(db, user.id)

        query_lower = query.lower()
        matching = []
        for e in entries:
            r = restaurant_repo.get_by_id(db, e.restaurant_id)
            if r and query_lower in r.name.lower():
                matching.append((e, r))

        if not matching:
            await update.message.reply_text(f"ไม่เจอร้าน \"{query}\" ใน blacklist ของคุณ")
            return

        if len(matching) == 1:
            entry, restaurant = matching[0]
            blacklist_repo.remove(db, user.id, entry.id)
            await update.message.reply_text(f"ลบ \"{restaurant.name}\" ออกจาก blacklist แล้ว ✅")
            return

        buttons = []
        for entry, r in matching[:5]:
            buttons.append([InlineKeyboardButton(r.name, callback_data=f"bl_rm:{entry.id}")])
        buttons.append([InlineKeyboardButton("❌ ยกเลิก", callback_data="bl_rm:cancel")])

        await update.message.reply_text(
            "เจอหลายร้าน เลือกร้านที่ต้องการลบ:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except Exception:
        logger.exception("Error in blacklist remove")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()


async def blacklist_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 2:
        return

    _, restaurant_id_str = parts

    if restaurant_id_str == "cancel":
        await query.edit_message_text("ยกเลิกแล้ว")
        return

    try:
        restaurant_id = uuid.UUID(restaurant_id_str)
    except ValueError:
        return

    db = SessionLocal()
    try:
        restaurant = restaurant_repo.get_by_id(db, restaurant_id)
        if not restaurant:
            await query.edit_message_text("ไม่เจอร้านนี้แล้ว")
            return

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚫 ถาวร", callback_data=f"bl_mode:{restaurant.id}:permanent"),
                InlineKeyboardButton("📅 แค่วันนี้", callback_data=f"bl_mode:{restaurant.id}:today"),
            ],
            [InlineKeyboardButton("❌ ยกเลิก", callback_data="bl_mode:cancel")],
        ])
        await query.edit_message_text(
            f"Blacklist \"{restaurant.name}\" แบบไหน?",
            reply_markup=keyboard,
        )
    except Exception:
        logger.exception("Error in blacklist pick callback")
    finally:
        db.close()


async def blacklist_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    if parts[1] == "cancel":
        await query.edit_message_text("ยกเลิกแล้ว")
        return

    if len(parts) != 3:
        return

    _, restaurant_id_str, mode_str = parts

    telegram_id = str(query.from_user.id)

    db = SessionLocal()
    try:
        restaurant_id = uuid.UUID(restaurant_id_str)
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, query.from_user.full_name or "Unknown")
        restaurant = restaurant_repo.get_by_id(db, restaurant_id)

        if not restaurant:
            await query.edit_message_text("ไม่เจอร้านนี้แล้ว")
            return

        mode = BlacklistMode.PERMANENT if mode_str == "permanent" else BlacklistMode.TODAY
        blacklist_repo.add(db, user.id, restaurant_id, mode)

        mode_text = "ถาวร" if mode == BlacklistMode.PERMANENT else "แค่วันนี้"
        await query.edit_message_text(
            f"เพิ่ม \"{restaurant.name}\" เข้า blacklist ({mode_text}) แล้วครับ ✅"
        )
    except Exception:
        logger.exception("Error in blacklist mode callback")
    finally:
        db.close()


async def blacklist_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 2:
        return

    _, entry_id_str = parts

    if entry_id_str == "cancel":
        await query.edit_message_text("ยกเลิกแล้ว")
        return

    telegram_id = str(query.from_user.id)

    db = SessionLocal()
    try:
        entry_id = uuid.UUID(entry_id_str)
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, query.from_user.full_name or "Unknown")

        removed = blacklist_repo.remove(db, user.id, entry_id)
        if removed:
            await query.edit_message_text("ลบออกจาก blacklist แล้ว ✅")
        else:
            await query.edit_message_text("ไม่เจอรายการนี้ใน blacklist")
    except Exception:
        logger.exception("Error in blacklist remove callback")
    finally:
        db.close()
