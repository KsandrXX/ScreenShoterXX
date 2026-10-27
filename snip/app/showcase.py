# -*- coding: utf-8 -*-
"""Витрина: все компоненты платформы во всех состояниях, тёмная и светлая темы рядом.

Запуск: python snipper.pyw --showcase [--scale 125]"""

import sys
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk

from ..core.winapi import system_scale
from ..ui import components as C
from ..ui import paint
from ..ui.icons import ICONS, icon as get_icon
from ..ui.layouts import HudToolbar, KeysSheet, glass_chip, CanvasHud
from ..ui.registry import Registry
from ..ui.tokens import ANNOTATION, CONTRAST_PAIRS, AA, THEMES, Theme, TYPE

STATES = [("normal", {}), ("hover", {"force": {"hover"}}), ("pressed", {"force": {"pressed"}}),
          ("focus", {"force": {"focus"}}), ("disabled", {"disabled": True}),
          ("error", {"error": True}), ("selected", {"selected": True}), ("loading", {"loading": True})]


def section(parent, th, title):
    C.Text(parent, th, title, "title", weight="strong").pack(anchor="w", pady=(th.sp(6), th.sp(2)))
    f = tk.Frame(parent, bg=parent.cget("bg"))
    f.pack(anchor="w", fill="x")
    return f


def state_grid(parent, th, make, states=STATES):
    for i, (name, kw) in enumerate(states):
        C.Text(parent, th, name, "caption", "secondary").grid(row=0, column=i, sticky="w", padx=th.sp(1))
        make(parent, kw).grid(row=1, column=i, sticky="w", padx=th.sp(1), pady=(0, th.sp(2)))


def build_column(parent, th, scale_note):
    col = C.Frame(parent, th, "surface", pad=4, border=True)
    C.Text(col, th, f"Тема: {th.name} · масштаб {int(th.scale * 100)} %{scale_note}", "headline",
           weight="strong").pack(anchor="w")

    # токены цвета
    sec = section(col, th, "Цветовые токены")
    for i, name in enumerate(th.colors):
        r, c = divmod(i, 4)
        cell = tk.Frame(sec, bg=sec.cget("bg"))
        cell.grid(row=r, column=c, sticky="w", padx=(0, th.sp(3)), pady=1)
        tk.Frame(cell, bg=th.c(name), width=th.sp(4), height=th.sp(4), highlightthickness=1,
                 highlightbackground=th.c("border-strong")).pack(side="left")
        C.Text(cell, th, " " + name, "caption", "secondary").pack(side="left")

    sec = section(col, th, f"Контраст (WCAG AA ≥ {AA})")
    worst = paint.glass_worst_bg(th.c("glass-tint"), th.glass("fill_alpha"))
    pairs = [(f, b, th.c(f), th.c(b)) for f, b in CONTRAST_PAIRS] + \
        [("text-primary", "стекло, худший фон", th.c("text-primary"), worst)]
    for i, (fn, bn, fg, bg) in enumerate(pairs):
        r = paint.contrast(fg, bg)
        ok = r >= AA
        cell = tk.Frame(sec, bg=bg, padx=th.sp(1))
        cell.grid(row=i // 2, column=i % 2, sticky="we", padx=(0, th.sp(2)), pady=1)
        tk.Label(cell, text=f"{fn} / {bn}: {r:.1f}", fg=fg, bg=bg, font=th.font("caption")).pack(side="left")
        tk.Label(cell, image=get_icon("check" if ok else "close", th.size("icon_sm"),
                                      fg), bg=bg).pack(side="left")

    sec = section(col, th, "Типографика")
    for role in TYPE:
        row = tk.Frame(sec, bg=sec.cget("bg"))
        row.pack(anchor="w")
        C.Text(row, th, f"{role} {TYPE[role][0]}/{TYPE[role][1]} — Съешь ещё этих булок", role).pack(side="left")
        C.Text(row, th, "  жирный", role, weight="strong").pack(side="left")

    for variant in ("primary", "secondary", "ghost", "danger"):
        sec = section(col, th, f"Кнопка · {variant}")
        state_grid(sec, th, lambda p, kw, v=variant: C.Button(p, th, "Кнопка", icon="save", variant=v, **kw))
    sec = section(col, th, "Кнопка-иконка")
    state_grid(sec, th, lambda p, kw: C.IconButton(p, th, "settings", "Настройки", **kw))

    on_off = [("off", {}), ("on", {"value": True}), ("hover", {"value": True, "force": {"hover"}}),
              ("focus", {"force": {"focus"}}), ("disabled", {"disabled": True}), ("error", {"error": True})]
    sec = section(col, th, "Переключатель")
    state_grid(sec, th, lambda p, kw: C.Toggle(p, th, **kw), on_off)
    sec = section(col, th, "Флажок")
    state_grid(sec, th, lambda p, kw: C.Checkbox(p, th, "Флажок", **kw), on_off)
    sec = section(col, th, "Радиокнопка")
    groups = {}

    def radio(p, kw):
        g = C.RadioGroup("a" if kw.pop("value", False) else None)
        groups[id(g)] = g
        return C.Radio(p, th, g, "a", "Вариант", **kw)
    state_grid(sec, th, radio, on_off)

    sec = section(col, th, "Подсказки: T1 (название + строка), T3 (образец линии), клавиша, недоступный контрол")
    tips = tk.Frame(sec, bg=sec.cget("bg"))
    tips.pack(anchor="w")
    accent_line = ANNOTATION["pen"]
    for i, (title, desc, hk, sample) in enumerate([
            ("Длительность записи GIF", "Пауза не считается; стоп — в любой момент", None, None),
            ("Размер", "Перо, Маркер, Ластик", None, {"width": 4, "color": accent_line, "alpha": 1}),
            ("Непрозрачность", "Перо и Маркер", None, None),
            ("Непрозрачность", "Недоступно: выбран Ластик", None, None),
            ("Перо", None, "P", None),
            ("Сохранить", "Сохранить снимок как…", "Ctrl+S", None)]):
        C.tooltip_body(tips, th, title, desc, hk, sample, bg=sec.cget("bg")).grid(
            row=i // 3, column=i % 3, sticky="nw", padx=(0, th.sp(3)), pady=(0, th.sp(2)))

    basic = [s for s in STATES if s[0] in ("normal", "hover", "focus", "disabled", "error")]
    sec = section(col, th, "Слайдер")
    state_grid(sec, th, lambda p, kw: C.Slider(p, th, 40, width=th.px(120), **kw), basic)
    sec = section(col, th, "Выпадающий список")
    state_grid(sec, th, lambda p, kw: C.Select(p, th, [(1, "Прямоугольник", "mode_rect"), (2, "Окно", "mode_window")], 1, **kw), basic)
    from .features import GIF_LIMIT, TOOL_OPACITY, TOOL_SIZE
    spec = GIF_LIMIT
    sec = section(col, th, "Число на панели (NumberField) — клик открывает окошко значения")
    state_grid(sec, th, lambda p, kw: C.NumberField(p, th, 5, spec, icon="timer", **kw), basic)
    row = tk.Frame(sec, bg=sec.cget("bg"))
    row.grid(row=2, column=0, columnspan=5, sticky="w")
    for name, v in (("особое значение", 0), ("дробное, вне ползунка", 45.5), ("параметра нет", None)):
        cell = tk.Frame(row, bg=row.cget("bg"))
        cell.pack(side="left", padx=th.sp(1))
        C.Text(cell, th, name, "caption", "secondary").pack(anchor="w")
        C.NumberField(cell, th, v, spec, icon="timer", disabled=v is None).pack(anchor="w")
    sec = section(col, th, "Окошко значения: время, размер, непрозрачность; из «…» — с заголовком")
    ring = th.size("focus") + 1
    px, top, bottom = th.size("value_pad")
    cards = tk.Frame(sec, bg=sec.cget("bg"))
    cards.pack(anchor="w")
    for i, (sp_, v, title) in enumerate(((GIF_LIMIT, 0, None), (TOOL_SIZE, 4, None), (TOOL_OPACITY, 100, None),
                                         (TOOL_SIZE, 45, "Размер"))):
        card = C.Card(cards, th, (px - ring, top - ring, bottom), bg=sec.cget("bg"))
        C.value_panel(card.body, th, v, sp_, lambda x: None, title=title)
        card.reshape()
        card.grid(row=i // 3, column=i % 3, sticky="nw", padx=(0, th.sp(3)), pady=(0, th.sp(3)))
    sec = section(col, th, "Правка числа: наведение — подсветка, клик — поле (кольцо — признак правки)")
    modes = tk.Frame(sec, bg=sec.cget("bg"))
    modes.pack(anchor="w")
    for i, (name, spec_, v, mode) in enumerate((("наведение на число", TOOL_SIZE, 4, "hover"),
                                                ("поле, ввели 12", TOOL_SIZE, 12, "edit"),
                                                ("время: 0 — «Без лимита»", GIF_LIMIT, 0, "edit"))):
        cell = tk.Frame(modes, bg=modes.cget("bg"))
        cell.grid(row=0, column=i, sticky="nw", padx=(0, th.sp(3)))
        C.Text(cell, th, name, "caption", "secondary").pack(anchor="w")
        f = C.NumberField(cell, th, v, spec_, icon="timer" if spec_ is GIF_LIMIT else "width")
        f.pack(anchor="w")
        if mode == "hover":
            f._num_hover = True
        else:
            f.paint()
            x = f._num_box[0] - th.size("focus") - th.sp(1)
            f._edit = C.InlineEdit(f, th, x, f.H // 2, C.edit_field_w(th, spec_), C.num_text(v), spec_, f._fill,
                                   lambda v: None, lambda v, a: None, focus=False)
        f.paint()
    cell = tk.Frame(modes, bg=modes.cget("bg"))
    cell.grid(row=0, column=3, sticky="nw")
    C.Text(cell, th, "двойной клик по плашке 16: поле с текущим 12", "caption", "secondary").pack(anchor="w")
    card = C.Card(cell, th, (px - ring, top - ring, bottom), bg=modes.cget("bg"))
    vp = C.value_panel(card.body, th, 12, TOOL_SIZE, lambda x: None)
    vp["chips"][3].start_edit("12", TOOL_SIZE, lambda v, a: None, focus=False)
    card.reshape()
    card.pack(anchor="w")
    sec = section(col, th, "Значок-переключатель (IconToggle): кнопка — сама иконка")
    toggle_states = [("выкл", {}), ("наведение", {"force": {"hover"}}), ("вкл", {"value": True}),
                     ("фокус", {"force": {"focus"}}), ("вкл + фокус", {"value": True, "force": {"focus"}}),
                     ("отключено", {"disabled": True})]
    state_grid(sec, th, lambda p, kw: C.IconToggle(p, th, "cursor", "Курсор в GIF", **kw), toggle_states)
    sec = section(col, th, "Клавиши: плашки (KeyCap), строка «Показать все», окно «Все клавиши»")
    caps = tk.Frame(sec, bg=sec.cget("bg"))
    caps.pack(anchor="w")
    for keys in (["P"], ["Ctrl+S"], ["Ctrl+Y", "Ctrl+Shift+Z"]):
        C.key_caps(caps, th, keys).pack(side="left", padx=(0, th.sp(4)))
    C.SettingRow(sec, th, "Клавиши в окне", "Собираются автоматически из всех действий",
                 build=lambda p: C.Button(p, th, "Показать все", icon="keyboard", variant="secondary"),
                 avail=th.size("row_min_w")).pack(fill="x", pady=(th.sp(2), 0))
    C.Text(sec, th, "содержимое окна (KeysSheet на холсте, две колонки; в программе — на стекле)",
           "caption", "secondary").pack(anchor="w", pady=(th.sp(2), 0))
    sheet = C.Panel(sec, th, "raised", pad=5)
    sheet.pack(anchor="w")
    demo = [("Общие", [("Создать", ["Ctrl+N"]), ("Настройки", ["Ctrl+,"])]),
            ("Правка", [("Отменить", ["Ctrl+Z"]), ("Повторить", ["Ctrl+Y", "Ctrl+Shift+Z"])]),
            ("Инструменты", [("Перо", ["P"]), ("Ластик", ["E", "Shift+E"])]),
            ("Вид", [("По размеру окна", ["Ctrl+0"])])]
    ks = KeysSheet(th, demo)
    w, h = ks.size(2)
    kc = tk.Canvas(sheet, width=w, height=h, bg=th.c("surface-raised"), highlightthickness=0, bd=0)
    kc.pack()
    ks.draw(kc, 0, 0, 2)
    sec = section(col, th, "Поле ввода")
    field_states =[("normal", {}), ("hover", {"force": {"hover"}}), ("focus", {"force": {"focus"}}),
                    ("disabled", {"disabled": True}), ("error", {"error": True}), ("readonly", {"readonly": True})]
    state_grid(sec, th, lambda p, kw: C.TextField(p, th, "Текст", width=th.px(110), **kw), field_states)
    sec = section(col, th, "Горячая клавиша · цвет · путь")
    row = tk.Frame(sec, bg=sec.cget("bg"))
    row.pack(anchor="w")
    C.HotkeyField(row, th, "Ctrl+Alt+S").pack(side="left")
    hk = C.HotkeyField(row, th, "")
    hk.capturing = True
    hk.paint()
    hk.pack(side="left")
    C.ColorField(row, th, ANNOTATION["pen"], show_hex=True).pack(side="left")
    C.ColorField(row, th, ANNOTATION["marker"], small=True, force={"focus"}).pack(side="left")
    C.PathField(sec, th, "C:\\Games\\screenshoterXX\\гифки", lambda: None, lambda: None, lambda: None,
                "«гифки»").pack(anchor="w", pady=th.sp(1))

    sec = section(col, th, "Вкладки и список")
    C.Tabs(sec, th, [(1, "Снимки"), (2, "Запись GIF"), (3, "Клавиши")], 2).pack(anchor="w")
    lv = C.ListView(sec, th, [(1, "Снимки", "snip", None), (2, "Запись GIF", "film", "Ctrl+G"),
                              (3, "Отключено", "keyboard", None)], value=2, width=th.px(240))
    lv.rows[2].configure_state(disabled=True)
    lv.rows[0].force = {"hover"}
    lv.rows[0].paint()
    lv.pack(anchor="w", pady=th.sp(2))

    sec = section(col, th, "Панель инструментов (HUD) с переполнением")
    reg = Registry()
    reg.group("a", "demo")
    reg.group("s", "demo", order=99, align="right")
    for i, (ic, t) in enumerate([("save", "Сохранить"), ("copy", "Копировать"), ("pen", "Перо"),
                                 ("marker", "Маркер"), ("undo", "Отменить"), ("trash", "Очистить")]):
        reg.action(f"d{i}", t, icon=ic, surface="demo", group="a", freq=3 if i < 4 else 1, value=3 if i < 4 else 2,
                   handler=lambda: None, order=i)
    reg.action("ds", "Настройки", icon="settings", surface="demo", group="s", kind="icon", handler=lambda: None)
    hud = HudToolbar(sec, th, reg.for_surface("demo"))
    hud.pack(fill="x")

    sec = section(col, th, "Состояния: прогресс, индикатор, уведомления")
    row = tk.Frame(sec, bg=sec.cget("bg"))
    row.pack(anchor="w")
    C.ProgressBar(row, th, value=0.6).pack(side="left", padx=th.sp(1))
    C.ProgressBar(row, th, value=None).pack(side="left", padx=th.sp(1))
    for tone in ("danger", "success", "warning", "accent", "muted"):
        C.StatusDot(row, th, tone).pack(side="left", padx=th.sp(1))
    for kind, text in (("info", "Информация"), ("success", "GIF №12 сохранён"),
                       ("warning", "Сочетание занято"), ("error", "Ошибка сохранения")):
        C.Toast(sec, th, text, kind, actions=[("Открыть", lambda: None)] if kind == "success" else ()
                ).pack(anchor="w", pady=th.sp(1))

    sec = section(col, th, "Панели: raised · glass (запасной вариант) · подсказка")
    row = tk.Frame(sec, bg=sec.cget("bg"))
    row.pack(anchor="w")
    for kind in ("raised", "glass"):
        p = C.Panel(row, th, kind)
        p.pack(side="left", padx=(0, th.sp(2)))
        C.Text(p, th, f"Panel · {kind}").pack()
    tip = C.Panel(row, th, "raised", pad=1)
    tip.configure(highlightbackground=th.c("border-strong"))
    tip.pack(side="left")
    C.Text(tip, th, "Подсказка", "caption").pack(side="left")
    C.Text(tip, th, "  Ctrl+N", "caption", "secondary").pack(side="left")

    sec = section(col, th, "Строка настройки и пустое состояние")
    C.SettingRow(sec, th, "Копировать в буфер", "Описание настройки второстепенным текстом",
                 build=lambda p: C.Toggle(p, th, True)).pack(fill="x")
    C.SettingRow(sec, th, "С ошибкой", None, error="Сочетание занято другой программой",
                 build=lambda p: C.HotkeyField(p, th, "Ctrl+Alt+S", error=True)).pack(fill="x")
    C.EmptyState(sec, th, "image", "Снимка пока нет", "Пустое состояние с действиями",
                 [lambda p: C.Button(p, th, "Создать", icon="snip", variant="primary", size="lg")]).pack(pady=th.sp(2))

    sec = section(col, th, "Настоящее стекло (оверлей): худший светлый и тёмный фон")
    W_, H_ = th.px(420), th.px(110)
    lightest = paint.hex_rgb(THEMES["light"]["surface-raised"])   # худший светлый фон
    darkest = paint.hex_rgb(THEMES["dark"]["overlay"])            # худший тёмный фон
    bg = Image.new("RGB", (W_, H_), lightest)
    d = ImageDraw.Draw(bg)
    d.rectangle((W_ // 2, 0, W_, H_), fill=darkest)
    for x in range(0, W_, th.sp(4)):
        d.line((x, 0, x + H_, H_), fill=paint.hex_rgb(th.c("danger-fg")), width=th.sp(1))
    cv = tk.Canvas(sec, width=W_, height=H_, highlightthickness=0, bd=0)
    cv.pack(anchor="w")
    cv._bg = ImageTk.PhotoImage(bg)
    cv.create_image(0, 0, anchor="nw", image=cv._bg)
    hudc = CanvasHud(cv, bg, th, [("free", "mode_free", "Произвольная", "1"), ("rect", "mode_rect", "Прямоугольник", "2"),
                                   ("window", "mode_window", "Окно", "3"), ("full", "mode_full", "Экран", "4")],
                     "rect", lambda v: None, "Выделите область · Esc", tag="hudc")
    hudc.place_top_center(W_ // 2, th.sp(2))
    cv._hud = hudc   # держать ссылку: иначе картинки стекла соберёт сборщик мусора
    cv._chip = glass_chip(cv, bg, th, th.sp(4), H_ - th.sp(8), "640 × 480")

    sec = section(col, th, f"Иконки ({len(ICONS)}) — единый штрих, сетка 24")
    grid = tk.Frame(sec, bg=sec.cget("bg"))
    grid.pack(anchor="w")
    for i, name in enumerate(sorted(ICONS)):
        r, c = divmod(i, 8)
        cell = tk.Frame(grid, bg=grid.cget("bg"))
        cell.grid(row=r, column=c, padx=th.sp(1), pady=th.sp(1), sticky="w")
        tk.Label(cell, image=get_icon(name, th.size("icon"), th.c("text-primary")),
                 bg=cell.cget("bg")).pack()
        C.Text(cell, th, name, "caption", "secondary", anchor="center").pack()
    return col


def run_showcase(app_dir):
    scale = system_scale()
    if "--scale" in sys.argv:
        scale = int(sys.argv[sys.argv.index("--scale") + 1]) / 100
    root = tk.Tk()
    root.title("Ножницы XX — витрина компонентов")
    dark, light = Theme("dark", scale=scale), Theme("light", scale=scale)
    root.configure(bg=dark.c("bg"))
    from ..core.winapi import set_titlebar_dark
    set_titlebar_dark(root, dark.dark_titlebar)
    area = C.ScrollArea(root, dark, "bg")
    area.pack(fill="both", expand=True)
    row = tk.Frame(area.body, bg=dark.c("bg"))
    row.pack(padx=dark.sp(4), pady=dark.sp(4))
    note = ""
    for i, th in enumerate((dark, light)):
        build_column(row, th, note).grid(row=0, column=i, sticky="n", padx=dark.sp(2))
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{min(row.winfo_reqwidth() + dark.px(60), sw - 40)}x{int(sh * 0.85)}+20+20")
    root.mainloop()
