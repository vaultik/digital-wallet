# app/api/router.py
from fastapi import APIRouter
from app.api.v1.auth_api import router as auth_router
from app.api.v1.wallet_api import router as wallet_router

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth_router)
api_router.include_router(wallet_router)
