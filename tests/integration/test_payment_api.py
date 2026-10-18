# tests/integration/test_payment_api.py
from http import HTTPStatus
from unittest.mock import MagicMock
from uuid import UUID

import stripe
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Wallet


async def test_create_deposit_session(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
        db_session: AsyncSession,
):
    """
    A deposit request returns a Stripe checkout URL and provisions a wallet.
    """
    response = await auth_client.post(
        '/api/v1/payments/deposit',
        json={'currency': 'USD', 'amount': '10.50'}
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['deposit_url'].startswith(
        'https://checkout.stripe.com'
    )
    create = stripe_client_override.v1.checkout.sessions.create_async
    create.assert_called_once()
    params = create.call_args.kwargs['params']

    price_data = params['line_items'][0]['price_data']
    assert price_data['unit_amount'] == 1050
    assert price_data['currency'] == 'usd'

    wallet = await db_session.get(Wallet, UUID(params['metadata']['wallet_id']))
    assert wallet is not None
    assert wallet.currency == 'USD'


async def test_create_deposit_rejects_excess_precision(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """
    An amount with more decimals than the currency allows is rejected.
    """
    response = await auth_client.post(
        '/api/v1/payments/deposit',
        json={'currency': 'USD', 'amount': '10.999'},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_create_deposit_unknown_currency(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """A currency that is not in the reference table is rejected."""
    response = await auth_client.post(
        '/api/v1/payments/deposit',
        json={'currency': 'WOW', 'amount': '10.50'}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    stripe_client_override.v1.checkout.sessions.create_async.assert_not_called()


async def test_create_deposit_crypto_currency(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """Cryptocurrencies cannot be topped up through Stripe."""
    response = await auth_client.post(
        '/api/v1/payments/deposit',
        json={'currency': 'BTC', 'amount': '10.50'}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    stripe_client_override.v1.checkout.sessions.create_async.assert_not_called()


async def test_create_deposit_stripe_error(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """A generic Stripe failure surfaces as 502 Bad Gateway."""
    stripe_client_override.v1.checkout.sessions.create_async.side_effect = (
        stripe.StripeError('provider is down')
    )

    response = await auth_client.post(
        '/api/v1/payments/deposit',
        json={'currency': 'USD', 'amount': '10.50'},
    )
    assert response.status_code == HTTPStatus.BAD_GATEWAY


async def test_create_deposit_stripe_invalid_request(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """An invalid request to Stripe surfaces as 502 Bad Gateway."""
    stripe_client_override.v1.checkout.sessions.create_async.side_effect = (
        stripe.InvalidRequestError('bad', param='currency')
    )

    response = await auth_client.post(
        '/api/v1/payments/deposit',
        json={'currency': 'USD', 'amount': '10.50'},
    )
    assert response.status_code == HTTPStatus.BAD_GATEWAY


async def test_create_deposit_rejects_non_finite_amount(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """A non-finite amount never reaches the service."""
    response = await auth_client.post(
        '/api/v1/payments/deposit',
        json={'currency': 'USD', 'amount': 'Infinity'},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
