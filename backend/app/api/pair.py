import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services import pairing_repo, web_session_repo

router = APIRouter(tags=["pairing"])

SESSION_COOKIE_MAX_AGE = 30 * 24 * 3600


class PairRequest(BaseModel):
    token: str


class PairResponse(BaseModel):
    user_id: uuid.UUID
    name: str


class MeResponse(BaseModel):
    user_id: uuid.UUID
    name: str


def require_session(
    session_id: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    web_session = web_session_repo.get_valid_session(db, session_id)
    if not web_session:
        raise HTTPException(status_code=401, detail="Session expired")
    user = db.get(User, web_session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/pair", response_model=PairResponse)
def pair(body: PairRequest, response: Response, db: Session = Depends(get_db)):
    token = pairing_repo.get_valid_token(db, body.token)
    if not token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    pairing_repo.consume_token(db, token)

    user = db.get(User, token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    web_session = web_session_repo.create_session(db, user.id)

    response.set_cookie(
        key="session_id",
        value=web_session.session_token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=SESSION_COOKIE_MAX_AGE,
    )

    return PairResponse(user_id=user.id, name=user.name)


@router.get("/me", response_model=MeResponse)
def get_me(user: User = Depends(require_session)):
    return MeResponse(user_id=user.id, name=user.name)


@router.post("/logout")
def logout(
    response: Response,
    session_id: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    if session_id:
        web_session_repo.delete_session(db, session_id)
    response.delete_cookie(key="session_id")
    return {"ok": True}
