import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app
from app.models.attendance import AttendanceStatus, UserAttendance
from app.models.user import User


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _create_user(db, telegram_id="12345", name="Test User"):
    user = User(id=uuid.uuid4(), telegram_id=telegram_id, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestAttendanceRepo:
    def test_set_status_new(self, db):
        from app.services.attendance_repo import set_status

        user = _create_user(db)
        today = date(2026, 4, 20)
        record = set_status(db, user.id, AttendanceStatus.IN_OFFICE, target_date=today)
        assert record.status == AttendanceStatus.IN_OFFICE
        assert record.user_id == user.id
        assert record.date == today

    def test_set_status_upsert(self, db):
        from app.services.attendance_repo import set_status

        user = _create_user(db)
        today = date(2026, 4, 20)
        set_status(db, user.id, AttendanceStatus.WFH, target_date=today)
        record = set_status(db, user.id, AttendanceStatus.IN_OFFICE, target_date=today)
        assert record.status == AttendanceStatus.IN_OFFICE
        assert db.query(UserAttendance).filter(UserAttendance.user_id == user.id, UserAttendance.date == today).count() == 1

    def test_set_status_different_dates(self, db):
        from app.services.attendance_repo import set_status

        user = _create_user(db)
        set_status(db, user.id, AttendanceStatus.WFH, target_date=date(2026, 4, 20))
        set_status(db, user.id, AttendanceStatus.IN_OFFICE, target_date=date(2026, 4, 21))
        assert db.query(UserAttendance).filter(UserAttendance.user_id == user.id).count() == 2

    def test_get_today_status_exists(self, db):
        from app.services.attendance_repo import get_today_status, set_status

        user = _create_user(db)
        today = date(2026, 4, 20)
        set_status(db, user.id, AttendanceStatus.WFH, target_date=today)
        status = get_today_status(db, user.id, target_date=today)
        assert status == AttendanceStatus.WFH

    def test_get_today_status_no_record(self, db):
        from app.services.attendance_repo import get_today_status

        user = _create_user(db)
        status = get_today_status(db, user.id, target_date=date(2026, 4, 20))
        assert status == AttendanceStatus.UNKNOWN

    def test_get_attendees_in_office(self, db):
        from app.services.attendance_repo import get_attendees, set_status

        u1 = _create_user(db, "111", "Alice")
        u2 = _create_user(db, "222", "Bob")
        u3 = _create_user(db, "333", "Charlie")
        today = date(2026, 4, 20)
        set_status(db, u1.id, AttendanceStatus.IN_OFFICE, target_date=today)
        set_status(db, u2.id, AttendanceStatus.WFH, target_date=today)
        set_status(db, u3.id, AttendanceStatus.IN_OFFICE, target_date=today)

        attendees = get_attendees(db, target_date=today, statuses=[AttendanceStatus.IN_OFFICE])
        names = {u.name for u in attendees}
        assert names == {"Alice", "Charlie"}

    def test_get_attendees_includes_unknown(self, db):
        from app.services.attendance_repo import get_attendees, set_status

        u1 = _create_user(db, "111", "Alice")
        u2 = _create_user(db, "222", "Bob")
        _create_user(db, "333", "Charlie")
        today = date(2026, 4, 20)
        set_status(db, u1.id, AttendanceStatus.IN_OFFICE, target_date=today)
        set_status(db, u2.id, AttendanceStatus.WFH, target_date=today)

        attendees = get_attendees(db, target_date=today)
        names = {u.name for u in attendees}
        assert names == {"Alice", "Charlie"}

    def test_get_attendees_wfh_only(self, db):
        from app.services.attendance_repo import get_attendees, set_status

        u1 = _create_user(db, "111", "Alice")
        today = date(2026, 4, 20)
        set_status(db, u1.id, AttendanceStatus.WFH, target_date=today)

        attendees = get_attendees(db, target_date=today, statuses=[AttendanceStatus.WFH])
        names = {u.name for u in attendees}
        assert names == {"Alice"}

    def test_drop_unknown(self, db):
        from app.services.attendance_repo import drop_unknown, set_status

        u1 = _create_user(db, "111", "Alice")
        u2 = _create_user(db, "222", "Bob")
        today = date(2026, 4, 20)
        set_status(db, u1.id, AttendanceStatus.UNKNOWN, target_date=today)
        set_status(db, u2.id, AttendanceStatus.IN_OFFICE, target_date=today)

        count = drop_unknown(db, target_date=today)
        assert count == 1
        record = db.query(UserAttendance).filter(UserAttendance.user_id == u1.id, UserAttendance.date == today).first()
        assert record.status == AttendanceStatus.WFH

    def test_drop_unknown_no_unknowns(self, db):
        from app.services.attendance_repo import drop_unknown, set_status

        u1 = _create_user(db, "111", "Alice")
        today = date(2026, 4, 20)
        set_status(db, u1.id, AttendanceStatus.IN_OFFICE, target_date=today)
        count = drop_unknown(db, target_date=today)
        assert count == 0


class TestAttendanceHandlers:
    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.full_name = "Test User"
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_wfh_handler(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.attendance.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.attendance.user_repo") as mock_user_repo,
            patch("app.bot.handlers.attendance.attendance_repo") as mock_att_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            from app.bot.handlers.attendance import wfh_handler

            await wfh_handler(mock_update, mock_context)

            mock_att_repo.set_status.assert_called_once_with(mock_db, mock_user.id, AttendanceStatus.WFH)
            call_args = mock_update.message.reply_text.call_args
            assert "home" in call_args[0][0].lower() or "Home" in call_args[0][0]
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_in_handler(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.attendance.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.attendance.user_repo") as mock_user_repo,
            patch("app.bot.handlers.attendance.attendance_repo") as mock_att_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            from app.bot.handlers.attendance import in_handler

            await in_handler(mock_update, mock_context)

            mock_att_repo.set_status.assert_called_once_with(mock_db, mock_user.id, AttendanceStatus.IN_OFFICE)
            call_args = mock_update.message.reply_text.call_args
            assert "office" in call_args[0][0].lower() or "Office" in call_args[0][0]
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_wfh_error_handling(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.attendance.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.attendance.user_repo") as mock_user_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user_repo.upsert_by_telegram_id.side_effect = Exception("DB error")

            from app.bot.handlers.attendance import wfh_handler

            await wfh_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            assert "Something went wrong" in call_args[0][0]
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_in_no_effective_user(self, mock_context):
        update = MagicMock()
        update.effective_user = None
        update.message = AsyncMock()

        from app.bot.handlers.attendance import in_handler

        await in_handler(update, mock_context)
        update.message.reply_text.assert_not_called()


class TestAttendanceAPI:
    @pytest.fixture
    def client(self):
        yield TestClient(app)

    def test_get_today_attendance(self, client):
        with patch("app.api.attendance.attendance_repo") as mock_repo:
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user.telegram_id = "12345"
            mock_user.name = "Test"
            mock_repo.get_attendees.return_value = [mock_user]

            resp = client.get("/attendance/today")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["attendees"]) == 1
            assert data["attendees"][0]["name"] == "Test"

    def test_get_today_attendance_empty(self, client):
        with patch("app.api.attendance.attendance_repo") as mock_repo:
            mock_repo.get_attendees.return_value = []

            resp = client.get("/attendance/today")
            assert resp.status_code == 200
            assert resp.json()["attendees"] == []
