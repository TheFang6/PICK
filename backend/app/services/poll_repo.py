import random
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.poll import PollSession, PollStatus, PollVote

POLL_TIMEOUT_MINUTES = 10


def create_poll(
    db: Session,
    chat_id: str,
    candidate_ids: list[uuid.UUID],
    session_id: str | None,
    created_by: uuid.UUID,
) -> PollSession:
    poll = PollSession(
        id=uuid.uuid4(),
        chat_id=chat_id,
        candidates=[str(cid) for cid in candidate_ids],
        session_id=session_id,
        status=PollStatus.ACTIVE,
        created_by=created_by,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=POLL_TIMEOUT_MINUTES),
    )
    db.add(poll)
    db.commit()
    db.refresh(poll)
    return poll


def set_message_id(db: Session, poll_id: uuid.UUID, message_id: int) -> None:
    poll = db.query(PollSession).filter(PollSession.id == poll_id).first()
    if poll:
        poll.message_id = message_id
        db.commit()


def cast_vote(
    db: Session,
    poll_id: uuid.UUID,
    user_id: uuid.UUID,
    restaurant_id: uuid.UUID,
) -> PollVote:
    existing = (
        db.query(PollVote)
        .filter(PollVote.poll_session_id == poll_id, PollVote.user_id == user_id)
        .first()
    )
    if existing:
        existing.restaurant_id = restaurant_id
        db.commit()
        db.refresh(existing)
        return existing

    vote = PollVote(
        id=uuid.uuid4(),
        poll_session_id=poll_id,
        user_id=user_id,
        restaurant_id=restaurant_id,
    )
    db.add(vote)
    db.commit()
    db.refresh(vote)
    return vote


def get_vote_counts(db: Session, poll_id: uuid.UUID) -> dict[str, int]:
    votes = db.query(PollVote).filter(PollVote.poll_session_id == poll_id).all()
    counts = Counter(str(v.restaurant_id) for v in votes)
    return dict(counts)


def get_total_votes(db: Session, poll_id: uuid.UUID) -> int:
    return db.query(PollVote).filter(PollVote.poll_session_id == poll_id).count()


def get_poll(db: Session, poll_id: uuid.UUID) -> PollSession | None:
    return db.query(PollSession).filter(PollSession.id == poll_id).first()


def cancel_poll(db: Session, poll_id: uuid.UUID) -> bool:
    poll = db.query(PollSession).filter(PollSession.id == poll_id).first()
    if not poll or poll.status != PollStatus.ACTIVE:
        return False
    poll.status = PollStatus.CANCELLED
    poll.completed_at = datetime.now(timezone.utc)
    db.commit()
    return True


def complete_poll(db: Session, poll_id: uuid.UUID, winner_id: uuid.UUID) -> bool:
    poll = db.query(PollSession).filter(PollSession.id == poll_id).first()
    if not poll or poll.status != PollStatus.ACTIVE:
        return False
    poll.status = PollStatus.COMPLETED
    poll.winner_restaurant_id = winner_id
    poll.completed_at = datetime.now(timezone.utc)
    db.commit()
    return True


def get_expired_active_polls(db: Session) -> list[PollSession]:
    now = datetime.now(timezone.utc)
    return (
        db.query(PollSession)
        .filter(PollSession.status == PollStatus.ACTIVE, PollSession.expires_at <= now)
        .all()
    )


def determine_winner(db: Session, poll: PollSession) -> uuid.UUID:
    counts = get_vote_counts(db, poll.id)
    candidate_ids = poll.candidates

    if not counts:
        return uuid.UUID(candidate_ids[0])

    max_votes = max(counts.values())
    top = [rid for rid, c in counts.items() if c == max_votes]
    return uuid.UUID(random.choice(top))


def get_voter_ids(db: Session, poll_id: uuid.UUID) -> list[uuid.UUID]:
    votes = db.query(PollVote).filter(PollVote.poll_session_id == poll_id).all()
    return [v.user_id for v in votes]
