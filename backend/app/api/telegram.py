from fastapi import APIRouter, Header, HTTPException, Request
from telegram import Update

from app.bot.application import get_application
from app.config import settings

router = APIRouter(tags=["telegram"])


@router.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    data = await request.json()
    application = await get_application()
    update = Update.de_json(data=data, bot=application.bot)
    await application.process_update(update)
    return {"ok": True}
