"""Управление десктопом: команды, запуск приложений, скриншоты, громкость."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils import platform as plat
from jarvis.utils.logger import log
from jarvis.utils.paths import SCREENSHOT_DIR, ensure_dirs


DANGEROUS_PATTERNS = (
    "rm -rf /", "rm -rf ~", "mkfs", "dd if=", ":(){", "fork bomb",
    "del /f /s /q c:\\", "format c:", "shutdown /s",
)


class DesktopControlSkill(Skill):
    """Запуск программ, выполнение команд, скриншоты, громкость, клавиатура."""

    @property
    def name(self) -> str:
        return "desktop_control"

    @property
    def description(self) -> str:
        return (
            "Управление компьютером: run_command (shell-команда), open_app "
            "(запустить приложение), open_file (открыть файл/папку в системе), "
            "open_url (открыть ссылку в браузере по умолчанию), "
            "screenshot (скриншот), volume (up/down/mute/set 0-100), "
            "type_text (набрать текст), hotkey (нажать комбинацию клавиш), "
            "lock (заблокировать ПК), shutdown (выключить через N сек), "
            "notify (системное уведомление). Используй для любых задач на компьютере."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "run_command", "open_app", "open_file", "open_url",
                        "screenshot", "volume", "type_text", "hotkey",
                        "lock", "shutdown", "notify",
                    ],
                },
                "command": {"type": "string", "description": "Команда, имя приложения, путь, текст или title уведомления"},
                "value": {"type": "string", "description": "Доп. значение: уровень громкости, hotkey, сообщение"},
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        command = (kwargs.get("command") or "").strip()
        value = (kwargs.get("value") or "").strip()

        try:
            if action == "run_command":
                if not command:
                    return "Не указана команда"
                return await self._run_command(command)
            if action == "open_app":
                if not command:
                    return "Не указано приложение"
                return await self._open_app(command)
            if action == "open_file":
                if not command:
                    return "Не указан путь"
                plat.open_in_file_manager(Path(os.path.expanduser(command)))
                return f"Открыто: {command}"
            if action == "open_url":
                url = command or value
                if not url:
                    return "Не указан URL"
                plat.open_url(url)
                return f"Открыт URL: {url}"
            if action == "screenshot":
                return await self._screenshot()
            if action == "volume":
                return await self._volume(command or value)
            if action == "type_text":
                return await self._type_text(command)
            if action == "hotkey":
                return await self._hotkey(command or value)
            if action == "lock":
                return self._lock()
            if action == "shutdown":
                delay = int(value or command or "60")
                return self._shutdown(delay)
            if action == "notify":
                plat.notify(command or "Jarvis", value or command)
                return "Уведомление отправлено"
            return f"Неизвестное действие: {action}"
        except Exception as e:
            log.exception("desktop_control")
            return f"Ошибка управления: {e}"

    # ---------- helpers ----------

    async def _run_command(self, command: str) -> str:
        low = command.lower()
        for d in DANGEROUS_PATTERNS:
            if d in low:
                return f"Команда заблокирована: {command}"
        log.info(f"$ {command}")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30,
            ),
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode != 0:
            return f"Код {result.returncode}\n{err or out}".strip()
        return out or "OK"

    async def _open_app(self, name: str) -> str:
        loop = asyncio.get_event_loop()
        if plat.is_windows():
            cmd: list[str] | str = ["cmd", "/c", "start", "", name]
            shell = False
        elif plat.is_macos():
            cmd = ["open", "-a", name]
            shell = False
        else:
            # На Linux: пробуем как exec, потом xdg-open, потом gtk-launch
            if plat.has_command(name):
                cmd = [name]
            elif plat.has_command("gtk-launch"):
                cmd = ["gtk-launch", name]
            else:
                cmd = ["xdg-open", name]
            shell = False

        try:
            await loop.run_in_executor(
                None,
                lambda: subprocess.Popen(  # noqa: S603
                    cmd,
                    shell=shell,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ),
            )
            return f"Запущено: {name}"
        except FileNotFoundError:
            return f"Не найдено: {name}"

    async def _screenshot(self) -> str:
        ensure_dirs()
        path = SCREENSHOT_DIR / f"jarvis_{int(asyncio.get_event_loop().time())}.png"
        loop = asyncio.get_event_loop()
        try:
            import pyautogui  # type: ignore[import-not-found]

            await loop.run_in_executor(None, lambda: pyautogui.screenshot(str(path)))
            return f"Скриншот: {path}"
        except Exception:
            # Платформенные fallback
            if plat.is_linux():
                for tool in ("scrot", "gnome-screenshot", "import"):
                    if plat.has_command(tool):
                        cmd = [tool, str(path)] if tool == "scrot" else [tool, "-window", "root", str(path)]
                        if tool == "gnome-screenshot":
                            cmd = ["gnome-screenshot", "-f", str(path)]
                        try:
                            await loop.run_in_executor(
                                None,
                                lambda c=cmd: subprocess.run(c, check=True, timeout=10),
                            )
                            return f"Скриншот: {path}"
                        except Exception:
                            continue
            return "Скриншот недоступен (установите pyautogui)"

    async def _volume(self, action: str) -> str:
        action = (action or "").lower()
        loop = asyncio.get_event_loop()

        if plat.is_linux():
            cmd_map = {
                "up": "amixer -q set Master 10%+",
                "down": "amixer -q set Master 10%-",
                "mute": "amixer -q set Master toggle",
            }
            if action.isdigit():
                cmd = f"amixer -q set Master {int(action)}%"
            else:
                cmd = cmd_map.get(action, "")
            if not cmd:
                return f"Неизвестное действие громкости: {action}"
            return await self._run_command(cmd)

        if plat.is_macos():
            mapping = {
                "up": "set volume output volume (output volume of (get volume settings) + 10)",
                "down": "set volume output volume (output volume of (get volume settings) - 10)",
                "mute": "set volume output muted not (output muted of (get volume settings))",
            }
            if action.isdigit():
                script = f"set volume output volume {int(action)}"
            else:
                script = mapping.get(action, "")
            if not script:
                return f"Неизвестное действие громкости: {action}"
            await loop.run_in_executor(None, lambda: subprocess.run(["osascript", "-e", script]))
            return f"Громкость: {action}"

        if plat.is_windows():
            # WSH через PowerShell SendKeys
            keys_map = {"up": "175", "down": "174", "mute": "173"}
            vk = keys_map.get(action, "")
            if not vk:
                return f"Неизвестное действие громкости: {action} (Windows: up/down/mute)"
            await loop.run_in_executor(
                None,
                lambda: subprocess.run([
                    "powershell", "-Command",
                    f"(New-Object -ComObject WScript.Shell).SendKeys([char]{vk})",
                ]),
            )
            return f"Громкость: {action}"

        return "Платформа не поддерживается"

    async def _type_text(self, text: str) -> str:
        if not text:
            return "Не указан текст"
        try:
            import pyautogui  # type: ignore[import-not-found]

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: pyautogui.typewrite(text, interval=0.02))
            return f"Набрано: {text[:50]}"
        except Exception as e:
            return f"Не удалось набрать текст: {e}"

    async def _hotkey(self, hotkey: str) -> str:
        if not hotkey:
            return "Не указана горячая клавиша"
        try:
            import pyautogui  # type: ignore[import-not-found]

            keys = [k.strip() for k in hotkey.replace(" ", "").split("+")]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: pyautogui.hotkey(*keys))
            return f"Hotkey: {hotkey}"
        except Exception as e:
            return f"Ошибка hotkey: {e}"

    def _lock(self) -> str:
        if plat.is_windows():
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Заблокировано"
        if plat.is_macos():
            subprocess.Popen([
                "osascript", "-e",
                'tell application "System Events" to keystroke "q" using {control down, command down}',
            ])
            return "Заблокировано"
        # Linux: xdg-screensaver или loginctl
        for cmd in (
            ["xdg-screensaver", "lock"],
            ["loginctl", "lock-session"],
            ["gnome-screensaver-command", "-l"],
        ):
            if plat.has_command(cmd[0]):
                subprocess.Popen(cmd)
                return "Заблокировано"
        return "Не удалось заблокировать ПК"

    def _shutdown(self, delay: int) -> str:
        delay = max(5, min(delay, 3600))  # safety
        if plat.is_windows():
            subprocess.Popen(["shutdown", "/s", "/t", str(delay)])
            return f"Выключение через {delay} сек. Отмена: shutdown /a"
        # POSIX
        mins = max(1, delay // 60)
        subprocess.Popen(["shutdown", "-h", f"+{mins}"])
        return f"Выключение через ~{mins} мин."
