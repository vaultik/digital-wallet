# app/repositories/idempotency_repository.py
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.exceptions import InvalidRequestHashError
from app.models import IdempotencyRecord


class IdempotencyRepository:
    """
    Guards financial operations against duplicate execution.

    A key is claimed before the operation runs, so the unique constraint
    on (user_id, key) serializes concurrent requests carrying the same key.
    The stored response is replayed on retries.
    """

    def __init__(self, db: AsyncSession = Depends(get_async_session)):
        self._db = db

    async def claim(
            self,
            key: UUID,
            user_id: UUID,
            request_hash: str,
    ) -> tuple[IdempotencyRecord, bool]:
        """
        Reserve the key for this operation.

        Returns (record, True) when the key was free, (record, False) when
        the same request was already processed.
        """
        record = IdempotencyRecord(
            key=key,
            user_id=user_id,
            request_hash=request_hash,
        )
        try:
            async with self._db.begin_nested():
                self._db.add(record)
                await self._db.flush()
            return record, True
        except IntegrityError:
            result = await self._db.execute(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.key == key,
                    IdempotencyRecord.user_id == user_id,
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                raise
            if record.request_hash != request_hash:
                raise InvalidRequestHashError(
                    'Idempotency key already used '
                    'with different request parameters'
                )
            return record, False

    async def save_response(
            self,
            record: IdempotencyRecord,
            status: int,
            body: dict,
    ) -> None:
        """Attach the operation's response to a claimed record."""
        record.response_status = status
        record.response_body = body
