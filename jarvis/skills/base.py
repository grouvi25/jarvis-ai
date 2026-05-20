"""Базовый класс скиллов J.A.R.V.I.S."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Skill(ABC):
    """Базовый скилл — единица функциональности Джарвиса."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя скилла (для вызова через LLM)."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Описание скилла на русском (для системного промпта LLM)."""

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema параметров скилла (для OpenAI function calling)."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Выполнить скилл. Возвращает текстовый результат."""
