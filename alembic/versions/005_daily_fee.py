"""Переход с оплаты за публикацию на дневной тариф перевозчика.

Revision ID: 005b1c2d3e40
Revises: 004a7b8c9d01
"""
from alembic import op
import sqlalchemy as sa

# Идентификаторы ревизии
revision = "005b1c2d3e40"
down_revision = "004a7b8c9d01"
branch_labels = None
depends_on = None

# Сколько пробных дней получают уже зарегистрированные перевозчики
DEFAULT_TRIAL_DAYS = 14


def upgrade() -> None:
    # Дата, за которую тариф уже оплачен или засчитан пробным днём
    op.add_column("users", sa.Column("last_fee_date", sa.Date(), nullable=True))

    # Остаток пробных активных дней
    op.add_column(
        "users",
        sa.Column("trial_days_left", sa.Integer(), nullable=False, server_default="0"),
    )

    # Уже зарегистрированные не должны остаться без пробного периода
    op.execute(f"UPDATE users SET trial_days_left = {DEFAULT_TRIAL_DAYS}")

    # Поштучная оплата публикации больше не используется
    op.drop_constraint("fk_flights_payment_id", "flights", type_="foreignkey")
    op.drop_column("flights", "payment_id")
    op.drop_column("flights", "paid_at")
    op.drop_index("ix_flights_is_paid", table_name="flights")
    op.drop_column("flights", "is_paid")


def downgrade() -> None:
    op.add_column(
        "flights",
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_flights_is_paid", "flights", ["is_paid"])
    op.add_column("flights", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("flights", sa.Column("payment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_flights_payment_id", "flights", "payments", ["payment_id"], ["id"],
    )

    op.drop_column("users", "trial_days_left")
    op.drop_column("users", "last_fee_date")
