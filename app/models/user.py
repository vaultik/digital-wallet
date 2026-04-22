# app/models/user.py
from typing import List

from sqlalchemy import (
    Boolean, Index, String,
)
from sqlalchemy.orm import (
    Mapped, mapped_column, relationship
)

from app.core.constants import STR_MED, STR_LONG
from app.models.base import Base, IdTimeMixin


class User(IdTimeMixin, Base):
    username: Mapped[str] = mapped_column(
        String(length=STR_MED),
        unique=True,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(length=STR_LONG),
    )
    hashed_password: Mapped[str] = mapped_column(
        String(STR_LONG),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False
    )

    wallets: Mapped[List['Wallet']] = relationship(
        back_populates='user',
        lazy='selectin',
    )

    __table_args__ = (
        Index(
            'idx_active_user_email',
            'email',
            unique=True,
            postgresql_where="is_active IS TRUE"
        ),
    )

    def __repr__(self) -> str:
        return (
            f'{super().__repr__()} '
            f'{self.username=} '
            f'{self.email=} '
        )
