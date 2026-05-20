"""Детектор wake word для J.A.R.V.I.S."""

from __future__ import annotations

import asyncio
import queue
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd

from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.utils.logger import log

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig


class WakeWordDetector:
    """Слушает wake word и активирует запись речи.

    Два режима:
    1. openwakeword — нейросетевой детектор (рекомендуется)
    2. keyword — простой поиск ключевого слова в транскрипции (fallback)
    """

    def __init__(self, config: JarvisConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self.wake_words = [w.lower() for w in config.wake_words]
        self._running = False
        self._oww_model = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._sample_rate = 16000
        self._chunk_size = 1280  # openwakeword ожидает чанки по 80мс при 16кГц

    def _try_load_openwakeword(self) -> bool:
        """Попробовать загрузить openwakeword."""
        try:
            import openwakeword
            from openwakeword.model import Model

            openwakeword.utils.download_models()
            self._oww_model = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx",
            )
            log.info("OpenWakeWord загружен — детектирую 'Hey Jarvis'")
            return True
        except (ImportError, Exception) as e:
            log.info(f"OpenWakeWord недоступен ({e}), используем keyword-режим")
            return False

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            log.warning(f"Аудио: {status}")
        self._audio_queue.put(indata.copy())

    async def listen(self) -> None:
        """Запустить детекцию wake word."""
        self._running = True
        use_oww = self._try_load_openwakeword()

        if use_oww:
            await self._listen_openwakeword()
        else:
            await self._listen_keyword()

    async def _listen_openwakeword(self) -> None:
        """Детекция через openwakeword (нейросеть)."""
        stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self._chunk_size,
            callback=self._audio_callback,
        )

        log.info(f"Слушаю wake word: {', '.join(self.wake_words)}...")

        with stream:
            while self._running:
                try:
                    data = self._audio_queue.get(timeout=0.1)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

                prediction = self._oww_model.predict(data.flatten())
                for model_name, score in prediction.items():
                    if score > 0.5:
                        log.info(
                            f"Wake word: [bold green]{model_name}[/bold green] ({score:.2f})"
                        )
                        await self.event_bus.emit(Event(
                            type=EventType.WAKE_WORD_DETECTED,
                            data={"word": model_name, "score": score},
                            source="wake_word",
                        ))
                        self._oww_model.reset()
                        await asyncio.sleep(0.5)
                        break

                await asyncio.sleep(0)

    async def _listen_keyword(self) -> None:
        """Fallback: детекция через транскрипцию (постоянно слушает и ищет ключевое слово)."""
        log.info(f"Keyword-режим — слушаю слова: {', '.join(self.wake_words)}...")
        log.info("Совет: установите openwakeword для лучшей детекции")

        # В keyword-режиме подписываемся на события распознавания речи
        # и ищем wake word в тексте
        async def check_wake_word(event: Event) -> None:
            text = event.data.get("text", "").lower()
            for word in self.wake_words:
                if word in text:
                    log.info(f"Wake word найден в тексте: [bold green]{word}[/bold green]")
                    # Убираем wake word из текста и передаём дальше
                    clean_text = text
                    for w in self.wake_words:
                        clean_text = clean_text.replace(w, "").strip()
                    clean_text = clean_text.strip(" ,.")

                    await self.event_bus.emit(Event(
                        type=EventType.WAKE_WORD_DETECTED,
                        data={"word": word, "remaining_text": clean_text},
                        source="wake_word",
                    ))
                    break

        self.event_bus.on(EventType.SPEECH_RECOGNIZED, check_wake_word)

        while self._running:
            await asyncio.sleep(0.1)

    def stop(self) -> None:
        self._running = False
