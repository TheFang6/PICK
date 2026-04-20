import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.attendance import AttendanceStatus, UserAttendance
from app.models.user import User


def set_status(db: Session, user_id: uuid.UUID, status: AttendanceStatus, target_date: date | None = None) -> UserAttendance:
    if target_date is None:
        from zoneinfo import ZoneInfo
        target_date = datetime.now(ZoneInfo("Asia/Bangkok")).date()

    existing = (
        db.query(UserAttendance)
        .filter(UserAttendance.user_id == user_id, UserAttendance.date == target_date)
        .first()
    )

    if existing:
        existing.status = status
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    record = UserAttendance(
        id=uuid.uuid4(),
        user_id=user_id,
        date=target_date,
        status=status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_today_status(db: Session, user_id: uuid.UUID, target_date: date | None = None) -> AttendanceStatus:
    if target_date is None:
        from zoneinfo import ZoneInfo
        target_date = datetime.now(ZoneInfo("Asia/Bangkok")).date()

    record = (
        db.query(UserAttendance)
        .filter(UserAttendance.user_id == user_id, UserAttendance.date == target_date)
        .first()
    )
    if record:
        return record.status
    return AttendanceStatus.UNKNOWN


def get_attendees(db: Session, target_date: date | None = None, statuses: list[AttendanceStatus] | None = None) -> list[User]:
    if target_date is None:
        from zoneinfo import ZoneInfo
        target_date = datetime.now(ZoneInfo("Asia/Bangkok")).date()

    if statuses is None:
        statuses = [AttendanceStatus.IN_OFFICE, AttendanceStatus.UNKNOWN]

    user_ids_with_status = (
        db.query(UserAttendance.user_id)
        .filter(UserAttendance.date == target_date, UserAttendance.status.in_(statuses))
        .all()
    )
    explicit_ids = {row[0] for row in user_ids_with_status}

    if AttendanceStatus.UNKNOWN in statuses:
        all_dated_user_ids = (
            db.query(UserAttendance.user_id)
            .filter(UserAttendance.date == target_date)
            .all()
        )
        dated_ids = {row[0] for row in all_dated_user_ids}
        all_users = db.query(User).all()
        unknown_ids = {u.id for u in all_users} - dated_ids
        target_ids = explicit_ids | unknown_ids
    else:
        target_ids = explicit_ids

    if not target_ids:
        return []
    return db.query(User).filter(User.id.in_(target_ids)).all()


def drop_unknown(db: Session, target_date: date | None = None) -> int:
    if target_date is None:
        from zoneinfo import ZoneInfo
        target_date = datetime.now(ZoneInfo("Asia/Bangkok")).date()

    count = (
        db.query(UserAttendance)
        .filter(UserAttendance.date == target_date, UserAttendance.status == AttendanceStatus.UNKNOWN)
        .update({"status": AttendanceStatus.WFH, "updated_at": datetime.now(timezone.utc)})
    )
    db.commit()
    return count
