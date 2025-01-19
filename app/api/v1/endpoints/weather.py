from fastapi import APIRouter, Query, Path, HTTPException, Header
from datetime import datetime, timedelta
from typing import Literal
from app.core.sample_data import generate_sample_weather, get_sample_stats
from app.core.cities_data import CITIES

router = APIRouter()


def get_city_key(city: str) -> str:
    """Convert city name to city key and validate it exists"""
    # First try exact match
    city_key = city.lower()
    if city_key in CITIES:
        return city_key

    # Try finding by city name
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


@router.get("/historical/{city}")
async def get_historical_weather(
        city: str = Path(..., description="City name"),
        date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format"),
        units: Literal["standard", "metric", "imperial"] = Query("metric", description="Units of measurement"),
        x_api_key: str = Header(..., alias="X-API-Key")
):
    """Get historical weather data for a specific date"""
    city_key = get_city_key(city)

    try:
        requested_date = datetime.strptime(date, "%Y-%m-%d")
        min_date = datetime.strptime("1979-01-02", "%Y-%m-%d")
        max_date = datetime.now() - timedelta(days=1)

        if not (min_date <= requested_date <= max_date):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_DATE",
                    "message": "Date out of valid range",
                    "details": "Historical data available from 1979-01-02 up to yesterday"
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

    return generate_sample_weather(city_key, date, units)


@router.get("/forecast/{city}")
async def get_forecast(
        city: str = Path(..., description="City name"),
        date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format"),
        units: Literal["standard", "metric", "imperial"] = Query("metric", description="Units of measurement"),
        x_api_key: str = Header(..., alias="X-API-Key")
):
    """Get weather forecast for a specific date"""
    city_key = get_city_key(city)

    try:
        requested_date = datetime.strptime(date, "%Y-%m-%d")
        min_date = datetime.now() + timedelta(days=1)
        max_date = datetime.now() + timedelta(days=548)  # ~1.5 years

        if not (min_date <= requested_date <= max_date):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_DATE",
                    "message": "Date out of valid range",
                    "details": "Forecast available from tomorrow up to 1.5 years ahead"
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

    return generate_sample_weather(city_key, date, units)


@router.get("/stats/{city}")
async def get_weather_stats(
        city: str = Path(..., description="City name"),
        start_date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$"),
        end_date: str = Query(..., regex="^\d{4}-\d{2}-\d{2}$"),
        units: Literal["standard", "metric", "imperial"] = Query("metric", description="Units of measurement"),
        x_api_key: str = Header(..., alias="X-API-Key")
):
    """Get weather statistics for the specified city and date range"""
    city_key = get_city_key(city)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_DATE_RANGE",
                    "message": "Start date must be before end date",
                    "details": None
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

    return get_sample_stats(city_key, start_date, end_date, units)