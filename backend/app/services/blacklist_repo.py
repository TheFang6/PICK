import uuid
from datetime import datetime, time, timezone

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.models.user_blacklist import BlacklistMode, UserBlacklist


def add(
    db: Session,
    user_id: uuid.UUID,
    restaurant_id: uuid.UUID,
    mode: str = BlacklistMode.PERMANENT,
) -> UserBlacklist:
    expires_at = None
    if mode == BlacklistMode.TODAY:
        today = datetime.now(timezone.utc).date()
        expires_at = datetime.combine(today, time(23, 59, 59), tzinfo=timezone.utc)

    existing = db.execute(
        select(UserBlacklist).where(
            UserBlacklist.user_id == user_id,
            UserBlacklist.restaurant_id == restaurant_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.mode = mode
        existing.expires_at = expires_at
        db.commit()
        db.refresh(existing)
        return existing

    entry = UserBlacklist(
        user_id=user_id,
        restaurant_id=restaurant_id,
        mode=mode,
        expires_at=expires_at,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def remove(db: Session, user_id: uuid.UUID, blacklist_id: uuid.UUID) -> bool:
    entry = db.execute(
        select(UserBlacklist).where(
            UserBlacklist.id == blacklist_id,
            UserBlacklist.user_id == user_id,
        )
    ).scalar_one_or_none()

    if not entry:
        return False

    db.delete(entry)
    db.commit()
    return True


def list_by_user(db: Session, user_id: uuid.UUID) -> list[UserBlacklist]:
    now = datetime.now(timezone.utc)
    stmt = select(UserBlacklist).where(
        UserBlacklist.user_id == user_id,
        or_(
            UserBlacklist.expires_at.is_(None),
            UserBlacklist.expires_at > now,
        ),
    ).order_by(UserBlacklist.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_blacklisted_restaurant_ids(
    db: Session,
    user_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    if not user_ids:
        return set()

    now = datetime.now(timezone.utc)
    stmt = select(UserBlacklist.restaurant_id).where(
        UserBlacklist.user_id.in_(user_ids),
        or_(
            UserBlacklist.expires_at.is_(None),
            UserBlacklist.expires_at > now,
        ),
    )
    rows = db.execute(stmt).scalars().all()
    return set(rows)


def cleanup_expired(db: Session) -> int:
    now = datetime.now(timezone.utc)
    stmt = delete(UserBlacklist).where(
        UserBlacklist.expires_at.isnot(None),
        UserBlacklist.expires_at < now,
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount
