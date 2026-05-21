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

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        await communicate.save(tmp_path)
        try:
            await self._play_audio(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

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

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        loop = asyncio.get_event_loop()
        try:
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
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _play_audio(self, file_path: str) -> None:
        try:
            from pydub import AudioSegment
            from pydub.playback import play as pydub_play

            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(
                None,
                lambda: AudioSegment.from_file(file_path),
            )
            await loop.run_in_executor(None, pydub_play, audio)
        except Exception:
            # Fallback: ffplay
            try:
                process = await asyncio.create_subprocess_exec(
                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await process.wait()
            except FileNotFoundError:
                log.warning("ffplay не найден — аудио не воспроизведено")

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
