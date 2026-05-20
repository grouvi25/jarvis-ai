"""Скилл управления контактами."""

from __future__ import annotations

from typing import Any

from jarvis.core.memory import Memory
from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class ContactsSkill(Skill):
    """Управление контактами — добавить, найти, удалить."""

    def __init__(self, memory: Memory) -> None:
        self._memory = memory

    @property
    def name(self) -> str:
        return "contacts"

    @property
    def description(self) -> str:
        return (
            "Управление контактами: добавить, найти, удалить, показать список. "
            "Используй когда пользователь просит добавить контакт, "
            "узнать чей-то Telegram, или написать кому-то по имени/метке "
            "(девушка, мама, друг и т.д.). "
            "Для отправки сообщения контакту — сначала найди контакт через "
            "эту функцию, потом используй send_telegram_message."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "find", "list", "remove"],
                    "description": (
                        "add — добавить контакт, find — найти контакт, "
                        "list — показать все контакты, remove — удалить"
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Имя контакта",
                },
                "telegram_id": {
                    "type": "string",
                    "description": (
                        "Telegram ID или @username контакта "
                        "(для add)"
                    ),
                },
                "label": {
                    "type": "string",
                    "description": (
                        "Метка/роль контакта: девушка, мама, "
                        "друг, босс и т.д. (для add)"
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "list")
        name = kwargs.get("name", "")
        telegram_id = kwargs.get("telegram_id", "")
        label = kwargs.get("label", "")

        if action == "add":
            if not name or not telegram_id:
                return "Укажи имя и telegram_id контакта"
            self._memory.add_contact(name, telegram_id, label)
            label_str = f" ({label})" if label else ""
            log.info(f"Контакт добавлен: {name}{label_str}")
            return f"Контакт добавлен: {name}{label_str} → {telegram_id}"

        elif action == "find":
            if not name:
                return "Укажи имя или метку для поиска"
            contact = self._memory.get_contact(name)
            if contact:
                label_str = f" ({contact['label']})" if contact.get("label") else ""
                return (
                    f"Найден контакт: {contact['name']}{label_str} "
                    f"→ Telegram: {contact['telegram_id']}"
                )
            return f"Контакт '{name}' не найден"

        elif action == "list":
            contacts = self._memory.list_contacts()
            if not contacts:
                return "Контактов пока нет. Добавь: 'Джарвис, добавь контакт ...'"
            lines = [f"Контакты ({len(contacts)}):"]
            for c in contacts:
                label_str = f" ({c['label']})" if c.get("label") else ""
                lines.append(
                    f"  - {c['name']}{label_str}: {c['telegram_id']}"
                )
            return "\n".join(lines)

        elif action == "remove":
            if not name:
                return "Укажи имя контакта для удаления"
            if self._memory.remove_contact(name):
                return f"Контакт '{name}' удалён"
            return f"Контакт '{name}' не найден"

        return f"Неизвестное действие: {action}"
