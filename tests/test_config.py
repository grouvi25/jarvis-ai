"""Тесты конфигурации J.A.R.V.I.S."""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.core.config import JarvisConfig, _dict_to_config, load_config, save_config


def test_load_default_config() -> None:
    config = load_config()
    assert isinstance(config, JarvisConfig)
    assert config.language == "ru"
    assert "джарвис" in config.wake_words
    assert config.llm.provider == "omniroute"
    assert config.stt.language == "ru"
    assert config.tts.engine == "edge-tts"


def test_config_defaults() -> None:
    config = JarvisConfig()
    assert config.language == "ru"
    assert config.name == "Джарвис"
    assert config.master_name == "сэр"
    assert config.llm.model == "gpt-4o-mini"
    assert config.internet.check_interval == 300
    assert config.server.port == 8765


def test_config_wake_words() -> None:
    config = load_config()
    wake_lower = [w.lower() for w in config.wake_words]
    assert "джарвис" in wake_lower
    assert "jarvis" in wake_lower


def test_dict_to_config_partial() -> None:
    cfg = _dict_to_config(
        {
            "general": {"name": "Алиса", "master_name": "босс"},
            "llm": {"model": "gpt-4o", "api_key": "secret"},
            "server": {"port": 9999},
        }
    )
    assert cfg.name == "Алиса"
    assert cfg.master_name == "босс"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.llm.api_key == "secret"
    assert cfg.server.port == 9999


def test_save_and_reload(tmp_path: Path) -> None:
    cfg = JarvisConfig(name="TestBot", master_name="командир")
    cfg.llm.api_key = "deadbeef"
    target = tmp_path / "out.yaml"
    save_config(cfg, target=target)
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "TestBot" in content
    assert "deadbeef" in content


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_LLM_MODEL", "test-model")
    monkeypatch.setenv("JARVIS_SERVER_PORT", "1234")
    cfg = load_config()
    assert cfg.llm.model == "test-model"
    assert cfg.server.port == 1234
