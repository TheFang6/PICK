from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    google_maps_api_key: str = ""
    debug: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
