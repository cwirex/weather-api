from datetime import datetime
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from app.models import WeatherResponse, HistoricalWeatherRecord, MongoDBStats


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

    async def get_stats(self) -> MongoDBStats:
        """Get MongoDB storage statistics"""
        try:
            # Get collection stats
            stats = await self.db.command("collStats", self.collection.name)

            # Get record counts by city
            pipeline = [
                {"$group": {"_id": "$city_key", "count": {"$sum": 1}}}
            ]
            city_counts = {doc["_id"]: doc["count"]
                           async for doc in self.collection.aggregate(pipeline)}

            # Get date range info for each city
            date_coverage = {}
            for city in self.tracked_cities:
                first_record = await self.collection.find_one(
                    {"city_key": city},
                    sort=[("date", 1)]
                )
                last_record = await self.collection.find_one(
                    {"city_key": city},
                    sort=[("date", -1)]
                )

                if first_record and last_record:
                    start_date = datetime.strptime(first_record["date"], "%Y-%m-%d")
                    end_date = datetime.strptime(last_record["date"], "%Y-%m-%d")
                    total_days = (end_date - start_date).days + 1

                    # Count actual records
                    actual_records = await self.collection.count_documents({"city_key": city})
                    missing_days = total_days - actual_records

                    date_coverage[city] = {
                        "start_date": first_record["date"],
                        "end_date": last_record["date"],
                        "total_days": total_days,
                        "missing_days": missing_days,
                        "coverage_percentage": round((actual_records / total_days) * 100, 2)
                    }

            # Get earliest and latest records overall
            earliest = await self.collection.find_one({}, sort=[("date", 1)])
            latest = await self.collection.find_one({}, sort=[("date", -1)])

            return MongoDBStats(
                status="operational",
                total_records=await self.collection.count_documents({}),
                earliest_record=earliest["date"] if earliest else None,
                latest_record=latest["date"] if latest else None,
                storage_size=f"{stats['size'] / 1024 / 1024:.1f} MB",
                records_by_city=city_counts,
                cities_tracked=list(self.tracked_cities),
                date_coverage=date_coverage
            )
        except Exception as e:
            return MongoDBStats(
                status="error",
                total_records=0,
                earliest_record=None,
                latest_record=None,
                storage_size="0 MB",
                records_by_city={},
                cities_tracked=list(self.tracked_cities),
                date_coverage={},
                error=str(e)
            )

    async def is_tracked_city(self, city_key: str) -> bool:
        """Check if city is being tracked for historical data"""
        return city_key in self.tracked_cities