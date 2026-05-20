"""Память J.A.R.V.I.S. — сохранение истории и контактов."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.utils.logger import log

JARVIS_DIR = Path.home() / ".jarvis"
HISTORY_FILE = JARVIS_DIR / "conversation_history.json"
CONTACTS_FILE = JARVIS_DIR / "contacts.json"


class Memory:
    """Долгосрочная память Джарвиса."""

    def __init__(
        self, max_history: int = 50, data_dir: Path | None = None,
    ) -> None:
        self._data_dir = data_dir or JARVIS_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._data_dir / "conversation_history.json"
        self._contacts_file = self._data_dir / "contacts.json"
        self.max_history = max_history
        self._history: list[dict[str, Any]] = []
        self._contacts: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        """Загрузить данные из файлов."""
        if self._history_file.exists():
            try:
                with open(self._history_file, encoding="utf-8") as f:
                    data = json.load(f)
                self._history = data.get("messages", [])
                log.info(
                    f"Загружена история: {len(self._history)} сообщений"
                )
            except (json.JSONDecodeError, OSError):
                self._history = []

        if self._contacts_file.exists():
            try:
                with open(self._contacts_file, encoding="utf-8") as f:
                    self._contacts = json.load(f)
                log.info(f"Загружено контактов: {len(self._contacts)}")
            except (json.JSONDecodeError, OSError):
                self._contacts = {}

    def save_history(self, messages: list[dict[str, Any]]) -> None:
        """Сохранить историю разговора."""
        self._history = messages[-self.max_history:]
        data = {
            "messages": self._history,
            "updated": datetime.now().isoformat(),
        }
        with open(self._history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_history(self) -> list[dict[str, Any]]:
        """Получить сохранённую историю."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Очистить историю."""
        self._history = []
        if self._history_file.exists():
            self._history_file.unlink()

    # --- Контакты ---

    def add_contact(self, name: str, telegram_id: str, label: str = "") -> None:
        """Добавить контакт."""
        key = name.lower().strip()
        self._contacts[key] = {
            "name": name,
            "telegram_id": telegram_id,
            "label": label,
            "added": datetime.now().isoformat(),
        }
        self._save_contacts()

    def get_contact(self, query: str) -> dict[str, str] | None:
        """Найти контакт по имени или метке."""
        query_lower = query.lower().strip()

        # Прямое совпадение
        if query_lower in self._contacts:
            return self._contacts[query_lower]

        # Поиск по метке (девушка, мама, друг и т.д.)
        for contact in self._contacts.values():
            if contact.get("label", "").lower() == query_lower:
                return contact

        # Частичное совпадение
        for key, contact in self._contacts.items():
            if query_lower in key or query_lower in contact.get("label", "").lower():
                return contact

        return None

    def list_contacts(self) -> list[dict[str, str]]:
        """Список всех контактов."""
        return list(self._contacts.values())

    def remove_contact(self, name: str) -> bool:
        """Удалить контакт."""
        key = name.lower().strip()
        if key in self._contacts:
            del self._contacts[key]
            self._save_contacts()
            return True
        return False

    def _save_contacts(self) -> None:
        with open(self._contacts_file, "w", encoding="utf-8") as f:
            json.dump(self._contacts, f, ensure_ascii=False, indent=2)
