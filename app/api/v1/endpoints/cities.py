from fastapi import APIRouter, Query, Depends, HTTPException
from app.core.cities_data import CITIES
from app.api.dependencies import verify_api_key

router = APIRouter()


@router.get("/search")
async def search_cities(
        q: str = Query(..., description="City name, city,country code, or country code"),
        limit: int = Query(1, ge=1, le=10),
        api_key: str = Depends(verify_api_key)
):
    """Search for cities and get their coordinates.

    You can search by:
    - City name (e.g., "london")
    - City and country code (e.g., "london,gb")
    - Country code only (e.g., "pl")
    """
    q = q.lower().strip()
    results = []

    # If query is exactly 2 characters, treat it as a country code
    if len(q) == 2:
        # Search for all cities in that country
        for city_id, city_data in CITIES.items():
            if city_data["country"].lower() == q:
                city_info = city_data.copy()
                city_info["id"] = city_id
                results.append(city_info)
    # If query contains comma, treat as city,country format
    elif "," in q:
        if q in CITIES:
            city_data = CITIES[q].copy()
            city_data["id"] = q
            results.append(city_data)
    # Otherwise, search by city name
    else:
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
                "details": "Try using: city name (e.g., 'london'), city,country (e.g., 'london,gb'), or country code (e.g., 'pl')"
            }
        )

    # Sort results by name
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