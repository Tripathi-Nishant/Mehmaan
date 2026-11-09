import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_jobs_once() -> None:
    from app.config import get_settings
    from app.db.session import session_factory
    from app.jobs.actions import (
        complete_due_bookings,
        expire_host_replies,
        expire_unpaid_holds,
        schedule_completed_payouts,
        send_due_mock_payouts,
    )
    from app.notifications.email import send_pending_emails

    async with session_factory() as session:
        await expire_unpaid_holds(session)
        await expire_host_replies(session)
        await complete_due_bookings(session)
        await schedule_completed_payouts(session)
        await send_due_mock_payouts(session)
        await send_pending_emails(session, get_settings())
    logger.debug("Mehmaan background jobs tick")


async def scheduler_loop(interval_seconds: int = 30) -> None:
    while True:
        await run_jobs_once()
        await asyncio.sleep(interval_seconds)
