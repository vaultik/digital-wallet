# app/repositories/token_repository.py
from fastapi import Depends
from redis.asyncio import Redis

from app.core.db import get_redis


class TokenRepository:

    def __init__(self, redis: Redis = Depends(get_redis)):
        self._redis = redis

    async def save_refresh_token(
            self,
            user_id: str,
            session_id: str,
            token: str,
            ttl: int
    ) -> None:
        await self._redis.set(
            f'refresh:{user_id}:{session_id}',
            token,
            ex=ttl
        )

    async def get_refresh_token(
            self,
            user_id: str,
            session_id: str,
    ) -> str | None:
        return await self._redis.get(
            f'refresh:{user_id}:{session_id}'
        )

    async def delete_refresh_token(
            self,
            user_id: str,
            session_id: str,
    ) -> None:
        await self._redis.delete(
            f'refresh:{user_id}:{session_id}'
        )

    async def delete_all_user_tokens(
            self,
            user_id: str,
    ) -> None:
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(
                cursor, match=f"refresh:{user_id}:*"
            )
            for key in keys:
                await self._redis.delete(key)
            if cursor == 0:
                break
