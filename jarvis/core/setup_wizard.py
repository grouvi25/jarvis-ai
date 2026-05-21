"""Мастер первоначальной настройки J.A.R.V.I.S. (интерактивный CLI)."""

from __future__ import annotations

import getpass
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from jarvis.core.config import JarvisConfig, load_config, save_config
from jarvis.utils import autostart
from jarvis.utils.paths import ensure_dirs


WELCOME = """
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝

       Just A Rather Very Intelligent System
"""


PROVIDERS = {
    "1": {
        "label": "OmniRoute (локально, рекомендуется — бесплатные модели)",
        "provider": "omniroute",
        "base_url": "http://localhost:20128/v1",
        "model": "gpt-4o-mini",
        "needs_key": False,
        "hint": "Установить: `npm i -g omniroute && omniroute`",
    },
    "2": {
        "label": "OpenAI (api.openai.com)",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "needs_key": True,
    },
    "3": {
        "label": "Groq (быстро + бесплатно)",
        "provider": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "needs_key": True,
    },
    "4": {
        "label": "Ollama (локальная модель)",
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "needs_key": False,
        "hint": "Установить с https://ollama.com и `ollama pull llama3.2`",
    },
    "5": {
        "label": "Другой OpenAI-совместимый",
        "provider": "custom",
        "base_url": "",
        "model": "",
        "needs_key": True,
    },
}


def _print_banner(console: Console) -> None:
    console.print(Panel(Text(WELCOME, style="bold cyan"), border_style="blue"))


def run_wizard() -> JarvisConfig:
    """Интерактивная настройка. Возвращает сохранённый конфиг."""
    ensure_dirs()
    console = Console()
    _print_banner(console)
    console.print("\n[bold]Привет! Давай настроим Джарвиса.[/bold]\n")

    # Загружаем текущий (или дефолтный) конфиг как стартовую точку
    config = load_config()

    config.master_name = Prompt.ask(
        "Как мне к тебе обращаться?", default=config.master_name or "сэр",
    )
    config.name = Prompt.ask(
        "Как зовут ассистента?", default=config.name or "Джарвис",
    )

    # Выбор LLM
    console.print("\n[bold]Выбери LLM-провайдер:[/bold]")
    for key, p in PROVIDERS.items():
        console.print(f"  [cyan]{key}.[/cyan] {p['label']}")
    pick = Prompt.ask("Номер", choices=list(PROVIDERS.keys()), default="1")
    pchoice = PROVIDERS[pick]
    config.llm.provider = pchoice["provider"]

    base_url = Prompt.ask(
        "Base URL", default=pchoice["base_url"] or config.llm.base_url,
    )
    config.llm.base_url = base_url

    model = Prompt.ask(
        "Модель", default=pchoice["model"] or config.llm.model,
    )
    config.llm.model = model

    if pchoice["needs_key"]:
        api_key = getpass.getpass("API key (вводится скрыто): ").strip()
        if api_key:
            config.llm.api_key = api_key

    if "hint" in pchoice:
        console.print(f"[dim]Подсказка: {pchoice['hint']}[/dim]")

    # Голос
    config.voice_enabled = Confirm.ask(
        "Включить голос (TTS-ответы)?", default=config.voice_enabled,
    )

    # Автозапуск
    config.autostart = Confirm.ask(
        "Запускать Джарвиса при включении системы?", default=config.autostart,
    )

    # Сохранение
    path = save_config(config)
    console.print(f"\n[green]✓[/green] Конфиг сохранён: [cyan]{path}[/cyan]")

    if config.autostart:
        console.print("[green]✓[/green] " + autostart.enable())

    console.print(
        "\n[bold]Готово![/bold] Запусти десктоп-приложение:\n"
        "  [cyan]jarvis-app[/cyan]            — фоновое приложение с треем\n"
        "  [cyan]jarvis --text[/cyan]         — простой текстовый чат в терминале\n"
        f"  Или открой UI: [cyan]http://{config.server.host}:{config.server.port}[/cyan]\n"
    )

    return config


def main() -> None:
    try:
        run_wizard()
    except (KeyboardInterrupt, EOFError):
        print("\nОтменено")
        sys.exit(1)


if __name__ == "__main__":
    main()
