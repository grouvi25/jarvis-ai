"""Скилл автоматического переподключения к интернету."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from jarvis.core.config import InternetConfig
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class InternetReconnectSkill(Skill):
    """Проверяет и восстанавливает интернет-соединение."""

    def __init__(self, config: InternetConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._monitoring = False

    @property
    def name(self) -> str:
        return "reconnect_internet"

    @property
    def description(self) -> str:
        return (
            "Проверить и восстановить интернет-соединение. "
            "Переподключает WiFi и проходит captive portal (авторизацию). "
            "Используй когда пользователь говорит что нет интернета, "
            "или когда нужно переподключиться к сети."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["check", "reconnect", "status"],
                    "description": (
                        "check — проверить есть ли интернет, "
                        "reconnect — переподключиться, "
                        "status — показать статус сети"
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "check")

        if action == "check":
            return await self._check_internet()
        elif action == "reconnect":
            return await self._reconnect()
        elif action == "status":
            return await self._network_status()
        else:
            return f"Неизвестное действие: {action}"

    async def _check_internet(self) -> str:
        """Проверить наличие интернета."""
        is_online = await self._ping()
        if is_online:
            return "Интернет работает"
        else:
            return "Интернет недоступен"

    async def _ping(self) -> bool:
        """Пинг для проверки интернета."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["ping", "-c", "1", "-W", "3", self._config.ping_host],
                    capture_output=True,
                    timeout=5,
                ),
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def _reconnect(self) -> str:
        """Полный цикл переподключения."""
        log.info("Начинаю переподключение к интернету...")
        steps: list[str] = []

        # Шаг 1: Проверяем текущее состояние
        if await self._ping():
            return "Интернет уже работает, переподключение не требуется"

        await self._event_bus.emit(Event(
            type=EventType.INTERNET_LOST,
            source="internet_skill",
        ))

        # Шаг 2: Переподключаем WiFi
        if self._config.wifi_ssid:
            steps.append(await self._reconnect_wifi())
        else:
            # Пробуем просто перезапустить NetworkManager
            steps.append(await self._restart_network())

        await asyncio.sleep(3)

        # Шаг 3: Captive portal
        if self._config.captive_portal.enabled:
            steps.append(await self._handle_captive_portal())
            await asyncio.sleep(2)

        # Шаг 4: Финальная проверка
        if await self._ping():
            steps.append("Интернет восстановлен!")
            await self._event_bus.emit(Event(
                type=EventType.INTERNET_RESTORED,
                source="internet_skill",
            ))
        else:
            steps.append("Не удалось восстановить интернет")

        return "\n".join(steps)

    async def _reconnect_wifi(self) -> str:
        """Переподключение к WiFi через nmcli."""
        loop = asyncio.get_event_loop()
        try:
            # Отключаемся
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["nmcli", "device", "wifi", "rescan"],
                    capture_output=True,
                    timeout=10,
                ),
            )
            await asyncio.sleep(2)

            # Подключаемся
            cmd = ["nmcli", "device", "wifi", "connect", self._config.wifi_ssid]
            if self._config.wifi_password:
                cmd.extend(["password", self._config.wifi_password])

            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=15),
            )

            if result.returncode == 0:
                return f"WiFi подключён: {self._config.wifi_ssid}"
            else:
                return f"Ошибка WiFi: {result.stderr.strip()}"

        except Exception as e:
            return f"Ошибка переподключения WiFi: {e}"

    async def _restart_network(self) -> str:
        """Перезапуск NetworkManager."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["sudo", "systemctl", "restart", "NetworkManager"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                ),
            )
            if result.returncode == 0:
                return "NetworkManager перезапущен"
            else:
                return f"Ошибка перезапуска NetworkManager: {result.stderr.strip()}"
        except Exception as e:
            return f"Ошибка: {e}"

    async def _handle_captive_portal(self) -> str:
        """Авторизация на captive portal."""
        portal = self._config.captive_portal
        if not portal.url:
            return "URL captive portal не настроен"

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                data = {}
                if portal.username:
                    data["username"] = portal.username
                if portal.password:
                    data["password"] = portal.password

                if portal.method.upper() == "POST":
                    async with session.post(portal.url, data=data) as resp:
                        status = resp.status
                elif portal.method.upper() == "GET":
                    async with session.get(portal.url, params=data) as resp:
                        status = resp.status
                else:
                    return f"Неизвестный HTTP метод: {portal.method}"

                if status in (200, 302, 301):
                    return f"Captive portal авторизация выполнена (статус {status})"
                else:
                    return f"Captive portal вернул статус {status}"

        except Exception as e:
            return f"Ошибка captive portal: {e}"

    async def _network_status(self) -> str:
        """Показать статус сети."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["nmcli", "general", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                ),
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "Не удалось получить статус сети"
        except Exception:
            return "nmcli недоступен"

    async def start_monitoring(self) -> None:
        """Запустить фоновый мониторинг интернета."""
        if not self._config.enabled:
            return

        self._monitoring = True
        log.info(
            f"Мониторинг интернета запущен "
            f"(проверка каждые {self._config.check_interval} сек)"
        )

        while self._monitoring:
            await asyncio.sleep(self._config.check_interval)
            if not await self._ping():
                log.warning("Интернет пропал! Переподключаюсь...")
                result = await self._reconnect()
                log.info(f"Результат переподключения: {result}")

    def stop_monitoring(self) -> None:
        """Остановить мониторинг."""
        self._monitoring = False
