import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PollStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PollSession(Base):
    __tablename__ = "poll_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidates: Mapped[list] = mapped_column(JSON, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PollStatus] = mapped_column(Enum(PollStatus), nullable=False, default=PollStatus.ACTIVE)
    winner_restaurant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PollVote(Base):
    __tablename__ = "poll_votes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poll_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("poll_sessions.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("restaurants.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("poll_session_id", "user_id", name="uq_poll_vote_session_user"),
    )
