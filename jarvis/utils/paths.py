"""OS-aware пути к конфигу, данным, логам J.A.R.V.I.S.

Использует platformdirs для следования стандартам каждой ОС:
- Windows: %APPDATA%\\Jarvis
- macOS:   ~/Library/Application Support/Jarvis
- Linux:   ~/.config/jarvis  и  ~/.local/share/jarvis
"""

from __future__ import annotations

from pathlib import Path

try:
    from platformdirs import PlatformDirs

    _dirs = PlatformDirs(appname="Jarvis", appauthor="Jarvis", roaming=False)
    CONFIG_DIR = Path(_dirs.user_config_dir)
    DATA_DIR = Path(_dirs.user_data_dir)
    LOG_DIR = Path(_dirs.user_log_dir)
    CACHE_DIR = Path(_dirs.user_cache_dir)
except ImportError:  # pragma: no cover — fallback for fresh install
    HOME = Path.home()
    CONFIG_DIR = HOME / ".config" / "jarvis"
    DATA_DIR = HOME / ".local" / "share" / "jarvis"
    LOG_DIR = DATA_DIR / "logs"
    CACHE_DIR = HOME / ".cache" / "jarvis"


CONFIG_FILE = CONFIG_DIR / "config.yaml"
SECRETS_FILE = CONFIG_DIR / "secrets.yaml"
MEMORY_FILE = DATA_DIR / "memory.json"
CONVERSATION_FILE = DATA_DIR / "conversation.json"
NOTES_FILE = DATA_DIR / "notes.json"
CONTACTS_FILE = DATA_DIR / "contacts.json"
LOG_FILE = LOG_DIR / "jarvis.log"
SCREENSHOT_DIR = DATA_DIR / "screenshots"

# Корень проекта (для dev-режима и поиска встроенных ресурсов)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BUNDLED_CONFIG = PROJECT_ROOT / "config" / "config.yaml"


def ensure_dirs() -> None:
    """Создать все необходимые каталоги если их нет."""
    for d in (CONFIG_DIR, DATA_DIR, LOG_DIR, CACHE_DIR, SCREENSHOT_DIR):
        d.mkdir(parents=True, exist_ok=True)


def web_assets_dir() -> Path:
    """Каталог со статикой web-UI (для FastAPI)."""
    return Path(__file__).resolve().parent.parent / "ui" / "web"


def icon_path() -> Path | None:
    """Путь к иконке приложения (для трея, окон, ярлыков)."""
    assets = Path(__file__).resolve().parent.parent / "assets"
    for name in ("icon.png", "jarvis.png", "icon.ico"):
        p = assets / name
        if p.exists():
            return p
    return None
