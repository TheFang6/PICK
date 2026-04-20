import random

from app.services.session_pool import (
    MAX_GACHA_ROLLS,
    add_previous_picks,
    get_session,
    increment_gacha,
)


class SessionNotFound(Exception):
    pass


class SessionExpired(Exception):
    pass


class GachaLimitExceeded(Exception):
    pass


def roll(session_id: str, k: int = 3) -> dict:
    session = get_session(session_id)
    if session is None:
        from app.services.session_pool import _sessions
        if session_id in _sessions:
            raise SessionExpired()
        raise SessionNotFound()

    if session["gacha_count"] >= MAX_GACHA_ROLLS:
        raise GachaLimitExceeded()

    pool = session["pool"]
    previous_picks = session["previous_picks"]

    available = [(r, score) for r, score in pool if r.id not in previous_picks]

    if not available:
        available = list(pool)

    if len(available) <= k:
        candidates = [r for r, _ in available]
    else:
        restaurants = [r for r, _ in available]
        weights = [max(0.01, score) for _, score in available]
        selected = []
        remaining = list(range(len(available)))
        remaining_weights = list(weights)

        for _ in range(k):
            chosen = random.choices(remaining, weights=remaining_weights, k=1)[0]
            idx = remaining.index(chosen)
            selected.append(chosen)
            remaining.pop(idx)
            remaining_weights.pop(idx)

        candidates = [restaurants[i] for i in selected]

    new_count = increment_gacha(session_id)
    add_previous_picks(session_id, {r.id for r in candidates})

    return {
        "candidates": candidates,
        "remaining_rolls": MAX_GACHA_ROLLS - new_count,
        "gacha_count": new_count,
    }
