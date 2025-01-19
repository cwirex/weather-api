from fastapi import HTTPException, Header, Depends
from typing import AsyncGenerator
from app.core.config import settings
from app.services.factory import get_weather_cache, get_weather_client
from app.services.weather_cache import WeatherCache
from app.services.openmeteo_client import OpenMeteoClient


async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key")
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "API key is required"}
        )
    return x_api_key


async def verify_admin_access(
    x_api_key: str = Depends(verify_api_key)
) -> str:
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail={"error": "Admin access required"}
        )
    return x_api_key


async def get_cache() -> AsyncGenerator[WeatherCache, None]:
    cache = get_weather_cache()
    try:
        yield cache
    finally:
        await cache.close()


async def get_weather_service() -> OpenMeteoClient:
    return get_weather_client()