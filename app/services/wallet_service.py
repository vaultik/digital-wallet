# app/services/wallet_service.py
import logging
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    SYSTEM_USER_ID,
    EntryType,
    TransactionType,
)
from app.core.db import get_async_session
from app.core.exceptions import (
    InvalidWalletsDataError,
    WalletAlreadyExistsError,
    WalletNotFoundError
)
from app.models import Transaction, Wallet
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

logger = logging.getLogger(__name__)


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
        """
        Return paginated list of wallets owned by the user.
        """
        wallets, total = await self.wallet_repo.get_all_by_user(
            user_id, limit, offset
        )
        return WalletListResponse(
            items=wallets,
            total=total,
            limit=limit,
            offset=offset
        )

    async def get_or_create_wallet(
            self, user_id: UUID, currency: str, is_system: bool = False
    ) -> Wallet:
        """
        Return the user's wallet for the given currency, creating it if missing.

        Pass is_system=True only for the internal clearing wallet used for
        external (Stripe) deposits.
        """
        wallet = await self.wallet_repo.get_by_user_and_currency(
            user_id, currency
        )
        if wallet is not None:
            return wallet
        return await self.wallet_repo.create(user_id, currency, is_system)

    async def _lock_and_apply_double_entry(
            self,
            debit_wallet_id: UUID,
            credit_wallet_id: UUID,
            amount: Decimal,
            transaction_type: str,
    ) -> tuple[Wallet, Wallet, UUID, Transaction]:
        """
        Lock both wallets (deadlock-safe order), adjust balances,
        and create the DEBIT/CREDIT ledger pair. Caller commits.
        """
        wallets = await self.wallet_repo.get_wallets_for_update([
            debit_wallet_id, credit_wallet_id
        ])
        if len(wallets) != 2:
            raise WalletNotFoundError('Wallet not found')

        wallets_by_id = {wallet.id: wallet for wallet in wallets}
        sender_wallet = wallets_by_id[debit_wallet_id]
        receiver_wallet = wallets_by_id[credit_wallet_id]

        if not sender_wallet.is_system and sender_wallet.balance < amount:
            raise InvalidWalletsDataError('The amount is insufficient')

        sender_wallet.balance -= amount
        receiver_wallet.balance += amount

        group_id = uuid4()
        transaction_sender = await self.transaction_repo.create_entry(
            wallet_id=sender_wallet.id,
            entry_type=EntryType.DEBIT,
            amount=amount,
            group_id=group_id,
            transaction_type=transaction_type
        )
        transaction_receiver = await self.transaction_repo.create_entry(
            wallet_id=receiver_wallet.id,
            entry_type=EntryType.CREDIT,
            amount=amount,
            group_id=group_id,
            transaction_type=transaction_type
        )
        return sender_wallet, receiver_wallet, group_id, transaction_sender

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

        sender_wallet, receiver_wallet, group_id, transaction_sender = (
            await self._lock_and_apply_double_entry(
                debit_wallet_id=sender_wallet.id,
                credit_wallet_id=receiver_wallet.id,
                amount=data.amount,
                transaction_type=TransactionType.LOCAL,
            )
        )
        await self._db.commit()
        await self._db.refresh(transaction_sender)

        return TransferResponse(
            group_id=group_id,
            sender_balance=sender_wallet.balance,
            currency=sender_wallet.currency,
            created_at=transaction_sender.created_at
        )

    async def credit_external_deposit(
            self, wallet_id: UUID, amount: Decimal, currency: str
    ) -> None:
        """
        Credit external funds (e.g. Stripe deposit) to a user's wallet.

        Debits the system clearing wallet, credits the user wallet.
        """
        user_wallet = await self.wallet_repo.get_by_id(wallet_id=wallet_id)
        if not user_wallet:
            logger.warning('User Wallet not found')
            raise WalletNotFoundError('Wallet not found')
        system_wallet = await self.get_or_create_wallet(
            SYSTEM_USER_ID, currency, is_system=True
        )
        if not system_wallet:
            logger.error('System Wallet not found')
            raise WalletNotFoundError('Wallet not found')
        if user_wallet.currency != system_wallet.currency:
            raise InvalidWalletsDataError('The currency does not match')

        await self._lock_and_apply_double_entry(
            debit_wallet_id=system_wallet.id,
            credit_wallet_id=user_wallet.id,
            amount=amount,
            transaction_type=TransactionType.STRIPE,
        )
        await self._db.commit()
