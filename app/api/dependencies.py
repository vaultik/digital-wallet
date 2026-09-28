# app/api/dependencies.py
import stripe
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.exceptions import UserNotFoundError
from app.core.security import decode_token
from app.core.stripe_client import get_stripe_client
from app.models import User
from app.repositories import (
    CurrencyRepository,
    TokenRepository,
    TransactionRepository,
    UserRepository,
    WebhookIdempotencyRepository,
)
from app.services import (
    AuthService,
    PaymentService,
    WalletService
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        user_repo: UserRepository = Depends(UserRepository)
) -> User:
    """Decode Bearer token and return the active user. Raise 401 if invalid."""
    payload = decode_token(token)
    user = await user_repo.get_by_id(payload.sub)
    if user is None or not user.is_active:
        raise UserNotFoundError('User not found')
    return user


async def get_auth_service(
        token_repo: TokenRepository = Depends(TokenRepository),
        user_repo: UserRepository = Depends(UserRepository),
) -> AuthService:
    """Dependency factory for AuthService with injected repositories."""
    return AuthService(
        token_repo=token_repo,
        user_repo=user_repo
    )


async def get_payment_service(
        currency_repo: CurrencyRepository = Depends(),
        stripe_client: stripe.StripeClient = Depends(get_stripe_client),
        transaction_repo: TransactionRepository = Depends(),
        wallet_service: WalletService = Depends(),
        webhook_idempotency_repo: WebhookIdempotencyRepository = Depends(),
        db: AsyncSession = Depends(get_async_session),
) -> PaymentService:
    """
    Dependency factory for PaymentService with injected repositories and Stripe client.
    """
    return PaymentService(
        currency_repo=currency_repo,
        stripe_client=stripe_client,
        transaction_repo=transaction_repo,
        wallet_service=wallet_service,
        webhook_idempotency_repo=webhook_idempotency_repo,
        db=db,
    )
