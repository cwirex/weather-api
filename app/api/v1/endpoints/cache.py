from fastapi import APIRouter, Path, Depends
from app.api.dependencies import verify_admin_access, get_cache, get_mongo_storage
from app.services.mongo_storage import MongoWeatherStorage
from app.services.weather_cache import WeatherCache

router = APIRouter()

@router.get("/stats")
async def get_cache_stats(
        weather_cache: WeatherCache = Depends(get_cache),
        mongo_storage: MongoWeatherStorage = Depends(get_mongo_storage),
        admin_key: str = Depends(verify_admin_access)
):
    """Get combined cache and MongoDB storage statistics (admin only)"""
    cache_stats = await weather_cache.get_stats()
    mongo_stats = await mongo_storage.get_stats()

    return {
        "cache": cache_stats,
        "mongodb": mongo_stats
    }

@router.delete("/{city}")
async def clear_city_cache(
    city: str = Path(..., description="City name"),
    weather_cache: WeatherCache = Depends(get_cache),
    admin_key: str = Depends(verify_admin_access)
):
    """Clear cache for specific city (admin only)"""
    return await weather_cache.clear_city_cache(city)