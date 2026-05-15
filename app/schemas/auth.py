from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr | None = None
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError('Password must be more than 8 characters long')
        if not any(char.isupper() for char in value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one digit')
        if not any(not char.isalnum() for char in value):
            raise ValueError('Password must contain at least one special character (!@#$...)')
        return value

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal['Bearer'] = 'Bearer'
    expires_in: int

class TokenPayload(BaseModel):
    sub: str
    sid: str
    exp: int
    iat: int
