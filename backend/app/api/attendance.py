from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.attendance import AttendanceStatus
from app.services import attendance_repo

router = APIRouter(tags=["attendance"])


class AttendeeResponse(BaseModel):
    id: str
    telegram_id: str
    name: str


class AttendanceTodayResponse(BaseModel):
    date: str
    attendees: list[AttendeeResponse]


@router.get("/attendance/today", response_model=AttendanceTodayResponse)
def get_today_attendance(db: Session = Depends(get_db)):
    from zoneinfo import ZoneInfo

    from datetime import datetime

    today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
    users = attendance_repo.get_attendees(db, target_date=today)
    return AttendanceTodayResponse(
        date=today.isoformat(),
        attendees=[
            AttendeeResponse(id=str(u.id), telegram_id=u.telegram_id, name=u.name)
            for u in users
        ],
    )
