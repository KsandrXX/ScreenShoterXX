# -*- coding: utf-8 -*-
"""Настройки пользователя (settings.json рядом с программой) и нумерация GIF."""

import json
import os
import re
import tempfile

from ..ui.tokens import ANNOTATION
from .i18n import tr


class Settings:
    DEFAULTS = {
        "mode": "rect",
        "delay": 0,               # устарело: задержки снимка больше нет в интерфейсе; ключ не трогаем
        "gif_limit": 0,           # длительность записи GIF, с; 0 — без лимита
        "fps": 15,
        "gif_scale": 100,
        "gif_cursor": True,
        "gif_dir": "",            # пусто = папка «гифки» рядом с программой
        "gif_counter": 0,
        "gif_save": False,        # GIF в папку gif_dir; выключено — только в буфер (временный файл, B17)
        "gif_temp_dir": "",       # пусто = системная Temp/ScreenshoterXX-GIF (тесты задают свою)
        # снимок всегда кладётся в буфер обмена; в папку — по snip_save (как GIF)
        "snip_save": False,
        "snip_dir": "",           # пусто = папка «снимки» рядом с программой
        "snip_counter": 0,
        "clipboard_off": False,   # СКРЫТАЯ, только для тестов: снимок не трогает буфер обмена пользователя
        # True — при закрытии / новом снимке пометки молча копируются в буфер; False — вопрос
        # «Сохранить?» (в окне — переключатель «Защита от случайного закрытия», наоборот)
        "copy_on_close": True,
        # снимок/GIF по глобальной клавише — не показывать окно программы (в окне — наоборот:
        # «Показывать окно редактора после быстрых действий»)
        "hotkey_silent": False,
        "last_dir": os.path.join(os.path.expanduser("~"), "Pictures"),
        "pen_color": ANNOTATION["pen"],
        "marker_color": ANNOTATION["marker"],
        # у каждого инструмента свои размер (px снимка) и непрозрачность (%)
        "pen_size": ANNOTATION["pen_size"],
        "pen_opacity": ANNOTATION["pen_opacity"],
        "marker_size": ANNOTATION["marker_size"],
        "marker_opacity": ANNOTATION["marker_opacity"],
        "eraser_size": ANNOTATION["eraser_size"],
        "eraser_mode": "brush",   # brush — стирает область (по умолчанию), stroke — объект целиком
        # устарели: pen_width (до общего размера) и tool_size (общий размер) — переносятся ниже
        "swatches": list(ANNOTATION["swatches"]),
        "theme": "light",
        "lang": "",                   # язык (B26): "" — как в Windows (русская — "ru", любая другая — "en")
        "accent": "lime",
        "ui_scale": "auto",
        "titlebar": "theme",      # theme — заголовок окна под тему, light — всегда светлый
        # глобальные сочетания по умолчанию НЕ назначены (B18): программа не занимает чужие клавиши.
        # PrintScreen на «Весь экран» ставится только при первом запуске (FIRST_RUN).
        # "" в settings.json — «очищено пользователем» и так и остаётся (не значение по умолчанию)
        "hk_snip": "",
        "hk_gif": "",
        "hk_full": "",
        # работа в фоне (B19): закрытие окна прячет его в трей; автозапуск — только при значке в трее
        "tray": False,
        "autostart": False,
        "settings_page": "capture",
        # свои быстрые значения окошек («плашки», меняются двойным кликом прямо в окошке):
        # {"gif_limit": [...], "size": [...], "opacity": [...]}; нет ключа — значения по умолчанию
        "quick_values": {"gif_limit": [0, 1, 3, 5]},
    }
    # Выбор пользователя для релиза V1.00, который трогает Windows (значок в трее, PrintScreen) —
    # пишется в settings.json только при ПЕРВОМ запуске настоящей программы (snipper.pyw, файла
    # настроек ещё нет). Не в DEFAULTS: тесты создают App на пустых временных настройках и иначе
    # занимали бы PrintScreen и ставили значок в трей рядом с программой пользователя.
    FIRST_RUN = {
        "tray": True,
        "hk_full": "Print",
        "hotkey_silent": True,    # после клавиши окно редактора не показывается
    }

    @classmethod
    def write_first_run(cls, path):
        """Первый запуск (файла настроек нет): записать FIRST_RUN. Файл есть — ничего не делать."""
        if os.path.exists(path):
            return False
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cls.FIRST_RUN, f, ensure_ascii=False, indent=2)
        except OSError:
            return False
        return True

    def __init__(self, path, app_dir):
        self.path = path
        self.app_dir = app_dir                # папки «гифки» и «снимки» по умолчанию — здесь
        self.data = dict(self.DEFAULTS)
        # f(key, value) после каждой смены: одна настройка бывает в нескольких местах окна
        # (курсор GIF — кнопка на панели и строка настроек) — все её контролы обновляются сразу
        self.listeners = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.data.update(loaded)
            if "pen_size" not in loaded:     # первый запуск со своими размерами у инструментов
                if "tool_size" in loaded:      # был общий размер — он и есть текущий у всех трёх
                    for k in ("pen_size", "marker_size", "eraser_size"):
                        self.data[k] = loaded["tool_size"]
                elif "pen_width" in loaded:    # ещё раньше: толщина пера
                    self.data["pen_size"] = loaded["pen_width"]
        except Exception:
            pass

    def get(self, key):
        return self.data.get(key, self.DEFAULTS.get(key))

    def set(self, key, value, save=True):
        self.data[key] = value
        if save:
            self.save()
        for f in list(self.listeners):
            try:
                f(key, value)
            except Exception:
                pass                  # окно уже закрыто и т. п. — сама настройка сохранена

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # --- GIF ---
    GIF_NAME_RE = re.compile(r"^(?:Гифка|GIF)_(\d+)_", re.IGNORECASE)   # номер — у файлов на любом языке

    def default_gif_dir(self):
        return os.path.join(self.app_dir, tr("гифки"))

    def gif_dir(self):
        return self.get("gif_dir") or self.default_gif_dir()

    def gif_temp_dir(self):
        """Временная папка GIF «только в буфер»: там лежит только последняя запись."""
        return self.get("gif_temp_dir") or os.path.join(tempfile.gettempdir(), "ScreenshoterXX-GIF")

    def clean_gif_temp(self, keep=None):
        """Удалить временные GIF (кроме keep). При запуске программы и перед новой записью."""
        d = self.gif_temp_dir()
        try:
            names = os.listdir(d)
        except OSError:
            return
        for name in names:
            p = os.path.join(d, name)
            if name.lower().endswith(".gif") and p != keep:
                try:
                    os.remove(p)
                except OSError:
                    pass

    # --- снимки (как GIF) ---
    SNIP_NAME_RE = re.compile(r"^(?:Снимок|Screenshot)_(\d+)_", re.IGNORECASE)

    def default_snip_dir(self):
        return os.path.join(self.app_dir, tr("снимки"))

    @staticmethod
    def file_name(kind, num, ext, when=None):
        """Имя файла снимка / GIF на языке интерфейса: «Снимок_0001_дата_время.png» / «Screenshot_0001_…».
        when=None — образец для настроек («дата_время»)."""
        stamp = when.strftime("%Y-%m-%d_%H-%M-%S") if when else tr("дата_время")
        return f"{tr(kind)}_{num:04d}_{stamp}.{ext}"

    def snip_dir(self):
        return self.get("snip_dir") or self.default_snip_dir()

    def next_snip_number(self):
        """Больше счётчика и любого номера, уже лежащего в папке."""
        n = int(self.get("snip_counter") or 0)
        try:
            for name in os.listdir(self.snip_dir()):
                m = self.SNIP_NAME_RE.match(name)
                if m:
                    n = max(n, int(m.group(1)))
        except OSError:
            pass
        return n + 1

    def next_gif_number(self):
        """Больше счётчика и любого номера, уже лежащего в папке."""
        n = int(self.get("gif_counter") or 0)
        try:
            for name in os.listdir(self.gif_dir()):
                m = self.GIF_NAME_RE.match(name)
                if m:
                    n = max(n, int(m.group(1)))
        except OSError:
            pass
        return n + 1
