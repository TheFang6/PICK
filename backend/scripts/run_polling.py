"""Run the Telegram bot in polling mode for local development.

Usage:
    cd backend && python -m scripts.run_polling
    # or
    cd backend && python scripts/run_polling.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from telegram.ext import Application, CommandHandler, MessageHandler, filters  # noqa: E402

from app.bot.handlers.attendance import in_handler, wfh_handler  # noqa: E402
from app.bot.handlers.help import help_handler  # noqa: E402
from app.bot.handlers.start import start_handler  # noqa: E402
from app.bot.handlers.unknown import unknown_handler  # noqa: E402
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
    app.add_handler(MessageHandler(filters.COMMAND, unknown_handler))

    logging.info("Bot starting in polling mode...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
