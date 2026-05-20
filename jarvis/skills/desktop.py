"""Скилл управления десктопом."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class DesktopControlSkill(Skill):
    """Управляет десктопом — запускает приложения, выполняет команды, управляет окнами."""

    @property
    def name(self) -> str:
        return "desktop_control"

    @property
    def description(self) -> str:
        return (
            "Управление компьютером: запустить программу, выполнить shell-команду, "
            "сделать скриншот экрана, управлять громкостью, открыть файл. "
            "Используй когда пользователь просит что-то сделать на компьютере."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "run_command",
                        "open_app",
                        "screenshot",
                        "volume",
                        "type_text",
                        "hotkey",
                    ],
                    "description": (
                        "Действие: run_command (выполнить команду), open_app (открыть приложение), "
                        "screenshot (скриншот), volume (громкость up/down/mute), "
                        "type_text (набрать текст), hotkey (нажать горячую клавишу)"
                    ),
                },
                "command": {
                    "type": "string",
                    "description": "Команда для выполнения, имя приложения, или текст",
                },
                "value": {
                    "type": "string",
                    "description": (
                        "Дополнительное значение "
                        "(напр. уровень громкости, горячая клавиша)"
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        command = kwargs.get("command", "")
        value = kwargs.get("value", "")

        try:
            if action == "run_command":
                if not command:
                    return "Не указана команда"
                return await self._run_command(command)

            elif action == "open_app":
                if not command:
                    return "Не указано имя приложения"
                return await self._open_app(command)

            elif action == "screenshot":
                return await self._take_screenshot()

            elif action == "volume":
                return await self._control_volume(command or value)

            elif action == "type_text":
                return await self._type_text(command)

            elif action == "hotkey":
                return await self._press_hotkey(command or value)

            else:
                return f"Неизвестное действие: {action}"

        except Exception as e:
            return f"Ошибка управления десктопом: {e}"

    async def _run_command(self, command: str) -> str:
        """Выполнить shell-команду."""
        # Блокируем опасные команды
        dangerous = ["rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb"]
        for d in dangerous:
            if d in command.lower():
                return f"Команда заблокирована по соображениям безопасности: {command}"

        log.info(f"Выполнение команды: {command}")
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                ),
            )
            output = result.stdout.strip()
            if result.returncode != 0:
                error = result.stderr.strip()
                return f"Команда завершилась с ошибкой (код {result.returncode}):\n{error}"
            return output if output else "Команда выполнена успешно"
        except subprocess.TimeoutExpired:
            return "Команда превысила таймаут (30 сек)"

    async def _open_app(self, app_name: str) -> str:
        """Открыть приложение."""
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: subprocess.Popen(
                    ["xdg-open", app_name] if "/" in app_name else [app_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ),
            )
            return f"Приложение запущено: {app_name}"
        except FileNotFoundError:
            return f"Приложение не найдено: {app_name}"

    async def _take_screenshot(self) -> str:
        """Сделать скриншот экрана."""
        path = "/tmp/jarvis_desktop_screenshot.png"
        try:
            import pyautogui

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: pyautogui.screenshot(path),
            )
            return f"Скриншот сохранён: {path}"
        except Exception:
            # Fallback через scrot
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(["scrot", path], check=True),
            )
            return f"Скриншот сохранён: {path}"

    async def _control_volume(self, action: str) -> str:
        """Управление громкостью."""
        cmd_map = {
            "up": "amixer set Master 10%+",
            "down": "amixer set Master 10%-",
            "mute": "amixer set Master toggle",
        }
        cmd = cmd_map.get(action.lower(), "")
        if not cmd:
            return f"Неизвестное действие громкости: {action}. Используй up/down/mute"
        return await self._run_command(cmd)

    async def _type_text(self, text: str) -> str:
        """Набрать текст через виртуальную клавиатуру."""
        if not text:
            return "Не указан текст"
        try:
            import pyautogui

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: pyautogui.typewrite(text, interval=0.02) if text.isascii()
                else pyautogui.hotkey("ctrl", "v"),
            )
            return f"Текст набран: {text[:50]}..."
        except Exception as e:
            return f"Ошибка ввода текста: {e}"

    async def _press_hotkey(self, hotkey: str) -> str:
        """Нажать горячую клавишу."""
        if not hotkey:
            return "Не указана горячая клавиша"
        try:
            import pyautogui

            keys = [k.strip() for k in hotkey.split("+")]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: pyautogui.hotkey(*keys),
            )
            return f"Горячая клавиша нажата: {hotkey}"
        except Exception as e:
            return f"Ошибка горячей клавиши: {e}"
