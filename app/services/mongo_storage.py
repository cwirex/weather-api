from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from app.models import WeatherResponse, HistoricalWeatherRecord


class MongoWeatherStorage:
    def __init__(
            self,
            mongo_url: str,
            database: str = "weather_history",
            collection: str = "historical_weather"
    ):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[database]
        self.collection = self.db[collection]
        self.tracked_cities = {"london,gb", "paris,fr", "lublin,pl"}  # Cities to track

    async def setup(self):
        """Setup indexes for better query performance"""
        await self.collection.create_index([("city_key", 1), ("date", 1)], unique=True)
        await self.collection.create_index("last_updated")

    async def get_weather(self, city_key: str, date: str, units: str = "standard") -> Optional[WeatherResponse]:
        """Get historical weather data for a specific city and date"""
        if city_key not in self.tracked_cities:
            return None

        record = await self.collection.find_one({"city_key": city_key, "date": date})
        if not record:
            return None

        from app.core.cities_data import CITIES
        city_data = CITIES[city_key]

        # Convert MongoDB record to WeatherResponse
        return WeatherResponse(
            lat=city_data["lat"],
            lon=city_data["lon"],
            date=record["date"],
            units="standard",  # We'll store in standard units
            cloud_cover={"afternoon": record["cloud_cover"]},
            humidity={"afternoon": record["humidity"]},
            precipitation={"total": record["precipitation_total"]},
            temperature={
                "min": record["temperature_min"],
                "max": record["temperature_max"],
                "afternoon": record["temperature_afternoon"],
                "night": record["temperature_night"],
                "evening": record["temperature_evening"],
                "morning": record["temperature_morning"]
            },
            pressure={"afternoon": record["pressure"]},
            wind={
                "max": {
                    "speed": record["wind_speed"],
                    "direction": record["wind_direction"]
                }
            }
        )

    async def store_weather(self, weather: WeatherResponse, city_key: str):
        """Store historical weather data"""
        if city_key not in self.tracked_cities:
            return

        record = HistoricalWeatherRecord(
            city_key=city_key,
            date=weather.date,
            temperature_min=weather.temperature.min,
            temperature_max=weather.temperature.max,
            temperature_afternoon=weather.temperature.afternoon,
            temperature_night=weather.temperature.night,
            temperature_evening=weather.temperature.evening,
            temperature_morning=weather.temperature.morning,
            precipitation_total=weather.precipitation.total,
            wind_speed=weather.wind.max.speed,
            wind_direction=weather.wind.max.direction,
            cloud_cover=weather.cloud_cover.afternoon,
            humidity=weather.humidity.afternoon,
            pressure=weather.pressure.afternoon
        )

        # Upsert the record
        await self.collection.update_one(
            {"city_key": city_key, "date": weather.date},
            {"$set": record.model_dump()},
            upsert=True
        )

    async def is_tracked_city(self, city_key: str) -> bool:
        """Check if city is being tracked for historical data"""
        return city_key in self.tracked_cities