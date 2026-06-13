"""add balance server_default

Revision ID: 3a60e4c13599
Revises: f5fbf00045a2
Create Date: 2026-06-13 22:45:14.507853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a60e4c13599'
down_revision: Union[str, Sequence[str], None] = 'f5fbf00045a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'wallet',
        'balance',
        server_default='0'
    )

def downgrade() -> None:
    op.alter_column(
        'wallet',
        'balance',
        server_default=None
    )
