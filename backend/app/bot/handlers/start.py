import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.database import SessionLocal
from app.services import pairing_repo, user_repo

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    telegram_id = str(update.effective_user.id)
    name = update.effective_user.full_name or "Unknown"

    db = SessionLocal()
    try:
        user, is_new = user_repo.upsert_by_telegram_id(db, telegram_id, name)
        token = pairing_repo.create_token(db, user.id)

        if is_new:
            text = (
                f"Welcome {name}! \U0001F44B\n"
                f"You are now registered with PICK.\n\n"
                f"Use the button below to open the web app."
            )
        else:
            text = (
                f"Welcome back, {name}! \U0001F44B\n\n"
                f"Use the button below to open the web app."
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "\U0001F310 Open Web App",
                url=f"https://pick.vercel.app/pair?token={token.token}",
            )]
        ])
        await update.message.reply_text(text, reply_markup=keyboard)
    except Exception:
        logger.exception("Error in /start handler")
        await update.message.reply_text("Something went wrong. Please try again.")
    finally:
        db.close()
