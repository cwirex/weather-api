from app.core.config import settings
from app.services.weather_cache import WeatherCache
from app.services.openmeteo_client import OpenMeteoClient
from app.services.mongo_storage import MongoWeatherStorage


_weather_client = None
_weather_cache = None
_mongo_storage = None

def get_weather_client() -> OpenMeteoClient:
    global _weather_client
    if _weather_client is None:
        _weather_client = OpenMeteoClient()
    return _weather_client

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

def get_mongo_storage_instance() -> MongoWeatherStorage:
    global _mongo_storage
    if _mongo_storage is None:
        _mongo_storage = MongoWeatherStorage(
            mongo_url=settings.MONGO_URL,
            database=settings.MONGO_DB,
            collection=settings.MONGO_COLLECTION
        )
    return _mongo_storage