# app/core/stripe_client.py
import logging
from typing import AsyncGenerator

import stripe

from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_stripe_client() -> AsyncGenerator[stripe.StripeClient, None]:
    http_client = stripe.HTTPXClient()
    client = stripe.StripeClient(
        api_key=settings.stripe_secret_key,
        http_client=http_client,
    )
    try:
        yield client
    except stripe.StripeError as e:
        logger.error('Stripe Error: %s', e, exc_info=True)
        raise
    finally:
        await http_client.close_async()
