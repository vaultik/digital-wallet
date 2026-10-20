# app/api/v1/__init__.py
from app.api.v1.auth_api import router as auth_router  # noqa
from app.api.v1.payments_api import router as payment_router  # noqa
from app.api.v1.wallet_api import router as wallet_router  # noqa
