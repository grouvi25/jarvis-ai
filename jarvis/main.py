"""J.A.R.V.I.S. — текстовая/голосовая CLI-точка входа.

Для запуска полноценного desktop-приложения (трей + web-UI) используй `jarvis-app`.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from jarvis.app import register_all_skills
from jarvis.core.brain import Brain
from jarvis.core.config import is_first_run, load_config
from jarvis.core.event_bus import Event, EventBus, EventType
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


async def run_text_mode(brain: Brain, speaker: Speaker, config) -> None:
    console.print(
        "\n[dim]Текстовый режим. Введи сообщение или 'выход' / Ctrl-D для завершения.[/dim]\n"
    )
    loop = asyncio.get_event_loop()
    while True:
        try:
            user_input = (
                await loop.run_in_executor(None, lambda: input("Ты > "))
            ).strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() in ("выход", "exit", "quit", "q"):
            break

        response = await brain.think(user_input)
        console.print(f"\n[bold cyan]{config.name}:[/bold cyan] {response}\n")
        if config.voice_enabled:
            await speaker.speak(response)


async def run_voice_mode(
    brain: Brain, speaker: Speaker, event_bus: EventBus, config,
) -> None:
    from jarvis.voice.listener import SpeechListener
    from jarvis.voice.wake_word import WakeWordDetector

    listener = SpeechListener(config.stt, event_bus)
    wake = WakeWordDetector(config, event_bus)

    async def on_wake(event: Event) -> None:
        text = (event.data.get("remaining_text") or "").strip()
        if not text:
            console.print(f"\n[bold green]{config.name} слушает...[/bold green]")
            return
        response = await brain.think(text)
        console.print(f"\n[bold cyan]{config.name}:[/bold cyan] {response}\n")
        if config.voice_enabled:
            await speaker.speak(response)

    event_bus.on(EventType.WAKE_WORD_DETECTED, on_wake)

    tasks = [
        asyncio.create_task(event_bus.process_events()),
        asyncio.create_task(listener.listen_continuous()),
        asyncio.create_task(wake.listen()),
    ]
    console.print(
        f"\n[bold green]Голосовой режим активен.[/bold green] "
        f"Скажи '{config.wake_words[0]}' для активации.\n"
        f"[dim]Ctrl+C для выхода[/dim]\n"
    )
    try:
        await asyncio.gather(*tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        listener.stop()
        wake.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. CLI")
    parser.add_argument("--text", action="store_true", help="Текстовый режим")
    parser.add_argument("--voice", action="store_true", help="Голосовой режим")
    parser.add_argument("--setup", action="store_true", help="Запустить мастер настройки")
    args = parser.parse_args()

    if args.setup or is_first_run():
        from jarvis.core.setup_wizard import run_wizard

        run_wizard()
        if args.setup:
            return

    console.print(Panel(Text(BANNER, style="bold cyan"), border_style="blue"))

    config = load_config()
    event_bus = EventBus()
    brain = Brain(config, event_bus)
    speaker = Speaker(config.tts, event_bus)
    register_all_skills(brain, config, event_bus)

    log.info(f"LLM: {config.llm.provider} / {config.llm.model}")

    if args.voice:
        mode = "voice"
    elif args.text:
        mode = "text"
    else:
        try:
            import sounddevice as sd  # type: ignore[import-not-found]

            devices = sd.query_devices()
            has_input = any(
                d["max_input_channels"] > 0 for d in devices if isinstance(d, dict)
            )
            mode = "voice" if has_input else "text"
        except Exception:
            mode = "text"

    async def run() -> None:
        bg: list[asyncio.Task] = []
        from jarvis.skills.internet import InternetReconnectSkill

        for skill in brain.skills.values():
            if isinstance(skill, InternetReconnectSkill) and config.internet.enabled:
                bg.append(asyncio.create_task(skill.start_monitoring()))

        if mode == "voice":
            await run_voice_mode(brain, speaker, event_bus, config)
        else:
            bg.append(asyncio.create_task(event_bus.process_events()))
            await run_text_mode(brain, speaker, config)

        await event_bus.emit(Event(type=EventType.SHUTDOWN))
        for t in bg:
            t.cancel()

    def handle_signal(sig, frame) -> None:
        console.print(
            f"\n[yellow]{config.name}: До свидания, {config.master_name}![/yellow]"
        )
        sys.exit(0)

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(s, handle_signal)
        except (ValueError, OSError):
            pass

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print(
            f"\n[yellow]{config.name}: До свидания, {config.master_name}![/yellow]"
        )


if __name__ == "__main__":
    main()
