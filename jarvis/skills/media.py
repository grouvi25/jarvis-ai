"""Скилл управления медиа."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class MediaControlSkill(Skill):
    """Управление музыкой и видео — play/pause/next/volume."""

    @property
    def name(self) -> str:
        return "media_control"

    @property
    def description(self) -> str:
        return (
            "Управление музыкой и видео: play, pause, next, previous, "
            "громкость. Работает с любым медиаплеером через playerctl/MPRIS. "
            "Используй когда пользователь просит включить/выключить музыку, "
            "переключить трек, поставить на паузу."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "play", "pause", "toggle", "next",
                        "previous", "status", "volume_up",
                        "volume_down",
                    ],
                    "description": (
                        "play — играть, pause — пауза, "
                        "toggle — переключить play/pause, "
                        "next — следующий трек, "
                        "previous — предыдущий, "
                        "status — что сейчас играет, "
                        "volume_up/volume_down — громкость"
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")

        playerctl_map = {
            "play": "play",
            "pause": "pause",
            "toggle": "play-pause",
            "next": "next",
            "previous": "previous",
        }

        if action == "status":
            return await self._get_status()

        if action in ("volume_up", "volume_down"):
            return await self._change_volume(action)

        playerctl_action = playerctl_map.get(action)
        if not playerctl_action:
            return f"Неизвестное действие: {action}"

        return await self._playerctl(playerctl_action)

    async def _playerctl(self, action: str) -> str:
        """Выполнить команду playerctl."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["playerctl", action],
                    capture_output=True, text=True, timeout=5,
                ),
            )
            if result.returncode == 0:
                action_ru = {
                    "play": "Воспроизведение",
                    "pause": "Пауза",
                    "play-pause": "Переключение play/pause",
                    "next": "Следующий трек",
                    "previous": "Предыдущий трек",
                }.get(action, action)
                return action_ru
            return f"playerctl ошибка: {result.stderr.strip()}"
        except FileNotFoundError:
            return (
                "playerctl не установлен. Установите: "
                "sudo apt install playerctl"
            )
        except subprocess.TimeoutExpired:
            return "Таймаут playerctl"

    async def _get_status(self) -> str:
        """Показать что сейчас играет."""
        loop = asyncio.get_event_loop()
        try:
            fmt = "{{artist}} — {{title}} [{{status}}]"
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["playerctl", "metadata", "--format", fmt],
                    capture_output=True, text=True, timeout=5,
                ),
            )
            if result.returncode == 0:
                info = result.stdout.strip()
                if info:
                    return f"Сейчас играет: {info}"
            return "Ничего не воспроизводится"
        except FileNotFoundError:
            return "playerctl не установлен"

    async def _change_volume(self, direction: str) -> str:
        """Изменить громкость системы."""
        loop = asyncio.get_event_loop()
        try:
            delta = "5%+" if direction == "volume_up" else "5%-"
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["amixer", "sset", "Master", delta],
                    capture_output=True, timeout=5,
                ),
            )
            action_ru = (
                "увеличена" if direction == "volume_up" else "уменьшена"
            )
            return f"Громкость {action_ru}"
        except FileNotFoundError:
            log.warning("amixer не найден, пробуем pactl")
            try:
                sign = "+" if direction == "volume_up" else "-"
                await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        ["pactl", "set-sink-volume",
                         "@DEFAULT_SINK@", f"{sign}5%"],
                        capture_output=True, timeout=5,
                    ),
                )
                action_ru = (
                    "увеличена"
                    if direction == "volume_up"
                    else "уменьшена"
                )
                return f"Громкость {action_ru}"
            except FileNotFoundError:
                return "amixer/pactl не найден"
