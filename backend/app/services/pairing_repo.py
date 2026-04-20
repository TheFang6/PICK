import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.pairing_token import PairingToken

PAIRING_TOKEN_TTL_MINUTES = 10


def create_token(db: Session, user_id: uuid.UUID) -> PairingToken:
    token = PairingToken(
        id=uuid.uuid4(),
        token=uuid.uuid4().hex,
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=PAIRING_TOKEN_TTL_MINUTES),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_valid_token(db: Session, token_str: str) -> PairingToken | None:
    now = datetime.now(timezone.utc)
    return (
        db.query(PairingToken)
        .filter(
            PairingToken.token == token_str,
            PairingToken.expires_at > now,
            PairingToken.consumed_at.is_(None),
        )
        .first()
    )


def consume_token(db: Session, token: PairingToken) -> None:
    token.consumed_at = datetime.now(timezone.utc)
    db.commit()


def cleanup_expired(db: Session) -> int:
    now = datetime.now(timezone.utc)
    count = (
        db.query(PairingToken)
        .filter(PairingToken.expires_at <= now, PairingToken.consumed_at.is_(None))
        .delete()
    )
    db.commit()
    return count
