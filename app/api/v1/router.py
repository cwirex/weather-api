from fastapi import APIRouter, Depends
from app.api.v1.endpoints import weather, cities, cache
from app.api.dependencies import verify_api_key

api_router = APIRouter()

@api_router.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}

# Include all routers
api_router.include_router(
    weather.router,
    prefix="/weather",
    tags=["weather"]
)

api_router.include_router(
    cities.router,
    prefix="/cities",
    tags=["cities"]
)

api_router.include_router(
    cache.router,
    prefix="/cache",
    tags=["cache"]
)