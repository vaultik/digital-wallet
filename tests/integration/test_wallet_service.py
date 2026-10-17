# tests/integration/test_wallet_service.py
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.core.exceptions import (
    InvalidWalletsDataError,
    WalletNotFoundError,
)
from app.models import Transaction, Wallet
from app.services import WalletService
from tests.helpers import assert_double_entry


async def test_credit_external_deposit_happy_path(
        db_session: AsyncSession,
        wallet_service: WalletService,
        deposit_wallet: Wallet,
):
    """
    Depositing external funds credits the user and debits the system wallet.
    """
    await wallet_service.credit_external_deposit(
        wallet_id=deposit_wallet.id,
        amount=Decimal('100.00'),
        currency='EUR',
    )
    assert deposit_wallet.balance == Decimal('100.00')

    system_wallets = (await db_session.execute(
        select(Wallet).where(Wallet.is_system)
    )).scalars().all()
    assert len(system_wallets) == 1
    system_wallet = system_wallets[0]
    assert system_wallet.currency == 'EUR'
    assert system_wallet.balance == Decimal('-100.00')

    entries = (
        await db_session.execute(select(Transaction))
    ).scalars().all()
    assert len(entries) == 2

    await assert_double_entry(
        session=db_session,
        group_id=entries[0].group_id,
        debit_wallet_id=system_wallet.id,
        credit_wallet_id=deposit_wallet.id,
        amount=Decimal('100.00'),
        transaction_type=TransactionType.STRIPE,
    )


async def test_credit_external_deposit_reuses_system_wallet(
        db_session: AsyncSession,
        wallet_service: WalletService,
        deposit_wallet: Wallet,
):
    """
    A second deposit debits the same system wallet instead of creating one.
    """
    await wallet_service.credit_external_deposit(
        wallet_id=deposit_wallet.id,
        amount=Decimal('100.00'),
        currency='EUR'
    )
    await wallet_service.credit_external_deposit(
        wallet_id=deposit_wallet.id,
        amount=Decimal('100.00'),
        currency='EUR'
    )
    system_wallets = (
        await db_session.execute(select(Wallet).where(Wallet.is_system))
    ).scalars().all()
    assert len(system_wallets) == 1
    assert system_wallets[0].balance == Decimal('-200.00')
    assert deposit_wallet.balance == Decimal('200.00')

    entries = (
        await db_session.execute(select(Transaction))
    ).scalars().all()
    assert len(entries) == 4


async def test_credit_external_deposit_unknown_wallet(
        wallet_service: WalletService,
):
    """Depositing into a missing wallet raises WalletNotFoundError."""
    with pytest.raises(WalletNotFoundError):
        await wallet_service.credit_external_deposit(
            wallet_id=uuid4(),
            amount=Decimal('100.00'),
            currency='EUR'
        )


async def test_credit_external_deposit_currency_mismatch(
        db_session: AsyncSession,
        wallet_service: WalletService,
        deposit_wallet: Wallet,
):
    """Currency that does not match the wallet is rejected."""
    with pytest.raises(InvalidWalletsDataError):
        await wallet_service.credit_external_deposit(
            wallet_id=deposit_wallet.id,
            amount=Decimal('100.00'),
            currency='USD'
        )

    system_wallets = (
        await db_session.execute(select(Wallet).where(Wallet.is_system))
    ).scalars().all()
    assert system_wallets == []
