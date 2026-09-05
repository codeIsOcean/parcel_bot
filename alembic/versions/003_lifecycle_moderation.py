"""Жизненный цикл доставки, модерация и чаты для кросс-постинга.

Revision ID: 003c5d6e7f80
Revises: 002f1a2b3c4d
"""
from alembic import op
import sqlalchemy as sa

# Идентификаторы ревизии
revision = "003c5d6e7f80"
down_revision = "002f1a2b3c4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === Посылка: этапы доставки ===
    # Код выдачи — подтверждение того, что посылка дошла до получателя
    op.add_column("parcels", sa.Column("handover_code", sa.String(length=6), nullable=True))
    op.add_column("parcels", sa.Column("handed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("parcels", sa.Column("in_transit_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("parcels", sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("parcels", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("parcels", sa.Column("handover_photo_file_ids", sa.Text(), nullable=True))
    op.add_column("parcels", sa.Column("delivery_photo_file_ids", sa.Text(), nullable=True))

    # === Пользователь: модерация ===
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("reports_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # === Жалобы ===
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("parcel_id", sa.Integer(), nullable=True),
        sa.Column(
            "reason",
            sa.Enum("scam", "no_show", "prohibited", "rude", "other", name="reportreason"),
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "reviewed", "confirmed", name="reportstatus"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["parcel_id"], ["parcels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_author_id", "reports", ["author_id"])
    op.create_index("ix_reports_target_id", "reports", ["target_id"])
    op.create_index("ix_reports_status", "reports", ["status"])

    # === Чаты для кросс-постинга рейсов ===
    op.create_table(
        "promo_chats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("cities", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("posts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id"),
    )
    op.create_index("ix_promo_chats_chat_id", "promo_chats", ["chat_id"])
    op.create_index("ix_promo_chats_is_active", "promo_chats", ["is_active"])


def downgrade() -> None:
    op.drop_table("promo_chats")
    op.drop_table("reports")
    sa.Enum(name="reportstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="reportreason").drop(op.get_bind(), checkfirst=True)
    op.drop_column("users", "reports_count")
    op.drop_column("users", "is_blocked")
    for column in (
        "delivery_photo_file_ids", "handover_photo_file_ids",
        "delivered_at", "arrived_at", "in_transit_at", "handed_at", "handover_code",
    ):
        op.drop_column("parcels", column)
