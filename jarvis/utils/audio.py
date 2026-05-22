"""Аудио-утилиты: bundled ffmpeg + воспроизведение без внешних бинарей.

ffmpeg качается автоматически через imageio-ffmpeg, ffplay не нужен.
Воспроизведение — через sounddevice (PortAudio в комплекте с wheel'ом).
"""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache

from jarvis.utils.logger import log


@lru_cache(maxsize=1)
def ffmpeg_path() -> str:
    """Путь к bundled ffmpeg бинарю."""
    try:
        import imageio_ffmpeg

        path = imageio_ffmpeg.get_ffmpeg_exe()
        return path
    except Exception as e:
        log.warning(f"imageio-ffmpeg недоступен ({e}), пробую системный ffmpeg")
        return "ffmpeg"


def configure_pydub() -> None:
    """Сказать pydub использовать bundled ffmpeg."""
    try:
        from pydub import AudioSegment

        ff = ffmpeg_path()
        AudioSegment.converter = ff
        AudioSegment.ffmpeg = ff
        AudioSegment.ffprobe = ff
        os.environ.setdefault("FFMPEG_BINARY", ff)
    except Exception as e:
        log.debug(f"configure_pydub: {e}")


async def play_audio_bytes(
    audio_bytes: bytes, input_format: str = "mp3",
) -> None:
    """Декодирует аудио через ffmpeg в PCM и проигрывает через sounddevice."""
    if not audio_bytes:
        return

    sample_rate = 24000
    ff = ffmpeg_path()
    try:
        proc = await asyncio.create_subprocess_exec(
            ff,
            "-loglevel", "quiet",
            "-f", input_format,
            "-i", "pipe:0",
            "-f", "s16le",
            "-ar", str(sample_rate),
            "-ac", "1",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError:
        log.warning("ffmpeg не найден — аудио не воспроизведено")
        return

    try:
        pcm, _ = await proc.communicate(audio_bytes)
    except Exception as e:
        log.warning(f"ffmpeg decode упал: {e}")
        return

    if not pcm:
        return

    try:
        import numpy as np
        import sounddevice as sd

        arr = np.frombuffer(pcm, dtype=np.int16)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: sd.play(arr, sample_rate))
        await loop.run_in_executor(None, sd.wait)
    except Exception as e:
        log.warning(f"sounddevice playback упал: {e}")
