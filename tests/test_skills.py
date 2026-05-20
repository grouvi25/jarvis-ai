"""Тесты скиллов J.A.R.V.I.S."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from jarvis.core.event_bus import EventBus
from jarvis.skills.notes import NotesSkill
from jarvis.skills.timer import TimerSkill


class TestNotesSkill:
    """Тесты заметок."""

    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        with patch("jarvis.skills.notes.NOTES_DIR", Path(self.tmp_dir)):
            self.skill = NotesSkill()
            self.skill._notes_file = Path(self.tmp_dir) / "notes.json"
            self.skill._notes = []

    @pytest.mark.asyncio
    async def test_add_note(self) -> None:
        result = await self.skill.execute(action="add", text="Купить молоко")
        assert "Записано" in result
        assert "Купить молоко" in result
        assert len(self.skill._notes) == 1

    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        result = await self.skill.execute(action="list")
        assert "пока нет" in result

    @pytest.mark.asyncio
    async def test_list_notes(self) -> None:
        await self.skill.execute(action="add", text="Заметка 1")
        await self.skill.execute(action="add", text="Заметка 2")
        result = await self.skill.execute(action="list")
        assert "Заметка 1" in result
        assert "Заметка 2" in result
        assert "(2)" in result

    @pytest.mark.asyncio
    async def test_delete_by_number(self) -> None:
        await self.skill.execute(action="add", text="Удали меня")
        result = await self.skill.execute(action="delete", text="1")
        assert "Удалено" in result
        assert len(self.skill._notes) == 0

    @pytest.mark.asyncio
    async def test_delete_by_text(self) -> None:
        await self.skill.execute(action="add", text="Купить хлеб")
        await self.skill.execute(action="add", text="Позвонить маме")
        result = await self.skill.execute(action="delete", text="хлеб")
        assert "Удалено" in result
        assert len(self.skill._notes) == 1

    @pytest.mark.asyncio
    async def test_search(self) -> None:
        await self.skill.execute(action="add", text="Купить молоко")
        await self.skill.execute(action="add", text="Купить хлеб")
        await self.skill.execute(action="add", text="Позвонить маме")
        result = await self.skill.execute(action="search", text="купить")
        assert "Найдено (2)" in result
        assert "молоко" in result
        assert "хлеб" in result
        assert "маме" not in result

    @pytest.mark.asyncio
    async def test_add_empty(self) -> None:
        result = await self.skill.execute(action="add", text="")
        assert "Не указан" in result

    @pytest.mark.asyncio
    async def test_persistence(self) -> None:
        await self.skill.execute(action="add", text="Тестовая заметка")
        assert self.skill._notes_file.exists()
        with open(self.skill._notes_file, encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved) == 1
        assert saved[0]["text"] == "Тестовая заметка"


class TestTimerSkill:
    """Тесты таймеров."""

    def setup_method(self) -> None:
        self.bus = EventBus()
        self.skill = TimerSkill(self.bus)

    @pytest.mark.asyncio
    async def test_set_timer(self) -> None:
        result = await self.skill.execute(
            seconds=5, message="Чай готов!", label="чай"
        )
        assert "чай" in result
        assert "5 сек" in result
        assert "чай" in self.skill._active_timers

    @pytest.mark.asyncio
    async def test_timer_format_minutes(self) -> None:
        result = await self.skill.execute(
            seconds=90, message="Тест"
        )
        assert "1 мин 30 сек" in result

    @pytest.mark.asyncio
    async def test_timer_format_hours(self) -> None:
        result = await self.skill.execute(
            seconds=3661, message="Тест"
        )
        assert "1 ч 1 мин" in result

    @pytest.mark.asyncio
    async def test_zero_seconds(self) -> None:
        result = await self.skill.execute(seconds=0, message="Тест")
        assert "положительное" in result

    @pytest.mark.asyncio
    async def test_timer_properties(self) -> None:
        assert self.skill.name == "set_timer"
        assert "таймер" in self.skill.description
        assert "seconds" in self.skill.parameters["properties"]
