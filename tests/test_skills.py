"""Тесты простых скиллов (без сетевых/системных зависимостей)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.skills.contacts import ContactsSkill
from jarvis.skills.files import FilesSkill
from jarvis.skills.notes import NotesSkill
from jarvis.skills.time_skill import TimeSkill


@pytest.mark.asyncio
async def test_files_skill_read_write(tmp_path: Path) -> None:
    skill = FilesSkill()
    file = tmp_path / "demo.txt"
    res = await skill.execute(action="write", path=str(file), content="hello")
    assert "Запись" in res or "Дозапись" in res
    assert file.read_text() == "hello"

    res = await skill.execute(action="read", path=str(file))
    assert "hello" in res

    res = await skill.execute(action="append", path=str(file), content=" world")
    assert file.read_text() == "hello world"

    res = await skill.execute(action="exists", path=str(file))
    assert res == "да"

    res = await skill.execute(action="exists", path=str(tmp_path / "nope"))
    assert res == "нет"

    res = await skill.execute(action="list", path=str(tmp_path))
    assert "demo.txt" in res


@pytest.mark.asyncio
async def test_files_skill_search(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.md").write_text("x")
    skill = FilesSkill()
    res = await skill.execute(action="search", path=str(tmp_path), pattern="*.txt")
    assert "a.txt" in res
    assert "b.md" not in res


@pytest.mark.asyncio
async def test_time_skill_now() -> None:
    skill = TimeSkill()
    res = await skill.execute(action="now")
    assert "Сейчас" in res


@pytest.mark.asyncio
async def test_notes_skill_remember_recall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Перенаправляем хранилище памяти в tmp_path
    import jarvis.utils.paths as paths

    monkeypatch.setattr(paths, "MEMORY_FILE", tmp_path / "mem.json")
    monkeypatch.setattr(paths, "NOTES_FILE", tmp_path / "notes.json")

    from jarvis.core.memory import MemoryStore  # импорт после monkeypatch

    memory = MemoryStore(path=tmp_path / "mem.json")
    skill = NotesSkill(memory=memory)
    res = await skill.execute(action="remember", text="меня зовут Тест")
    assert "Запомнил" in res

    res = await skill.execute(action="recall")
    assert "Тест" in res

    res = await skill.execute(action="add_note", text="купить кофе")
    assert "Заметка добавлена" in res
    res = await skill.execute(action="list_notes")
    assert "купить кофе" in res


@pytest.mark.asyncio
async def test_contacts_add_and_find_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import jarvis.utils.paths as paths

    monkeypatch.setattr(paths, "CONTACTS_FILE", tmp_path / "contacts.json")
    # Re-import to pick up monkeypatched path
    import jarvis.skills.contacts as contacts_mod

    monkeypatch.setattr(contacts_mod, "CONTACTS_FILE", tmp_path / "contacts.json")

    skill = ContactsSkill()
    res = await skill.execute(action="add", name="Маша", telegram_id="@masha123", label="девушка")
    assert "Контакт сохранён" in res

    res = await skill.execute(action="find", name="Маша")
    assert "Маша" in res
    assert "девушка" in res


@pytest.mark.asyncio
async def test_contacts_find_by_label(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import jarvis.utils.paths as paths

    monkeypatch.setattr(paths, "CONTACTS_FILE", tmp_path / "contacts.json")
    import jarvis.skills.contacts as contacts_mod

    monkeypatch.setattr(contacts_mod, "CONTACTS_FILE", tmp_path / "contacts.json")

    skill = ContactsSkill()
    await skill.execute(action="add", name="Маша", telegram_id="@masha123", label="девушка")

    # The key fix: find by label when name is empty
    res = await skill.execute(action="find", label="девушка")
    assert "Маша" in res
    assert "девушка" in res


@pytest.mark.asyncio
async def test_contacts_list_and_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import jarvis.utils.paths as paths

    monkeypatch.setattr(paths, "CONTACTS_FILE", tmp_path / "contacts.json")
    import jarvis.skills.contacts as contacts_mod

    monkeypatch.setattr(contacts_mod, "CONTACTS_FILE", tmp_path / "contacts.json")

    skill = ContactsSkill()
    await skill.execute(action="add", name="Маша", telegram_id="@masha123", label="девушка")
    await skill.execute(action="add", name="Петя", telegram_id="@petya", label="друг")

    res = await skill.execute(action="list")
    assert "Маша" in res
    assert "Петя" in res

    res = await skill.execute(action="delete", name="Маша")
    assert "удалён" in res

    res = await skill.execute(action="list")
    assert "Маша" not in res
    assert "Петя" in res
