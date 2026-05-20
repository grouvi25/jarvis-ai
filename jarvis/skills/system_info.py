"""Скилл системной информации: CPU, RAM, диск, батарея, процессы."""

from __future__ import annotations

import asyncio
import platform
from typing import Any

from jarvis.skills.base import Skill


class SystemInfoSkill(Skill):
    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return (
            "Информация о компьютере: cpu, ram, disk, battery, processes (топ по памяти), "
            "all (всё сразу). Используй когда пользователь спрашивает 'как нагружен пк', "
            "'сколько свободной памяти', 'батарея', 'что грузит компьютер'."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "what": {
                    "type": "string",
                    "enum": ["cpu", "ram", "disk", "battery", "processes", "all"],
                },
            },
            "required": ["what"],
        }

    async def execute(self, **kwargs: Any) -> str:
        what = kwargs.get("what", "all")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._gather, what)

    def _gather(self, what: str) -> str:
        try:
            import psutil
        except ImportError:
            return "psutil не установлен"

        parts: list[str] = []

        if what in ("cpu", "all"):
            cpu = psutil.cpu_percent(interval=0.3)
            cpu_count = psutil.cpu_count()
            parts.append(f"CPU: {cpu:.0f}% ({cpu_count} ядер, {platform.processor() or 'unknown'})")

        if what in ("ram", "all"):
            mem = psutil.virtual_memory()
            parts.append(
                f"RAM: {mem.percent:.0f}% занято "
                f"({mem.used / 1024**3:.1f} / {mem.total / 1024**3:.1f} GB)"
            )

        if what in ("disk", "all"):
            try:
                disk = psutil.disk_usage("/")
                parts.append(
                    f"Диск /: {disk.percent:.0f}% занято "
                    f"({disk.used / 1024**3:.1f} / {disk.total / 1024**3:.1f} GB)"
                )
            except Exception:
                pass

        if what in ("battery", "all"):
            try:
                bat = psutil.sensors_battery()
                if bat:
                    state = "заряжается" if bat.power_plugged else "от батареи"
                    parts.append(f"Батарея: {bat.percent:.0f}% ({state})")
            except Exception:
                pass

        if what in ("processes", "all"):
            try:
                procs = []
                for p in psutil.process_iter(["name", "memory_percent"]):
                    try:
                        procs.append((p.info["name"], p.info["memory_percent"] or 0))
                    except Exception:
                        pass
                procs.sort(key=lambda x: x[1], reverse=True)
                top = procs[:5]
                top_str = ", ".join(f"{n} ({m:.1f}%)" for n, m in top)
                parts.append(f"Топ процессов по RAM: {top_str}")
            except Exception:
                pass

        if not parts:
            return f"Нечего показать для '{what}'"
        return "\n".join(parts)
