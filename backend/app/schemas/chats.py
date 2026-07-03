from datetime import datetime
from pydantic import BaseModel, Field


class MessageSend(BaseModel):
    """Отправка сообщения в чат."""
    text: str = Field(min_length=1, max_length=4000)


class PriceOffer(BaseModel):
    """Предложение цены (торг)."""
    price: float = Field(gt=0, le=10000)


class MessageResponse(BaseModel):
    """Сообщение в ответе."""
    id: int
    chat_id: int
    sender_id: int
    receiver_id: int
    text: str | None = None
    message_type: str
    offer_price: float | None = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatPreview(BaseModel):
    """Превью чата в списке."""
    chat_id: int
    partner_id: int
    partner_name: str
    partner_avatar: str | None = None
    last_message: str | None = None
    last_message_time: datetime | None = None
    unread_count: int = 0
    parcel_id: int | None = None
