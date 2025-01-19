from fastapi import HTTPException, Header, Depends
from app.core.config import settings

async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key")
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "API key is required"}
        )
    return x_api_key

async def verify_admin_access(
    x_api_key: str = Depends(verify_api_key)
) -> str:
    # In production, you would verify against a list of admin API keys
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail={"error": "Admin access required"}
        )
    return x_api_key