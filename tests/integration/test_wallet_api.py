# tests/integration/test_wallet_api.py
from decimal import Decimal
from http import HTTPStatus
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import TransactionType
from app.models import (
    IdempotencyRecord,
    Transaction,
    Wallet,
)
from tests.helpers import assert_double_entry

NONEXISTENT_WALLET_ID = '00000000-0000-0000-0000-000000000000'


# POST /wallets
async def test_create_wallet_success(auth_client: AsyncClient):
    """
    Return 201 with wallet data including currency and generated wallet_id.
    """
    response = await auth_client.post(
        '/api/v1/wallets',
        json={'currency': 'USD'}
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['currency'] == 'USD'


async def test_create_wallet_duplicate(auth_client: AsyncClient):
    """
    Return 409 when user attempts to create second wallet in same currency.
    """
    await auth_client.post('/api/v1/wallets', json={'currency': 'USD'})
    response = await auth_client.post(
        '/api/v1/wallets',
        json={'currency': 'USD'}
    )
    assert response.status_code == HTTPStatus.CONFLICT


async def test_create_wallet_unauthorized(async_client: AsyncClient):
    response = await async_client.post(
        '/api/v1/wallets',
        json={'currency': 'USD'}
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# GET /wallets
async def test_get_wallets_empty(auth_client: AsyncClient):
    """Return 200 with empty items list for user with no wallets."""
    response = await auth_client.get('/api/v1/wallets')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['items'] == []
    assert response.json()['total'] == 0


async def test_get_wallets_with_data(
        user_with_wallet: tuple[AsyncClient, str]
):
    client, wallet_id = user_with_wallet
    response = await client.get('/api/v1/wallets')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()['items']) == 1
    assert response.json()['total'] == 1


async def test_get_wallets_unauthorized(async_client: AsyncClient):
    response = await async_client.get('/api/v1/wallets')
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# GET /wallets/{id}
async def test_get_wallet(
        user_with_wallet: tuple[AsyncClient, str]
):
    client, wallet_id = user_with_wallet
    response = await client.get(f'/api/v1/wallets/{wallet_id}')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['wallet_id'] == wallet_id


async def test_get_wallet_not_found(auth_client: AsyncClient):
    """Return 404 for non-existent wallet ID regardless of ownership."""
    response = await auth_client.get(
        f'/api/v1/wallets/{NONEXISTENT_WALLET_ID}'
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_get_wallet_unauthorized(async_client: AsyncClient):
    response = await async_client.get(
        f'/api/v1/wallets/{NONEXISTENT_WALLET_ID}'
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# POST /wallets/transfer
async def test_transfer_success(
        db_session: AsyncSession,
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str],
):
    """Successful P2P transfer returns 200 and updated sender balance."""
    client1, wallet_id1, client2, wallet_id2 = funded_wallets
    response = await client1.post(
        '/api/v1/wallets/transfer',
        json={
            'sender_wallet_id': wallet_id1,
            'receiver_wallet_id': wallet_id2,
            'amount': '100.00'
        },
        headers={'Idempotency-Key': str(uuid4())}
    )
    assert response.status_code == HTTPStatus.OK
    assert Decimal(response.json()['sender_balance']) == Decimal('900')
    await assert_double_entry(
        session=db_session,
        group_id=UUID(response.json()['group_id']),
        debit_wallet_id=UUID(wallet_id1),
        credit_wallet_id=UUID(wallet_id2),
        amount=Decimal('100.00'),
        transaction_type=TransactionType.LOCAL,
    )
    receiver = await db_session.get(Wallet, UUID(wallet_id2))
    assert receiver.balance == Decimal('100.00')


async def test_transfer_insufficient_funds(
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str]
):
    """Transfer exceeding balance returns 400 Bad Request."""
    client1, wallet_id1, client2, wallet_id2 = funded_wallets
    response = await client2.post(
        '/api/v1/wallets/transfer',
        json={
            'sender_wallet_id': wallet_id2,
            'receiver_wallet_id': wallet_id1,
            'amount': '100.00'
        },
        headers={'Idempotency-Key': str(uuid4())}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_transfer_to_self(
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str]
):
    """Transfer to own wallet returns 400 Bad Request."""
    client1, wallet_id1, client2, wallet_id2 = funded_wallets
    response = await client1.post(
        '/api/v1/wallets/transfer',
        json={
            'sender_wallet_id': wallet_id1,
            'receiver_wallet_id': wallet_id1,
            'amount': '100.00'
        },
        headers={'Idempotency-Key': str(uuid4())}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_transfer_different_currencies(
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str],
        third_user_with_wallet_diff_currency: tuple[AsyncClient, str]
):
    """Transfer between wallets with different currencies returns 400."""
    client1, wallet_id1, client2, wallet_id2 = funded_wallets
    client3, wallet_id3 = third_user_with_wallet_diff_currency
    response = await client1.post(
        '/api/v1/wallets/transfer',
        json={
            'sender_wallet_id': wallet_id1,
            'receiver_wallet_id': wallet_id3,
            'amount': '100.00'
        },
        headers={'Idempotency-Key': str(uuid4())}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_transfer_wallet_not_found(
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str],
):
    """Transfer to non-existent wallet returns 404 Not Found."""
    client1, wallet_id1, client2, wallet_id2 = funded_wallets
    fake_id = str(uuid4())
    response = await client1.post(
        '/api/v1/wallets/transfer',
        json={
            'sender_wallet_id': wallet_id1,
            'receiver_wallet_id': fake_id,
            'amount': '100.00'
        },
        headers={'Idempotency-Key': str(uuid4())}
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


async def test_transfer_unauthorized(async_client: AsyncClient):
    """Transfer without auth token returns 401 Unauthorized."""
    response = await async_client.post(
        '/api/v1/wallets/transfer',
        json={
            'sender_wallet_id': NONEXISTENT_WALLET_ID,
            'receiver_wallet_id': NONEXISTENT_WALLET_ID,
            'amount': '100.00'
        },
        headers={'Idempotency-Key': str(uuid4())}
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_transfer_idempotent(
        db_session: AsyncSession,
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str],
):
    """
    Repeating a transfer with the same key replays the stored response
    without moving money twice.
    """
    client1, wallet_id1, client2, wallet_id2 = funded_wallets
    key = str(uuid4())
    payload = {
        'sender_wallet_id': wallet_id1,
        'receiver_wallet_id': wallet_id2,
        'amount': '100.00',
    }

    first = await client1.post(
        '/api/v1/wallets/transfer',
        json=payload,
        headers={'Idempotency-Key': key},
    )
    second = await client1.post(
        '/api/v1/wallets/transfer',
        json=payload,
        headers={'Idempotency-Key': key},
    )

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.OK
    assert first.json() == second.json()

    db_session.expire_all()

    records = (
        await db_session.execute(select(IdempotencyRecord))
    ).scalars().all()
    assert len(records) == 1

    entries = (
        await db_session.execute(select(Transaction))
    ).scalars().all()
    assert len(entries) == 2

    wallet1 = await db_session.get(Wallet, UUID(wallet_id1))
    wallet2 = await db_session.get(Wallet, UUID(wallet_id2))
    assert wallet1.balance == Decimal('900.00')
    assert wallet2.balance == Decimal('100.00')


async def test_transfer_same_key_different_payload(
        db_session: AsyncSession,
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str],
):
    """Reusing a key with different parameters is rejected."""
    client1, wallet_id1, client2, wallet_id2 = funded_wallets
    key = str(uuid4())
    payload1 = {
        'sender_wallet_id': wallet_id1,
        'receiver_wallet_id': wallet_id2,
        'amount': '100.00',
    }
    payload2 = {
        'sender_wallet_id': wallet_id1,
        'receiver_wallet_id': wallet_id2,
        'amount': '200.00',
    }

    first = await client1.post(
        '/api/v1/wallets/transfer',
        json=payload1,
        headers={'Idempotency-Key': key},
    )
    second = await client1.post(
        '/api/v1/wallets/transfer',
        json=payload2,
        headers={'Idempotency-Key': key},
    )

    assert first.status_code == HTTPStatus.OK
    assert second.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
