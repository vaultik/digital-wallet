"""seed system user

Revision ID: 49d052e550af
Revises: 1ddd3808f155
Create Date: 2026-09-27 01:31:27.131992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49d052e550af'
down_revision: Union[str, Sequence[str], None] = '1ddd3808f155'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
            INSERT INTO "user" (id, username, is_system_user, is_active, is_superuser, hashed_password)
            VALUES ('09875260-0520-0003-5000-096240009401', 'system', true, false, false, 'OINDuh278gd2idb2781128-1278th138d12jd3c1-12hc718f2c1xh')
        """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""DELETE FROM "user" WHERE id = '09875260-0520-0003-5000-096240009401'""")
