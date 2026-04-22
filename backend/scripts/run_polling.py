"""Run the Telegram bot in polling mode for local development.

Usage:
    cd backend && python scripts/run_polling.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(override=True)

from telegram import BotCommand  # noqa: E402
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters  # noqa: E402

from app.bot.handlers.attendance import in_handler, wfh_handler  # noqa: E402
from app.bot.handlers.blacklist import (  # noqa: E402
    blacklist_handler,
    blacklist_mode_callback,
    blacklist_pick_callback,
    blacklist_remove_callback,
)
from app.bot.handlers.gacha_solo import gacha_confirm_callback, gacha_handler, gacha_reroll_callback  # noqa: E402
from app.bot.handlers.help import help_handler  # noqa: E402
from app.bot.handlers.lunch import dm_pick_callback, lunch_handler  # noqa: E402
from app.bot.handlers.poll_callbacks import cancel_callback, gacha_callback, skip_callback, vote_callback  # noqa: E402
from app.bot.handlers.restaurant_cmd import build_add_conversation_handler, build_edit_conversation_handler  # noqa: E402
from app.bot.handlers.start import start_handler  # noqa: E402
from app.bot.handlers.unknown import unknown_handler  # noqa: E402
from app.bot.poll_timeout import check_expired_polls  # noqa: E402
from app.config import settings  # noqa: E402

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def main():
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("wfh", wfh_handler))
    app.add_handler(CommandHandler("in", in_handler))
    app.add_handler(CommandHandler("lunch", lunch_handler))
    app.add_handler(CommandHandler("gacha", gacha_handler))
    app.add_handler(CommandHandler("blacklist", blacklist_handler))
    app.add_handler(build_add_conversation_handler())
    app.add_handler(build_edit_conversation_handler())
    app.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^vote:"))
    app.add_handler(CallbackQueryHandler(cancel_callback, pattern=r"^cancel:"))
    app.add_handler(CallbackQueryHandler(gacha_callback, pattern=r"^gacha:"))
    app.add_handler(CallbackQueryHandler(skip_callback, pattern=r"^skip:"))
    app.add_handler(CallbackQueryHandler(dm_pick_callback, pattern=r"^dm_pick:"))
    app.add_handler(CallbackQueryHandler(gacha_confirm_callback, pattern=r"^gacha_ok:"))
    app.add_handler(CallbackQueryHandler(gacha_reroll_callback, pattern=r"^gacha_reroll"))
    app.add_handler(CallbackQueryHandler(blacklist_pick_callback, pattern=r"^bl_pick:"))
    app.add_handler(CallbackQueryHandler(blacklist_mode_callback, pattern=r"^bl_mode:"))
    app.add_handler(CallbackQueryHandler(blacklist_remove_callback, pattern=r"^bl_rm:"))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_handler))

    commands = [
        BotCommand("start", "Register and get pairing link for web app"),
        BotCommand("help", "Show available commands"),
        BotCommand("lunch", "Get restaurant recommendations for lunch"),
        BotCommand("gacha", "Random solo restaurant pick"),
        BotCommand("wfh", "Mark yourself as working from home today"),
        BotCommand("in", "Mark yourself as in the office today"),
        BotCommand("blacklist", "Manage your restaurant blacklist"),
        BotCommand("addrestaurant", "Add a new restaurant"),
        BotCommand("editrestaurant", "Edit or delete your restaurants"),
    ]

    logging.info("Bot starting in polling mode...")
    await app.initialize()
    await app.bot.set_my_commands(commands)
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    try:
        while True:
            await check_expired_polls(app)
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
