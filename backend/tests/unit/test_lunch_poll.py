import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.poll import PollSession, PollStatus, PollVote
from app.models.restaurant import Restaurant, RestaurantSource
from app.models.user import User


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _create_user(db, telegram_id="12345", name="Test"):
    user = User(id=uuid.uuid4(), telegram_id=telegram_id, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_restaurant(db, name="Test Restaurant"):
    r = Restaurant(
        id=uuid.uuid4(),
        name=name,
        source=RestaurantSource.MANUAL,
        rating=4.0,
        price_level=2,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


class TestPollRepo:
    def test_create_poll(self, db):
        from app.services.poll_repo import create_poll

        user = _create_user(db)
        r1 = _create_restaurant(db, "R1")
        r2 = _create_restaurant(db, "R2")

        poll = create_poll(db, "chat123", [r1.id, r2.id], "session1", user.id)
        assert poll.status == PollStatus.ACTIVE
        assert poll.chat_id == "chat123"
        assert len(poll.candidates) == 2
        assert poll.created_by == user.id

    def test_set_message_id(self, db):
        from app.services.poll_repo import create_poll, get_poll, set_message_id

        user = _create_user(db)
        poll = create_poll(db, "chat1", [], None, user.id)
        set_message_id(db, poll.id, 42)
        updated = get_poll(db, poll.id)
        assert updated.message_id == 42

    def test_cast_vote_new(self, db):
        from app.services.poll_repo import cast_vote, create_poll

        user = _create_user(db)
        r = _create_restaurant(db)
        poll = create_poll(db, "chat1", [r.id], None, user.id)

        vote = cast_vote(db, poll.id, user.id, r.id)
        assert vote.restaurant_id == r.id

    def test_cast_vote_change(self, db):
        from app.services.poll_repo import cast_vote, create_poll

        user = _create_user(db)
        r1 = _create_restaurant(db, "R1")
        r2 = _create_restaurant(db, "R2")
        poll = create_poll(db, "chat1", [r1.id, r2.id], None, user.id)

        cast_vote(db, poll.id, user.id, r1.id)
        vote = cast_vote(db, poll.id, user.id, r2.id)
        assert vote.restaurant_id == r2.id
        assert db.query(PollVote).filter(PollVote.poll_session_id == poll.id).count() == 1

    def test_get_vote_counts(self, db):
        from app.services.poll_repo import cast_vote, create_poll, get_vote_counts

        u1 = _create_user(db, "111", "A")
        u2 = _create_user(db, "222", "B")
        r1 = _create_restaurant(db, "R1")
        r2 = _create_restaurant(db, "R2")
        poll = create_poll(db, "chat1", [r1.id, r2.id], None, u1.id)

        cast_vote(db, poll.id, u1.id, r1.id)
        cast_vote(db, poll.id, u2.id, r1.id)

        counts = get_vote_counts(db, poll.id)
        assert counts[str(r1.id)] == 2

    def test_get_total_votes(self, db):
        from app.services.poll_repo import cast_vote, create_poll, get_total_votes

        u1 = _create_user(db, "111", "A")
        u2 = _create_user(db, "222", "B")
        r = _create_restaurant(db)
        poll = create_poll(db, "chat1", [r.id], None, u1.id)

        cast_vote(db, poll.id, u1.id, r.id)
        cast_vote(db, poll.id, u2.id, r.id)

        assert get_total_votes(db, poll.id) == 2

    def test_cancel_poll(self, db):
        from app.services.poll_repo import cancel_poll, create_poll, get_poll

        user = _create_user(db)
        poll = create_poll(db, "chat1", [], None, user.id)

        assert cancel_poll(db, poll.id) is True
        updated = get_poll(db, poll.id)
        assert updated.status == PollStatus.CANCELLED

    def test_cancel_already_completed(self, db):
        from app.services.poll_repo import cancel_poll, complete_poll, create_poll

        user = _create_user(db)
        r = _create_restaurant(db)
        poll = create_poll(db, "chat1", [r.id], None, user.id)
        complete_poll(db, poll.id, r.id)

        assert cancel_poll(db, poll.id) is False

    def test_complete_poll(self, db):
        from app.services.poll_repo import complete_poll, create_poll, get_poll

        user = _create_user(db)
        r = _create_restaurant(db)
        poll = create_poll(db, "chat1", [r.id], None, user.id)

        assert complete_poll(db, poll.id, r.id) is True
        updated = get_poll(db, poll.id)
        assert updated.status == PollStatus.COMPLETED
        assert updated.winner_restaurant_id == r.id

    def test_get_expired_active_polls(self, db):
        from app.services.poll_repo import create_poll, get_expired_active_polls

        user = _create_user(db)
        poll = create_poll(db, "chat1", [], None, user.id)
        poll.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

        expired = get_expired_active_polls(db)
        assert len(expired) == 1
        assert expired[0].id == poll.id

    def test_no_expired_polls(self, db):
        from app.services.poll_repo import create_poll, get_expired_active_polls

        user = _create_user(db)
        create_poll(db, "chat1", [], None, user.id)

        expired = get_expired_active_polls(db)
        assert len(expired) == 0

    def test_determine_winner_with_votes(self, db):
        from app.services.poll_repo import cast_vote, create_poll, determine_winner

        u1 = _create_user(db, "111", "A")
        u2 = _create_user(db, "222", "B")
        u3 = _create_user(db, "333", "C")
        r1 = _create_restaurant(db, "R1")
        r2 = _create_restaurant(db, "R2")
        poll = create_poll(db, "chat1", [r1.id, r2.id], None, u1.id)

        cast_vote(db, poll.id, u1.id, r1.id)
        cast_vote(db, poll.id, u2.id, r1.id)
        cast_vote(db, poll.id, u3.id, r2.id)

        winner = determine_winner(db, poll)
        assert winner == r1.id

    def test_determine_winner_no_votes(self, db):
        from app.services.poll_repo import create_poll, determine_winner

        user = _create_user(db)
        r1 = _create_restaurant(db, "R1")
        r2 = _create_restaurant(db, "R2")
        poll = create_poll(db, "chat1", [r1.id, r2.id], None, user.id)

        winner = determine_winner(db, poll)
        assert winner == r1.id

    def test_determine_winner_tie(self, db):
        from app.services.poll_repo import cast_vote, create_poll, determine_winner

        u1 = _create_user(db, "111", "A")
        u2 = _create_user(db, "222", "B")
        r1 = _create_restaurant(db, "R1")
        r2 = _create_restaurant(db, "R2")
        poll = create_poll(db, "chat1", [r1.id, r2.id], None, u1.id)

        cast_vote(db, poll.id, u1.id, r1.id)
        cast_vote(db, poll.id, u2.id, r2.id)

        winner = determine_winner(db, poll)
        assert winner in (r1.id, r2.id)

    def test_get_voter_ids(self, db):
        from app.services.poll_repo import cast_vote, create_poll, get_voter_ids

        u1 = _create_user(db, "111", "A")
        u2 = _create_user(db, "222", "B")
        r = _create_restaurant(db)
        poll = create_poll(db, "chat1", [r.id], None, u1.id)

        cast_vote(db, poll.id, u1.id, r.id)
        cast_vote(db, poll.id, u2.id, r.id)

        voter_ids = get_voter_ids(db, poll.id)
        assert set(voter_ids) == {u1.id, u2.id}


class TestLunchHandler:
    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.full_name = "Test User"
        update.effective_chat = MagicMock()
        update.effective_chat.id = -100123
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        update.message.reply_text.return_value = MagicMock(message_id=99)
        return update

    @pytest.fixture
    def mock_context(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_no_attendees(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.lunch.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.lunch.user_repo") as mock_user_repo,
            patch("app.bot.handlers.lunch.attendance_repo") as mock_att_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)
            mock_att_repo.get_attendees.return_value = []

            from app.bot.handlers.lunch import lunch_handler

            await lunch_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            assert "No one" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_with_attendees(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.lunch.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.lunch.user_repo") as mock_user_repo,
            patch("app.bot.handlers.lunch.attendance_repo") as mock_att_repo,
            patch("app.bot.handlers.lunch.recommend") as mock_recommend,
            patch("app.bot.handlers.lunch.poll_repo") as mock_poll_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            attendee1 = MagicMock()
            attendee1.id = uuid.uuid4()
            attendee2 = MagicMock()
            attendee2.id = uuid.uuid4()
            mock_att_repo.get_attendees.return_value = [attendee1, attendee2]

            r1 = MagicMock()
            r1.id = uuid.uuid4()
            r1.name = "Restaurant A"
            r1.rating = 4.5
            r2 = MagicMock()
            r2.id = uuid.uuid4()
            r2.name = "Restaurant B"
            r2.rating = 4.0
            mock_recommend.return_value = {"candidates": [r1, r2], "session_id": "sess1", "pool": [], "remaining_rolls": 5}

            mock_poll = MagicMock()
            mock_poll.id = uuid.uuid4()
            mock_poll_repo.create_poll.return_value = mock_poll

            from app.bot.handlers.lunch import lunch_handler

            await lunch_handler(mock_update, mock_context)

            mock_recommend.assert_called_once()
            mock_poll_repo.create_poll.assert_called_once()
            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_update, mock_context):
        with (
            patch("app.bot.handlers.lunch.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.lunch.user_repo") as mock_user_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_user_repo.upsert_by_telegram_id.side_effect = Exception("DB error")

            from app.bot.handlers.lunch import lunch_handler

            await lunch_handler(mock_update, mock_context)

            call_args = mock_update.message.reply_text.call_args
            assert "Something went wrong" in call_args[0][0]


class TestVoteCallback:
    @pytest.mark.asyncio
    async def test_vote_success(self):
        query = AsyncMock()
        query.data = f"vote:{uuid.uuid4()}:0"
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.from_user.full_name = "Test"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        with (
            patch("app.bot.handlers.poll_callbacks.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.poll_callbacks.poll_repo") as mock_poll_repo,
            patch("app.bot.handlers.poll_callbacks.user_repo") as mock_user_repo,
            patch("app.bot.handlers.poll_callbacks.restaurant_repo") as mock_rest_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_poll = MagicMock()
            mock_poll.id = uuid.uuid4()
            mock_poll.status = PollStatus.ACTIVE
            mock_poll.candidates = [str(uuid.uuid4())]
            mock_poll_repo.get_poll.return_value = mock_poll
            mock_poll_repo.get_vote_counts.return_value = {}
            mock_poll_repo.get_total_votes.return_value = 1

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            mock_rest = MagicMock()
            mock_rest.id = uuid.uuid4()
            mock_rest.name = "R1"
            mock_rest.rating = 4.0
            mock_rest_repo.get_by_id.return_value = mock_rest

            from app.bot.handlers.poll_callbacks import vote_callback

            await vote_callback(update, context)

            mock_poll_repo.cast_vote.assert_called_once()
            query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_vote_poll_ended(self):
        query = AsyncMock()
        query.data = f"vote:{uuid.uuid4()}:0"
        query.answer = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        with (
            patch("app.bot.handlers.poll_callbacks.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.poll_callbacks.poll_repo") as mock_poll_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_poll = MagicMock()
            mock_poll.status = PollStatus.COMPLETED
            mock_poll_repo.get_poll.return_value = mock_poll

            from app.bot.handlers.poll_callbacks import vote_callback

            await vote_callback(update, context)

            query.answer.assert_called_with("This poll has ended.", show_alert=True)


class TestCancelCallback:
    @pytest.mark.asyncio
    async def test_cancel_by_creator(self):
        poll_id = uuid.uuid4()
        query = AsyncMock()
        query.data = f"cancel:{poll_id}"
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.from_user.full_name = "Test"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        user_id = uuid.uuid4()

        with (
            patch("app.bot.handlers.poll_callbacks.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.poll_callbacks.poll_repo") as mock_poll_repo,
            patch("app.bot.handlers.poll_callbacks.user_repo") as mock_user_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_poll = MagicMock()
            mock_poll.created_by = user_id
            mock_poll.status = PollStatus.ACTIVE
            mock_poll_repo.get_poll.return_value = mock_poll

            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            from app.bot.handlers.poll_callbacks import cancel_callback

            await cancel_callback(update, context)

            mock_poll_repo.cancel_poll.assert_called_once()
            query.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_by_non_creator(self):
        poll_id = uuid.uuid4()
        query = AsyncMock()
        query.data = f"cancel:{poll_id}"
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.from_user.full_name = "Test"
        query.answer = AsyncMock()

        update = MagicMock()
        update.callback_query = query
        context = MagicMock()

        with (
            patch("app.bot.handlers.poll_callbacks.SessionLocal") as mock_session_cls,
            patch("app.bot.handlers.poll_callbacks.poll_repo") as mock_poll_repo,
            patch("app.bot.handlers.poll_callbacks.user_repo") as mock_user_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            mock_poll = MagicMock()
            mock_poll.created_by = uuid.uuid4()
            mock_poll.status = PollStatus.ACTIVE
            mock_poll_repo.get_poll.return_value = mock_poll

            mock_user = MagicMock()
            mock_user.id = uuid.uuid4()
            mock_user_repo.upsert_by_telegram_id.return_value = (mock_user, False)

            from app.bot.handlers.poll_callbacks import cancel_callback

            await cancel_callback(update, context)

            query.answer.assert_called_with("Only the poll creator can cancel.", show_alert=True)
            mock_poll_repo.cancel_poll.assert_not_called()


class TestPollTimeout:
    @pytest.mark.asyncio
    async def test_check_expired_polls(self):
        with (
            patch("app.bot.poll_timeout.SessionLocal") as mock_session_cls,
            patch("app.bot.poll_timeout.poll_repo") as mock_poll_repo,
            patch("app.bot.poll_timeout.restaurant_repo") as mock_rest_repo,
            patch("app.bot.poll_timeout.history_repo") as mock_hist_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db

            winner_id = uuid.uuid4()
            mock_poll = MagicMock()
            mock_poll.id = uuid.uuid4()
            mock_poll.chat_id = "chat1"
            mock_poll.message_id = 42
            mock_poll.candidates = [str(winner_id)]
            mock_poll_repo.get_expired_active_polls.return_value = [mock_poll]
            mock_poll_repo.determine_winner.return_value = winner_id
            mock_poll_repo.get_vote_counts.return_value = {str(winner_id): 2}
            mock_poll_repo.get_voter_ids.return_value = [uuid.uuid4(), uuid.uuid4()]

            mock_winner = MagicMock()
            mock_winner.name = "Winner Restaurant"
            mock_rest_repo.get_by_id.return_value = mock_winner

            mock_app = AsyncMock()
            mock_app.bot = AsyncMock()

            from app.bot.poll_timeout import check_expired_polls

            await check_expired_polls(mock_app)

            mock_poll_repo.complete_poll.assert_called_once()
            mock_hist_repo.log_lunch.assert_called_once()
            mock_app.bot.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_expired_polls(self):
        with (
            patch("app.bot.poll_timeout.SessionLocal") as mock_session_cls,
            patch("app.bot.poll_timeout.poll_repo") as mock_poll_repo,
        ):
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_poll_repo.get_expired_active_polls.return_value = []

            mock_app = AsyncMock()

            from app.bot.poll_timeout import check_expired_polls

            await check_expired_polls(mock_app)

            mock_poll_repo.complete_poll.assert_not_called()
