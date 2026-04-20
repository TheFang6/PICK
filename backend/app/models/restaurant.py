import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RestaurantSource(str, enum.Enum):
    GOOGLE_MAPS = "google_maps"
    MANUAL = "manual"


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    place_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default=RestaurantSource.GOOGLE_MAPS)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    vicinity: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    types: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    photo_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_weekdays: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    closed_monthly_ranges: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    added_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_restaurants_source", "source"),
        Index("ix_restaurants_place_id", "place_id"),
        Index("ix_restaurants_added_by", "added_by"),
    )
