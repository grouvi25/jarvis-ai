"""Управление десктопом: команды, запуск приложений, скриншоты, громкость."""

from __future__ import annotations

import asyncio
import glob
import os
import subprocess
from pathlib import Path
from typing import Any

from jarvis.skills.base import Skill
from jarvis.utils import platform as plat
from jarvis.utils.logger import log
from jarvis.utils.paths import SCREENSHOT_DIR, ensure_dirs

DANGEROUS_PATTERNS = (
    "rm -rf /", "rm -rf ~", "mkfs", "dd if=", ":(){", "fork bomb",
    "del /f /s /q c:\\", "format c:", "shutdown /s",
)

# Маппинг популярных приложений: русские и английские алиасы → исполняемый файл / команда
# Для Windows: используется Start-Process или прямой путь
_APP_ALIASES: dict[str, list[str]] = {
    # Мессенджеры
    "telegram": ["telegram", "телеграм", "телега", "тг"],
    "discord": ["discord", "дискорд", "диск"],
    "whatsapp": ["whatsapp", "ватсап", "вотсап", "вацап"],
    "viber": ["viber", "вайбер"],
    "slack": ["slack", "слак"],
    "teams": ["teams", "тимс", "тимз"],
    "zoom": ["zoom", "зум"],
    "skype": ["skype", "скайп"],
    # Браузеры
    "chrome": ["chrome", "хром", "гугл хром", "google chrome"],
    "firefox": ["firefox", "фаерфокс", "огнелис", "мозилла", "mozilla"],
    "edge": ["edge", "эдж", "microsoft edge"],
    "opera": ["opera", "опера"],
    "yandex": ["yandex browser", "яндекс", "яндекс браузер"],
    "brave": ["brave", "брейв"],
    # Редакторы и IDE
    "code": ["code", "vscode", "vs code", "visual studio code", "вскод"],
    "notepad": ["notepad", "блокнот"],
    "notepad++": ["notepad++", "нотпад++", "нотпад плюс"],
    "sublime": ["sublime", "сублайм", "sublime text"],
    "word": ["word", "ворд", "microsoft word"],
    "excel": ["excel", "эксель", "microsoft excel"],
    "powerpoint": ["powerpoint", "повер поинт", "повер поинт"],
    # Медиа
    "spotify": ["spotify", "спотифай"],
    "vlc": ["vlc", "влц", "вэлси"],
    "steam": ["steam", "стим"],
    # Утилиты
    "calc": ["calc", "calculator", "калькулятор"],
    "explorer": ["explorer", "проводник", "эксплорер", "файловый менеджер"],
    "cmd": ["cmd", "командная строка", "терминал", "консоль"],
    "powershell": ["powershell", "повершелл", "павершелл"],
    "taskmgr": ["taskmgr", "task manager", "диспетчер задач", "диспетчер"],
    "control": ["control", "панель управления"],
    "mspaint": ["mspaint", "paint", "пэинт", "пейнт", "рисование"],
    "snipping tool": ["snippingtool", "ножницы"],
    "settings": ["settings", "настройки", "параметры"],
}

# Где искать приложения на Windows
_WIN_SEARCH_DIRS = [
    os.path.expandvars(r"%ProgramFiles%"),
    os.path.expandvars(r"%ProgramFiles(x86)%"),
    os.path.expandvars(r"%LOCALAPPDATA%"),
    os.path.expandvars(r"%APPDATA%"),
    os.path.expandvars(r"%USERPROFILE%\Desktop"),
]

# Конкретные пути для популярных Windows приложений
_WIN_APP_PATHS: dict[str, list[str]] = {
    "telegram": [
        r"%APPDATA%\Telegram Desktop\Telegram.exe",
        r"%USERPROFILE%\AppData\Roaming\Telegram Desktop\Telegram.exe",
    ],
    "discord": [
        r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe",
    ],
    "chrome": [
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    ],
    "firefox": [
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
        r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
    ],
    "edge": [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    ],
    "yandex": [
        r"%LOCALAPPDATA%\Yandex\YandexBrowser\Application\browser.exe",
    ],
    "code": [
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
    ],
    "steam": [
        r"%ProgramFiles(x86)%\Steam\steam.exe",
        r"%ProgramFiles%\Steam\steam.exe",
    ],
    "spotify": [
        r"%APPDATA%\Spotify\Spotify.exe",
    ],
    "vlc": [
        r"%ProgramFiles%\VideoLAN\VLC\vlc.exe",
        r"%ProgramFiles(x86)%\VideoLAN\VLC\vlc.exe",
    ],
    "notepad++": [
        r"%ProgramFiles%\Notepad++\notepad++.exe",
        r"%ProgramFiles(x86)%\Notepad++\notepad++.exe",
    ],
    "sublime": [
        r"%ProgramFiles%\Sublime Text\sublime_text.exe",
        r"%ProgramFiles%\Sublime Text 3\sublime_text.exe",
    ],
    "whatsapp": [
        r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
    ],
    "zoom": [
        r"%APPDATA%\Zoom\bin\Zoom.exe",
    ],
    "teams": [
        r"%LOCALAPPDATA%\Microsoft\Teams\Update.exe --processStart Teams.exe",
    ],
    "settings": [
        "ms-settings:",
    ],
}


class DesktopControlSkill(Skill):
    """Запуск программ, выполнение команд, скриншоты, громкость, клавиатура."""

    @property
    def name(self) -> str:
        return "desktop_control"

    @property
    def description(self) -> str:
        return (
            "Управление компьютером пользователя. Действия:\n"
            "- open_app: запуск приложения по имени (русски или англ: 'telegram', 'телеграм', "
            "'chrome', 'хром', 'блокнот', 'калькулятор', 'discord', 'дискорд', 'vscode' и др). "
            "Автоматически ищет установленные приложения.\n"
            "- run_command: выполнить shell-команду\n"
            "- open_file: открыть файл/папку в файловом менеджере\n"
            "- open_url: открыть URL в браузере\n"
            "- screenshot: сделать скриншот экрана\n"
            "- volume: управление громкостью (up/down/mute или число 0-100)\n"
            "- type_text: набрать текст с клавиатуры\n"
            "- hotkey: нажать комбинацию клавиш (ctrl+c, alt+tab и т.д.)\n"
            "- lock: заблокировать компьютер\n"
            "- shutdown: выключить через N секунд\n"
            "- notify: показать системное уведомление"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "run_command", "open_app", "open_file", "open_url",
                        "screenshot", "volume", "type_text", "hotkey",
                        "lock", "shutdown", "notify",
                    ],
                },
                "command": {
                    "type": "string",
                    "description": (
                        "Для open_app: имя приложения "
                        "(telegram, chrome, блокнот, калькулятор, "
                        "discord и т.д.). Для run_command: команда. "
                        "Для open_file: путь. Для open_url: URL."
                    ),
                },
                "value": {
                    "type": "string",
                    "description": "Доп. значение: громкость, hotkey, текст",
                },
            },
            "required": ["action"],
        }

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "")
        command = (kwargs.get("command") or "").strip()
        value = (kwargs.get("value") or "").strip()

        try:
            if action == "run_command":
                if not command:
                    return "Не указана команда"
                return await self._run_command(command)
            if action == "open_app":
                if not command:
                    return "Не указано приложение"
                return await self._open_app(command)
            if action == "open_file":
                if not command:
                    return "Не указан путь"
                plat.open_in_file_manager(Path(os.path.expanduser(command)))
                return f"Открыто: {command}"
            if action == "open_url":
                url = command or value
                if not url:
                    return "Не указан URL"
                plat.open_url(url)
                return f"Открыт URL: {url}"
            if action == "screenshot":
                return await self._screenshot()
            if action == "volume":
                return await self._volume(command or value)
            if action == "type_text":
                return await self._type_text(command)
            if action == "hotkey":
                return await self._hotkey(command or value)
            if action == "lock":
                return self._lock()
            if action == "shutdown":
                delay = int(value or command or "60")
                return self._shutdown(delay)
            if action == "notify":
                plat.notify(command or "Jarvis", value or command)
                return "Уведомление отправлено"
            return f"Неизвестное действие: {action}"
        except Exception as e:
            log.exception("desktop_control")
            return f"Ошибка управления: {e}"

    # ---------- helpers ----------

    async def _run_command(self, command: str) -> str:
        low = command.lower()
        for d in DANGEROUS_PATTERNS:
            if d in low:
                return f"Команда заблокирована: {command}"
        log.info(f"$ {command}")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30,
            ),
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode != 0:
            return f"Код {result.returncode}\n{err or out}".strip()
        return out or "OK"

    async def _open_app(self, name: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._open_app_sync, name)

    def _open_app_sync(self, name: str) -> str:
        """Умный запуск приложений с поддержкой русских имён и поиском."""
        name_lower = name.lower().strip()

        if plat.is_windows():
            return self._open_app_windows(name_lower, name)
        elif plat.is_macos():
            return self._open_app_macos(name_lower, name)
        else:
            return self._open_app_linux(name_lower, name)

    def _resolve_app_key(self, name_lower: str) -> str | None:
        """Найти ключ приложения по русскому или английскому имени."""
        for app_key, aliases in _APP_ALIASES.items():
            if name_lower in aliases or name_lower == app_key:
                return app_key
        for app_key, aliases in _APP_ALIASES.items():
            for alias in aliases:
                if alias in name_lower or name_lower in alias:
                    return app_key
        return None

    def _open_app_windows(self, name_lower: str, original_name: str) -> str:
        """Запуск приложения на Windows с умным поиском."""
        app_key = self._resolve_app_key(name_lower)

        # 1. Проверяем известные пути для этого приложения
        if app_key and app_key in _WIN_APP_PATHS:
            for path_template in _WIN_APP_PATHS[app_key]:
                expanded = os.path.expandvars(path_template)
                # Специальные URI (ms-settings: и т.д.)
                if expanded.startswith("ms-"):
                    subprocess.Popen(["cmd", "/c", "start", expanded],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Запущено: {original_name}"
                # Путь с аргументами (Discord Update.exe --processStart)
                if " --" in expanded or " /" in expanded:
                    parts = expanded.split(" ", 1)
                    exe_path = parts[0]
                    if Path(exe_path).exists():
                        subprocess.Popen(expanded, shell=True,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return f"Запущено: {original_name}"
                    continue
                if Path(expanded).exists():
                    subprocess.Popen([expanded],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Запущено: {original_name}"

        # 2. Пробуем запустить через cmd /c start (для системных утилит)
        cmd_name = app_key or name_lower
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", cmd_name],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            return f"Запущено: {original_name}"
        except FileNotFoundError:
            pass

        # 3. Поиск через PowerShell в Start Menu
        found = self._search_start_menu(app_key or name_lower)
        if found:
            subprocess.Popen(
                [found], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return f"Запущено: {original_name}"

        # 4. Поиск .exe в стандартных папках
        found = self._search_exe_in_dirs(app_key or name_lower)
        if found:
            subprocess.Popen(
                [found], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return f"Запущено: {original_name}"

        return (
            f"Приложение '{original_name}' не найдено. "
            "Убедитесь, что оно установлено, или укажите точный путь к .exe файлу."
        )

    def _search_start_menu(self, name: str) -> str | None:
        """Поиск ярлыка в Start Menu на Windows."""
        start_menu_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        ]
        name_lower = name.lower()
        for menu_dir in start_menu_dirs:
            if not os.path.isdir(menu_dir):
                continue
            for root, dirs, files in os.walk(menu_dir):
                for f in files:
                    if f.lower().endswith(".lnk") and name_lower in f.lower():
                        return os.path.join(root, f)
        return None

    def _search_exe_in_dirs(self, name: str) -> str | None:
        """Поиск .exe по имени в стандартных директориях."""
        for search_dir in _WIN_SEARCH_DIRS:
            if not os.path.isdir(search_dir):
                continue
            pattern = os.path.join(search_dir, "**", f"*{name}*.exe")
            matches = glob.glob(pattern, recursive=True)
            if matches:
                matches.sort(key=lambda p: len(p))
                return matches[0]
        return None

    def _open_app_macos(self, name_lower: str, original_name: str) -> str:
        app_key = self._resolve_app_key(name_lower)
        try_name = app_key or original_name
        try:
            subprocess.Popen(
                ["open", "-a", try_name],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return f"Запущено: {original_name}"
        except FileNotFoundError:
            return f"Приложение '{original_name}' не найдено"

    def _open_app_linux(self, name_lower: str, original_name: str) -> str:
        app_key = self._resolve_app_key(name_lower)
        try_name = app_key or name_lower
        if plat.has_command(try_name):
            subprocess.Popen([try_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Запущено: {original_name}"
        if plat.has_command("gtk-launch"):
            subprocess.Popen(["gtk-launch", try_name],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Запущено: {original_name}"
        subprocess.Popen(["xdg-open", try_name],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Запущено: {original_name}"

    async def _screenshot(self) -> str:
        ensure_dirs()
        path = SCREENSHOT_DIR / f"jarvis_{int(asyncio.get_event_loop().time())}.png"
        loop = asyncio.get_event_loop()
        try:
            import pyautogui  # type: ignore[import-not-found]

            await loop.run_in_executor(None, lambda: pyautogui.screenshot(str(path)))
            return f"Скриншот: {path}"
        except Exception:
            # Платформенные fallback
            if plat.is_linux():
                for tool in ("scrot", "gnome-screenshot", "import"):
                    if plat.has_command(tool):
                        if tool == "scrot":
                            cmd = [tool, str(path)]
                        else:
                            cmd = [tool, "-window", "root", str(path)]
                        if tool == "gnome-screenshot":
                            cmd = ["gnome-screenshot", "-f", str(path)]
                        try:
                            await loop.run_in_executor(
                                None,
                                lambda c=cmd: subprocess.run(c, check=True, timeout=10),
                            )
                            return f"Скриншот: {path}"
                        except Exception:
                            continue
            return "Скриншот недоступен (установите pyautogui)"

    async def _volume(self, action: str) -> str:
        action = (action or "").lower()
        loop = asyncio.get_event_loop()

        if plat.is_linux():
            cmd_map = {
                "up": "amixer -q set Master 10%+",
                "down": "amixer -q set Master 10%-",
                "mute": "amixer -q set Master toggle",
            }
            if action.isdigit():
                cmd = f"amixer -q set Master {int(action)}%"
            else:
                cmd = cmd_map.get(action, "")
            if not cmd:
                return f"Неизвестное действие громкости: {action}"
            return await self._run_command(cmd)

        if plat.is_macos():
            mapping = {
                "up": "set volume output volume (output volume of (get volume settings) + 10)",
                "down": "set volume output volume (output volume of (get volume settings) - 10)",
                "mute": "set volume output muted not (output muted of (get volume settings))",
            }
            if action.isdigit():
                script = f"set volume output volume {int(action)}"
            else:
                script = mapping.get(action, "")
            if not script:
                return f"Неизвестное действие громкости: {action}"
            await loop.run_in_executor(None, lambda: subprocess.run(["osascript", "-e", script]))
            return f"Громкость: {action}"

        if plat.is_windows():
            # WSH через PowerShell SendKeys
            keys_map = {"up": "175", "down": "174", "mute": "173"}
            vk = keys_map.get(action, "")
            if not vk:
                return f"Неизвестное действие громкости: {action} (Windows: up/down/mute)"
            await loop.run_in_executor(
                None,
                lambda: subprocess.run([
                    "powershell", "-Command",
                    f"(New-Object -ComObject WScript.Shell).SendKeys([char]{vk})",
                ]),
            )
            return f"Громкость: {action}"

        return "Платформа не поддерживается"

    async def _type_text(self, text: str) -> str:
        if not text:
            return "Не указан текст"
        try:
            import pyautogui  # type: ignore[import-not-found]

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: pyautogui.typewrite(text, interval=0.02))
            return f"Набрано: {text[:50]}"
        except Exception as e:
            return f"Не удалось набрать текст: {e}"

    async def _hotkey(self, hotkey: str) -> str:
        if not hotkey:
            return "Не указана горячая клавиша"
        try:
            import pyautogui  # type: ignore[import-not-found]

            keys = [k.strip() for k in hotkey.replace(" ", "").split("+")]
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: pyautogui.hotkey(*keys))
            return f"Hotkey: {hotkey}"
        except Exception as e:
            return f"Ошибка hotkey: {e}"

    def _lock(self) -> str:
        if plat.is_windows():
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Заблокировано"
        if plat.is_macos():
            subprocess.Popen([
                "osascript", "-e",
                'tell application "System Events" to keystroke '
                '"q" using {control down, command down}',
            ])
            return "Заблокировано"
        # Linux: xdg-screensaver или loginctl
        for cmd in (
            ["xdg-screensaver", "lock"],
            ["loginctl", "lock-session"],
            ["gnome-screensaver-command", "-l"],
        ):
            if plat.has_command(cmd[0]):
                subprocess.Popen(cmd)
                return "Заблокировано"
        return "Не удалось заблокировать ПК"

    def _shutdown(self, delay: int) -> str:
        delay = max(5, min(delay, 3600))  # safety
        if plat.is_windows():
            subprocess.Popen(["shutdown", "/s", "/t", str(delay)])
            return f"Выключение через {delay} сек. Отмена: shutdown /a"
        # POSIX
        mins = max(1, delay // 60)
        subprocess.Popen(["shutdown", "-h", f"+{mins}"])
        return f"Выключение через ~{mins} мин."
