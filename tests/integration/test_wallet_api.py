# tests/integration/test_wallet_api.py
from http import HTTPStatus
from uuid import uuid4

import pytest
from httpx import AsyncClient

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
        funded_wallets: tuple[AsyncClient, str, AsyncClient, str]
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
    assert response.json()['sender_balance'] == '900.000000000000000000'


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
