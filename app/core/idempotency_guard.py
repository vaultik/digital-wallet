# app/core/idempotency_guard.py
import hashlib
import json
from uuid import UUID

from pydantic import BaseModel

from app.models import IdempotencyRecord
from app.repositories import IdempotencyRepository


class IdempotencyGuard:
    """
    Per-request helper that makes an operation safe to retry.

    The router claims the key before running the operation and saves the
    response afterwards; both happen inside the operation's transaction.
    """

    def __init__(
            self,
            key: UUID,
            user_id: UUID,
            repo: IdempotencyRepository,
    ):
        self._key = key
        self._user_id = user_id
        self._repo = repo
        self._record: IdempotencyRecord | None = None

    async def claim(self, request_model: BaseModel) -> tuple[dict | None, bool]:
        """
        Reserve the key for this request.

        Returns (None, True) when the operation should run, or
        (stored_body, False) when it already did.
        """
        record, is_new = await self._repo.claim(
            self._key, self._user_id, self._request_hash(request_model)
        )
        self._record = record
        if is_new:
            return None, True
        return record.response_body, False

    async def save(self, response_model: BaseModel, status: int = 200) -> None:
        """Store the operation's response on the claimed record."""
        if self._record is None:
            raise RuntimeError('save() called before claim()')
        await self._repo.save_response(
            record=self._record,
            status=status,
            body=response_model.model_dump(mode='json'),
        )

    @staticmethod
    def _request_hash(request_model: BaseModel) -> str:
        """Return a stable hash of the request payload."""
        dump = json.dumps(
            request_model.model_dump(mode='json'), sort_keys=True
        ).encode()
        return hashlib.sha256(dump).hexdigest()
