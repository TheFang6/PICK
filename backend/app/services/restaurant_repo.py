import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.restaurant import Restaurant, RestaurantSource
from app.schemas.google_maps import Restaurant as MapsRestaurant
from app.schemas.restaurant import ManualRestaurantCreate, RestaurantUpdate


def upsert_from_maps(db: Session, data: MapsRestaurant) -> Restaurant:
    stmt = insert(Restaurant).values(
        place_id=data.place_id,
        name=data.name,
        source=RestaurantSource.GOOGLE_MAPS,
        lat=data.location.lat,
        lng=data.location.lng,
        vicinity=data.vicinity,
        rating=data.rating,
        user_ratings_total=data.user_ratings_total,
        price_level=data.price_level,
        types=data.types,
        photo_reference=data.photo_reference,
        last_fetched_at=datetime.now(timezone.utc),
    ).on_conflict_do_update(
        index_elements=["place_id"],
        set_={
            "name": data.name,
            "lat": data.location.lat,
            "lng": data.location.lng,
            "vicinity": data.vicinity,
            "rating": data.rating,
            "user_ratings_total": data.user_ratings_total,
            "price_level": data.price_level,
            "types": data.types,
            "photo_reference": data.photo_reference,
            "last_fetched_at": datetime.now(timezone.utc),
        },
    ).returning(Restaurant)

    result = db.execute(stmt)
    db.commit()
    return result.scalar_one()


def create_manual(db: Session, data: ManualRestaurantCreate, user_id: uuid.UUID) -> Restaurant:
    restaurant = Restaurant(
        name=data.name,
        source=RestaurantSource.MANUAL,
        lat=data.lat,
        lng=data.lng,
        vicinity=data.vicinity,
        rating=data.rating,
        price_level=data.price_level,
        types=data.types,
        photo_reference=data.photo_reference,
        closed_weekdays=data.closed_weekdays,
        closed_monthly_ranges=data.closed_monthly_ranges,
        added_by=user_id,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


def search(db: Session, query: str, limit: int = 20) -> list[Restaurant]:
    stmt = (
        select(Restaurant)
        .where(Restaurant.name.ilike(f"%{query}%"))
        .order_by(Restaurant.name)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_by_id(db: Session, restaurant_id: uuid.UUID) -> Restaurant | None:
    return db.get(Restaurant, restaurant_id)


def list_all(
    db: Session,
    source: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Restaurant], int]:
    query = select(Restaurant)
    count_query = select(func.count()).select_from(Restaurant)

    if source:
        query = query.where(Restaurant.source == source)
        count_query = count_query.where(Restaurant.source == source)

    total = db.execute(count_query).scalar()
    restaurants = db.execute(
        query.order_by(Restaurant.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    return list(restaurants), total


def update(db: Session, restaurant_id: uuid.UUID, data: RestaurantUpdate) -> Restaurant | None:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(restaurant, key, value)

    db.commit()
    db.refresh(restaurant)
    return restaurant


def delete(db: Session, restaurant_id: uuid.UUID) -> bool:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        return False
    db.delete(restaurant)
    db.commit()
    return True
