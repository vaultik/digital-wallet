# app/core/exceptions.py
class InvalidTokenError(Exception):
    """Raised when JWT token is invalid, expired or revoked."""

class InvalidCredentialsError(Exception):
    """Raised when username or password is incorrect."""

class UserAlreadyExistsError(Exception):
    """Raised when username or email is already registered."""

class UserNotFoundError(Exception):
    """Raised when requested user does not exist."""
