# -*- coding: utf-8 -*-
"""Сборка exe для релиза: один файл «ScreenShoterXX.exe» в папке release/ (в git не попадает).

    python tools/build_exe.py

Нужен PyInstaller (`pip install pyinstaller`). В exe вшиты код, иконка и раскладка настроек
(settings_layout.json); настройки пользователя exe хранит в %APPDATA%\\ScreenshoterXX (см. snipper.pyw).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "release")
WORK = os.path.join(OUT, "_build")
NAME = "ScreenShoterXX"          # латиницей: имя файла для скачивания с GitHub


def main():
    ico = os.path.join(ROOT, "иконка", "icon.ico")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", NAME, "--icon", ico,
           "--add-data", f"{ico}{os.pathsep}иконка",
           "--add-data", f"{os.path.join(ROOT, 'settings_layout.json')}{os.pathsep}.",
           "--distpath", OUT, "--workpath", WORK, "--specpath", WORK,
           os.path.join(ROOT, "snipper.pyw")]
    subprocess.run(cmd, check=True, cwd=ROOT)
    shutil.rmtree(WORK, ignore_errors=True)
    exe = os.path.join(OUT, NAME + ".exe")
    print(f"готово: {exe} ({os.path.getsize(exe) / 1e6:.1f} МБ)")


if __name__ == "__main__":
    main()
