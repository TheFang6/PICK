import uuid
from datetime import datetime, timedelta, timezone

_sessions: dict[str, dict] = {}

DEFAULT_TTL_HOURS = 2
MAX_GACHA_ROLLS = 5


def create_session(pool: list[tuple]) -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "pool": pool,
        "gacha_count": 0,
        "previous_picks": set(),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=DEFAULT_TTL_HOURS),
    }
    return session_id


def get_session(session_id: str) -> dict | None:
    session = _sessions.get(session_id)
    if session is None:
        return None
    if datetime.now(timezone.utc) > session["expires_at"]:
        return None
    return session


def increment_gacha(session_id: str) -> int:
    session = _sessions.get(session_id)
    if session is None:
        return -1
    session["gacha_count"] += 1
    return session["gacha_count"]


def add_previous_picks(session_id: str, pick_ids: set[uuid.UUID]) -> None:
    session = _sessions.get(session_id)
    if session:
        session["previous_picks"].update(pick_ids)


def cleanup_expired() -> int:
    now = datetime.now(timezone.utc)
    expired = [sid for sid, s in _sessions.items() if now > s["expires_at"]]
    for sid in expired:
        del _sessions[sid]
    return len(expired)


def clear_all() -> None:
    _sessions.clear()
