# app/services/auth_service.py
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EntryType, TransactionType
from app.core.db import get_async_session
from app.core.exceptions import (
    InvalidWalletsDataError,
    WalletAlreadyExistsError,
    WalletNotFoundError
)
from app.repositories import (
    TransactionRepository,
    WalletRepository
)
from app.schemas.wallet_schemas import (
    TransferCreate,
    TransferResponse,
    WalletCreate,
    WalletListResponse,
    WalletResponse,
)

class WalletService:

    def __init__(
            self,
            wallet_repo: WalletRepository = Depends(),
            transaction_repo: TransactionRepository = Depends(),
            db: AsyncSession = Depends(get_async_session),
    ):
        self.wallet_repo = wallet_repo
        self.transaction_repo = transaction_repo
        self._db = db

    async def create_wallet(
            self, user_id: UUID, data: WalletCreate
    ) -> WalletResponse:
        """
        Create a new wallet for the user. Raise 409 if currency wallet already exists.
        """
        wallet = await self.wallet_repo.get_by_user_and_currency(
                user_id, data.currency
        )
        if wallet is not None:
            raise WalletAlreadyExistsError('Wallet already exist')
        wallet = await self.wallet_repo.create(user_id, data.currency)
        await self._db.commit()
        await self._db.refresh(wallet)
        return WalletResponse.model_validate(wallet)

    async def get_wallet(
            self, wallet_id: UUID, current_user_id: UUID
    ) -> WalletResponse:
        """
        Return wallet by ID. Raise 404 if not found or belongs to another user.
        """
        wallet = await self.wallet_repo.get_by_id(wallet_id)
        if wallet is None or wallet.user_id != current_user_id:
            raise WalletNotFoundError('Wallet not found')
        return WalletResponse.model_validate(wallet)

    async def get_wallets(
            self, user_id: UUID, limit: int, offset: int
    ) -> WalletListResponse:
        """Return paginated list of wallets owned by the user."""
        wallets, total = await self.wallet_repo.get_all_by_user(
            user_id, limit, offset
        )
        return WalletListResponse(
            items=wallets,
            total=total,
            limit=limit,
            offset=offset
        )

    async def transfer(
            self, current_user_id: UUID, data: TransferCreate
    ) -> TransferResponse:
        """
        Execute P2P transfer between two wallets atomically.

        Uses SELECT FOR UPDATE with lock ordering to prevent race conditions.
        Creates double-entry bookkeeping records (DEBIT + CREDIT) linked by group_id.
        """
        sender_wallet = await self.wallet_repo.get_by_id(data.sender_wallet_id)
        if sender_wallet is None or sender_wallet.user_id != current_user_id:
            raise WalletNotFoundError('Wallet not found')
        receiver_wallet = await self.wallet_repo.get_by_id(data.receiver_wallet_id)
        if receiver_wallet is None:
            raise WalletNotFoundError('Wallet not found')
        if sender_wallet.user_id == receiver_wallet.user_id:
            raise InvalidWalletsDataError('You cannot send it to yourself')
        if sender_wallet.currency != receiver_wallet.currency:
            raise InvalidWalletsDataError('The currency does not match')

        wallets = await self.wallet_repo.get_wallets_for_update([
            sender_wallet.id, receiver_wallet.id
        ])
        if len(wallets) != 2:
            raise WalletNotFoundError('Wallet not found')
        if sender_wallet.id < receiver_wallet.id:
            sender_wallet, receiver_wallet = wallets
        else:
            receiver_wallet, sender_wallet = wallets
        if sender_wallet.balance < data.amount:
            raise InvalidWalletsDataError('The amount is insufficient')

        sender_wallet.balance -= data.amount
        receiver_wallet.balance += data.amount

        group_id = uuid4()
        transaction_sender = await self.transaction_repo.create_entry(
            wallet_id=sender_wallet.id,
            entry_type=EntryType.DEBIT,
            amount=data.amount,
            group_id=group_id,
            transaction_type=TransactionType.LOCAL
        )
        transaction_receiver = await self.transaction_repo.create_entry(
            wallet_id=receiver_wallet.id,
            entry_type=EntryType.CREDIT,
            amount=data.amount,
            group_id=group_id,
            transaction_type=TransactionType.LOCAL
        )
        await self._db.flush()
        await self._db.commit()
        await self._db.refresh(transaction_sender)

        return TransferResponse(
            group_id=group_id,
            sender_balance=sender_wallet.balance,
            currency=sender_wallet.currency,
            created_at=transaction_sender.created_at
        )
