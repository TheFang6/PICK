from telegram import Update
from telegram.ext import ContextTypes


async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Unknown command. Type /help to see all available commands."
    )
