"""Ответ оператора из KVD Ads Panel: вход по X-API-Key, запись в переписку."""

import httpx
import pytest
from sqlalchemy import select

from backend.app.config import settings
from backend.app.database import get_session
from backend.app.main import app
from backend.app.services import support_service
from shared.models.chat import SupportMessage
from shared.models.user import User

URL = "/api/v1/internal/crm/reply"


@pytest.fixture
async def client(session, monkeypatch):
    """HTTP-клиент к приложению с тестовой базой и включённым мостом."""
    monkeypatch.setattr(settings, "crm_ingest_url", "https://cabinet/ingest")
    monkeypatch.setattr(settings, "crm_api_key", "secret")
    monkeypatch.setattr(settings, "admin_ids", "777")

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reply_requires_key(client):
    assert (await client.post(URL, json={"user_id": 1, "text": "hi"})).status_code == 403
    assert (await client.post(URL, json={"user_id": 1, "text": "hi"}, headers={"X-API-Key": "nope"})).status_code == 403


@pytest.mark.asyncio
async def test_reply_hidden_when_bridge_off(client, monkeypatch):
    """Ключ не задан — эндпоинта как будто нет."""
    monkeypatch.setattr(settings, "crm_api_key", "")
    resp = await client.post(URL, json={"user_id": 1, "text": "hi"}, headers={"X-API-Key": ""})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reply_404_without_ticket(client):
    resp = await client.post(URL, json={"user_id": 5, "text": "hi"}, headers={"X-API-Key": "secret"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reply_lands_in_conversation(client, session, monkeypatch):
    """Ответ из панели — сообщение админа в переписке, в CRM обратно не уходит."""
    mirrored = []
    monkeypatch.setattr(support_service.crm_bridge, "schedule", lambda e: mirrored.append(e))

    user = User(id=5, first_name="Али", lang="ru")
    session.add(user)
    await session.commit()
    await support_service.send_user_message(session, user, "Где посылка?")
    mirrored.clear()

    resp = await client.post(URL, json={"user_id": 5, "text": "Уже в пути"}, headers={"X-API-Key": "secret"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True

    msg = await session.get(SupportMessage, body["message_id"])
    assert msg.sender_role == support_service.ROLE_ADMIN
    assert msg.text == "Уже в пути"
    assert msg.sender_id == 777
    # Ответ пришёл из CRM — обратно в CRM не зеркалим
    assert mirrored == []

    roles = [m.sender_role for m in (await session.execute(select(SupportMessage))).scalars()]
    assert roles == ["user", "admin"]
