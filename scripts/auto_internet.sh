#!/usr/bin/env bash
#
# J.A.R.V.I.S. — Скрипт автоматического переподключения к интернету
#
# Установка:
#   chmod +x scripts/auto_internet.sh
#   # Добавить в cron (каждые 5 минут):
#   crontab -e
#   */5 * * * * /path/to/jarvis-ai/scripts/auto_internet.sh >> /var/log/jarvis_internet.log 2>&1
#
# Или как systemd timer (рекомендуется):
#   sudo cp scripts/jarvis-internet.service /etc/systemd/system/
#   sudo cp scripts/jarvis-internet.timer /etc/systemd/system/
#   sudo systemctl enable --now jarvis-internet.timer

set -euo pipefail

# === НАСТРОЙКИ (измени под свою общагу) ===
PING_HOST="${JARVIS_PING_HOST:-8.8.8.8}"
PING_COUNT=2
PING_TIMEOUT=3

WIFI_SSID="${JARVIS_WIFI_SSID:-}"
WIFI_PASSWORD="${JARVIS_WIFI_PASSWORD:-}"

# Captive portal (авторизация в сети общаги)
CAPTIVE_PORTAL_URL="${JARVIS_CAPTIVE_URL:-}"
CAPTIVE_USERNAME="${JARVIS_CAPTIVE_USER:-}"
CAPTIVE_PASSWORD="${JARVIS_CAPTIVE_PASS:-}"
# ==========================================

LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')] [JARVIS-NET]"

log_info() {
    echo "$LOG_PREFIX INFO: $*"
}

log_warn() {
    echo "$LOG_PREFIX WARN: $*"
}

log_error() {
    echo "$LOG_PREFIX ERROR: $*"
}

check_internet() {
    ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$PING_HOST" > /dev/null 2>&1
}

reconnect_wifi() {
    log_info "Сканирую WiFi сети..."
    nmcli device wifi rescan 2>/dev/null || true
    sleep 2

    if [ -n "$WIFI_SSID" ]; then
        log_info "Подключаюсь к WiFi: $WIFI_SSID"
        if [ -n "$WIFI_PASSWORD" ]; then
            nmcli device wifi connect "$WIFI_SSID" password "$WIFI_PASSWORD" 2>&1 || true
        else
            nmcli device wifi connect "$WIFI_SSID" 2>&1 || true
        fi
    else
        # Пробуем переподключить текущую сеть
        log_info "Перезапускаю NetworkManager..."
        sudo systemctl restart NetworkManager 2>/dev/null || true
    fi

    sleep 5
}

handle_captive_portal() {
    if [ -z "$CAPTIVE_PORTAL_URL" ]; then
        return 0
    fi

    log_info "Авторизуюсь на captive portal: $CAPTIVE_PORTAL_URL"

    local response_code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$CAPTIVE_PORTAL_URL" \
        -d "username=${CAPTIVE_USERNAME}&password=${CAPTIVE_PASSWORD}" \
        -c /tmp/jarvis_portal_cookies \
        --max-time 10 \
        2>/dev/null || echo "000")

    if [ "$response_code" = "200" ] || [ "$response_code" = "302" ]; then
        log_info "Captive portal авторизация успешна (HTTP $response_code)"
    else
        log_warn "Captive portal вернул HTTP $response_code"
    fi
}

# === ОСНОВНОЙ ЦИКЛ ===
main() {
    if check_internet; then
        # Всё ок, молча выходим
        exit 0
    fi

    log_warn "Интернет недоступен! Начинаю переподключение..."

    # Попытка 1: Просто WiFi
    reconnect_wifi

    if check_internet; then
        log_info "Интернет восстановлен после переподключения WiFi"
        exit 0
    fi

    # Попытка 2: Captive portal
    handle_captive_portal
    sleep 3

    if check_internet; then
        log_info "Интернет восстановлен после captive portal"
        exit 0
    fi

    # Попытка 3: Полный перезапуск
    log_warn "Стандартные методы не помогли, перезапускаю сетевой стек..."
    sudo ip link set "$(nmcli -t -f DEVICE,TYPE device | grep wifi | head -1 | cut -d: -f1)" down 2>/dev/null || true
    sleep 2
    sudo ip link set "$(nmcli -t -f DEVICE,TYPE device | grep wifi | head -1 | cut -d: -f1)" up 2>/dev/null || true
    sleep 5

    reconnect_wifi
    handle_captive_portal
    sleep 3

    if check_internet; then
        log_info "Интернет восстановлен после полного перезапуска"
    else
        log_error "Не удалось восстановить интернет после всех попыток"
        exit 1
    fi
}

main "$@"
