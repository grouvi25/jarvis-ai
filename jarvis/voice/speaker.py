"""Синтез речи (TTS) для J.A.R.V.I.S."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.utils.logger import log

if TYPE_CHECKING:
    from jarvis.core.config import TTSConfig


class Speaker:
    """Озвучивает ответы Джарвиса."""

    def __init__(self, config: TTSConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self._xtts_model = None
        self._is_speaking = False

        event_bus.on(EventType.LLM_RESPONSE, self._on_response)

    async def speak(self, text: str) -> None:
        """Озвучить текст."""
        if not text.strip():
            return

        self._is_speaking = True
        await self.event_bus.emit(Event(
            type=EventType.SPEECH_STARTED,
            data={"text": text},
            source="speaker",
        ))

        try:
            if self.config.engine == "edge-tts":
                await self._speak_edge(text)
            elif self.config.engine == "xtts":
                await self._speak_xtts(text)
            else:
                log.warning(f"Неизвестный TTS движок: {self.config.engine}")
        except Exception as e:
            log.error(f"Ошибка TTS: {e}")
        finally:
            self._is_speaking = False
            await self.event_bus.emit(Event(
                type=EventType.SPEECH_FINISHED,
                data={"text": text},
                source="speaker",
            ))

    async def _speak_edge(self, text: str) -> None:
        """Синтез через edge-tts (бесплатный, нужен интернет)."""
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            voice=self.config.edge_voice,
            rate=self.config.edge_rate,
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        await communicate.save(tmp_path)
        await self._play_audio(tmp_path)

        Path(tmp_path).unlink(missing_ok=True)

    async def _speak_xtts(self, text: str) -> None:
        """Синтез через Coqui XTTS v2 (локальный, клонирование голоса)."""
        if self._xtts_model is None:
            log.info("Загрузка XTTS модели...")
            try:
                from TTS.api import TTS

                loop = asyncio.get_event_loop()
                self._xtts_model = await loop.run_in_executor(
                    None,
                    lambda: TTS(self.config.xtts_model),
                )
                log.info("XTTS модель загружена")
            except ImportError:
                log.error(
                    "TTS не установлен. Установите: pip install 'jarvis-ai[xtts]'"
                )
                return

        speaker_wav = self.config.xtts_speaker_wav
        if not Path(speaker_wav).exists():
            log.error(f"Файл голоса не найден: {speaker_wav}")
            log.info("Используйте edge-tts или добавьте аудио-файл голоса Джарвиса")
            await self._speak_edge(text)
            return

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._xtts_model.tts_to_file(
                text=text,
                speaker_wav=speaker_wav,
                language=self.config.xtts_language,
                file_path=tmp_path,
            ),
        )

        await self._play_audio(tmp_path)
        Path(tmp_path).unlink(missing_ok=True)

    async def _play_audio(self, file_path: str) -> None:
        """Воспроизвести аудио-файл."""
        try:
            from pydub import AudioSegment
            from pydub.playback import play as pydub_play

            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(
                None,
                lambda: AudioSegment.from_file(file_path),
            )
            await loop.run_in_executor(None, pydub_play, audio)
        except ImportError:
            # Fallback: aplay / ffplay
            process = await asyncio.create_subprocess_exec(
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()

    async def _on_response(self, event: Event) -> None:
        """Озвучить ответ LLM."""
        text = event.data.get("response", "")
        if text:
            await self.speak(text)

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
