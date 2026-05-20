# J.A.R.V.I.S.

**Just A Rather Very Intelligent System**

Автономный AI-ассистент с голосовым управлением, контролем десктопа и полной поддержкой русского языка. Вдохновлён Джарвисом из "Железного Человека".

```
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

---

## Что умеет

- **Голосовое управление** — скажи "Джарвис" и он слушает. Распознаёт русский и английский (Whisper)
- **Голос Джарвиса** — клонирование голоса через XTTS v2 или edge-tts на русском
- **Управление браузером** — открывает сайты, гуглит, заполняет формы (Playwright)
- **Управление десктопом** — запускает программы, выполняет команды, горячие клавиши, громкость
- **Отправка сообщений** — пишет в Telegram. Говоришь "напиши моей девушке" — он найдёт контакт и отправит
- **Контакты** — база контактов с метками (девушка, мама, друг). Больше никаких chat_id — только имена
- **Авто-переподключение интернета** — сам переподключает WiFi и проходит captive portal (идеально для общаг)
- **Погода** — "Джарвис, какая погода в Москве?" (бесплатно через wttr.in)
- **Таймеры** — "Поставь таймер на 5 минут — чай готов"
- **Заметки** — "Запомни: купить молоко". Сохраняются между сессиями
- **Системная информация** — время, дата, батарея, CPU, диск, RAM
- **Файлы** — найти файл, прочитать, открыть, показать папку
- **Медиа контроль** — play/pause/next/volume через playerctl
- **Память** — помнит разговоры между перезапусками
- **Плагины** — свои скиллы через файлы в `~/.jarvis/plugins/`
- **Любой LLM через API** — [OmniRoute](https://omniroute.online/) (160+ провайдеров, авто-фоллбэк, бесплатные модели), OpenAI, Groq, Ollama

## Быстрый старт

### 1. Установка

```bash
# Клонируй репозиторий
git clone https://github.com/grouvi25/jarvis-ai.git
cd jarvis-ai

# Создай виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установи базовые зависимости (лёгкие, без GPU)
pip install -e .

# Дополнительно (опционально):
pip install -e ".[telegram]"   # Отправка сообщений в Telegram
pip install -e ".[browser]"    # Управление браузером
pip install -e ".[desktop]"    # Управление десктопом
pip install -e ".[voice]"      # Голосовой режим (Whisper + wake word)
pip install -e ".[all]"        # Всё сразу
```

### 2. Установи [OmniRoute](https://omniroute.online/) (бесплатный AI-шлюз)

```bash
npm install -g omniroute
omniroute
# Откроется дашборд — добавь свои API-ключи от провайдеров (OpenAI, Anthropic, Google и т.д.)
# OmniRoute сам роутит запросы с авто-фоллбэком
```

OmniRoute — это локальный прокси на `localhost:20128/v1`. 160+ провайдеров, сжатие токенов, авто-фоллбэк между моделями. Бесплатные модели доступны из коробки.

### 3. Настрой конфиг

```bash
cp config/config.yaml config/local.yaml
# Отредактируй config/local.yaml под себя
```

### 4. Запуск

```bash
# Текстовый режим (без микрофона)
jarvis --text

# Голосовой режим
jarvis --voice

# Автоопределение
jarvis

# Очистить историю разговоров
jarvis --clear-history

# Версия
jarvis --version
```

## Конфигурация

Основные настройки в `config/local.yaml`:

### LLM (мозг)

```yaml
# OmniRoute (рекомендуется — бесплатный AI-шлюз)
llm:
  provider: "omniroute"
  model: "gpt-4o-mini"  # любая модель из твоих провайдеров
  base_url: "http://localhost:20128/v1"  # локальный OmniRoute
  # base_url: "https://cloud.omniroute.online/v1"  # или облачный

# Или напрямую к провайдеру (без OmniRoute):
# llm:
#   provider: "openai"
#   model: "gpt-4o-mini"
#   base_url: "https://api.openai.com/v1"
#   api_key: "sk-..."
```

### Голос

```yaml
tts:
  engine: "edge-tts"        # edge-tts (бесплатно) / xtts (клон голоса)
  edge_voice: "ru-RU-DmitryNeural"  # Мужской русский голос

stt:
  engine: "google"          # google (бесплатно, нужен инет) / faster-whisper (локально)
  language: "ru"
```

### Telegram

```yaml
telegram:
  enabled: true
  bot_token: "123456:ABC..."  # От @BotFather
```

### Авто-интернет (для общаги)

```yaml
internet:
  enabled: true
  check_interval: 300        # Проверять каждые 5 минут
  wifi_ssid: "Dormitory_WiFi"
  wifi_password: "пароль"
  captive_portal:
    enabled: true
    url: "http://portal.dormitory.ru/login"
    username: "student123"
    password: "mypassword"
```

## Клонирование голоса Джарвиса

Чтобы Джарвис говорил голосом из фильма:

1. Найди чистое аудио Пола Беттани (голос Джарвиса), 6-30 секунд
2. Сохрани как `models/jarvis_voice.wav`
3. Измени конфиг:

```yaml
tts:
  engine: "xtts"
  xtts_speaker_wav: "models/jarvis_voice.wav"
  xtts_language: "ru"
```

4. Установи XTTS: `pip install -e ".[xtts]"`

## Авто-переподключение интернета

Для общаги где интернет отключается ночью:

### Вариант 1: Через Джарвиса (автоматически)
Если Джарвис запущен — он сам мониторит интернет и переподключает.

### Вариант 2: Системный сервис (даже без Джарвиса)

```bash
# Настрой переменные в scripts/jarvis-internet.service
sudo cp scripts/jarvis-internet.{service,timer} /etc/systemd/system/
sudo systemctl enable --now jarvis-internet.timer
```

### Вариант 3: Cron

```bash
chmod +x scripts/auto_internet.sh
crontab -e
# Добавь:
# */5 * * * * /path/to/jarvis-ai/scripts/auto_internet.sh >> ~/jarvis_internet.log 2>&1
```

## Архитектура

```
┌──────────────────────────────────────────────┐
│                JARVIS                         │
│                                               │
│  Микрофон → [Wake Word] → [Whisper STT]      │
│                              ↓                │
│                         [LLM Brain]           │
│                        ↙    ↓     ↘           │
│                 [TTS]  [Skills]  [Events]     │
│                   ↓    ↙  ↓   ↘               │
│              Динамики  📱  🌐   🖥️             │
│                     Telegram Browser Desktop  │
│                                               │
│  [Internet Monitor] — фоновая проверка сети   │
└──────────────────────────────────────────────┘
```

### Модули

| Модуль | Описание |
|--------|----------|
| `jarvis/core/brain.py` | LLM-мозг с function calling |
| `jarvis/core/event_bus.py` | Асинхронная шина событий |
| `jarvis/core/config.py` | Конфигурация из YAML + .env |
| `jarvis/core/memory.py` | Память — история и контакты |
| `jarvis/voice/listener.py` | STT через faster-whisper |
| `jarvis/voice/speaker.py` | TTS через edge-tts / XTTS v2 |
| `jarvis/voice/wake_word.py` | Детектор wake word |
| `jarvis/skills/messenger.py` | Отправка сообщений в Telegram |
| `jarvis/skills/contacts.py` | Контакты с метками |
| `jarvis/skills/browser.py` | Управление браузером (Playwright) |
| `jarvis/skills/desktop.py` | Управление десктопом |
| `jarvis/skills/internet.py` | Авто-переподключение интернета |
| `jarvis/skills/weather.py` | Погода через wttr.in |
| `jarvis/skills/timer.py` | Таймеры и напоминания |
| `jarvis/skills/notes.py` | Заметки с поиском |
| `jarvis/skills/system_info.py` | Системная информация |
| `jarvis/skills/file_manager.py` | Работа с файлами |
| `jarvis/skills/media.py` | Управление медиа |

## Создание своих скиллов

```python
from jarvis.skills.base import Skill

class MySkill(Skill):
    @property
    def name(self) -> str:
        return "my_skill"

    @property
    def description(self) -> str:
        return "Описание для LLM на русском"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Описание"},
            },
            "required": ["param1"],
        }

    async def execute(self, **kwargs) -> str:
        # Твоя логика
        return "Результат"
```

**Вариант 1:** Зарегистрируй в `main.py`:
```python
brain.register_skill(MySkill())
```

**Вариант 2:** Как плагин — сохрани файл в `~/.jarvis/plugins/my_skill.py`:
```python
def register(brain, config, event_bus, memory):
    brain.register_skill(MySkill())
```
Плагины загружаются автоматически при запуске.

## Требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| Python | 3.10+ | 3.12+ |
| RAM | 2 GB | 4 GB |
| GPU | Не нужна | Не нужна (всё через API) |
| ОС | Linux | Ubuntu 22.04+ |
| Интернет | Нужен (для API) | Нужен |

**Ноутбук?** Без проблем! Всё тяжёлое работает через API (OmniRoute/OpenAI/Groq). Твой комп только шлёт запросы и играет аудио.

## Авто-запуск при включении компа

```bash
# Скопируй сервис
mkdir -p ~/.config/systemd/user/
cp scripts/jarvis.service ~/.config/systemd/user/

# Включи авто-запуск
systemctl --user enable jarvis.service
systemctl --user start jarvis.service

# Проверить статус
systemctl --user status jarvis.service
```

## Лицензия

MIT
