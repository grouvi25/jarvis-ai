"""Веб-поиск через DuckDuckGo Instant Answer / HTML — без ключей."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import aiohttp

from jarvis.skills.base import Skill


class WebSearchSkill(Skill):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Поиск в интернете через DuckDuckGo (без ключей). "
            "Возвращает короткие сниппеты результатов. "
            "Используй когда нужно что-то узнать из сети — погода, новости, факты, "
            "и пользователь не просит явно открыть браузер."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> str:
        query = (kwargs.get("query") or "").strip()
        if not query:
            return "Не указан запрос"

        url = (
            "https://api.duckduckgo.com/?format=json&no_html=1&no_redirect=1&q="
            + quote_plus(query)
        )
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
            ) as session:
                async with session.get(url, headers={"User-Agent": "Jarvis/0.2"}) as resp:
                    data = await resp.json(content_type=None)
        except Exception as e:
            return f"Ошибка поиска: {e}"

        # Сборка ответа
        parts: list[str] = []
        if data.get("AbstractText"):
            src = data.get("AbstractSource") or ""
            parts.append(f"{data['AbstractText']} (источник: {src})")
        for topic in (data.get("RelatedTopics") or [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(f"- {topic['Text']}")
        if data.get("Answer"):
            parts.insert(0, f"Ответ: {data['Answer']}")
        if not parts:
            return f"Ничего полезного по запросу '{query}'. Попробуй через браузер."
        return "\n".join(parts)
