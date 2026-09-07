"""Админ-панель: доступ, пользователи, посылки, группы, рассылка."""

from datetime import date, timedelta

import pytest

from backend.app.config import settings
from backend.app.main import app
from backend.app.services import admin_service, crosspost_service, notification_service
from shared.models.flight import Flight, FlightStatus
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.promo_chat import GroupPost, PromoChat
from shared.models.report import Report, ReportReason, ReportStatus
from shared.models.user import User, UserRole
from helpers import auth, make_client

OWNER = 777
PANEL_ADMIN = 5
PLAIN = 9


@pytest.fixture
async def client(session, monkeypatch):
    """Клиент с владельцем из .env, админом из панели и обычным пользователем."""
    monkeypatch.setattr(settings, "admin_ids", str(OWNER))
    session.add_all([
        User(id=OWNER, first_name="Owner", lang="ru"),
        User(id=PANEL_ADMIN, first_name="Panel", is_admin=True, lang="ru"),
        User(id=PLAIN, first_name="Plain", username="plain_user", phone="+77010000000", lang="ru"),
    ])
    await session.commit()
    async with make_client(session) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_access(client):
    """Без токена 401, обычному 403, владельцу и админу из панели 200."""
    assert (await client.get("/api/v1/admin/me")).status_code == 401
    assert (await client.get("/api/v1/admin/me", headers=auth(PLAIN))).status_code == 403
    resp = await client.get("/api/v1/admin/me", headers=auth(OWNER))
    assert resp.status_code == 200 and resp.json()["is_env_admin"] is True
    resp = await client.get("/api/v1/admin/me", headers=auth(PANEL_ADMIN))
    assert resp.status_code == 200 and resp.json()["is_env_admin"] is False


@pytest.mark.asyncio
async def test_me_exposes_is_admin_and_phone(client):
    """Свой профиль отдаёт признак админа и телефон, чужой — нет."""
    me = (await client.get("/api/v1/users/me", headers=auth(PANEL_ADMIN))).json()
    assert me["is_admin"] is True
    plain = (await client.get("/api/v1/users/me", headers=auth(PLAIN))).json()
    assert plain["is_admin"] is False and plain["phone"] == "+77010000000"
    public = (await client.get(f"/api/v1/users/{PLAIN}", headers=auth(PANEL_ADMIN))).json()
    assert "phone" not in public


@pytest.mark.asyncio
async def test_stats(client, session):
    """Сводка считает людей и посылки."""
    session.add(Parcel(sender_id=PLAIN, from_city="Dubai", to_city="Almaty", description="Док",
                       weight=1, price=10, status=ParcelStatus.PENDING))
    await session.commit()
    stats = (await client.get("/api/v1/admin/stats", headers=auth(OWNER))).json()
    assert stats["users"]["total"] == 3
    assert stats["users"]["with_phone"] == 1
    assert stats["parcels"]["open"] == 1


@pytest.mark.asyncio
async def test_user_search_and_block(client, session, monkeypatch):
    """Поиск по username и телефону; блокировка закрывает API и шлёт уведомление."""
    sent = []
    monkeypatch.setattr(notification_service, "notify_admin_block", lambda u, b: sent.append((u.id, b)))

    found = (await client.get("/api/v1/admin/users", params={"q": "plain"}, headers=auth(OWNER))).json()
    assert [u["id"] for u in found["items"]] == [PLAIN]
    found = (await client.get("/api/v1/admin/users", params={"q": "7701"}, headers=auth(OWNER))).json()
    assert found["total"] == 1

    resp = await client.post(f"/api/v1/admin/users/{PLAIN}/block", json={"value": True}, headers=auth(OWNER))
    assert resp.status_code == 200 and resp.json()["is_blocked"] is True
    assert sent == [(PLAIN, True)]

    # Заблокированный больше не проходит авторизацию
    assert (await client.get("/api/v1/users/me", headers=auth(PLAIN))).status_code == 403

    # Себя и владельца блокировать нельзя
    resp = await client.post(f"/api/v1/admin/users/{OWNER}/block", json={"value": True}, headers=auth(PANEL_ADMIN))
    assert resp.status_code == 400 and resp.json()["detail"] == "cannot_block_admin"

    blocked = (await client.get("/api/v1/admin/users", params={"only": "blocked"}, headers=auth(OWNER))).json()
    assert blocked["total"] == 1


@pytest.mark.asyncio
async def test_admin_roles(client):
    """Назначение и снятие админа; владельца из .env снять нельзя."""
    resp = await client.post(f"/api/v1/admin/users/{PLAIN}/admin", json={"value": True}, headers=auth(OWNER))
    assert resp.json()["is_admin"] is True
    assert (await client.get("/api/v1/admin/me", headers=auth(PLAIN))).status_code == 200

    resp = await client.post(f"/api/v1/admin/users/{OWNER}/admin", json={"value": False}, headers=auth(PLAIN))
    assert resp.status_code == 400 and resp.json()["detail"] == "cannot_revoke_env_admin"

    resp = await client.post(f"/api/v1/admin/users/{PLAIN}/admin", json={"value": False}, headers=auth(OWNER))
    assert resp.json()["is_admin"] is False
    assert (await client.get("/api/v1/admin/me", headers=auth(PLAIN))).status_code == 403


@pytest.mark.asyncio
async def test_balance_adjust(client, session, monkeypatch):
    """Ручное начисление и списание проходят через сервис баланса."""
    monkeypatch.setattr(notification_service, "notify_admin_balance", lambda *a: None)
    resp = await client.post(f"/api/v1/admin/users/{PLAIN}/balance", json={"delta": 50, "note": "бонус"}, headers=auth(OWNER))
    assert resp.status_code == 200 and resp.json()["balance_stars"] == 50
    resp = await client.post(f"/api/v1/admin/users/{PLAIN}/balance", json={"delta": -20}, headers=auth(OWNER))
    assert resp.json()["balance_stars"] == 30
    resp = await client.post(f"/api/v1/admin/users/{PLAIN}/balance", json={"delta": -100}, headers=auth(OWNER))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_parcels_flights_cancel_close_posts(client, session):
    """Принудительная отмена закрывает объявления в группах."""
    parcel = Parcel(sender_id=PLAIN, from_city="Dubai", to_city="Almaty", description="Док",
                    weight=1, price=10, status=ParcelStatus.PENDING)
    flight = Flight(traveler_id=PLAIN, from_city="Dubai", to_city="Almaty",
                    flight_date=date.today() + timedelta(days=2), available_kg=5, total_kg=5,
                    price_per_kg=8, status=FlightStatus.ACTIVE)
    session.add_all([parcel, flight])
    await session.commit()
    session.add_all([
        GroupPost(chat_id=-1, message_id=1, kind="parcel", entity_id=parcel.id),
        GroupPost(chat_id=-1, message_id=2, kind="flight", entity_id=flight.id),
    ])
    await session.commit()

    listed = (await client.get("/api/v1/admin/parcels", params={"status": "pending"}, headers=auth(OWNER))).json()
    assert listed["total"] == 1 and listed["items"][0]["sender_name"] == "Plain"

    resp = await client.post(f"/api/v1/admin/parcels/{parcel.id}/cancel", headers=auth(OWNER))
    assert resp.json()["status"] == "cancelled"
    resp = await client.post(f"/api/v1/admin/flights/{flight.id}/cancel", headers=auth(OWNER))
    assert resp.json()["status"] == "cancelled"
    # Повторная отмена — ошибка
    assert (await client.post(f"/api/v1/admin/parcels/{parcel.id}/cancel", headers=auth(OWNER))).status_code == 400

    posts = (await session.execute(__import__("sqlalchemy").select(GroupPost))).scalars().all()
    assert all(p.is_closed for p in posts)


@pytest.mark.asyncio
async def test_reports_resolve(client, session):
    """Жалобы видны и закрываются."""
    session.add(Report(author_id=OWNER, target_id=PLAIN, reason=ReportReason.RUDE, status=ReportStatus.OPEN))
    await session.commit()
    items = (await client.get("/api/v1/admin/reports", headers=auth(OWNER))).json()["items"]
    assert len(items) == 1 and items[0]["target_name"] == "Plain"
    resp = await client.post(f"/api/v1/admin/reports/{items[0]['id']}/resolve", json={"status": "confirmed"}, headers=auth(OWNER))
    assert resp.json()["status"] == "confirmed"
    assert (await client.get("/api/v1/admin/reports", headers=auth(OWNER))).json()["items"] == []


@pytest.mark.asyncio
async def test_groups_crud(client, session, monkeypatch):
    """Подключение по ссылке через getChat, настройки, удаление."""
    async def fake_get_chat(method, payload):
        assert method == "getChat" and payload["chat_id"] == "@dxb_parcels"
        return {"id": -100123, "type": "supergroup", "title": "Посылки Дубай", "username": "dxb_parcels"}
    monkeypatch.setattr(crosspost_service, "call_api", fake_get_chat)
    monkeypatch.setattr(settings, "bot_token", "token")

    resp = await client.post("/api/v1/admin/groups", json={"link": "https://t.me/dxb_parcels"}, headers=auth(OWNER))
    assert resp.status_code == 201
    group = resp.json()
    assert group["chat_id"] == -100123 and group["is_member"] and group["post_parcels"]

    resp = await client.post("/api/v1/admin/groups", json={"link": "https://t.me/+invite"}, headers=auth(OWNER))
    assert resp.status_code == 400 and resp.json()["detail"] == "invite_link"

    resp = await client.patch(f"/api/v1/admin/groups/{group['id']}", json={"post_parcels": False, "cities": "Dubai"}, headers=auth(OWNER))
    assert resp.json()["post_parcels"] is False and resp.json()["cities"] == "Dubai"

    items = (await client.get("/api/v1/admin/groups", headers=auth(OWNER))).json()["items"]
    assert len(items) == 1

    assert (await client.delete(f"/api/v1/admin/groups/{group['id']}", headers=auth(OWNER))).status_code == 200
    assert (await client.get("/api/v1/admin/groups", headers=auth(OWNER))).json()["items"] == []


@pytest.mark.asyncio
async def test_broadcast(client, session, monkeypatch):
    """Рассылка идёт только тем, кто не заблокирован и не скрыл бота."""
    sent = []
    monkeypatch.setattr(notification_service, "notify", lambda u, t, m=None: sent.append(u.id))
    session.add(User(id=11, first_name="Hidden", bot_blocked=True, role=UserRole.TRAVELER))
    session.add(User(id=12, first_name="Trav", role=UserRole.TRAVELER))
    await session.commit()

    resp = await client.post("/api/v1/admin/broadcast", json={"audience": "travelers", "text": "Привет"}, headers=auth(OWNER))
    assert resp.status_code == 200 and resp.json()["sent"] == 1 and sent == [12]
    resp = await client.post("/api/v1/admin/broadcast", json={"audience": "all", "text": "Привет"}, headers=auth(OWNER))
    assert resp.json()["sent"] == 4


@pytest.mark.asyncio
async def test_support_inbox(client, session, monkeypatch):
    """Инбокс: обращение видно, ответ ложится в переписку, закрытие уводит в архив."""
    from backend.app.services import support_service
    monkeypatch.setattr(support_service.crm_bridge, "schedule", lambda e: None)
    user = await session.get(User, PLAIN)
    await support_service.send_user_message(session, user, "Помогите")

    items = (await client.get("/api/v1/admin/support/sessions", headers=auth(OWNER))).json()["items"]
    assert len(items) == 1 and items[0]["user_id"] == PLAIN and items[0]["is_pending"]

    resp = await client.post(f"/api/v1/admin/support/{PLAIN}/reply", json={"text": "Уже смотрим"}, headers=auth(OWNER))
    assert resp.status_code == 200
    msgs = (await client.get(f"/api/v1/admin/support/{PLAIN}/messages", headers=auth(OWNER))).json()["items"]
    assert [m["sender_role"] for m in msgs] == ["user", "admin"]

    assert (await client.post(f"/api/v1/admin/support/{PLAIN}/close", headers=auth(OWNER))).json()["ok"] is True
    assert (await client.get("/api/v1/admin/support/sessions", headers=auth(OWNER))).json()["items"] == []
    archived = (await client.get("/api/v1/admin/support/sessions", params={"status": "archived"}, headers=auth(OWNER))).json()["items"]
    assert len(archived) == 1
