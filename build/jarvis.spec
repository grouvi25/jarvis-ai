# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для сборки J.A.R.V.I.S. в один исполняемый файл.

Использование:
    pyinstaller build/jarvis.spec

Получится `dist/Jarvis.exe` (Windows) / `dist/Jarvis` (Linux/macOS).
"""
from pathlib import Path
import sys

ROOT = Path(SPECPATH).parent

block_cipher = None

# Подтягиваем все ресурсы (web UI + assets + дефолтный config)
datas = [
    (str(ROOT / "jarvis" / "ui" / "web"), "jarvis/ui/web"),
    (str(ROOT / "jarvis" / "assets"), "jarvis/assets"),
    (str(ROOT / "config" / "config.yaml"), "config"),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "pystray._win32" if sys.platform.startswith("win") else (
        "pystray._darwin" if sys.platform == "darwin" else "pystray._xorg"
    ),
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "yaml",
    "edge_tts",
    "rich",
    "rich.logging",
]

a = Analysis(
    [str(ROOT / "jarvis" / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "pytest"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = ROOT / "jarvis" / "assets" / "icon.ico"
icon_arg = str(icon_path) if icon_path.exists() else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Jarvis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,  # GUI-приложение, без окна консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
