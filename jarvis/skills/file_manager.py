"""Скилл работы с файлами."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class FileManagerSkill(Skill):
    """Работа с файлами — поиск, чтение, открытие."""

    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return (
            "Работа с файлами на компьютере: найти файл, прочитать содержимое, "
            "открыть файл, показать содержимое папки. "
            "Используй когда пользователь просит найти файл, "
            "открыть документ, показать что в папке."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["find", "read", "open", "list_dir"],
                    "description": (
                        "find — найти файл по имени, "
                        "read — прочитать содержимое текстового файла, "
                        "open — открыть файл стандартной программой, "
                        "list_dir — показать содержимое папки"
                    ),
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Путь к файлу/папке или имя файла для поиска"
                    ),
                },
                "directory": {
                    "type": "string",
                    "description": (
                        "Директория для поиска "
                        "(по умолчанию домашняя папка)"
                    ),
                },
            },
            "required": ["action", "path"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        path = kwargs.get("path", "")
        directory = kwargs.get("directory", str(Path.home()))

        if not path:
            return "Укажи путь или имя файла"

        try:
            if action == "find":
                return await self._find_file(path, directory)
            elif action == "read":
                return await self._read_file(path)
            elif action == "open":
                return await self._open_file(path)
            elif action == "list_dir":
                return await self._list_dir(path)
            else:
                return f"Неизвестное действие: {action}"
        except Exception as e:
            return f"Ошибка: {e}"

    async def _find_file(self, name: str, directory: str) -> str:
        """Найти файл по имени."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["find", directory, "-maxdepth", "5",
                     "-iname", f"*{name}*", "-type", "f"],
                    capture_output=True, text=True, timeout=10,
                ),
            )
            files = result.stdout.strip().split("\n")
            files = [f for f in files if f]

            if not files:
                return f"Файлы с именем '{name}' не найдены в {directory}"

            if len(files) > 15:
                files = files[:15]
                return (
                    "Найдено много файлов, показываю первые 15:\n"
                    + "\n".join(f"  {f}" for f in files)
                )

            return f"Найдено ({len(files)}):\n" + "\n".join(
                f"  {f}" for f in files
            )
        except subprocess.TimeoutExpired:
            return "Поиск занял слишком долго, попробуй сузить директорию"

    async def _read_file(self, path: str) -> str:
        """Прочитать текстовый файл."""
        p = Path(path).expanduser()
        if not p.exists():
            return f"Файл не найден: {path}"
        if not p.is_file():
            return f"Это не файл: {path}"
        if p.stat().st_size > 100_000:
            return f"Файл слишком большой ({p.stat().st_size} байт)"

        try:
            content = p.read_text(encoding="utf-8")
            if len(content) > 3000:
                content = content[:3000] + "\n... (обрезано)"
            return f"Содержимое {p.name}:\n{content}"
        except UnicodeDecodeError:
            return f"Файл '{p.name}' — бинарный, не могу прочитать как текст"

    async def _open_file(self, path: str) -> str:
        """Открыть файл стандартной программой."""
        p = Path(path).expanduser()
        if not p.exists():
            return f"Файл не найден: {path}"

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: subprocess.Popen(
                    ["xdg-open", str(p)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                ),
            )
            log.info(f"Открыт файл: {p}")
            return f"Файл открыт: {p.name}"
        except FileNotFoundError:
            return "xdg-open не найден — не могу открыть файл"

    async def _list_dir(self, path: str) -> str:
        """Показать содержимое директории."""
        p = Path(path).expanduser()
        if not p.exists():
            return f"Директория не найдена: {path}"
        if not p.is_dir():
            return f"Это не директория: {path}"

        items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        if not items:
            return f"Папка пуста: {path}"

        lines = [f"Содержимое {p} ({len(items)} элементов):"]
        for item in items[:30]:
            icon = "📁" if item.is_dir() else "📄"
            size = ""
            if item.is_file():
                s = item.stat().st_size
                if s >= 1_000_000:
                    size = f" ({s / 1_000_000:.1f} МБ)"
                elif s >= 1_000:
                    size = f" ({s / 1_000:.1f} КБ)"
                else:
                    size = f" ({s} Б)"
            lines.append(f"  {icon} {item.name}{size}")

        if len(items) > 30:
            lines.append(f"  ... и ещё {len(items) - 30}")

        return "\n".join(lines)
