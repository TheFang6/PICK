import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.database import SessionLocal
from app.services import history_repo, user_repo
from app.services.recommendation import recommend

logger = logging.getLogger(__name__)

OFFICE_LAT = 13.756331
OFFICE_LNG = 100.501762


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
            office_lat=OFFICE_LAT,
            office_lng=OFFICE_LNG,
        )

        candidates = result["candidates"]
        if not candidates:
            await update.message.reply_text("ไม่เจอร้านอาหารเลย ลองเพิ่มร้านด้วย /addrestaurant")
            return

        pick = candidates[0]

        history_repo.log_lunch(db, pick.id, [user.id])

        distance = ""
        if pick.lat and pick.lng:
            from math import radians, sin, cos, sqrt, atan2
            R = 6371000
            rlat1, rlat2 = radians(OFFICE_LAT), radians(pick.lat)
            dlat = radians(pick.lat - OFFICE_LAT)
            dlng = radians(pick.lng - OFFICE_LNG)
            a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
            d = R * 2 * atan2(sqrt(a), sqrt(1 - a))
            distance = f"{int(d)}m"

        rating = f"\u2B50 {pick.rating}" if pick.rating else ""
        parts = [f"\U0001F3AF วันนี้ไปร้านนี้เลยนะ\n"]
        parts.append(f"\U0001F35C {pick.name}")
        if distance or rating:
            parts.append(f"   {distance} {rating}".strip())

        await update.message.reply_text("\n".join(parts))

    except Exception:
        logger.exception("Error in /gacha handler")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()
