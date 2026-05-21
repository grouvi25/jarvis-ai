"""Время, дата, таймеры."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from jarvis.core.event_bus import EventBus
from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class TimeSkill(Skill):
    """Текущее время, дата, день недели + отложенные напоминания."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus

    @property
    def name(self) -> str:
        return "time"

    @property
    def description(self) -> str:
        return (
            "Время и таймеры: now (текущее время/дата), reminder "
            "(поставить напоминание через N секунд). "
            "Используй для 'сколько времени', 'какой сегодня день', "
            "'напомни через 10 минут о...'."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["now", "reminder"]},
                "seconds": {
                    "type": "integer",
                    "description": "Через сколько секунд напомнить (для action=reminder).",
                },
                "message": {
                    "type": "string",
                    "description": "Текст напоминания (для action=reminder).",
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "now")
        if action == "now":
            now = datetime.now()
            days = ["понедельник", "вторник", "среда", "четверг",
                    "пятница", "суббота", "воскресенье"]
            return now.strftime(
                f"Сейчас %H:%M:%S, {days[now.weekday()]} %d.%m.%Y"
            )

        if action == "reminder":
            seconds = int(kwargs.get("seconds", 0) or 0)
            message = kwargs.get("message", "") or "напоминание"
            if seconds <= 0:
                return "Не указано через сколько секунд"
            asyncio.create_task(self._fire(seconds, message))
            return f"Напомню через {seconds} сек: {message}"

        return f"Неизвестное действие: {action}"

    async def _fire(self, seconds: int, message: str) -> None:
        await asyncio.sleep(seconds)
        log.info(f"⏰ Напоминание: {message}")
        if self._event_bus:
            from jarvis.core.event_bus import Event, EventType

            await self._event_bus.emit(Event(
                type=EventType.LLM_RESPONSE,
                data={"response": f"Напоминание: {message}", "from": "reminder"},
                source="time_skill",
            ))
