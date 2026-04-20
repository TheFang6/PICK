from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "\U0001F37D *PICK Commands*\n\n"
    "/start \\- Register and get web link\n"
    "/lunch \\- Start lunch recommendation\n"
    "/gacha \\- Reshuffle picks\n"
    "/wfh \\- Announce work from home\n"
    "/in \\- Announce in\\-office\n"
    "/blacklist \\- Manage blacklist\n"
    "/addrestaurant \\- Add a restaurant\n"
    "/editrestaurant \\- Edit your restaurant\n"
    "/help \\- Show this help message"
)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")
