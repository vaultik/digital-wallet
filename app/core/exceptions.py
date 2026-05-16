# app/core/exceptions.py
class InvalidTokenError(Exception):
    pass

class InvalidCredentialsError(Exception):
    pass

class UserAlreadyExistsError(Exception):
    pass

class UserNotFoundError(Exception):
    pass
