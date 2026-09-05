"""Мост чата поддержки в KVD Ads Panel: выключен без настроек, ретраи, payload."""

from datetime import datetime, timezone

import pytest

from backend.app.config import settings
from backend.app.services import crm_bridge as bridge_module
from backend.app.services.crm_bridge import CrmBridge, CrmEvent, SENDER_USER


def _event() -> CrmEvent:
    return CrmEvent(
        sender=SENDER_USER, user_id=42, text="Где моя посылка?", external_id=7, session_id=3,
        created_at=datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc),
        client={"first_name": "Али", "role": "sender"},
    )


class _Resp:
    def __init__(self, status: int, text: str = ""):
        self.status_code = status
        self.text = text


class _FakeClient:
    """Подмена httpx.AsyncClient: отдаёт заранее заданные статусы по очереди."""
    statuses: list[int] = []
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeClient.calls.append({"url": url, "json": json, "headers": headers})
        return _Resp(_FakeClient.statuses.pop(0))


@pytest.fixture
def fake_http(monkeypatch):
    """HTTP без сети и без пауз между попытками."""
    _FakeClient.statuses = []
    _FakeClient.calls = []
    monkeypatch.setattr(bridge_module.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(bridge_module, "RETRY_DELAYS", (0, 0, 0))
    return _FakeClient


def test_payload_shape():
    """В CRM уходит всё, что нужно для треда и карточки."""
    payload = _event().to_payload()
    assert payload["event"] == "message"
    assert payload["sender"] == "user"
    assert payload["user_id"] == 42
    assert payload["external_id"] == "7"
    assert payload["created_at"].startswith("2026-09-06T10:00")
    assert payload["client"]["role"] == "sender"


def test_disabled_without_settings(monkeypatch):
    """Нет URL или ключа — ни одной задачи и ни одного запроса."""
    monkeypatch.setattr(settings, "crm_ingest_url", "")
    monkeypatch.setattr(settings, "crm_api_key", "k")
    assert CrmBridge().enabled is False
    assert CrmBridge().schedule(_event()) is None


@pytest.mark.asyncio
async def test_send_success_with_key_header(monkeypatch, fake_http):
    monkeypatch.setattr(settings, "crm_ingest_url", "https://cabinet/api/v1/crm/ingest")
    monkeypatch.setattr(settings, "crm_api_key", "secret")
    fake_http.statuses = [200]

    assert await CrmBridge().send(_event()) is True
    assert len(fake_http.calls) == 1
    assert fake_http.calls[0]["headers"] == {"X-API-Key": "secret"}
    assert fake_http.calls[0]["url"] == "https://cabinet/api/v1/crm/ingest"


@pytest.mark.asyncio
async def test_send_retries_on_5xx(monkeypatch, fake_http):
    """Временная ошибка панели — повторяем, пока не примет."""
    monkeypatch.setattr(settings, "crm_ingest_url", "https://cabinet/ingest")
    monkeypatch.setattr(settings, "crm_api_key", "secret")
    fake_http.statuses = [502, 503, 200]

    assert await CrmBridge().send(_event()) is True
    assert len(fake_http.calls) == 3


@pytest.mark.asyncio
async def test_send_gives_up_on_4xx(monkeypatch, fake_http):
    """Неверный ключ — повторять бессмысленно, одна попытка."""
    monkeypatch.setattr(settings, "crm_ingest_url", "https://cabinet/ingest")
    monkeypatch.setattr(settings, "crm_api_key", "wrong")
    fake_http.statuses = [403]

    assert await CrmBridge().send(_event()) is False
    assert len(fake_http.calls) == 1


@pytest.mark.asyncio
async def test_schedule_runs_in_background(monkeypatch, fake_http):
    monkeypatch.setattr(settings, "crm_ingest_url", "https://cabinet/ingest")
    monkeypatch.setattr(settings, "crm_api_key", "secret")
    fake_http.statuses = [200]

    task = CrmBridge().schedule(_event())
    assert task is not None
    assert await task is True
