# tests/integration/test_wallet_service.py
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
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

    system_wallet = (await db_session.execute(
        select(Wallet).where(Wallet.is_system)
    )).scalars().all()
    assert len(system_wallet) == 1
    system_wallet = system_wallet[0]
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
