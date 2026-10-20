# app/api/v1/payments_api.py
from fastapi import APIRouter, Depends, Header, Request

from app.api.dependencies import (
    get_current_user,
    get_payment_service
)
from app.models import User
from app.schemas.deposit_schemas import DepositCreate, DepositResponse
from app.services import PaymentService

router = APIRouter(prefix='/payments', tags=['payment'])


@router.post(
    '/deposit',
    response_model=DepositResponse,
    status_code=201
)
async def create_deposit(
        data: DepositCreate,
        current_user: User = Depends(get_current_user),
        service: PaymentService = Depends(get_payment_service)
) -> DepositResponse:
    """
    Create a Stripe Checkout Session for a fiat deposit.

    Validates the target currency, gets or creates the user's wallet for it,
    and returns the Stripe-hosted checkout URL to redirect the client to.
    The wallet is not credited here – that happens later, when Stripe
    confirms payment via POST /payments/stripe-webhook.
    """
    return await service.create_checkout_session(
        data=data, user_id=current_user.id
    )


@router.post(
    '/stripe-webhook',
    status_code=200
)
async def handle_stripe_webhook(
        request: Request,
        service: PaymentService = Depends(get_payment_service),
        stripe_signature: str = Header(alias='stripe-signature'),
) -> None:
    """
    Receive and process Stripe webhook events.

    Verifies `stripe-signature` against the raw request body before trusting
    the payload – this replaces JWT auth for this endpoint, since Stripe
    (not a logged-in user) is the caller.

    Always responds 200 for events we deliberately ignore (unhandled event
    type, unpaid session, missing wallet_id metadata), so Stripe stops
    retrying them. Responds 400 only when signature verification itself
    fails (handled via InvalidWebhookSignatureError -> global handler).
    """
    payload = await request.body()
    return await service.handle_webhook(
        payload=payload, sig_header=stripe_signature
    )
