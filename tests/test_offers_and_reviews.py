"""Отклики перевозчиков на посылки, режим пользователя, ответы на отзывы."""

from datetime import date, timedelta

import pytest

from backend.app.config import settings
from backend.app.main import app
from backend.app.services import notification_service
from shared.models.flight import Flight, FlightStatus
from shared.models.match import Match
from shared.models.parcel import Parcel, ParcelStatus
from shared.models.review import Review
from shared.models.user import User
from helpers import auth, make_client

SENDER = 1
TRAVELER = 2
OTHER = 3


@pytest.fixture
async def client(session, monkeypatch):
    """Отправитель с посылкой, перевозчик с рейсом, посторонний."""
    # Пробный период: отклики без оплаты
    monkeypatch.setattr(settings, "free_access_until", "2099-01-01")
    session.add_all([
        User(id=SENDER, first_name="Sender", lang="ru"),
        User(id=TRAVELER, first_name="Trav", lang="ru", trial_days_left=5),
        User(id=OTHER, first_name="Other", lang="ru"),
    ])
    session.add(Parcel(sender_id=SENDER, from_city="Dubai", to_city="Almaty", description="Документы",
                       weight=1, price=20, status=ParcelStatus.PENDING))
    session.add(Flight(traveler_id=TRAVELER, from_city="Dubai", to_city="Almaty",
                       flight_date=date.today() + timedelta(days=3), available_kg=10, total_kg=10,
                       price_per_kg=9, status=FlightStatus.ACTIVE))
    await session.commit()
    async with make_client(session) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_offer_flow_sender_accepts(client, session, monkeypatch):
    """Перевозчик откликнулся → отправитель видит отклик → принимает → посылка его."""
    events = []
    monkeypatch.setattr(notification_service, "notify_offer_received", _rec(events, "received"))
    monkeypatch.setattr(notification_service, "notify_offer_accepted", _rec(events, "accepted"))

    # Карточку посылки перевозчик видит с данными отправителя
    card = (await client.get("/api/v1/parcels/1", headers=auth(TRAVELER))).json()
    assert card["sender_name"] == "Sender"

    resp = await client.post("/api/v1/parcels/1/offer", json={"flight_id": 1}, headers=auth(TRAVELER))
    assert resp.status_code == 201 and resp.json()["initiator"] == "traveler"
    # Дубль запрещён
    assert (await client.post("/api/v1/parcels/1/offer", json={"flight_id": 1}, headers=auth(TRAVELER))).status_code == 400
    # Чужим рейсом откликнуться нельзя
    assert (await client.post("/api/v1/parcels/1/offer", json={"flight_id": 1}, headers=auth(OTHER))).status_code == 400

    offers = (await client.get("/api/v1/parcels/1/offers", headers=auth(SENDER))).json()
    assert offers["total"] == 1 and offers["items"][0]["traveler"]["name"] == "Trav"
    # Посторонний своих откликов не имеет — пустой список
    assert (await client.get("/api/v1/parcels/1/offers", headers=auth(OTHER))).json()["total"] == 0

    match_id = offers["items"][0]["id"]
    # Перевозчик сам принять свой отклик не может
    assert (await client.post(f"/api/v1/matches/{match_id}/accept", headers=auth(TRAVELER))).status_code == 400
    resp = await client.post(f"/api/v1/matches/{match_id}/accept", headers=auth(SENDER))
    assert resp.status_code == 200

    parcel = await session.get(Parcel, 1)
    await session.refresh(parcel)
    assert parcel.status == ParcelStatus.ACCEPTED and parcel.traveler_id == TRAVELER
    assert events == ["received", "accepted"]


@pytest.mark.asyncio
async def test_offer_declined_by_sender(client, session, monkeypatch):
    """Отправитель отклоняет отклик — перевозчик получает уведомление."""
    events = []
    monkeypatch.setattr(notification_service, "notify_offer_received", _rec(events, "received"))
    monkeypatch.setattr(notification_service, "notify_offer_declined", _rec(events, "declined"))

    match_id = (await client.post("/api/v1/parcels/1/offer", json={"flight_id": 1}, headers=auth(TRAVELER))).json()["id"]
    assert (await client.post(f"/api/v1/matches/{match_id}/decline", headers=auth(SENDER))).status_code == 200
    assert events == ["received", "declined"]
    assert (await session.get(Parcel, 1)).status == ParcelStatus.PENDING


@pytest.mark.asyncio
async def test_sender_request_still_accepted_by_traveler(client, session, monkeypatch):
    """Старый путь: заявка отправителя принимается хозяином рейса, не отправителем."""
    monkeypatch.setattr(notification_service, "notify_new_request", _rec([], "x"))
    monkeypatch.setattr(notification_service, "notify_request_accepted", _rec([], "x"))
    match_id = (await client.post("/api/v1/matches", json={"parcel_id": 1, "flight_id": 1}, headers=auth(SENDER))).json()["id"]
    assert (await client.post(f"/api/v1/matches/{match_id}/accept", headers=auth(SENDER))).status_code == 400
    assert (await client.post(f"/api/v1/matches/{match_id}/accept", headers=auth(TRAVELER))).status_code == 200


@pytest.mark.asyncio
async def test_create_parcel_with_flight_creates_request(client, session, monkeypatch):
    """Посылка, созданная с flight_id, сразу подаёт заявку на рейс."""
    monkeypatch.setattr(notification_service, "notify_new_request", _rec([], "x"))
    resp = await client.post("/api/v1/parcels", json={
        "from_city": "Dubai", "to_city": "Almaty", "description": "Подарок", "weight": 2, "price": 30, "flight_id": 1,
    }, headers=auth(SENDER))
    assert resp.status_code == 201
    from sqlalchemy import select
    matches = (await session.execute(select(Match).where(Match.parcel_id == resp.json()["id"]))).scalars().all()
    assert len(matches) == 1 and matches[0].initiator == "sender"


@pytest.mark.asyncio
async def test_role_mode_persists(client):
    """Режим «везу / отправляю» сохраняется в профиле."""
    resp = await client.put("/api/v1/users/me", json={"role": "traveler"}, headers=auth(SENDER))
    assert resp.status_code == 200 and resp.json()["role"] == "traveler"
    assert (await client.get("/api/v1/users/me", headers=auth(SENDER))).json()["role"] == "traveler"
    assert (await client.put("/api/v1/users/me", json={"role": "both"}, headers=auth(SENDER))).status_code == 422


@pytest.mark.asyncio
async def test_review_tags_and_reply(client, session, monkeypatch):
    """Отзыв с тегами; ответить может только получатель и только один раз."""
    notified = []
    monkeypatch.setattr(notification_service, "notify_review_replied", lambda a, t, x: notified.append((a.id, x)))
    parcel = await session.get(Parcel, 1)
    parcel.traveler_id = TRAVELER
    parcel.status = ParcelStatus.DELIVERED
    await session.commit()

    resp = await client.post(f"/api/v1/users/{TRAVELER}/reviews", json={
        "parcel_id": 1, "rating": 5, "comment": "Супер", "tags": ["on_time", "on_time", "bogus", "careful"],
    }, headers=auth(SENDER))
    assert resp.status_code == 201
    review = resp.json()
    assert review["tags"] == ["on_time", "careful"]

    # Автор отзыва ответить не может, посторонний тоже
    assert (await client.post(f"/api/v1/users/reviews/{review['id']}/reply", json={"text": "?"}, headers=auth(SENDER))).status_code == 403
    assert (await client.post(f"/api/v1/users/reviews/{review['id']}/reply", json={"text": "?"}, headers=auth(OTHER))).status_code == 403

    resp = await client.post(f"/api/v1/users/reviews/{review['id']}/reply", json={"text": "Спасибо!"}, headers=auth(TRAVELER))
    assert resp.status_code == 200 and resp.json()["reply_text"] == "Спасибо!"
    assert notified == [(SENDER, "Спасибо!")]
    # Второй ответ запрещён
    assert (await client.post(f"/api/v1/users/reviews/{review['id']}/reply", json={"text": "Ещё"}, headers=auth(TRAVELER))).status_code == 409

    listed = (await client.get(f"/api/v1/users/{TRAVELER}/reviews")).json()
    assert listed[0]["reply_text"] == "Спасибо!" and listed[0]["tags"] == ["on_time", "careful"]


def _rec(events, name):
    """Заглушка уведомления, запоминающая факт вызова."""
    async def _fake(*args, **kwargs):
        events.append(name)
    return _fake
