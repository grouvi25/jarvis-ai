#!/usr/bin/env bash
# Установщик J.A.R.V.I.S. для Linux/macOS.
#
# Использование:
#   curl -fsSL https://raw.githubusercontent.com/grouvi25/jarvis-ai/main/scripts/install.sh | bash
# или:
#   bash scripts/install.sh
#
# Что делает:
#   1. Проверяет наличие Python 3.10+
#   2. Создаёт venv в ~/.local/share/jarvis/venv
#   3. Устанавливает jarvis-ai из репозитория
#   4. Создаёт launcher-скрипт в ~/.local/bin/jarvis-app
#   5. Создаёт .desktop запись (Linux) / запускает мастер настройки

set -euo pipefail

REPO_URL="${JARVIS_REPO:-https://github.com/grouvi25/jarvis-ai}"
INSTALL_DIR="${HOME}/.local/share/jarvis"
VENV_DIR="${INSTALL_DIR}/venv"
BIN_DIR="${HOME}/.local/bin"

info()   { printf '\033[36m▶\033[0m %s\n' "$*"; }
ok()     { printf '\033[32m✓\033[0m %s\n' "$*"; }
err()    { printf '\033[31m✗\033[0m %s\n' "$*" >&2; }
abort()  { err "$*"; exit 1; }

# 1. Python
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    abort "Не найден python3. Установи Python 3.10+ и повтори."
fi
PY_VER=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJ=${PY_VER%%.*}; PY_MIN=${PY_VER##*.}
if [ "$PY_MAJ" -lt 3 ] || { [ "$PY_MAJ" -eq 3 ] && [ "$PY_MIN" -lt 10 ]; }; then
    abort "Нужен Python 3.10+, найден $PY_VER"
fi
ok "Python $PY_VER"

# 2. Каталоги
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# 3. Venv
if [ ! -d "$VENV_DIR" ]; then
    info "Создаю виртуальное окружение в $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip wheel >/dev/null

# 4. Источник
if [ -f "$(dirname "$0")/../pyproject.toml" ]; then
    SRC="$(cd "$(dirname "$0")/.." && pwd)"
    info "Устанавливаю Jarvis (со всеми экстрами) из $SRC"
    pip install -e "$SRC[all]"
else
    info "Клонирую $REPO_URL"
    git -C "$INSTALL_DIR" clone "$REPO_URL" src 2>/dev/null || (cd "$INSTALL_DIR/src" && git pull)
    SRC="$INSTALL_DIR/src"
    pip install -e "$SRC[all]"
fi

# 4b. Playwright Chromium (для browser_action скилла) — один раз
info "Качаю Chromium для Playwright"
if ! python -m playwright install chromium 2>/dev/null; then
    info "Не удалось поставить Chromium — скилл browser_action работать не будет (это ок)"
fi

# 5. Launcher
LAUNCHER="$BIN_DIR/jarvis-app"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/jarvis-app" "\$@"
EOF
chmod +x "$LAUNCHER"

CLI_LAUNCHER="$BIN_DIR/jarvis"
cat > "$CLI_LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/jarvis" "\$@"
EOF
chmod +x "$CLI_LAUNCHER"

ok "Установлено: $LAUNCHER, $CLI_LAUNCHER"

# 6. .desktop entry (Linux)
if [ "$(uname -s)" = "Linux" ]; then
    DESKTOP="${HOME}/.local/share/applications/jarvis.desktop"
    mkdir -p "$(dirname "$DESKTOP")"
    cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Jarvis
Comment=AI ассистент с голосом и чатом
Exec=$LAUNCHER
Terminal=false
Categories=Utility;Network;
EOF
    ok "Ярлык: $DESKTOP"
fi

# 7. Проверка PATH
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo
       echo "⚠️  $BIN_DIR не в PATH. Добавь в ~/.bashrc или ~/.zshrc:"
       echo "    export PATH=\"$BIN_DIR:\$PATH\""
       ;;
esac

echo
ok "Установка завершена."
echo "Запусти мастер настройки:"
echo "    $CLI_LAUNCHER-setup   (или просто запусти jarvis-app — он сам предложит)"
