"""Контакты — сохранение и поиск контактов с метками (девушка, мама, друг)."""

from __future__ import annotations

import json
from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils.paths import CONTACTS_FILE, ensure_dirs


class ContactsSkill(Skill):
    """Управление контактами: добавить, найти, удалить, список."""

    @property
    def name(self) -> str:
        return "contacts"

    @property
    def description(self) -> str:
        return (
            "Управление контактами пользователя. Действия: "
            "add (добавить контакт), find (найти по имени или метке), "
            "list (показать все), delete (удалить). "
            "Поле label — метка-роль: девушка, мама, друг, коллега, и т.д. "
            "Когда пользователь говорит 'напиши моей девушке' — "
            "ищи по label='девушка'."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "find", "list", "delete"],
                    "description": "Действие",
                },
                "name": {
                    "type": "string",
                    "description": "Имя контакта",
                },
                "telegram_id": {
                    "type": "string",
                    "description": "Telegram username или ID",
                },
                "label": {
                    "type": "string",
                    "description": (
                        "Метка-роль: девушка, мама, друг, коллега, босс"
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action")
        name = (kwargs.get("name") or "").strip()
        telegram_id = (kwargs.get("telegram_id") or "").strip()
        label = (kwargs.get("label") or "").strip()

        if action == "add":
            if not name:
                return "Укажи имя контакта"
            return self._add(name, telegram_id, label)

        if action == "find":
            query = name or label
            if not query:
                return "Укажи имя или метку для поиска"
            return self._find(query)

        if action == "list":
            return self._list_all()

        if action == "delete":
            if not name:
                return "Укажи имя контакта для удаления"
            return self._delete(name)

        return f"Неизвестное действие: {action}"

    # ---------- internal ----------

    def _load(self) -> dict[str, dict[str, str]]:
        if not CONTACTS_FILE.exists():
            return {}
        try:
            return json.loads(
                CONTACTS_FILE.read_text(encoding="utf-8"),
            )
        except Exception:
            return {}

    def _save(self, contacts: dict[str, dict[str, str]]) -> None:
        ensure_dirs()
        CONTACTS_FILE.write_text(
            json.dumps(contacts, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _add(
        self, name: str, telegram_id: str, label: str,
    ) -> str:
        contacts = self._load()
        key = name.lower().strip()
        contacts[key] = {
            "name": name,
            "telegram_id": telegram_id,
            "label": label,
        }
        self._save(contacts)
        label_str = f" ({label})" if label else ""
        tg_str = f", Telegram: {telegram_id}" if telegram_id else ""
        return f"Контакт сохранён: {name}{label_str}{tg_str}"

    def _find(self, query: str) -> str:
        contacts = self._load()
        query_lower = query.lower().strip()

        if query_lower in contacts:
            return self._format_contact(contacts[query_lower])

        for contact in contacts.values():
            if contact.get("label", "").lower() == query_lower:
                return self._format_contact(contact)

        for key, contact in contacts.items():
            if (
                query_lower in key
                or query_lower in contact.get("label", "").lower()
            ):
                return self._format_contact(contact)

        return f"Контакт '{query}' не найден"

    def _list_all(self) -> str:
        contacts = self._load()
        if not contacts:
            return "Контактов пока нет"
        lines = []
        for c in contacts.values():
            lines.append(self._format_contact(c))
        return "\n".join(lines)

    def _delete(self, name: str) -> str:
        contacts = self._load()
        key = name.lower().strip()
        if key not in contacts:
            return f"Контакт '{name}' не найден"
        del contacts[key]
        self._save(contacts)
        return f"Контакт '{name}' удалён"

    @staticmethod
    def _format_contact(c: dict[str, str]) -> str:
        parts = [c.get("name", "?")]
        if c.get("label"):
            parts.append(f"({c['label']})")
        if c.get("telegram_id"):
            parts.append(f"TG: {c['telegram_id']}")
        return " — ".join(parts)
