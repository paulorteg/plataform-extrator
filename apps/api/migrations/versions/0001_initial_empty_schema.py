"""initial empty schema

Revision ID: 0001_initial_empty_schema
Revises:
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union


revision: str = "0001_initial_empty_schema"
down_revision: Optional[str] = None
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
