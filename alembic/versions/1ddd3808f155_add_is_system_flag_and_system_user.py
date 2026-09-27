"""add is_system flag and system user

Revision ID: 1ddd3808f155
Revises: c5a9629af249
Create Date: 2026-09-27 01:22:08.019975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ddd3808f155'
down_revision: Union[str, Sequence[str], None] = 'c5a9629af249'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user', sa.Column(
        'is_system_user', sa.Boolean(), nullable=False, server_default=sa.text('false')
    ))
    op.add_column('wallet', sa.Column(
        'is_system', sa.Boolean(), nullable=False, server_default=sa.text('false')
    ))
    op.drop_constraint('check_positive_balance', 'wallet', type_='check')
    op.create_check_constraint(
        'check_positive_balance', 'wallet', 'is_system OR balance >= 0'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'check_positive_balance', 'wallet', type_='check'
    )
    op.create_check_constraint(
        'check_positive_balance', 'wallet', 'balance >= 0'
    )
    op.drop_column('wallet', 'is_system')
    op.drop_column('user', 'is_system_user')
