"""Тесты новых скиллов J.A.R.V.I.S."""

import tempfile
from pathlib import Path

import pytest

from jarvis.core.memory import Memory
from jarvis.skills.contacts import ContactsSkill
from jarvis.skills.system_info import SystemInfoSkill


class TestContactsSkill:
    """Тесты контактов."""

    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.memory = Memory(data_dir=self.tmp_dir)
        self.skill = ContactsSkill(self.memory)

    @pytest.mark.asyncio
    async def test_add_contact(self) -> None:
        result = await self.skill.execute(
            action="add", name="Маша", telegram_id="@masha", label="девушка"
        )
        assert "добавлен" in result.lower()

    @pytest.mark.asyncio
    async def test_find_contact(self) -> None:
        await self.skill.execute(
            action="add", name="Маша", telegram_id="@masha", label="девушка"
        )
        result = await self.skill.execute(action="find", name="девушка")
        assert "Маша" in result
        assert "@masha" in result

    @pytest.mark.asyncio
    async def test_list_contacts(self) -> None:
        await self.skill.execute(
            action="add", name="Маша", telegram_id="@masha"
        )
        result = await self.skill.execute(action="list")
        assert "Маша" in result
        assert "(1)" in result

    @pytest.mark.asyncio
    async def test_empty_contacts(self) -> None:
        result = await self.skill.execute(action="list")
        assert "пока нет" in result.lower()

    @pytest.mark.asyncio
    async def test_remove_contact(self) -> None:
        await self.skill.execute(
            action="add", name="Маша", telegram_id="@masha"
        )
        result = await self.skill.execute(action="remove", name="Маша")
        assert "удалён" in result.lower()

    @pytest.mark.asyncio
    async def test_properties(self) -> None:
        assert self.skill.name == "contacts"
        assert "контакт" in self.skill.description


class TestSystemInfoSkill:
    """Тесты системной информации."""

    def setup_method(self) -> None:
        self.skill = SystemInfoSkill()

    @pytest.mark.asyncio
    async def test_time(self) -> None:
        result = await self.skill.execute(query="time")
        assert "время" in result.lower()
        assert ":" in result

    @pytest.mark.asyncio
    async def test_date(self) -> None:
        result = await self.skill.execute(query="date")
        assert "сегодня" in result.lower()

    @pytest.mark.asyncio
    async def test_cpu(self) -> None:
        result = await self.skill.execute(query="cpu")
        assert "cpu" in result.lower()

    @pytest.mark.asyncio
    async def test_disk(self) -> None:
        result = await self.skill.execute(query="disk")
        assert "диск" in result.lower() or "информация" in result.lower()

    @pytest.mark.asyncio
    async def test_properties(self) -> None:
        assert self.skill.name == "system_info"
        assert "query" in self.skill.parameters["properties"]
