# app/models/wallet.py
import uuid
from datetime import datetime as dt
from decimal import Decimal
from typing import List

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    Numeric, SmallInteger, String, UniqueConstraint, func
)
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship
)

from app.core.constants import (
    CRYPTO_PRECISION, CRYPTO_SCALE,
    STR_MINI, STR_SHORT
)
from app.models.base import Base, IdTimeMixin


class Wallet(IdTimeMixin, Base):
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('user.id', name='fk_wallet_user_id'),
        index=True,
    )
    currency: Mapped[str] = mapped_column(
        ForeignKey('currency.code', name='fk_wallet_currency_code')
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(CRYPTO_PRECISION, CRYPTO_SCALE),
        default=Decimal('0'),
        server_default='0'
    )

    user: Mapped['User'] = relationship(
        back_populates='wallets',
        lazy = 'joined',
    )
    transactions: Mapped[List['Transaction']] = relationship(
        back_populates='wallet',
        lazy='select',
    )
    currency_info: Mapped['Currency'] = relationship(
        back_populates='wallets',
        lazy='joined'
    )

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'currency',
            name='uq_currency_user'
        ),
        CheckConstraint(
            'balance >= 0',
            name='check_positive_balance'
        ),
    )


class Currency(Base):
    code: Mapped[str] = mapped_column(
        String(STR_MINI), primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(STR_SHORT)
    )
    decimals: Mapped[int] = mapped_column(
        SmallInteger, default=2
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    is_fiat: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    created_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        index=True,
        server_default=func.timezone('utc', func.now())
    )
    updated_at: Mapped[dt] = mapped_column(
        DateTime(timezone=True),
        index=True,
        server_default=func.timezone('utc', func.now()),
        onupdate=func.now()
    )

    wallets: Mapped[List['Wallet']] = relationship(
        back_populates='currency_info',
        lazy='select'
    )

    __table_args__ = (
        CheckConstraint(
            'decimals >= 0',
            name='check_positive_decimals'
        ),
    )
