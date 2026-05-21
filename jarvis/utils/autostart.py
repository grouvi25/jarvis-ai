"""Установка/удаление автозапуска Джарвиса при входе в систему."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from jarvis.utils import platform as plat
from jarvis.utils.logger import log

APP_NAME = "Jarvis"


def _executable() -> str:
    """Команда для автозапуска. В PyInstaller-сборке — путь к exe,
    иначе — `python -m jarvis.app`."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m jarvis.app'


def enable() -> str:
    """Включить автозапуск. Возвращает понятное человеку сообщение."""
    try:
        if plat.is_windows():
            return _enable_windows()
        if plat.is_macos():
            return _enable_macos()
        if plat.is_linux():
            return _enable_linux()
    except Exception as e:
        log.error(f"Не удалось включить автозапуск: {e}")
        return f"Ошибка автозапуска: {e}"
    return "Платформа не поддерживается"


def disable() -> str:
    """Выключить автозапуск."""
    try:
        if plat.is_windows():
            return _disable_windows()
        if plat.is_macos():
            return _disable_macos()
        if plat.is_linux():
            return _disable_linux()
    except Exception as e:
        return f"Ошибка: {e}"
    return "Платформа не поддерживается"


def is_enabled() -> bool:
    try:
        if plat.is_windows():
            return _registry_key_exists()
        if plat.is_macos():
            return _macos_plist().exists()
        if plat.is_linux():
            return _linux_desktop().exists()
    except Exception:
        return False
    return False


# ---------- Windows ----------

def _registry_key_exists() -> bool:
    import winreg  # type: ignore[import-not-found]

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    ) as key:
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False


def _enable_windows() -> str:
    import winreg  # type: ignore[import-not-found]

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        0, winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _executable())
    return "Автозапуск включён (Windows registry HKCU\\...\\Run)"


def _disable_windows() -> str:
    import winreg  # type: ignore[import-not-found]

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            0, winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    return "Автозапуск отключён"


# ---------- macOS ----------

def _macos_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.jarvis.{APP_NAME}.plist"


def _enable_macos() -> str:
    plist = _macos_plist()
    plist.parent.mkdir(parents=True, exist_ok=True)
    program_args = "".join(
        f"    <string>{p}</string>\n" for p in _executable().replace('"', "").split()
    )
    plist.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jarvis.{APP_NAME}</string>
    <key>ProgramArguments</key>
    <array>
{program_args}    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
""",
        encoding="utf-8",
    )
    os.system(f"launchctl load -w {plist}")  # noqa: S605
    return f"Автозапуск включён ({plist})"


def _disable_macos() -> str:
    plist = _macos_plist()
    if plist.exists():
        os.system(f"launchctl unload -w {plist}")  # noqa: S605
        plist.unlink()
    return "Автозапуск отключён"


# ---------- Linux ----------

def _linux_desktop() -> Path:
    autostart_dir = Path(
        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    ) / "autostart"
    return autostart_dir / f"{APP_NAME.lower()}.desktop"


def _enable_linux() -> str:
    desktop = _linux_desktop()
    desktop.parent.mkdir(parents=True, exist_ok=True)
    exe = _executable()
    desktop.write_text(
        f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=J.A.R.V.I.S. AI Assistant
Exec={exe}
Icon=jarvis
X-GNOME-Autostart-enabled=true
Terminal=false
Categories=Utility;
""",
        encoding="utf-8",
    )
    desktop.chmod(0o755)
    return f"Автозапуск включён ({desktop})"


def _disable_linux() -> str:
    desktop = _linux_desktop()
    if desktop.exists():
        desktop.unlink()
    return "Автозапуск отключён"
