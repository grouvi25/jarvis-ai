"""Шина событий для J.A.R.V.I.S. — связь между модулями."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine


class EventType(Enum):
    """Типы событий в системе."""

    # Голосовые события
    WAKE_WORD_DETECTED = "wake_word_detected"
    SPEECH_RECOGNIZED = "speech_recognized"
    SPEECH_STARTED = "speech_started"
    SPEECH_FINISHED = "speech_finished"
    VOICE_STATUS = "voice_status"

    # LLM события
    LLM_RESPONSE = "llm_response"
    LLM_THINKING = "llm_thinking"

    # Скилл-события
    SKILL_EXECUTE = "skill_execute"
    SKILL_RESULT = "skill_result"

    # Системные
    INTERNET_LOST = "internet_lost"
    INTERNET_RESTORED = "internet_restored"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class Event:
    """Событие в системе."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Асинхронная шина событий."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._queue: asyncio.Queue[Event] = asyncio.Queue()

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """Подписаться на событие."""
        self._handlers[event_type].append(handler)

    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """Отписаться от события."""
        handlers = self._handlers[event_type]
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: Event) -> None:
        """Отправить событие всем подписчикам."""
        await self._queue.put(event)

    async def process_events(self) -> None:
        """Обрабатывать события из очереди (запускать как задачу)."""
        while True:
            event = await self._queue.get()
            if event.type == EventType.SHUTDOWN:
                break
            handlers = self._handlers.get(event.type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    error_event = Event(
                        type=EventType.ERROR,
                        data={"error": str(e), "original_event": event.type.value},
                        source="event_bus",
                    )
                    for err_handler in self._handlers.get(EventType.ERROR, []):
                        try:
                            await err_handler(error_event)
                        except Exception:
                            pass
