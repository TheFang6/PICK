# 021 — Fix Poll Timeout in Production + Change to 5 Minutes

**Phase:** 6 (Improvements)
**Estimated Time:** 1-2 hours
**Dependencies:** 010 (lunch poll flow)

> **For agentic workers:** Use the `task-dev` skill to implement this plan task-by-task. English-only for all commits and PR text. Stop before opening a PR and wait for user review.

---

## Goal

Fix poll auto-close in production (webhook mode) and reduce poll timeout from 10 to 5 minutes.

**Bug:** `check_expired_polls` only runs inside `run_polling.py` (dev mode). Production uses `uvicorn app.main:app` (webhook mode) which has no background task checking for expired polls — polls never auto-close.

**Feature:** Change poll timeout from 10 minutes to 5 minutes.

---

## Architecture

```
BEFORE (broken in production):
  run_polling.py → while True: check_expired_polls(); sleep(60)
  main.py (FastAPI) → no background task → polls never expire

AFTER:
  main.py (FastAPI) → lifespan starts background task
                     → while True: check_expired_polls(); sleep(60)
  run_polling.py → keeps its own loop (dev mode still works)
```

---

## Tech Stack

- Python 3.12, FastAPI, SQLAlchemy 2.x, python-telegram-bot v20+
- pytest + pytest-asyncio for tests

---

## Single PR

**Branch:** `fix/021-poll-timeout-production` (off `main`)

---

## Task 1: Change poll timeout to 5 minutes + update display text

**Files:**
- Modify: `backend/app/services/poll_repo.py` (line 10)
- Modify: `backend/app/bot/handlers/lunch.py` (line 47)
- Modify: `backend/tests/unit/test_lunch_poll.py`

### Step 1.1: Write/update test for 5-minute timeout

In `backend/tests/unit/test_lunch_poll.py`, find the test that verifies poll expiration uses 10 minutes and update the expected value to 5 minutes.

Also add a test verifying `POLL_TIMEOUT_MINUTES == 5`:

```python
def test_poll_timeout_is_five_minutes():
    from app.services.poll_repo import POLL_TIMEOUT_MINUTES
    assert POLL_TIMEOUT_MINUTES == 5
```

Run: `cd backend && pytest tests/unit/test_lunch_poll.py -v -k "timeout"`

Expected: **FAIL** — timeout is still 10.

### Step 1.2: Change timeout constant

Modify `backend/app/services/poll_repo.py` line 10:

```python
POLL_TIMEOUT_MINUTES = 5
```

### Step 1.3: Update display text

Modify `backend/app/bot/handlers/lunch.py` line 47. Change:

```python
f"⏱ Vote within 10 min | Votes: {total_votes}",
```

to:

```python
f"⏱ Vote within 5 min | Votes: {total_votes}",
```

### Step 1.4: Run tests — should pass

```bash
cd backend && pytest tests/unit/test_lunch_poll.py -v
```

Expected: all green.

### Step 1.5: Commit

```bash
git add backend/app/services/poll_repo.py \
        backend/app/bot/handlers/lunch.py \
        backend/tests/unit/test_lunch_poll.py
git commit -m "feat: reduce poll timeout from 10 to 5 minutes

Shorter timeout keeps lunch decisions quick. Also updates the
display text to match the actual timeout duration."
```

---

## Task 2: Add background poll expiry checker to FastAPI lifespan

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/bot/poll_timeout.py` (needs to accept Application or work standalone)
- Create: `backend/tests/unit/test_poll_timeout.py`

### Step 2.1: Write failing test for the background task

Create `backend/tests/unit/test_poll_timeout.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.bot.poll_timeout import check_expired_polls, poll_expiry_loop


@pytest.mark.asyncio
async def test_poll_expiry_loop_calls_check():
    """poll_expiry_loop should call check_expired_polls at least once."""
    with patch("app.bot.poll_timeout.check_expired_polls", new_callable=AsyncMock) as mock_check:
        task = asyncio.create_task(poll_expiry_loop())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        mock_check.assert_called()
```

Run: `cd backend && pytest tests/unit/test_poll_timeout.py -v`

Expected: **FAIL** — `poll_expiry_loop` does not exist.

### Step 2.2: Add `poll_expiry_loop` to `poll_timeout.py`

Add to `backend/app/bot/poll_timeout.py` after the existing code:

```python
import asyncio

POLL_CHECK_INTERVAL_SECONDS = 60


async def poll_expiry_loop() -> None:
    while True:
        try:
            application = await get_application()
            await check_expired_polls(application)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error in poll expiry loop")
        await asyncio.sleep(POLL_CHECK_INTERVAL_SECONDS)
```

Add the import at the top:

```python
from app.bot.application import get_application
```

### Step 2.3: Run poll_timeout tests — should pass

```bash
cd backend && pytest tests/unit/test_poll_timeout.py -v
```

### Step 2.4: Write failing test for FastAPI lifespan starting the background task

Add to `backend/tests/unit/test_poll_timeout.py`:

```python
from fastapi.testclient import TestClient


def test_lifespan_starts_poll_expiry_loop():
    """FastAPI app lifespan should start the poll expiry background task."""
    with patch("app.main.poll_expiry_loop", new_callable=AsyncMock) as mock_loop:
        from app.main import app
        with TestClient(app):
            pass
        # The lifespan should have created a task for poll_expiry_loop
```

### Step 2.5: Add lifespan to FastAPI app

Modify `backend/app/main.py`. Add a lifespan context manager that starts the background task:

```python
import asyncio
from contextlib import asynccontextmanager

from app.bot.poll_timeout import poll_expiry_loop


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(poll_expiry_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Pick API", version="0.1.0", lifespan=lifespan)
```

### Step 2.6: Run all tests — should pass

```bash
cd backend && pytest -q
```

Expected: all green.

### Step 2.7: Commit

```bash
git add backend/app/main.py \
        backend/app/bot/poll_timeout.py \
        backend/tests/unit/test_poll_timeout.py
git commit -m "fix: add poll expiry background task to production webhook mode

check_expired_polls only ran in run_polling.py (dev mode). Production
uses uvicorn with FastAPI webhook, which had no background loop to
close expired polls. Added poll_expiry_loop as a lifespan background
task so polls auto-close in production."
```

---

## Task 3: Update docs

**Files:**
- Modify: `backend/STRUCTURE.md`
- Modify: `tasks/INDEX.md`

### Step 3.1: Update STRUCTURE.md

Update the `poll_timeout.py` description line to mention the lifespan background task:

```
│   │   ├── poll_timeout.py       # Poll expiry checker + background loop (runs in FastAPI lifespan)
```

Update test counts for `test_lunch_poll.py` and add `test_poll_timeout.py`.

### Step 3.2: Update tasks/INDEX.md

Add task 021 to Phase 6:

```markdown
- [ ] [021 — Fix Poll Timeout in Production](./021-fix-poll-timeout-production.md)
```

Update status summary.

### Step 3.3: Commit

```bash
git add backend/STRUCTURE.md tasks/INDEX.md
git commit -m "docs: add task 021 and update structure for poll timeout fix"
```

### Step 3.4: Run full test suite

```bash
cd backend && pytest -q
```

Expected: all green.

### Step 3.5: STOP — wait for user review before opening PR.

---

## Acceptance Criteria

- [ ] `POLL_TIMEOUT_MINUTES` is 5 (not 10)
- [ ] Poll display text says "Vote within 5 min"
- [ ] `poll_expiry_loop` runs as a FastAPI lifespan background task in production
- [ ] `run_polling.py` dev mode still works (keeps its own loop)
- [ ] All backend tests pass
- [ ] STRUCTURE.md and INDEX.md updated

---

## Risk / Rollback

- If the lifespan task causes issues, it can be removed from `main.py` without affecting any other functionality.
- The `run_polling.py` dev loop is unchanged, so local development is unaffected.
