"""Управление конфигурацией J.A.R.V.I.S.

Порядок поиска конфига:
1. Bundled `config/config.yaml` в репозитории — дефолты.
2. `~/.config/jarvis/config.yaml` (или эквивалент OS) — пользовательский.
3. `~/.config/jarvis/secrets.yaml` — секреты (API-ключи, пароли).
4. Переменные окружения с префиксом `JARVIS_` — высший приоритет.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from jarvis.utils.paths import (
    BUNDLED_CONFIG,
    CONFIG_FILE,
    SECRETS_FILE,
    ensure_dirs,
)


@dataclass
class LLMConfig:
    provider: str = "omniroute"
    model: str = "gpt-4o-mini"
    base_url: str = "http://localhost:20128/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""


@dataclass
class STTConfig:
    engine: str = "google"
    model: str = "base"
    language: str = "ru"
    device: str = "cpu"


@dataclass
class TTSConfig:
    engine: str = "edge-tts"
    edge_voice: str = "ru-RU-DmitryNeural"
    edge_rate: str = "+10%"
    edge_pitch: str = "-5Hz"
    xtts_model: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    xtts_speaker_wav: str = "models/jarvis_voice.wav"
    xtts_language: str = "ru"


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    allowed_users: list[int] = field(default_factory=list)


@dataclass
class BrowserConfig:
    enabled: bool = True
    headless: bool = False
    browser_type: str = "chromium"


@dataclass
class DesktopConfig:
    enabled: bool = True
    screenshot_interval: int = 10


@dataclass
class CaptivePortalConfig:
    enabled: bool = False
    url: str = ""
    username: str = ""
    password: str = ""
    method: str = "POST"


@dataclass
class InternetConfig:
    enabled: bool = True
    check_interval: int = 300
    ping_host: str = "8.8.8.8"
    wifi_ssid: str = ""
    wifi_password: str = ""
    captive_portal: CaptivePortalConfig = field(default_factory=CaptivePortalConfig)


@dataclass
class ServerConfig:
    """Локальный HTTP/WebSocket сервер для веб-UI."""

    host: str = "127.0.0.1"
    port: int = 8765
    open_browser_on_start: bool = False


@dataclass
class JarvisConfig:
    language: str = "ru"
    wake_words: list[str] = field(default_factory=lambda: ["джарвис", "jarvis"])
    name: str = "Джарвис"
    master_name: str = "сэр"
    voice_enabled: bool = True
    autostart: bool = False
    llm: LLMConfig = field(default_factory=LLMConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    desktop: DesktopConfig = field(default_factory=DesktopConfig)
    internet: InternetConfig = field(default_factory=InternetConfig)
    server: ServerConfig = field(default_factory=ServerConfig)


# ---------- Helpers ----------

def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Рекурсивное слияние словарей (override побеждает)."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _filter(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k in cls.__dataclass_fields__}


def _dict_to_config(data: dict[str, Any]) -> JarvisConfig:
    general = data.get("general", {})
    internet_data = dict(data.get("internet", {}))
    captive_data = internet_data.pop("captive_portal", {}) or {}

    return JarvisConfig(
        language=general.get("language", "ru"),
        wake_words=general.get("wake_words", ["джарвис", "jarvis"]),
        name=general.get("name", "Джарвис"),
        master_name=general.get("master_name", "сэр"),
        voice_enabled=general.get("voice_enabled", True),
        autostart=general.get("autostart", False),
        llm=LLMConfig(**_filter(LLMConfig, data.get("llm", {}))),
        stt=STTConfig(**_filter(STTConfig, data.get("stt", {}))),
        tts=TTSConfig(**_filter(TTSConfig, data.get("tts", {}))),
        telegram=TelegramConfig(
            **_filter(TelegramConfig, data.get("telegram", {})),
        ),
        browser=BrowserConfig(
            **_filter(BrowserConfig, data.get("browser", {})),
        ),
        desktop=DesktopConfig(
            **_filter(DesktopConfig, data.get("desktop", {})),
        ),
        internet=InternetConfig(
            **_filter(InternetConfig, internet_data),
            captive_portal=CaptivePortalConfig(
                **_filter(CaptivePortalConfig, captive_data),
            ),
        ),
        server=ServerConfig(**_filter(ServerConfig, data.get("server", {}))),
    )


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Переопределить через переменные окружения JARVIS_*."""
    env = os.environ
    mapping = {
        "JARVIS_LLM_PROVIDER": ("llm", "provider"),
        "JARVIS_LLM_MODEL": ("llm", "model"),
        "JARVIS_LLM_BASE_URL": ("llm", "base_url"),
        "JARVIS_LLM_API_KEY": ("llm", "api_key"),
        "JARVIS_TELEGRAM_TOKEN": ("telegram", "bot_token"),
        "JARVIS_TELEGRAM_ENABLED": ("telegram", "enabled"),
        "JARVIS_SERVER_HOST": ("server", "host"),
        "JARVIS_SERVER_PORT": ("server", "port"),
        "JARVIS_VOICE_ENABLED": ("general", "voice_enabled"),
    }
    out = dict(data)
    for var, (section, key) in mapping.items():
        if var not in env:
            continue
        val: Any = env[var]
        if val.lower() in ("true", "false"):
            val = val.lower() == "true"
        else:
            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except ValueError:
                pass
        out.setdefault(section, {})[key] = val
    return out


def load_config() -> JarvisConfig:
    """Загрузить конфиг с учётом всех источников."""
    ensure_dirs()
    data: dict[str, Any] = {}

    if BUNDLED_CONFIG.exists():
        data = _deep_merge(data, _load_yaml(BUNDLED_CONFIG))

    if CONFIG_FILE.exists():
        data = _deep_merge(data, _load_yaml(CONFIG_FILE))

    if SECRETS_FILE.exists():
        data = _deep_merge(data, _load_yaml(SECRETS_FILE))

    data = _apply_env_overrides(data)
    return _dict_to_config(data)


def save_config(config: JarvisConfig, *, target: Path | None = None) -> Path:
    """Сохранить конфиг в YAML. По умолчанию — в пользовательский каталог."""
    ensure_dirs()
    path = target or CONFIG_FILE

    data = {
        "general": {
            "language": config.language,
            "wake_words": config.wake_words,
            "name": config.name,
            "master_name": config.master_name,
            "voice_enabled": config.voice_enabled,
            "autostart": config.autostart,
        },
        "llm": asdict(config.llm),
        "stt": asdict(config.stt),
        "tts": asdict(config.tts),
        "telegram": asdict(config.telegram),
        "browser": asdict(config.browser),
        "desktop": asdict(config.desktop),
        "internet": asdict(config.internet),
        "server": asdict(config.server),
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return path


def is_first_run() -> bool:
    """Запущен ли Джарвис впервые (нет пользовательского конфига)."""
    return not CONFIG_FILE.exists()
