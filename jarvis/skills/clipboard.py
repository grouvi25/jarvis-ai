"""Скилл буфера обмена."""

from __future__ import annotations

import asyncio
from typing import Any

from jarvis.skills.base import Skill


class ClipboardSkill(Skill):
    @property
    def name(self) -> str:
        return "clipboard"

    @property
    def description(self) -> str:
        return (
            "Буфер обмена: get (что сейчас скопировано), set (положить текст в буфер). "
            "Используй когда пользователь просит скопировать что-то или вставить, "
            "или хочет посмотреть что у него в буфере."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["get", "set"]},
                "text": {"type": "string", "description": "Текст для копирования (action=set)"},
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action")
        loop = asyncio.get_event_loop()
        try:
            import pyperclip
        except ImportError:
            return "pyperclip не установлен"

        try:
            if action == "get":
                text = await loop.run_in_executor(None, pyperclip.paste)
                if not text:
                    return "буфер пуст"
                return f"В буфере: {text[:1000]}"
            if action == "set":
                text = kwargs.get("text", "")
                await loop.run_in_executor(None, pyperclip.copy, text)
                return f"Скопировано в буфер: {text[:80]}"
            return f"Неизвестное действие: {action}"
        except Exception as e:
            return f"Ошибка буфера обмена: {e}"
