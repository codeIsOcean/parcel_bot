"""Админ-панель Mini App: /api/v1/admin/*.

Тонкие роуты: проверка доступа, разбор параметров, вызов admin_service /
crosspost_service / support_service. Доступ — владельцы из ADMIN_IDS и
пользователи с флагом is_admin.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_session
from backend.app.dependencies import get_current_user
from backend.app.services import admin_service, crosspost_service, support_service
from backend.app.services.admin_service import AdminActionError
from shared.models.chat import SupportSession
from shared.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency — только администратор."""
    if not admin_service.is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def _raise(e: AdminActionError):
    """Ошибку сервиса переводим в HTTP-ответ с кодом причины."""
    raise HTTPException(status_code=e.status, detail=e.reason)


# === Схемы ===

class FlagRequest(BaseModel):
    """Включить или выключить флаг."""
    value: bool = True


class BalanceRequest(BaseModel):
    """Ручное изменение баланса."""
    delta: int = Field(ne=0, ge=-100000, le=100000)
    note: str | None = Field(default=None, max_length=200)


class ReportResolveRequest(BaseModel):
    """Закрытие жалобы."""
    status: str = Field(pattern="^(reviewed|confirmed)$")


class BroadcastRequest(BaseModel):
    """Рассылка."""
    audience: str = Field(pattern="^(all|senders|travelers|with_phone)$")
    text: str = Field(min_length=1, max_length=4000)


class GroupAddRequest(BaseModel):
    """Подключение группы по ссылке, @username или ID."""
    link: str = Field(min_length=1, max_length=200)


class GroupUpdateRequest(BaseModel):
    """Настройки группы."""
    is_active: bool | None = None
    post_parcels: bool | None = None
    post_flights: bool | None = None
    cities: str | None = Field(default=None, max_length=1000)
    title: str | None = Field(default=None, max_length=200)


class SupportReplyRequest(BaseModel):
    """Ответ пользователю в поддержку."""
    text: str = Field(min_length=1, max_length=4000)


# === Доступ и статистика ===

@router.get("/me")
async def admin_me(admin: User = Depends(get_current_admin)):
    """Проверка доступа — фронт открывает панель только после 200."""
    return {"id": admin.id, "is_env_admin": admin_service.is_env_admin(admin.id)}


@router.get("/stats")
async def stats(admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session)):
    """Сводка по сервису."""
    return await admin_service.get_stats(session)


# === Пользователи ===

@router.get("/users")
async def users(
    q: str | None = Query(None, max_length=100),
    only: str | None = Query(None, pattern="^(blocked|admins|travelers|reported)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Поиск и список пользователей."""
    rows, total = await admin_service.search_users(session, q=q, only=only, page=page, limit=limit)
    return {"items": [admin_service.user_row(u) for u in rows], "total": total, "page": page, "limit": limit}


@router.get("/users/{user_id}")
async def user_detail(
    user_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Карточка пользователя с его посылками, рейсами и жалобами."""
    try:
        user = await admin_service.get_user(session, user_id)
    except AdminActionError as e:
        _raise(e)

    parcels, _ = await admin_service.list_parcels(session, q=str(user_id), limit=10)
    flights, _ = await admin_service.list_flights(session, q=str(user_id), limit=10)
    reports = [r for r in await admin_service.list_reports(session, status=None) if r["target_id"] == user_id]
    return {
        "user": admin_service.user_row(user),
        # Поиск по id находит и чужие посылки с таким id — оставляем только свои
        "parcels": [p for p in parcels if user_id in (p["sender_id"], p["traveler_id"])],
        "flights": [f for f in flights if f["traveler_id"] == user_id],
        "reports": reports[:10],
    }


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: int, data: FlagRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Заблокировать (value=true) или разблокировать."""
    try:
        user = await admin_service.set_blocked(session, admin, user_id, data.value)
    except AdminActionError as e:
        _raise(e)
    return admin_service.user_row(user)


@router.post("/users/{user_id}/verify")
async def verify_user(
    user_id: int, data: FlagRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Поставить или снять галочку проверенного."""
    try:
        user = await admin_service.set_verified(session, admin, user_id, data.value)
    except AdminActionError as e:
        _raise(e)
    return admin_service.user_row(user)


@router.post("/users/{user_id}/admin")
async def set_admin(
    user_id: int, data: FlagRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Назначить или снять администратора."""
    try:
        user = await admin_service.set_admin(session, admin, user_id, data.value)
    except AdminActionError as e:
        _raise(e)
    return admin_service.user_row(user)


@router.post("/users/{user_id}/balance")
async def adjust_balance(
    user_id: int, data: BalanceRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Начислить или списать звёзды вручную."""
    try:
        balance = await admin_service.adjust_balance(session, admin, user_id, data.delta, data.note)
    except AdminActionError as e:
        _raise(e)
    return {"balance_stars": balance}


# === Посылки и рейсы ===

@router.get("/parcels")
async def parcels(
    status: str | None = Query(None, max_length=20),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Все посылки с фильтром по статусу и поиском."""
    items, total = await admin_service.list_parcels(session, status=status, q=q, page=page, limit=limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/parcels/{parcel_id}/cancel")
async def cancel_parcel(
    parcel_id: int,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Принудительно отменить посылку."""
    try:
        parcel = await admin_service.cancel_parcel(session, admin, parcel_id)
    except AdminActionError as e:
        _raise(e)
    return {"id": parcel.id, "status": parcel.status.value}


@router.get("/flights")
async def flights(
    status: str | None = Query(None, max_length=20),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Все рейсы с фильтром по статусу и поиском."""
    items, total = await admin_service.list_flights(session, status=status, q=q, page=page, limit=limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/flights/{flight_id}/cancel")
async def cancel_flight(
    flight_id: int,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Принудительно отменить рейс."""
    try:
        flight = await admin_service.cancel_flight(session, admin, flight_id)
    except AdminActionError as e:
        _raise(e)
    return {"id": flight.id, "status": flight.status.value}


# === Жалобы и платежи ===

@router.get("/reports")
async def reports(
    status: str | None = Query("open", max_length=20),
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Жалобы. status=all — все."""
    return {"items": await admin_service.list_reports(session, status=None if status == "all" else status)}


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int, data: ReportResolveRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Закрыть жалобу."""
    try:
        report = await admin_service.resolve_report(session, admin, report_id, data.status)
    except AdminActionError as e:
        _raise(e)
    return {"id": report.id, "status": report.status.value}


@router.get("/payments")
async def payments(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Платежи."""
    items, total = await admin_service.list_payments(session, page=page, limit=limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


# === Рассылка ===

@router.post("/broadcast")
async def broadcast(
    data: BroadcastRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Разослать сообщение аудитории."""
    try:
        sent = await admin_service.broadcast(session, admin, data.audience, data.text)
    except AdminActionError as e:
        _raise(e)
    return {"sent": sent}


# === Группы ===

def _group_row(chat) -> dict:
    """Карточка группы для панели."""
    return {
        "id": chat.id,
        "chat_id": chat.chat_id,
        "title": chat.title,
        "username": chat.username,
        "chat_type": chat.chat_type,
        "cities": chat.cities,
        "is_active": chat.is_active,
        "is_member": chat.is_member,
        "post_parcels": chat.post_parcels,
        "post_flights": chat.post_flights,
        "posts_count": chat.posts_count,
        "created_at": chat.created_at,
    }


@router.get("/groups")
async def groups(admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session)):
    """Реестр подключённых групп."""
    return {"items": [_group_row(c) for c in await crosspost_service.list_chats(session)]}


@router.post("/groups", status_code=201)
async def add_group(
    data: GroupAddRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Подключить группу по ссылке. Бот уже должен быть в ней."""
    result = await crosspost_service.resolve_link(session, data.link, added_by=admin.id)
    if not result.chat:
        # Причина уходит фронту как код: bad_link / invite_link / not_found / not_group / no_token
        raise HTTPException(status_code=400, detail=result.reason)
    return _group_row(result.chat)


@router.patch("/groups/{group_id}")
async def update_group(
    group_id: int, data: GroupUpdateRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Настройки группы: включена, что постить, фильтр городов."""
    chat = await crosspost_service.get_chat(session, group_id)
    if not chat:
        raise HTTPException(status_code=404, detail="group_not_found")
    chat = await crosspost_service.update_chat(session, chat, **data.model_dump(exclude_none=True))
    return _group_row(chat)


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Удалить группу из реестра."""
    chat = await crosspost_service.get_chat(session, group_id)
    if not chat:
        raise HTTPException(status_code=404, detail="group_not_found")
    await crosspost_service.delete_chat(session, chat)
    return {"ok": True}


# === Поддержка ===

@router.get("/support/sessions")
async def support_sessions(
    status: str = Query("open", pattern="^(open|archived|all)$"),
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Инбокс поддержки: открытые, архив или все."""
    stmt = select(SupportSession)
    if status == "open":
        stmt = stmt.where(SupportSession.is_active == True)  # noqa: E712
    elif status == "archived":
        stmt = stmt.where(SupportSession.is_active == False)  # noqa: E712
    rows = (await session.execute(stmt.order_by(SupportSession.updated_at.desc()).limit(100))).scalars().all()

    items = []
    for ticket in rows:
        user = await session.get(User, ticket.user_id)
        items.append({
            "id": ticket.id,
            "user_id": ticket.user_id,
            "user_name": user.full_name if user else str(ticket.user_id),
            "username": user.username if user else None,
            "is_active": ticket.is_active,
            "is_pending": ticket.is_pending,
            "message_count": ticket.message_count,
            "updated_at": ticket.updated_at,
        })
    return {"items": items}


@router.get("/support/{user_id}/messages")
async def support_messages(
    user_id: int,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Переписка с пользователем."""
    messages = await support_service.get_messages(session, user_id)
    return {"items": [{
        "id": m.id, "sender_role": m.sender_role, "text": m.text, "created_at": m.created_at,
    } for m in messages]}


@router.post("/support/{user_id}/reply")
async def support_reply(
    user_id: int, data: SupportReplyRequest,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Ответить пользователю. Уходит ему в бот и зеркалится в CRM."""
    message = await support_service.send_admin_reply(session, admin.id, user_id, data.text)
    if not message:
        raise HTTPException(status_code=404, detail="no_ticket")
    return {"id": message.id, "created_at": message.created_at}


@router.post("/support/{user_id}/close")
async def support_close(
    user_id: int,
    admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session),
):
    """Закрыть обращение (в архив)."""
    ok = await support_service.close_session(session, user_id)
    return {"ok": ok}
