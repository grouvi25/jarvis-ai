"""Тесты конфигурации J.A.R.V.I.S."""

from jarvis.core.config import JarvisConfig, load_config


def test_load_default_config() -> None:
    """Загрузка дефолтного конфига."""
    config = load_config()
    assert isinstance(config, JarvisConfig)
    assert config.language == "ru"
    assert "джарвис" in config.wake_words
    assert config.llm.provider == "omniroute"
    assert config.stt.language == "ru"
    assert config.tts.engine == "edge-tts"


def test_config_defaults() -> None:
    """Дефолтные значения конфига."""
    config = JarvisConfig()
    assert config.language == "ru"
    assert config.name == "Джарвис"
    assert config.master_name == "сэр"
    assert config.llm.model == "gpt-4o-mini"
    assert config.internet.check_interval == 300


def test_config_wake_words() -> None:
    """Wake words содержат русский и английский варианты."""
    config = load_config()
    wake_lower = [w.lower() for w in config.wake_words]
    assert "джарвис" in wake_lower
    assert "jarvis" in wake_lower
