from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import List, Dict, Any
import asyncio
from app.services.openmeteo_client import OpenMeteoClient
from app.services.mongo_storage import MongoWeatherStorage
from app.core.cities_data import CITIES


class PopulationService:
    def __init__(self, weather_client: OpenMeteoClient, mongo_storage: MongoWeatherStorage):
        self.weather_client = weather_client
        self.mongo_storage = mongo_storage

    async def populate_historical_data(
            self,
            city_key: str,
            days_back: int,
            delay_between_requests: float = 1.0
    ) -> Dict[str, Any]:
        """
        Populate MongoDB with historical weather data for a specific city

        Args:
            city_key: City identifier (e.g., 'london,gb')
            days_back: Number of days to go back
            delay_between_requests: Delay between API requests in seconds
        """
        if city_key not in CITIES:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "CITY_NOT_FOUND",
                    "message": f"City '{city_key}' not found",
                    "details": "Check available cities using the /api/v1/cities/list endpoint"
                }
            )

        if not await self.mongo_storage.is_tracked_city(city_key):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "CITY_NOT_TRACKED",
                    "message": f"City '{city_key}' is not configured for historical tracking",
                    "details": "Only specific cities are configured for historical data storage"
                }
            )

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        city_data = CITIES[city_key]
        processed_dates = []
        failed_dates = []

        # Setup MongoDB indexes if they don't exist
        await self.mongo_storage.setup()

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            try:
                # Check if data already exists
                existing_data = await self.mongo_storage.get_weather(city_key, date_str)
                if existing_data:
                    processed_dates.append({
                        "date": date_str,
                        "status": "skipped",
                        "reason": "data_exists"
                    })
                else:
                    # Fetch data from OpenMeteo
                    weather_data = await self.weather_client.get_historical_weather(
                        lat=city_data["lat"],
                        lon=city_data["lon"],
                        date=date_str,
                        units="standard"  # Always store in standard units
                    )

                    # Store in MongoDB
                    await self.mongo_storage.store_weather(weather_data, city_key)
                    processed_dates.append({
                        "date": date_str,
                        "status": "success"
                    })

                    # Add delay to respect API rate limits
                    await asyncio.sleep(delay_between_requests)

            except Exception as e:
                failed_dates.append({
                    "date": date_str,
                    "error": str(e)
                })

            current_date += timedelta(days=1)

        return {
            "city": city_key,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days_requested": days_back,
            "days_processed": len(processed_dates),
            "days_failed": len(failed_dates),
            "processed_dates": processed_dates,
            "failed_dates": failed_dates
        }