from fastapi import APIRouter, Query, Depends, HTTPException
from app.core.sample_data import CITIES
from app.api.dependencies import verify_api_key

router = APIRouter()


@router.get("/search")
async def search_cities(
        q: str = Query(..., description="City name or city,country code"),
        limit: int = Query(1, ge=1, le=5),
        api_key: str = Depends(verify_api_key)
):
    """Search for cities and get their coordinates"""
    q = q.lower()
    results = []

    # If country code is provided (e.g., "london,gb")
    if "," in q:
        if q in CITIES:
            city_data = CITIES[q].copy()
            city_data["id"] = q
            results.append(city_data)
    else:
        # Search by city name
        for city_id, city_data in CITIES.items():
            if q in city_data["name"].lower():
                city_info = city_data.copy()
                city_info["id"] = city_id
                results.append(city_info)

    if not results:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CITY_NOT_FOUND",
                "message": f"No cities found matching '{q}'",
                "details": "Try using city,country format (e.g., london,gb) for more precise results"
            }
        )

    # Sort by name and limit results
    results.sort(key=lambda x: x["name"])
    return {"results": results[:limit]}


@router.get("/list")
async def list_cities(
        api_key: str = Depends(verify_api_key)
):
    """Get list of all available cities"""
    cities = []
    for city_id, city_data in CITIES.items():
        city_info = city_data.copy()
        city_info["id"] = city_id
        cities.append(city_info)

    cities.sort(key=lambda x: f"{x['name']}, {x['country']}")
    return {"cities": cities}