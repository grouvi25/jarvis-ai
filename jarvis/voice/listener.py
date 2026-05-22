"""Распознавание речи (STT) для J.A.R.V.I.S."""

from __future__ import annotations

import asyncio
import io
import queue
import wave
from typing import TYPE_CHECKING

import numpy as np

from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.utils.logger import log

if TYPE_CHECKING:
    from jarvis.core.config import STTConfig


class SpeechListener:
    """Слушает микрофон, распознаёт речь через faster-whisper."""

    def __init__(self, config: STTConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._running = False
        self._model = None
        self._sample_rate = 16000
        self._block_size = 1024

    def _load_model(self) -> None:
        """Ленивая загрузка модели Whisper."""
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel

            log.info(
                f"Загрузка Whisper модели: [bold]{self.config.model}[/bold] "
                f"(устройство: {self.config.device})"
            )
            self._model = WhisperModel(
                self.config.model,
                device=self.config.device,
                compute_type="int8" if self.config.device == "cpu" else "float16",
            )
            log.info("Whisper модель загружена")
        except ImportError:
            log.warning("faster-whisper не установлен, используем SpeechRecognition")
            self._model = "speech_recognition"

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: object,
    ) -> None:
        """Callback для sounddevice — складывает аудио в очередь."""
        if status:
            log.warning(f"Аудио статус: {status}")
        self._audio_queue.put(indata.copy())

    async def _transcribe_buffer(self, audio_data: np.ndarray) -> str:
        """Транскрибировать аудио-буфер в текст."""
        if self._model is None:
            self._load_model()

        if self._model == "speech_recognition":
            return await self._transcribe_sr(audio_data)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_whisper, audio_data)

    def _transcribe_whisper(self, audio_data: np.ndarray) -> str:
        """Транскрипция через faster-whisper."""
        audio_float = audio_data.flatten().astype(np.float32)
        if np.max(np.abs(audio_float)) > 1.0:
            audio_float = audio_float / 32768.0

        segments, info = self._model.transcribe(
            audio_float,
            language=self.config.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()

    async def _transcribe_sr(self, audio_data: np.ndarray) -> str:
        """Fallback транскрипция через SpeechRecognition (Google API)."""
        import speech_recognition as sr

        audio_int16 = (audio_data.flatten() * 32768).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self._sample_rate)
            wf.writeframes(audio_int16.tobytes())
        buf.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(buf) as source:
            audio = recognizer.record(source)

        loop = asyncio.get_event_loop()
        try:
            text = await loop.run_in_executor(
                None,
                lambda: recognizer.recognize_google(audio, language=self.config.language),
            )
            return text
        except (sr.UnknownValueError, sr.RequestError):
            return ""

    async def listen_continuous(self) -> None:
        """Непрерывное прослушивание микрофона с VAD."""
        self._load_model()
        self._running = True
        log.info("Микрофон активен — слушаю...")

        silence_threshold = 0.01
        speech_threshold = 0.02
        min_speech_duration = 0.5  # секунд
        max_speech_duration = 30.0  # секунд
        silence_after_speech = 1.5  # секунд тишины = конец фразы

        import sounddevice as sd

        stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self._block_size,
            callback=self._audio_callback,
        )

        with stream:
            speech_buffer: list[np.ndarray] = []
            is_speaking = False
            silence_counter = 0
            speech_blocks = 0
            blocks_per_second = self._sample_rate / self._block_size

            while self._running:
                try:
                    data = self._audio_queue.get(timeout=0.1)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

                amplitude = np.max(np.abs(data))

                if not is_speaking and amplitude > speech_threshold:
                    is_speaking = True
                    speech_buffer = [data]
                    silence_counter = 0
                    speech_blocks = 1
                elif is_speaking:
                    speech_buffer.append(data)
                    speech_blocks += 1

                    if amplitude < silence_threshold:
                        silence_counter += 1
                    else:
                        silence_counter = 0

                    speech_duration = speech_blocks / blocks_per_second
                    silence_duration = silence_counter / blocks_per_second

                    speech_ended = (silence_duration >= silence_after_speech
                                    or speech_duration >= max_speech_duration)
                    if speech_ended:
                        is_speaking = False
                        if speech_duration >= min_speech_duration:
                            audio = np.concatenate(speech_buffer)
                            text = await self._transcribe_buffer(audio)
                            if text:
                                await self.event_bus.emit(Event(
                                    type=EventType.SPEECH_RECOGNIZED,
                                    data={"text": text},
                                    source="listener",
                                ))
                        speech_buffer = []
                        silence_counter = 0
                        speech_blocks = 0

                await asyncio.sleep(0)

    def stop(self) -> None:
        """Остановить прослушивание."""
        self._running = False
