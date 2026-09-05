"""Платный доступ к ответам на заявки: оплата публикации рейса.

Revision ID: 002f1a2b3c4d
Revises: 001a2b3c4d5e
"""
from alembic import op
import sqlalchemy as sa

# Идентификаторы ревизии
revision = "002f1a2b3c4d"
down_revision = "001a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Оплачена ли публикация рейса. Пока нет — перевозчик видит заявки,
    # но не может их принять и не может писать отправителю.
    op.add_column(
        "flights",
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_flights_is_paid", "flights", ["is_paid"])

    # Момент оплаты
    op.add_column(
        "flights",
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Платёж, которым закрыта публикация
    op.add_column(
        "flights",
        sa.Column("payment_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_flights_payment_id", "flights", "payments", ["payment_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_flights_payment_id", "flights", type_="foreignkey")
    op.drop_column("flights", "payment_id")
    op.drop_column("flights", "paid_at")
    op.drop_index("ix_flights_is_paid", table_name="flights")
    op.drop_column("flights", "is_paid")
