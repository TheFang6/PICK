import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.config import settings
from app.database import SessionLocal
from app.services import history_repo, user_repo
from app.services.recommendation import recommend

logger = logging.getLogger(__name__)


def _format_pick(pick):
    distance = ""
    if pick.lat and pick.lng:
        from math import atan2, cos, radians, sin, sqrt

        R = 6371000
        rlat1, rlat2 = radians(settings.office_lat), radians(pick.lat)
        dlat = radians(pick.lat - settings.office_lat)
        dlng = radians(pick.lng - settings.office_lng)
        a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
        d = R * 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = f"{d / 1000:.2f}km" if d >= 1000 else f"{int(d)}m"

    rating = f"\u2b50 {pick.rating}" if pick.rating else ""
    parts = [f"\U0001f3af Pick for you!\n"]
    parts.append(f"\U0001f35c {pick.name}")
    if distance or rating:
        parts.append(f"   {distance} {rating}".strip())
    parts.append("\n\nGo to this place?")
    return "\n".join(parts)


async def gacha_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, name)

        result = await recommend(
            db=db,
            user_ids=[user.id],
            office_lat=settings.office_lat,
            office_lng=settings.office_lng,
        )

        candidates = result["candidates"]
        if not candidates:
            await update.message.reply_text(
                "No restaurants found. Try adding one with /addrestaurant"
            )
            return

        pick = random.choice(candidates[:5])

        text = _format_pick(pick)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("\u2705 Confirm", callback_data=f"gacha_ok:{pick.id}"),
                InlineKeyboardButton("\U0001f504 Reroll", callback_data="gacha_reroll"),
            ]
        ])

        await update.message.reply_text(text, reply_markup=keyboard)

    except Exception:
        logger.exception("Error in /gacha handler")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()


async def gacha_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query or not query.data or not update.effective_user:
        return

    await query.answer()

    restaurant_id = query.data.split(":")[1]
    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, name)
        history_repo.log_lunch(db, restaurant_id, [user.id])
        await query.edit_message_text("\u2705 Saved! Enjoy your meal \U0001f60b")
    except Exception:
        logger.exception("Error in gacha confirm callback")
        await query.edit_message_text("Something went wrong. Please try again.")
    finally:
        db.close()


async def gacha_reroll_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query or not update.effective_user:
        return

    await query.answer()

    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, name)

        result = await recommend(
            db=db,
            user_ids=[user.id],
            office_lat=settings.office_lat,
            office_lng=settings.office_lng,
        )

        candidates = result["candidates"]
        if not candidates:
            await query.edit_message_text(
                "No restaurants found. Try adding one with /addrestaurant"
            )
            return

        pick = random.choice(candidates[:5])

        text = _format_pick(pick)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("\u2705 Confirm", callback_data=f"gacha_ok:{pick.id}"),
                InlineKeyboardButton("\U0001f504 Reroll", callback_data="gacha_reroll"),
            ]
        ])

        await query.edit_message_text(text, reply_markup=keyboard)

    except Exception:
        logger.exception("Error in gacha reroll callback")
        await query.edit_message_text("Something went wrong. Please try again.")
    finally:
        db.close()
