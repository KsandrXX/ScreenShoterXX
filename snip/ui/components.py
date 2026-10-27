# -*- coding: utf-8 -*-
"""
СЛОЙ 2 — БАЗОВЫЕ КОМПОНЕНТЫ.

Каждый компонент — один класс; внешний вид берётся только из токенов темы
(th), состояния общие для всех:
    normal · hover · pressed · focus · disabled · error · selected · loading
Все интерактивные компоненты доступны с клавиатуры (Tab — фокус,
Space/Enter — действие, стрелки — где уместно) и принимают tooltip.

Параметр force={"hover", "pressed", "focus"} фиксирует состояние —
используется витриной (showcase) для показа всех состояний.
"""

import tkinter as tk
from decimal import ROUND_HALF_UP, Decimal

from ..core.i18n import tr
from . import paint
from .icons import icon as get_icon, icon_tight

TONES = {
    "primary": "text-primary", "secondary": "text-secondary", "disabled": "text-disabled",
    "accent": "accent-fg", "danger": "danger-fg", "success": "success", "warning": "warning",
    "on-accent": "text-on-accent",
}


def parent_bg(parent):
    try:
        return parent.cget("bg")
    except tk.TclError:
        return parent.cget("background")


def within(widget, parent):
    """Виджет — это parent или лежит внутри него. По границе имени: «.a.numberfield2» НЕ внутри
    «.a.numberfield» (сравнение строк по началу считало его своим — окошки не закрывались)."""
    w, p = str(widget), str(parent)
    return w == p or w.startswith(p + ".") or p == "."


def is_text_input(widget):
    return isinstance(widget, (tk.Entry, tk.Text))


# Кольцо фокуса показывается только при работе с клавиатуры (Tab, стрелки).
# Фокус, полученный кликом мышью, «тихий»: кольцо не рисуется, рамки не мигают.
# nav — после последнего клика мышью был Tab (человек ходит по кнопкам с клавиатуры);
# key — последняя нажатая клавиша. Esc без nav — кольца нет (фокус «тихий», как от мыши).
INPUT = {"last": "key", "nav": False, "key": None}
TAB_KEYS = ("Tab", "ISO_Left_Tab")


def note_key(keysym):
    INPUT["last"], INPUT["key"] = "key", keysym
    if keysym in TAB_KEYS:
        INPUT["nav"] = True


def note_mouse():
    INPUT["last"], INPUT["nav"] = "mouse", False


def esc_quiet():
    """Esc, а по Tab до этого не ходили: кольцо не показывать."""
    return INPUT["last"] == "key" and INPUT["key"] == "Escape" and not INPUT["nav"]


def focus_auto(widget):
    """Передать фокус; кольцо будет видно, только если последним вводом была клавиатура
    (но не Esc без Tab)."""
    widget._quiet = INPUT["last"] == "mouse" or esc_quiet()
    widget.focus_set()


def _watch_input(widget):
    """Один раз на Tk: клики и Tab в любом виджете (не только в Control) — для INPUT."""
    root = widget._root()
    if getattr(root, "_input_watched", False):
        return
    root._input_watched = True
    root.bind_all("<ButtonPress>", lambda e: note_mouse(), add="+")
    root.bind_all("<KeyPress-Tab>", lambda e: note_key("Tab"), add="+")


# ==========================================================================
# Поверхности и текст
# ==========================================================================
def Frame(parent, th, tone="surface", pad=0, border=False):
    """Контейнер-поверхность. tone — токен фона (bg / surface / surface-raised)."""
    f = tk.Frame(parent, bg=th.c(tone), padx=th.sp(pad) if pad else 0,
                 pady=th.sp(pad) if pad else 0)
    if border:
        f.configure(highlightthickness=th.size("border"), highlightbackground=th.c("border"),
                    highlightcolor=th.c("border"))
    return f


class Panel(tk.Frame):
    """Карточка / панель-стекло. kind: raised | glass | surface.

    glass в окне Tk — запасной вариант стекла: тонированная заливка + тонкая
    граница (Tk не умеет размывать фон под виджетом). Настоящее стекло с
    размытием рисуется на оверлее захвата (paint.glass)."""

    def __init__(self, parent, th, kind="raised", pad=3):
        if kind == "glass":
            base = th.c("surface")
            fill = paint.mix(th.c("glass-tint"), base, th.glass("fill_alpha"))
            border = paint.mix(th.c("glass-border"), fill, th.glass("border_alpha"))
        elif kind == "surface":
            fill, border = th.c("surface"), th.c("border")
        else:
            fill, border = th.c("surface-raised"), th.c("border")
        super().__init__(parent, bg=fill, padx=th.sp(pad), pady=th.sp(pad),
                         highlightthickness=th.size("border"), highlightbackground=border,
                         highlightcolor=border)
        self.th = th


def Text(parent, th, text="", role="body", tone="primary", weight="regular", wrap=0,
         anchor="w", justify="left"):
    return tk.Label(parent, text=text, bg=parent_bg(parent), fg=th.c(TONES[tone]),
                    font=th.font(role, weight), anchor=anchor, justify=justify,
                    wraplength=wrap or 0, bd=0, padx=0, pady=0)


def Divider(parent, th, vertical=False, pad=2):
    d = tk.Frame(parent, bg=th.c("border"), width=th.size("border"), height=th.size("border"))
    if vertical:
        d.configure(width=th.size("border"))
    return d


# ==========================================================================
# Подсказка
# ==========================================================================
# Режим проверки «номера окон» (`snipper.pyw --ids`): {вид окна: "#N"} (карта — app/winmap.py,
# docs/WINDOWS.md); None — выключен, плашек нет.
WINDOW_IDS = None


def window_badge(win, th, key, corner="ne", x=None, y=None):
    """Режим «номера окон»: плашка «#N» (danger, жирный caption) в углу окна или вида —
    corner ne / nw / se / sw, или в точке x, y. Повторный вызов заменяет плашку. Выключено —
    ничего не делает."""
    if not WINDOW_IDS or key not in WINDOW_IDS:
        return None
    old = getattr(win, "_id_badge", None)
    if old is not None:
        try:
            old.destroy()
        except tk.TclError:
            pass
    lab = tk.Label(win, text=WINDOW_IDS[key], bg=th.c("danger"), fg=th.c("text-on-danger"),
                   font=th.font("caption", "strong"), bd=0, padx=th.sp(1))
    if x is not None:
        lab.place(x=x, y=y, anchor="nw")
    else:
        lab.place(relx=1.0 if "e" in corner else 0.0, rely=1.0 if "s" in corner else 0.0, anchor=corner)
    lab.lift()
    win._id_badge = lab
    return lab


def tip_parts(text):
    """Содержимое подсказки -> (название, пояснение). text: строка (только название),
    (название, пояснение) или функция, возвращающая одно из них (состояние на момент показа).
    Название None — одна строка пояснения обычным начертанием (например, путь к папке)."""
    text = text() if callable(text) else text
    if isinstance(text, (tuple, list)):
        title, desc = (list(text) + [None])[:2]
        return title or None, desc or None
    return (text or None), None


def tooltip_body(parent, th, title, desc=None, hotkey=None, sample=None, bg=None):
    """Вид подсказки: холст с карточкой surface-raised, рамка border-strong, скругление md,
    отступы tooltip_pad. Строка названия — caption жирный text-primary, справа клавиша
    (caption, text-secondary, через tooltip_hotkey_gap); ниже — пояснение (caption,
    text-secondary); ниже — образец линии sample = {"width", "color", "alpha"} (T3).
    Ширина по содержимому, не больше tooltip_max_w. bg — цвет вокруг карточки (на нём
    сглаживаются углы); None — окно с цветом-ключом (углы прозрачные)."""
    px, py = th.size("tooltip_pad")
    max_w = th.size("tooltip_max_w") - 2 * px
    gap = th.size("tooltip_hotkey_gap")
    cap_strong, cap = th.font("caption", "strong"), th.font("caption")
    line = th.line("caption")
    key = th.tech("transparent_key")
    cv = tk.Canvas(parent, bg=bg or key, highlightthickness=0, bd=0, takefocus=0)
    items, y, w = [], py, 0
    if title:
        tw = th.measure(title, "caption", "strong")
        hw = th.measure(hotkey, "caption") if hotkey else 0
        w = max(w, min(max_w, tw + (gap + hw if hotkey else 0)))
        items.append(("title", y, title, hotkey))
        y += line
    if desc:
        dw = min(max_w, th.measure(desc, "caption"))
        w = max(w, dw)
        tid = cv.create_text(0, 0, anchor="nw", text=desc, font=cap, width=max_w)
        dh = cv.bbox(tid)[3] - cv.bbox(tid)[1]
        cv.delete(tid)
        items.append(("desc", y, desc, None))
        y += max(line, dh)
    if sample:
        sw, sh = th.size("tip_sample")
        w = max(w, sw)
        y += th.sp(1)
        items.append(("sample", y, None, None))
        y += sh
    W, H = w + 2 * px, y + py
    fill, border = th.c("surface-raised"), th.c("border-strong")
    if bg:
        img = paint.rounded(W, H, th.r("md"), fill, bg, border=border, border_w=th.size("border"))
    else:
        img = paint.rounded_hard(W, H, th.r("md"), fill, key, border=border, border_w=th.size("border"))
    cv.configure(width=W, height=H)
    cv.create_image(0, 0, anchor="nw", image=img)
    cv._imgs = [img]                                  # иначе картинки соберёт сборщик мусора
    for kind, iy, text, hk in items:
        if kind == "title":
            cv.create_text(px, iy, anchor="nw", text=text, font=cap_strong, fill=th.c("text-primary"),
                           width=max_w - (gap + th.measure(hk, "caption") if hk else 0))
            if hk:
                cv.create_text(W - px, iy, anchor="ne", text=hk, font=cap, fill=th.c("text-secondary"))
        elif kind == "desc":
            cv.create_text(px, iy, anchor="nw", text=text, font=cap, fill=th.c("text-secondary"),
                           width=max_w)
        else:
            sw, sh = th.size("tip_sample")
            lw = max(1, min(th.px(sample["width"]), sh - th.sp(1)))   # не толще поля минус 4
            im = paint.line_sample(sw, sh, th.size("tip_checker"), th.c("control-hover"),
                                   th.c("surface-raised"), th.c("border"), lw, sample["color"],
                                   sample.get("alpha", 1), th.sp(2))
            cv.create_image(px, iy, anchor="nw", image=im)
            cv._imgs.append(im)
    return cv


class Tooltip:
    """Всплывающая подсказка (слой popup): название жирным, пояснение, клавиша справа в строке
    названия, у размера — образец линии (`tooltip_body`). Показывается при наведении (и у
    недоступных контролов — объясняет причину) и при фокусе с клавиатуры. Без тени и анимации.
    Место — под виджетом, левым краем по его левому краю; не влезает справа — правым краем
    по правому краю виджета."""

    # Настоящее положение виджета на экране f(widget) -> (x, y, w, h); программа подключает
    # WinAPI. Нужно внутри переподчинённых окон (модальная карточка), где winfo_root* у Tk неверны.
    screen_rect = None

    def __init__(self, widget, th, text, hotkey=None, sample=None):
        self.w, self.th, self.text, self.hotkey = widget, th, text, hotkey
        self.sample = sample            # () -> {"width", "color", "alpha"} или None (образец линии)
        self.tip = None
        self.job = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")
        widget.bind("<FocusOut>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def _schedule(self, _=None):
        self._cancel()
        self.job = self.w.after(self.th.timing("tooltip_delay"), self.show)

    def _cancel(self):
        if self.job:
            try:
                self.w.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None

    def show(self):
        self.job = None
        if self.tip or not self.w.winfo_exists() or getattr(self.w, "pressed", False):
            return                        # кнопку держат (повтор − / +) — подсказка мешает
        if Popup.any_open():
            return                        # открыто всплывающее окно — подсказка легла бы на него
        title, desc = tip_parts(self.text)
        if not (title or desc):
            return
        th = self.th
        sample = self.sample() if self.sample else None
        t = tk.Toplevel(self.w)
        t.withdraw()                      # показать уже на месте (иначе мелькает в углу экрана)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.configure(bg=th.tech("transparent_key"))
        t.attributes("-transparentcolor", th.tech("transparent_key"))   # углы карточки сквозные
        tooltip_body(t, th, title, desc, self.hotkey if title else None, sample).pack()
        window_badge(t, th, "tooltip")
        t.update_idletasks()
        if Tooltip.screen_rect:
            x, y, w, h = Tooltip.screen_rect(self.w)
        else:
            x, y = self.w.winfo_rootx(), self.w.winfo_rooty()
            w, h = self.w.winfo_width(), self.w.winfo_height()
        ring = getattr(self.w, "ring", 0)    # поле под кольцо фокуса — не часть кнопки
        x, y, w, h = x + ring, y + ring, w - 2 * ring, h - 2 * ring
        tw = t.winfo_reqwidth()
        _l, _t, r, _b = (Popup.screen_bounds(x, y) if Popup.screen_bounds else
                         (0, 0, self.w.winfo_screenwidth(), self.w.winfo_screenheight()))
        if x + tw > r:                    # не влезает справа — правым краем по правому краю кнопки
            x = x + w - tw
        t.geometry(f"+{x}+{y + h + th.sp(1)}")
        t.deiconify()
        self.tip = t

    def refresh(self):
        """Состояние сменилось (переключили щелчком): подсказка с НОВЫМ текстом сразу, если курсор
        всё ещё над виджетом. Иначе подсказка, закрытая нажатием, вернулась бы только после того,
        как курсор уйдёт и снова наведётся (а текст-функция так и показывала бы старое)."""
        self.hide()
        try:
            if not self.w.winfo_exists():
                return
            over = self.w.winfo_containing(*self.w.winfo_pointerxy())
        except (tk.TclError, KeyError):
            return
        if over is not None and within(over, self.w):
            self.job = self.w.after(1, self.show)

    def hide(self, _=None):
        self._cancel()
        if self.tip:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None


# ==========================================================================
# База интерактивного контрола
# ==========================================================================
class Control(tk.Canvas):
    """Общая логика состояний, фокуса, клавиатуры и подсказки."""

    def __init__(self, parent, th, width, height, *, tooltip=None, hotkey=None,
                 disabled=False, error=False, selected=False, loading=False, force=None,
                 focusable=True, command=None, cursor="hand2", on_hold=None, tip_sample=None):
        self.bg = parent_bg(parent)
        super().__init__(parent, width=width, height=height, bg=self.bg, highlightthickness=0,
                         bd=0, takefocus=1 if focusable else 0, cursor=cursor)
        self.th = th
        self.W, self.H = width, height
        self.command = command
        self.on_hold = on_hold        # удержание дольше TIMING.hold -> on_hold(self) вместо клика
        self._hold_job, self._held = None, False
        self.hover = self.pressed = self.focused = False
        self._quiet = False          # фокус от мыши — без кольца
        _watch_input(self)
        self.disabled, self.error, self.selected, self.loading = disabled, error, selected, loading
        self.force = set(force or ())
        self.ring = th.size("focus") + 1          # поле под кольцо фокуса
        self._spin = 0
        self._spin_job = None
        self.tooltip = Tooltip(self, th, tooltip, hotkey, tip_sample) if tooltip else None
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus, add="+")
        self.bind("<FocusOut>", self._on_blur, add="+")
        self.bind("<KeyPress-space>", self._on_key)
        self.bind("<Return>", self._on_key)
        self.bind("<KeyPress>", self._any_key, add="+")
        if loading:
            self._spin_tick()

    # состояние с учётом витрины
    @property
    def is_hover(self):
        return (self.hover or "hover" in self.force) and not self.disabled

    @property
    def is_pressed(self):
        return (self.pressed or "pressed" in self.force) and not self.disabled

    @property
    def is_focus(self):
        return ((self.focused and not self._quiet) or "focus" in self.force) and not self.disabled

    @property
    def interactive(self):
        return not (self.disabled or self.loading)

    def configure_state(self, **flags):
        for k, v in flags.items():
            setattr(self, k, v)
        self.configure(cursor="arrow" if self.disabled else "hand2",
                       takefocus=0 if self.disabled else 1)
        if flags.get("loading"):
            self._spin_tick()
        self.paint()

    def _on_enter(self, _):
        self.hover = True
        self.paint()

    def _on_leave(self, _):
        self.hover = self.pressed = False
        self._cancel_hold()
        self.paint()

    def _cancel_hold(self):
        if self._hold_job:
            self.after_cancel(self._hold_job)
            self._hold_job = None

    def _fire_hold(self):
        self._hold_job = None
        self._held, self.pressed = True, False
        self.paint()
        self.on_hold(self)

    def _on_press(self, _):
        if not self.interactive:
            return
        if self.on_hold:
            self._held = False
            self._hold_job = self.after(self.th.timing("hold"), self._fire_hold)
        self.pressed = True
        note_mouse()
        if int(self.cget("takefocus") or 0):
            self._quiet = True
            self.focus_set()
        self.paint()

    def _on_release(self, e):
        self._cancel_hold()
        if self._held:                 # было удержание — клик не засчитываем
            self._held = False
            return
        if not self.pressed:
            return
        self.pressed = False
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        self.paint()
        if inside and self.interactive:
            self.activate()

    def _on_key(self, e):
        note_key(getattr(e, "keysym", "Return"))   # e = None — вызов кодом (тесты), как Enter
        if self.interactive:
            self.activate()
        return "break"

    def _any_key(self, e):
        if e.keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R"):
            return
        note_key(e.keysym)
        if esc_quiet():        # Esc, а по Tab не ходили — кольцо не показывать
            return
        if self._quiet:        # начали работать с клавиатуры — показать, где фокус
            self._quiet = False
            self.paint()

    def _on_focus(self, _):
        self.focused = True
        self.paint()

    def _on_blur(self, _):
        self.focused = False
        self._quiet = False
        self.paint()

    def activate(self):
        if self.command:
            self.command()

    def _spin_tick(self):
        if not self.loading:
            self._spin_job = None
            return
        self._spin = (self._spin + 30) % 360
        self.paint()
        self._spin_job = self.after(self.th.timing("spinner_step"), self._spin_tick)

    # отрисовка — в наследниках
    def paint(self):
        raise NotImplementedError

    def _bg_image(self, fill, border=None, radius=None, w=None, h=None):
        th = self.th
        w = w or self.W
        h = h or self.H
        radius = th.r("md") if radius is None else radius
        bw = th.size("border") if border else 0
        if self.is_focus:   # кольцо фокуса занимает поле self.ring вокруг фигуры
            img = paint.rounded(w, h, radius, fill, self.bg, border=border, border_w=bw,
                                ring=th.c("focus-ring"), ring_w=th.size("focus"), ring_gap=1)
            self.create_image(0, 0, anchor="nw", image=img)
        else:
            img = paint.rounded(w - 2 * self.ring, h - 2 * self.ring, radius, fill, self.bg,
                                border=border, border_w=bw)
            self.create_image(self.ring, self.ring, anchor="nw", image=img)

    def _spinner(self, cx, cy, color):
        r = self.th.size("icon_sm") // 2 - 1
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=self._spin, extent=270,
                        style="arc", outline=color, width=self.th.size("focus"))


# ==========================================================================
# Кнопки
# ==========================================================================
class Button(Control):
    """variant: primary | secondary | ghost | danger. size: sm | md | lg."""

    def __init__(self, parent, th, text="", *, icon=None, variant="secondary", size="md",
                 width=None, **kw):
        self.text, self.icon_name, self.variant = text, icon, variant
        self._fixed_w = width
        h = th.size({"sm": "control_sm", "md": "control", "lg": "control_lg"}[size])
        ring = th.size("focus") + 1
        super().__init__(parent, th, width or self._natural_w(th, text, icon), h + 2 * ring, **kw)
        self.paint()

    def _natural_w(self, th, text, icon):
        isz = th.size("icon_sm")
        content = (isz if icon else 0) + (th.sp(2) if icon and text else 0) + \
            (th.measure(text, "body", "strong" if self.variant == "primary" else "regular") if text else 0)
        return content + 2 * th.sp(3) + 2 * (th.size("focus") + 1)

    def relabel(self, text, icon=None):
        """Сменить подпись/иконку с пересчётом ширины."""
        self.text, self.icon_name = text, icon or self.icon_name
        if not self._fixed_w:
            self.W = self._natural_w(self.th, self.text, self.icon_name)
            self.configure(width=self.W)
        self.paint()

    def colors(self):
        th = self.th
        v = self.variant
        if self.disabled:
            return (self.bg if v == "ghost" else th.c("control")), None, th.c("text-disabled")
        if v == "primary":
            fill = th.c("accent-pressed" if self.is_pressed else "accent-hover" if self.is_hover else "accent")
            return fill, None, th.c("text-on-accent")
        if v == "danger":
            fill = th.c("danger-hover" if (self.is_pressed or self.is_hover) else "danger")
            return fill, None, th.c("text-on-danger")
        if v == "ghost":
            if self.selected:
                fill = th.c("accent-soft")
                return (paint.mix(th.c("text-primary"), fill, 0.06) if self.is_hover else fill,
                        None, th.c("accent-fg"))
            if self.is_pressed:
                fill = th.c("control-pressed")
            elif self.is_hover:
                fill = th.c("control-hover")
            else:
                fill = self.bg
            return fill, None, th.c("text-primary")
        fill = th.c("control-pressed" if self.is_pressed else "control-hover" if self.is_hover else "control")
        border = th.c("danger-fg") if self.error else th.c("border-strong" if self.is_hover else "border")
        if self.selected:
            fill, border = th.c("accent-soft"), th.c("accent-fg")
        return fill, border, th.c("text-primary")

    def paint(self):
        self.delete("all")
        th = self.th
        fill, border, fg = self.colors()
        self._bg_image(fill, border)
        cx, cy = self.W // 2, self.H // 2
        isz = th.size("icon_sm")
        weight = "strong" if self.variant == "primary" else "regular"
        tw = th.measure(self.text, "body", weight) if self.text else 0
        total = (isz if self.icon_name or self.loading else 0) + \
            (th.sp(2) if (self.icon_name or self.loading) and self.text else 0) + tw
        x = cx - total // 2
        if self.loading:
            self._spinner(x + isz // 2, cy, fg)
            x += isz + th.sp(2)
        elif self.icon_name:
            self.create_image(x, cy, anchor="w", image=get_icon(self.icon_name, isz, fg))
            x += isz + (th.sp(2) if self.text else 0)
        if self.text:
            self.create_text(x, cy, text=self.text, anchor="w", fill=fg, font=th.font("body", weight))

    def set_text(self, text):
        self.text = text
        self.paint()


class IconToggle(Control):
    """Значок-переключатель: кнопкой служит сама линейная иконка — без плитки, заливки, рамки.
    Выключено — text-secondary, наведение — text-primary, включено — icon-on и штрих
    ICON.stroke_on, отключено — text-disabled. Зона нажатия невидимая, размером с соседние
    кнопки панели; кольцо фокуса — только с клавиатуры. tooltip может быть функцией
    (подпись с состоянием: «Курсор в GIF: включён»)."""

    def __init__(self, parent, th, icon, tooltip, value=False, on_change=None, *, size="sm", **kw):
        ring = th.size("focus") + 1
        h = th.size({"sm": "control_sm", "md": "control", "lg": "control_lg"}[size])
        self.icon_name, self.on_change = icon, on_change
        super().__init__(parent, th, h + 2 * ring, h + 2 * ring, tooltip=tooltip, selected=bool(value), **kw)
        self.paint()

    @property
    def value(self):
        return self.selected

    def set(self, v):
        self.selected = bool(v)
        self.paint()

    def activate(self):
        self.set(not self.selected)
        if self.on_change:
            self.on_change(self.selected)
        if self.tooltip:                     # «Курсор в GIF: включён» → «выключен» — сразу, под курсором
            self.tooltip.refresh()

    def paint(self):
        self.delete("all")
        th = self.th
        if self.is_focus:                    # невидимая зона нажатия видна только кольцом фокуса
            self._bg_image(self.bg)
        stroke = None
        if self.disabled:
            color = th.c("text-disabled")
        elif self.selected:
            color, stroke = th.c("icon-on"), th.icon_stroke("stroke_on")
        elif self.is_hover or self.is_pressed:
            color = th.c("text-primary")
        else:
            color = th.c("text-secondary")
        self.create_image(self.W // 2, self.H // 2,
                          image=get_icon(self.icon_name, th.size("icon_sm"), color, stroke))


class IconButton(Button):
    """Квадратная кнопка-иконка. tooltip обязателен (это её подпись)."""

    def __init__(self, parent, th, icon, tooltip, *, variant="ghost", size="sm", **kw):
        ring = th.size("focus") + 1
        h = th.size({"sm": "control_sm", "md": "control", "lg": "control_lg"}[size])
        super().__init__(parent, th, "", icon=icon, variant=variant, size=size,
                         width=h + 2 * ring, tooltip=tooltip, **kw)

    def set_icon(self, name):
        self.icon_name = name
        self.paint()


# ==========================================================================
# Переключатели
# ==========================================================================
class Toggle(Control):
    def __init__(self, parent, th, value=False, on_change=None, **kw):
        self.value, self.on_change = bool(value), on_change
        ring = th.size("focus") + 1
        super().__init__(parent, th, th.size("toggle_w") + 2 * ring, th.size("toggle_h") + 2 * ring, **kw)
        self.paint()

    def activate(self):
        self.set(not self.value)
        if self.on_change:
            self.on_change(self.value)

    def get(self):
        return self.value

    def set(self, v):
        self.value = bool(v)
        self.paint()

    def paint(self):
        self.delete("all")
        th = self.th
        h = self.H - 2 * self.ring
        if self.disabled:
            fill, knob, border = th.c("control"), th.c("text-disabled"), th.c("border")
        elif self.value:
            fill = th.c("accent-hover" if self.is_hover else "accent")
            knob, border = th.c("text-on-accent"), None
        else:
            fill, knob = th.c("control-pressed"), th.c("text-secondary")
            border = th.c("danger-fg") if self.error else th.c("text-secondary" if self.is_hover else "border-strong")
        self._bg_image(fill, border, radius=h // 2)
        k = h - 2 * th.sp(1)
        x = self.ring + (self.W - 2 * self.ring - k - th.sp(1) if self.value else th.sp(1))
        self.create_image(x, self.ring + th.sp(1), anchor="nw",
                          image=paint.circle(k, knob, fill))


class Checkbox(Control):
    def __init__(self, parent, th, text="", value=False, on_change=None, **kw):
        self.text, self.value, self.on_change = text, bool(value), on_change
        ring = th.size("focus") + 1
        box = th.size("check")
        w = box + 2 * ring + (th.sp(2) + th.measure(text) if text else 0)
        super().__init__(parent, th, w, max(box + 2 * ring, th.line("body")), **kw)
        self.paint()

    def activate(self):
        self.set(not self.value)
        if self.on_change:
            self.on_change(self.value)

    def get(self):
        return self.value

    def set(self, v):
        self.value = bool(v)
        self.paint()

    def paint(self):
        self.delete("all")
        th = self.th
        box = th.size("check")
        bw = box + 2 * self.ring
        y0 = (self.H - bw) // 2
        if self.disabled:
            fill, border, mark = th.c("control"), th.c("border"), th.c("text-disabled")
        elif self.value:
            fill = th.c("accent-hover" if self.is_hover else "accent")
            border, mark = None, th.c("text-on-accent")
        else:
            fill, mark = th.c("control"), None
            border = th.c("danger-fg") if self.error else th.c("text-secondary" if self.is_hover else "border-strong")
        ring = th.c("focus-ring") if self.is_focus else None
        img = paint.rounded(bw, bw, th.r("sm"), fill, self.bg, border=border,
                            border_w=th.size("border") if border else 0, ring=ring,
                            ring_w=th.size("focus") if ring else 0, ring_gap=1 if ring else 0)
        if not ring:
            img = paint.rounded(box, box, th.r("sm"), fill, self.bg, border=border,
                                border_w=th.size("border") if border else 0)
            self.create_image(self.ring, y0 + self.ring, anchor="nw", image=img)
        else:
            self.create_image(0, y0, anchor="nw", image=img)
        if self.value:
            self.create_image(self.ring + box // 2, y0 + self.ring + box // 2,
                              image=get_icon("check", box - 2, mark or th.c("text-on-accent")))
        if self.text:
            self.create_text(bw + th.sp(2), self.H // 2, anchor="w", text=self.text,
                             font=th.font("body"),
                             fill=th.c("text-disabled" if self.disabled else "text-primary"))


class RadioGroup:
    """Общее значение для набора Radio."""

    def __init__(self, value=None, on_change=None):
        self.value, self.on_change, self.items = value, on_change, []

    def set(self, v, notify=False):
        self.value = v
        for r in self.items:
            r.paint()
        if notify and self.on_change:
            self.on_change(v)


class Radio(Control):
    def __init__(self, parent, th, group, value, text="", **kw):
        self.group, self.value, self.text = group, value, text
        group.items.append(self)
        ring = th.size("focus") + 1
        box = th.size("check")
        w = box + 2 * ring + (th.sp(2) + th.measure(text) if text else 0)
        super().__init__(parent, th, w, max(box + 2 * ring, th.line("body")), **kw)
        self.bind("<Up>", lambda e: self._move(-1))
        self.bind("<Down>", lambda e: self._move(1))
        self.bind("<Left>", lambda e: self._move(-1))
        self.bind("<Right>", lambda e: self._move(1))
        self.paint()

    def _move(self, d):
        items = [r for r in self.group.items if not r.disabled]
        i = (items.index(self) + d) % len(items)
        items[i].focus_set()
        items[i].activate()
        return "break"

    def activate(self):
        self.group.set(self.value, notify=True)

    def paint(self):
        self.delete("all")
        th = self.th
        box = th.size("check")
        on = self.group.value == self.value
        y0 = (self.H - box) // 2
        x0 = self.ring
        if self.is_focus:
            r = self.ring
            self.create_image(0, y0 - r, anchor="nw",
                              image=paint.circle(box + 2 * r, th.c("focus-ring"), self.bg))
            self.create_image(x0 - 1, y0 - 1, anchor="nw", image=paint.circle(box + 2, self.bg, self.bg))
        if self.disabled:
            border, dot = th.c("border"), th.c("text-disabled") if on else None
        else:
            border = th.c("accent") if on else (th.c("danger-fg") if self.error else
                                                th.c("text-secondary" if self.is_hover else "border-strong"))
            dot = th.c("accent") if on else None
        fill = th.c("control")
        self.create_image(x0, y0, anchor="nw",
                          image=paint.circle(box, fill, self.bg, border, th.size("focus")))
        if dot:
            d = box // 2
            self.create_image(x0 + (box - d) // 2, y0 + (box - d) // 2, anchor="nw",
                              image=paint.circle(d, dot, fill))
        if self.text:
            self.create_text(box + 2 * self.ring + th.sp(2), self.H // 2, anchor="w", text=self.text,
                             font=th.font("body"),
                             fill=th.c("text-disabled" if self.disabled else "text-primary"))


class Slider(Control):
    def __init__(self, parent, th, value=0, lo=0, hi=100, step=1, width=None, on_change=None, **kw):
        self.value, self.lo, self.hi, self.step, self.on_change = value, lo, hi, step, on_change
        ring = th.size("focus") + 1
        w = width or th.size("field_w")
        super().__init__(parent, th, w, th.size("slider_thumb") + 2 * ring + 2, **kw)
        self.bind("<B1-Motion>", self._drag)
        for k, d in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1)):
            self.bind(f"<{k}>", lambda e, d=d: self._nudge(d))
        self.bind("<Home>", lambda e: self._set(self.lo, True))
        self.bind("<End>", lambda e: self._set(self.hi, True))
        self.paint()

    def _x_range(self):
        t = self.th.size("slider_thumb")
        return self.ring + t // 2, self.W - self.ring - t // 2

    def _on_press(self, e):
        super()._on_press(e)
        if self.interactive:
            self._drag(e)

    def activate(self):
        pass

    def _drag(self, e):
        if not self.interactive:
            return
        a, b = self._x_range()
        f = min(1, max(0, (e.x - a) / max(1, b - a)))
        self._set(self.lo + f * (self.hi - self.lo), True)

    def _nudge(self, d):
        if self.interactive:
            self._set(self.value + d * self.step, True)
        return "break"

    def _set(self, v, notify):
        v = round((min(self.hi, max(self.lo, v)) - self.lo) / self.step) * self.step + self.lo
        if v != self.value:
            self.value = v
            self.paint()
            if notify and self.on_change:
                self.on_change(v)

    def get(self):
        return self.value

    def set(self, v):
        self._set(v, False)

    def paint(self):
        self.delete("all")
        th = self.th
        a, b = self._x_range()
        cy = self.H // 2
        tr = th.size("slider_track")
        f = (self.value - self.lo) / max(1e-9, self.hi - self.lo)
        x = a + f * (b - a)
        self.create_image(a - tr // 2, cy - tr // 2, anchor="nw",
                          image=paint.rounded(b - a + tr, tr, tr // 2, th.c("control-pressed"), self.bg))
        on = th.c("text-disabled") if self.disabled else th.c("danger-fg") if self.error else th.c("accent")
        if x - a > 0:
            self.create_image(a - tr // 2, cy - tr // 2, anchor="nw",
                              image=paint.rounded(int(x - a) + tr, tr, tr // 2, on, self.bg))
        t = th.size("slider_thumb")
        if self.is_focus:
            r = t + 2 * th.size("focus") + 2
            self.create_image(x, cy, image=paint.circle(r, th.c("focus-ring"), self.bg))
            self.create_image(x, cy, image=paint.circle(t + 2, self.bg, self.bg))
        knob = th.c("text-disabled") if self.disabled else th.c("text-primary")
        if self.is_hover or self.is_pressed:
            knob = th.c("accent-hover") if not self.disabled else knob
        self.create_image(x, cy, image=paint.circle(t, knob, self.bg, th.c("border-strong"), 1))


# ==========================================================================
# Поля
# ==========================================================================
class TextField(tk.Canvas):
    """Поле ввода. on_commit(text) — по Enter и при потере фокуса."""

    def __init__(self, parent, th, value="", *, width=None, chars=None, readonly=False,
                 disabled=False, error=False, on_commit=None, on_nudge=None, force=None,
                 tooltip=None, align="left"):
        self.th = th
        self.bg = parent_bg(parent)
        self.ring = th.size("focus") + 1
        if chars:
            width = th.measure("0" * chars) + 2 * th.sp(2)
        self.W = (width or th.size("field_w")) + 2 * self.ring
        self.H = th.size("control") + 2 * self.ring
        super().__init__(parent, width=self.W, height=self.H, bg=self.bg, highlightthickness=0,
                         bd=0, takefocus=0)
        self.readonly, self.disabled, self.error = readonly, disabled, error
        self.force = set(force or ())
        self.hover = self.focused = self._quiet = False
        self.on_commit, self.on_nudge = on_commit, on_nudge
        self.var = tk.StringVar(value=str(value))
        self.entry = tk.Entry(self, textvariable=self.var, relief="flat", bd=0,
                              font=th.font("body"), justify=align,
                              bg=th.c("control"), fg=th.c("text-primary"),
                              insertbackground=th.c("text-primary"),
                              selectbackground=th.c("accent-soft"),
                              selectforeground=th.c("text-primary"),
                              disabledbackground=th.c("control"),
                              disabledforeground=th.c("text-disabled"),
                              readonlybackground=th.c("control"),
                              highlightthickness=0)
        pad = th.sp(2)
        self.win = self.create_window(self.ring + pad, self.H // 2, anchor="w", window=self.entry,
                                      width=self.W - 2 * self.ring - 2 * pad)
        if tooltip:
            Tooltip(self.entry, th, tooltip)
        for w in (self, self.entry):
            w.bind("<Enter>", lambda e: self._hov(True), add="+")
            w.bind("<Leave>", lambda e: self._hov(False), add="+")
        self.entry.bind("<ButtonPress-1>", lambda e: setattr(self, "_quiet", True), add="+")
        self.entry.bind("<FocusIn>", lambda e: self._foc(True), add="+")
        self.entry.bind("<FocusOut>", lambda e: (self._foc(False), self._commit()), add="+")
        self.entry.bind("<Return>", lambda e: (self._commit(), "break")[1])
        self.entry.bind("<Up>", lambda e: self._nudge(1))
        self.entry.bind("<Down>", lambda e: self._nudge(-1))
        self._apply_state()

    def _hov(self, v):
        self.hover = v
        self.paint()

    def _foc(self, v):
        self.focused = v
        if not v:
            self._quiet = False
        self.paint()

    def _commit(self):
        if self.on_commit and not self.disabled:
            self.on_commit(self.var.get())

    def _nudge(self, d):
        if self.on_nudge and not self.disabled:
            self.on_nudge(d)
            return "break"

    def _apply_state(self):
        self.entry.configure(state="disabled" if self.disabled else "readonly" if self.readonly else "normal",
                             takefocus=0 if self.disabled else 1)
        self.paint()

    def configure_state(self, **flags):
        for k, v in flags.items():
            setattr(self, k, v)
        self._apply_state()

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(str(v))

    def paint(self):
        self.delete("bgimg")
        th = self.th
        focus = (self.focused or "focus" in self.force) and not self.disabled
        ring_on = (focus and not self._quiet) or "focus" in self.force
        hover = (self.hover or "hover" in self.force) and not self.disabled
        if self.error:
            border = th.c("danger-fg")
        elif focus:
            border = th.c("accent-fg")
        else:
            border = th.c("border-strong" if hover else "border")
        ring = th.c("focus-ring") if ring_on else None
        fill = th.c("control")
        if ring:
            img = paint.rounded(self.W, self.H, th.r("md"), fill, self.bg, border=border,
                                border_w=th.size("border"), ring=ring, ring_w=th.size("focus"), ring_gap=1)
            self.create_image(0, 0, anchor="nw", image=img, tags="bgimg")
        else:
            img = paint.rounded(self.W - 2 * self.ring, self.H - 2 * self.ring, th.r("md"), fill, self.bg,
                                border=border, border_w=th.size("border"))
            self.create_image(self.ring, self.ring, anchor="nw", image=img, tags="bgimg")
        self.tag_lower("bgimg")


class HotkeyField(Control):
    """Поле горячей клавиши: Enter/клик — запись сочетания, Esc — отмена,
    Backspace/Delete — очистить. Значение — строка вида "Ctrl+Alt+S"."""

    MODS = (("Control", 0x4, "Ctrl"), ("Alt", 0x20000, "Alt"), ("Shift", 0x1, "Shift"))

    def __init__(self, parent, th, value="", on_change=None, on_capture=None, on_reject=None, **kw):
        """on_change(v) -> текст ошибки или None (ошибка — вернуть прежнее значение);
        on_reject(текст) — сочетание не принято самим полем (F12, Win)."""
        self.value, self.on_change, self.on_capture, self.on_reject = value, on_change, on_capture, on_reject
        self.capturing = False
        self._win = False             # клавиша Win зажата
        ring = th.size("focus") + 1
        super().__init__(parent, th, th.size("hotkey_w") + 2 * ring, th.size("control") + 2 * ring, **kw)
        self.bind("<KeyPress>", self._key, add="+")
        self.bind("<KeyRelease>", self._release, add="+")
        # поле пересобрали или закрыли посреди записи — глобальные клавиши не должны остаться выключенными
        self.bind("<Destroy>", lambda e: e.widget is self and self.capturing and self._stop(), add="+")
        self.paint()

    def activate(self):
        if self.capturing:
            return
        self.capturing = True
        self._win = False
        if self.on_capture:
            self.on_capture(True)
        self.focus_set()
        self.paint()

    def _stop(self):
        self.capturing = False
        if self.on_capture:
            self.on_capture(False)
        try:
            self.paint()
        except tk.TclError:
            pass                      # поле уже уничтожено

    VK_SNAPSHOT = 0x2C

    def _release(self, e):
        if e.keysym in ("Win_L", "Win_R"):
            self._win = False
        # PrintScreen: Windows присылает только ОТПУСКАНИЕ (нажатие забирает себе) —
        # сочетание с ним записываем по отпусканию; модификаторы в state ещё зажаты
        if self.capturing and getattr(e, "keycode", 0) == self.VK_SNAPSHOT:
            return self._key(e)

    def _on_blur(self, e):
        if self.capturing:
            self._stop()
        super()._on_blur(e)

    def _on_key(self, e):
        if self.capturing:
            return self._key(e)
        return super()._on_key(e)

    def _key(self, e):
        if not self.capturing:
            if e.keysym in ("BackSpace", "Delete"):
                self._set("")
                return "break"
            return None
        ks = e.keysym
        if ks == "Escape":
            self._stop()
            return "break"
        if ks in ("BackSpace", "Delete"):
            self._stop()
            self._set("")
            return "break"
        if ks in ("Win_L", "Win_R"):
            self._win = True
            return "break"
        if ks in ("Control_L", "Control_R", "Alt_L", "Alt_R", "Shift_L", "Shift_R"):
            return "break"
        mods = [name for _, mask, name in self.MODS if e.state & mask]
        key = self._vk_name(getattr(e, "keycode", 0)) or (ks.upper() if len(ks) == 1 else ks)
        is_fn = key.startswith("F") and key[1:].isdigit() or key in ("Print", "Pause", "Scroll_Lock")
        if not mods and not is_fn:
            return "break"  # одиночная клавиша глобально перехватила бы ввод
        if self._win or key in self.RESERVED:
            self._stop()
            if self.on_reject:
                self.on_reject(tr("Сочетания с Win заняты Windows — выберите другое") if self._win
                               else tr(self.RESERVED[key]))
            return "break"
        # сначала снять паузу глобальных клавиш, потом назначать: регистрация видит новое сразу
        self._stop()
        self._set("+".join(mods + [key]))
        return "break"

    # Клавишу берём по коду клавиши Windows, а не по символу: в русской раскладке keysym
    # был бы «Cyrillic_o», с Shift — «exclam», и RegisterHotKey такое не принимает.
    VK_NAMES = {0x2C: "Print", 0x13: "Pause", 0x91: "Scroll_Lock", 0x20: "space", 0x2D: "Insert",
                0x24: "Home", 0x23: "End", 0x21: "Prior", 0x22: "Next"}

    @classmethod
    def _vk_name(cls, vk):
        if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
            return chr(vk)
        if 0x70 <= vk <= 0x87:
            return f"F{vk - 0x6F}"
        return cls.VK_NAMES.get(vk)

    # F12 зарезервирована Windows для отладчика (документация RegisterHotKey)
    RESERVED = {"F12": "F12 зарезервирована Windows — выберите другую клавишу"}

    def _set(self, v):
        old, self.value = self.value, v
        if self.on_change and self.on_change(v):
            self.value = old          # не принято — остаётся прежнее рабочее сочетание
        self.paint()

    def get(self):
        return self.value

    def paint(self):
        self.delete("all")
        th = self.th
        if self.capturing:
            border = th.c("accent-fg")
        elif self.error:
            border = th.c("danger-fg")
        else:
            border = th.c("border-strong" if self.is_hover else "border")
        self._bg_image(th.c("control"), border)
        isz = th.size("icon_sm")
        x = self.ring + th.sp(2)
        fg = th.c("text-disabled" if self.disabled else "text-secondary")
        self.create_image(x, self.H // 2, anchor="w", image=get_icon("keyboard", isz, fg))
        if self.capturing:
            txt, tone = tr("Нажмите сочетание…"), "accent-fg"
        elif self.value:
            txt, tone = self.value, "text-primary"
        else:
            txt, tone = tr("Не задано"), "text-secondary"
        self.create_text(x + isz + th.sp(2), self.H // 2, anchor="w", text=txt,
                         fill=th.c("text-disabled" if self.disabled else tone), font=th.font("body"))


class HotkeyInput(tk.Frame):
    """Поле глобального сочетания (HotkeyField) + крестик «Очистить сочетание» справа (B18):
    IconButton ghost размера поля. Очистка — то же, что Backspace: on_change("") снимает
    сочетание и сохраняет ПУСТОЕ значение. Пусто — крестик неактивен."""

    def __init__(self, parent, th, value="", on_change=None, on_capture=None, on_reject=None):
        super().__init__(parent, bg=parent_bg(parent))
        self._on_change = on_change

        def changed(v):
            err = on_change(v) if on_change else None
            self.after_idle(self._sync)
            return err
        self.field = HotkeyField(self, th, value, on_change=changed, on_capture=on_capture, on_reject=on_reject)
        self.field.pack(side="left")
        self.clear = IconButton(self, th, "close", tr("Очистить сочетание"), size="md", command=self._clear,
                                disabled=not value)
        self.clear.pack(side="left")

    def _clear(self):
        if self.field.value:
            self.field._set("")

    def _sync(self):
        if self.winfo_exists():
            self.clear.configure_state(disabled=not self.field.value)

    def get(self):
        return self.field.value


class ColorField(Control):
    """Образец цвета (+ необязательная подпись hex). Активация -> on_pick()."""

    def __init__(self, parent, th, color, on_pick=None, show_hex=False, small=False, **kw):
        self.color, self.on_pick, self.show_hex, self.small = color, on_pick, show_hex, small
        ring = th.size("focus") + 1
        sw = th.size("swatch" if small else "swatch_lg")
        w = sw + 2 * ring + (th.sp(2) + th.measure("#" + "8" * 6) if show_hex else 0)
        super().__init__(parent, th, w, sw + 2 * ring, command=self._pick, **kw)
        self.paint()

    def _pick(self):
        if self.on_pick:
            self.on_pick(self)

    def set(self, color):
        self.color = color
        self.paint()

    def get(self):
        return self.color

    def paint(self):
        self.delete("all")
        th = self.th
        sw = th.size("swatch" if self.small else "swatch_lg")
        border = th.c("text-secondary" if self.is_hover else "border-strong")
        ring = th.c("focus-ring") if self.is_focus else None
        if ring:
            self.create_image(0, 0, anchor="nw", image=paint.rounded(
                sw + 2 * self.ring, sw + 2 * self.ring, th.r("sm"), self.color, self.bg, border=border,
                border_w=th.size("border"), ring=ring, ring_w=th.size("focus"), ring_gap=1))
        else:
            self.create_image(self.ring, self.ring, anchor="nw", image=paint.rounded(
                sw, sw, th.r("sm"), self.color, self.bg, border=border, border_w=th.size("border")))
        if self.show_hex:
            self.create_text(sw + 2 * self.ring + th.sp(2), self.H // 2, anchor="w",
                             text=self.color.upper(), font=th.font("caption"),
                             fill=th.c("text-secondary"))


class PathField(tk.Frame):
    """Путь к папке: поле только для чтения + «Изменить…» + открыть (+ сброс)."""

    def __init__(self, parent, th, value, on_browse, on_open=None, on_reset=None, reset_text=None):
        super().__init__(parent, bg=parent_bg(parent))
        self.field = TextField(self, th, value, readonly=True, tooltip=(None, value))   # путь — одной строкой
        self.field.pack(side="left")
        Button(self, th, tr("Изменить…"), command=on_browse).pack(side="left", padx=(th.sp(1), 0))
        if on_open:
            IconButton(self, th, "open", tr("Открыть папку"), size="md", command=on_open).pack(side="left")
        if on_reset:
            Button(self, th, reset_text or tr("По умолчанию"), variant="ghost", command=on_reset).pack(side="left")

    def set(self, v):
        self.field.set(v)


# ==========================================================================
# Списки, выпадающие списки, вкладки
# ==========================================================================
class ListRow(Control):
    """Строка списка/меню: иконка, текст, подсказка справа (горячая клавиша)."""

    def __init__(self, parent, th, text, *, icon=None, hint=None, width=None, **kw):
        self.text, self.icon_name, self.hint = text, icon, hint
        ring = th.size("focus") + 1
        isz = th.size("icon_sm")
        w = width or (2 * ring + 2 * th.sp(3) + (isz + th.sp(2) if icon else 0) + th.measure(text)
                      + (th.sp(6) + th.measure(hint, "caption") if hint else 0))
        super().__init__(parent, th, w, th.size("control") + 2 * ring, **kw)
        self.paint()

    def paint(self):
        self.delete("all")
        th = self.th
        if self.selected:
            fill = th.c("accent-soft")
        elif self.is_pressed:
            fill = th.c("control-pressed")
        elif self.is_hover:
            fill = th.c("control-hover")
        else:
            fill = self.bg
        self._bg_image(fill, None, radius=th.r("sm"))
        x = self.ring + th.sp(3)
        cy = self.H // 2
        fg = th.c("text-disabled" if self.disabled else "text-primary")
        ic = th.c("text-disabled" if self.disabled else "accent-fg" if self.selected else "text-secondary")
        if self.selected:
            bar = th.size("focus")
            self.create_rectangle(self.ring, cy - th.sp(2), self.ring + bar, cy + th.sp(2),
                                  fill=th.c("accent-fg"), outline="")
        if self.icon_name:
            self.create_image(x, cy, anchor="w", image=get_icon(self.icon_name, th.size("icon_sm"), ic))
            x += th.size("icon_sm") + th.sp(2)
        self.create_text(x, cy, anchor="w", text=self.text, fill=fg,
                         font=th.font("body", "strong" if self.selected else "regular"))
        if self.hint:
            self.create_text(self.W - self.ring - th.sp(3), cy, anchor="e", text=self.hint,
                             fill=th.c("text-secondary"), font=th.font("caption"))


class ListView(tk.Frame):
    """Вертикальный список с одиночным выбором. items: [(value, text, icon, hint)]."""

    def __init__(self, parent, th, items, value=None, on_select=None, width=None, selectable=True):
        super().__init__(parent, bg=parent_bg(parent))
        self.th, self.on_select, self.value, self.rows = th, on_select, value, []
        self.selectable = selectable
        width = width or max([0] + [ListRow(self, th, t, icon=i, hint=h).W for _, t, i, h in items])
        for w in self.winfo_children():
            w.destroy()
        for v, t, i, h in items:
            r = ListRow(self, th, t, icon=i, hint=h, width=width,
                        selected=selectable and v == value, command=lambda v=v: self.select(v, True))
            r.value = v
            r.bind("<Up>", lambda e, r=r: self._move(r, -1))
            r.bind("<Down>", lambda e, r=r: self._move(r, 1))
            r.pack(fill="x")
            self.rows.append(r)

    def _move(self, row, d):
        i = (self.rows.index(row) + d) % len(self.rows)
        self.rows[i].focus_set()
        return "break"

    def select(self, v, notify=False):
        self.value = v
        if self.selectable:
            for r in self.rows:
                r.selected = r.value == v
                r.paint()
        if notify and self.on_select:
            self.on_select(v)

    def focus_selected(self):
        for r in self.rows:
            if r.value == self.value:
                focus_auto(r)
                return
        if self.rows:
            focus_auto(self.rows[0])


class Card(tk.Canvas):
    """Скруглённая карточка слоя popup: surface-raised, рамка 1 px border-strong, радиус md;
    содержимое — в .body с отступами pad = (по бокам, сверху, снизу). Размер — по НАСТОЯЩЕМУ
    размеру содержимого (после update_idletasks), не по формуле. bg — цвет вокруг (на нём
    сглаживаются углы); None — цвет-ключ окна (углы прозрачные, без сглаживания)."""

    def __init__(self, parent, th, pad, bg=None):
        super().__init__(parent, bg=bg or th.tech("transparent_key"), highlightthickness=0, bd=0, takefocus=0)
        self.th, self.pad, self.around = th, pad, bg
        self.body = tk.Frame(self, bg=th.c("surface-raised"))

    def reshape(self):
        th = self.th
        px, top, bottom = self.pad
        self.body.update_idletasks()
        W = self.body.winfo_reqwidth() + 2 * px
        H = self.body.winfo_reqheight() + top + bottom
        self.delete("all")
        self.configure(width=W, height=H)
        args = (W, H, th.r("md"), th.c("surface-raised"))
        kw = {"border": th.c("border-strong"), "border_w": th.size("border")}
        self._img = (paint.rounded(*args, self.around, **kw) if self.around else
                     paint.rounded_hard(*args, th.tech("transparent_key"), **kw))
        self.create_image(0, 0, anchor="nw", image=self._img)
        self.create_window(px, top, anchor="nw", window=self.body)


class Popup(tk.Toplevel):
    """Слой popup: окно-меню поверх, закрывается по Esc и при потере фокуса.

    hooks["open"] (после захвата фокуса) / hooks["close"] — функции f(popup) уровня ОС, которые программа
    подключает сама (например, чтобы главное окно не мигало «неактивным», пока открыт список)."""

    hooks = {"open": [], "close": []}
    _open = set()            # открытые сейчас всплывающие окна (пока есть — подсказок нет)
    # границы монитора для точки (x, y) -> (l, t, r, b); программа подключает свою (WinAPI)
    screen_bounds = None

    def __init__(self, anchor, th, build, below=True, card=None, within=None, kind=None):
        """card=(x, top, bottom) — скруглённая карточка (радиус md, рамка border-strong) с этими
        отступами вокруг содержимого; без card — прямоугольная панель. within — окно, за
        правый/левый край которого окно не выходит (при нехватке места сдвигается влево)."""
        super().__init__(anchor)
        # Сначала скрыто: иначе Windows показывает новое окно в левом верхнем углу экрана,
        # а перенос под кнопку при быстрых кликах иногда не успевает примениться.
        self.withdraw()
        self.th, self.anchor = th, anchor
        self._jobs = []
        self.keep_open = None    # () -> True: фокус ушёл, но окно не закрывать (см. _check_focus)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self._card = None
        if card:
            key = th.tech("transparent_key")
            self.configure(bg=key)
            self.attributes("-transparentcolor", key)      # углы карточки — сквозные
            self._card = Card(self, th, card)
            self._card.pack()
            self.panel = self._card.body
        else:
            self.panel = Panel(self, th, "raised", pad=1)
            self.panel.configure(highlightbackground=th.c("border-strong"))
            self.panel.pack()
        try:
            build(self.panel, self)
        except Exception:
            self.destroy()      # недостроенное окно не показываем
            raise
        if card:
            self.reshape()
        window_badge(self, th, kind)        # режим «номера окон»: kind — вид окна (select, value…)
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        if anchor.winfo_ismapped():
            x = anchor.winfo_rootx() + (getattr(anchor, "ring", 0) if card else 0)   # по краю кнопки
            y = anchor.winfo_rooty() + (anchor.winfo_height() if below else 0)
        else:                   # кнопка не на экране — открываем у курсора, а не в углу
            x, y = self.winfo_pointerxy()
        l, t, r, b = (Popup.screen_bounds(x, y) if Popup.screen_bounds else
                      (0, 0, anchor.winfo_screenwidth(), anchor.winfo_screenheight()))
        if within is not None:
            l = max(l, within.winfo_rootx())
            r = min(r, within.winfo_rootx() + within.winfo_width())
        x = max(l, min(x, r - w))
        if y + h > b:
            y = (anchor.winfo_rooty() if anchor.winfo_ismapped() else y) - h
        y = max(t, y)
        self.geometry(f"+{x}+{y}")
        self.deiconify()
        self.bind("<Escape>", lambda e: (note_key("Escape"), self.close()))
        self.bind("<FocusOut>", self._focus_out)
        self.bind("<Destroy>", lambda e: e.widget is self and self._run_close_hooks())
        Popup._open.add(self)
        self._hooked = True
        for f in Popup.hooks["open"]:     # до захвата фокуса: окно-владелец уже «держит» активный вид
            f(self)
        self.focus_force()

    def reshape(self):
        """Карточку — по новому размеру содержимого (плашка стала полем и т. п.)."""
        if self._card is not None:
            self._card.reshape()

    @classmethod
    def toggle(cls, anchor, th, build, below=True, **kw):
        """Открыть список у кнопки — или закрыть, если он уже открыт.
        Клик по кнопке сначала уводит фокус из списка (он закрывается), поэтому
        «только что закрыт потерей фокуса» тоже считается повторным кликом."""
        import time
        open_ = getattr(anchor, "_popup", None)
        if open_ is not None and open_.winfo_exists():
            open_.close()
            return None
        closed = getattr(anchor, "_popup_lost_focus", 0)
        if (time.monotonic() - closed) * 1000 < th.layout("popup_reopen_ms"):
            anchor._popup_lost_focus = 0
            return None
        pop = cls(anchor, th, build, below, **kw)
        anchor._popup = pop
        return pop

    def _focus_out(self, _):
        self.after(1, self._check_focus)

    def _check_focus(self):
        if getattr(self, "_closed", False):
            return      # уже закрыт выбором пункта — это не «клик мимо»
        try:
            f = self.focus_get()
        except (KeyError, tk.TclError):
            f = None
        inside = f is not None and within(f, self)
        if not inside and self.keep_open is not None:
            # окно-владелец держит окно открытым, пока это нужно ему самому (правка числа на
            # кнопке-якоре). Весь якорь разрешать нельзя: после клика по месту главного окна, не
            # берущему фокус, Tk возвращает фокус якорю — окно не закрывалось и Esc не работал
            inside = self.keep_open()
        if not inside:
            import time
            # «только что закрыт потерей фокуса» — значит, кликнули по самой кнопке-якорю, и тот же
            # клик не должен открыть окно снова (Popup.toggle). Закрыли кликом мимо — не считать:
            # иначе быстрый клик по кнопке сразу после него ничего не открывал
            try:
                under = self.winfo_containing(*self.winfo_pointerxy())
            except (KeyError, tk.TclError):
                under = None
            if under is not None and within(under, self.anchor):
                self.anchor._popup_lost_focus = time.monotonic()
            if f is not None and isinstance(f, Control):
                # закрыли кликом мышью мимо, Tk вернул фокус кнопке главного окна — без кольца
                f._quiet = True
                f.paint()
            self.close()

    def after(self, ms, func=None, *args):
        """Отложенные вызовы окна отменяются при его закрытии: иначе срабатывают после
        уничтожения и попадают в чужую функцию (tkinter переиспользует имена команд)."""
        job = super().after(ms, func, *args)
        if func is not None:
            self._jobs.append(job)
        return job

    def _cancel_jobs(self):
        for job in getattr(self, "_jobs", ()):
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._jobs = []

    @classmethod
    def any_open(cls):
        cls._open = {p for p in cls._open if not getattr(p, "_closed", False) and p.winfo_exists()}
        return bool(cls._open)

    def _run_close_hooks(self):
        Popup._open.discard(self)
        self._cancel_jobs()
        if getattr(self, "_hooked", False):
            self._hooked = False
            for f in Popup.hooks["close"]:
                f(self)

    def share_keys(self):
        """Клавиши, не занятые самим окном, работают как в окне-владельце (P/M/E, Ctrl+Z…):
        в теги привязок каждого виджета добавляется тег окна кнопки-якоря."""
        owner = str(self.anchor.winfo_toplevel())

        def walk(w):
            tags = list(w.bindtags())
            if owner not in tags:
                i = tags.index(str(self)) + 1 if str(self) in tags else len(tags) - 1
                tags.insert(i, owner)
                w.bindtags(tuple(tags))
            for c in w.winfo_children():
                walk(c)
        walk(self)

    def close(self):
        self._closed = True
        # фокус — на кнопку-якорь ДО уничтожения окна, если он был внутри окна (Esc, выбор пункта);
        # закрыли кликом мимо — фокус уже там, куда кликнули, его не трогать
        try:
            f = self.focus_get()
        except (KeyError, tk.TclError):
            f = None
        if f is not None and within(f, self) and self.anchor.winfo_exists():
            focus_auto(self.anchor)
        self._run_close_hooks()
        if getattr(self.anchor, "_popup", None) is self:
            self.anchor._popup = None
        try:
            self.destroy()
        except tk.TclError:
            pass


def menu(anchor, th, items, on_pick, kind="menu"):
    """Меню: items [(value, text, icon, hint)]. kind — вид окна (режим «номера окон»)."""
    def build(panel, pop):
        lv = ListView(panel, th, items, selectable=False,
                      on_select=lambda v: (pop.close(), on_pick(v)))
        lv.pack()
        pop.after(1, lambda: lv.rows and focus_auto(lv.rows[0]))
    return Popup.toggle(anchor, th, build, kind=kind)


CUSTOM = "__custom__"   # значение строки «Своё значение…» в списке


def num_value(v):
    """Число до десятых: целое — int (7), дробное — float (7.5). Округление школьное:
    7,55 -> 7,6 (встроенный round дал бы 7,5: 7.55 во float — это 7.5499…)."""
    v = float(Decimal(str(v)).quantize(Decimal("0.1"), ROUND_HALF_UP))
    return int(v) if v.is_integer() else v


def num_text(v):
    """Число для людей: 7 -> "7", 7.5 -> "7,5" (до десятых, с запятой)."""
    return str(num_value(v)).replace(".", ",")


def custom_text(custom, value):
    """Подпись своего значения по формату custom["fmt"], например "{} с" -> "7,5 с"."""
    if isinstance(value, (int, float)):
        value = num_text(value)
    return custom.get("fmt", "{}").format(value)


def number_popup(anchor, th, value, custom, on_ok):
    """Поле ввода своего числа под кнопкой: Enter — сохранить, Esc — отмена.
    custom: {"lo", "hi", "fmt", "int"=False}. Числа — до десятых (запятая или точка),
    "int": True — только целые. Вне диапазона — ставится ближний край (B16); не число — ошибка."""
    lo, hi = custom["lo"], custom["hi"]
    as_int = custom.get("int", False)

    def norm(v):
        return int(round(v)) if as_int else num_value(v)

    def build(panel, pop):
        bg = panel.cget("bg")
        row = tk.Frame(panel, bg=bg)
        row.pack(padx=th.sp(2), pady=(th.sp(2), 0))
        start = value if isinstance(value, (int, float)) and lo <= value <= hi else lo
        holder = {}

        def commit(_=None):
            raw = holder["f"].get().strip().replace(",", ".")
            try:
                v = float(raw)
            except ValueError:
                v = None
            if v is None or v != v:
                holder["f"].configure_state(error=True)
                return
            v = norm(min(hi, max(lo, v)))
            pop.close()
            on_ok(v)

        def nudge(d):
            try:
                v = float(holder["f"].get().replace(",", ".")) + d
            except ValueError:
                v = lo
            v = lo if v != v else norm(min(hi, max(lo, v)))
            holder["f"].set(num_text(v))
            holder["f"].configure_state(error=False)

        f = TextField(row, th, num_text(start), chars=max(3, len(str(hi)) + (1 if as_int else 3)),
                      on_nudge=nudge)
        f.entry.bind("<Return>", lambda e: (commit(), "break")[1])
        f.pack(side="left")
        holder["f"] = f
        unit = custom_text(custom, "").strip()
        if unit:
            Text(row, th, unit, "body", "secondary").pack(side="left", padx=(th.sp(1), th.sp(2)))
        Button(row, th, "OK", variant="primary", size="sm", command=commit).pack(side="left")
        hint = tr("от {} до {}").format(lo, hi) + ("" if as_int else tr(", можно дробное: 2,5"))
        Text(panel, th, hint + tr("  ·  Enter — сохранить, Esc — отмена"), "caption", "secondary").pack(
            anchor="w", padx=th.sp(3), pady=(th.sp(1), th.sp(2)))

        def focus():
            f._quiet = INPUT["last"] == "mouse"   # открыли мышью — без кольца, только рамка поля
            f.entry.focus_set()
            f.entry.select_range(0, "end")
        pop.after(1, focus)
    return Popup.toggle(anchor, th, build, kind="custom")


def number_label(spec, value):
    """Подпись числа: особые значения — словами («Без лимита»), иначе по формату «3 с»;
    None — параметра сейчас нет (поле неактивно)."""
    if value is None:
        return "—"
    special = spec.get("special", {})
    if value in special:
        return special[value]
    return spec.get("fmt", "{}").format(num_text(value))


def chip_label(spec, value):
    """Подпись плашки и края шкалы: особое значение — словами, иначе по `chip_fmt`
    («5 с» у времени, «4» у размера и непрозрачности)."""
    special = spec.get("special", {})
    if value in special:
        return special[value]
    return spec.get("chip_fmt", "{}").format(num_text(value))


class Chip(Control):
    """Плашка быстрого значения в окошке: высота value_chip_h, отступы sp(2), радиус sm, рамка
    1 px border, текст caption. Выбранная (= текущее значение) — accent-soft и рамка accent-fg.
    `start_edit` — плашка становится полем (`InlineEdit`) той же высоты."""

    def __init__(self, parent, th, text, value, *, selected=False, command=None, **kw):
        self.text, self.value = text, value
        self._edit = None
        super().__init__(parent, th, self._natural_w(th, text), th.size("value_chip_h") + 2 * (th.size("focus") + 1),
                         selected=selected, command=command, **kw)
        self.paint()

    @staticmethod
    def _natural_w(th, text):
        return th.measure(text, "caption") + 2 * th.sp(2) + 2 * (th.size("focus") + 1)

    def relabel(self, text, value):
        self.text, self.value = text, value
        self.W = self._natural_w(self.th, text)
        self.configure(width=self.W)
        self.paint()

    @property
    def is_focus(self):
        return super().is_focus and self._edit is None

    def activate(self):
        if self._edit is None:          # второе отпускание двойного клика — уже поле
            super().activate()

    def start_edit(self, text, spec, on_end, focus=True):
        """Плашка — поле: ширина под самое длинное число (до max), высота плашки, число выделено."""
        th = self.th
        ring = th.size("focus") + 1
        vmax = spec.get("max", spec.get("hi", 30))
        fw = max(self.W - 2 * ring, th.measure(num_text(vmax)) + 2 * (th.size("focus") + th.sp(1)))
        self.W = fw + 2 * ring
        self.configure(width=self.W)
        self.delete("all")

        def end(v, accepted):
            on_end(v, accepted)
            self.after_idle(self._edit_gone)
        self._edit = InlineEdit(self, th, ring, self.H // 2, fw, text, spec, self.bg, lambda v: None, end,
                                live=False, h=th.size("value_chip_h"), focus=focus)

    def _edit_gone(self):
        self._edit = None
        self.relabel(self.text, self.value)

    def paint(self):
        if self._edit is not None:
            return                      # поле рисует себя само
        self.delete("all")
        th = self.th
        if self.selected:
            fill, border = th.c("accent-soft"), th.c("accent-fg")
        else:
            fill = th.c("control-pressed" if self.is_pressed else "control-hover" if self.is_hover else "surface-raised")
            border = th.c("border-strong" if self.is_hover else "border")
        self._bg_image(fill, border, radius=th.r("sm"))
        self.create_text(self.W // 2, self.H // 2, text=self.text, fill=th.c("text-primary"),
                         font=th.font("caption"))


class RepeatButton(IconButton):
    """Кнопка − / + окошка значения: квадрат control_sm, рамка border, иконка 16. Нажатие —
    шаг сразу; удержание — повтор после TIMING.repeat_delay каждые TIMING.repeat_every мс.
    Отпускание, уход курсора и уничтожение останавливают повтор."""

    def __init__(self, parent, th, icon, tooltip, step, **kw):
        super().__init__(parent, th, icon, tooltip, variant="secondary", size="sm", **kw)
        self.step, self._rep = step, None
        self.bind("<Destroy>", lambda e: self._stop(), add="+")

    def _on_press(self, e):
        super()._on_press(e)
        if self.interactive:
            self.step()
            self._rep = self.after(self.th.timing("repeat_delay"), self._again)

    def _again(self):
        self.step()
        self._rep = self.after(self.th.timing("repeat_every"), self._again)

    def _stop(self):
        if self._rep:
            try:
                self.after_cancel(self._rep)
            except tk.TclError:
                pass
            self._rep = None

    def _on_release(self, e):
        self._stop()
        self.pressed = False
        self.paint()

    def _on_leave(self, e):
        self._stop()
        super()._on_leave(e)

    def activate(self):            # Space / Enter — один шаг
        self.step()


def value_panel(panel, th, value, spec, on_change, title=None, on_resize=None):
    """Содержимое окошка значения (время, размер, непрозрачность), сверху вниз: [заголовок],
    ряд плашек быстрых значений, строка «− ползунок +», под ползунком — края шкалы.

    spec: lo/hi/step — ползунок (целые); min/max — допустимое значение (больше hi — ползунок в
    правом краю, плашки не выбраны, значение принимается); nudge — шаг − / + и стрелок; quick —
    значения плашек; fmt — подпись «{} с», chip_fmt — подпись плашек и краёв, special —
    {0: "Без лимита"}. Числа — до десятых (num_value). title — заголовок (окошко из «…»: на панели
    нет кнопки с числом): слева название жирным, справа текущее значение, под ним линия border.
    Возвращает {"slider", "chips", "sync"(v)}."""
    lo, hi, step = spec.get("lo", 0), spec.get("hi", 30), spec.get("step", 1)
    vmin, vmax = spec.get("min", lo), spec.get("max", hi)
    nudge = spec.get("nudge", step)
    quick = spec.get("quick", ())
    quick = list(quick() if callable(quick) else quick)
    ring = th.size("focus") + 1
    btn_w = th.size("control_sm") + 2 * ring     # кнопка − / + с полем под кольцо
    bg = th.c("surface-raised")
    state = {"v": value if value is not None else vmin}

    def apply(v, notify=True):
        v = min(vmax, max(vmin, num_value(v)))
        state["v"] = v
        s.set(min(hi, max(lo, v)))          # вне шкалы — в край
        for c in chips:
            if c.selected != (c.value == v):
                c.configure_state(selected=c.value == v)
        if head is not None:
            draw_head()
        if notify:
            on_change(v)

    head = None
    hs = {"hover": False, "edit": None, "box": None}
    if title:
        hw = th.size("value_slider_w") + 2 * btn_w - 2 * ring
        row_h = max(th.line("body"), th.size("edit_h"))
        head = tk.Canvas(panel, bg=bg, highlightthickness=0, bd=0, takefocus=0, width=hw,
                         height=row_h + th.sp(2) + th.size("border"))
        head.pack(fill="x", padx=ring, pady=(0, th.sp(2)))

        def draw_head():
            """Строка заголовка: название жирным слева, значение справа (число — правится
            кликом: наведение подсвечивает, клик — поле), под строкой линия border."""
            keep = hs["edit"]._items if hs["edit"] is not None else []
            for i in head.find_all():
                if i not in keep:
                    head.delete(i)
            W = max(head.winfo_width(), int(head.cget("width"))) if head.winfo_ismapped() else hw
            cy = row_h // 2
            head.create_text(0, cy, anchor="w", text=title, font=th.font("body", "strong"), fill=th.c("text-primary"))
            num, unit = number_parts(spec, state["v"])
            if hs["edit"] is not None:
                unit = spec.get("fmt", "{}").split("{}")[-1]
            uw = th.measure(unit)
            if unit:
                head.create_text(W, cy, anchor="e", text=unit, font=th.font("body"), fill=th.c("text-primary"))
            if hs["edit"] is None:
                nw = th.measure(num)
                hs["box"] = (W - uw - nw, nw)
                if hs["hover"]:
                    pad = th.sp(1)
                    hs["img"] = number_hover_box(head, th, W - uw - nw - pad, cy, nw + 2 * pad, bg)
                head.create_text(W - uw, cy, anchor="e", text=num, font=th.font("body"), fill=th.c("text-primary"))
            head.create_line(0, row_h + th.sp(2), W, row_h + th.sp(2), fill=th.c("border"), width=th.size("border"))
            for i in keep:
                head.tag_raise(i)

        def over(e):
            b = hs["box"]
            return b is not None and b[0] <= e.x <= b[0] + b[1] and e.y <= row_h

        def head_motion(e):
            hov = hs["edit"] is None and over(e)
            if hov != hs["hover"]:
                hs["hover"] = hov
                head.configure(cursor="xterm" if hov else "")
                draw_head()

        def head_leave(_):
            if hs["hover"]:
                hs["hover"] = False
                draw_head()

        def head_click(e):
            if hs["edit"] is not None or not over(e):
                return
            note_mouse()
            hs["hover"], hs["orig"] = False, state["v"]
            W = head.winfo_width()
            fw = edit_field_w(th, spec)
            uw = th.measure(spec.get("fmt", "{}").split("{}")[-1])
            hs["edit"] = InlineEdit(head, th, W - uw - fw, row_h // 2, fw,
                                    num_text(state["v"]), spec, bg, lambda v: apply(v), head_end)
            draw_head()

        def head_end(v, accepted):
            if not accepted and state["v"] != hs["orig"]:
                apply(hs["orig"])               # Esc или неверный ввод — прежнее значение
            focus_auto(s)                       # фокус — ДО уничтожения поля
            head.after_idle(head_gone)

        def head_gone():
            hs["edit"] = None
            draw_head()
        head.bind("<Motion>", head_motion)
        head.bind("<Leave>", head_leave)
        head.bind("<ButtonPress-1>", head_click)
        head.bind("<Configure>", lambda e: draw_head())

    chips = []
    row = tk.Frame(panel, bg=bg)
    row.pack(anchor="w")
    gap = max(0, th.size("value_chip_gap") - 2 * ring)
    def chip_click(q):
        state["before"] = state["v"]    # первый клик двойного клика — значение до него
        apply(q)

    def chip_double(c):
        """Двойной клик: значение — как было ДО первого клика; плашка — поле с текущим значением
        контрола. Enter — записать число в плашку и применить, Esc — отмена. Порядок и число
        плашек не меняются, одинаковых не бывает; новые значения сохраняются сразу."""
        if "before" in state:
            apply(state.pop("before"))
        if c._edit is not None:
            return

        def end(v, accepted):
            others = [o.value for o in chips if o is not c]
            focus_auto(s)                         # фокус — ДО уничтожения поля
            if accepted and v not in others:
                c.text, c.value = chip_label(spec, v), v
                quick[chips.index(c)] = v
                if spec.get("save_quick"):
                    spec["save_quick"](list(quick))
                apply(v)
            if on_resize:
                panel.after_idle(on_resize)
        c.start_edit(num_text(state["v"]), spec, end)
        if on_resize:
            on_resize()

    for q in quick:
        c = Chip(row, th, chip_label(spec, q), q, selected=q == state["v"])
        c.command = lambda c=c: chip_click(c.value)   # ТЕКУЩЕЕ значение: двойной клик его меняет
        c.on_double = lambda c=c: chip_double(c)
        c.bind("<Double-Button-1>", lambda e, c=c: c.on_double())
        c.pack(side="left", padx=(0, gap))
        chips.append(c)

    line = tk.Frame(panel, bg=bg)
    line.pack(anchor="w", pady=(max(0, th.size("value_row_gap") - 2 * ring), 0))
    RepeatButton(line, th, "minus", tr("Меньше"), lambda: apply(state["v"] - nudge)).pack(side="left")
    s = Slider(line, th, min(hi, max(lo, state["v"])), lo, hi, step, width=th.size("value_slider_w"),
               on_change=lambda v: apply(max(vmin, v)))
    s.pack(side="left")
    RepeatButton(line, th, "plus", tr("Больше"), lambda: apply(state["v"] + nudge)).pack(side="left")
    for k, d in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1)):   # стрелки — шаг nudge
        s.bind(f"<{k}>", lambda e, d=d: (apply(state["v"] + d * nudge), "break")[1])

    ends = tk.Frame(panel, bg=bg, width=s.W - 2 * ring, height=th.line("caption"))   # края шкалы
    ends.pack(anchor="w", padx=btn_w + ring)
    ends.pack_propagate(False)
    Text(ends, th, chip_label(spec, lo), "caption", "secondary").pack(side="left")
    Text(ends, th, chip_label(spec, hi), "caption", "secondary").pack(side="right")

    if head is not None:
        draw_head()

    def sync(v):                    # значение сменилось снаружи (другой инструмент и т. п.)
        apply(v, notify=False)
    return {"slider": s, "chips": chips, "sync": sync, "head": head}


def value_popup(anchor, th, value, spec, on_change, title=None, within=None):
    """Окошко значения (`value_panel`) под кнопкой — только через Popup.toggle: скруглённая
    карточка surface-raised, рамка border-strong, отступы value_pad; не выходит за край окна
    within (сдвигается влево). Фокус — на ползунке (стрелки сразу работают). Закрытие: клик
    мимо, Esc, Enter на ползунке. Клавиши окна работают и при открытом окошке (share_keys).
    Возвращает Popup с sync(v)."""
    holder = {}

    def build(panel, p):
        holder.update(value_panel(panel, th, value, spec, on_change, title=title, on_resize=p.reshape))
        s = holder["slider"]
        p.focus_target = s              # сюда возвращается фокус после правки числа
        s.bind("<Return>", lambda e: (p.close(), "break")[1])

        def focus():
            s._quiet = INPUT["last"] == "mouse"
            s.focus_set()
        p.after(1, focus)

    ring = th.size("focus") + 1
    px, top, bottom = th.size("value_pad")
    pop = Popup.toggle(anchor, th, build, card=(px - ring, top - ring, bottom), within=within,
                       kind="value_more" if title else "value")
    if pop is not None:
        pop.share_keys()

        def sync(v):
            if v is None:
                pop.close()
            else:
                holder["sync"](v)
        pop.sync = sync
    return pop


def number_parts(spec, value):
    """Подпись значения на две части — число и единица: ("45,5", " с"); особое значение —
    словом без единицы: ("Без лимита", "")."""
    special = spec.get("special", {})
    if value in special:
        return special[value], ""
    post = spec.get("fmt", "{}").split("{}")[-1]
    return num_text(value), post


def parse_number(text, spec):
    """Ввод числа: запятая или точка, до десятых (num_value); больше max — max, меньше min — min
    (B16); не число — None."""
    try:
        v = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    if v != v:                          # nan
        return None
    lo, hi = spec.get("min", spec.get("lo", 0)), spec.get("max", spec.get("hi", 30))
    return num_value(min(hi, max(lo, v)))   # сначала в предел: 1e400 — бесконечность



def edit_field_w(th, spec):
    """Ширина поля правки числа: самое длинное число (до max, с десятыми) + кольцо и отступы."""
    vmax = spec.get("max", spec.get("hi", 30))
    longest = max((num_text(vmax), num_text(vmax - 0.1)), key=lambda t: th.measure(t))
    return th.measure(longest) + 2 * (th.size("focus") + th.sp(1))


def number_hover_box(cv, th, x, cy, w, bg):
    """Подсветка числа, которое можно править кликом (наведение при открытом окошке):
    фон surface-raised, рамка 1 px border-strong, радиус sm."""
    h = th.size("edit_h")
    img = paint.rounded(int(w), h, th.r("sm"), th.c("surface-raised"), bg, border=th.c("border-strong"),
                        border_w=th.size("border"))
    cv.create_image(x, cy, anchor="w", image=img)
    return img


class InlineEdit:
    """Число, ставшее полем ввода на месте (кнопка значения, заголовок окошка, плашка):
    фон surface-raised, кольцо 2 px focus-ring (здесь кольцо — признак правки, поэтому и от мыши),
    число выделено. Ввод сразу двигает значение (`on_live`); Enter и потеря фокуса — принять,
    Esc — отменить правку (дальше не идёт: окошко не закрывается); неверный ввод — откат к
    прежнему значению без ошибки. `on_end(value, accepted)` вызывается ДО уничтожения поля:
    в нём фокус переводят дальше (иначе фокус Windows теряется, см. CLAUDE.md)."""

    def __init__(self, cv, th, x, cy, w, text, spec, bg, on_live, on_end, live=True, focus=True, h=None):
        self.cv, self.th, self.spec = cv, th, spec
        self.on_live, self.on_end, self.live = on_live, on_end, live
        self.done = False
        h = h or th.size("edit_h")
        ring = th.size("focus")
        self._img = paint.rounded(int(w), h, th.r("sm"), th.c("surface-raised"), bg, border=th.c("focus-ring"),
                                  border_w=ring)
        self._items = [cv.create_image(x, cy, anchor="w", image=self._img)]
        self.entry = tk.Entry(cv, font=th.font("body"), bg=th.c("surface-raised"), fg=th.c("text-primary"),
                              insertbackground=th.c("text-primary"), relief="flat", bd=0, highlightthickness=0,
                              selectbackground=th.c("accent-soft"), selectforeground=th.c("text-primary"))
        pad = ring + th.sp(1)
        self._items.append(cv.create_window(x + pad, cy, anchor="w", window=self.entry,
                                            width=max(1, int(w) - 2 * pad), height=th.line("body")))
        self.entry.insert(0, text)
        self.entry.bind("<Return>", lambda e: (self.finish(True), "break")[1])
        self.entry.bind("<KP_Enter>", lambda e: (self.finish(True), "break")[1])
        self.entry.bind("<Escape>", lambda e: (self.finish(False), "break")[1])
        self.entry.bind("<KeyRelease>", self._typed)
        if focus:                   # focus=False — только показ (витрина)
            self.entry.bind("<FocusOut>", lambda e: self.finish(True))
            self.entry.focus_set()
        self.entry.select_range(0, "end")
        self.entry.icursor("end")

    def _typed(self, e):
        if self.live and e.keysym not in ("Return", "KP_Enter", "Escape"):
            v = parse_number(self.entry.get(), self.spec)
            if v is not None:
                self.on_live(v)

    def get(self):
        return self.entry.get()

    def finish(self, accept):
        if self.done:
            return
        self.done = True
        v = parse_number(self.entry.get(), self.spec) if accept else None
        self.on_end(v, accept and v is not None)
        self.destroy()

    def destroy(self):
        for i in self._items:
            self.cv.delete(i)
        try:
            self.entry.destroy()
        except tk.TclError:
            pass


class NumberField(Control):
    """Число с единицей на панели («3 px», «Без лимита»); клик — окошко значения
    (`value_popup`). Пока окошко открыто: наведение на число подсвечивает его, клик — число
    становится полем (`InlineEdit`), единица остаётся снаружи; окошко не закрывается, ползунок
    идёт вживую. spec — см. value_panel; icon — иконка слева. value=None — параметра сейчас нет:
    поле неактивно и показывает «—». Ширина — заранее под самую длинную подпись и под поле
    правки: при смене значения и правке соседние кнопки не сдвигаются."""

    def __init__(self, parent, th, value, spec, on_change=None, icon=None, **kw):
        self.value, self.spec, self.on_change, self.icon_name = value, spec, on_change, icon
        self._pop = None
        self._edit = None
        self._num_box = None           # (x, w) числа на кнопке
        self._num_hover = False
        ring = th.size("focus") + 1
        vmax = spec.get("max", spec.get("hi", 30))
        texts = [number_label(spec, v) for v in [vmax - 0.1, vmax, spec.get("hi", 30)] + list(spec.get("special", {}))]
        unit_w = max(th.measure(number_parts(spec, v)[1]) for v in (vmax,))
        content = max(max(th.measure(t) for t in texts), edit_field_w(th, spec) + unit_w)
        width = content + (th.size("icon_sm") + th.sp(2) if icon else 0) + th.size("icon_sm") + 3 * th.sp(3)
        super().__init__(parent, th, width + 2 * ring, th.size("control") + 2 * ring, **kw)
        self.bind("<Down>", lambda e: (self.activate(), "break")[1])
        self.bind("<Motion>", self._motion, add="+")
        self.paint()

    def label(self):
        return number_label(self.spec, self.value)

    @property
    def is_focus(self):
        # фокус в поле правки Tk сообщает и кнопке (родителю): кольцо тогда только у поля
        return super().is_focus and self._edit is None

    def activate(self):
        if self.value is None:
            return
        self._pop = value_popup(self, self.th, self.value, self.spec, self._changed,
                                within=self.winfo_toplevel())
        if self._pop is not None:
            self._pop.keep_open = self._keeps_popup
        self.paint()

    def _keeps_popup(self):
        """Окошко не закрывать, хотя фокус ушёл из него: идёт правка числа на кнопке или клик
        именно по числу (Windows отдаёт фокус полю не сразу — решать по курсору над числом)."""
        if self._edit is not None:
            return True
        try:
            x, y = self.winfo_pointerxy()
            x, y = x - self.winfo_rootx(), y - self.winfo_rooty()
        except tk.TclError:
            return False
        return 0 <= y <= self.winfo_height() and self._over_number(type("P", (), {"x": x})())

    def _changed(self, v):
        self.value = v
        self.paint()
        if self.on_change:
            self.on_change(v)

    def is_open(self):
        return self._pop is not None and self._pop.winfo_exists() and not getattr(self._pop, "_closed", False)

    def _over_number(self, e):
        if self._num_box is None:
            return False
        x, w = self._num_box
        return x <= e.x <= x + w

    def _motion(self, e):
        hov = self.is_open() and self._edit is None and self._over_number(e)
        if hov != self._num_hover:
            self._num_hover = hov
            self.configure(cursor="xterm" if hov else "hand2")
            self.paint()

    def _on_leave(self, e):
        self._num_hover = False
        super()._on_leave(e)

    def _on_press(self, e):
        if self.is_open() and self._edit is None and self._over_number(e):
            note_mouse()
            self.start_edit()
            return
        if self._edit is not None:     # клик по кнопке во время правки — правку принять
            self._edit.finish(True)
        super()._on_press(e)

    def start_edit(self):
        """Число на кнопке становится полем ввода (окошко остаётся открытым)."""
        if not self.is_open() or self.value is None:
            return
        th = self.th
        self._num_hover = False
        self.paint()
        x = self._num_box[0] - th.size("focus") - th.sp(1)
        self._edit = InlineEdit(self, th, x, self.H // 2, edit_field_w(th, self.spec), num_text(self.value),
                                self.spec, self._fill, self._edit_live, self._edit_end)
        self._edit_orig = self.value
        self.paint()

    def _edit_live(self, v):
        self._changed(v)
        if self.is_open():
            self._pop.sync(v)

    def _edit_end(self, v, accepted):
        if not accepted and self.value != self._edit_orig:
            self._edit_live(self._edit_orig)       # Esc или неверный ввод — прежнее значение
        # фокус — ДО уничтожения поля: на ползунок окошка (второй Esc закроет окошко)
        if self.is_open() and getattr(self._pop, "focus_target", None) is not None:
            focus_auto(self._pop.focus_target)
        else:
            focus_auto(self)
        self.after_idle(self._edit_gone)

    def _edit_gone(self):
        self._edit = None
        self.paint()

    def set(self, v):
        """Новое значение снаружи; открытое окошко сразу его показывает (None — закрывается)."""
        changed = v != self.value
        self.value = v
        if changed and self.is_open():
            self._pop.sync(v)
        self.paint()

    def get(self):
        return self.value

    def paint(self):
        keep = [i for i in getattr(self._edit, "_items", ())] if self._edit is not None else []
        for i in self.find_all():
            if i not in keep:
                self.delete(i)
        th = self.th
        off = self.disabled or self.value is None
        if off:
            fill, border, fg, ifg = th.c("control"), th.c("border"), th.c("text-disabled"), th.c("text-disabled")
        else:
            fill = th.c("control-pressed" if self.is_pressed or self.is_open() else
                        "control-hover" if self.is_hover else "control")
            border = th.c("danger-fg") if self.error else th.c("border-strong" if self.is_hover else "border")
            fg, ifg = th.c("text-primary"), th.c("text-secondary")
        self._fill = fill
        self._bg_image(fill, border)
        x, cy, isz = self.ring + th.sp(3), self.H // 2, th.size("icon_sm")
        if self.icon_name:
            self.create_image(x, cy, anchor="w", image=get_icon(self.icon_name, isz, ifg))
            x += isz + th.sp(2)
        if self.value is None:
            self.create_text(x, cy, anchor="w", text=self.label(), fill=fg, font=th.font("body"))
            self._num_box = None
        else:
            num, unit = number_parts(self.spec, self.value)
            nw = th.measure(num)
            self._num_box = (x, nw)
            if self._edit is not None:
                ux = x - th.size("focus") - th.sp(1) + edit_field_w(th, self.spec)
            else:
                if self._num_hover:
                    pad = th.sp(1)
                    self._hover_img = number_hover_box(self, th, x - pad, cy, nw + 2 * pad, fill)
                self.create_text(x, cy, anchor="w", text=num, fill=fg, font=th.font("body"))
                ux = x + nw
            if self._edit is not None:       # в поле — число («0» у «Без лимита»), единица снаружи
                unit = self.spec.get("fmt", "{}").split("{}")[-1]
            if unit:
                self.create_text(ux, cy, anchor="w", text=unit, fill=fg, font=th.font("body"))
        self.create_image(self.W - self.ring - th.sp(2), cy, anchor="e",
                          image=get_icon("chevron_down", isz, ifg))
        for i in keep:                  # поле правки — поверх фона
            self.tag_raise(i)


class Select(Control):
    """Выпадающий список. options: [(value, text)] или [(value, text, icon)].
    custom={"lo", "hi", "fmt"} — в конце списка строка «Своё значение…» с вводом числа."""

    def __init__(self, parent, th, options, value, on_change=None, width=None, prefix="", custom=None, **kw):
        self.options = [o if len(o) == 3 else (o[0], o[1], None) for o in options]
        self.value, self.on_change, self.prefix, self.custom = value, on_change, prefix, custom
        ring = th.size("focus") + 1
        if width is None:
            texts = [t for _, t, _ in self.options]
            if custom:                               # место и под самое длинное своё значение
                texts.append(custom_text(custom, custom["hi"] - 0.1))   # самое длинное: «3599,9 с»
            longest = max(th.measure(prefix + t) for t in texts)
            icon_w = th.size("icon_sm") + th.sp(2) if any(i for _, _, i in self.options) else 0
            width = longest + icon_w + th.size("icon_sm") + 3 * th.sp(3)
        super().__init__(parent, th, width + 2 * ring, th.size("control") + 2 * ring, **kw)
        self.bind("<Down>", lambda e: (self.activate(), "break")[1])
        self.paint()

    def is_custom_value(self):
        return all(v != self.value for v, _, _ in self.options)

    def label(self):
        for v, t, i in self.options:
            if v == self.value:
                return t, i
        icon = next((i for _, _, i in self.options if i), None)
        if self.custom:
            return custom_text(self.custom, self.value), icon
        return str(self.value), icon

    def activate(self):
        th = self.th
        items = [(v, t, i, None) for v, t, i in self.options]
        current = self.value
        if self.custom:
            title = self.custom.get("label", tr("Своё значение…"))
            if self.is_custom_value():
                title = f"{title}  ({custom_text(self.custom, self.value)})"
                current = CUSTOM
            items.append((CUSTOM, title, "plus", None))
        width = max([self.W - 2 * self.ring] +
                    [th.measure(t) + th.size("icon_sm") + 4 * th.sp(3) for _, t, _, _ in items])

        def pick(v, pop):
            pop.close()
            if v == CUSTOM:
                self.after(1, self.ask_custom)
            else:
                self.set(v, True)
                focus_auto(self)

        def build(panel, pop):
            lv = ListView(panel, th, items, value=current, width=width, on_select=lambda v: pick(v, pop))
            lv.pack()
            pop.after(1, lv.focus_selected)
        Popup.toggle(self, th, build, kind="select")

    def ask_custom(self):
        number_popup(self, self.th, self.value, self.custom, lambda v: (self.set(v, True), focus_auto(self)))

    def set(self, v, notify=False):
        self.value = v
        self.paint()
        if notify and self.on_change:
            self.on_change(v)

    def get(self):
        return self.value

    def paint(self):
        self.delete("all")
        th = self.th
        if self.disabled:
            fill, border, fg = th.c("control"), th.c("border"), th.c("text-disabled")
        else:
            fill = th.c("control-pressed" if self.is_pressed else "control-hover" if self.is_hover else "control")
            border = th.c("danger-fg") if self.error else th.c("border-strong" if self.is_hover else "border")
            fg = th.c("text-primary")
        self._bg_image(fill, border)
        text, ic = self.label()
        x = self.ring + th.sp(3)
        cy = self.H // 2
        isz = th.size("icon_sm")
        if ic:
            self.create_image(x, cy, anchor="w", image=get_icon(ic, isz, th.c("text-secondary")))
            x += isz + th.sp(2)
        self.create_text(x, cy, anchor="w", text=self.prefix + text, fill=fg, font=th.font("body"))
        self.create_image(self.W - self.ring - th.sp(2), cy, anchor="e",
                          image=get_icon("chevron_down", isz, th.c("text-secondary")))


class Tabs(tk.Frame):
    """Горизонтальные вкладки. items: [(value, text)]. Стрелки — переключение."""

    def __init__(self, parent, th, items, value, on_change=None):
        super().__init__(parent, bg=parent_bg(parent))
        self.th, self.value, self.on_change, self.tabs = th, value, on_change, []
        for v, t in items:
            tab = _Tab(self, th, t, v)
            tab.pack(side="left")
            self.tabs.append(tab)

    def select(self, v, notify=False):
        self.value = v
        for t in self.tabs:
            t.paint()
        if notify and self.on_change:
            self.on_change(v)

    def move(self, tab, d):
        i = (self.tabs.index(tab) + d) % len(self.tabs)
        self.tabs[i].focus_set()
        self.select(self.tabs[i].value, True)


class _Tab(Control):
    def __init__(self, tabs, th, text, value):
        self.tabs, self.text, self.value = tabs, text, value
        ring = th.size("focus") + 1
        super().__init__(tabs, th, th.measure(text, "body", "strong") + 2 * th.sp(3) + 2 * ring,
                         th.size("control") + 2 * ring, command=lambda: tabs.select(value, True))
        self.bind("<Left>", lambda e: (tabs.move(self, -1), "break")[1])
        self.bind("<Right>", lambda e: (tabs.move(self, 1), "break")[1])
        self.paint()

    def paint(self):
        self.delete("all")
        th = self.th
        on = self.tabs.value == self.value
        fill = th.c("control-hover") if self.is_hover and not on else self.bg
        self._bg_image(fill, None, radius=th.r("sm"))
        fg = th.c("text-primary") if on or self.is_hover else th.c("text-secondary")
        self.create_text(self.W // 2, self.H // 2, text=self.text, fill=fg,
                         font=th.font("body", "strong" if on else "regular"))
        if on:
            b = th.size("focus")
            self.create_rectangle(self.ring + th.sp(2), self.H - self.ring - b,
                                  self.W - self.ring - th.sp(2), self.H - self.ring,
                                  fill=th.c("accent-fg"), outline="")


# ==========================================================================
# Прокрутка
# ==========================================================================
class Scrollbar(tk.Canvas):
    """Тонкая полоса прокрутки, совместимая с xview/yview Tk."""

    def __init__(self, parent, th, orient="vertical", command=None):
        self.th, self.orient, self.command = th, orient, command
        s = th.size("scrollbar")
        bg = parent_bg(parent)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0,
                         width=s if orient == "vertical" else 1,
                         height=s if orient == "horizontal" else 1)
        self.first, self.last = 0.0, 1.0
        self.hover = False
        self._drag = None
        self.bind("<Configure>", lambda e: self.paint())
        self.bind("<Enter>", lambda e: self._hov(True))
        self.bind("<Leave>", lambda e: self._hov(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)

    def _hov(self, v):
        self.hover = v
        self.paint()

    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        self.paint()

    def _len(self):
        return self.winfo_height() if self.orient == "vertical" else self.winfo_width()

    def _press(self, e):
        pos = (e.y if self.orient == "vertical" else e.x) / max(1, self._len())
        if not (self.first <= pos <= self.last) and self.command:
            self.command("moveto", max(0, pos - (self.last - self.first) / 2))
        self._drag = (pos, self.first)

    def _motion(self, e):
        if self._drag and self.command:
            pos = (e.y if self.orient == "vertical" else e.x) / max(1, self._len())
            self.command("moveto", self._drag[1] + pos - self._drag[0])

    def paint(self):
        self.delete("all")
        if self.last - self.first >= 0.999:
            return
        th = self.th
        L = self._len()
        s = th.size("scrollbar")
        t = max(2, s - th.sp(1) if self.hover else s // 2)
        a, b = int(self.first * L), int(self.last * L)
        b = max(b, a + 2 * s)
        col = th.c("text-secondary" if self.hover else "scrollbar")
        if self.orient == "vertical":
            self.create_image((s - t) // 2, a, anchor="nw", image=paint.rounded(t, b - a, t // 2, col, self.cget("bg")))
        else:
            self.create_image(a, (s - t) // 2, anchor="nw", image=paint.rounded(b - a, t, t // 2, col, self.cget("bg")))


class ScrollArea(tk.Frame):
    """Прокручиваемая по вертикали область. Содержимое — в .body."""

    def __init__(self, parent, th, tone="surface"):
        super().__init__(parent, bg=th.c(tone))
        self.cv = tk.Canvas(self, bg=th.c(tone), highlightthickness=0, bd=0)
        self.sb = Scrollbar(self, th, "vertical", self.cv.yview)
        self.cv.configure(yscrollcommand=self.sb.set)
        self.sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.cv, bg=th.c(tone))
        self.win = self.cv.create_window(0, 0, anchor="nw", window=self.body)
        self.body.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))
        self.bind_all_wheel()

    def bind_all_wheel(self):
        def wheel(e):
            self.cv.yview_scroll(-e.delta // 120, "units")
        self.cv.bind("<Enter>", lambda e: self.cv.bind_all("<MouseWheel>", wheel))
        self.cv.bind("<Leave>", lambda e: self.cv.unbind_all("<MouseWheel>"))


# ==========================================================================
# Состояния: прогресс, индикатор, тост, пустое состояние, строка настройки
# ==========================================================================
class ProgressBar(tk.Canvas):
    """Индикатор прогресса: value 0..1 или None (неопределённый)."""

    def __init__(self, parent, th, width=None, value=None):
        self.th = th
        self.bg = parent_bg(parent)
        self.W = width or th.size("select_w")
        self.H = th.size("slider_track")
        super().__init__(parent, width=self.W, height=self.H, bg=self.bg, highlightthickness=0, bd=0)
        self.value = value
        self._pos = 0
        self._job = None
        self.paint()
        if value is None:
            self._tick()

    def _tick(self):
        if self.value is not None or not self.winfo_exists():
            return
        self._pos = (self._pos + 0.08) % 1.4
        self.paint()
        self._job = self.after(self.th.timing("spinner_step"), self._tick)

    def set(self, value):
        was_none = self.value is None
        self.value = value
        self.paint()
        if value is None and not was_none:
            self._tick()

    def paint(self):
        self.delete("all")
        th = self.th
        r = self.H // 2
        self.create_image(0, 0, anchor="nw", image=paint.rounded(self.W, self.H, r, th.c("control-pressed"), self.bg))
        if self.value is None:
            seg = self.W // 3
            x = int((self._pos - 0.4) * self.W)
            a, b = max(0, x), min(self.W, x + seg)
        else:
            a, b = 0, int(self.W * max(0, min(1, self.value)))
        if b - a > 1:
            self.create_image(a, 0, anchor="nw", image=paint.rounded(b - a, self.H, r, th.c("accent"), self.bg))


class StatusDot(tk.Canvas):
    """Цветной индикатор состояния (tone: danger|success|warning|accent), может мигать."""

    def __init__(self, parent, th, tone="danger", blink=False):
        self.th, self.tone = th, tone
        self.bg = parent_bg(parent)
        s = th.sp(3)
        super().__init__(parent, width=s, height=s, bg=self.bg, highlightthickness=0, bd=0)
        self.on = True
        self.blink = blink
        self.paint()
        if blink:
            self._tick()

    def _tick(self):
        if not self.blink or not self.winfo_exists():
            return
        self.on = not self.on
        self.paint()
        self.after(self.th.timing("blink"), self._tick)

    def set(self, tone=None, blink=None):
        if tone:
            self.tone = tone
        if blink is not None:
            start = blink and not self.blink
            self.blink = blink
            self.on = True
            if start:
                self._tick()
        self.paint()

    def paint(self):
        self.delete("all")
        token = {"danger": "danger-fg", "success": "success", "warning": "warning",
                 "accent": "accent-fg", "muted": "text-secondary"}[self.tone]
        s = self.th.sp(3)
        if self.on:
            self.create_image(0, 0, anchor="nw", image=paint.circle(s, self.th.c(token), self.bg))


TOAST_KINDS = {"info": ("info", "text-secondary"), "success": ("success", "success"),
               "warning": ("warning", "warning"), "error": ("error", "danger-fg")}


class Toast(Panel):
    """Уведомление внутри окна: иконка вида, текст, действия, закрыть."""

    def __init__(self, parent, th, text, kind="info", actions=(), on_close=None):
        super().__init__(parent, th, "raised", pad=2)
        self.configure(highlightbackground=th.c("border-strong"))
        ic, tone = TOAST_KINDS[kind]
        # крестик — первым: он всегда получает своё место, а текст переносится в оставшемся
        close = IconButton(self, th, "close", tr("Закрыть"), command=lambda: on_close and on_close(self))
        close.pack(side="right", anchor="n")
        icon_pad = (th.sp(1), th.sp(2))
        tk.Label(self, image=get_icon(ic, th.size("icon"), th.c(tone)), bg=self.cget("bg")).pack(
            side="left", padx=icon_pad, anchor="n", pady=th.sp(1))
        body = tk.Frame(self, bg=self.cget("bg"))
        body.pack(side="left", fill="x", expand=True)
        wrap = (th.size("toast_w") - 2 * th.size("border") - 2 * th.sp(2)
                - th.size("icon") - sum(icon_pad) - close.W)
        Text(body, th, text, "body", wrap=wrap).pack(anchor="w", pady=th.sp(1))
        if actions:
            row = tk.Frame(body, bg=self.cget("bg"))
            row.pack(anchor="w")
            for label, cmd in actions:
                Button(row, th, label, variant="ghost", size="sm",
                       command=lambda c=cmd: (c(), on_close and on_close(self))).pack(side="left")
        window_badge(self, th, "toast", corner="nw")


class EmptyState(tk.Frame):
    def __init__(self, parent, th, icon, title, text, actions=(), hint=None):
        super().__init__(parent, bg=parent_bg(parent))
        tk.Label(self, image=get_icon(icon, th.size("icon_lg"), th.c("text-secondary")),
                 bg=self.cget("bg")).pack(pady=(0, th.sp(3)))
        Text(self, th, title, "title", weight="strong", anchor="center").pack()
        Text(self, th, text, "body", "secondary", anchor="center", justify="center").pack(pady=(th.sp(1), th.sp(4)))
        if actions:
            row = tk.Frame(self, bg=self.cget("bg"))
            row.pack()
            for w in actions:
                w(row).pack(side="left", padx=th.sp(1))
        if hint:
            Text(self, th, hint, "caption", "secondary", anchor="center", justify="center").pack(pady=(th.sp(4), 0))


class KeyCap(tk.Canvas):
    """Плашка клавиши: сочетание целиком («Ctrl+Shift+Z») в рамке, как клавиша клавиатуры.
    Только показ — не фокусируется и не нажимается."""

    def __init__(self, parent, th, text):
        self.th, self.text, self.bg = th, text, parent_bg(parent)
        self.W = th.measure(text, "caption") + 2 * th.sp(2)
        self.H = th.size("keycap_h")
        super().__init__(parent, width=self.W, height=self.H, bg=self.bg, highlightthickness=0, bd=0,
                         takefocus=0)
        self._img = paint.rounded(self.W, self.H, th.r("sm"), th.c("control"), self.bg,
                                  border=th.c("border-strong"), border_w=th.size("border"))
        self.create_image(0, 0, anchor="nw", image=self._img)     # держим ссылку: иначе картинку соберут
        self.create_text(self.W // 2, self.H // 2, text=text, fill=th.c("text-primary"), font=th.font("caption"))


def key_caps(parent, th, keys):
    """Ряд плашек: альтернативы через « / » (["Ctrl+Y", "Ctrl+Shift+Z"])."""
    row = tk.Frame(parent, bg=parent_bg(parent))
    for i, k in enumerate(keys):
        if i:
            Text(row, th, "/", "caption", "secondary").pack(side="left", padx=th.sp(1))
        KeyCap(row, th, k).pack(side="left")
    return row


class SettingRow(tk.Frame):
    """Строка настройки: название + описание слева, контрол справа."""

    def __init__(self, parent, th, title, description=None, build=None, error=None, wrap=None,
                 stacked=False, avail=None):
        """stacked=True — контрол всегда под подписью; иначе переносится под подпись
        автоматически, когда не помещается справа."""
        super().__init__(parent, bg=parent_bg(parent))
        self.th, self.force_stacked, self.stacked = th, stacked, None
        self.left = left = tk.Frame(self, bg=self.cget("bg"))
        self.title_label = Text(left, th, title, "body")
        self.title_label.pack(anchor="w")
        wrap = wrap or th.size("row_min_w") // 2
        self.wrap = wrap
        self.desc = None
        self.title_icon = None
        if description:
            self.desc = Text(left, th, description, "caption", "secondary", wrap=wrap)
            self.desc.pack(anchor="w")
        self.err = None
        self.set_error(error)
        self.control = build(self) if build else None
        if not stacked and avail and self.control is not None:   # сразу верная раскладка
            self.control.update_idletasks()
            stacked = avail < self._need()
        self._arrange(stacked)
        if not self.force_stacked:
            self.bind("<Configure>", self._on_resize)

    def add_title_icon(self, name, on):
        """Значок в конце названия (тот же, что у этой функции на панели, например курсор у
        «Показывать курсор»): включено — icon-on, выключено — text-secondary."""
        th = self.th
        line = tk.Frame(self.left, bg=self.left.cget("bg"))
        line.pack(anchor="w", before=self.title_label)
        self.title_label.pack(in_=line, side="left")
        # название создано раньше рамки строки — без подъёма рамка закрывает его (порядок наложения Tk)
        self.title_label.tk.call("raise", self.title_label._w)
        # по центру прописных букв названия: рисунок без полей, поднят на title_icon_lift. Значок
        # ПОВЕРХ строки (place) над пустым местом его ширины: pady растил бы строку и сдвигал текст
        self._title_slot = tk.Frame(line, bg=line.cget("bg"), height=1)
        self._title_slot.pack(side="left", padx=(th.sp(2), 0))
        self.title_icon = tk.Label(line, bg=line.cget("bg"), bd=0)
        self.title_icon.place(in_=self._title_slot, x=0, rely=0.5, y=-th.size("title_icon_lift"), anchor="w")
        self._title_icon_name = name
        self.paint_title_icon(on)

    def paint_title_icon(self, on):
        th = self.th
        img = icon_tight(self._title_icon_name, th.size("title_icon"), th.c("icon-on" if on else "text-secondary"),
                         th.icon_stroke("stroke_on") if on else None)
        self.title_icon.configure(image=img)
        self._title_slot.configure(width=img.width())
        self.title_icon.img = img              # держать картинку, иначе её соберёт сборщик мусора

    def set_error(self, text):
        """Текст ошибки под описанием (None — убрать)."""
        if self.err is not None:
            self.err.destroy()
            self.err = None
        if text:
            self.err = Text(self.left, self.th, text, "caption", "danger", wrap=self.wrap)
            self.err.pack(anchor="w")

    def _need(self):
        return self.th.size("row_min_w") // 2 + self.control.winfo_reqwidth() + self.th.sp(4)

    def _on_resize(self, e):
        if self.control is None or e.width <= 1:
            return
        self._arrange(e.width < self._need())

    def _arrange(self, stacked):
        if stacked == self.stacked:
            return
        self.stacked = stacked
        th = self.th
        self.left.pack_forget()
        if self.control is not None:
            self.control.pack_forget()
        # рядом с контролом — по центру строки: без описания название на одной линии с контролом
        self.left.pack(side="top" if stacked else "left", fill="x", expand=True, anchor="n" if stacked else "w",
                       pady=(th.sp(2), 0 if stacked else th.sp(2)))
        if self.control is None:
            return
        if stacked:
            self.control.pack(side="top", anchor="w", pady=(th.sp(1), th.sp(2)))
        else:
            # отступы сверху и снизу — как у подписи: в строке без описания («Язык», «Тема») контрол
            # выше текста и иначе прижимался к полоскам между строками
            self.control.pack(side="right", anchor="center", padx=(th.sp(4), 0), pady=th.sp(2))
