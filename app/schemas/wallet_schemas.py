# app/schemas/auth_schemas.py
from datetime import datetime as dt
from decimal import Decimal
from typing import Annotated, List
from uuid import UUID

from pydantic import (
    BaseModel, ConfigDict, Field, UUID4
)

from app.core.constants import (
    POSITIVE_DECIMAL,
    POSITIVE_AND_NULL_DECIMAL,
    CORRECTLY_CURRENCY
)


class WalletBaseModel(BaseModel):
    """
    Base model with ORM mode enabled for all wallet response schemas.
    """
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class WalletCreate(BaseModel):
    """Request body for wallet creation."""
    currency: CORRECTLY_CURRENCY


class WalletResponse(WalletBaseModel):
    """Single wallet representation returned to the client."""
    currency: CORRECTLY_CURRENCY
    wallet_id: UUID4 = Field(serialization_alias='wallet_id', alias='id')
    balance: POSITIVE_AND_NULL_DECIMAL
    created_at: dt = Field(default_factory=dt.utcnow)


class WalletListResponse(WalletBaseModel):
    """Paginated list of wallets."""
    items: List[WalletResponse]
    total: int
    limit: int = 20
    offset: int = 0


class TransferCreate(BaseModel):
    """Request body for P2P transfer between two wallets."""
    sender_wallet_id: UUID
    receiver_wallet_id: UUID
    amount: POSITIVE_DECIMAL


class TransferResponse(WalletBaseModel):
    """Transfer result returned to the sender."""
    group_id: UUID4
    sender_balance: POSITIVE_AND_NULL_DECIMAL
    currency: CORRECTLY_CURRENCY
    created_at: dt = Field(default_factory=dt.utcnow)
