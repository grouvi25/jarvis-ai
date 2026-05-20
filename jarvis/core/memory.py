"""Долговременная память Джарвиса: факты о пользователе + история диалога."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jarvis.utils.paths import CONVERSATION_FILE, MEMORY_FILE, ensure_dirs


@dataclass
class Memory:
    """Сохраняемое в файл состояние памяти."""

    facts: list[str] = field(default_factory=list)
    preferences: dict[str, str] = field(default_factory=dict)


class MemoryStore:
    """Хранит факты о пользователе между сессиями.

    Брейн вызывает `remember_fact` через skill, чтобы запомнить что-то полезное
    («меня зовут Никита», «я живу в Москве», «не пингай меня по утрам»).
    """

    def __init__(self, path: Path = MEMORY_FILE) -> None:
        self.path = path
        self.memory = Memory()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.memory = Memory(
                facts=list(data.get("facts", [])),
                preferences=dict(data.get("preferences", {})),
            )
        except Exception:
            # повреждённый файл — стартуем с чистого листа
            self.memory = Memory()

    def _save(self) -> None:
        ensure_dirs()
        self.path.write_text(
            json.dumps(
                {"facts": self.memory.facts, "preferences": self.memory.preferences},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def add_fact(self, fact: str) -> str:
        fact = fact.strip()
        if not fact:
            return "пустой факт"
        if fact in self.memory.facts:
            return "этот факт уже запомнен"
        self.memory.facts.append(fact)
        self._save()
        return "запомнено"

    def remove_fact(self, fact: str) -> str:
        before = len(self.memory.facts)
        self.memory.facts = [
            f for f in self.memory.facts if fact.lower() not in f.lower()
        ]
        self._save()
        return f"удалено {before - len(self.memory.facts)} факт(ов)"

    def all_facts(self) -> list[str]:
        return list(self.memory.facts)

    def as_prompt_block(self) -> str:
        """Сформировать кусочек системного промпта с запомненными фактами."""
        if not self.memory.facts:
            return ""
        bullets = "\n".join(f"- {f}" for f in self.memory.facts)
        return (
            "Что ты помнишь о пользователе (используй это в ответах):\n"
            f"{bullets}"
        )

    def set_preference(self, key: str, value: str) -> None:
        self.memory.preferences[key] = value
        self._save()

    def get_preference(self, key: str, default: str = "") -> str:
        return self.memory.preferences.get(key, default)


class ConversationStore:
    """Хранит историю диалога в JSON (для восстановления после перезапуска)."""

    MAX_TURNS = 200

    def __init__(self, path: Path = CONVERSATION_FILE) -> None:
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get("turns", []) if isinstance(data, dict) else []
        except Exception:
            return []

    def save(self, turns: list[dict[str, Any]]) -> None:
        ensure_dirs()
        # Обрезаем длинную историю, сохраняем последние N
        trimmed = turns[-self.MAX_TURNS :]
        self.path.write_text(
            json.dumps(
                {"updated_at": datetime.now(timezone.utc).isoformat(), "turns": trimmed},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
