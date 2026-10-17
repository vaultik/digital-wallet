# app/models/idempotency.py
import uuid

from sqlalchemy import String, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import STR_MED
from app.models.base import Base, IdTimeMixin


class IdempotencyRecord(IdTimeMixin, Base):
    """
    Stores request/response pairs to prevent duplicate financial operations.
    """

    __tablename__ = 'idempotency_records'

    key: Mapped[uuid.UUID] = mapped_column(UUID)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('user.id', name='fk_idempotency_user_id')
    )
    request_hash: Mapped[str] = mapped_column(String(64))
    response_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_status: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'key',
            name='uq_idempotency_user_key'
        ),
    )


class WebhookIdempotencyRecord(IdTimeMixin, Base):
    """
    Store key to prevent duplicate webhook signature.
    """

    __tablename__ = 'webhook_idempotency_records'

    stripe_event_id: Mapped[str] = mapped_column(String(STR_MED), unique=True)
