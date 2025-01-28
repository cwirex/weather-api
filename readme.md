# Weather API

A FastAPI-based weather API that provides current, historical, and forecast weather data with caching and historical data storage.

<p align="center">
  <img src="https://github.com/user-attachments/assets/b190b8ea-5270-4403-9322-abecae89e568" alt="API Documentation" width="600"/>
  <br>
  <em>Interactive Swagger UI documentation showing all available endpoints</em>
</p>

## Features

- Current weather conditions for any supported city
- Historical weather data with MongoDB storage for tracked cities
- Weather forecasts up to 7 days ahead
- Weather statistics for custom date ranges
- Redis caching for optimal performance
- Support for metric, imperial, and standard units
- Admin endpoints for data population and cache management

### Examples
<details>
<summary>API Call Example: /weather/stats</summary>
<p align="center">
  <img src="https://github.com/user-attachments/assets/581caf8e-0875-4a4f-954c-732c9f10d305" alt="API Call Example" width="800"/>
  <br>
  <em>Example of a successful API call returning weather data</em>
</p>
</details>

<details>
<summary>API Call Example: /cities/search</summary>
<p align="center">
  <img src="https://github.com/user-attachments/assets/b92fac9e-1335-4497-bc6f-81deb5ca8848" alt="API Call Example" width="800"/>
  <br>
  <em>Example of a successful API call returning list of cities</em>
</p>
</details>

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

<p align="center">
  <img src="https://github.com/user-attachments/assets/c426fdca-2f1f-4895-98bf-8ca0100f72c6" alt="Docker Compose Stack" width="600"/>
  <br>
  <em>Weather API stack: FastAPI service, Redis cache, and MongoDB database running in Docker containers</em>
</p>

The API will be available at http://localhost:8000 and will redirect you to the API documentation.

## API Documentation

Once running, you can access:
- OpenAPI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Environment Variables

You can customize the application behavior using environment variables in docker-compose.yml:

- `REDIS_HOST`: Redis host (default: redis)
- `MONGO_URL`: MongoDB connection URL
- `MONGO_DB`: MongoDB database name (default: weather_history)
- `MONGO_COLLECTION`: MongoDB collection name (default: historical_weather)
- `OPENMETEO_FORECAST_URL`: OpenMeteo forecast API URL
- `OPENMETEO_HISTORICAL_URL`: OpenMeteo historical API URL
- `RATE_LIMIT_PER_MINUTE`: API rate limit per minute (default: 60)
- `ADMIN_API_KEY`: Admin API key for protected endpoints (default: admin-sk)

## Data Storage

- Redis is used for caching weather data
- MongoDB stores historical weather data for tracked cities
- Both Redis and MongoDB data persist through Docker volumes

## Historical Data Population

Historical data can be populated using the admin API endpoint:

```bash
# Populate 30 days of historical data for London
curl -X POST "http://localhost:8000/api/v1/cache/populate/london,gb?days_back=30&delay=1.0" \
     -H "X-API-Key: admin-sk"
```

## Cache Management

Clear cache and historical data for a city:

```bash
# Clear both Redis cache and MongoDB data
curl -X DELETE "http://localhost:8000/api/v1/cache/london,gb" \
     -H "X-API-Key: admin-sk"

# Clear only Redis cache (keep historical data)
curl -X DELETE "http://localhost:8000/api/v1/cache/london,gb?clear_historical=false" \
     -H "X-API-Key: admin-sk"
```

## Units

The API supports different unit systems:
- `standard`: Temperature in Kelvin, wind speed in m/s
- `metric`: Temperature in Celsius, wind speed in m/s
- `imperial`: Temperature in Fahrenheit, wind speed in mph

## Notes

- The application tracks weather data for several major cities by default
- Historical data is stored in standard units (Kelvin for temperature, m/s for wind speed)
- Redis cache has different TTL for different types of data
- Rate limiting is applied per API key
