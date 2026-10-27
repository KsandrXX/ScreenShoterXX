# -*- coding: utf-8 -*-
"""
СЛОЙ 1 — ТОКЕНЫ.

Единственное место в программе, где записаны цвета, размеры, шрифты,
прозрачности, слои и тайминги. Всё остальное обращается к ним по имени
через объект Theme (th.c("accent"), th.px(8), th.sp(2), th.font("body")).

Размеры заданы в пикселях при масштабе 100 % и умножаются на th.scale.
"""

import tkinter.font as tkfont

# --------------------------------------------------------------------------
# Типографика: один шрифт, 4 размера, 2 начертания
# --------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"          # системный шрифт Windows 10
TYPE = {                          # роль: (размер px, межстрочный интервал px)
    "caption": (12, 16),
    "body": (14, 20),
    "title": (16, 22),
    "headline": (20, 28),
}
WEIGHT = {"regular": "normal", "strong": "bold"}

# --------------------------------------------------------------------------
# Сетка: базовая единица 4 px
# --------------------------------------------------------------------------
SPACE = {0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32}
RADIUS = {"none": 0, "sm": 4, "md": 8, "lg": 12}
SIZE = {
    "control_sm": 28,        # высота компактных контролов (тулбар, строки)
    "control": 32,           # стандартная высота контрола
    "control_lg": 40,        # крупные (основные действия пустого состояния)
    "icon_sm": 16,
    "title_icon": 21,        # значок в конце названия настройки («Показывать курсор»)
    "title_icon_lift": 0,    # …подъём над серединой строки (0 — рисунок без полей уже по центру букв)
    "icon": 20,
    "icon_lg": 40,
    "border": 1,
    "focus": 2,              # толщина кольца фокуса
    "toggle_w": 36,
    "toggle_h": 20,
    "check": 16,
    "slider_track": 4,
    "slider_thumb": 14,
    "scrollbar": 10,
    "drag_gap_max": 72,      # конструктор: высота щели «Сюда» (не выше блока)
    "drag_ghost_off": 14,    # конструктор: карточка перетаскиваемого блока — от курсора
    "swatch": 18,
    "swatch_lg": 28,
    "field_chars": 4,        # ширина короткого числового поля, символов (не масштабируется)
    "field_chars_hex": 8,
    "field_w": 240,          # ширина поля ввода по умолчанию
    "select_w": 160,
    "hotkey_w": 180,
    "tooltip_max_w": 320,
    "tooltip_pad": (10, 6),  # отступы подсказки по горизонтали и вертикали
    "tooltip_hotkey_gap": 16,   # от названия до клавиши в строке названия (= sp(4))
    "tip_sample": (150, 26), # образец линии в подсказке размера (T3)
    "tip_checker": 10,       # клетка шахматного фона образца
    "toast_w": 340,
    "dialog_min_w": 360,
    "settings_nav_w": 200,
    "settings_narrow": 640,  # уже этого — категории настроек становятся вкладками
    "row_min_w": 520,
    "picker_field": 256,     # поле цвета в палитре
    "picker_bar": 20,
    "picker_preview": (72, 34),
    "loupe": 132,            # лупа пипетки, px
    "rec_border": 2,         # рамка записываемой области
    "selection_border": 1,   # рамка выделения на оверлее
    "app_icon": 64,
    "settings_window": (780, 560),   # размер окна, когда настройки открыты из пустого состояния
    "value_slider_w": 172,   # ползунок в окошке значения (с полем под кольцо): окошко ≈ 268 при 100 %
    "value_pad": (16, 14, 12),   # окошко значения: отступ по бокам, сверху, снизу
    "value_chip_h": 24,      # плашка быстрого значения
    "value_chip_gap": 6,     # между плашками
    "value_row_gap": 12,     # от ряда плашек до строки «− ползунок +»
    "edit_h": 26,            # поле правки числа на месте (кнопка, заголовок, плашка) и его подсветка
    "keycap_h": 22,          # высота плашки клавиши (KeyCap)
    "keys_row_gap": 2,       # отступ над и под строкой в окне «Все клавиши» (строки плотные, как в макете)
    "modal_max_w": 760,      # предел ширины модальной карточки в большом окне
}

# Курсоры инструментов: чёрный значок с белой обводкой — виден на любом фоне
CURSOR = {"ink": "#000000", "halo_color": "#ffffff", "halo": 1.0}

# Тень модальной карточки (рисуется в слое затемнения, где фон известен): размытие, сдвиг вниз,
# непрозрачность. Других теней в интерфейсе нет.
SHADOW = {"blur": 18, "offset": 8, "alpha": 0.32}

# Физические крайние цвета — для расчёта худшего фона под стеклом
EXTREMES = {"white": "#ffffff", "black": "#000000"}

# Технические значения (не видны пользователю как цвет)
TECH = {
    "transparent_key": "#010203",    # цвет-ключ прозрачности окна-рамки записи
}

# Правила раскладки (используются шаблонами и реестром)
LAYOUT = {
    "toolbar_max_visible": 11,    # не больше N элементов на видимом уровне (левые группы)
    "min_visible_priority": 3,    # приоритет ниже — сразу во «Ещё»
    "list_visible_rows": 8,       # строк в выпадающем списке до прокрутки
    "toast_stack": 3,
    "loupe_cells": 11,            # сколько пикселей экрана видно в лупе (нечётное)
    "zoom_min": 0.1,              # масштаб редактора
    "zoom_max": 16.0,
    "zoom_step": 1.1,             # шаг колёсика (одно «деление» = +10 %), переход анимирован
    "zoom_pixel": 2.0,            # от этого масштаба пиксели показываются чёткими квадратами
    "zoom_reduce_gap": 3.0,       # мелкий масштаб: грубое предуменьшение перед сглаживанием (PIL reducing_gap)
    "popup_reopen_ms": 400,       # повторный клик по кнопке списка в этот срок — закрыть, а не открыть
    "window_fill": 0.92,          # доля монитора, которую может занять окно со снимком
    "modal_fill": 0.88,           # ширина модальной карточки — доля ширины окна (не уже содержимого)
}

# --------------------------------------------------------------------------
# Глубина: единая шкала слоёв
# --------------------------------------------------------------------------
LAYER = {
    "base": 0,      # фон окна (bg)
    "panel": 1,     # панели (surface)
    "raised": 2,    # карточки, поля, кнопки (surface-raised / control)
    "popup": 3,     # подсказки, списки, меню — отдельное окно поверх
    "modal": 4,     # диалоги — модальное окно
    "overlay": 5,   # оверлей захвата — поверх всего экрана
}

# --------------------------------------------------------------------------
# Движение: по умолчанию без анимации
# --------------------------------------------------------------------------
MOTION = {"instant": 0, "fast": 120}
TIMING = {
    "tooltip_delay": 500,
    "toast_life": 4000,
    "blink": 500,          # мигание индикатора записи
    "spinner_step": 120,   # кадр индикатора загрузки (= MOTION fast)
    "poll": 100,
    "hotkey_poll": 250,    # запасной опрос глобальных клавиш (основной путь — событие из потока)
    "hotkey_poll_tray": 2000,   # то же, пока окно в трее: нагрузки в фоне почти нет
    "hide_anim": 250,
    "dwm_settle": 50,      # пауза, чтобы DWM применил смену атрибутов окна (без блокировки)      # анимация скрытия окна Windows (старые версии без исключения из захвата)
    "frame": 16,           # кадр функциональной анимации (плавный зум), ~60 к/с
    "drag_gap": 140,       # конструктор: щель «Сюда» раздвигает блоки
    "drop_flash": 900,     # конструктор: блок на новом месте вспыхивает и гаснет
    "hold": 400,           # удержание кнопки дольше этого — второе действие (меню режимов)
    "repeat_delay": 400,   # − / + в окошке значения: удержание — повтор после этой паузы…
    "repeat_every": 60,    # …и дальше каждые N мс
}

# --------------------------------------------------------------------------
# Стекло / HUD
# --------------------------------------------------------------------------
GLASS = {
    "fill_alpha": 0.72,     # непрозрачность тонировки поверх фона
    "border_alpha": 0.16,   # непрозрачность светлой/тёмной границы
    "blur": 14,             # радиус размытия фона, px (только где фон известен)
    "radius": "lg",
    "window_alpha": 0.94,   # прозрачность HUD-окна (панель записи)
    "scrim_alpha": 0.45,    # затемнение экрана на оверлее захвата
    # модальное окно: затемнение страницы (светлее, чем у оверлея захвата) и полупрозрачная
    # карточка — страница сквозь неё бледно видна; текст ≥ AA на крайних фонах (проверяет verify_ui)
    "modal_scrim": 0.32,
    "modal_alpha": {"dark": 0.95, "light": 0.94},   # плотная: страница лишь угадывается, текст читается
}

# --------------------------------------------------------------------------
# Цвета: семантические токены, тёмная и светлая тема
# --------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#0b0c0e",
        "surface": "#131518",
        "surface-raised": "#1b1e22",
        "overlay": "#000000",          # цвет затемнения (с GLASS.scrim_alpha)
        "canvas": "#08090a",           # фон под изображением в редакторе
        "border": "#2a2e34",
        "border-strong": "#3b4048",
        "control": "#202328",
        "control-hover": "#2a2e34",
        "control-pressed": "#33383f",
        "text-primary": "#f3f4f6",
        "text-secondary": "#a8afb9",
        "text-disabled": "#5f656e",
        "success": "#4ade80",
        "warning": "#facc15",
        "danger": "#dc2626",           # заливка опасного действия
        "danger-hover": "#b91c1c",
        "danger-fg": "#f87171",        # опасность как текст/иконка
        "text-on-danger": "#ffffff",
        "glass-tint": "#0b0c0e",
        "glass-border": "#ffffff",
        "scrollbar": "#3b4048",
    },
    "light": {
        "bg": "#eef0f3",
        "surface": "#f7f8fa",
        "surface-raised": "#ffffff",
        "overlay": "#000000",
        "canvas": "#dfe3e8",
        "border": "#d9dde3",
        "border-strong": "#b8bec7",
        "control": "#ffffff",
        "control-hover": "#eceff3",
        "control-pressed": "#e1e5ea",
        "text-primary": "#0d0f12",
        "text-secondary": "#4a525e",
        "text-disabled": "#a3a9b2",
        "success": "#15803d",
        "warning": "#a16207",
        "danger": "#c81e1e",
        "danger-hover": "#a51818",
        "danger-fg": "#b91c1c",
        "text-on-danger": "#ffffff",
        "glass-tint": "#ffffff",
        "glass-border": "#000000",
        "scrollbar": "#b8bec7",
    },
}

# Акцент — единственный «цветной» цвет интерфейса. Набор значений на тему.
ACCENTS = {
    "lime": {   # из иконки программы
        "dark": {"accent": "#c5f03c", "accent-hover": "#d4f76a", "accent-pressed": "#aed62a",
                 "accent-fg": "#c5f03c", "accent-soft": "#2b3313", "text-on-accent": "#0b0c0e",
                 "focus-ring": "#c5f03c", "icon-on": "#c5f03c"},
        "light": {"accent": "#c5f03c", "accent-hover": "#b4e021", "accent-pressed": "#a2cc12",
                  "accent-fg": "#4f6b00", "accent-soft": "#eef9cf", "text-on-accent": "#0d0f12",
                  "focus-ring": "#4f6b00", "icon-on": "#5f8f00"},   # icon-on — включённый значок-переключатель
    },
}

# Линейные иконки: толщина штриха на сетке 24×24
ICON = {
    "stroke": 1.75,       # обычный штрих всех иконок
    "stroke_on": 2.0,     # включённый значок-переключатель (IconToggle) — чуть толще
}

THEME_NAMES = {"dark": "Тёмная", "light": "Светлая"}
# Системный заголовок окна (рамка Windows) для каждой темы: "dark" | "light"
TITLEBAR = {"dark": "dark", "light": "light"}
ACCENT_NAMES = {"lime": "Лайм"}

# Цвета СОДЕРЖИМОГО (пометки на снимке) — не интерфейс, но тоже только здесь
ANNOTATION = {
    # цвета, размеры и образцы по умолчанию — как настроил пользователь для релиза V1.00
    "pen": "#ffe600",
    "marker": "#afc850",
    "freeform_bg": "#ffffff",     # фон за пределами «произвольной формы»
    "outside_bg": "#ffffff",      # фон под снимком при сохранении (картинка размером со снимок — не виден)
    "marker_alpha": 0.45,
    # размеры (диаметр, px снимка) и непрозрачность (%) инструментов по умолчанию
    "pen_size": 3,
    "pen_opacity": 100,
    "marker_size": 24,
    "marker_opacity": 100,
    "eraser_size": 16,
    "swatches": ["#2a5360", "#afc850", "#ffe600", "#ffffff", "#f35e5e"],   # образцы в палитре
}

# Пары «текст / фон», которые обязаны проходить WCAG AA (проверяет тест)
CONTRAST_PAIRS = [
    ("text-primary", "bg"), ("text-primary", "surface"), ("text-primary", "surface-raised"),
    ("text-primary", "control-hover"), ("text-primary", "control-pressed"),
    ("text-secondary", "bg"), ("text-secondary", "surface"), ("text-secondary", "surface-raised"),
    ("text-secondary", "control"),
    ("text-on-accent", "accent"), ("text-on-accent", "accent-hover"),
    ("text-on-accent", "accent-pressed"),
    ("accent-fg", "surface"), ("accent-fg", "surface-raised"), ("accent-fg", "accent-soft"),
    ("text-primary", "accent-soft"),
    ("text-on-danger", "danger"), ("text-on-danger", "danger-hover"),
    ("danger-fg", "surface"), ("danger-fg", "surface-raised"),
    ("success", "surface-raised"), ("warning", "surface-raised"),
]
AA = 4.5
# Графические объекты (иконки без подписи-текста рядом): WCAG 1.4.11 — не меньше 3 : 1 к фону
GRAPHIC = 3.0
GRAPHIC_PAIRS = [("icon-on", "surface"), ("icon-on", "bg")]


class Theme:
    """Набор значений токенов для темы + акцента + масштаба."""

    def __init__(self, name="dark", accent="lime", scale=1.0):
        self.name = name if name in THEMES else "dark"
        self.accent = accent if accent in ACCENTS else "lime"
        self.scale = max(0.75, float(scale))
        self.colors = dict(THEMES[self.name])
        self.colors.update(ACCENTS[self.accent][self.name])
        self._fonts = {}

    # --- цвета ---
    def c(self, token):
        return self.colors[token]

    # --- размеры ---
    def px(self, value):
        """Пиксели с учётом масштаба. Только для значений из токенов."""
        return max(1, int(round(value * self.scale))) if value else 0

    def sp(self, step):
        return self.px(SPACE[step])

    def r(self, name):
        return self.px(RADIUS[name])

    def size(self, name):
        v = SIZE[name]
        return tuple(self.px(x) for x in v) if isinstance(v, tuple) else self.px(v)

    def line(self, role):
        return self.px(TYPE[role][1])

    # --- шрифты ---
    def font(self, role="body", weight="regular"):
        key = (role, weight)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(family=FONT_FAMILY, size=-self.px(TYPE[role][0]),
                                           weight=WEIGHT[weight])
        return self._fonts[key]

    def measure(self, text, role="body", weight="regular"):
        return self.font(role, weight).measure(text)

    # --- прочее ---
    @property
    def dark_titlebar(self):
        return TITLEBAR[self.name] == "dark"

    @staticmethod
    def timing(name):
        return TIMING[name]

    @staticmethod
    def motion(name):
        return MOTION[name]

    @staticmethod
    def layout(name):
        return LAYOUT[name]

    @staticmethod
    def glass(name):
        return GLASS[name]

    @staticmethod
    def icon_stroke(name):
        return ICON[name]

    @staticmethod
    def shadow(name):
        return SHADOW[name]

    @staticmethod
    def tech(name):
        return TECH[name]
