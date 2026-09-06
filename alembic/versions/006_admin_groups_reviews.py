"""Админ-панель, группы с постами, ответы на отзывы, отклики перевозчиков.

Revision ID: 006c2d3e4f51
Revises: 005b1c2d3e40
"""
from alembic import op
import sqlalchemy as sa

# Идентификаторы ревизии
revision = "006c2d3e4f51"
down_revision = "005b1c2d3e40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Администраторы, назначенные из панели (владельцы из .env — всегда админы)
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Отзыв: теги-похвалы и один ответ получателя
    op.add_column("reviews", sa.Column("tags", sa.String(255), nullable=True))
    op.add_column("reviews", sa.Column("reply_text", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("reply_created_at", sa.DateTime(timezone=True), nullable=True))

    # Кто создал заявку: отправитель выбрал рейс или перевозчик откликнулся
    op.add_column(
        "matches",
        sa.Column("initiator", sa.String(10), nullable=False, server_default="sender"),
    )

    # Группы: реестр членства и что именно публиковать
    op.add_column("promo_chats", sa.Column("username", sa.String(64), nullable=True))
    op.add_column("promo_chats", sa.Column("chat_type", sa.String(20), nullable=True))
    op.add_column(
        "promo_chats",
        sa.Column("is_member", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "promo_chats",
        sa.Column("post_parcels", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "promo_chats",
        sa.Column("post_flights", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Опубликованные в группах объявления — чтобы редактировать их при закрытии
    op.create_table(
        "group_posts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_group_posts_chat_id", "group_posts", ["chat_id"])
    op.create_index("ix_group_posts_kind", "group_posts", ["kind"])
    op.create_index("ix_group_posts_entity_id", "group_posts", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_group_posts_entity_id", table_name="group_posts")
    op.drop_index("ix_group_posts_kind", table_name="group_posts")
    op.drop_index("ix_group_posts_chat_id", table_name="group_posts")
    op.drop_table("group_posts")

    op.drop_column("promo_chats", "post_flights")
    op.drop_column("promo_chats", "post_parcels")
    op.drop_column("promo_chats", "is_member")
    op.drop_column("promo_chats", "chat_type")
    op.drop_column("promo_chats", "username")

    op.drop_column("matches", "initiator")

    op.drop_column("reviews", "reply_created_at")
    op.drop_column("reviews", "reply_text")
    op.drop_column("reviews", "tags")

    op.drop_column("users", "is_admin")
