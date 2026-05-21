"""Тесты MemoryStore и ConversationStore."""

from __future__ import annotations

from pathlib import Path

from jarvis.core.memory import ConversationStore, MemoryStore


def test_memory_add_and_recall(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "mem.json")
    assert store.all_facts() == []
    assert store.add_fact("меня зовут Никита") == "запомнено"
    assert store.add_fact("меня зовут Никита") == "этот факт уже запомнен"
    assert "меня зовут Никита" in store.all_facts()

    reloaded = MemoryStore(path=tmp_path / "mem.json")
    assert "меня зовут Никита" in reloaded.all_facts()


def test_memory_remove(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "mem.json")
    store.add_fact("я люблю Python")
    store.add_fact("я живу в Москве")
    store.remove_fact("Python")
    facts = store.all_facts()
    assert any("Москве" in f for f in facts)
    assert not any("Python" in f for f in facts)


def test_memory_as_prompt_block(tmp_path: Path) -> None:
    store = MemoryStore(path=tmp_path / "mem.json")
    assert store.as_prompt_block() == ""
    store.add_fact("факт 1")
    block = store.as_prompt_block()
    assert "факт 1" in block
    assert "пользователе" in block.lower()


def test_conversation_roundtrip(tmp_path: Path) -> None:
    conv = ConversationStore(path=tmp_path / "conv.json")
    assert conv.load() == []
    turns = [
        {"role": "user", "content": "привет"},
        {"role": "assistant", "content": "слушаю"},
    ]
    conv.save(turns)
    assert conv.load() == turns
    conv.clear()
    assert conv.load() == []
