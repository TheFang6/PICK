import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.database import SessionLocal
from app.models.attendance import AttendanceStatus
from app.services import attendance_repo, user_repo

logger = logging.getLogger(__name__)


async def wfh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, name)
        attendance_repo.set_status(db, user.id, AttendanceStatus.WFH)
        await update.message.reply_text("Got it! Enjoy working from home \U0001F3E0")
    except Exception:
        logger.exception("Error in /wfh handler")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()


async def in_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"

    db = SessionLocal()
    try:
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, name)
        attendance_repo.set_status(db, user.id, AttendanceStatus.IN_OFFICE)
        await update.message.reply_text("Got it! See you at the office \U0001F3E2")
    except Exception:
        logger.exception("Error in /in handler")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()
