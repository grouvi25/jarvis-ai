"""Скилл погоды."""

from __future__ import annotations

from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils.logger import log


class WeatherSkill(Skill):
    """Показывает текущую погоду и прогноз через wttr.in API."""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return (
            "Узнать погоду в городе. Показывает температуру, осадки, ветер. "
            "Используй когда пользователь спрашивает про погоду, "
            "температуру, нужна ли куртка, зонт и т.д."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": (
                        "Город на английском (например Moscow, "
                        "Saint+Petersburg, Novosibirsk)"
                    ),
                },
            },
            "required": ["city"],
        }

    async def execute(self, **kwargs: Any) -> str:
        city = kwargs.get("city", "Moscow")

        try:
            import aiohttp

            url = f"https://wttr.in/{city}?format=j1&lang=ru"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return f"Не удалось получить погоду для {city}"
                    data = await resp.json()

            current = data.get("current_condition", [{}])[0]
            temp = current.get("temp_C", "?")
            feels = current.get("FeelsLikeC", "?")
            desc_list = current.get("lang_ru", [{}])
            desc = desc_list[0].get("value", "") if desc_list else ""
            humidity = current.get("humidity", "?")
            wind = current.get("windspeedKmph", "?")
            wind_dir = current.get("winddir16Point", "")

            area = data.get("nearest_area", [{}])[0]
            area_name = area.get("areaName", [{}])[0].get("value", city)

            result = (
                f"Погода в {area_name}:\n"
                f"  Температура: {temp}°C (ощущается {feels}°C)\n"
                f"  {desc}\n"
                f"  Влажность: {humidity}%\n"
                f"  Ветер: {wind} км/ч {wind_dir}"
            )

            forecast = data.get("weather", [])
            if forecast:
                today = forecast[0]
                max_t = today.get("maxtempC", "?")
                min_t = today.get("mintempC", "?")
                result += f"\n  Сегодня: {min_t}..{max_t}°C"

            return result

        except Exception as e:
            log.error(f"Ошибка получения погоды: {e}")
            return f"Ошибка получения погоды: {e}"
