from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router
from app.services.factory import get_weather_client, get_weather_cache

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("shutdown")
async def shutdown_event():
    # Clean up resources
    client = get_weather_client()
    await client.close()

    cache = get_weather_cache()
    await cache.close()