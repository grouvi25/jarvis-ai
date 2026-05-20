"""J.A.R.V.I.S. — точка входа."""

from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from jarvis.core.brain import Brain
from jarvis.core.config import load_config
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.core.memory import Memory
from jarvis.skills.browser import BrowserSkill
from jarvis.skills.contacts import ContactsSkill
from jarvis.skills.desktop import DesktopControlSkill
from jarvis.skills.file_manager import FileManagerSkill
from jarvis.skills.internet import InternetReconnectSkill
from jarvis.skills.media import MediaControlSkill
from jarvis.skills.messenger import TelegramMessengerSkill
from jarvis.skills.notes import NotesSkill
from jarvis.skills.system_info import SystemInfoSkill
from jarvis.skills.timer import TimerSkill
from jarvis.skills.weather import WeatherSkill
from jarvis.utils.logger import log
from jarvis.voice.speaker import Speaker

console = Console()

BANNER = r"""
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
  Just A Rather Very Intelligent System  v0.2.0
"""


async def run_text_mode(brain: Brain, speaker: Speaker, config: object) -> None:
    """Текстовый режим — ввод через консоль (для работы без микрофона)."""
    console.print(
        "\n[dim]Текстовый режим. Введите сообщение или 'выход' для завершения.[/dim]\n"
    )

    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = await loop.run_in_executor(None, lambda: input("Вы > ").strip())
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("выход", "exit", "quit", "q"):
            break

        response = await brain.think(user_input)
        console.print(f"\n[bold cyan]{config.name}:[/bold cyan] {response}\n")
        await speaker.speak(response)


async def run_voice_mode(
    brain: Brain,
    speaker: Speaker,
    event_bus: EventBus,
    config: object,
) -> None:
    """Голосовой режим — wake word + микрофон."""
    from jarvis.voice.listener import SpeechListener
    from jarvis.voice.wake_word import WakeWordDetector

    listener = SpeechListener(config.stt, event_bus)
    wake_detector = WakeWordDetector(config, event_bus)

    # Когда wake word обнаружен — говорим "Слушаю"
    async def on_wake(event: Event) -> None:
        remaining = event.data.get("remaining_text", "")
        if remaining:
            # Уже есть текст после wake word — обрабатываем сразу
            response = await brain.think(remaining)
            console.print(f"\n[bold cyan]{config.name}:[/bold cyan] {response}\n")
            await speaker.speak(response)
        else:
            console.print(f"\n[bold green]{config.name} слушает...[/bold green]")

    event_bus.on(EventType.WAKE_WORD_DETECTED, on_wake)

    # Обрабатываем LLM-ответ на распознанную речь
    async def on_llm_response(event: Event) -> None:
        response = event.data.get("response", "")
        if response:
            console.print(f"\n[bold cyan]{config.name}:[/bold cyan] {response}\n")

    event_bus.on(EventType.LLM_RESPONSE, on_llm_response)

    # Запускаем всё параллельно
    tasks = [
        asyncio.create_task(event_bus.process_events()),
        asyncio.create_task(listener.listen_continuous()),
        asyncio.create_task(wake_detector.listen()),
    ]

    console.print(
        f"\n[bold green]Голосовой режим активен.[/bold green] "
        f"Скажите '{config.wake_words[0]}' для активации.\n"
        f"[dim]Ctrl+C для выхода[/dim]\n"
    )

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        listener.stop()
        wake_detector.stop()


def _load_plugins(
    brain: Brain, config: object, event_bus: EventBus, memory: object
) -> None:
    """Загрузить пользовательские плагины из ~/.jarvis/plugins/."""
    import importlib.util

    plugins_dir = Path.home() / ".jarvis" / "plugins"
    if not plugins_dir.exists():
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return

    for plugin_file in sorted(plugins_dir.glob("*.py")):
        try:
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem, plugin_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore[union-attr]
                if hasattr(module, "register"):
                    module.register(brain, config, event_bus, memory)
                    log.info(f"Плагин загружен: {plugin_file.name}")
        except Exception as e:
            log.error(f"Ошибка загрузки плагина {plugin_file.name}: {e}")


def _parse_args() -> object:
    """Разобрать аргументы командной строки."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="J.A.R.V.I.S. — персональный AI-ассистент",
    )
    parser.add_argument(
        "--text", action="store_true",
        help="Текстовый режим (без микрофона)",
    )
    parser.add_argument(
        "--voice", action="store_true",
        help="Голосовой режим (нужен микрофон)",
    )
    parser.add_argument(
        "--clear-history", action="store_true",
        help="Очистить историю разговоров",
    )
    parser.add_argument(
        "--version", action="version", version="J.A.R.V.I.S. v0.2.0",
    )
    return parser.parse_args()


def main() -> None:
    """Главная точка входа."""
    args = _parse_args()
    console.print(Panel(Text(BANNER, style="bold cyan"), border_style="blue"))

    config = load_config()
    event_bus = EventBus()

    # Инициализация памяти и мозга
    memory = Memory()
    brain = Brain(config, event_bus, memory)
    speaker = Speaker(config.tts, event_bus)

    # Регистрация скиллов
    skills = [
        TelegramMessengerSkill(config),
        BrowserSkill(config),
        DesktopControlSkill(),
        InternetReconnectSkill(config.internet, event_bus),
        WeatherSkill(),
        TimerSkill(event_bus),
        NotesSkill(),
        ContactsSkill(memory),
        SystemInfoSkill(),
        FileManagerSkill(),
        MediaControlSkill(),
    ]

    for skill in skills:
        brain.register_skill(skill)

    # Загрузка плагинов из ~/.jarvis/plugins/
    _load_plugins(brain, config, event_bus, memory)

    # Очистка истории если запрошено
    if args.clear_history:
        memory.clear_history()
        console.print("[yellow]История разговоров очищена[/yellow]")

    log.info(f"Язык: {config.language}")
    log.info(f"LLM: {config.llm.provider} / {config.llm.model}")
    log.info(f"STT: {config.stt.engine} ({config.stt.model})")
    log.info(f"TTS: {config.tts.engine}")
    log.info(f"Скиллов: {len(brain.skills)}")

    # Определяем режим
    mode = "text"
    if args.voice:
        mode = "voice"
    elif args.text:
        mode = "text"
    else:
        # Пробуем определить автоматически
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            has_input = any(d["max_input_channels"] > 0 for d in devices if isinstance(d, dict))
            if has_input:
                mode = "voice"
                log.info("Обнаружен микрофон, запускаю голосовой режим")
            else:
                log.info("Микрофон не найден, запускаю текстовый режим")
        except Exception:
            log.info("sounddevice недоступен, запускаю текстовый режим")

    async def run() -> None:
        tasks: list[asyncio.Task[None]] = []

        # Фоновый мониторинг интернета
        internet_skill = brain.skills.get("reconnect_internet")
        if config.internet.enabled and internet_skill:
            tasks.append(asyncio.create_task(internet_skill.start_monitoring()))

        if mode == "voice":
            await run_voice_mode(brain, speaker, event_bus, config)
        else:
            # В текстовом режиме тоже запускаем event bus
            tasks.append(asyncio.create_task(event_bus.process_events()))
            await run_text_mode(brain, speaker, config)

        # Завершение
        await event_bus.emit(Event(type=EventType.SHUTDOWN))
        for task in tasks:
            task.cancel()

    def handle_signal(sig: int, frame: object) -> None:
        console.print(f"\n[yellow]{config.name}: До свидания, {config.master_name}![/yellow]")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print(f"\n[yellow]{config.name}: До свидания, {config.master_name}![/yellow]")


if __name__ == "__main__":
    main()
