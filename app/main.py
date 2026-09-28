# app/main.py
import stripe
from fastapi import FastAPI

from app.core.config import settings
from app.api.router import api_router
from app.core.constants import APP_TITLE, DESCRIPTION
from app.core.exception_handlers import EXCEPTION_HANDLERS

app = FastAPI(
    title=APP_TITLE,
    description=DESCRIPTION
)

app.include_router(api_router)

stripe.api_key = settings.stripe_secret_key

for exc_class, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)
