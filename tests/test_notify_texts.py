"""Тесты текстов уведомлений."""

from shared.locale.notify_texts import NOTIFY_TEXTS, nt


def test_all_keys_have_both_languages():
    """Каждый текст должен быть и на русском, и на английском."""
    missing = [k for k, v in NOTIFY_TEXTS.items() if "ru" not in v or "en" not in v]
    assert missing == []


def test_formats_values():
    """Подстановка значений работает."""
    text = nt("ru", "handover_code", code="4821")
    assert "4821" in text


def test_falls_back_to_russian():
    """Неизвестный язык откатывается на русский, а не ломается."""
    assert nt("kz", "btn_open_app") == NOTIFY_TEXTS["btn_open_app"]["ru"]
    assert nt(None, "btn_open_app") == NOTIFY_TEXTS["btn_open_app"]["ru"]


def test_missing_key_returns_key():
    """Неизвестный ключ не роняет отправку уведомления."""
    assert nt("ru", "нет_такого_ключа") == "нет_такого_ключа"


def test_missing_placeholder_does_not_crash():
    """Не хватило подстановки — отдаём шаблон, а не исключение."""
    result = nt("ru", "handover_code")
    assert "{code}" in result
