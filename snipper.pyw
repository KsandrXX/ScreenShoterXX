# -*- coding: utf-8 -*-
"""
Ножницы XX — аналог «Ножниц» Windows 10 с записью GIF.

Запуск:            pythonw snipper.pyw
Витрина компонентов: python snipper.pyw --showcase
Номера окон (для сообщений о багах): pythonw snipper.pyw --ids — карта номеров в docs/WINDOWS.md
Конструктор настроек: pythonw snipper.pyw --layout — разложить настройки по разделам и группам,
                   поменять тексты (файл settings_layout.json; настройки в нём — временная копия)
Сразу в трей:      pythonw snipper.pyw --tray — окно не показывается, если включён «Значок в трее»
                   (так программу запускает автозапуск Windows; без значка окно показывается как обычно)

Устройство интерфейса и правила расширения — DESIGN.md.
Зависимости: Python 3.8+, Pillow.

Где данные: при запуске из Python — всё рядом с программой. У exe (PyInstaller) — settings.json и logs
в %APPDATA%\\ScreenshoterXX, папки «гифки» и «снимки» — в «Изображения\\Ножницы XX», раскладка
настроек — своя, вшитая в exe. SCREENSHOTER_DATA=папка — другая папка данных и отдельная копия
программы (для проверки exe рядом с запущенной программой).
"""

import os
import sys

FROZEN = getattr(sys, "frozen", False)
APP_DIR = sys._MEIPASS if FROZEN else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
TEST_DATA = os.environ.get("SCREENSHOTER_DATA")


def data_dirs():
    """(data_dir, media_dir, media_root, layout_path) — см. «Где данные» выше; None — рядом с программой.
    media_root — «Изображения»: папка программы в нём называется на языке интерфейса (App)."""
    if TEST_DATA:
        return TEST_DATA, TEST_DATA, None, os.path.join(APP_DIR, "settings_layout.json") if FROZEN else None
    if not FROZEN:
        return None, None, None, None
    import ctypes
    buf = ctypes.create_unicode_buffer(260)
    pics = os.path.join(os.path.expanduser("~"), "Pictures")
    if ctypes.windll.shell32.SHGetFolderPathW(None, 0x27, None, 0, buf) == 0:     # CSIDL_MYPICTURES
        pics = buf.value
    data = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "ScreenshoterXX")
    os.makedirs(data, exist_ok=True)
    return data, None, pics, os.path.join(APP_DIR, "settings_layout.json")


from snip.core.winapi import init_process, single_instance, show_existing, message_box  # noqa: E402

init_process("ScreenshoterXX.Snipper")

if __name__ == "__main__":
    if "--showcase" in sys.argv:
        from snip.app.showcase import run_showcase
        run_showcase(APP_DIR)
    elif "--layout" in sys.argv:                    # конструктор настроек (B23) — рядом с программой
        import json
        import shutil
        import tempfile
        from snip.app.main import App
        from snip.app.layout_store import LayoutStore
        tmp = os.path.join(tempfile.gettempdir(), "ScreenshoterXX-layout")
        os.makedirs(tmp, exist_ok=True)
        sp = os.path.join(tmp, "settings.json")
        try:                                        # копия настроек: переключатели в конструкторе
            shutil.copyfile(os.path.join(APP_DIR, "settings.json"), sp)   # не меняют настоящие
        except OSError:
            open(sp, "w").write("{}")
        try:
            d = json.load(open(sp, encoding="utf-8"))
        except ValueError:
            d = {}
        d.update(clipboard_off=True, copy_on_close=False, gif_temp_dir=os.path.join(tmp, "gif"),
                 gif_dir=os.path.join(tmp, "gif"), settings_page=d.get("settings_page", "capture"))
        json.dump(d, open(sp, "w", encoding="utf-8"), ensure_ascii=False)
        App(APP_DIR, sp, layout_path=os.path.join(APP_DIR, LayoutStore.FILE), layout_edit=True).run()
    elif single_instance("ScreenshoterXX.Snipper.Instance" + (".Test" if TEST_DATA else "")):
        from snip.app.main import App
        if "--ids" in sys.argv:                     # режим проверки: номер на каждом окне (docs/WINDOWS.md)
            from snip.app.winmap import WINDOW_IDS
            from snip.ui import components
            components.WINDOW_IDS = WINDOW_IDS
        data, media, media_root, layout = data_dirs()
        from snip.core.settings import Settings
        Settings.write_first_run(os.path.join(data or APP_DIR, "settings.json"))   # выбор для релиза
        app = App(APP_DIR, hidden="--tray" in sys.argv, data_dir=data, media_dir=media, media_root=media_root,
                  layout_path=layout)
        app.sync_autostart()                        # запись автозапуска: путь верный (папку могли перенести)
        if "--open" in sys.argv[:-1]:               # --open картинка.png — сразу в редактор (для проверок)
            from PIL import Image
            app.load_image(Image.open(sys.argv[sys.argv.index("--open") + 1]))
        app.run()
    elif "--tray" in sys.argv:                      # автозапуск, а программа уже открыта — ничего не делать
        pass
    else:
        # вторая копия: настройки не читаются — сообщения на языке Windows
        from snip.core import i18n
        from snip.core.i18n import tr
        from snip.app.main import APP_NAME
        i18n.set_lang(i18n.system_lang())
        if "--ids" in sys.argv:                     # уже открытая копия — без номеров, её не подменить
            message_box(tr(APP_NAME), tr("Программа уже запущена без номеров окон. Закройте её и запустите "
                                         "«Номера окон» снова."))
        elif not show_existing((APP_NAME, i18n.EN[APP_NAME]), skip=("витрина", "конструктор")):
            # окно первой копии скрыто: идёт снимок или запись GIF
            message_box(tr(APP_NAME), tr("Программа уже запущена: сейчас идёт снимок или запись GIF."))
