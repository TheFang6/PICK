from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    google_maps_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    base_url: str = ""
    debug: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
