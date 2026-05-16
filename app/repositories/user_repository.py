# app/repositories/user_repository.py
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.models.user import User

class UserRepository:

    def __init__(self, db: AsyncSession = Depends(get_async_session)):
        self._db = db

    async def create_user(
            self,
            username: str,
            email: str | None,
            hashed_password: str,
    ) -> User:
        payload = {
            'username': username,
            'email': email,
            'hashed_password': hashed_password
        }
        user = User(**payload)
        self._db.add(user)  # Почему без await?
        await self._db.flush()
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def get_by_username(
            self,
            username: str
    ) -> User | None:
        result = await self._db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(
            self,
            email: str,
    ) -> User | None:
        result = await self._db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(
            self,
            user_id: str
    ) -> User | None:
        return await self._db.get(User, user_id)
