import logging
import random
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

    _, poll_id_str, index_str = parts

    db = SessionLocal()
    try:
        poll_id = uuid.UUID(poll_id_str)
        candidate_index = int(index_str)

        poll = poll_repo.get_poll(db, poll_id)
        if not poll or poll.status != PollStatus.ACTIVE:
            await query.answer("This poll has ended.", show_alert=True)
            return

        if candidate_index < 0 or candidate_index >= len(poll.candidates):
            await query.answer("Invalid option.", show_alert=True)
            return

        restaurant_id = uuid.UUID(poll.candidates[candidate_index])

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

        candidate_ids = [uuid.UUID(cid) for cid in poll.candidates]
        restaurants = []
        for cid in candidate_ids:
            r = restaurant_repo.get_by_id(db, cid)
            if r:
                restaurants.append(r)

        if not restaurants:
            await query.answer("No restaurants to pick from.", show_alert=True)
            return

        pick = random.choice(restaurants)

        voter_ids = poll_repo.get_voter_ids(db, poll_id)
        if voter_ids:
            history_repo.log_lunch(db, pick.id, voter_ids)

        poll_repo.complete_poll(db, poll_id, pick.id)

        distance = ""
        if pick.lat and pick.lng:
            from math import atan2, cos, radians, sin, sqrt
            R = 6371000
            olat, olng = 13.756331, 100.501762
            rlat1, rlat2 = radians(olat), radians(pick.lat)
            dlat = radians(pick.lat - olat)
            dlng = radians(pick.lng - olng)
            a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
            d = R * 2 * atan2(sqrt(a), sqrt(1 - a))
            distance = f"{int(d)}m"

        rating = f"⭐ {pick.rating}" if pick.rating else ""
        lines = ["\U0001F3B2 Gacha picked!\n"]
        lines.append(f"\U0001F35C {pick.name}")
        if distance or rating:
            lines.append(f"   {distance} {rating}".strip())
        lines.append("\nEnjoy your meal! \U0001F60B")

        await query.edit_message_text("\n".join(lines))
    except Exception:
        logger.exception("Error in gacha callback")
    finally:
        db.close()
