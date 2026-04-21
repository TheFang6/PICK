from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.bot.handlers.attendance import in_handler, wfh_handler
from app.bot.handlers.gacha_solo import gacha_confirm_callback, gacha_handler, gacha_reroll_callback
from app.bot.handlers.help import help_handler
from app.bot.handlers.lunch import lunch_handler
from app.bot.handlers.poll_callbacks import cancel_callback, gacha_callback, vote_callback
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
        _application.add_handler(CommandHandler("wfh", wfh_handler))
        _application.add_handler(CommandHandler("in", in_handler))
        _application.add_handler(CommandHandler("lunch", lunch_handler))
        _application.add_handler(CommandHandler("gacha", gacha_handler))
        _application.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^vote:"))
        _application.add_handler(CallbackQueryHandler(cancel_callback, pattern=r"^cancel:"))
        _application.add_handler(CallbackQueryHandler(gacha_callback, pattern=r"^gacha:"))
        _application.add_handler(CallbackQueryHandler(gacha_confirm_callback, pattern=r"^gacha_ok:"))
        _application.add_handler(CallbackQueryHandler(gacha_reroll_callback, pattern=r"^gacha_reroll"))
        _application.add_handler(
            MessageHandler(filters.COMMAND, unknown_handler)
        )
        await _application.initialize()
    return _application
