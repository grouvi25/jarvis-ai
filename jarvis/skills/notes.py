"""Заметки и память Джарвиса о пользователе."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from jarvis.core.memory import MemoryStore
from jarvis.skills.base import Skill
from jarvis.utils import paths as _paths
from jarvis.utils.paths import ensure_dirs


class NotesSkill(Skill):
    """Скилл заметок: добавить, прочитать, удалить + долгая память о пользователе."""

    def __init__(self, memory: MemoryStore | None = None) -> None:
        self._memory = memory or MemoryStore()

    @property
    def name(self) -> str:
        return "notes"

    @property
    def description(self) -> str:
        return (
            "Заметки и память: add_note (добавить заметку), list_notes "
            "(список заметок), clear_notes (удалить все), "
            "remember (запомнить факт о пользователе на будущее, например 'меня зовут …'), "
            "forget (забыть факт), recall (показать что запомнил). "
            "ВАЖНО: когда пользователь говорит 'запомни/я хочу чтобы ты знал/меня зовут' — "
            "используй remember."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "add_note", "list_notes", "clear_notes",
                        "remember", "forget", "recall",
                    ],
                },
                "text": {
                    "type": "string",
                    "description": "Текст заметки или факта",
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action")
        text = (kwargs.get("text") or "").strip()
        if action == "add_note":
            if not text:
                return "Не указан текст заметки"
            return self._add_note(text)
        if action == "list_notes":
            return self._list_notes()
        if action == "clear_notes":
            self._save_notes([])
            return "Все заметки удалены"
        if action == "remember":
            if not text:
                return "Не указан факт"
            return f"Запомнил: '{text}'. ({self._memory.add_fact(text)})"
        if action == "forget":
            if not text:
                return "Не указано что забыть"
            return self._memory.remove_fact(text)
        if action == "recall":
            facts = self._memory.all_facts()
            if not facts:
                return "Я пока ничего о тебе не запомнил."
            return "Что я о тебе помню:\n" + "\n".join(f"- {f}" for f in facts)
        return f"Неизвестное действие: {action}"

    # ---------- internal ----------

    def _load_notes(self) -> list[dict[str, Any]]:
        if not _paths.NOTES_FILE.exists():
            return []
        try:
            return json.loads(_paths.NOTES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_notes(self, notes: list[dict[str, Any]]) -> None:
        ensure_dirs()
        _paths.NOTES_FILE.write_text(
            json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _add_note(self, text: str) -> str:
        notes = self._load_notes()
        notes.append({"at": datetime.now(timezone.utc).isoformat(), "text": text})
        self._save_notes(notes)
        return f"Заметка добавлена ({len(notes)} всего)"

    def _list_notes(self) -> str:
        notes = self._load_notes()
        if not notes:
            return "Заметок пока нет"
        return "\n".join(
            f"[{i+1}] {n['at'][:16]}: {n['text']}" for i, n in enumerate(notes)
        )
