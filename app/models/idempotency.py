# app/models/idempotency.py
import uuid

from sqlalchemy import String, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import STR_MED
from app.models.base import Base, IdTimeMixin


class IdempotencyRecord(IdTimeMixin, Base):
    """
    Stores request/response pairs to prevent duplicate financial operations.
    """

    __tablename__ = 'idempotency_records'

    key: Mapped[uuid.UUID] = mapped_column(UUID, unique=True)
    response_body: Mapped[dict] = mapped_column(JSONB)
    response_status: Mapped[int] = mapped_column()


class WebhookIdempotencyRecord(IdTimeMixin, Base):
    """
    Store key to prevent duplicate webhook signature.
    """

    __tablename__ = 'webhook_idempotency_records'

    stripe_event_id: Mapped[str] = mapped_column(String(STR_MED), unique=True)
