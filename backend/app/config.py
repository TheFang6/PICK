from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    google_maps_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    base_url: str = ""
    debug: bool = False
    office_lat: float = 13.756331
    office_lng: float = 100.501762

    model_config = {"env_file": ".env"}


settings = Settings()
