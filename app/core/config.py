from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Weather API"

    # Admin Settings
    ADMIN_API_KEY: str = "admin-sk"

    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # OpenMeteo API URLs
    OPENMETEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENMETEO_HISTORICAL_URL: str = "https://historical-forecast-api.open-meteo.com/v1/forecast"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()