"""merge speech metadata and tour progress branches

Revision ID: 8ab42c17d3e9
Revises: c3b7e1d9a62f, 5c81a1e74f2b
"""
from typing import Sequence, Union

revision: str = "8ab42c17d3e9"
down_revision: Union[str, Sequence[str], None] = ("c3b7e1d9a62f", "5c81a1e74f2b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
