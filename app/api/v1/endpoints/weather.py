from fastapi import APIRouter, Query, Path, HTTPException, Header, Depends
from datetime import datetime, timedelta
from typing import Literal
from app.core.cities_data import CITIES
from app.services.mongo_storage import MongoWeatherStorage
from app.services.openmeteo_client import OpenMeteoClient
from app.services.weather_cache import WeatherCache
from app.models import WeatherMeta
from app.api.dependencies import verify_api_key, get_cache, get_weather_service, get_mongo_storage

router = APIRouter()


def get_city_key(city: str) -> str:
    """Convert city name to city key and validate it exists"""
    city_key = city.lower()
    if city_key in CITIES:
        return city_key

    for key, data in CITIES.items():
        if data["name"].lower() == city.lower():
            return key

    raise HTTPException(
        status_code=404,
        detail={
            "code": "CITY_NOT_FOUND",
            "message": f"City '{city}' not found",
            "details": "Try using city,country format (e.g., london,gb) for more precise results"
        }
    )


@router.get("/current/{city}")
async def get_current_weather(
        city: str = Path(..., description="City name"),
        units: Literal["standard", "metric", "imperial"] = Query("metric"),
        weather_cache: WeatherCache = Depends(get_cache),
        weather_client: OpenMeteoClient = Depends(get_weather_service),
        x_api_key: str = Depends(verify_api_key)
):
    """Get current weather data"""
    city_key = get_city_key(city)
    city_data = CITIES[city_key]
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Try to get from cache first, passing requested units
    cached_data = await weather_cache.get(city_key, current_date, "current", units)
    if cached_data:
        return cached_data

    # If not in cache, fetch from OpenMeteo
    weather_data = await weather_client.get_current_weather(
        lat=city_data["lat"],
        lon=city_data["lon"],
        units=units
    )

    # Add metadata
    weather_data.meta = WeatherMeta(
        cached=False,
        cache_time=None,
        provider="OpenMeteo",
        data_type="current"
    )

    # Store in cache (it will be converted to standard units)
    await weather_cache.set(city_key, current_date, "current", weather_data)

    return weather_data


@router.get("/historical/{city}")
async def get_historical_weather(
        city: str = Path(..., description="City name"),
        date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$"),
        units: Literal["standard", "metric", "imperial"] = Query("metric"),
        weather_cache: WeatherCache = Depends(get_cache),
        mongo_storage: MongoWeatherStorage = Depends(get_mongo_storage),
        weather_client: OpenMeteoClient = Depends(get_weather_service),
        x_api_key: str = Depends(verify_api_key)
):
    """Get historical weather data"""
    city_key = get_city_key(city)
    city_data = CITIES[city_key]

    # Validate date range
    try:
        requested_date = datetime.strptime(date, "%Y-%m-%d")
        min_date = datetime.strptime("2022-01-01", "%Y-%m-%d")
        max_date = datetime.now() - timedelta(days=1)

        if not (min_date <= requested_date <= max_date):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_DATE",
                    "message": "Date out of valid range",
                    "details": "Historical data available from 2022-01-01 up to yesterday"
                }
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DATE_FORMAT",
                "message": "Invalid date format",
                "details": "Date should be in YYYY-MM-DD format"
            }
        )

    # Try to get from cache first
    cached_data = await weather_cache.get(city_key, date, "historical", units)
    if cached_data:
        return cached_data

    # If not in cache, try MongoDB for tracked cities
    if await mongo_storage.is_tracked_city(city_key):
        mongo_data = await mongo_storage.get_weather(city_key, date, units=units)
        if mongo_data:
            # Update metadata to indicate MongoDB source
            mongo_data.meta = WeatherMeta(
                cached=False,
                cache_time=None,
                provider="OpenMeteo [MongoDB Storage]",
                data_type="historical"
            )
            # Convert from standard units to requested units
            if units != "standard":
                mongo_data = await weather_cache.convert_units(mongo_data, units)

            # Store in cache
            await weather_cache.set(city_key, date, "historical", mongo_data)
            return mongo_data

    # If not in MongoDB or not a tracked city, fetch from OpenMeteo
    weather_data = await weather_client.get_historical_weather(
        lat=city_data["lat"],
        lon=city_data["lon"],
        date=date,
        units=units
    )

    # Add metadata
    weather_data.meta = WeatherMeta(
        cached=False,
        cache_time=None,
        provider="OpenMeteo",
        data_type="historical"
    )

    # Store in cache
    await weather_cache.set(city_key, date, "historical", weather_data)

    # Store in MongoDB if it's a tracked city
    if await mongo_storage.is_tracked_city(city_key):
        await mongo_storage.store_weather(weather_data, city_key)

    return weather_data


@router.get("/forecast/{city}")
async def get_forecast(
        city: str = Path(..., description="City name"),
        date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$"),
        units: Literal["standard", "metric", "imperial"] = Query("metric"),
        weather_cache: WeatherCache = Depends(get_cache),
        weather_client: OpenMeteoClient = Depends(get_weather_service),
        x_api_key: str = Depends(verify_api_key)
):
    """Get weather forecast"""
    city_key = get_city_key(city)
    city_data = CITIES[city_key]

    # Validate date range
    try:
        requested_date = datetime.strptime(date, "%Y-%m-%d")
        min_date = datetime.now() + timedelta(days=1)
        max_date = datetime.now() + timedelta(days=7)  # OpenMeteo free tier limit

        if not (min_date <= requested_date <= max_date):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_DATE",
                    "message": "Date out of valid range",
                    "details": "Forecast available from tomorrow up to 7 days ahead"
                }
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DATE_FORMAT",
                "message": "Invalid date format",
                "details": "Date should be in YYYY-MM-DD format"
            }
        )

    # Try to get from cache first
    cached_data = await weather_cache.get(city_key, date, "forecast", units)
    if cached_data:
        return cached_data

    # If not in cache, fetch from OpenMeteo
    weather_data = await weather_client.get_forecast(
        lat=city_data["lat"],
        lon=city_data["lon"],
        date=date,
        units=units
    )

    # Add metadata
    weather_data.meta = WeatherMeta(
        cached=False,
        cache_time=None,
        provider="OpenMeteo",
        data_type="forecast"
    )

    # Store in cache
    await weather_cache.set(city_key, date, "forecast", weather_data)

    return weather_data


@router.get("/stats/{city}")
async def get_weather_stats(
        city: str = Path(..., description="City name"),
        start_date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$"),
        end_date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$"),
        units: Literal["standard", "metric", "imperial"] = Query("metric"),
        weather_cache: WeatherCache = Depends(get_cache),
        weather_client: OpenMeteoClient = Depends(get_weather_service),
        x_api_key: str = Depends(verify_api_key)
):
    """Get weather statistics"""
    city_key = get_city_key(city)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        # Validate date range
        min_date = datetime.strptime("2022-01-01", "%Y-%m-%d")  # OpenMeteo historical limit
        max_date = datetime.now() - timedelta(days=1)

        if start > end:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_DATE_RANGE",
                    "message": "Start date must be before end date",
                    "details": None
                }
            )

        if not (min_date <= start <= max_date) or not (min_date <= end <= max_date):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_DATE_RANGE",
                    "message": "Dates out of valid range",
                    "details": "Statistics available from 2022-01-01 up to yesterday"
                }
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DATE_FORMAT",
                "message": "Invalid date format",
                "details": "Dates should be in YYYY-MM-DD format"
            }
        )

    # Try to get from cache first
    cache_key = f"{start_date}_{end_date}"
    cached_data = await weather_cache.get(city_key, cache_key, "stats", units)
    if cached_data:
        return cached_data

    # If not in cache, calculate statistics
    weather_data = await weather_client.get_weather_stats(
        lat=CITIES[city_key]["lat"],
        lon=CITIES[city_key]["lon"],
        start_date=start_date,
        end_date=end_date,
        units=units
    )

    # Add metadata
    weather_data.meta = WeatherMeta(
        cached=False,
        cache_time=None,
        provider="OpenMeteo",
        data_type="stats"
    )

    # Store in cache
    await weather_cache.set(city_key, cache_key, "stats", weather_data)

    return weather_data