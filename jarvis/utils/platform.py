"""Хелперы для определения и работы с разными ОС."""

from __future__ import annotations

import platform as _platform
import shutil
import subprocess
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def os_name() -> str:
    if is_windows():
        return "windows"
    if is_macos():
        return "macos"
    if is_linux():
        return "linux"
    return _platform.system().lower()


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def open_in_file_manager(path: Path | str) -> None:
    """Открыть путь в системном файловом менеджере."""
    path = str(path)
    if is_windows():
        subprocess.Popen(["explorer", path])  # noqa: S603
    elif is_macos():
        subprocess.Popen(["open", path])  # noqa: S603
    else:
        subprocess.Popen(["xdg-open", path])  # noqa: S603


def open_url(url: str) -> None:
    """Открыть URL в системном браузере."""
    import webbrowser

    webbrowser.open(url)


def notify(title: str, message: str) -> None:
    """Показать системное уведомление (best-effort, без жёсткой зависимости)."""
    try:
        if is_linux() and has_command("notify-send"):
            subprocess.Popen(["notify-send", title, message])  # noqa: S603
            return
        if is_macos():
            subprocess.Popen([
                "osascript", "-e",
                f'display notification "{message}" with title "{title}"',
            ])  # noqa: S603
            return
        if is_windows():
            # Через PowerShell BurntToast / msg fallback
            try:
                subprocess.Popen([
                    "powershell", "-Command",
                    f"[reflection.assembly]::LoadWithPartialName('System.Windows.Forms');"
                    f"[System.Windows.Forms.MessageBox]::Show('{message}','{title}')",
                ], creationflags=0x08000000)  # noqa: S603
            except Exception:
                pass
    except Exception:
        # Уведомления — не критичны
        pass
