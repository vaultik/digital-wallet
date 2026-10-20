# tests/integration/test_repositories.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WebhookIdempotencyRecord
from app.repositories import WebhookIdempotencyRepository


async def test_register_event_new(db_session: AsyncSession):
    """A previously unseen event id is registered."""
    repo = WebhookIdempotencyRepository(db_session)
    assert await repo.register_event('evt_test_1') is True

    webhook_records = (await db_session.execute(
        select(WebhookIdempotencyRecord)
    )).scalars().all()
    assert len(webhook_records) == 1


async def test_register_event_duplicate(db_session: AsyncSession):
    """Re-delivering the same event is rejected without a second record."""
    repo = WebhookIdempotencyRepository(db_session)
    assert await repo.register_event('evt_test_2') is True
    assert await repo.register_event('evt_test_2') is False

    webhook_records = (await db_session.execute(
        select(WebhookIdempotencyRecord)
    )).scalars().all()
    assert len(webhook_records) == 1


async def test_register_event_duplicate_keeps_session_usable(
        db_session: AsyncSession
):
    """A rejected duplicate must not poison the surrounding transaction."""

    repo = WebhookIdempotencyRepository(db_session)
    await repo.register_event('evt_poison')
    assert await repo.register_event('evt_poison') is False

    assert await repo.register_event('evt_after_failure') is True

    webhook_records = (await db_session.execute(
        select(WebhookIdempotencyRecord)
    )).scalars().all()
    assert len(webhook_records) == 2
