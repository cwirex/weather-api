import asyncio
from datetime import datetime, timedelta
from app.core.config import settings
from app.services.openmeteo_client import OpenMeteoClient
from app.services.mongo_storage import MongoWeatherStorage
from app.core.cities_data import CITIES

async def populate_historical_data():
    """Populate MongoDB with historical weather data for tracked cities"""
    # Initialize services
    weather_client = OpenMeteoClient()
    mongo_storage = MongoWeatherStorage(
        mongo_url=settings.MONGO_URL,
        database=settings.MONGO_DB,
        collection=settings.MONGO_COLLECTION
    )

    # Setup MongoDB indexes
    await mongo_storage.setup()

    # Calculate date range (e.g., last 2 years)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=1*2) # TODO: update

    # Tracked cities
    tracked_cities = ["london,gb", "paris,fr", "lublin,pl"]

    for city_key in tracked_cities:
        print(f"Processing {city_key}...")
        city_data = CITIES[city_key]

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            try:
                # Fetch data from OpenMeteo
                weather_data = await weather_client.get_historical_weather(
                    lat=city_data["lat"],
                    lon=city_data["lon"],
                    date=date_str,
                    units="standard"  # Always store in standard units
                )

                # Store in MongoDB
                await mongo_storage.store_weather(weather_data, city_key)
                print(f"Stored data for {city_key} on {date_str}")

                # Add delay to respect API rate limits
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Error processing {city_key} for {date_str}: {str(e)}")

            current_date += timedelta(days=1)

    await weather_client.close()

if __name__ == "__main__":
    asyncio.run(populate_historical_data())