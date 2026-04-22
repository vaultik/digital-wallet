# app/models/transaction.py
import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, ForeignKey,
    Index, Numeric, String, UUID,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship
)

from app.core.constants import (
    CRYPTO_PRECISION, CRYPTO_SCALE, STR_MINI
)
from app.models.base import Base, IdTimeMixin


class Transaction(IdTimeMixin, Base):
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            'idempotency_records.id',
            name='fk_transaction_idempotency_key'
        ),
        index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        default=uuid.uuid4,
        index=True
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('wallet.id', name='fk_transaction_wallet_id'),
        index=True
    )
    entry_type: Mapped[str] = mapped_column(String(STR_MINI))
    amount: Mapped[Decimal] = mapped_column(
        Numeric(CRYPTO_PRECISION, CRYPTO_SCALE)
    )
    transaction_type: Mapped[str] = mapped_column(String(STR_MINI))
    rate: Mapped[Decimal | None] = mapped_column(
        Numeric(CRYPTO_PRECISION, CRYPTO_SCALE)
    )

    wallet: Mapped['Wallet'] = relationship(
        back_populates='transactions',
        lazy='joined'
    )

    __table_args__ = (
        CheckConstraint(
            'amount >= 0',
            name='check_positive_balance'
        ),
        CheckConstraint(
            "entry_type IN ('DEBIT', 'CREDIT')",
            name='check_valid_entry_type'
        ),
        CheckConstraint(
            "transaction_type IN ('STRIPE', 'LOCAL')",
            name='check_valid_transaction_type'
        )
    )


class IdempotencyRecord(IdTimeMixin, Base):
    __tablename__ = 'idempotency_records'

    key: Mapped[uuid.UUID] = mapped_column(UUID, unique=True)
    response_body: Mapped[dict] = mapped_column(JSONB)
    response_status: Mapped[int] = mapped_column()
