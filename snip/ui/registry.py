# -*- coding: utf-8 -*-
"""
СЛОЙ 4 — РЕЕСТР.

Единая точка регистрации. Функция программы описывается записью, а шаблоны
(layouts) сами решают, где и как её показать:

    reg.action("snip", "Создать", icon="snip", surface="header", group="capture",
               freq=3, value=3, hotkey="Ctrl+N", kind="primary", handler=app.new_snip)

    reg.setting("gif_fps", "Кадров в секунду", page="gif", kind="select",
                options=[(10, "10"), (15, "15")])

    reg.page("gif", "Запись GIF", icon="film", order=20)

Приоритет = freq (частота, 1–3) × value (полезность, 1–3) = 1…9.
Внутри поверхности элементы идут по порядку групп, внутри группы — по
приоритету (выше — левее/выше). Элементы с приоритетом ниже
LAYOUT.min_visible_priority и всё, что не влезло по ширине или сверх
LAYOUT.toolbar_max_visible, уходит в меню «Ещё» — первыми уходят самые
низкоприоритетные.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..core.i18n import tr


@dataclass
class Action:
    id: str
    title: str
    icon: Optional[str] = None
    surface: str = "header"          # header | editor | rec | overlay | empty
    group: str = "main"
    freq: int = 2                    # 1 редко · 2 иногда · 3 постоянно
    value: int = 2                   # 1 мало пользы · 2 средне · 3 ключевое
    kind: str = "button"             # button | primary | danger | icon | select | tool | color | number | toggle
    handler: Optional[Callable] = None
    hotkey: Optional[str] = None     # локальная клавиша, вид "Ctrl+N", "P", "Escape"
    alt_hotkeys: tuple = ()          # дополнительные сочетания того же действия ("Ctrl+Shift+Z")
    tooltip: Any = None              # пояснение под названием в подсказке: строка или () -> строка
    tip_sample: Optional[Callable] = None   # образец линии в подсказке: () -> {"width","color","alpha"} или None
    options: Any = None              # select: [(value, text, icon?)] или callable() -> list; toggle: (слово «выкл», «вкл»)
    custom: Optional[dict] = None    # select: своё число {"lo", "hi", "fmt": "{} с"} — строка «Своё значение…»
    number: Optional[dict] = None    # number: поле с ползунком {"lo","hi","step","min","max","fmt","special"}
    get: Optional[Callable] = None   # select / tool / color: текущее значение
    set: Optional[Callable] = None   # select / color: установить значение
    enabled: Callable = lambda: True
    visible: Callable = lambda: True
    show_label: bool = True          # подпись рядом с иконкой на видимом уровне
    label: Optional[Callable] = None # динамическая подпись: () -> (текст, иконка)
    label_variants: tuple = ()       # все варианты подписи — кнопка сразу резервирует ширину под самый длинный
    also: tuple = ()                 # дополнительные поверхности (например "empty")
    hold: Optional[Callable] = None  # удержание кнопки (TIMING.hold): hold(widget) — например, меню режимов
    keys: Optional[str] = None       # группа в окне «Все клавиши»; по умолчанию — группы панели (Group.keys)
    key: Optional[Callable] = None   # своя обработка горячей клавиши: key(hotkey) вместо set/handler
    order: int = 0

    @property
    def priority(self):
        return self.freq * self.value


@dataclass
class Group:
    id: str
    surface: str
    order: int = 0
    align: str = "left"              # left | right (правая группа — системные действия)
    keys: Optional[str] = None       # группа в окне «Все клавиши» для клавиш её действий


@dataclass
class Page:
    id: str
    title: str
    icon: str = "settings"
    order: int = 0


@dataclass
class Setting:
    key: str
    title: str
    page: str
    kind: str = "toggle"             # toggle | select | slider | path | hotkey | color | info | shortcuts
    description: Optional[str] = None
    default: Any = None              # значение, пока пользователь его не менял
    options: Any = None              # select: [(value, text)] или callable
    lo: float = 0
    hi: float = 100
    step: float = 1
    section: Optional[str] = None
    order: int = 0
    on_change: Optional[Callable] = None
    text: Optional[Callable] = None  # info: callable() -> текст
    extra: dict = field(default_factory=dict)  # параметры конкретного вида (path: on_browse...)


class Registry:
    # Порядок групп в окне «Все клавиши»; другие названия — после них, «Прочее» — в конце
    KEY_GROUPS = ("Общие", "Файл", "Правка", "Инструменты", "Вид")
    KEY_OTHER = "Прочее"

    def __init__(self):
        self.actions = {}
        self.groups = {}
        self.pages = {}
        self.settings = {}

    # --- регистрация ---
    def group(self, id, surface, order=0, align="left", keys=None):
        self.groups[(surface, id)] = Group(id, surface, order, align, keys)

    def action(self, id, title, **kw):
        a = Action(id, title, **kw)
        if (a.surface, a.group) not in self.groups:
            self.group(a.group, a.surface, order=len(self.groups) * 10)
        self.actions[id] = a
        return a

    def page(self, id, title, icon="settings", order=0):
        self.pages[id] = Page(id, title, icon, order)

    def setting(self, key, title, page, **kw):
        self.settings[key] = Setting(key, title, page, **kw)
        return self.settings[key]

    def remove(self, id):
        """Удалить действие / настройку / страницу по идентификатору."""
        self.actions.pop(id, None)
        self.settings.pop(id, None)
        self.pages.pop(id, None)

    # --- выборки для шаблонов ---
    def for_surface(self, surface):
        """[(Group, [Action...]), ...] в порядке групп; действия — по приоритету."""
        out = []
        groups = sorted((g for (s, _), g in self.groups.items() if s == surface),
                        key=lambda g: (g.align == "right", g.order))
        for g in groups:
            acts = [a for a in self.actions.values()
                    if a.surface == surface and a.group == g.id and a.visible()]
            acts.sort(key=lambda a: (-a.priority, a.order))
            if acts:
                out.append((g, acts))
        return out

    def list_for(self, surface):
        """Плоский список для поверхностей без групп (пустое состояние)."""
        acts = [a for a in self.actions.values()
                if (a.surface == surface or surface in a.also) and a.visible()]
        return sorted(acts, key=lambda a: (-a.priority, a.order))

    def page_list(self):
        return sorted(self.pages.values(), key=lambda p: p.order)

    def settings_for(self, page):
        items = [s for s in self.settings.values() if s.page == page]
        return sorted(items, key=lambda s: s.order)

    def shortcuts(self):
        """Все локальные горячие клавиши — для страницы настроек и подсказок."""
        return [(" / ".join(human_key(k) for k in (a.hotkey,) + tuple(a.alt_hotkeys)), a.title, a.surface)
                for a in self.actions.values() if a.hotkey]

    def key_group(self, a):
        """Группа действия в окне «Все клавиши»: своя (Action.keys), иначе группы панели, иначе «Прочее»."""
        g = self.groups.get((a.surface, a.group))
        return a.keys or (g.keys if g else None) or self.KEY_OTHER

    def shortcut_groups(self):
        """[(группа, [(название, [сочетание, альтернатива…])])] — для окна «Все клавиши».
        Собирается из реестра: новая клавиша сама попадает в свою группу."""
        groups = {}
        for a in self.actions.values():
            if a.hotkey:
                keys = [human_key(k) for k in (a.hotkey,) + tuple(a.alt_hotkeys)]
                groups.setdefault(self.key_group(a), []).append((a.title, keys))
        order = list(self.KEY_GROUPS) + sorted(g for g in groups if g not in self.KEY_GROUPS
                                               and g != self.KEY_OTHER) + [self.KEY_OTHER]
        return [(tr(g), groups[g]) for g in order if g in groups]    # группы — по-русски внутри

    # --- горячие клавиши ---
    def bind_hotkeys(self, root, active_surfaces):
        """Привязать локальные клавиши действий к окну. active_surfaces() -> множество
        поверхностей, которые сейчас на экране (клавиша работает только для них)."""
        for a in self.actions.values():
            if not a.hotkey:
                continue
            for hk in (a.hotkey,) + tuple(a.alt_hotkeys):
                for seq in tk_sequences(hk):
                    root.bind(seq, lambda e, a=a, hk=hk: _fire(e, a, active_surfaces, hk), add="+")


TEXT_EDIT_KEYS = {"Ctrl+C", "Ctrl+X", "Ctrl+V", "Ctrl+Z", "Ctrl+Y", "Ctrl+Shift+Z", "Ctrl+A"}


def _fire(event, action, active_surfaces, hotkey=None):
    from .components import is_text_input
    hotkey = hotkey or action.hotkey
    plain = "+" not in hotkey or hotkey.startswith("Shift+")
    if (plain or hotkey in TEXT_EDIT_KEYS) and is_text_input(event.widget):
        return None   # в поле ввода клавиши принадлежат полю
    if action.surface not in active_surfaces():
        return None
    if not (action.visible() and action.enabled()):
        return None
    if action.key:
        action.key(hotkey)
    elif action.kind == "tool" and action.set:
        action.set(action.id)
    elif action.handler:
        action.handler()
    return "break"


_TK_MODS = {"Ctrl": "Control", "Alt": "Alt", "Shift": "Shift"}
_TK_KEYS = {",": "comma", ".": "period", "/": "slash", ";": "semicolon", "-": "minus", "=": "equal"}


_HUMAN_KEYS = {"space": "Пробел", "Return": "Enter", "Escape": "Esc"}


def human_key(hotkey):
    """Подпись клавиши для людей: "space" -> "Пробел", "Ctrl+Return" -> "Ctrl+Enter"."""
    parts = hotkey.split("+")
    parts[-1] = tr(_HUMAN_KEYS.get(parts[-1], parts[-1]))
    return "+".join(parts)


def tk_sequences(hotkey):
    """"Ctrl+Shift+S" -> ["<Control-Shift-KeyPress-s>", "<Control-Shift-KeyPress-S>"]."""
    parts = hotkey.split("+")
    key = _TK_KEYS.get(parts[-1], parts[-1])
    mods = "".join(_TK_MODS[p] + "-" for p in parts[:-1])
    if len(key) == 1 and key.isalpha():
        return [f"<{mods}KeyPress-{key.lower()}>", f"<{mods}KeyPress-{key.upper()}>"]
    return [f"<{mods}KeyPress-{key}>"]
