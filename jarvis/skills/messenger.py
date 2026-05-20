"""Скилл отправки сообщений через Telegram."""

from __future__ import annotations

from typing import Any

from jarvis.core.config import JarvisConfig
from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class TelegramMessengerSkill(Skill):
    """Отправляет сообщения через Telegram бота."""

    def __init__(self, config: JarvisConfig) -> None:
        self._config = config
        self._bot = None

    @property
    def name(self) -> str:
        return "send_telegram_message"

    @property
    def description(self) -> str:
        return (
            "Отправить сообщение в Telegram. Используй когда пользователь просит "
            "написать кому-то сообщение, отправить текст, связаться с кем-то."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": (
                        "ID чата или username получателя в Telegram "
                        "(например @username или числовой ID)"
                    ),
                },
                "message": {
                    "type": "string",
                    "description": "Текст сообщения для отправки",
                },
            },
            "required": ["chat_id", "message"],
        }

    async def _get_bot(self) -> Any:
        if self._bot is not None:
            return self._bot

        from telegram import Bot

        token = self._config.telegram.bot_token
        if not token:
            raise ValueError(
                "Telegram bot token не настроен. "
                "Добавь bot_token в config/local.yaml → telegram → bot_token"
            )
        self._bot = Bot(token=token)
        return self._bot

    async def execute(self, **kwargs: Any) -> str:
        chat_id = kwargs.get("chat_id", "")
        message = kwargs.get("message", "")

        if not chat_id or not message:
            return "Ошибка: не указан chat_id или message"

        if not self._config.telegram.enabled:
            return (
                "Telegram не включён. Включите в config/local.yaml: "
                "telegram.enabled: true и укажите bot_token"
            )

        try:
            bot = await self._get_bot()
            await bot.send_message(chat_id=chat_id, text=message)
            log.info(f"Сообщение отправлено в Telegram: {chat_id}")
            return f"Сообщение успешно отправлено в чат {chat_id}"
        except Exception as e:
            error = f"Ошибка отправки в Telegram: {e}"
            log.error(error)
            return error
