"""Синтез речи (TTS) для J.A.R.V.I.S."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.utils.audio import play_audio_bytes
from jarvis.utils.logger import log

if TYPE_CHECKING:
    from jarvis.core.config import TTSConfig


class Speaker:
    """Озвучивает текст. Вызывается явно из главного цикла."""

    def __init__(self, config: TTSConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self._xtts_model = None
        self._is_speaking = False
        self._lock = asyncio.Lock()

    async def speak(self, text: str) -> None:
        if not text or not text.strip():
            return

        async with self._lock:
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
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            voice=self.config.edge_voice,
            rate=self.config.edge_rate,
        )

        audio_bytes = bytearray()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                audio_bytes.extend(chunk["data"])

        await play_audio_bytes(bytes(audio_bytes), input_format="mp3")

    async def _speak_xtts(self, text: str) -> None:
        if self._xtts_model is None:
            log.info("Загрузка XTTS модели...")
            try:
                from TTS.api import TTS

                loop = asyncio.get_event_loop()
                self._xtts_model = await loop.run_in_executor(
                    None,
                    lambda: TTS(self.config.xtts_model),
                )
                log.info("XTTS загружен")
            except ImportError:
                log.error("TTS не установлен. pip install 'jarvis-ai[xtts]'")
                await self._speak_edge(text)
                return

        speaker_wav = self.config.xtts_speaker_wav
        if not Path(speaker_wav).exists():
            log.warning(f"Файл голоса не найден: {speaker_wav}, fallback на edge-tts")
            await self._speak_edge(text)
            return

        # XTTS пишет в файл — используем tempfile, читаем байты, удаляем.
        tmp_dir = Path(tempfile.gettempdir())
        tmp_path = tmp_dir / f"jarvis_xtts_{id(text)}.wav"
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._xtts_model.tts_to_file(
                    text=text,
                    speaker_wav=speaker_wav,
                    language=self.config.xtts_language,
                    file_path=str(tmp_path),
                ),
            )
            audio_bytes = tmp_path.read_bytes()
            await play_audio_bytes(audio_bytes, input_format="wav")
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
