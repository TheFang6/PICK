from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    google_maps_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    base_url: str = ""
    web_url: str = "https://pick.vercel.app"
    allowed_origins: str = "http://localhost:3000"
    debug: bool = False
    office_lat: float = 18.7964464
    office_lng: float = 99.0164042
    office_radius: int = 1000
    rating_threshold: float = 3.8
    ratings_count_threshold: int = 20

    model_config = {"env_file": ".env"}


settings = Settings()
