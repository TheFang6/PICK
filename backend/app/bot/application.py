from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.bot.handlers.help import help_handler
from app.bot.handlers.start import start_handler
from app.bot.handlers.unknown import unknown_handler
from app.config import settings

_application: Application | None = None


async def get_application() -> Application:
    global _application
    if _application is None:
        _application = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .updater(None)
            .build()
        )
        _application.add_handler(CommandHandler("start", start_handler))
        _application.add_handler(CommandHandler("help", help_handler))
        _application.add_handler(
            MessageHandler(filters.COMMAND, unknown_handler)
        )
        await _application.initialize()
    return _application
