"""Скилл таймеров и напоминаний."""

from __future__ import annotations

import asyncio
from typing import Any

from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class TimerSkill(Skill):
    """Устанавливает таймеры и напоминания."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._active_timers: dict[str, asyncio.Task[None]] = {}

    @property
    def name(self) -> str:
        return "set_timer"

    @property
    def description(self) -> str:
        return (
            "Установить таймер или напоминание. "
            "Используй когда пользователь просит напомнить, "
            "поставить таймер, будильник, или сделать что-то через N минут."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "integer",
                    "description": "Через сколько секунд сработает таймер",
                },
                "message": {
                    "type": "string",
                    "description": "Текст напоминания",
                },
                "label": {
                    "type": "string",
                    "description": (
                        "Метка таймера "
                        "(для отмены, например 'чай' или 'пицца')"
                    ),
                },
            },
            "required": ["seconds", "message"],
        }

    async def execute(self, **kwargs: Any) -> str:
        seconds = kwargs.get("seconds", 0)
        message = kwargs.get("message", "Таймер сработал!")
        label = kwargs.get("label", f"timer_{len(self._active_timers)}")

        if seconds <= 0:
            return "Укажи положительное количество секунд"

        if label in self._active_timers:
            self._active_timers[label].cancel()

        task = asyncio.create_task(self._timer_task(seconds, message, label))
        self._active_timers[label] = task

        if seconds >= 3600:
            time_str = f"{seconds // 3600} ч {(seconds % 3600) // 60} мин"
        elif seconds >= 60:
            time_str = f"{seconds // 60} мин {seconds % 60} сек"
        else:
            time_str = f"{seconds} сек"

        return f"Таймер '{label}' установлен на {time_str}: {message}"

    async def _timer_task(
        self, seconds: int, message: str, label: str
    ) -> None:
        """Фоновая задача таймера."""
        try:
            await asyncio.sleep(seconds)
            log.info(f"Таймер '{label}' сработал: {message}")
            await self._event_bus.emit(Event(
                type=EventType.LLM_RESPONSE,
                data={"response": f"Напоминание: {message}"},
                source="timer",
            ))
        except asyncio.CancelledError:
            log.info(f"Таймер '{label}' отменён")
        finally:
            self._active_timers.pop(label, None)
