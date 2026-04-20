from fastapi import APIRouter, Query

from app.schemas.google_maps import NearbySearchResponse
from app.services.google_maps import search_nearby

router = APIRouter(prefix="/dev", tags=["dev"])


@router.get("/nearby", response_model=NearbySearchResponse)
async def nearby_restaurants(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(1000, ge=100, le=5000, description="Search radius in meters"),
):
    return await search_nearby(lat=lat, lng=lng, radius=radius)
