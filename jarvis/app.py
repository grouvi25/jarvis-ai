"""J.A.R.V.I.S. Desktop App — точка входа фоновой программы.

Запускает в одном процессе:
- FastAPI/uvicorn-сервер (web-UI и API на localhost)
- Системный трей (pystray)
- Опционально голос (wake word + микрофон)

Открыть UI: клик по иконке в трее. Выйти: меню → Выход.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from typing import Any

from jarvis.core.brain import Brain
from jarvis.core.config import (
    JarvisConfig,
    is_first_run,
    load_config,
    save_config,
)
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.skills.browser import BrowserSkill
from jarvis.skills.clipboard import ClipboardSkill
from jarvis.skills.desktop import DesktopControlSkill
from jarvis.skills.files import FilesSkill
from jarvis.skills.internet import InternetReconnectSkill
from jarvis.skills.messenger import TelegramMessengerSkill
from jarvis.skills.notes import NotesSkill
from jarvis.skills.system_info import SystemInfoSkill
from jarvis.skills.time_skill import TimeSkill
from jarvis.skills.web_search import WebSearchSkill
from jarvis.ui.server import create_app, find_free_port
from jarvis.ui.tray import JarvisTray
from jarvis.utils import autostart, platform as plat
from jarvis.utils.audio import configure_pydub
from jarvis.utils.logger import log
from jarvis.utils.paths import ensure_dirs
from jarvis.voice.speaker import Speaker


def register_all_skills(brain: Brain, config: JarvisConfig, event_bus: EventBus) -> None:
    """Зарегистрировать все стандартные скиллы."""
    brain.register_skill(DesktopControlSkill())
    brain.register_skill(FilesSkill())
    brain.register_skill(ClipboardSkill())
    brain.register_skill(SystemInfoSkill())
    brain.register_skill(TimeSkill(event_bus))
    brain.register_skill(NotesSkill(brain.memory))
    brain.register_skill(WebSearchSkill())
    brain.register_skill(BrowserSkill(config))
    brain.register_skill(InternetReconnectSkill(config.internet, event_bus))
    brain.register_skill(TelegramMessengerSkill(config))


class JarvisApp:
    """Главный контроллер desktop-приложения."""

    def __init__(self, config: JarvisConfig, *, no_tray: bool = False) -> None:
        self.config = config
        self.no_tray = no_tray
        self.event_bus = EventBus()
        self.brain = Brain(config, self.event_bus)
        self.speaker = Speaker(config.tts, self.event_bus)
        self._stop_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tray: JarvisTray | None = None
        self._voice_task: asyncio.Task | None = None
        self._url: str = ""

        register_all_skills(self.brain, config, self.event_bus)

    # ---------- voice ----------

    async def _start_voice(self) -> None:
        """Запуск голосового движка в фоне (если установлены зависимости)."""
        try:
            from jarvis.voice.listener import SpeechListener
            from jarvis.voice.wake_word import WakeWordDetector
        except Exception as e:
            log.info(f"Голосовой режим недоступен ({e})")
            return

        listener = SpeechListener(self.config.stt, self.event_bus)
        wake = WakeWordDetector(self.config, self.event_bus)

        async def on_wake(event: Event) -> None:
            text = (event.data.get("remaining_text") or "").strip()
            if not text:
                await self.speaker.speak("Слушаю")
                return
            response = await self.brain.think(text)
            if self.config.voice_enabled:
                await self.speaker.speak(response)

        self.event_bus.on(EventType.WAKE_WORD_DETECTED, on_wake)

        try:
            await asyncio.gather(
                listener.listen_continuous(),
                wake.listen(),
            )
        except asyncio.CancelledError:
            listener.stop()
            wake.stop()
            raise
        except Exception as e:
            log.warning(f"Voice loop остановлен: {e}")

    # ---------- tray callbacks ----------

    def _toggle_voice(self) -> bool:
        self.config.voice_enabled = not self.config.voice_enabled
        save_config(self.config)
        if self._tray is not None:
            self._tray.notify(
                "Jarvis",
                f"Голос {'включён' if self.config.voice_enabled else 'выключен'}",
            )
        return self.config.voice_enabled

    def _reload_config(self) -> None:
        new_cfg = load_config()
        self.config.__dict__.update(new_cfg.__dict__)
        log.info("Конфиг перезагружен")
        if self._tray is not None:
            self._tray.notify("Jarvis", "Конфиг перезагружен")

    def _request_quit(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)

    # ---------- main run ----------

    async def run(self) -> None:
        self._loop = asyncio.get_event_loop()
        ensure_dirs()
        configure_pydub()

        # 1. Сервер
        port = find_free_port(self.config.server.host, self.config.server.port)
        self._url = f"http://{self.config.server.host}:{port}"
        log.info(f"Jarvis API/UI: [bold cyan]{self._url}[/bold cyan]")

        app = create_app(self.brain, self.config, self.event_bus, speaker=self.speaker)
        import uvicorn

        ucfg = uvicorn.Config(
            app,
            host=self.config.server.host,
            port=port,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(ucfg)
        server_task = asyncio.create_task(server.serve(), name="uvicorn")

        # 2. Event bus
        bus_task = asyncio.create_task(self.event_bus.process_events(), name="event-bus")

        # 3. Internet monitor (если включено)
        bg_tasks: list[asyncio.Task[Any]] = [server_task, bus_task]
        if self.config.internet.enabled:
            for skill in self.brain.skills.values():
                if isinstance(skill, InternetReconnectSkill):
                    bg_tasks.append(asyncio.create_task(
                        skill.start_monitoring(), name="internet",
                    ))

        # 4. Голос
        if self.config.voice_enabled:
            self._voice_task = asyncio.create_task(self._start_voice(), name="voice")
            bg_tasks.append(self._voice_task)

        # 5. Трей (в фоновом потоке)
        if not self.no_tray:
            self._tray = JarvisTray(
                url=self._url,
                on_quit=self._request_quit,
                on_toggle_voice=self._toggle_voice,
                on_reload=self._reload_config,
                name=self.config.name,
            )
            self._tray.start()
            self._tray.notify(
                self.config.name,
                f"Запущен. Чат: {self._url}",
            )
        if self.config.server.open_browser_on_start:
            plat.open_url(self._url)

        # 6. Ожидаем сигнала на выход
        try:
            await self._stop_event.wait()
        finally:
            log.info("Завершаюсь…")
            server.should_exit = True
            for t in bg_tasks:
                t.cancel()
            await asyncio.gather(*bg_tasks, return_exceptions=True)
            await self.event_bus.emit(Event(type=EventType.SHUTDOWN))
            if self._tray is not None:
                self._tray.stop()


def _install_signal_handlers(app: JarvisApp) -> None:
    def _handler(sig: int, frame: object) -> None:
        log.info(f"Получен сигнал {sig}, завершаюсь")
        app._request_quit()

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(s, _handler)
        except (ValueError, OSError):
            # Не главный поток или сигнал недоступен на платформе
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Desktop App")
    parser.add_argument("--no-voice", action="store_true", help="Не запускать голос")
    parser.add_argument(
        "--no-tray", action="store_true",
        help="Не запускать иконку в трее (только web-UI)",
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Запустить мастер первоначальной настройки",
    )
    parser.add_argument("--open", action="store_true", help="Открыть UI после старта")
    parser.add_argument("--port", type=int, help="Порт HTTP-сервера")
    parser.add_argument("--host", default=None, help="Хост HTTP-сервера")
    args = parser.parse_args()

    ensure_dirs()

    # Первый запуск или явный --setup
    if args.setup or is_first_run():
        from jarvis.core.setup_wizard import run_wizard

        run_wizard()
        if args.setup:
            return

    config = load_config()
    if args.no_voice:
        config.voice_enabled = False
    if args.open:
        config.server.open_browser_on_start = True
    if args.port:
        config.server.port = args.port
    if args.host:
        config.server.host = args.host

    # Применить автозапуск, если включено
    if config.autostart and not autostart.is_enabled():
        log.info(autostart.enable())

    app = JarvisApp(config, no_tray=args.no_tray)
    _install_signal_handlers(app)

    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        pass
    log.info("Jarvis остановлен")


if __name__ == "__main__":
    main()
