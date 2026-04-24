import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_poll_expiry_loop_calls_check():
    with (
        patch("app.bot.poll_timeout.check_expired_polls", new_callable=AsyncMock) as mock_check,
        patch("app.bot.poll_timeout.get_application", new_callable=AsyncMock) as mock_get_app,
    ):
        from app.bot.poll_timeout import poll_expiry_loop

        task = asyncio.create_task(poll_expiry_loop())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        mock_check.assert_called()


@pytest.mark.asyncio
async def test_poll_expiry_loop_handles_errors():
    call_count = 0

    async def check_side_effect(*args):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("DB error")

    with (
        patch("app.bot.poll_timeout.check_expired_polls", side_effect=check_side_effect) as mock_check,
        patch("app.bot.poll_timeout.get_application", new_callable=AsyncMock) as mock_get_app,
        patch("app.bot.poll_timeout.POLL_CHECK_INTERVAL_SECONDS", 0.01),
    ):
        from app.bot.poll_timeout import poll_expiry_loop

        task = asyncio.create_task(poll_expiry_loop())
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert call_count >= 2
