import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.web_session import WebSession

SESSION_LIFETIME_DAYS = 30


def create_session(db: Session, user_id: uuid.UUID) -> WebSession:
    session = WebSession(
        user_id=user_id,
        session_token=uuid.uuid4().hex + uuid.uuid4().hex,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_LIFETIME_DAYS),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_valid_session(db: Session, session_token: str) -> WebSession | None:
    now = datetime.now(timezone.utc)
    return db.execute(
        select(WebSession).where(
            WebSession.session_token == session_token,
            WebSession.expires_at > now,
        )
    ).scalar_one_or_none()


def delete_session(db: Session, session_token: str) -> bool:
    session = db.execute(
        select(WebSession).where(WebSession.session_token == session_token)
    ).scalar_one_or_none()
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True


def cleanup_expired(db: Session) -> int:
    now = datetime.now(timezone.utc)
    count = (
        db.query(WebSession)
        .filter(WebSession.expires_at <= now)
        .delete()
    )
    db.commit()
    return count
