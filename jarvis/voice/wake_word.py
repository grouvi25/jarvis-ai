"""Детектор wake word для J.A.R.V.I.S."""

from __future__ import annotations

import asyncio
import queue
from typing import TYPE_CHECKING

import numpy as np

from jarvis.core.event_bus import Event, EventBus, EventType
from jarvis.utils.logger import log

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig


class WakeWordDetector:
    """Слушает wake word и активирует запись речи.

    Три режима (выбирается автоматически):
    1. openwakeword — нейросетевой детектор (если установлен, для "Hey Jarvis")
    2. keyword — поиск ключевого слова в транскрипции (основной для русского "Джарвис")
    3. always_on — без wake word, всегда слушает (для отладки)

    Для русского языка рекомендуется keyword-режим, т.к. openwakeword
    поддерживает только английский "Hey Jarvis".
    """

    def __init__(self, config: JarvisConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        self.wake_words = [w.lower() for w in config.wake_words]
        self._running = False
        self._oww_model = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._sample_rate = 16000
        self._chunk_size = 1280

    def _has_russian_wake_words(self) -> bool:
        """Проверяем, есть ли русские wake words."""
        for word in self.wake_words:
            if any("\u0400" <= ch <= "\u04ff" for ch in word):
                return True
        return False

    def _try_load_openwakeword(self) -> bool:
        """Попробовать загрузить openwakeword."""
        if self._has_russian_wake_words():
            log.info(
                "Русские wake words обнаружены — openwakeword их не поддерживает, "
                "используем keyword-режим (распознавание через STT)"
            )
            return False
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
        status: object,
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
        import sounddevice as sd

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
        """Keyword-режим: ищет wake word в транскрипции.

        Подписывается на события SPEECH_RECOGNIZED от SpeechListener,
        ищет wake word в распознанном тексте, и если нашёл — убирает
        wake word из текста и передаёт команду дальше.
        """
        log.info(
            f"Keyword-режим активирован — слушаю: {', '.join(self.wake_words)}\n"
            "  Скажите «Джарвис, [команда]» — и ассистент выполнит команду."
        )

        async def check_wake_word(event: Event) -> None:
            text = event.data.get("text", "").lower()
            for word in self.wake_words:
                if word in text:
                    log.info(f"Wake word найден: [bold green]{word}[/bold green] в «{text}»")
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
