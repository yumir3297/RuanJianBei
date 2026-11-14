"""Merge GuideLoop pilot and application integration histories.

Revision ID: bd17a3f492c0
Revises: 91a0c5e2f347, 6f0ecdb27c41
"""
from typing import Sequence, Union

revision: str = "bd17a3f492c0"
down_revision: Union[str, Sequence[str], None] = ("91a0c5e2f347", "6f0ecdb27c41")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
