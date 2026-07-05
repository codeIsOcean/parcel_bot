"""Создание всех начальных таблиц проекта.

Revision ID: 001a2b3c4d5e
Revises: -
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

# Идентификаторы ревизии
revision = "001a2b3c4d5e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создание всех 10 таблиц и enum-типов."""

    # --- Enum-типы (сначала удаляем если есть для идемпотентности) ---
    op.execute("DROP TYPE IF EXISTS userrole CASCADE")
    op.execute("DROP TYPE IF EXISTS parcelstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS parcelsize CASCADE")
    op.execute("DROP TYPE IF EXISTS flightstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS matchstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS subscriptionplan CASCADE")
    op.execute("DROP TYPE IF EXISTS paymentmethod CASCADE")
    op.execute("DROP TYPE IF EXISTS paymentstatus CASCADE")

    op.execute("CREATE TYPE userrole AS ENUM ('sender', 'traveler', 'both')")
    op.execute("CREATE TYPE parcelstatus AS ENUM ('pending', 'accepted', 'handed', 'in_transit', 'delivered', 'cancelled')")
    op.execute("CREATE TYPE parcelsize AS ENUM ('small', 'medium', 'large')")
    op.execute("CREATE TYPE flightstatus AS ENUM ('active', 'full', 'in_transit', 'completed', 'cancelled')")
    op.execute("CREATE TYPE matchstatus AS ENUM ('pending', 'accepted', 'declined', 'counter')")
    op.execute("CREATE TYPE subscriptionplan AS ENUM ('monthly', 'quarterly', 'yearly', 'trial')")
    op.execute("CREATE TYPE paymentmethod AS ENUM ('stars', 'ton')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('pending', 'completed', 'failed', 'refunded')")

    # Создаём Enum объекты для использования в колонках (create_type=False чтобы не создавать типы повторно)
    userrole = sa.Enum("sender", "traveler", "both", name="userrole", create_constraint=True, create_type=False)
    parcelstatus = sa.Enum(
        "pending", "accepted", "handed", "in_transit", "delivered", "cancelled",
        name="parcelstatus", create_constraint=True, create_type=False,
    )
    parcelsize = sa.Enum("small", "medium", "large", name="parcelsize", create_constraint=True, create_type=False)
    flightstatus = sa.Enum(
        "active", "full", "in_transit", "completed", "cancelled",
        name="flightstatus", create_constraint=True, create_type=False,
    )
    matchstatus = sa.Enum(
        "pending", "accepted", "declined", "counter",
        name="matchstatus", create_constraint=True, create_type=False,
    )
    subscriptionplan = sa.Enum(
        "monthly", "quarterly", "yearly", "trial",
        name="subscriptionplan", create_constraint=True, create_type=False,
    )
    paymentmethod = sa.Enum("stars", "ton", name="paymentmethod", create_constraint=True, create_type=False)
    paymentstatus = sa.Enum(
        "pending", "completed", "failed", "refunded",
        name="paymentstatus", create_constraint=True, create_type=False,
    )

    # --- 1. users ---
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("role", userrole, nullable=False, server_default="sender"),
        sa.Column("rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("deliveries_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reviews_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("bot_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("lang", sa.String(5), nullable=False, server_default="ru"),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("avatar_file_id", sa.String(200), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 2. cities (нет FK, можно создавать рано) ---
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name_en", sa.String(100), nullable=False, unique=True),
        sa.Column("name_ru", sa.String(100), nullable=False),
        sa.Column("name_kz", sa.String(100), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("flag", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
    )

    # --- 3. parcels (FK → users) ---
    op.create_table(
        "parcels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sender_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("traveler_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("from_city", sa.String(100), nullable=False, index=True),
        sa.Column("to_city", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("size", parcelsize, nullable=False, server_default="medium"),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("accepted_price", sa.Float(), nullable=True),
        sa.Column("photo_file_ids", sa.Text(), nullable=True),
        sa.Column("status", parcelstatus, nullable=False, server_default="pending", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 4. flights (FK → users) ---
    op.create_table(
        "flights",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("traveler_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("from_city", sa.String(100), nullable=False, index=True),
        sa.Column("to_city", sa.String(100), nullable=False, index=True),
        sa.Column("flight_date", sa.Date(), nullable=False, index=True),
        sa.Column("flight_number", sa.String(20), nullable=True),
        sa.Column("available_kg", sa.Float(), nullable=False),
        sa.Column("total_kg", sa.Float(), nullable=False),
        sa.Column("price_per_kg", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", flightstatus, nullable=False, server_default="active", index=True),
        sa.Column("requests_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 5. matches (FK → parcels, flights) ---
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id"), nullable=False, index=True),
        sa.Column("flight_id", sa.Integer(), sa.ForeignKey("flights.id"), nullable=False, index=True),
        sa.Column("status", matchstatus, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 6. relay_messages (FK → users, parcels) ---
    op.create_table(
        "relay_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.Integer(), nullable=False, index=True),
        sa.Column("sender_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("receiver_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id"), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("offer_price", sa.Float(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 7. reviews (FK → users, parcels) ---
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("author_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("target_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("parcel_id", sa.Integer(), sa.ForeignKey("parcels.id"), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 8. subscriptions (FK → users) ---
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("plan", subscriptionplan, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 9. payments (FK → users, subscriptions) ---
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("method", paymentmethod, nullable=False),
        sa.Column("status", paymentstatus, nullable=False, server_default="pending"),
        sa.Column("transaction_id", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- 10. route_votes (FK → users, UniqueConstraint) ---
    op.create_table(
        "route_votes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("route_name", sa.String(200), nullable=False, index=True),
        sa.Column("votes_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "route_name", name="uq_user_route_vote"),
    )


def downgrade() -> None:
    """Удаление всех таблиц и enum-типов (в обратном порядке зависимостей)."""

    # Сначала таблицы с FK, потом базовые
    op.drop_table("route_votes")
    op.drop_table("payments")
    op.drop_table("subscriptions")
    op.drop_table("reviews")
    op.drop_table("relay_messages")
    op.drop_table("matches")
    op.drop_table("flights")
    op.drop_table("parcels")
    op.drop_table("cities")
    op.drop_table("users")

    # Удаление enum-типов
    sa.Enum(name="paymentstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="paymentmethod").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscriptionplan").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="matchstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="flightstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="parcelsize").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="parcelstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
