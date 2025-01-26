from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.api.v1.router import api_router
from app.services.factory import get_weather_client, get_weather_cache

description = """
# Weather API

Welcome to the Weather API! This service provides comprehensive weather data including current conditions, historical records, and forecasts for cities worldwide.

To get started, browse the available endpoints below and make sure to include your API key in the `X-API-Key` header.

---

## Detailed Information

<details>
<summary>Click to expand</summary>

### Key Features

* 🌡️ **Current Weather**: Get real-time weather conditions for any supported city
* 📊 **Historical Data**: Access weather history with data stored in MongoDB for tracked cities
* 🔮 **Weather Forecast**: Get weather predictions for up to 7 days ahead
* 📈 **Weather Statistics**: Calculate weather stats for any date range
* 🚀 **Fast Response**: Redis caching for optimal performance
* 🌍 **Multiple Units**: Support for metric, imperial, and standard units

### Data Sources

* Current and forecast data: OpenMeteo API
* Historical data: Stored in MongoDB for tracked cities
* Cache: Redis for improved performance

### Units Available

* **standard**: Temperature in Kelvin, wind speed in m/s
* **metric**: Temperature in Celsius, wind speed in m/s
* **imperial**: Temperature in Fahrenheit, wind speed in mph

### Rate Limits

The API has a rate limit of {settings.RATE_LIMIT_PER_MINUTE} requests per minute per API key.

For more information, contact the API administrator.

</details>
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=description,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0"
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root path to API documentation"""
    return RedirectResponse(url="/docs")

@app.on_event("shutdown")
async def shutdown_event():
    # Clean up resources
    client = get_weather_client()
    await client.close()

    cache = get_weather_cache()
    await cache.close()