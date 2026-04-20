import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.restaurant import (
    ManualRestaurantCreate,
    RestaurantListResponse,
    RestaurantResponse,
    RestaurantUpdate,
)
from app.services import restaurant_repo
from app.services.google_maps import search_nearby

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=RestaurantListResponse)
def list_restaurants(
    source: str | None = Query(None, description="Filter by source: google_maps or manual"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    restaurants, total = restaurant_repo.list_all(db, source=source, page=page, page_size=page_size)
    return RestaurantListResponse(
        restaurants=[RestaurantResponse.model_validate(r) for r in restaurants],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{restaurant_id}", response_model=RestaurantResponse)
def get_restaurant(restaurant_id: uuid.UUID, db: Session = Depends(get_db)):
    restaurant = restaurant_repo.get_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return RestaurantResponse.model_validate(restaurant)


@router.post("/manual", response_model=RestaurantResponse, status_code=201)
def create_manual_restaurant(
    data: ManualRestaurantCreate,
    user_id: uuid.UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    restaurant = restaurant_repo.create_manual(db, data, user_id)
    return RestaurantResponse.model_validate(restaurant)


@router.put("/{restaurant_id}", response_model=RestaurantResponse)
def update_restaurant(
    restaurant_id: uuid.UUID,
    data: RestaurantUpdate,
    user_id: uuid.UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    restaurant = restaurant_repo.get_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if restaurant.source != "manual":
        raise HTTPException(status_code=403, detail="Cannot edit Google Maps restaurants")
    if restaurant.added_by != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can edit this restaurant")

    updated = restaurant_repo.update(db, restaurant_id, data)
    return RestaurantResponse.model_validate(updated)


@router.delete("/{restaurant_id}", status_code=204)
def delete_restaurant(
    restaurant_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    restaurant = restaurant_repo.get_by_id(db, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if restaurant.source != "manual":
        raise HTTPException(status_code=403, detail="Cannot delete Google Maps restaurants")
    if restaurant.added_by != user_id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this restaurant")

    restaurant_repo.delete(db, restaurant_id)


@router.post("/sync-from-maps", response_model=dict)
async def sync_from_maps(
    lat: float = Query(...),
    lng: float = Query(...),
    radius: int = Query(1000, ge=100, le=5000),
    db: Session = Depends(get_db),
):
    result = await search_nearby(lat=lat, lng=lng, radius=radius)
    if result.status != "OK":
        raise HTTPException(status_code=502, detail=f"Google Maps API error: {result.status}")

    upserted = 0
    for r in result.restaurants:
        restaurant_repo.upsert_from_maps(db, r)
        upserted += 1

    return {"synced": upserted, "status": result.status}
