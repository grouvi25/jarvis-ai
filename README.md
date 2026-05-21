# J.A.R.V.I.S.

**Just A Rather Very Intelligent System** — личный AI-ассистент, который живёт в трее
твоего компьютера, отвечает голосом и текстом, и реально делает дела: открывает сайты,
читает файлы, переподключает интернет, запоминает что ты ему говоришь.

```
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

---

## Что это

Десктопное приложение, которое:

1. **Висит иконкой в трее** — клик открывает чат в браузере.
2. **Чат + голос** — общайся текстом в красивом веб-UI или голосом ("Джарвис, …").
3. **Делает дела на компе** — запускает программы, читает файлы, копирует в буфер,
   выключает компьютер по таймеру, смотрит сколько RAM свободно, ищет в гугле,
   управляет браузером через Playwright.
4. **Помнит тебя** — запоминает факты ("меня зовут Никита", "я живу в Москве"),
   сохраняет историю разговоров между сессиями.
5. **Запускается при входе в систему** — один раз поставил и забыл.
6. **Любой LLM** — OmniRoute (бесплатный шлюз с 160+ провайдерами), OpenAI, Groq,
   Ollama, или любой OpenAI-совместимый.

---

## Установка

### Windows — готовый инсталлятор

1. Скачай `Jarvis-Setup.exe` со страницы релизов.
2. Двойной клик → "Далее" → "Установить".
3. Выбери "Запускать при старте Windows" (если хочешь).
4. После установки откроется мастер настройки — выбери LLM и введи API-ключ.
5. Иконка появится в трее. Клик → откроется чат.

### Windows — из исходников

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\install.ps1
```

### Linux / macOS — одной командой

```bash
bash scripts/install.sh
```

Скрипт:
1. Проверит Python 3.10+
2. Создаст `venv` в `~/.local/share/jarvis/venv`
3. Установит пакет и положит лаунчер в `~/.local/bin/jarvis-app`
4. На Linux — добавит `.desktop`-запись, чтобы Джарвис был в меню приложений
5. Спросит про автозапуск

После установки запусти `jarvis-app` — впервые откроется CLI-мастер настройки.

### Любая платформа — pip

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -e ".[voice]"     # голосовой режим (whisper + микрофон)
pip install -e ".[desktop]"   # управление десктопом (pyautogui)
pip install -e ".[browser]"   # управление браузером (playwright)
pip install -e ".[all]"       # всё сразу

jarvis-setup     # интерактивный мастер
jarvis-app       # запустить десктоп-приложение (трей + web-UI)
jarvis --text    # простой текстовый CLI
jarvis --voice   # голосовой CLI без трея
```

---

## Сборка собственного exe

```bash
pip install -e .[build]
python build/build.py                 # → dist/Jarvis.exe
python build/build.py --installer     # +Inno Setup инсталлятор (только Windows)
```

`build/jarvis.spec` — конфиг PyInstaller, `build/installer.iss` — Inno Setup.

---

## Использование

После установки в трее появится иконка `J`. Меню:

- **Открыть чат** — открывает `http://127.0.0.1:8765` в браузере
- **Голос: вкл/выкл** — включает/выключает TTS-ответы
- **Перезагрузить конфиг** — после ручной правки yaml
- **Выход** — корректно останавливает фоновый процесс

В чате четыре вкладки:

- **Чат** — диалог с Джарвисом
- **Память** — что он о тебе помнит (можно вручную добавить/удалить)
- **Настройки** — LLM, голос, автозапуск, имя, обращение
- **Скиллы** — список доступных инструментов

---

## Что умеет (скиллы)

| Скилл | Примеры |
|---|---|
| `desktop_control` | "запусти firefox", "сделай скриншот", "поставь громкость 50", "выключи комп через 10 минут", "заблокируй экран" |
| `files` | "прочитай ~/notes.txt", "сохрани это в файл report.md", "что в папке Downloads", "найди все *.pdf" |
| `clipboard` | "что у меня в буфере", "скопируй это" |
| `system_info` | "сколько свободной памяти", "как нагружен процессор", "сколько батареи", "что грузит комп" |
| `time` | "сколько времени", "напомни через 10 минут о созвоне" |
| `notes` | "запомни что меня зовут Никита", "что ты обо мне помнишь", "забудь про работу", "запиши: купить молоко" |
| `web_search` | "найди в интернете последние новости про …" (DuckDuckGo, без ключей) |
| `browser_action` | "открой ютуб", "погугли рецепт борща", "сделай скрин страницы" (Playwright) |
| `reconnect_internet` | "пропал интернет, переподключись" — для общаги |
| `send_telegram_message` | "напиши Маше что я опоздаю" (через Telegram-бота) |

---

## Конфигурация

Конфиг хранится в OS-стандартных местах:

| OS | Путь |
|---|---|
| Linux | `~/.config/jarvis/config.yaml` |
| macOS | `~/Library/Application Support/Jarvis/config.yaml` |
| Windows | `%APPDATA%\Jarvis\config.yaml` |

Логи: `~/.local/share/jarvis/logs/jarvis.log` (Linux) / соответствующий путь на других ОС.

Все настройки можно поменять через web-UI (вкладка "Настройки") или вручную.

### Переменные окружения

Поверх yaml-конфига приоритетнее всего — переменные окружения с префиксом `JARVIS_`:

```bash
JARVIS_LLM_PROVIDER=openai
JARVIS_LLM_MODEL=gpt-4o-mini
JARVIS_LLM_BASE_URL=https://api.openai.com/v1
JARVIS_LLM_API_KEY=sk-…
JARVIS_SERVER_PORT=8765
JARVIS_VOICE_ENABLED=false
JARVIS_TELEGRAM_TOKEN=…
```

---

## LLM-провайдеры

### OmniRoute (рекомендуется)
[OmniRoute](https://omniroute.online/) — локальный AI-шлюз с 160+ провайдеров и
бесплатными моделями.

```bash
npm install -g omniroute
omniroute   # откроется дашборд, добавь свои ключи
```

В мастере выбери `1. OmniRoute`. Базовый URL `http://localhost:20128/v1` уже стоит.

### OpenAI / Groq / Ollama
Все OpenAI-совместимые. Просто введи свой `base_url`, `model`, `api_key` в мастере
или в UI.

---

## Клонирование голоса Джарвиса

Чтобы он говорил как из фильма (Пол Беттани):

1. Найди чистый wav-кусочек его голоса 6-30 сек → сохрани как `models/jarvis_voice.wav`.
2. В настройках выбери TTS-движок `xtts`.
3. `pip install -e .[xtts]`

Иначе по умолчанию работает `edge-tts` с бесплатным русским мужским голосом
`ru-RU-DmitryNeural`.

---

## Голосовой режим

Активируется одним из путей:

- В десктопе — он сам включится при наличии микрофона (если в настройках `voice_enabled: true`)
- В CLI — `jarvis --voice`

Wake word — `Джарвис` или `jarvis`. Внутри две стратегии:

1. **openwakeword** (рекомендуется) — нейросетевой детектор фразы "hey jarvis"
2. **keyword fallback** — постоянная транскрипция через faster-whisper и поиск
   wake-word в тексте

Для распознавания речи — `faster-whisper` локально или Google Speech API онлайн.

---

## Автоматическое переподключение интернета

Особенно полезно если ты живёшь в общаге, и WiFi отключается ночью:

```yaml
internet:
  enabled: true
  check_interval: 300
  wifi_ssid: "Dormitory_WiFi"
  wifi_password: "пароль"
  captive_portal:
    enabled: true
    url: "http://portal.dormitory.ru/login"
    username: "student123"
    password: "mypassword"
```

Джарвис будет проверять интернет каждые 5 минут и переподключаться сам.

Если Джарвис не запущен — есть systemd-сервис:

```bash
sudo cp scripts/jarvis-internet.{service,timer} /etc/systemd/system/
sudo systemctl enable --now jarvis-internet.timer
```

---

## Архитектура

```
┌────────────────────────────────────────────────────┐
│                JARVIS Desktop App                  │
│                                                    │
│   ┌──────────┐   ┌──────────┐   ┌──────────────┐   │
│   │   Tray   │   │  Voice   │   │ FastAPI      │   │
│   │ (pystray)│   │ Wake+STT │   │  + WebSocket │   │
│   └────┬─────┘   └────┬─────┘   └──────┬───────┘   │
│        │              │                │           │
│        └──────────────┴────────────────┘           │
│                       │                            │
│                  ┌────▼────┐    ┌──────────────┐   │
│                  │  Brain  │◄───┤    Memory    │   │
│                  │  (LLM)  │    │ (persistent) │   │
│                  └────┬────┘    └──────────────┘   │
│                       │                            │
│                  ┌────▼─────────────────┐          │
│                  │  Skills (function    │          │
│                  │  calling tools)      │          │
│                  └──────────────────────┘          │
└────────────────────────────────────────────────────┘
              │             │           │
           Desktop       Browser     Telegram
          (любая ОС)   (Playwright)   (бот)
```

### Что где

| Модуль | Что делает |
|---|---|
| `jarvis/app.py` | Главная точка входа desktop-приложения |
| `jarvis/main.py` | CLI-точка входа (`jarvis --text`/`--voice`) |
| `jarvis/core/brain.py` | LLM-мозг с multi-step function calling |
| `jarvis/core/memory.py` | Долговременная память + история диалога |
| `jarvis/core/event_bus.py` | Асинхронная шина событий |
| `jarvis/core/config.py` | Конфиг (YAML + env vars) |
| `jarvis/core/setup_wizard.py` | Интерактивный мастер первого запуска |
| `jarvis/voice/listener.py` | STT (faster-whisper или Google) |
| `jarvis/voice/speaker.py` | TTS (edge-tts или XTTS) |
| `jarvis/voice/wake_word.py` | Детектор wake word |
| `jarvis/skills/*` | Скиллы — каждый файл = один инструмент |
| `jarvis/ui/server.py` | FastAPI + WebSocket бэкенд |
| `jarvis/ui/tray.py` | Иконка в системном трее |
| `jarvis/ui/web/*` | HTML/CSS/JS веб-UI |
| `jarvis/utils/paths.py` | OS-aware пути (Win/Mac/Linux) |
| `jarvis/utils/autostart.py` | Установка автозапуска при входе в систему |
| `build/` | PyInstaller spec, Inno Setup инсталлятор |
| `scripts/install.sh`, `install.ps1` | Скрипты установки из исходников |

---

## Создание своих скиллов

```python
from jarvis.skills.base import Skill

class WeatherSkill(Skill):
    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Узнать погоду в городе. Используй когда спрашивают про погоду."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Название города"},
            },
            "required": ["city"],
        }

    async def execute(self, **kwargs) -> str:
        city = kwargs.get("city", "")
        # ... твоя логика ...
        return f"В {city} сейчас солнечно, +20°C"
```

Зарегистрируй в `jarvis/app.py` → `register_all_skills`:

```python
brain.register_skill(WeatherSkill())
```

---

## Разработка

```bash
pip install -e .[dev]
pytest                  # запустить тесты
ruff check jarvis       # линт
ruff format jarvis      # форматирование
```

---

## Лицензия

MIT
