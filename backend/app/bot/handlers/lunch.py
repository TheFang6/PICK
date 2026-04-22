import logging
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from app.config import settings
from app.database import SessionLocal
from app.services import attendance_repo, poll_repo, user_repo
from app.services.recommendation import recommend

logger = logging.getLogger(__name__)



def _build_poll_keyboard(poll_id: uuid.UUID, candidates: list) -> InlineKeyboardMarkup:
    number_emojis = ["\u0031\uFE0F\u20E3", "\u0032\uFE0F\u20E3", "\u0033\uFE0F\u20E3"]
    buttons = []
    for i, r in enumerate(candidates):
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        label = f"{emoji} {r.name}"
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"vote:{poll_id}:{i}"),
            InlineKeyboardButton("❌", callback_data=f"skip:{poll_id}:{i}"),
        ])

    buttons.append([
        InlineKeyboardButton("\U0001F3B2 Gacha!", callback_data=f"gacha:{poll_id}"),
        InlineKeyboardButton("\u274C Cancel", callback_data=f"cancel:{poll_id}"),
    ])
    return InlineKeyboardMarkup(buttons)


def _build_poll_text(candidates: list, vote_counts: dict | None = None, total_votes: int = 0) -> str:
    from zoneinfo import ZoneInfo
    from datetime import datetime

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    date_str = now.strftime("%d %b %Y")

    lines = [
        f"\U0001F37D Lunch today ({date_str})",
        f"\u23F1 Vote within 10 min | Votes: {total_votes}",
        "",
    ]

    number_emojis = ["1\uFE0F\u20E3", "2\uFE0F\u20E3", "3\uFE0F\u20E3"]
    for i, r in enumerate(candidates):
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        rating = f"\u2B50 {r.rating}" if r.rating else ""
        count = vote_counts.get(str(r.id), 0) if vote_counts else 0
        vote_indicator = f" [{count} vote{'s' if count != 1 else ''}]" if count > 0 else ""
        lines.append(f"{emoji} {r.name} {rating}{vote_indicator}")

    return "\n".join(lines)


def _build_dm_text(candidates: list) -> str:
    from zoneinfo import ZoneInfo
    from datetime import datetime

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    date_str = now.strftime("%d %b %Y")

    lines = [
        f"\U0001F37D Lunch today ({date_str})",
        f"Pick one!\n",
    ]

    number_emojis = ["1️⃣", "2️⃣", "3️⃣"]
    for i, r in enumerate(candidates):
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        rating = f"⭐ {r.rating}" if r.rating else ""
        lines.append(f"{emoji} {r.name} {rating}")

    return "\n".join(lines)


def _build_dm_keyboard(candidates: list) -> InlineKeyboardMarkup:
    number_emojis = ["1️⃣", "2️⃣", "3️⃣"]
    buttons = []
    for i, r in enumerate(candidates):
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        label = f"{emoji} {r.name}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dm_pick:{r.id}")])
    return InlineKeyboardMarkup(buttons)


async def lunch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"
    is_dm = update.effective_chat.type == ChatType.PRIVATE

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, name)

        if is_dm:
            result = await recommend(
                db=db,
                user_ids=[user.id],
                office_lat=settings.office_lat,
                office_lng=settings.office_lng,
            )
            candidates = result["candidates"]
            if not candidates:
                await update.message.reply_text("No restaurants found. Try adding one with /addrestaurant")
                return

            picks = candidates[:3]
            text = _build_dm_text(picks)
            keyboard = _build_dm_keyboard(picks)
            await update.message.reply_text(text, reply_markup=keyboard)
            return

        attendees = attendance_repo.get_attendees(db)
        attendee_ids = [u.id for u in attendees]

        if not attendee_ids:
            await update.message.reply_text("No one is in the office today \U0001F614")
            return

        result = await recommend(
            db=db,
            user_ids=attendee_ids,
            office_lat=settings.office_lat,
            office_lng=settings.office_lng,
        )

        candidates = result["candidates"]
        session_id = result["session_id"]

        if not candidates:
            await update.message.reply_text("No restaurants found nearby. Try adding some manually with /addrestaurant")
            return

        poll = poll_repo.create_poll(db, str(update.effective_chat.id), [r.id for r in candidates], session_id, user.id)
        text = _build_poll_text(candidates)
        keyboard = _build_poll_keyboard(poll.id, candidates)
        msg = await update.message.reply_text(text, reply_markup=keyboard)
        poll_repo.set_message_id(db, poll.id, msg.message_id)

    except Exception:
        logger.exception("Error in /lunch handler")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()


async def dm_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return

    await query.answer()

    restaurant_id = query.data.split(":")[1]
    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"

    from app.services import history_repo, restaurant_repo

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, name)
        restaurant = restaurant_repo.get_by_id(db, uuid.UUID(restaurant_id))
        if not restaurant:
            await query.edit_message_text("Restaurant not found.")
            return

        history_repo.log_lunch(db, restaurant.id, [user.id])
        await query.edit_message_text(f"✅ {restaurant.name} — Enjoy your meal! \U0001F60B")
    except Exception:
        logger.exception("Error in dm_pick callback")
        await query.edit_message_text("Something went wrong. Please try again.")
    finally:
        db.close()
