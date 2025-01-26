from fastapi import APIRouter, Path, Query, Depends
from app.api.dependencies import verify_admin_access, get_cache, get_mongo_storage, get_weather_service
from app.services.mongo_storage import MongoWeatherStorage
from app.services.weather_cache import WeatherCache
from app.services.population_service import PopulationService

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


@router.post("/populate/{city}")
async def populate_historical_data(
        city: str = Path(..., description="City key (e.g., london,gb)"),
        days_back: int = Query(..., gt=0, le=365, description="Number of days to go back"),
        delay: float = Query(1.0, ge=0.5, le=5.0, description="Delay between API requests in seconds"),
        weather_client=Depends(get_weather_service),
        mongo_storage: MongoWeatherStorage = Depends(get_mongo_storage),
        admin_key: str = Depends(verify_admin_access)
):
    """
    Populate historical weather data for a specific city (admin only)

    - Requires admin API key
    - City must be in the tracked cities list
    - Maximum 365 days of historical data
    - Minimum delay between requests is 0.5 seconds
    """
    population_service = PopulationService(weather_client, mongo_storage)
    return await population_service.populate_historical_data(
        city_key=city.lower(),
        days_back=days_back,
        delay_between_requests=delay
    )