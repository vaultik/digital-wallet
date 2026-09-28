# app/api/router.py
from fastapi import APIRouter
from app.api.v1 import auth_router, payment_router, wallet_router

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth_router)
api_router.include_router(payment_router)
api_router.include_router(wallet_router)
