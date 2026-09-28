# app/services/payment_service.py
import logging
from decimal import Decimal
from uuid import UUID, uuid4

import stripe
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.constants import (
    SYSTEM_USER_ID,
    EntryType,
    TransactionType,
)
from app.core.db import get_async_session
from app.core.exceptions import (
    InvalidPaymentDataError,
    InvalidWebhookSignatureError,
    PaymentProviderError,
)
from app.core.stripe_client import get_stripe_client
from app.repositories import (
    CurrencyRepository,
    TransactionRepository,
    WebhookIdempotencyRepository,
)
from app.services import WalletService
from app.schemas.deposit_schemas import (
    DepositCreate, DepositResponse
)

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(
            self,
            currency_repo: CurrencyRepository = Depends(),
            transaction_repo: TransactionRepository = Depends(),
            wallet_service: WalletService = Depends(),
            webhook_idempotency_repo: WebhookIdempotencyRepository = Depends(),
            db: AsyncSession = Depends(get_async_session),
            stripe_client: stripe.StripeClient = Depends(get_stripe_client)
    ):
        self.currency_repo = currency_repo
        self.transaction_repo = transaction_repo
        self.wallet_service = wallet_service
        self.webhook_idempotency_repo = webhook_idempotency_repo
        self._db = db
        self.stripe_client = stripe_client

    async def create_checkout_session(
            self, data: DepositCreate, user_id: UUID
    ) -> DepositResponse:
        """
        Validate currency, get or create wallet, and create a Stripe.

        Checkout Session for a one-time deposit.
        Returns the URL the frontend should redirect the user to.
        """
        currency = await self.currency_repo.get_by_code(data.currency)
        if not currency or not currency.is_active or not currency.is_fiat:
            raise InvalidPaymentDataError('The currency does not match')
        wallet = await self.wallet_service.get_or_create_wallet(
            user_id=user_id, currency=data.currency
        )
        await self._db.commit()
        amount_in_cents = int(data.amount * (10 ** currency.decimals))

        try:
            stripe_session = await self.stripe_client.v1.checkout.sessions.create_async(
                mode='payment',
                success_url=settings.stripe_success_url,
                cancel_url=settings.stripe_cancel_url,
                line_items=[{
                    'price_data': {
                        'currency': currency.code.lower(),
                        'unit_amount': amount_in_cents,
                        'product_data': {
                            'name': f'Deposit {data.amount} {currency.code}',
                        }
                    },
                    'quantity': 1,
                }],
                metadata={
                    'wallet_id': str(wallet.id),
                }
            )
            checkout_url = stripe_session.url
        except stripe.InvalidRequestError as e:
            logger.error('InvalidRequestError: %s', e, exc_info=True)
            raise PaymentProviderError('Payments provider is unavailable.') from e
        except stripe.StripeError as e:
            logger.error('StripeError: %s', e, exc_info=True)
            raise PaymentProviderError('Payments provider is unavailable.') from e

        return DepositResponse(deposit_url=checkout_url)

    async def handle_webhook(
            self, payload: bytes, sig_header: str
    ) -> None:
        """
        Verify a Stripe webhook and credit the deposit on
        'checkout.session.completed' with payment_status == 'paid'.

        Unrelated event types and already-processed events are ignored,
        returning 200 so Stripe stops retrying them.
        """
        try:
            event = self.stripe_client.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=settings.stripe_webhook_secret
            )
        except stripe.SignatureVerificationError as e:
            logger.error('Stripe SignatureVerificationError: %s', e, exc_info=True)
            raise InvalidWebhookSignatureError('Webhook signature is invalid.') from e

        if event.type != 'checkout.session.completed':
            return

        session = event.data.object
        if session.payment_status != 'paid':
            return

        wallet_id_str = session.metadata.get('wallet_id')
        if not wallet_id_str:
            logger.warning('session.metadata.get("wallet_id") is empty')
            return

        is_new = await self.webhook_idempotency_repo.register_event(event.id)
        if not is_new:
            return

        currency = await self.currency_repo.get_by_code(session.currency.upper())
        if not currency or not currency.is_active or not currency.is_fiat:
            raise InvalidPaymentDataError('The currency does not match')
        amount = Decimal(session.amount_total) / (10 ** currency.decimals)

        await self.wallet_service.credit_external_deposit(
            wallet_id=UUID(wallet_id_str), amount=amount, currency=currency.code
        )
