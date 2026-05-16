# app/main.py
from fastapi import FastAPI

from app.api.router import api_router
from app.core.exception_handlers import EXCEPTION_HANDLERS

app = FastAPI()

app.include_router(api_router)

for exc_class, handler in EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)
