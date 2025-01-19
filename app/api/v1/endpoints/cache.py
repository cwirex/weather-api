from fastapi import APIRouter, Path, Depends
from datetime import datetime
from app.api.dependencies import verify_admin_access

router = APIRouter()

# Sample cache statistics (in production, this would come from Redis)
SAMPLE_CACHE_STATS = {
    "status": "operational",
    "total_keys": 150,
    "memory_usage": "24.5 MB",
    "hit_rate": "85.2%",
    "miss_rate": "14.8%",
    "evicted_keys": 12,
    "expired_keys": 45,
    "uptime": "5d 12h 34m",
    "connected_clients": 3,
    "last_save": datetime.utcnow().isoformat() + "Z",
    "cache_type_distribution": {
        "current_weather": 45,
        "historical": 65,
        "forecast": 40
    }
}

@router.get("/stats")
async def get_cache_stats(
    admin_key: str = Depends(verify_admin_access)
):
    """Get cache statistics (admin only)"""
    return SAMPLE_CACHE_STATS

@router.delete("/{city}")
async def clear_city_cache(
    city: str = Path(..., description="City name"),
    admin_key: str = Depends(verify_admin_access)
):
    """Clear cache for specific city (admin only)"""
    # In production, this would actually clear the cache
    return {
        "status": "success",
        "message": f"Cache cleared for city: {city}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "details": {
            "keys_removed": 12,
            "memory_freed": "1.2 MB"
        }
    }