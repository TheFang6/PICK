import logging
import uuid

from telegram.ext import Application

from app.database import SessionLocal
from app.services import history_repo, poll_repo, restaurant_repo

logger = logging.getLogger(__name__)


async def check_expired_polls(application: Application) -> None:
    db = SessionLocal()
    try:
        expired = poll_repo.get_expired_active_polls(db)
        for poll in expired:
            try:
                await _complete_poll(db, poll, application)
            except Exception:
                logger.exception("Error completing poll %s", poll.id)
    finally:
        db.close()


async def _complete_poll(db, poll, application: Application) -> None:
    winner_id = poll_repo.determine_winner(db, poll)
    poll_repo.complete_poll(db, poll.id, winner_id)

    winner = restaurant_repo.get_by_id(db, winner_id)
    winner_name = winner.name if winner else "Unknown"

    vote_counts = poll_repo.get_vote_counts(db, poll.id)
    winner_votes = vote_counts.get(str(winner_id), 0)

    voter_ids = poll_repo.get_voter_ids(db, poll.id)
    if voter_ids:
        history_repo.log_lunch(db, winner_id, voter_ids)

    text = (
        f"\U0001F389 Poll results\n"
        f"\u2705 Winner: {winner_name}"
    )
    if winner_votes > 0:
        text += f" ({winner_votes} vote{'s' if winner_votes != 1 else ''})"
    text += "\n\nEnjoy your lunch! \U0001F4CD"

    try:
        await application.bot.edit_message_text(
            chat_id=poll.chat_id,
            message_id=poll.message_id,
            text=text,
        )
    except Exception:
        logger.exception("Failed to edit poll message for poll %s", poll.id)
