import uuid

from sqlalchemy.orm import Session

from app.models.user import User


def upsert_by_telegram_id(db: Session, telegram_id: str, name: str) -> tuple[User, bool]:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        user.name = name
        db.commit()
        db.refresh(user)
        return user, False

    user = User(id=uuid.uuid4(), telegram_id=telegram_id, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True
