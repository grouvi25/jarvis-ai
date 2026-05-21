"""Сборка J.A.R.V.I.S. в исполняемый файл через PyInstaller.

Использование:
    python build/build.py            # собрать exe/бинарь
    python build/build.py --installer  # +Inno Setup (только Windows)

Зависимости: `pip install -e .[build]`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "build" / "jarvis.spec"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        sys.exit(res.returncode)


def ensure_icon() -> None:
    """Сгенерировать ICO из SVG, если нет."""
    ico = ROOT / "jarvis" / "assets" / "icon.ico"
    if ico.exists():
        return
    try:
        from PIL import Image, ImageDraw

        for size in (256, 128, 64, 32, 16):
            pass  # placeholder
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([10, 10, 246, 246], fill=(15, 22, 36), outline=(64, 196, 255), width=8)
        try:
            from PIL import ImageFont

            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 160)
        except Exception:
            font = None
        if font is not None:
            d.text((128, 128), "J", fill=(64, 196, 255), font=font, anchor="mm")
        else:
            d.rectangle([100, 80, 160, 200], fill=(64, 196, 255))
        ico.parent.mkdir(parents=True, exist_ok=True)
        img.save(ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        # PNG для Linux/macOS
        img.save(ico.with_suffix(".png"))
        print(f"Сгенерирована иконка: {ico}")
    except Exception as e:
        print(f"Не удалось сгенерировать иконку ({e}); продолжаю без неё")


def build_exe() -> None:
    ensure_icon()
    dist = ROOT / "dist"
    build = ROOT / "build" / "_pyi"
    for d in (dist, build):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--distpath", str(dist),
        "--workpath", str(build),
        str(SPEC),
    ])
    out = dist / ("Jarvis.exe" if os.name == "nt" else "Jarvis")
    print(f"\n✓ Готово: {out}")
    if out.exists():
        size = out.stat().st_size / 1024 / 1024
        print(f"  Размер: {size:.1f} MB")


def build_installer() -> None:
    if os.name != "nt":
        print("Инсталлятор Inno Setup доступен только на Windows. На Linux/macOS — `install.sh`.")
        return
    iss = ROOT / "build" / "installer.iss"
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if not iscc:
        print("Inno Setup не найден в PATH. Установите: https://jrsoftware.org/isinfo.php")
        sys.exit(1)
    run([iscc, str(iss)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--installer", action="store_true",
        help="Также собрать Windows-инсталлятор",
    )
    parser.add_argument(
        "--only-installer", action="store_true",
        help="Только инсталлятор (exe уже собран)",
    )
    args = parser.parse_args()

    if not args.only_installer:
        build_exe()
    if args.installer or args.only_installer:
        build_installer()


if __name__ == "__main__":
    main()
