from __future__ import annotations

import importlib

import app.core.config as config_module


def test_settings_use_app_port_when_port_not_set(monkeypatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("APP_PORT", "8010")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_HOST", "")

    reloaded = importlib.reload(config_module)
    settings = reloaded.Settings()

    assert settings.app_port == 8010
    assert settings.app_host == "127.0.0.1"


def test_settings_port_takes_precedence_over_app_port(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("APP_PORT", "8010")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_HOST", "")

    reloaded = importlib.reload(config_module)
    settings = reloaded.Settings()

    assert settings.app_port == 10000
    assert settings.app_host == "0.0.0.0"


def test_settings_invalid_port_falls_back_to_app_port(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "not-a-number")
    monkeypatch.setenv("APP_PORT", "8010")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_HOST", "")

    reloaded = importlib.reload(config_module)
    settings = reloaded.Settings()

    assert settings.app_port == 8010
    assert settings.app_host == "0.0.0.0"


def test_settings_invalid_app_port_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("APP_PORT", "bad-value")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_HOST", "")

    reloaded = importlib.reload(config_module)
    settings = reloaded.Settings()

    assert settings.app_port == 8000
    assert settings.app_host == "127.0.0.1"