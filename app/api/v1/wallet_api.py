# app/api/v1/wallet_api.py
from uuid import UUID

from fastapi import (
    APIRouter, Depends, Header,
)

from app.api.dependencies import get_current_user
from app.models import User
from app.schemas.wallet_schemas import (
    WalletCreate,
    TransferCreate,
    TransferResponse,
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
        idempotency_key: UUID = Header(..., alias='Idempotency-Key')
) -> TransferResponse:
    """
    Execute an atomic P2P transfer between two wallets of the same currency.
    """
    return await service.transfer(
        current_user_id=current_user.id,
        data=data
    )
