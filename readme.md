# Weather API

A FastAPI-based weather API that provides current, historical, and forecast weather data with caching and historical data storage.

## Quick Start

1. Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    image: mocwieja/weather-api:latest
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - MONGO_URL=mongodb://admin:password@mongodb:27017
      - MONGO_DB=weather_history
      - MONGO_COLLECTION=historical_weather
      - OPENMETEO_FORECAST_URL=https://api.open-meteo.com/v1/forecast
      - OPENMETEO_HISTORICAL_URL=https://historical-forecast-api.open-meteo.com/v1/forecast
    depends_on:
      - redis
      - mongodb

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --save 60 1 --loglevel warning

  mongodb:
    image: mongo:6
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password
    volumes:
      - mongodb_data:/data/db

volumes:
  redis_data:
  mongodb_data:
```

2. Run the application:
```bash
docker-compose up
```

The API will be available at http://localhost:8000

## API Documentation

Once running, you can access:
- OpenAPI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Populating Historical Data

To populate historical weather data for tracked cities (London, Paris), you'll need to run the population script. Here's how to do it:

1. Clone the repository or create a new Python script `populate_data.py`:

```python
import asyncio
from datetime import datetime, timedelta
from app.services.openmeteo_client import OpenMeteoClient
from app.services.mongo_storage import MongoWeatherStorage

async def populate_historical_data():
    """Populate MongoDB with historical weather data for tracked cities"""
    # Initialize services
    weather_client = OpenMeteoClient()
    mongo_storage = MongoWeatherStorage(
        mongo_url="mongodb://admin:password@localhost:27017",
        database="weather_history",
        collection="historical_weather"
    )

    # Setup MongoDB indexes
    await mongo_storage.setup()

    # Calculate date range (e.g., last year)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)  # Adjust number of days as needed

    # Tracked cities
    tracked_cities = ["london,gb", "paris,fr"]

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
                    units="standard"
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
    
CITIES = {
    "london,gb": {
        "name": "London",
        "country": "GB",
        "state": "England",
        "lat": 51.5074,
        "lon": -0.1278,
        "tz": "+00:00"
    },
    "paris,fr": {
        "name": "Paris",
        "country": "FR",
        "state": "Île-de-France",
        "lat": 48.8566,
        "lon": 2.3522,
        "tz": "+01:00"
    },
}

if __name__ == "__main__":
    asyncio.run(populate_historical_data())
```

2. Install required packages:
```bash
pip install motor httpx
```

3. Run the script:
```bash
python populate_data.py
```

Note: Make sure to run the script after the Docker containers are up and running since it needs to connect to MongoDB.

## Environment Variables

You can customize the application behavior using environment variables in docker-compose.yml:

- `REDIS_HOST`: Redis host (default: redis)
- `MONGO_URL`: MongoDB connection URL
- `MONGO_DB`: MongoDB database name (default: weather_history)
- `MONGO_COLLECTION`: MongoDB collection name (default: historical_weather)
- `OPENMETEO_FORECAST_URL`: OpenMeteo forecast API URL
- `OPENMETEO_HISTORICAL_URL`: OpenMeteo historical API URL

## Data Storage

- Redis is used for caching weather data
- MongoDB stores historical weather data for tracked cities
- Both Redis and MongoDB data persist through Docker volumes

## Notes

- The application tracks weather data for London and Paris by default
- Historical data is stored in standard units (Kelvin for temperature, m/s for wind speed)
- The API supports metric, imperial, and standard unit systems
- Redis cache has different TTL for different types of data (current, forecast, historical)
