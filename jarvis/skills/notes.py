"""Скилл заметок."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils.logger import log

NOTES_DIR = Path.home() / ".jarvis" / "notes"


class NotesSkill(Skill):
    """Создаёт, читает и удаляет заметки."""

    def __init__(self) -> None:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        self._notes_file = NOTES_DIR / "notes.json"
        self._notes = self._load_notes()

    @property
    def name(self) -> str:
        return "notes"

    @property
    def description(self) -> str:
        return (
            "Управление заметками: создать, прочитать, удалить, список. "
            "Используй когда пользователь просит запомнить, записать, "
            "напомнить что-то, показать записи."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "delete", "search"],
                    "description": (
                        "add — добавить заметку, list — показать все, "
                        "delete — удалить, search — найти по тексту"
                    ),
                },
                "text": {
                    "type": "string",
                    "description": (
                        "Текст заметки (для add) или "
                        "поисковый запрос (для search/delete)"
                    ),
                },
            },
            "required": ["action"],
        }

    def _load_notes(self) -> list[dict[str, str]]:
        """Загрузить заметки из файла."""
        if self._notes_file.exists():
            try:
                with open(self._notes_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_notes(self) -> None:
        """Сохранить заметки в файл."""
        with open(self._notes_file, "w", encoding="utf-8") as f:
            json.dump(self._notes, f, ensure_ascii=False, indent=2)

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "list")
        text = kwargs.get("text", "")

        if action == "add":
            return self._add_note(text)
        elif action == "list":
            return self._list_notes()
        elif action == "delete":
            return self._delete_note(text)
        elif action == "search":
            return self._search_notes(text)
        else:
            return f"Неизвестное действие: {action}"

    def _add_note(self, text: str) -> str:
        if not text:
            return "Не указан текст заметки"

        from datetime import datetime

        note = {
            "text": text,
            "created": datetime.now().isoformat(),
        }
        self._notes.append(note)
        self._save_notes()
        log.info(f"Заметка добавлена: {text[:50]}")
        return f"Записано: {text}"

    def _list_notes(self) -> str:
        if not self._notes:
            return "Заметок пока нет"

        lines = [f"Заметки ({len(self._notes)}):"]
        for i, note in enumerate(self._notes, 1):
            created = note.get("created", "")[:10]
            lines.append(f"  {i}. [{created}] {note['text']}")
        return "\n".join(lines)

    def _delete_note(self, query: str) -> str:
        if not query:
            return "Укажи номер или текст заметки для удаления"

        if query.isdigit():
            idx = int(query) - 1
            if 0 <= idx < len(self._notes):
                removed = self._notes.pop(idx)
                self._save_notes()
                return f"Удалено: {removed['text']}"
            return f"Заметки с номером {query} нет"

        for i, note in enumerate(self._notes):
            if query.lower() in note["text"].lower():
                removed = self._notes.pop(i)
                self._save_notes()
                return f"Удалено: {removed['text']}"

        return f"Заметка не найдена: {query}"

    def _search_notes(self, query: str) -> str:
        if not query:
            return self._list_notes()

        found = [
            n for n in self._notes
            if query.lower() in n["text"].lower()
        ]
        if not found:
            return f"Заметок по запросу '{query}' не найдено"

        lines = [f"Найдено ({len(found)}):"]
        for note in found:
            lines.append(f"  - {note['text']}")
        return "\n".join(lines)
