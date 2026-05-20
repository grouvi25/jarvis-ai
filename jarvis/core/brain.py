"""Мозг J.A.R.V.I.S. — интеграция с LLM."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from jarvis.core.config import JarvisConfig
from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.core.memory import Memory
from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class Brain:
    """LLM-мозг Джарвиса. Понимает запросы и вызывает скиллы."""

    def __init__(
        self, config: JarvisConfig, event_bus: EventBus, memory: Memory | None = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.memory = memory or Memory()
        self.conversation_history: list[dict[str, Any]] = self.memory.get_history()
        self.skills: dict[str, Skill] = {}
        self.max_history = 50

        llm = config.llm
        self.client = AsyncOpenAI(
            base_url=llm.base_url,
            api_key=llm.api_key or "not-needed",
        )
        self.model = llm.model

        event_bus.on(EventType.SPEECH_RECOGNIZED, self._on_speech)

    def register_skill(self, skill: Skill) -> None:
        """Зарегистрировать скилл."""
        self.skills[skill.name] = skill
        log.info(f"Скилл зарегистрирован: [bold]{skill.name}[/bold] — {skill.description}")

    def _build_tools(self) -> list[dict[str, Any]]:
        """Сформировать список tools для OpenAI API из зарегистрированных скиллов."""
        tools = []
        for skill in self.skills.values():
            tools.append({
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.parameters,
                },
            })
        return tools

    def _build_system_prompt(self) -> str:
        """Сформировать системный промпт."""
        base = self.config.llm.system_prompt
        skills_info = "\n".join(
            f"- {s.name}: {s.description}" for s in self.skills.values()
        )
        return f"{base}\n\nДоступные инструменты:\n{skills_info}"

    async def think(self, user_message: str) -> str:
        """Обработать сообщение пользователя через LLM."""
        self.conversation_history.append({"role": "user", "content": user_message})

        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._build_system_prompt()},
            *self.conversation_history,
        ]

        tools = self._build_tools()
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.config.llm.temperature,
            "max_tokens": self.config.llm.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            await self.event_bus.emit(Event(
                type=EventType.LLM_THINKING,
                data={"message": user_message},
                source="brain",
            ))

            response = await self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            # Обработка вызовов инструментов
            if message.tool_calls:
                # Добавляем ответ ассистента с tool_calls в историю
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
                        func_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        func_args = {}

                    log.info(f"Вызов скилла: [bold cyan]{func_name}[/bold cyan]({func_args})")

                    skill = self.skills.get(func_name)
                    if skill:
                        result = await skill.execute(**func_args)
                        log.info(f"Результат скилла {func_name}: {result}")
                    else:
                        result = f"Скилл '{func_name}' не найден"

                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    })

                # Получаем финальный ответ после выполнения инструментов
                messages = [
                    {"role": "system", "content": self._build_system_prompt()},
                    *self.conversation_history,
                ]
                follow_up = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                )
                reply = follow_up.choices[0].message.content or ""
            else:
                reply = message.content or ""

            self.conversation_history.append({"role": "assistant", "content": reply})
            self.memory.save_history(self.conversation_history)

            await self.event_bus.emit(Event(
                type=EventType.LLM_RESPONSE,
                data={"response": reply, "user_message": user_message},
                source="brain",
            ))

            return reply

        except Exception as e:
            error_msg = f"Ошибка LLM: {e}"
            log.error(error_msg)
            await self.event_bus.emit(Event(
                type=EventType.ERROR,
                data={"error": error_msg},
                source="brain",
            ))
            return f"Прошу прощения, {self.config.master_name}, произошла ошибка: {e}"

    async def _on_speech(self, event: Event) -> None:
        """Обработчик распознанной речи."""
        text = event.data.get("text", "")
        if not text:
            return
        log.info(f"[bold green]Вы:[/bold green] {text}")
        response = await self.think(text)
        log.info(f"[bold blue]{self.config.name}:[/bold blue] {response}")
