import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.models.lunch_history import LunchHistory


def log_lunch(
    db: Session,
    restaurant_id: uuid.UUID,
    attendees: list[uuid.UUID],
    lunch_date: date | None = None,
) -> LunchHistory:
    if lunch_date is None:
        lunch_date = datetime.now(timezone.utc).date()

    entry = LunchHistory(
        restaurant_id=restaurant_id,
        date=lunch_date,
        attendees=[str(uid) for uid in attendees],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_recent_restaurant_ids(
    db: Session,
    user_ids: list[uuid.UUID],
    days: int = 7,
) -> set[uuid.UUID]:
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    stmt = select(LunchHistory).where(LunchHistory.date >= cutoff)
    entries = db.execute(stmt).scalars().all()

    user_id_strs = {str(uid) for uid in user_ids}
    result = set()
    for entry in entries:
        entry_attendees = set(entry.attendees or [])
        if entry_attendees & user_id_strs:
            result.add(entry.restaurant_id)

    return result


def get_user_history(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 30,
    offset: int = 0,
    month: str | None = None,
) -> list[LunchHistory]:
    stmt = select(LunchHistory).order_by(LunchHistory.date.desc())
    if month:
        year, mon = month.split("-")
        stmt = stmt.where(
            extract("year", LunchHistory.date) == int(year),
            extract("month", LunchHistory.date) == int(mon),
        )
    entries = db.execute(stmt).scalars().all()

    user_id_str = str(user_id)
    filtered = [e for e in entries if user_id_str in (e.attendees or [])]
    return filtered[offset : offset + limit]


def get_team_history(
    db: Session,
    limit: int = 30,
    offset: int = 0,
    month: str | None = None,
) -> list[LunchHistory]:
    stmt = select(LunchHistory).order_by(LunchHistory.date.desc())
    if month:
        year, mon = month.split("-")
        stmt = stmt.where(
            extract("year", LunchHistory.date) == int(year),
            extract("month", LunchHistory.date) == int(mon),
        )
    stmt = stmt.offset(offset).limit(limit)
    return list(db.execute(stmt).scalars().all())
