"""Скилл системной информации."""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
from datetime import datetime
from typing import Any

from jarvis.skills.base import Skill


class SystemInfoSkill(Skill):
    """Информация о системе — время, батарея, CPU, диск, процессы."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return (
            "Информация о компьютере: текущее время и дата, "
            "заряд батареи, загрузка CPU, свободное место на диске, "
            "запущенные процессы, имя пользователя. "
            "Используй когда пользователь спрашивает время, "
            "дату, заряд батареи, состояние компьютера."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "enum": [
                        "time", "date", "battery", "cpu",
                        "disk", "memory", "processes", "full",
                    ],
                    "description": (
                        "Что именно узнать: time (время), "
                        "date (дата), battery (батарея), "
                        "cpu (нагрузка), disk (место), "
                        "memory (RAM), processes (топ процессов), "
                        "full (всё сразу)"
                    ),
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "full")

        handlers = {
            "time": self._get_time,
            "date": self._get_date,
            "battery": self._get_battery,
            "cpu": self._get_cpu,
            "disk": self._get_disk,
            "memory": self._get_memory,
            "processes": self._get_processes,
        }

        if query == "full":
            parts = []
            for handler in handlers.values():
                parts.append(await handler())
            return "\n".join(parts)

        handler = handlers.get(query)
        if handler:
            return await handler()
        return f"Неизвестный запрос: {query}"

    async def _get_time(self) -> str:
        now = datetime.now()
        return f"Текущее время: {now.strftime('%H:%M:%S')}"

    async def _get_date(self) -> str:
        now = datetime.now()
        days_ru = [
            "понедельник", "вторник", "среда", "четверг",
            "пятница", "суббота", "воскресенье",
        ]
        months_ru = [
            "", "января", "февраля", "марта", "апреля",
            "мая", "июня", "июля", "августа",
            "сентября", "октября", "ноября", "декабря",
        ]
        day_name = days_ru[now.weekday()]
        return (
            f"Сегодня {day_name}, {now.day} {months_ru[now.month]} "
            f"{now.year} года, {now.strftime('%H:%M')}"
        )

    async def _get_battery(self) -> str:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["cat", "/sys/class/power_supply/BAT0/capacity"],
                    capture_output=True, text=True, timeout=5,
                ),
            )
            if result.returncode == 0:
                pct = result.stdout.strip()
                status_result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        ["cat", "/sys/class/power_supply/BAT0/status"],
                        capture_output=True, text=True, timeout=5,
                    ),
                )
                status = status_result.stdout.strip() if status_result.returncode == 0 else ""
                status_ru = {
                    "Charging": "заряжается",
                    "Discharging": "разряжается",
                    "Full": "полностью заряжен",
                    "Not charging": "не заряжается",
                }.get(status, status)
                return f"Батарея: {pct}% ({status_ru})"
            return "Батарея: информация недоступна (возможно, десктоп)"
        except Exception:
            return "Батарея: информация недоступна"

    async def _get_cpu(self) -> str:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["cat", "/proc/loadavg"],
                    capture_output=True, text=True, timeout=5,
                ),
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                cores = os.cpu_count() or 1
                load1 = float(parts[0])
                load_pct = int(load1 / cores * 100)
                return (
                    f"CPU: нагрузка {load_pct}% "
                    f"({parts[0]}/{parts[1]}/{parts[2]}), "
                    f"{cores} ядер, {platform.processor() or platform.machine()}"
                )
        except Exception:
            pass
        return f"CPU: {os.cpu_count()} ядер, {platform.machine()}"

    async def _get_disk(self) -> str:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["df", "-h", "--output=target,size,avail,pcent", "/"],
                    capture_output=True, text=True, timeout=5,
                ),
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    return (
                        f"Диск /: {parts[2]} свободно из {parts[1]} "
                        f"(использовано {parts[3]})"
                    )
        except Exception:
            pass
        return "Диск: информация недоступна"

    async def _get_memory(self) -> str:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["free", "-h", "--si"],
                    capture_output=True, text=True, timeout=5,
                ),
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    return (
                        f"RAM: {parts[2]} использовано из {parts[1]} "
                        f"(свободно {parts[3]})"
                    )
        except Exception:
            pass
        return "RAM: информация недоступна"

    async def _get_processes(self) -> str:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["ps", "aux", "--sort=-%cpu"],
                    capture_output=True, text=True, timeout=5,
                ),
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[:6]
                return "Топ процессы по CPU:\n" + "\n".join(
                    f"  {line}" for line in lines
                )
        except Exception:
            pass
        return "Процессы: информация недоступна"
