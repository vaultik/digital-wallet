"""seed_currencies

Revision ID: f5fbf00045a2
Revises: fd0908d27577
Create Date: 2026-04-22 18:50:02.726228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5fbf00045a2'
down_revision: Union[str, Sequence[str], None] = 'fd0908d27577'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        INSERT INTO currency (code, name, decimals, is_fiat, is_active)
        VALUES
            ('USD', 'US Dollar', 2,  true,  true),
            ('EUR', 'Euro',      2,  true,  true),
            ('BTC', 'Bitcoin',   8,  false, true),
            ('ETH', 'Ethereum',  18, false, true)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM currency WHERE code IN ('USD', 'EUR', 'BTC', 'ETH')")
