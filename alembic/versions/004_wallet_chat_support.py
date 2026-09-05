"""Баланс в звёздах, сессии чатов и поддержка.

Revision ID: 004a7b8c9d01
Revises: 003c5d6e7f80
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Идентификаторы ревизии
revision = "004a7b8c9d01"
down_revision = "003c5d6e7f80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === Баланс пользователя ===
    op.add_column(
        "users",
        sa.Column("balance_stars", sa.Integer(), nullable=False, server_default="0"),
    )

    # === Платежи: звёзды и TON ===
    # Новый вид оплаты с баланса
    op.execute("ALTER TYPE paymentmethod ADD VALUE IF NOT EXISTS 'balance'")

    op.add_column("payments", sa.Column("amount_stars", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("amount_ton", sa.Float(), nullable=True))
    op.add_column("payments", sa.Column("payment_code", sa.String(length=40), nullable=True))
    op.add_column("payments", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    # Тип создаём отдельно: add_column его сам не заводит
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentkind') THEN
                CREATE TYPE paymentkind AS ENUM ('topup', 'post', 'subscription');
            END IF;
        END
        $$;
        """
    )
    op.add_column(
        "payments",
        sa.Column(
            "kind",
            postgresql.ENUM("topup", "post", "subscription", name="paymentkind", create_type=False),
            nullable=False,
            server_default="topup",
        ),
    )
    # Уникальность защищает от повторного зачисления одного платежа
    op.create_unique_constraint("uq_payments_transaction_id", "payments", ["transaction_id"])
    op.create_index("ix_payments_transaction_id", "payments", ["transaction_id"])
    op.create_unique_constraint("uq_payments_payment_code", "payments", ["payment_code"])
    op.create_index("ix_payments_payment_code", "payments", ["payment_code"])
    op.create_index("ix_payments_kind", "payments", ["kind"])

    # === Журнал баланса ===
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'balancetxnkind') THEN
                CREATE TYPE balancetxnkind AS ENUM ('topup', 'charge', 'refund');
            END IF;
        END
        $$;
        """
    )
    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM("topup", "charge", "refund", name="balancetxnkind", create_type=False),
            nullable=False,
        ),
        sa.Column("amount_stars", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("external_ref", sa.String(length=200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_ref", name="uq_balance_transactions_external_ref"),
    )
    op.create_index("ix_balance_transactions_user_id", "balance_transactions", ["user_id"])
    op.create_index("ix_balance_transactions_kind", "balance_transactions", ["kind"])
    op.create_index("ix_balance_transactions_external_ref", "balance_transactions", ["external_ref"])

    # === Сессии чата отправитель ↔ перевозчик ===
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parcel_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=False),
        sa.Column("traveler_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["traveler_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parcel_id", name="uq_chat_sessions_parcel_id"),
    )
    op.create_index("ix_chat_sessions_sender_id", "chat_sessions", ["sender_id"])
    op.create_index("ix_chat_sessions_traveler_id", "chat_sessions", ["traveler_id"])

    # === Поддержка ===
    op.create_table(
        "support_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_pending", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_sessions_user_id", "support_sessions", ["user_id"])
    op.create_index("ix_support_sessions_is_active", "support_sessions", ["is_active"])
    op.create_index("ix_support_sessions_is_pending", "support_sessions", ["is_pending"])

    op.create_table(
        "support_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_role", sa.String(length=20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["support_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_messages_session_id", "support_messages", ["session_id"])
    op.create_index(
        "ix_support_messages_session_created", "support_messages", ["session_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("support_messages")
    op.drop_table("support_sessions")
    op.drop_table("chat_sessions")
    op.drop_table("balance_transactions")
    sa.Enum(name="balancetxnkind").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_payments_kind", table_name="payments")
    op.drop_index("ix_payments_payment_code", table_name="payments")
    op.drop_constraint("uq_payments_payment_code", "payments", type_="unique")
    op.drop_index("ix_payments_transaction_id", table_name="payments")
    op.drop_constraint("uq_payments_transaction_id", "payments", type_="unique")
    for column in ("kind", "completed_at", "expires_at", "payment_code", "amount_ton", "amount_stars"):
        op.drop_column("payments", column)
    sa.Enum(name="paymentkind").drop(op.get_bind(), checkfirst=True)

    op.drop_column("users", "balance_stars")
