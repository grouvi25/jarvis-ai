# J.A.R.V.I.S. — Windows installer (PowerShell).
#
# Запуск (от пользователя, без админа):
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   .\scripts\install.ps1
#
# Что делает:
#   1. Проверяет Python 3.10+
#   2. Создаёт venv в %LOCALAPPDATA%\Jarvis\venv
#   3. Устанавливает jarvis-ai
#   4. Создаёт ярлык на рабочем столе и в меню "Пуск"
#   5. По желанию — автозапуск при входе в систему

$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "▶ $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "✓ $msg" -ForegroundColor Green }
function Err($msg)  { Write-Host "✗ $msg" -ForegroundColor Red }

# 1. Python
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) {
    Err "Python не найден. Установи Python 3.10+ с https://www.python.org/downloads/ и поставь галку 'Add to PATH'."
    exit 1
}
$pyver = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$parts = $pyver.Split(".")
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
    Err "Нужен Python 3.10+, найден $pyver"
    exit 1
}
Ok "Python $pyver"

# 2. Каталоги
$Install = Join-Path $env:LOCALAPPDATA "Jarvis"
$Venv = Join-Path $Install "venv"
New-Item -ItemType Directory -Path $Install -Force | Out-Null

# 3. Venv
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
    Info "Создаю venv в $Venv"
    & $python -m venv $Venv
}

$VenvPy  = Join-Path $Venv "Scripts\python.exe"
$VenvPip = Join-Path $Venv "Scripts\pip.exe"
& $VenvPy -m pip install --upgrade pip wheel | Out-Null

# 4. Источник
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $Here
if (Test-Path (Join-Path $RepoRoot "pyproject.toml")) {
    Info "Устанавливаю Jarvis (со всеми экстрами) из $RepoRoot"
    & $VenvPip install -e "$RepoRoot[all]"
    $Src = $RepoRoot
} else {
    Info "Клонирую репозиторий"
    if (-not (Test-Path (Join-Path $Install "src"))) {
        git clone https://github.com/grouvi25/jarvis-ai (Join-Path $Install "src")
    } else {
        Push-Location (Join-Path $Install "src"); git pull; Pop-Location
    }
    $Src = Join-Path $Install "src"
    & $VenvPip install -e "$Src[all]"
}

# 4b. Playwright Chromium (для browser_action скилла)
Info "Качаю Chromium для Playwright (нужно один раз)"
try {
    & $VenvPy -m playwright install chromium
    Ok "Playwright Chromium установлен"
} catch {
    Info "Не удалось поставить Chromium — скилл browser_action не будет работать (это ок)"
}

# 5. Ярлыки
$AppExe = Join-Path $Venv "Scripts\jarvis-app.exe"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Lnk = Join-Path $Desktop "Jarvis.lnk"
$Shell = New-Object -ComObject WScript.Shell
$short = $Shell.CreateShortcut($Lnk)
$short.TargetPath = $AppExe
$short.Description = "J.A.R.V.I.S. AI Assistant"
$short.WorkingDirectory = $Install
$short.Save()
Ok "Ярлык: $Lnk"

# Меню Пуск
$Start = [Environment]::GetFolderPath("Programs")
$LnkStart = Join-Path $Start "Jarvis.lnk"
$shortS = $Shell.CreateShortcut($LnkStart)
$shortS.TargetPath = $AppExe
$shortS.WorkingDirectory = $Install
$shortS.Save()
Ok "В меню Пуск: $LnkStart"

# Автозапуск
$Ans = Read-Host "Запускать Jarvis при входе в систему? [y/N]"
if ($Ans -match '^[yY]') {
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" `
        -Name "Jarvis" -Value "`"$AppExe`""
    Ok "Автозапуск включён"
}

Write-Host ""
Ok "Готово. Запусти 'Jarvis' с рабочего стола или меню Пуск."
Write-Host "Чат: http://127.0.0.1:8765"
