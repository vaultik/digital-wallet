# app/core/exceptions.py
class InvalidTokenError(Exception):
    """Raised when JWT token is invalid, expired or revoked."""

class InvalidCredentialsError(Exception):
    """Raised when username or password is incorrect."""

class UserAlreadyExistsError(Exception):
    """Raised when username or email is already registered."""

class UserNotFoundError(Exception):
    """Raised when requested user does not exist."""

class WalletAlreadyExistsError(Exception):
    """Raised when wallet already existed."""

class WalletNotFoundError(Exception):
    """Raised when requested wallet does not exist."""

class InvalidWalletsDataError(Exception):
    """Raised when wallet's data is incorrect."""

class InvalidPaymentDataError(Exception):
    """Raised when payment's data is incorrect."""

class PaymentProviderError(Exception):
    """Raised when Stripe API is unavailable or returns an unexpected error."""

class InvalidWebhookSignatureError(Exception):
    """Raised when webhook signature invalid."""
