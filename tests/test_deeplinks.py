"""Диплинки: один параметр — один экран для бота, групп и Mini App."""

from shared import deeplinks


def test_entity_params_map_to_paths():
    assert deeplinks.screen_path("parcel_12") == "/parcels/12"
    assert deeplinks.screen_path("flight_7") == "/flights/7"
    assert deeplinks.screen_path("profile_3") == "/profile/3"
    assert deeplinks.screen_path("chat_9") == "/chats/9"


def test_named_screens_and_fallback():
    assert deeplinks.screen_path("publish") == "/publish-flight"
    assert deeplinks.screen_path("admin_groups") == "/admin?tab=groups"
    assert deeplinks.screen_path(None) == "/"
    assert deeplinks.screen_path("hack_1") == "/"
    assert deeplinks.screen_path("parcel_abc") == "/"


def test_validity():
    assert deeplinks.is_valid_param("parcel_1")
    assert deeplinks.is_valid_param("admin")
    assert not deeplinks.is_valid_param("")
    assert not deeplinks.is_valid_param("parcel_")
    assert not deeplinks.is_valid_param("x" * 50)


def test_urls():
    assert deeplinks.startapp_url("parcel_bot", "parcel_5") == "https://t.me/parcel_bot?startapp=parcel_5"
    assert deeplinks.startapp_url("@parcel_bot") == "https://t.me/parcel_bot"
    assert deeplinks.startapp_url("", "parcel_5") is None
    assert deeplinks.start_url("parcel_bot", "flight_2") == "https://t.me/parcel_bot?start=flight_2"
    assert deeplinks.webapp_url("https://fly.example.com/", "flight_2") == "https://fly.example.com/flights/2"
    assert deeplinks.webapp_url("http://localhost", "flight_2") is None
