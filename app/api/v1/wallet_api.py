# app/api/v1/wallet_api.py
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_idempotency_guard,
)
from app.core.db import get_async_session
from app.core.idempotency_guard import IdempotencyGuard
from app.models import User
from app.schemas.wallet_schemas import (
    TransferCreate,
    TransferResponse,
    WalletCreate,
    WalletListResponse,
    WalletResponse,
)
from app.services import WalletService

router = APIRouter(prefix='/wallets', tags=['wallet'])


@router.post(
    '',
    response_model=WalletResponse,
    status_code=201
)
async def create_wallet(
        data: WalletCreate,
        current_user: User = Depends(get_current_user),
        service: WalletService = Depends()
) -> WalletResponse:
    """Create a new currency wallet for the authenticated user."""
    return await service.create_wallet(
        user_id=current_user.id,
        data=data
    )


@router.get(
    '',
    response_model=WalletListResponse,
    status_code=200
)
async def get_wallets(
        limit: int = 20,
        offset: int = 0,
        current_user: User = Depends(get_current_user),
        service: WalletService = Depends()
) -> WalletListResponse:
    """Return paginated list of wallets owned by the authenticated user."""
    return await service.get_wallets(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )


@router.get(
    '/{wallet_id}',
    response_model=WalletResponse,
    status_code=200
)
async def get_wallet(
        wallet_id: UUID,
        current_user: User = Depends(get_current_user),
        service: WalletService = Depends()
) -> WalletResponse:
    """
    Return a single wallet by ID. Returns 404 for foreign or missing wallets.
    """
    return await service.get_wallet(
        wallet_id=wallet_id,
        current_user_id=current_user.id
    )


@router.post(
    '/transfer',
    response_model=TransferResponse,
    status_code=200
)
async def transfer(
        data: TransferCreate,
        current_user: User = Depends(get_current_user),
        service: WalletService = Depends(),
        guard: IdempotencyGuard = Depends(get_idempotency_guard),
        db: AsyncSession = Depends(get_async_session),
) -> TransferResponse:
    """
    Execute an atomic P2P transfer between two wallets of the same currency.
    """
    stored, is_new = await guard.claim(data)
    if not is_new:
        return stored

    result = await service.transfer(
        current_user_id=current_user.id,
        data=data
    )
    await guard.save(result)
    await db.commit()
    return result
