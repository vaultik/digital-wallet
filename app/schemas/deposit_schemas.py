# app/schemas/deposit_schemas.py
from pydantic import BaseModel

from app.core.constants import (
    POSITIVE_DECIMAL,
    CORRECTLY_CURRENCY
)


class DepositCreate(BaseModel):
    currency: CORRECTLY_CURRENCY
    amount: POSITIVE_DECIMAL


class DepositResponse(BaseModel):
    deposit_url: str
