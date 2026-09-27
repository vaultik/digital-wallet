# app/services/payment_service.py
import logging
from uuid import UUID

import stripe
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_async_session
from app.core.exceptions import (
    InvalidPaymentDataError,
    InvalidWebhookSignatureError,
    PaymentProviderError,
)
from app.core.stripe_client import get_stripe_client
from app.repositories import CurrencyRepository
from app.services import WalletService
from app.schemas.deposit_schemas import (
    DepositCreate, DepositResponse
)

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(
            self,
            currency_repo: CurrencyRepository = Depends(),
            wallet_service: WalletService = Depends(),
            db: AsyncSession = Depends(get_async_session),
            stripe_client: stripe.StripeClient = Depends(get_stripe_client)
    ):
        self.currency_repo = currency_repo
        self.wallet_service = wallet_service
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
            currency=data.currency, user_id=user_id
        )
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
