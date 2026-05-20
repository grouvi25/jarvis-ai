"""Управление конфигурацией J.A.R.V.I.S."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "config.yaml"
LOCAL_CONFIG = PROJECT_ROOT / "config" / "local.yaml"


@dataclass
class LLMConfig:
    provider: str = "ollama"
    model: str = "llama3.1"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: str = ""


@dataclass
class STTConfig:
    engine: str = "faster-whisper"
    model: str = "base"
    language: str = "ru"
    device: str = "cpu"


@dataclass
class TTSConfig:
    engine: str = "edge-tts"
    edge_voice: str = "ru-RU-DmitryNeural"
    edge_rate: str = "+10%"
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
class JarvisConfig:
    language: str = "ru"
    wake_words: list[str] = field(default_factory=lambda: ["джарвис", "jarvis"])
    name: str = "Джарвис"
    master_name: str = "сэр"
    llm: LLMConfig = field(default_factory=LLMConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    desktop: DesktopConfig = field(default_factory=DesktopConfig)
    internet: InternetConfig = field(default_factory=InternetConfig)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Рекурсивное слияние словарей."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _dict_to_config(data: dict[str, Any]) -> JarvisConfig:
    """Преобразовать словарь в JarvisConfig."""
    general = data.get("general", {})
    llm_data = data.get("llm", {})
    stt_data = data.get("stt", {})
    tts_data = data.get("tts", {})
    telegram_data = data.get("telegram", {})
    browser_data = data.get("browser", {})
    desktop_data = data.get("desktop", {})
    internet_data = data.get("internet", {})

    captive_data = internet_data.pop("captive_portal", {})
    if "captive_portal" not in internet_data:
        captive_data = captive_data or {}

    return JarvisConfig(
        language=general.get("language", "ru"),
        wake_words=general.get("wake_words", ["джарвис", "jarvis"]),
        name=general.get("name", "Джарвис"),
        master_name=general.get("master_name", "сэр"),
        llm=LLMConfig(**{k: v for k, v in llm_data.items() if k in LLMConfig.__dataclass_fields__}),
        stt=STTConfig(**{k: v for k, v in stt_data.items() if k in STTConfig.__dataclass_fields__}),
        tts=TTSConfig(**{k: v for k, v in tts_data.items() if k in TTSConfig.__dataclass_fields__}),
        telegram=TelegramConfig(
            **{k: v for k, v in telegram_data.items() if k in TelegramConfig.__dataclass_fields__}
        ),
        browser=BrowserConfig(
            **{k: v for k, v in browser_data.items() if k in BrowserConfig.__dataclass_fields__}
        ),
        desktop=DesktopConfig(
            **{k: v for k, v in desktop_data.items() if k in DesktopConfig.__dataclass_fields__}
        ),
        internet=InternetConfig(
            **{k: v for k, v in internet_data.items() if k in InternetConfig.__dataclass_fields__},
            captive_portal=CaptivePortalConfig(
                **{k: v for k, v in captive_data.items()
                  if k in CaptivePortalConfig.__dataclass_fields__}
            ),
        ),
    )


def load_config() -> JarvisConfig:
    """Загрузить конфигурацию из YAML-файлов."""
    data: dict[str, Any] = {}

    if DEFAULT_CONFIG.exists():
        with open(DEFAULT_CONFIG, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    if LOCAL_CONFIG.exists():
        with open(LOCAL_CONFIG, encoding="utf-8") as f:
            local_data = yaml.safe_load(f) or {}
            data = _deep_merge(data, local_data)

    return _dict_to_config(data)
