"""Тесты шины событий."""

import asyncio

import pytest

from jarvis.core.event_bus import Event, EventBus, EventType

pytestmark = pytest.mark.asyncio


async def test_event_bus_emit_and_handle() -> None:
    """Отправка и получение событий."""
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.on(EventType.SPEECH_RECOGNIZED, handler)

    task = asyncio.create_task(bus.process_events())

    await bus.emit(Event(
        type=EventType.SPEECH_RECOGNIZED,
        data={"text": "привет джарвис"},
        source="test",
    ))

    await asyncio.sleep(0.1)
    await bus.emit(Event(type=EventType.SHUTDOWN))
    await task

    assert len(received) == 1
    assert received[0].data["text"] == "привет джарвис"


async def test_event_bus_multiple_handlers() -> None:
    """Несколько обработчиков на одно событие."""
    bus = EventBus()
    count = {"value": 0}

    async def handler1(event: Event) -> None:
        count["value"] += 1

    async def handler2(event: Event) -> None:
        count["value"] += 10

    bus.on(EventType.WAKE_WORD_DETECTED, handler1)
    bus.on(EventType.WAKE_WORD_DETECTED, handler2)

    task = asyncio.create_task(bus.process_events())

    await bus.emit(Event(type=EventType.WAKE_WORD_DETECTED, source="test"))
    await asyncio.sleep(0.1)
    await bus.emit(Event(type=EventType.SHUTDOWN))
    await task

    assert count["value"] == 11


async def test_event_bus_unsubscribe() -> None:
    """Отписка от события."""
    bus = EventBus()
    received: list[Event] = []

    async def handler(event: Event) -> None:
        received.append(event)

    bus.on(EventType.ERROR, handler)
    bus.off(EventType.ERROR, handler)

    task = asyncio.create_task(bus.process_events())

    await bus.emit(Event(type=EventType.ERROR, data={"error": "test"}))
    await asyncio.sleep(0.1)
    await bus.emit(Event(type=EventType.SHUTDOWN))
    await task

    assert len(received) == 0
