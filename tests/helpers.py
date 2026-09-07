"""Общие помощники API-тестов: клиент к приложению и токены."""

import httpx

from backend.app.database import get_session
from backend.app.dependencies import create_access_token
from backend.app.main import app


def make_client(session) -> httpx.AsyncClient:
    """HTTP-клиент к приложению с подменённой сессией БД."""

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def auth(user_id: int) -> dict:
    """Заголовок авторизации для пользователя."""
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}
