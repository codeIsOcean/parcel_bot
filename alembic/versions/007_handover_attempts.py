"""Счётчик неверных кодов выдачи — защита от перебора.

Revision ID: 007d3e4f5a62
Revises: 006c2d3e4f51
"""
from alembic import op
import sqlalchemy as sa

# Идентификаторы ревизии
revision = "007d3e4f5a62"
down_revision = "006c2d3e4f51"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Сколько раз введён неверный код выдачи
    op.add_column(
        "parcels",
        sa.Column("handover_attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("parcels", "handover_attempts")
