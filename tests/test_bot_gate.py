"""Тонкий бот: белый список сообщений и кнопка запуска."""
import pytest

from bot.middlewares.gate import is_allowed


def test_commands_contact_and_payment_pass():
    assert is_allowed("/start", False, False, None)
    assert is_allowed("/start parcel_1", False, False, None)
    assert is_allowed(None, True, False, None)
    assert is_allowed(None, False, True, None)


def test_plain_text_blocked_unless_bot_waits():
    assert not is_allowed("Привет", False, False, None)
    assert not is_allowed("Отправить посылку", False, False, None)
    assert not is_allowed(None, False, False, None)
    # Бот ждёт ответ (онбординг или ответ поддержки) — пропускаем
    assert is_allowed("Текст ответа", False, False, "SupportReply:waiting_text")


def test_open_app_keyboard(monkeypatch):
    from bot.keyboards import webapp_kb
    monkeypatch.setattr(webapp_kb, "WEBAPP_URL", "https://fly.example.com")
    kb = webapp_kb.open_app_keyboard("ru", "parcel_5")
    button = kb.inline_keyboard[0][0]
    assert button.web_app.url == "https://fly.example.com/parcels/5"
    assert "посылку" in button.text
    assert webapp_kb.open_app_keyboard("en").inline_keyboard[0][0].web_app.url == "https://fly.example.com/"

    monkeypatch.setattr(webapp_kb, "WEBAPP_URL", "")
    assert webapp_kb.open_app_keyboard("ru") is None


@pytest.mark.asyncio
async def test_setup_bot_ui_sets_menu_button(monkeypatch):
    """При старте бот ставит Menu Button на Mini App и список команд."""
    from bot import main as bot_main

    calls = []

    class FakeBot:
        async def set_chat_menu_button(self, menu_button):
            calls.append(("menu", menu_button.web_app.url))

        async def set_my_commands(self, commands):
            calls.append(("commands", [c.command for c in commands]))

    monkeypatch.setattr(bot_main, "WEBAPP_URL", "https://fly.example.com")
    await bot_main._setup_bot_ui(FakeBot())
    assert calls[0] == ("menu", "https://fly.example.com")
    assert calls[1] == ("commands", ["app", "lang", "help"])
