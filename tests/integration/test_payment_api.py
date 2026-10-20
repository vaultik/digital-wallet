# tests/integration/test_payment_api.py
import json
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import MagicMock
from uuid import UUID

import stripe
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Transaction,
    Wallet,
    WebhookIdempotencyRecord,
)
from tests.helpers import stripe_signature_header

DEPOSIT_URL = '/api/v1/payments/deposit'
WEBHOOK_URL = '/api/v1/payments/stripe-webhook'


def checkout_event(wallet_id: str, **overrides) -> dict:
    """
    Build a paid checkout.session.completed event, overriding any field.
    """
    session = {
        'payment_status': 'paid',
        'currency': 'eur',
        'amount_total': 10_000,
        'metadata': {'wallet_id': wallet_id},
    }
    session.update(overrides.pop('session', {}))
    event = {
        'id': 'evt_test',
        'type': 'checkout.session.completed',
        'data': {'object': session},
    }
    event.update(overrides)
    return event


async def post_webhook(
        client: AsyncClient,
        event: dict,
        signature: str | None = None,
) -> Response:
    """Send an event to the webhook endpoint, signing it by default."""
    payload = json.dumps(event).encode()
    if signature is None:
        signature = stripe_signature_header(
            payload, settings.stripe_webhook_secret
        )
    return await client.post(
        WEBHOOK_URL,
        content=payload,
        headers={'stripe-signature': signature},
    )


async def test_create_deposit_session(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
        db_session: AsyncSession,
):
    """
    A deposit request returns a Stripe checkout URL and provisions a wallet.
    """
    response = await auth_client.post(
        DEPOSIT_URL,
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
        DEPOSIT_URL,
        json={'currency': 'USD', 'amount': '10.999'},
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_create_deposit_unknown_currency(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """A currency that is not in the reference table is rejected."""
    response = await auth_client.post(
        DEPOSIT_URL,
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
        DEPOSIT_URL,
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
        DEPOSIT_URL,
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
        DEPOSIT_URL,
        json={'currency': 'USD', 'amount': '10.50'},
    )
    assert response.status_code == HTTPStatus.BAD_GATEWAY


async def test_create_deposit_rejects_non_finite_amount(
        auth_client: AsyncClient,
        stripe_client_override: MagicMock,
):
    """A non-finite amount never reaches the service."""
    response = await auth_client.post(
        DEPOSIT_URL,
        json={'currency': 'USD', 'amount': 'Infinity'},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# POST /payments/stripe-webhook
async def test_webhook_credits_deposit(
        async_client: AsyncClient,
        stripe_webhook_override: None,
        db_session: AsyncSession,
        deposit_wallet: Wallet,
):
    """A paid checkout session credits the wallet via double entry."""
    event = checkout_event(
        str(deposit_wallet.id),
    )
    response = await post_webhook(
        async_client,
        event,
    )
    assert response.status_code == HTTPStatus.OK

    wallet = await db_session.get(Wallet, deposit_wallet.id)
    assert wallet.balance == Decimal('100.00')


async def test_webhook_rejects_invalid_signature(
        async_client: AsyncClient,
        stripe_webhook_override: None,
        db_session: AsyncSession,
        deposit_wallet: Wallet,
):
    """A tampered signature is rejected and nothing is credited."""
    event = checkout_event(
        str(deposit_wallet.id),
    )
    response = await post_webhook(
        async_client,
        event,
        signature='t=123,v1=deadbeef',
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST

    wallet = await db_session.get(Wallet, deposit_wallet.id)
    assert wallet.balance == Decimal('0.00')


async def test_webhook_ignores_unrelated_event_type(
        async_client: AsyncClient,
        stripe_webhook_override: None,
        db_session: AsyncSession,
        deposit_wallet: Wallet,
):
    """Events we don't handle are acknowledged without side effects."""
    event = checkout_event(
        str(deposit_wallet.id),
        type='payment_intent.succeeded',
    )
    response = await post_webhook(
        async_client,
        event,
    )
    assert response.status_code == HTTPStatus.OK

    wallet = await db_session.get(Wallet, deposit_wallet.id)
    assert wallet.balance == Decimal('0.00')


async def test_webhook_ignores_unpaid_session(
        async_client: AsyncClient,
        stripe_webhook_override: None,
        db_session: AsyncSession,
        deposit_wallet: Wallet,
):
    """A session that was not paid does not credit the wallet."""
    event = checkout_event(
        str(deposit_wallet.id),
        session={'payment_status': 'unpaid'},
    )
    response = await post_webhook(
        async_client,
        event,
    )
    assert response.status_code == HTTPStatus.OK

    wallet = await db_session.get(Wallet, deposit_wallet.id)
    assert wallet.balance == Decimal('0.00')


async def test_webhook_ignores_missing_wallet_id(
        async_client: AsyncClient,
        stripe_webhook_override: None,
        db_session: AsyncSession,
        deposit_wallet: Wallet,
):
    """A session without wallet_id metadata is acknowledged and skipped."""
    event = checkout_event(
        str(deposit_wallet.id),
        session={'metadata': {}},
    )
    response = await post_webhook(
        async_client,
        event,
    )
    assert response.status_code == HTTPStatus.OK

    wallet = await db_session.get(Wallet, deposit_wallet.id)
    assert wallet.balance == Decimal('0.00')


async def test_webhook_is_idempotent(
        async_client: AsyncClient,
        stripe_webhook_override: None,
        db_session: AsyncSession,
        deposit_wallet: Wallet,
):
    """Re-delivering the same event does not credit twice."""
    event = checkout_event(
        str(deposit_wallet.id),
        id='evt_test_idempotency',
    )
    response1 = await post_webhook(
        async_client,
        event
    )
    response2 = await post_webhook(
        async_client,
        event
    )
    assert response1.status_code == HTTPStatus.OK
    assert response2.status_code == HTTPStatus.OK

    wallet = await db_session.get(Wallet, deposit_wallet.id)
    assert wallet.balance == Decimal('100.00')

    entries = (
        await db_session.execute(select(Transaction))
    ).scalars().all()
    assert len(entries) == 2
    record = (
        await db_session.execute(select(WebhookIdempotencyRecord))
    ).scalars().all()
    assert len(record) == 1
