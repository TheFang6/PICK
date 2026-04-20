"""Set up the Telegram webhook for the bot.

Usage:
    python scripts/setup_webhook.py <base_url>

Example:
    python scripts/setup_webhook.py https://pick-api.up.railway.app
"""

import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

from app.config import settings  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/setup_webhook.py <base_url>")
        print("Example: python scripts/setup_webhook.py https://pick-api.up.railway.app")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    webhook_url = f"{base_url}/webhook/telegram"
    token = settings.telegram_bot_token

    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    params = {"url": webhook_url}
    if settings.telegram_webhook_secret:
        params["secret_token"] = settings.telegram_webhook_secret

    resp = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json=params,
    )
    print(f"setWebhook response: {resp.json()}")

    info_resp = httpx.get(
        f"https://api.telegram.org/bot{token}/getWebhookInfo"
    )
    print(f"getWebhookInfo: {info_resp.json()}")


if __name__ == "__main__":
    main()
