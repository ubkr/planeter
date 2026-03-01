"""Geocoding proxy endpoints"""
import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/geocode", tags=["geocode"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    """Proxy reverse geocoding to Nominatim (avoids browser CORS restrictions)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={"lat": lat, "lon": lon, "format": "json", "accept-language": "en"},
                headers={"User-Agent": "PlanetVisibilityApp/1.0"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Geocoding upstream error")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {str(e)}")
