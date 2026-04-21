import logging
import random
import uuid

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from app.config import settings
from app.database import SessionLocal
from app.services import attendance_repo, poll_repo, user_repo
from app.services.recommendation import recommend

logger = logging.getLogger(__name__)

OFFICE_LAT = 13.756331
OFFICE_LNG = 100.501762


def _build_poll_keyboard(poll_id: uuid.UUID, candidates: list) -> InlineKeyboardMarkup:
    number_emojis = ["\u0031\uFE0F\u20E3", "\u0032\uFE0F\u20E3", "\u0033\uFE0F\u20E3"]
    buttons = []
    for i, r in enumerate(candidates):
        emoji = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
        label = f"{emoji} {r.name}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"vote:{poll_id}:{i}")])

    buttons.append([
        InlineKeyboardButton("\U0001F3B2 Gacha!", callback_data=f"gacha:{poll_id}"),
        InlineKeyboardButton("\u274C Cancel", callback_data=f"cancel:{poll_id}"),
    ])
    return InlineKeyboardMarkup(buttons)


def _build_poll_text(candidates: list, vote_counts: dict | None = None, total_votes: int = 0, total_attendees: int = 0) -> str:
    from zoneinfo import ZoneInfo
    from datetime import datetime

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    date_str = now.strftime("%d %b %Y")

    lines = [
        f"\U0001F37D Lunch today ({date_str})",
        f"\u23F1 Vote within 10 min | Votes: {total_votes}/{total_attendees}",
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


def _format_solo_pick(pick) -> str:
    distance = ""
    if pick.lat and pick.lng:
        from math import atan2, cos, radians, sin, sqrt

        R = 6371000
        rlat1, rlat2 = radians(OFFICE_LAT), radians(pick.lat)
        dlat = radians(pick.lat - OFFICE_LAT)
        dlng = radians(pick.lng - OFFICE_LNG)
        a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
        d = R * 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = f"{int(d)}m"

    rating = f"⭐ {pick.rating}" if pick.rating else ""
    parts = [f"\U0001f3af Pick for you!\n"]
    parts.append(f"\U0001f35c {pick.name}")
    if distance or rating:
        parts.append(f"   {distance} {rating}".strip())
    parts.append("\n\nGo to this place?")
    return "\n".join(parts)


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
                office_lat=OFFICE_LAT,
                office_lng=OFFICE_LNG,
            )
            candidates = result["candidates"]
            if not candidates:
                await update.message.reply_text("No restaurants found. Try adding one with /addrestaurant")
                return

            pick = random.choice(candidates[:5])
            text = _format_solo_pick(pick)
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data=f"gacha_ok:{pick.id}"),
                    InlineKeyboardButton("\U0001f504 Reroll", callback_data="gacha_reroll"),
                ]
            ])
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
            office_lat=OFFICE_LAT,
            office_lng=OFFICE_LNG,
        )

        candidates = result["candidates"]
        session_id = result["session_id"]

        if not candidates:
            await update.message.reply_text("No restaurants found nearby. Try adding some manually with /addrestaurant")
            return

        poll = poll_repo.create_poll(db, str(update.effective_chat.id), [r.id for r in candidates], session_id, user.id)
        text = _build_poll_text(candidates, total_attendees=len(attendee_ids))
        keyboard = _build_poll_keyboard(poll.id, candidates)
        msg = await update.message.reply_text(text, reply_markup=keyboard)
        poll_repo.set_message_id(db, poll.id, msg.message_id)

    except Exception:
        logger.exception("Error in /lunch handler")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()
