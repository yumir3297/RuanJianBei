"""merge the independent W01 tour and K01 knowledge migration branches

Revision ID: f324abc9d012
Revises: e9f4c2b8016a, d12a77c0e40e
Create Date: 2026-10-29
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f324abc9d012"
down_revision: Union[str, Sequence[str], None] = ("e9f4c2b8016a", "d12a77c0e40e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
