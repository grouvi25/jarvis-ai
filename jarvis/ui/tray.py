"""Системный трей J.A.R.V.I.S. через pystray."""

from __future__ import annotations

import threading
from typing import Callable

from jarvis.utils import platform as plat
from jarvis.utils.logger import log


def make_icon_image(size: int = 64) -> "object":
    """Сгенерировать иконку Джарвиса (PIL Image)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Круг (рамка)
    pad = 4
    d.ellipse([pad, pad, size - pad, size - pad], fill=(15, 22, 36, 255), outline=(64, 196, 255, 255), width=3)
    # Буква "J"
    try:
        from PIL import ImageFont

        font = ImageFont.truetype("DejaVuSans-Bold.ttf", size - 24)
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
    text = "J"
    if font is not None:
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
               text, fill=(64, 196, 255, 255), font=font)
    return img


class JarvisTray:
    """Иконка в системном трее с меню Open/Pause/Quit."""

    def __init__(
        self,
        *,
        url: str,
        on_quit: Callable[[], None],
        on_toggle_voice: Callable[[], bool] | None = None,
        on_reload: Callable[[], None] | None = None,
        name: str = "Jarvis",
    ) -> None:
        self.url = url
        self.on_quit = on_quit
        self.on_toggle_voice = on_toggle_voice
        self.on_reload = on_reload
        self.name = name
        self._icon = None
        self._thread: threading.Thread | None = None
        self._voice_on = True

    def start(self) -> None:
        """Запустить трей в отдельном потоке."""
        try:
            import pystray
        except ImportError:
            log.warning("pystray не установлен — трей не доступен")
            return

        image = make_icon_image()

        def _open(_icon=None, _item=None) -> None:
            plat.open_url(self.url)

        def _quit(_icon=None, _item=None) -> None:
            log.info("Выход из Джарвиса по нажатию из трея")
            try:
                if self._icon is not None:
                    self._icon.stop()
            finally:
                self.on_quit()

        def _toggle_voice(_icon=None, _item=None) -> None:
            if self.on_toggle_voice is None:
                return
            self._voice_on = self.on_toggle_voice()
            if self._icon is not None:
                self._icon.update_menu()

        def _reload(_icon=None, _item=None) -> None:
            if self.on_reload is not None:
                self.on_reload()

        menu_items = [
            pystray.MenuItem("Открыть чат", _open, default=True),
        ]
        if self.on_toggle_voice is not None:
            menu_items.append(
                pystray.MenuItem(
                    lambda _i: f"Голос: {'вкл' if self._voice_on else 'выкл'}",
                    _toggle_voice,
                )
            )
        if self.on_reload is not None:
            menu_items.append(pystray.MenuItem("Перезагрузить конфиг", _reload))
        menu_items.append(pystray.Menu.SEPARATOR)
        menu_items.append(pystray.MenuItem("Выход", _quit))

        self._icon = pystray.Icon(
            self.name, image, self.name, pystray.Menu(*menu_items)
        )

        def _run() -> None:
            try:
                assert self._icon is not None
                self._icon.run()
            except Exception as e:
                log.error(f"Tray crashed: {e}")

        self._thread = threading.Thread(target=_run, daemon=True, name="jarvis-tray")
        self._thread.start()

    def notify(self, title: str, message: str) -> None:
        """Балун-уведомление от иконки трея (best-effort)."""
        try:
            if self._icon is not None and hasattr(self._icon, "notify"):
                self._icon.notify(message, title)
            else:
                plat.notify(title, message)
        except Exception:
            plat.notify(title, message)

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
