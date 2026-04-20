import logging
import uuid

from telegram import Update
from telegram.ext import ContextTypes

from app.database import SessionLocal
from app.models.poll import PollStatus
from app.services import history_repo, poll_repo, restaurant_repo, user_repo

logger = logging.getLogger(__name__)


async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 3:
        return

    _, poll_id_str, restaurant_id_str = parts

    db = SessionLocal()
    try:
        poll_id = uuid.UUID(poll_id_str)
        restaurant_id = uuid.UUID(restaurant_id_str)

        poll = poll_repo.get_poll(db, poll_id)
        if not poll or poll.status != PollStatus.ACTIVE:
            await query.answer("This poll has ended.", show_alert=True)
            return

        telegram_id = str(query.from_user.id)
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, query.from_user.full_name or "Unknown")
        poll_repo.cast_vote(db, poll_id, user.id, restaurant_id)

        vote_counts = poll_repo.get_vote_counts(db, poll_id)
        total_votes = poll_repo.get_total_votes(db, poll_id)

        candidate_ids = [uuid.UUID(cid) for cid in poll.candidates]
        restaurants = []
        for cid in candidate_ids:
            r = restaurant_repo.get_by_id(db, cid)
            if r:
                restaurants.append(r)

        from app.bot.handlers.lunch import _build_poll_text, _build_poll_keyboard
        text = _build_poll_text(restaurants, vote_counts=vote_counts, total_votes=total_votes)
        keyboard = _build_poll_keyboard(poll.id, restaurants)

        await query.edit_message_text(text, reply_markup=keyboard)
    except Exception:
        logger.exception("Error in vote callback")
    finally:
        db.close()


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 2:
        return

    _, poll_id_str = parts

    db = SessionLocal()
    try:
        poll_id = uuid.UUID(poll_id_str)
        poll = poll_repo.get_poll(db, poll_id)
        if not poll:
            return

        telegram_id = str(query.from_user.id)
        user, _ = user_repo.upsert_by_telegram_id(db, telegram_id, query.from_user.full_name or "Unknown")

        if poll.created_by != user.id:
            await query.answer("Only the poll creator can cancel.", show_alert=True)
            return

        if poll.status != PollStatus.ACTIVE:
            await query.answer("This poll has already ended.", show_alert=True)
            return

        poll_repo.cancel_poll(db, poll_id)
        await query.edit_message_text("\u274C Poll cancelled.")
    except Exception:
        logger.exception("Error in cancel callback")
    finally:
        db.close()


async def gacha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 2:
        return

    _, poll_id_str = parts

    db = SessionLocal()
    try:
        poll_id = uuid.UUID(poll_id_str)
        poll = poll_repo.get_poll(db, poll_id)
        if not poll or poll.status != PollStatus.ACTIVE:
            await query.answer("This poll has ended.", show_alert=True)
            return

        if not poll.session_id:
            await query.answer("No gacha pool available.", show_alert=True)
            return

        from app.services.gacha import GachaLimitExceeded, SessionExpired, SessionNotFound, roll

        try:
            result = roll(poll.session_id)
        except (SessionNotFound, SessionExpired):
            await query.answer("Gacha session expired.", show_alert=True)
            return
        except GachaLimitExceeded:
            await query.answer("Max gacha rolls reached (5).", show_alert=True)
            return

        new_candidates = result["candidates"]
        new_candidate_ids = [r.id for r in new_candidates]
        poll.candidates = [str(cid) for cid in new_candidate_ids]
        db.commit()

        from app.bot.handlers.lunch import _build_poll_text, _build_poll_keyboard
        text = _build_poll_text(new_candidates)
        remaining = result["remaining_rolls"]
        text += f"\n\n\U0001F3B2 Gacha! ({remaining} rolls left)"
        keyboard = _build_poll_keyboard(poll.id, new_candidates)

        await query.edit_message_text(text, reply_markup=keyboard)
    except Exception:
        logger.exception("Error in gacha callback")
    finally:
        db.close()
