"""Скилл для работы с файлами: чтение, запись, поиск, листинг каталогов."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from jarvis.skills.base import Skill


class FilesSkill(Skill):
    """Чтение/запись файлов и листинг каталогов на компьютере пользователя."""

    MAX_READ_BYTES = 200_000  # ограничение чтобы не задавить LLM-контекст
    MAX_LIST_ENTRIES = 200

    @property
    def name(self) -> str:
        return "files"

    @property
    def description(self) -> str:
        return (
            "Работа с файлами: list (список файлов в папке), read (прочитать файл), "
            "write (создать/перезаписать файл), append (дописать в файл), "
            "exists (проверить наличие), search (найти файлы по имени). "
            "Используй для просьб типа 'прочитай файл', 'сохрани в файл', "
            "'покажи что в папке', 'найди такие-то файлы'."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "read", "write", "append", "exists", "search"],
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Путь к файлу или каталогу. ~ раскрывается в домашний каталог."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "Содержимое (для write/append).",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob-шаблон для search (например '*.txt').",
                },
            },
            "required": ["action"],
        }

    @staticmethod
    def _resolve(p: str) -> Path:
        return Path(os.path.expanduser(p)).resolve()

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        path_str = kwargs.get("path", "")
        loop = asyncio.get_event_loop()

        try:
            if action == "list":
                return await loop.run_in_executor(None, self._list, path_str or ".")
            if action == "read":
                if not path_str:
                    return "Не указан путь"
                return await loop.run_in_executor(None, self._read, path_str)
            if action == "write":
                if not path_str:
                    return "Не указан путь"
                return await loop.run_in_executor(
                    None, self._write, path_str, kwargs.get("content", ""), False,
                )
            if action == "append":
                if not path_str:
                    return "Не указан путь"
                return await loop.run_in_executor(
                    None, self._write, path_str, kwargs.get("content", ""), True,
                )
            if action == "exists":
                if not path_str:
                    return "Не указан путь"
                return "да" if self._resolve(path_str).exists() else "нет"
            if action == "search":
                return await loop.run_in_executor(
                    None, self._search, path_str or ".", kwargs.get("pattern", "*"),
                )
            return f"Неизвестное действие: {action}"
        except Exception as e:
            return f"Ошибка работы с файлом: {e}"

    def _list(self, path: str) -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"Путь не найден: {p}"
        if not p.is_dir():
            return f"Это не каталог: {p}"
        entries = []
        for i, item in enumerate(sorted(p.iterdir())):
            if i >= self.MAX_LIST_ENTRIES:
                entries.append("… (обрезано)")
                break
            kind = "📁" if item.is_dir() else "📄"
            entries.append(f"{kind} {item.name}")
        if not entries:
            return f"Папка пуста: {p}"
        return f"Содержимое {p}:\n" + "\n".join(entries)

    def _read(self, path: str) -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"Файл не найден: {p}"
        if not p.is_file():
            return f"Это не файл: {p}"
        size = p.stat().st_size
        with open(p, "rb") as f:
            data = f.read(self.MAX_READ_BYTES)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return f"Бинарный файл ({size} байт): {p}"
        suffix = ""
        if size > self.MAX_READ_BYTES:
            suffix = f"\n… (показано {self.MAX_READ_BYTES} из {size} байт)"
        return f"Содержимое {p}:\n{text}{suffix}"

    def _write(self, path: str, content: str, append: bool) -> str:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        return f"{'Дозапись' if append else 'Запись'} в {p} ({len(content)} симв.)"

    def _search(self, path: str, pattern: str) -> str:
        p = self._resolve(path)
        if not p.exists():
            return f"Путь не найден: {p}"
        results = list(p.rglob(pattern))
        if not results:
            return f"Ничего не найдено по '{pattern}' в {p}"
        results = results[: self.MAX_LIST_ENTRIES]
        return f"Найдено {len(results)} в {p}:\n" + "\n".join(str(r) for r in results)
