# app/repositories/webhook_idempotency_repository.py
from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.models import WebhookIdempotencyRecord


class WebhookIdempotencyRepository:
    """
    Tracks processed Stripe webhook event IDs to prevent duplicate deposit crediting.
    """

    def __init__(self, db: AsyncSession = Depends(get_async_session)):
        self._db = db

    async def register_event(self, stripe_event_id: str) -> bool:
        """
        Try to atomically register a webhook event.

        Returns True if newly registered,
        False if already processed (duplicate).
        """
        try:
            async with self._db.begin_nested():
                self._db.add(
                    WebhookIdempotencyRecord(stripe_event_id=stripe_event_id)
                )
                await self._db.flush()
            return True
        except IntegrityError:
            return False
