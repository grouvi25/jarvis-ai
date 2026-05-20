"""J.A.R.V.I.S. — точка входа."""

from __future__ import annotations

import asyncio
import signal
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from jarvis.core.brain import Brain
from jarvis.core.config import load_config
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.skills.browser import BrowserSkill
from jarvis.skills.desktop import DesktopControlSkill
from jarvis.skills.internet import InternetReconnectSkill
from jarvis.skills.messenger import TelegramMessengerSkill
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
  Just A Rather Very Intelligent System  v0.1.0
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


def main() -> None:
    """Главная точка входа."""
    console.print(Panel(Text(BANNER, style="bold cyan"), border_style="blue"))

    config = load_config()
    event_bus = EventBus()

    # Инициализация мозга
    brain = Brain(config, event_bus)
    speaker = Speaker(config.tts, event_bus)

    # Регистрация скиллов
    messenger = TelegramMessengerSkill(config)
    browser = BrowserSkill(config)
    desktop = DesktopControlSkill()
    internet = InternetReconnectSkill(config.internet, event_bus)

    brain.register_skill(messenger)
    brain.register_skill(browser)
    brain.register_skill(desktop)
    brain.register_skill(internet)

    log.info(f"Язык: {config.language}")
    log.info(f"LLM: {config.llm.provider} / {config.llm.model}")
    log.info(f"STT: {config.stt.engine} ({config.stt.model})")
    log.info(f"TTS: {config.tts.engine}")

    # Определяем режим
    mode = "text"
    if "--voice" in sys.argv:
        mode = "voice"
    elif "--text" in sys.argv:
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
        if config.internet.enabled:
            tasks.append(asyncio.create_task(internet.start_monitoring()))

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
        await browser.close()

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
