from app.core.config import settings
from app.services.weather_cache import WeatherCache
from app.services.openweather_client import OpenWeatherClient

_weather_cache = None
_weather_client = None

def get_weather_cache() -> WeatherCache:
    global _weather_cache
    if _weather_cache is None:
        _weather_cache = WeatherCache(
            redis_host=settings.REDIS_HOST,
            redis_port=settings.REDIS_PORT,
            redis_db=settings.REDIS_DB,
            redis_password=settings.REDIS_PASSWORD
        )
    return _weather_cache

def get_weather_client() -> OpenWeatherClient:
    global _weather_client
    if _weather_client is None:
        _weather_client = OpenWeatherClient(
            api_key=settings.OPENWEATHER_API_KEY,
            base_url=settings.OPENWEATHER_BASE_URL
        )
    return _weather_client