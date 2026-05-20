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
- **Управление десктопом** — запускает программы, выполняет команды, горячие клавиши
- **Отправка сообщений** — пишет в Telegram от твоего имени
- **Авто-переподключение интернета** — сам переподключает WiFi и проходит captive portal (идеально для общаг)
- **Любой LLM через API** — OpenRouter (много моделей, есть бесплатные), OpenAI, Groq, Ollama
- **Расширяемость** — легко добавлять свои скиллы

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

### 2. Получи API-ключ

Самый простой вариант — [OpenRouter](https://openrouter.ai/) (много моделей через один ключ, есть бесплатные):
1. Зарегистрируйся на https://openrouter.ai/
2. Создай API-ключ в https://openrouter.ai/keys
3. Вставь в конфиг (see ниже)

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
```

## Конфигурация

Основные настройки в `config/local.yaml`:

### LLM (мозг)

```yaml
# OpenRouter (рекомендуется)
llm:
  provider: "openrouter"
  model: "google/gemini-2.0-flash-001"  # или любая с openrouter.ai/models
  base_url: "https://openrouter.ai/api/v1"
  api_key: "sk-or-..."     # Твой ключ с openrouter.ai/keys

# Или OpenAI напрямую:
# llm:
#   provider: "openai"
#   model: "gpt-4o-mini"
#   base_url: "https://api.openai.com/v1"
#   api_key: "sk-..."

# Или Groq (быстро + есть бесплатный tier):
# llm:
#   provider: "groq"
#   model: "llama-3.1-70b-versatile"
#   base_url: "https://api.groq.com/openai/v1"
#   api_key: "gsk_..."

# Или Ollama (локально, если мощный комп):
# llm:
#   provider: "ollama"
#   model: "llama3.1"
#   base_url: "http://localhost:11434/v1"
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
| `jarvis/core/config.py` | Конфигурация из YAML |
| `jarvis/voice/listener.py` | STT через faster-whisper |
| `jarvis/voice/speaker.py` | TTS через edge-tts / XTTS v2 |
| `jarvis/voice/wake_word.py` | Детектор wake word |
| `jarvis/skills/messenger.py` | Отправка сообщений в Telegram |
| `jarvis/skills/browser.py` | Управление браузером (Playwright) |
| `jarvis/skills/desktop.py` | Управление десктопом |
| `jarvis/skills/internet.py` | Авто-переподключение интернета |

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

Зарегистрируй в `main.py`:
```python
brain.register_skill(MySkill())
```

## Требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| Python | 3.10+ | 3.12+ |
| RAM | 2 GB | 4 GB |
| GPU | Не нужна | Не нужна (всё через API) |
| ОС | Linux | Ubuntu 22.04+ |
| Интернет | Нужен (для API) | Нужен |

**Ноутбук?** Без проблем! Всё тяжёлое работает через API (OpenRouter/OpenAI/Groq). Твой комп только шлёт запросы и играет аудио.

## Лицензия

MIT
