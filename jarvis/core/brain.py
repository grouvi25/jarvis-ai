"""Мозг J.A.R.V.I.S. — интеграция с LLM + вызов скиллов + персистентная память."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from jarvis.core.config import JarvisConfig
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.core.memory import ConversationStore, MemoryStore
from jarvis.skills.base import Skill
from jarvis.utils import platform as plat
from jarvis.utils.logger import log


class Brain:
    """LLM-мозг Джарвиса. Понимает запросы, вызывает скиллы, помнит контекст."""

    MAX_TOOL_LOOPS = 4  # сколько раундов tool_calls подряд разрешено в одном ходу

    def __init__(self, config: JarvisConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self.skills: dict[str, Skill] = {}
        self.max_history = 30

        self.memory = MemoryStore()
        self._conv = ConversationStore()
        self.conversation_history: list[dict[str, Any]] = self._conv.load()

        llm = config.llm
        self.client = AsyncOpenAI(
            base_url=llm.base_url or None,
            api_key=llm.api_key or "not-needed",
        )
        self.model = llm.model

    # ---------- skills ----------

    def register_skill(self, skill: Skill) -> None:
        self.skills[skill.name] = skill
        log.info(f"Скилл: [bold]{skill.name}[/bold] — {skill.description[:80]}")

    def _build_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.parameters,
                },
            }
            for skill in self.skills.values()
        ]

    def _build_system_prompt(self) -> str:
        base = self.config.llm.system_prompt or (
            "Ты — J.A.R.V.I.S., AI-ассистент пользователя. "
            "Отвечай по-русски, кратко, по существу. "
            "Когда тебя просят что-то сделать на компьютере — используй инструменты, не объясняй."
        )
        memory_block = self.memory.as_prompt_block()
        skills_info = "\n".join(
            f"- {s.name}: {s.description}" for s in self.skills.values()
        )
        parts = [base, self._os_context()]
        if memory_block:
            parts.append(memory_block)
        if skills_info:
            parts.append(f"Доступные инструменты:\n{skills_info}")
        return "\n\n".join(parts)

    def _os_context(self) -> str:
        """Дать LLM знать, какую ОС/shell использовать при run_command."""
        if plat.is_windows():
            return (
                "Окружение: Windows. shell — PowerShell. "
                "Используй PowerShell/cmd команды (не bash/Linux). "
                "Громкость: nircmd.exe или [Audio]::SetVolume. "
                "Менеджер пакетов: winget. "
                "Пути с обратными слешами. "
                "НИКОГДА не используй amixer, apt, xdg-open, killall, ls — это команды Linux."
            )
        if plat.is_macos():
            return (
                "Окружение: macOS. shell — zsh/bash. "
                "Громкость: osascript. Менеджер пакетов: brew. "
                "Открыть файл/URL: open."
            )
        return (
            "Окружение: Linux. shell — bash. "
            "Громкость: amixer/pactl. Открыть файл/URL: xdg-open. "
            "Менеджер пакетов: apt/dnf/pacman."
        )

    # ---------- main think loop ----------

    async def think(self, user_message: str) -> str:
        """Обработать сообщение пользователя через LLM с поддержкой multi-step tools."""
        self.conversation_history.append({"role": "user", "content": user_message})
        self._trim_history()

        await self.event_bus.emit(Event(
            type=EventType.LLM_THINKING,
            data={"message": user_message},
            source="brain",
        ))

        try:
            reply = await self._chat_loop()
        except Exception as e:
            log.exception("Ошибка LLM")
            await self.event_bus.emit(Event(
                type=EventType.ERROR,
                data={"error": str(e)},
                source="brain",
            ))
            reply = f"Прошу прощения, {self.config.master_name}, произошла ошибка: {e}"

        self.conversation_history.append({"role": "assistant", "content": reply})
        self._trim_history()
        self._conv.save(self.conversation_history)

        await self.event_bus.emit(Event(
            type=EventType.LLM_RESPONSE,
            data={"response": reply, "user_message": user_message},
            source="brain",
        ))
        return reply

    async def _chat_loop(self) -> str:
        """Цикл: LLM → опц. tool_calls → LLM → … до финального ответа."""
        tools = self._build_tools()
        for _ in range(self.MAX_TOOL_LOOPS):
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": self._build_system_prompt()},
                *self.conversation_history,
            ]
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": self.config.llm.temperature,
                "max_tokens": self.config.llm.max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            if not message.tool_calls:
                return message.content or ""

            # Сохраняем шаг с tool_calls
            self.conversation_history.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    func_args = {}

                log.info(f"→ tool [bold cyan]{func_name}[/bold cyan]({func_args})")
                await self.event_bus.emit(Event(
                    type=EventType.SKILL_EXECUTE,
                    data={"skill": func_name, "args": func_args},
                    source="brain",
                ))

                skill = self.skills.get(func_name)
                if skill:
                    try:
                        result = await skill.execute(**func_args)
                    except Exception as e:
                        result = f"Ошибка скилла {func_name}: {e}"
                        log.error(result)
                else:
                    result = f"Скилл '{func_name}' не найден"

                log.info(f"  ← {str(result)[:200]}")
                await self.event_bus.emit(Event(
                    type=EventType.SKILL_RESULT,
                    data={"skill": func_name, "result": result},
                    source="brain",
                ))

                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                })

        # Если зациклились на tool_calls — возвращаем что есть
        return (
            "Извини, " + self.config.master_name +
            ", застрял в цикле инструментов. Попробуй переформулировать запрос."
        )

    # ---------- history ----------

    def _trim_history(self) -> None:
        """Урезаем историю, но не рвём цепочки tool_calls."""
        if len(self.conversation_history) <= self.max_history:
            return
        # Удаляем самые старые сообщения, пока не помещаемся
        excess = len(self.conversation_history) - self.max_history
        # Не отрезаем посередине tool_call → tool ответа: ищем безопасную точку
        cut = excess
        while cut < len(self.conversation_history):
            entry = self.conversation_history[cut]
            if entry.get("role") not in ("tool",) and not entry.get("tool_calls"):
                break
            cut += 1
        self.conversation_history = self.conversation_history[cut:]

    def reset_history(self) -> None:
        self.conversation_history = []
        self._conv.clear()
