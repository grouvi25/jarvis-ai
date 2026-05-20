"""Скилл управления браузером."""

from __future__ import annotations

from typing import Any

from jarvis.core.config import JarvisConfig
from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class BrowserSkill(Skill):
    """Управляет браузером — открывает сайты, кликает, заполняет формы."""

    def __init__(self, config: JarvisConfig) -> None:
        self._config = config
        self._browser = None
        self._page = None

    @property
    def name(self) -> str:
        return "browser_action"

    @property
    def description(self) -> str:
        return (
            "Управление браузером: открыть сайт, найти что-то в Google, "
            "кликнуть на элемент, заполнить форму, сделать скриншот страницы. "
            "Используй когда пользователь просит открыть сайт, погуглить, "
            "зайти на страницу, авторизоваться где-то."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open_url", "search", "click", "type_text", "screenshot", "get_text"],
                    "description": "Действие: open_url (открыть URL), search (поиск в Google), "
                    "click (кликнуть на элемент), type_text (ввести текст), "
                    "screenshot (скриншот), get_text (прочитать текст страницы)",
                },
                "url": {
                    "type": "string",
                    "description": "URL для открытия (для action=open_url)",
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Поисковый запрос (для action=search) "
                        "или CSS-селектор (для click/type_text)"
                    ),
                },
                "text": {
                    "type": "string",
                    "description": "Текст для ввода (для action=type_text)",
                },
            },
            "required": ["action"],
        }

    async def _ensure_browser(self) -> None:
        """Запустить браузер если ещё не запущен."""
        if self._page is not None:
            return

        try:
            from playwright.async_api import async_playwright

            pw = await async_playwright().start()
            browser_type = getattr(pw, self._config.browser.browser_type)
            self._browser = await browser_type.launch(
                headless=self._config.browser.headless,
            )
            self._page = await self._browser.new_page()
            log.info("Браузер запущен")
        except Exception as e:
            log.error(f"Ошибка запуска браузера: {e}")
            raise

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")

        if not self._config.browser.enabled:
            return "Браузер отключён в настройках"

        await self._ensure_browser()
        assert self._page is not None

        try:
            if action == "open_url":
                url = kwargs.get("url", "")
                if not url:
                    return "Не указан URL"
                await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                title = await self._page.title()
                return f"Открыта страница: {title} ({url})"

            elif action == "search":
                query = kwargs.get("query", "")
                if not query:
                    return "Не указан поисковый запрос"
                url = f"https://www.google.com/search?q={query}"
                await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                return f"Поиск Google: {query}"

            elif action == "click":
                selector = kwargs.get("query", "")
                if not selector:
                    return "Не указан селектор элемента"
                await self._page.click(selector, timeout=5000)
                return f"Клик по элементу: {selector}"

            elif action == "type_text":
                selector = kwargs.get("query", "")
                text = kwargs.get("text", "")
                if not selector or not text:
                    return "Не указан селектор или текст"
                await self._page.fill(selector, text)
                return f"Текст введён в {selector}"

            elif action == "screenshot":
                path = "/tmp/jarvis_screenshot.png"
                await self._page.screenshot(path=path, full_page=True)
                return f"Скриншот сохранён: {path}"

            elif action == "get_text":
                text = await self._page.inner_text("body")
                # Ограничиваем длину
                if len(text) > 2000:
                    text = text[:2000] + "..."
                return f"Текст страницы:\n{text}"

            else:
                return f"Неизвестное действие: {action}"

        except Exception as e:
            return f"Ошибка браузера: {e}"

    async def close(self) -> None:
        """Закрыть браузер."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
