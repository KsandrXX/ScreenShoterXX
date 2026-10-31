# -*- coding: utf-8 -*-
"""
СЛОЙ 3 — ШАБЛОНЫ МАКЕТОВ.

Каркасы, в которые компоненты вставляются по правилам, а не руками:
    AppShell        главное окно: шапка / основная область / строка статуса + тосты
    HudToolbar      панель инструментов: группы, разделители, «Ещё» при переполнении
    SettingsLayout  настройки: категории слева (вкладки, если окно узкое), строки справа
    Dialog          модальный диалог: заголовок / тело / кнопки (основная справа)
    CanvasHud       HUD на оверлее захвата: стеклянная панель и кнопки на холсте
    StatusBar, ToastHost
Шаблоны получают описания элементов (Action, Setting из registry) и сами
выбирают компонент, размер, порядок и место.
"""

import tkinter as tk

from PIL import Image, ImageTk

from ..core.i18n import tr
from . import components as C
from . import paint
from .icons import icon as get_icon, pil_icon


# ==========================================================================
# Главное окно
# ==========================================================================
class AppShell(tk.Frame):
    """Области: header (HudToolbar), main (виды), status (StatusBar), toasts."""

    def __init__(self, root, th):
        super().__init__(root, bg=th.c("bg"))
        self.th = th
        self.header = C.Frame(self, th, "surface")
        self.header_line = C.Divider(self, th)
        self.main = C.Frame(self, th, "bg")
        self.status_line = C.Divider(self, th)
        self.status = StatusBar(self, th)
        self.views = {}
        self.current = None
        self.toasts = ToastHost(self.main, th)
        self.compact = False

    def layout(self, compact=False):
        """compact=True — только main (режим HUD, например запись)."""
        for w in (self.header, self.header_line, self.main, self.status_line, self.status):
            w.pack_forget()
        if not compact:
            self.header.pack(side="top", fill="x")
            self.header_line.pack(side="top", fill="x")
            self.status.pack(side="bottom", fill="x")
            self.status_line.pack(side="bottom", fill="x")
        self.main.pack(side="top", fill="both", expand=True)
        self.compact = compact

    def add_view(self, vid, frame):
        self.views[vid] = frame

    def show(self, vid):
        for v in self.views.values():
            v.pack_forget()
        self.views[vid].pack(in_=self.main, fill="both", expand=True)
        self.current = vid
        self.toasts.lift_all()


class StatusBar(tk.Frame):
    def __init__(self, parent, th):
        super().__init__(parent, bg=th.c("surface"), padx=th.sp(3), pady=th.sp(1))
        self.th = th
        self.meta = C.Text(self, th, "", "caption", "secondary")
        self.meta.pack(side="right", padx=(th.sp(3), 0))   # постоянная справка вида (масштаб и т. п.)
        self.actions = tk.Frame(self, bg=self.cget("bg"))
        self.actions.pack(side="right")          # действия получают место раньше текста
        self.text = C.Text(self, th, "", "caption", "secondary")
        self.text.pack(side="left", fill="x", expand=True)
        self.progress = None

    def set_meta(self, text):
        self.meta.configure(text=text)

    def set(self, text, tone="secondary", actions=(), busy=False):
        th = self.th
        self.text.configure(text=text, fg=th.c(C.TONES[tone]))
        for w in self.actions.winfo_children():
            w.destroy()
        for label, cmd in actions:
            C.Button(self.actions, th, label, variant="ghost", size="sm", command=cmd).pack(side="left")
        if busy:
            self.progress = C.ProgressBar(self.actions, th)
            self.progress.pack(side="left", padx=th.sp(2))


class ToastHost:
    """Стопка уведомлений в правом нижнем углу области main."""

    def __init__(self, area, th):
        self.area, self.th, self.items = area, th, []

    def show(self, text, kind="info", actions=(), sticky=False):
        th = self.th
        t = C.Toast(self.area, th, text, kind, actions, on_close=self.close)
        self.items.append(t)
        del_n = len(self.items) - th.layout("toast_stack")
        for old in self.items[:max(0, del_n)]:
            self.close(old)
        self._place()
        if not sticky:
            t.after(th.timing("toast_life"), lambda: self.close(t))
        return t

    def close(self, t):
        if t in self.items:
            self.items.remove(t)
            try:
                t.destroy()
            except tk.TclError:
                pass
            self._place()

    def _place(self):
        th = self.th
        y = -th.sp(4)
        for t in reversed(self.items):
            t.place(relx=1, rely=1, anchor="se", x=-th.sp(4), y=y, width=th.size("toast_w"))
            t.update_idletasks()
            y -= t.winfo_reqheight() + th.sp(2)
            t.lift()

    def lift_all(self):
        for t in self.items:
            t.lift()


# ==========================================================================
# Панель инструментов (HUD)
# ==========================================================================
def action_tip(a):
    """Подсказка действия: название (как на панели) и пояснение `tooltip` (строка или функция —
    например, причина недоступности); считается в момент показа."""
    return lambda: (a.title, a.tooltip() if callable(a.tooltip) else a.tooltip)


class HudToolbar(tk.Frame):
    """Собирает панель из групп действий. Переполнение -> меню «Ещё».

    groups: [(Group, [Action...])] из Registry.for_surface().
    lead:   необязательная функция build(parent) — неактивное содержимое слева
            (например таймер записи)."""

    def __init__(self, parent, th, groups, lead=None, tone="surface", size="sm", pad=2, overflow=True):
        super().__init__(parent, bg=th.c(tone), padx=th.sp(pad), pady=th.sp(1))
        self.th, self.groups, self.size, self.overflow = th, groups, size, overflow
        self._expand = False
        self.items = []          # (action, widget, group, align)
        self.widgets = {}
        self.dividers = []
        self.sep_lines = []      # (линия, действие перед ней)
        if lead:
            self.lead = lead(self)
            self.lead.pack(side="left", padx=(0, th.sp(3)))
        else:
            self.lead = None
        self.more = C.IconButton(self, th, "more", tr("Ещё"), size=size, command=self._open_more)
        self._hidden = []
        for g, acts in groups:
            for a, nxt in zip(acts, list(acts[1:]) + [None]):
                # название инструмента стоит у линии: до неё pair_gap вместо обычного поля кнопки
                trim = th.sp(3) + th.size("focus") + 1 - th.size("pair_gap") if nxt and nxt.sep else 0
                w = self._make(a, trim)
                self.items.append((a, w, g))
                self.widgets[a.id] = w
        self.bind("<Configure>", lambda e: self._relayout())
        self._relayout()

    # --- фабрика: вид действия -> компонент ---
    def _make(self, a, trim=0):
        th = self.th
        tip = action_tip(a)
        enabled = a.enabled()
        title, icon_name = a.label() if a.label else (a.title, a.icon)
        label = title if a.show_label and a.priority >= 6 else ""
        if a.kind == "select":
            opts = a.options() if callable(a.options) else a.options
            w = C.Select(self, th, opts, a.get(), on_change=a.set, tooltip=tip, hotkey=a.hotkey,
                         disabled=not enabled, custom=a.custom)
        elif a.kind == "number":
            w = C.NumberField(self, th, a.get(), a.number, on_change=a.set, icon=icon_name, tooltip=tip,
                              hotkey=a.hotkey, disabled=not enabled, tip_sample=a.tip_sample)
        elif a.kind == "toggle":
            # подсказка — с состоянием: «Курсор в GIF» / «Включён»; слова состояния — options (выкл, вкл)
            off, on = a.options or (tr("выключено"), tr("включено"))
            w = C.IconToggle(self, th, icon_name, lambda a=a, off=off, on=on: (
                             a.title, (on if a.get() else off).capitalize()), a.get(),
                             on_change=a.set, size=self.size, hotkey=a.hotkey, disabled=not enabled)
        elif a.kind == "color":
            w = C.ColorField(self, th, a.get(), small=True, tooltip=tip, hotkey=a.hotkey,
                             on_pick=lambda f, a=a: a.handler(f), disabled=not enabled)
        elif a.kind == "tool":
            w = C.Button(self, th, label, icon=icon_name, variant="ghost", size=self.size, trim=trim,
                         selected=a.get() == a.id, tooltip=tip, hotkey=a.hotkey,
                         command=lambda a=a: (a.set(a.id), self.refresh()), disabled=not enabled,
                         on_hold=a.hold)
        elif a.kind in ("primary", "danger"):
            w = C.Button(self, th, title, icon=icon_name, variant=a.kind, size=self.size,
                         tooltip=tip, hotkey=a.hotkey, command=a.handler, disabled=not enabled)
        elif a.kind == "icon" or not label:
            w = C.IconButton(self, th, icon_name, tip, size=self.size, hotkey=a.hotkey,
                             command=a.handler, disabled=not enabled)
        else:
            fixed = None
            if a.label_variants:   # ширина под самый длинный вариант — панель не «прыгает»
                probe = C.Button(self, th, label, icon=icon_name, variant="ghost", size=self.size)
                fixed = max(probe._natural_w(th, t, i) for t, i in a.label_variants)
                probe.destroy()
            w = C.Button(self, th, label, icon=icon_name, variant="ghost", size=self.size, width=fixed,
                         tooltip=tip, hotkey=a.hotkey, command=a.handler, disabled=not enabled)
        return w

    def refresh(self):
        """Обновить состояния (выбранный инструмент, значения, доступность)."""
        if not self.winfo_exists():
            return      # действие пересобрало интерфейс (смена темы из «…») — эта панель уже удалена
        for a, w, _ in self.items:
            if a.kind == "tool":
                w.selected = a.get() == a.id
            elif a.kind == "select":
                w.value = a.get()
            elif a.kind == "color":
                w.color = a.get()
            elif a.kind in ("number", "toggle"):
                w.disabled = not a.enabled()
                w.set(a.get())
            if a.label and isinstance(w, C.IconToggle):
                w.icon_name = a.label()[1]
            elif a.label and isinstance(w, C.Button):
                text, ic = a.label()
                if isinstance(w, C.IconButton):
                    w.icon_name = ic
                else:
                    w.relabel(text, ic)
            w.disabled = not a.enabled()
            w.paint()
        self._paint_sep_lines()

    def _paint_sep_lines(self):
        """Линия у выбранного инструмента не видна; место остаётся, панель не прыгает."""
        for d, a in self.sep_lines:
            on = a.kind == "tool" and a.get() == a.id
            d.configure(bg=self.cget("bg") if on else self.th.c("border-strong"))

    # --- раскладка с переполнением ---
    def _plan(self, avail=None):
        """Какие элементы скрыть в «Ещё». avail=None — без ограничения ширины."""
        th = self.th
        left = [(a, w, g) for a, w, g in self.items if g.align == "left"]
        if not self.overflow:
            return set()
        hidden = {a.id for a, _, _ in left if a.priority < th.layout("min_visible_priority")}
        visible = [x for x in left if x[0].id not in hidden]

        def weakest():  # самый низкий приоритет; при равенстве — самый правый
            return min(visible, key=lambda x: (x[0].priority, -left.index(x)))
        while len(visible) > th.layout("toolbar_max_visible"):
            low = weakest()
            visible.remove(low)
            hidden.add(low[0].id)
        while avail is not None and visible and self._width(visible, hidden) > avail:
            low = weakest()
            visible.remove(low)
            hidden.add(low[0].id)
        return hidden

    def _width(self, visible, hidden):
        th = self.th
        w = sum(wd.W for a, wd, g in self.items if g.align == "right")
        w += (self.lead.winfo_reqwidth() + th.sp(3)) if self.lead else 0
        w += sum(wd.W for _, wd, _ in visible)
        for p, x in zip(visible, visible[1:]):
            if p[2].id != x[2].id:
                w += 2 * th.sp(1) + th.size("border")
            elif x[0].sep:
                w += th.size("border") + th.size("pair_gap") - (th.size("focus") + 1)
        w += self.more.W if hidden else 0
        return w + 2 * int(self.cget("padx"))

    def full_width(self):
        """Ширина панели, при которой ничего не уходит в «Ещё» сверх правил приоритета."""
        hidden = self._plan(None)
        visible = [x for x in self.items if x[2].align == "left" and x[0].id not in hidden]
        return self._width(visible, hidden)

    def _relayout(self):
        th = self.th
        width = self.winfo_width()
        hidden = self._plan(width if width > 1 and not self._expand else None)
        if hidden == getattr(self, "_hidden_ids", None):
            return   # набор не изменился — не трогаем раскладку (иначе возможна обратная связь с окном)
        self._hidden_ids = hidden
        for _, w, _ in self.items:
            w.pack_forget()
        for d in self.dividers:
            d.destroy()
        self.dividers = []
        self.sep_lines = []
        self.more.pack_forget()
        last_group = prev = None
        for a, w, g in self.items:
            if a.id in hidden:
                continue
            side = "right" if g.align == "right" else "left"
            if side == "left" and last_group is not None and g.id != last_group:
                d = C.Divider(self, th, vertical=True)
                d.pack(side="left", fill="y", padx=th.sp(1), pady=th.sp(1))
                self.dividers.append(d)
            elif side == "left" and a.sep:   # линия перед образцом цвета: он сам отступает на кольцо
                d = C.Divider(self, th, vertical=True, length=th.size("swatch"), color="border-strong")
                d.pack(side="left", padx=(0, th.size("pair_gap") - th.size("focus") - 1))
                self.dividers.append(d)
                self.sep_lines.append((d, prev))
            if side == "left":
                last_group, prev = g.id, a
            w.pack(side=side)
        self._paint_sep_lines()
        self._hidden = [a for a, _, _ in self.items if a.id in hidden]
        if self._hidden:
            self.more.pack(side="left")

    def expand(self):
        """Разложить без учёта текущей ширины (перед «естественным» размером окна)."""
        self._expand = True
        self._relayout()
        self._expand = False

    def _open_more(self):
        items = []
        for a in self._hidden:
            if a.kind == "select":
                opts = a.options() if callable(a.options) else a.options
                cur = next((o[1] for o in opts if o[0] == a.get()), None)
                if cur is None:
                    cur = C.custom_text(a.custom, a.get()) if a.custom else C.num_text(a.get())
                items.append(((a, None), f"{a.title}: {cur}", a.icon, "›"))
            elif a.kind == "number":
                if a.enabled():
                    items.append(((a, None), f"{a.title}: {C.number_label(a.number, a.get())}", a.icon, "›"))
            elif a.kind == "toggle":
                items.append(((a, None), a.title, "check" if a.get() else a.icon, None))
            else:
                title, ic = a.label() if a.label else (a.title, a.icon)
                items.append(((a, None), title, ic, a.hotkey))

        def pick(v):
            a, opt = v
            if a.kind == "number":   # та же панель с ползунком — под кнопкой «Ещё»
                self.after(1, lambda: C.value_popup(self.more, self.th, a.get(), a.number,
                                                    lambda x: (a.set(x), self.refresh()), title=a.title,
                                                    within=self.winfo_toplevel()))
                return
            if a.kind == "toggle":
                a.set(not a.get())
                self.refresh()
                return
            if a.kind == "select":   # второй уровень — варианты списка
                opts = a.options() if callable(a.options) else a.options
                sub = [(o[0], o[1], "check" if o[0] == a.get() else (o[2] if len(o) > 2 else None), None)
                       for o in opts]
                if a.custom:
                    sub.append((C.CUSTOM, a.custom.get("label", tr("Своё значение…")), "plus", None))

                def chosen(val, a=a):
                    if val == C.CUSTOM:
                        self.after(1, lambda: C.number_popup(self.more, self.th, a.get(), a.custom,
                                                             lambda v: (a.set(v), self.refresh())))
                    else:
                        a.set(val)
                        self.refresh()
                C.menu(self.more, self.th, sub, chosen, kind="more_sub")
                return
            if a.kind == "tool":
                a.set(a.id)
            elif a.kind == "color":
                a.handler(self.widgets[a.id])
            elif a.handler:
                a.handler()
            self.refresh()
        C.menu(self.more, self.th, items, pick, kind="more")


# ==========================================================================
# Настройки
# ==========================================================================
class SettingsLayout(tk.Frame):
    """Категории слева, строки справа. store: объект с get(key) / set(key, value).
    editor — конструктор настроек (app.layout_store.LayoutEditor, B23): у каждого блока ручка ⠿
    (перетащить внутри раздела или на раздел слева), тексты правятся щелчком; разделы слева тоже
    перетаскиваются, двойной щелчок — переименовать; None — обычный вид."""

    def __init__(self, parent, th, registry, store, page=None, on_page=None, header=None, on_built=None,
                 editor=None):
        super().__init__(parent, bg=th.c("surface"))
        self.th, self.reg, self.store, self.on_page = th, registry, store, on_page
        self.editor = editor
        self._drag = None
        self.on_built = on_built        # страница построена (например, подогнать высоту окна)
        pages = registry.page_list()
        self.page = page if page in registry.pages else (pages[0].id if pages else None)
        self.narrow = None
        self.header = header
        self.nav = tk.Frame(self, bg=th.c("surface"))
        self.navdiv = C.Divider(self, th, vertical=True)
        self.body = C.ScrollArea(self, th, "surface")
        self.navw = None
        self._width = 0
        self._tall = None               # (ширина, высота самой длинной страницы)
        # Страница строится один раз, когда известна настоящая ширина (первый показ).
        # Если строить сразу, она собирается под ширину 1 px и потом пересобирается
        # на глазах — мерцание и «фантомные» иконки.
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, e):
        if e.width <= 1:
            return
        self._width = e.width
        narrow = e.width < self.th.size("settings_narrow")
        if narrow != self.narrow:
            self._build_nav(narrow)
            self._build_page()

    def need_height(self):
        """Высота вида, при которой страница влезает целиком, без прокрутки."""
        self.update_idletasks()
        return self.winfo_height() + self.body.body.winfo_reqheight() - self.body.cv.winfo_height()

    def tallest(self, width):
        """Высота вида под самую длинную страницу при этой ширине. Раскладку может менять
        пользователь, поэтому страницы меряются настоящей сборкой, один раз на ширину. Вид ещё
        скрыт; после замера построена текущая страница, первый показ её не пересобирает.
        В окне шире замеренного строки только короче, поэтому прошлый замер годится."""
        if self._tall and self._tall[0] <= width:
            return self._tall[1]
        self._width = width
        narrow = width < self.th.size("settings_narrow")
        if narrow != self.narrow:
            self._build_nav(narrow)
        page, built, self.on_built = self.page, self.on_built, None
        top = 0
        for p in self._pages():
            self.page = p.id
            self._build_page()
            for row in self.rows.values():      # в скрытом виде ширина строки случайная, не слушать её
                if row.control is not None and not row.force_stacked:
                    row.unbind("<Configure>")
                    row._arrange(self._row_width() < row._need())
            self.update_idletasks()
            top = max(top, self.body.body.winfo_reqheight())
        self.page = page
        self._build_page()
        self.on_built = built
        nav = self.nav.winfo_reqheight()
        self._tall = (width, top + nav if narrow else max(top, nav))
        return self._tall[1]

    def _row_width(self):
        """Ширина строки настройки при текущей ширине — чтобы сразу разложить строки верно."""
        th = self.th
        w = self._width
        if not self.narrow:
            w -= th.size("settings_nav_w") + 2 * th.sp(2) + th.size("border")
        return w - 2 * th.sp(6) - th.size("scrollbar")

    def _build_nav(self, narrow):
        th = self.th
        self.narrow = narrow
        for w in self.nav.winfo_children():
            w.destroy()
        self.nav.pack_forget()
        self.navdiv.pack_forget()
        self.body.pack_forget()
        pages = self._pages()
        if self.page not in [p.id for p in pages]:
            self.page = pages[0].id if pages else None
        if narrow:
            self.navw = C.Tabs(self.nav, th, [(p.id, p.title) for p in pages], self.page,
                               on_change=self.set_page, end={p.id: p.icon for p in pages if p.bottom})
            self.navw.pack(side="left", fill="x", expand=True, padx=th.sp(3), pady=(th.sp(2), 0))
            if self.editor:
                C.IconButton(self.nav, th, "plus", tr("Новый раздел"), command=self._add_page).pack(
                    side="left", pady=(th.sp(2), 0))
            self.nav.pack(side="top", fill="x")
            C.Divider(self.nav, th).pack(side="bottom", fill="x")
        else:
            C.Text(self.nav, th, tr("Настройки"), "title", weight="strong").pack(
                anchor="w", padx=th.sp(4), pady=(th.sp(4), th.sp(2)))
            self.navw = C.ListView(self.nav, th, [(p.id, p.title, p.icon, None) for p in pages],
                                   value=self.page, width=th.size("settings_nav_w"),
                                   on_select=self.set_page, trail="grip" if self.editor else None,
                                   bottom=[p.id for p in pages if p.bottom])
            self.navw.pack(anchor="n", fill="y", expand=True, padx=th.sp(2), pady=(0, th.sp(2)))
            if self.editor:
                for i, (row, p) in enumerate(zip(self.navw.rows, pages)):
                    self._nav_block(row, i, not p.bottom)
                C.Button(self.nav, th, tr("Новый раздел"), icon="plus", variant="ghost",
                         command=self._add_page).pack(anchor="w", padx=th.sp(2), pady=(th.sp(2), 0))
            self.nav.pack(side="left", fill="y")
            self.navdiv.pack(side="left", fill="y")
        self.body.pack(side="left", fill="both", expand=True)

    def _pages(self):
        """Разделы слева. Обычный вид — только непустые (раздел мог опустеть в конструкторе)."""
        if self.editor:
            return [self.reg.pages[pid] for pid in self.editor.page_ids() if pid in self.reg.pages]
        return [p for p in self.reg.page_list() if self.reg.settings_for(p.id)]

    def set_page(self, pid):
        self.page = pid
        if self.on_page:
            self.on_page(pid)
        if self.navw is None:
            return                      # ещё не показана — построится при первом показе
        if self.navw.value != pid:
            self.navw.select(pid)
        self._build_page()

    def _build_page(self, keep_scroll=False):
        th = self.th
        body = self.body.body
        pos = self.body.cv.yview()[0] if keep_scroll else 0
        for w in body.winfo_children():
            w.destroy()
        if not self.page or self.page not in self.reg.pages:
            return
        p = self.reg.pages[self.page]
        wrap = tk.Frame(body, bg=th.c("surface"), padx=th.sp(6), pady=th.sp(4))
        wrap.pack(fill="both", expand=True)
        C.window_badge(wrap, th, f"page:{self.page}")
        self.rows = {}
        if self.editor:
            self._build_edit_page(wrap, p)
            self.update_idletasks()
            self.body.cv.yview_moveto(pos)
            if self.on_built:
                self.on_built()
            return
        C.Text(wrap, th, p.title, "headline", weight="strong").pack(anchor="w", pady=(0, th.sp(3)))
        section = None
        self.rows = {}
        for i, s in enumerate(self.reg.settings_for(self.page)):
            # разделитель только МЕЖДУ строками: под последней строкой уже идёт линия строки статуса
            if i and not s.extra.get("danger"):      # у опасной строки своя рамка
                C.Divider(wrap, th).pack(fill="x")
            if s.section and s.section != section:
                section = s.section
                C.Text(wrap, th, section, "caption", "secondary", weight="strong").pack(
                    anchor="w", pady=(th.sp(4), th.sp(1)))
            err = s.extra.get("error")
            row = C.SettingRow(wrap, th, s.title, s.description(self.store) if callable(s.description)
                               else s.description, build=lambda parent, s=s: self.control(parent, s),
                               error=err() if callable(err) else err, stacked=bool(self.narrow),
                               avail=self._row_width(), danger=bool(s.extra.get("danger")))
            row.pack(fill="x", pady=th.sp(3) if s.extra.get("danger") else 0)
            self.rows[s.key] = row
        self.body.cv.yview_moveto(0)
        if self.on_built:
            self.on_built()

    def sync_row(self, key):
        """Настройку поменяли в другом месте окна (кнопка на панели) — переключатель её строки
        показывает то же значение (с учётом «наоборот») и значок в названии — тот же цвет."""
        row = getattr(self, "rows", {}).get(key)
        s = self.reg.settings.get(key)
        if row is None or s is None or s.kind != "toggle" or not row.winfo_exists():
            return
        v = bool(self.store.get(key))
        shown = (not v) if s.extra.get("invert") else v
        if row.control is not None and row.control.get() != shown:
            row.control.set(shown)
        if row.title_icon is not None:
            row.paint_title_icon(shown)

    def refresh_rows(self):
        """Доступность и описание строк, зависящих от других настроек (extra["enabled"],
        описание-функция), — на месте, без пересборки страницы и прокрутки."""
        for key, row in getattr(self, "rows", {}).items():
            s = self.reg.settings.get(key)
            if s is None or not row.winfo_exists():
                continue
            en = s.extra.get("enabled")
            if en and row.control is not None:
                row.control.configure_state(disabled=not en())
            if callable(s.description) and getattr(row, "desc", None) is not None:
                row.desc.configure(text=s.description(self.store))

    def refresh_errors(self):
        """Ошибки-функции строк (сочетание занято) — на месте, без пересборки страницы."""
        for key, row in getattr(self, "rows", {}).items():
            err = self.reg.settings[key].extra.get("error") if key in self.reg.settings else None
            if callable(err) and row.winfo_exists():
                row.set_error(err())

    # ------------------------------------------------------------ конструктор настроек (B23)
    def _rebuild(self):
        """После действия конструктора: разделы слева и страница — заново, прокрутка та же.
        Фокус — на сам вид ДО пересборки: удалённое поле с фокусом оставило бы клавиатуру
        «ни на чём» (ловушка из CLAUDE.md)."""
        self.focus_set()
        self._build_nav(self.narrow)
        self._build_page(keep_scroll=True)

    def _add_page(self):
        self.page = self.editor.add_page()
        if self.on_page:
            self.on_page(self.page)
        self._rebuild()

    def _build_edit_page(self, wrap, p):
        th, ed = self.th, self.editor
        bg = th.c("surface")
        C.Text(wrap, th, tr("Конструктор настроек: тащите блок за ⠿ — выше, ниже или на раздел слева. "
                         "Щёлкните по тексту, чтобы изменить. Разделы слева тоже можно перетаскивать, "
                         "двойной щелчок — переименовать. Всё сохраняется сразу."),
               "caption", "secondary", wrap=self._row_width()).pack(anchor="w", pady=(0, th.sp(2)))
        tools = tk.Frame(wrap, bg=bg)
        tools.pack(fill="x", pady=(0, th.sp(3)))
        C.Button(tools, th, tr("Новая группа"), icon="plus", variant="secondary", size="sm",
                 command=lambda: (ed.add_section(self.page), self._rebuild())).pack(side="left")
        C.Button(tools, th, tr("Сбросить всё"), icon="undo", variant="ghost", size="sm",
                 command=self._reset_layout).pack(side="right")
        head = tk.Frame(wrap, bg=bg)
        head.pack(fill="x", pady=(0, th.sp(3)))
        title = C.Text(head, th, p.title, "headline", weight="strong")
        title.pack(side="left")
        self._editable(title, p.title, lambda v: (ed.rename_page(self.page, v), self._rebuild()))
        empty = not ed.has_settings(self.page)
        for ic, tip, d in (("chevron_down", tr("Раздел ниже"), 1), ("chevron_up", tr("Раздел выше"), -1)):
            C.IconButton(head, th, ic, tip, disabled=p.bottom,
                         command=lambda d=d: ed.move_page(self.page, d) and self._rebuild()).pack(side="right")
        C.IconButton(head, th, "trash", tr("Удалить раздел") if empty else tr("Удалить можно только пустой раздел"),
                     disabled=not empty, command=self._remove_page).pack(side="right", padx=(0, th.sp(2)))
        self._blocks = []
        self._wrap = wrap
        items = ed.items(self.page)
        for i, (kind, val) in enumerate(items):
            if i:
                C.Divider(wrap, th).pack(fill="x")
            blk = tk.Frame(wrap, bg=bg)
            blk.pack(fill="x")
            self._grip(blk, i).pack(side="left", anchor="n", pady=th.sp(2), padx=(0, th.sp(2)))
            if kind == "section":
                self._edit_section(blk, i, val)
            else:
                self._edit_row(blk, val)
            self._blocks.append(blk)
        if not items:
            C.Text(wrap, th, tr("Раздел пуст: перетащите сюда настройку за ⠿ (на название раздела слева) "
                             "или нажмите «Новая группа»."), "body", "secondary",
                   wrap=self._row_width()).pack(anchor="w", pady=th.sp(4))

    def _edit_section(self, blk, i, name):
        th, ed = self.th, self.editor
        t = C.Text(blk, th, name or tr("Без группы"), "caption", "secondary" if name else "disabled", weight="strong")
        t.pack(side="left", pady=th.sp(2))
        self._editable(t, name, lambda v: (ed.rename_section(self.page, i, v), self._rebuild()))
        C.IconButton(blk, th, "close", tr("Убрать группу (настройки останутся на месте)"),
                     command=lambda: (ed.remove_section(self.page, i), self._rebuild())).pack(side="right")

    def _edit_row(self, blk, s):
        th, ed = self.th, self.editor
        err = s.extra.get("error")
        avail = self._row_width() - th.size("icon") - th.sp(2)
        row = C.SettingRow(blk, th, s.title, s.description(self.store) if callable(s.description)
                           else s.description, build=lambda parent, s=s: self.control(parent, s),
                           error=err() if callable(err) else err, stacked=bool(self.narrow), avail=avail)
        row.pack(side="left", fill="x", expand=True)
        self.rows[s.key] = row
        self._editable(row.title_label, s.title, lambda v: (ed.set_text(s.key, "title", v), self._rebuild()))
        if not ed.editable(s.key, "description"):
            if row.desc is not None:
                C.Tooltip(row.desc, th, tr("Этот текст программа меняет сама — его не изменить"))
            return
        if row.desc is None:                    # описания нет — его можно добавить
            row.desc = C.Text(row.left, th, tr("Добавить описание"), "caption", "disabled", wrap=row.wrap)
            row.desc.pack(anchor="w")
        self._editable(row.desc, s.description or "",
                       lambda v: (ed.set_text(s.key, "description", v), self._rebuild()))

    def _editable(self, label, value, on_set):
        """Текст, который правится щелчком: на его месте — поле ввода; Enter или уход фокуса —
        сохранить, Esc — отменить."""
        th = self.th
        fg = label.cget("fg")
        label.configure(cursor="xterm")
        label.bind("<Enter>", lambda e: label.configure(fg=th.c("accent")))
        label.bind("<Leave>", lambda e: label.configure(fg=fg))
        label.bind("<Button-1>", lambda e: self._edit_text(label, value, on_set))

    def _edit_text(self, label, value, on_set, over=None):
        """Поле вместо текста label; over=(виджет, отступ слева) — поверх виджета: у строки
        раздела слева текст нарисован на холсте, вынуть его из укладки нельзя."""
        th = self.th
        done = {"v": False}

        def commit(text):
            if done["v"]:
                return
            done["v"] = True
            text = " ".join(text.split())
            if text == (value or ""):
                self.after_idle(self._rebuild)
            else:
                self.after_idle(lambda: on_set(text))

        def cancel(_):
            C.note_key("Escape")
            done["v"] = True
            self.after_idle(self._rebuild)
            return "break"
        if over:
            w, x = over
            f = C.TextField(w.master, th, value or "", width=w.winfo_width() - x - 2 * w.ring, on_commit=commit)
            f.place(in_=w, x=x, rely=0.5, anchor="w")
        else:
            info = label.pack_info()
            w = max(label.winfo_width(), th.size("field_w"))
            f = C.TextField(label.master, th, value or "", width=min(w, self._row_width() - th.size("icon")),
                            on_commit=commit)
            opts = {k: info[k] for k in ("side", "anchor", "fill", "expand", "padx", "pady") if k in info}
            f.pack(before=label, **opts)
            label.pack_forget()
        f.entry.bind("<Escape>", cancel)
        f.entry.focus_set()
        f.entry.select_range(0, "end")

    def _grip(self, parent, i):
        th = self.th
        img = get_icon("grip", th.size("icon"), th.c("text-secondary"))
        g = tk.Label(parent, image=img, bg=parent.cget("bg"), cursor="fleur", bd=0)
        g.img = img                             # картинку держать, иначе её соберёт сборщик мусора
        C.Tooltip(g, th, tr("Перетащить блок"))
        g.bind("<ButtonPress-1>", lambda e: self._drag_start(i))
        g.bind("<B1-Motion>", lambda e: self._drag_move())
        g.bind("<ButtonRelease-1>", lambda e: self._drag_end())
        return g

    def _nav_block(self, row, i, movable=True):
        """Раздел слева как блок: щелчок — открыть, потянуть — перенести, двойной — переименовать.
        Ручки нет: строка сама принимает щелчок, перенос начинается, когда мышь сдвинулась.
        movable=False — раздел, прижатый к низу: только щелчок и имя."""
        th = self.th
        if not movable:
            C.Tooltip(row, th, tr("Двойной щелчок — переименовать"))
            row.bind("<Double-Button-1>", lambda e: self._nav_rename(row), add="+")
            return
        C.Tooltip(row, th, tr("Тащите, чтобы поменять порядок. Двойной щелчок — переименовать"))
        at = {}

        def moved(e):
            if self._drag:
                self._drag_move()
            elif at and max(abs(e.x - at["x"]), abs(e.y - at["y"])) >= th.size("drag_start"):
                row.pressed = False               # уже не щелчок: при отпускании раздел не открывать
                row.paint()
                self._nav_drag_start(i)
                self._drag_move()

        def released(e):
            at.clear()
            self._drag_end()
        row.bind("<ButtonPress-1>", lambda e: at.update(x=e.x, y=e.y), add="+")
        row.bind("<B1-Motion>", moved, add="+")
        row.bind("<ButtonRelease-1>", released, add="+")
        row.bind("<Double-Button-1>", lambda e: self._nav_rename(row), add="+")

    def _nav_rename(self, row):
        th, pid = self.th, row.value
        self._edit_text(row, row.text, lambda v: (self.editor.rename_page(pid, v), self._rebuild()),
                        over=(row, th.sp(3) + th.size("icon_sm")))      # текст поля — там же, где текст строки

    # --- перетаскивание: что откуда и куда — видно всё время ---
    # «Отсюда» — блок обведён акцентом; у курсора — карточка с названием блока и итогом
    # («→ в раздел …», «останется на месте»); «сюда» — блоки плавно раздвигаются, в щели —
    # пунктирная рамка «Сюда»; раздел слева, на который бросят, подсвечен. После броска блок на
    # новом месте вспыхивает и гаснет (на другом разделе — мигает его название слева).
    def _drag_start(self, i):
        th = self.th
        self.update_idletasks()
        blk = self._blocks[i]
        kind, val = self.editor.items(self.page)[i]
        name = val.title if kind == "setting" else (val or tr("Без группы"))
        self._drag = self._drag_state(i, name, blk, self._blocks, self._wrap, self._wrap.winfo_width() - 2 * th.sp(6))
        self._drag["h"] = min(self._drag["h"], th.size("drag_gap_max"))

    def _nav_drag_start(self, i):
        self.update_idletasks()
        row = self.navw.rows[i]
        rows = [r for r in self.navw.rows if not self.reg.pages[r.value].bottom]
        self._drag = self._drag_state(i, row.text, row, rows, self.navw, self.navw.winfo_width())
        self._drag["nav"] = True

    def _drag_state(self, i, name, blk, blocks, host, gap_w):
        return {
            "i": i, "name": name, "target": None, "row": None, "nav": False,
            "blocks": blocks, "host": host, "gap_w": gap_w,
            # середины блоков в начале: место считается по ним (+ высота щели), иначе щель,
            # сдвигая блоки, сама меняла бы место и дёргалась туда-сюда
            "mids": [bl.winfo_y() + bl.winfo_height() // 2 for bl in blocks],
            "h": blk.winfo_height(),
            "gap": None, "gap_at": None, "gap_h": 0, "job": None,
            "outline": self._outline(blk, self.th.c("accent")), "ghost": self._ghost(name)}

    def _outline(self, w, color, t=None):
        """Рамка вокруг виджета — четыре полоски поверх него (у Tk нет прозрачной заливки)."""
        t = t or self.th.size("focus")
        parts = []
        for kw in ({"x": 0, "y": 0, "relwidth": 1, "height": t}, {"x": 0, "rely": 1, "y": -t, "relwidth": 1, "height": t},
                   {"x": 0, "y": 0, "width": t, "relheight": 1}, {"relx": 1, "x": -t, "y": 0, "width": t, "relheight": 1}):
            f = tk.Frame(w.master, bg=color)
            f.place(in_=w, **kw)
            f.tk.call("raise", f._w)
            parts.append(f)
        return parts

    def _ghost(self, name):
        """Карточка у курсора: что тащим и что будет, если отпустить здесь."""
        th = self.th
        g = tk.Frame(self, bg=th.c("surface-raised"), highlightthickness=th.size("focus"),
                     highlightbackground=th.c("accent"), padx=th.sp(2), pady=th.sp(1))
        img = get_icon("grip", th.size("icon_sm"), th.c("accent"))
        ic = tk.Label(g, image=img, bg=g.cget("bg"), bd=0)
        ic.img = img
        ic.pack(side="left", padx=(0, th.sp(1)))
        C.Text(g, th, name, "body", weight="strong").pack(side="left")
        g.note = C.Text(g, th, "", "caption", "accent")
        g.note.pack(side="left", padx=(th.sp(2), 0))
        return g

    def _drag_target(self, x, y):
        """Куда упадёт блок: ("page", раздел, строка слева) — над разделом слева; ("at", место, None) —
        на странице (место — номер блока, перед которым встанет)."""
        d = self._drag
        if d["nav"]:
            return ("at", self._drag_place(y), None)
        w = self.winfo_containing(x, y)
        if w is not None and C.within(w, d["ghost"]):
            w = None
        for row in getattr(self.navw, "rows", None) or getattr(self.navw, "tabs", []):
            if w is not None and C.within(w, row):
                return ("page", row.value, row)
        cv = self.body.cv
        edge = self.th.sp(5)
        if y < cv.winfo_rooty() + edge:
            cv.yview_scroll(-1, "units")          # у края — прокрутить
        elif y > cv.winfo_rooty() + cv.winfo_height() - edge:
            cv.yview_scroll(1, "units")
        return ("at", self._drag_place(y), None)

    def _drag_place(self, y):
        """Перед каким блоком встанет то, что тащим."""
        d = self._drag
        yy = y - d["host"].winfo_rooty()
        g, gh = d["gap_at"], d["gap_h"]
        for k, m in enumerate(d["mids"]):
            if yy < m + (gh if g is not None and k >= g else 0):
                return k
        return len(d["mids"])

    def _drag_move(self, x=None, y=None):
        d = self._drag
        if not d:
            return
        if x is None:
            x, y = self.winfo_pointerxy()
        kind, val, row = t = self._drag_target(x, y)
        if d["row"] is not None and d["row"] is not row:
            d["row"].force = set()
            d["row"].paint()
            d["row"] = None
        i = d["i"]
        if kind == "page":
            other = val != self.page
            note = tr("→ в раздел «{}»").format(self.reg.pages[val].title) if other else tr("уже в этом разделе")
            if other:
                row.force = {"hover"}
                row.paint()
                d["row"] = row
            gap = None
        else:
            same = val in (i, i + 1)
            note = tr("останется на месте") if same else ""
            gap = None if same else val
        if gap != d["gap_at"]:
            self._gap_to(gap)
        g = d["ghost"]
        g.note.configure(text=note)
        off = self.th.size("drag_ghost_off")
        gx = x - self.winfo_rootx() + off
        if d["nav"]:             # список узкий: у курсора карточка закрыла бы щель «Встанет сюда»
            gx = max(gx, self.navw.winfo_rootx() + self.navw.winfo_width() - self.winfo_rootx() + off)
        g.place(x=gx, y=y - self.winfo_rooty() + off)
        g.tk.call("raise", g._w)
        d["target"] = t

    def _gap_to(self, j):
        """Раздвинуть блоки на месте j (None — убрать щель). Щель растёт плавно, за TIMING.drag_gap."""
        d, th = self._drag, self.th
        if d["job"]:
            self.after_cancel(d["job"])
            d["job"] = None
        if d["gap"] is not None:
            d["gap"].destroy()
        d["gap"], d["gap_at"], d["gap_h"] = None, j, 0
        if j is None:
            return
        gap = tk.Canvas(d["host"], bg=th.c("surface"), width=1, height=1, highlightthickness=0, bd=0)
        if j < len(d["blocks"]):
            gap.pack(fill="x", before=d["blocks"][j])
        else:
            gap.pack(fill="x", after=d["blocks"][-1])
        d["gap"] = gap
        steps = max(1, th.timing("drag_gap") // th.timing("frame"))

        def step(k):
            if d["gap"] is not gap:
                return
            e = k / steps
            h = max(1, round(d["h"] * (1 - (1 - e) ** 3)))    # быстро в начале, мягко в конце
            gap.configure(height=h)
            d["gap_h"] = h
            self._paint_gap(gap, h, d["gap_w"])
            d["job"] = self.after(th.timing("frame"), lambda: step(k + 1)) if k < steps else None
        step(1)

    def _paint_gap(self, gap, h, w):
        th = self.th
        gap.delete("all")
        pad = th.sp(1)
        if h <= 2 * pad + 2:
            return
        gap.create_rectangle(pad, pad, w - pad, h - pad, outline=th.c("accent"), dash=(4, 3),
                             width=th.size("border"), fill=th.c("accent-soft"))
        if h >= th.line("caption") + 2 * pad:
            # справа: слева, у ручки ⠿, обычно курсор с карточкой — она закрыла бы надпись
            gap.create_text(w - th.sp(4), h // 2, text=tr("Встанет сюда"), anchor="e", fill=th.c("accent-fg"),
                            font=th.font("caption", "strong"))

    def _drag_end(self):
        d, self._drag = self._drag, None
        if not d:
            return
        if d["job"]:
            self.after_cancel(d["job"])
        for w in d["outline"] + [d["ghost"], d["gap"]]:
            if w is not None:
                w.destroy()
        if d["row"] is not None:
            d["row"].force = set()
            d["row"].paint()
        t = d["target"]
        if not t:
            return
        kind, val, _ = t
        i = d["i"]
        if d["nav"]:
            if self.editor.place_page(self.navw.rows[i].value, val):
                self._rebuild()
                self._flash(self.navw.rows[val - 1 if val > i else val])
        elif kind == "page":
            if val != self.page and self.editor.move(self.page, i, val):
                self._rebuild()
                self._blink_nav(val)
        elif self.editor.move(self.page, i, self.page, val):
            self._rebuild()
            self._flash(self._blocks[val - 1 if val > i else val])

    def _flash(self, w):
        """Блок на новом месте: рамка акцентом, гаснет за TIMING.drop_flash."""
        th = self.th
        parts = self._outline(w, th.c("accent"), 2 * th.size("focus"))
        steps = max(1, th.timing("drop_flash") // (2 * th.timing("frame")))
        self._flash_parts = parts

        def step(k):
            if not all(p.winfo_exists() for p in parts):
                return
            if k > steps:
                for p in parts:
                    p.destroy()
                return
            c = paint.mix(th.c("accent"), th.c("surface"), 1 - k / steps)
            for p in parts:
                p.configure(bg=c)
            self.after(2 * th.timing("frame"), lambda: step(k + 1))
        self.after(th.timing("drop_flash") // 3, lambda: step(1))   # сначала — ярко, потом гаснет

    def _blink_nav(self, pid, n=6):
        """Блок ушёл на другой раздел: его название слева мигает (подсветка наведения)."""
        row = next((r for r in getattr(self.navw, "rows", []) if r.value == pid), None)
        if row is None or not row.winfo_exists():
            return
        row.force = {"hover"} if n % 2 == 0 and n else set()
        row.paint()
        if n:
            self.after(self.th.timing("drop_flash") // 6, lambda: self._blink_nav(pid, n - 1))

    def _remove_page(self):
        if self.editor.remove_page(self.page):
            self.page = self.editor.page_ids()[0]
            if self.on_page:
                self.on_page(self.page)
            self._rebuild()

    def _reset_layout(self):
        ans = ask(self.winfo_toplevel(), self.th, tr("Сбросить всё"),
                  tr("Вернуть разделы, группы и тексты настроек как в программе? Своя раскладка удалится."),
                  ((tr("Отмена"), "ghost", None), (tr("Сбросить"), "danger", "yes")))
        if ans == "yes":
            self.editor.reset()
            self._rebuild()

    def control(self, parent, s):
        """Фабрика: вид настройки -> компонент."""
        th, store = self.th, self.store
        opts = (s.options() if callable(s.options) else s.options) if s.options else None
        value = store.get(s.key)
        if value is None:   # значение по умолчанию: из записи, иначе разумное для вида
            value = s.default if s.default is not None else {
                "toggle": False, "slider": s.lo, "hotkey": "", "select": opts[0][0] if opts else None,
            }.get(s.kind)

        inv = s.kind == "toggle" and s.extra.get("invert")    # в окне — наоборот хранимому значению

        def changed(v, s=s):
            v = (not v) if inv else v
            store.set(s.key, v)
            if s.on_change:
                s.on_change(v)
            icon = getattr(parent, "title_icon", None)
            if icon is not None:
                parent.paint_title_icon(bool(store.get(s.key)) != bool(inv))

        if s.kind == "toggle":
            en = s.extra.get("enabled")           # недоступна, пока не включена другая настройка
            shown = (not value) if inv else value
            if s.extra.get("title_icon") and isinstance(parent, C.SettingRow):
                parent.add_title_icon(s.extra["title_icon"], bool(shown))
            return C.Toggle(parent, th, shown, on_change=changed, tooltip=s.title,
                            disabled=bool(en) and not en(), danger=bool(s.extra.get("danger")))
        if s.kind == "select":
            return C.Select(parent, th, opts, value, on_change=changed, custom=s.extra.get("custom"))
        if s.kind == "slider":
            return C.Slider(parent, th, value, s.lo, s.hi, s.step, on_change=changed)
        if s.kind == "hotkey":
            # extra["apply"](v) -> текст ошибки или None: сама сохраняет и регистрирует сочетание;
            # при ошибке поле возвращает прежнее значение, а строка показывает причину
            apply = s.extra.get("apply")
            row = parent if isinstance(parent, C.SettingRow) else None
            show = row.set_error if row else (lambda text: None)

            def hk_changed(v, s=s):
                if apply is None:
                    changed(v)
                    return None
                err = apply(v)
                show(err)
                return err
            return C.HotkeyInput(parent, th, value, on_change=hk_changed,
                                 on_capture=s.extra.get("on_capture"), on_reject=show)
        if s.kind == "color":
            return C.ColorField(parent, th, value, show_hex=True,
                                on_pick=lambda f, s=s: s.extra["on_pick"](f, changed))
        if s.kind == "path":
            holder = {}

            def browse(s=s):
                v = s.extra["on_browse"]()
                if v:
                    changed(v)
                    holder["f"].set(s.extra["display"]())
            reset = s.extra.get("on_reset")

            def do_reset(s=s):
                reset()
                holder["f"].set(s.extra["display"]())
            f = C.PathField(parent, th, s.extra["display"](), browse, s.extra.get("on_open"),
                            do_reset if reset else None, s.extra.get("reset_text"))
            holder["f"] = f
            return f
        if s.kind == "info":
            return C.Text(parent, th, s.text(), "caption", "secondary", wrap=th.size("field_w"))
        if s.kind == "shortcuts":             # кнопка «Показать все» -> окно «Все клавиши»
            b = C.Button(parent, th, s.extra.get("button", tr("Показать все")), icon="keyboard", variant="secondary")
            b.command = lambda: shortcuts_modal(self.winfo_toplevel(), th, self.reg, s.title, return_focus=b)
            return b
        if s.kind == "button":                # extra: button — надпись, icon, on_click, enabled
            en = s.extra.get("enabled")
            return C.Button(parent, th, s.extra["button"], icon=s.extra.get("icon"), variant="secondary",
                            command=s.extra["on_click"], disabled=bool(en) and not en())
        raise ValueError(f"Неизвестный вид настройки: {s.kind}")


# ==========================================================================
# Таблица клавиш и модальное окно
# ==========================================================================
class KeysSheet:
    """Таблица клавиш, нарисованная на ХОЛСТЕ. Группы в колонках: заголовок ЗАГЛАВНЫМИ, жирный,
    акцентом; строки «название — плашки клавиш» (жирный текст в плашке). groups:
    [(группа, [(название, [сочетания])])] (Registry.shortcut_groups()). Колонки балансируются по
    числу строк (группа целиком в одной колонке) и растягиваются на заданную ширину;
    ничего не переносится."""

    def __init__(self, th, groups):
        self.th, self.groups = th, groups
        self._sizes = {}

    @staticmethod
    def split(groups, columns):
        """Разбить группы на колонки подряд так, чтобы самая длинная была как можно короче."""
        if columns <= 1 or len(groups) <= 1:
            return [groups]
        w = [len(rows) + 2 for _, rows in groups]      # заголовок группы ~ две строки
        best = min(range(1, len(groups)), key=lambda k: max(sum(w[:k]), sum(w[k:])))
        return [groups[:best], groups[best:]]

    # --- метрики ---
    def _cap_w(self, k):
        return self.th.measure(k, "caption", "strong") + 2 * self.th.sp(2)

    def _caps_w(self, keys):
        th = self.th
        return sum(self._cap_w(k) for k in keys) + (len(keys) - 1) * (th.measure("/", "caption") + 2 * th.sp(1))

    def _row_h(self):
        th = self.th
        return max(th.line("body"), th.size("keycap_h")) + 2 * th.size("keys_row_gap")

    def _head_h(self, first):
        th = self.th
        return (0 if first else th.sp(3)) + th.line("body") + th.sp(1)

    def _col_size(self, groups):
        th = self.th
        w = h = 0
        for gi, (name, rows) in enumerate(groups):
            w = max(w, th.measure(name.upper(), "body", "strong"))
            h += self._head_h(gi == 0)
            for title, keys in rows:
                w = max(w, th.measure(title, "body") + th.sp(6) + self._caps_w(keys))
                h += self._row_h()
        return w, h

    def gap(self):
        return self.th.sp(8)

    def size(self, columns):
        if columns not in self._sizes:               # спрашивают на каждом шаге растягивания окна
            cols = [self._col_size(g) for g in self.split(self.groups, columns)]
            self._sizes[columns] = (sum(c[0] for c in cols) + self.gap() * (len(cols) - 1),
                                    max(c[1] for c in cols))
        return self._sizes[columns]

    # --- рисование ---
    def draw(self, cv, x, y, columns, width=None, tag="keys"):
        """width — растянуть колонки на эту ширину (лишнее делится поровну между колонками)."""
        th = self.th
        cols = self.split(self.groups, columns)
        natural, _ = self.size(columns)
        extra = max(0, (width or natural) - natural) / len(cols)
        for groups in cols:
            cw = self._col_size(groups)[0] + extra
            yy = y
            for gi, (name, rows) in enumerate(groups):
                yy += 0 if gi == 0 else th.sp(3)
                cv.create_text(x, yy + th.line("body") // 2, anchor="w", text=name.upper(), tags=tag,
                               fill=th.c("accent-fg"), font=th.font("body", "strong"))
                yy += th.line("body") + th.sp(1)
                rh = self._row_h()
                for title, keys in rows:
                    cy = yy + rh // 2
                    cv.create_text(x, cy, anchor="w", text=title, fill=th.c("text-primary"),
                                   font=th.font("body"), tags=tag)
                    kx = x + cw - self._caps_w(keys)
                    for i, k in enumerate(keys):
                        if i:
                            kx += th.sp(1)
                            cv.create_text(kx, cy, anchor="w", text="/", fill=th.c("text-secondary"),
                                           font=th.font("caption"), tags=tag)
                            kx += th.measure("/", "caption") + th.sp(1)
                        kw = self._cap_w(k)
                        cv.create_image(kx, cy, anchor="w", tags=tag, image=paint.rounded_rgba(
                            kw, th.size("keycap_h"), th.r("sm"), th.c("control"), th.c("border-strong"),
                            th.size("border")))
                        cv.create_text(kx + kw // 2, cy, text=k, fill=th.c("text-primary"),
                                       font=th.font("caption", "strong"), tags=tag)
                        kx += kw
                    yy += rh
            x += cw + self.gap()


class Modal:
    """Модальное окно над окном программы (слой modal), как на макете: затемнение страницы,
    мягкая тень и полупрозрачная карточка по центру — заголовок слева, ✕ справа, содержимое.

    Затемнение — отдельное окно с попиксельной прозрачностью: страница под ним ЖИВАЯ, при
    изменении размера окна перестраивается как обычно (никаких снимков, чёрных полос и рывков).
    Карточка — окно с общей прозрачностью `GLASS.modal_alpha[тема]`: страница сквозь неё бледно
    видна. Оба окна принадлежат окну программы и двигаются ВМЕСТЕ с ним прямо из его оконной
    процедуры (`Modal.host.follow`): и пока окно тащат, и пока тянут за край.

    content — объект с size(columns) -> (w, h) и draw(canvas, x, y, columns, width) (например,
    KeysSheet). Ширина карточки — `LAYOUT.modal_fill` окна (не уже содержимого, не шире
    `SIZE.modal_max_w`); шире окна — columns=1, выше — прокрутка внутри карточки. Закрытие: Esc,
    ✕, клик по затемнению. Фокус — внутри (Tab по кругу), колесо не листает страницу; после
    закрытия фокус — на return_focus. Появляется сразу, без анимации."""

    # WinAPI окна программы (winapi.OverlayHost): затемнение с тенью и следование за окном
    host = None

    def __init__(self, root, th, title, content, return_focus=None, columns=2, kind="modal"):
        self.root, self.th, self.title, self.content = root, th, title, content
        self.kind = kind                              # вид окна (режим «номера окон»)
        self.return_focus, self.columns = return_focus, columns
        self.scrim = self.shade = self.card = None
        self._rebuild_job = None
        self._need_rebuild = False
        self._scrim_set = False
        self._measure()
        try:
            self._open()
        except Exception:
            self.close()                              # недостроенное окно не оставляем
            raise

    # --- размеры ---
    def _client(self):
        r = self.root
        if self.host:
            return self.host.client_rect(self._root_h)
        r.update_idletasks()
        return r.winfo_rootx(), r.winfo_rooty(), r.winfo_width(), r.winfo_height()

    def _measure(self):
        """Всё, что требует Tk (ширины текста, размеры таблицы), — заранее, в контексте Tk:
        _plan зовут и из оконной процедуры, а там вызывать Tk нельзя (падение: GIL отпущен)."""
        th = self.th
        self._m = {"title_w": th.measure(self.title, "title", "strong"),
                   "sizes": {c: self.content.size(c) for c in {1, self.columns}}}

    def _plan(self, cw_, ch_):
        """Колонки, прокрутка и размер карточки для клиентской области cw_ × ch_. Только
        арифметика по заранее измеренному (_measure) — можно звать из оконной процедуры."""
        th = self.th
        pad, top = th.sp(5), th.sp(4)
        margin = th.sp(6)
        max_w, max_h = cw_ - 2 * margin, ch_ - 2 * margin
        btn = th.size("control_sm") + 2 * (th.size("focus") + 1)
        head_h = max(th.line("title"), btn)
        cols = self.columns
        w, h = self._m["sizes"][cols]
        if w + 2 * pad > max_w and cols > 1:
            cols = 1
            w, h = self._m["sizes"][cols]
        title_w = self._m["title_w"] + btn + pad + top
        W = max(w + 2 * pad, title_w, min(int(cw_ * th.layout("modal_fill")), th.size("modal_max_w")))
        W = min(W, max_w)
        body_y = top + head_h + th.sp(2)
        H = body_y + h + pad
        scroll = H > max_h
        if scroll:
            H = max_h
        return {"cols": cols, "scroll": scroll, "W": int(W), "H": int(H), "body_y": body_y,
                "pad": pad, "top": top, "btn": btn, "head_h": head_h, "content_h": h}

    # --- построение ---
    def _open(self):
        th, root = self.th, self.root
        if self.host:
            self._root_h = self.host.handle(root)
        x, y, cw_, ch_ = self._client()
        # затемнение — сплошное окно с общей прозрачностью; тень — окно с попиксельной; карточка —
        # с общей и цветом-ключом в углах. В программе все три — ДОЧЕРНИЕ окна окна программы
        self.scrim = s = tk.Toplevel(root)
        s.withdraw()
        s.overrideredirect(True)
        s.configure(bg=th.c("overlay"))
        if not self.host:                             # в программе прозрачность — WinAPI после adopt
            s.attributes("-alpha", th.glass("modal_scrim"))
        self.shade = sh = tk.Toplevel(root) if self.host else None
        if sh is not None:
            sh.withdraw()
            sh.overrideredirect(True)
        self.card = c = tk.Toplevel(root if self.host else s)
        c.withdraw()
        c.overrideredirect(True)
        key = th.tech("transparent_key")
        c.configure(bg=key)
        if not self.host:
            c.attributes("-transparentcolor", key)    # углы карточки — сквозные
            c.attributes("-alpha", th.glass("modal_alpha")[th.name])
        self._build_card(cw_, ch_)
        off = "+-32000+-32000"                        # сначала за экраном: окна получат дескрипторы
        for w in (s, sh, c):
            if w is not None:
                w.geometry(("1x1" if w is not c else "") + off)
                w.deiconify()
        # полный update: внешнее окно Tk создаёт только при нём
        root.update()
        if self.host:
            h = self.host
            self._scrim_h, self._shade_h, self._card_h = (h.handle(w) for w in (s, sh, c))
            for wh in (self._scrim_h, self._shade_h, self._card_h):
                h.adopt(wh, self._root_h)             # дочерние: едут и растягиваются с окном в одном кадре
            h.set_alpha(self._scrim_h, th.glass("modal_scrim"))
            self._fill = h.solid(self._scrim_h, th.c("overlay"))   # закрашивать сразу, без Tk
            # новая часть окна при растягивании (DWM показывает её раньше, чем дочерние окна) —
            # сразу затемнённым фоном, как страница под затемнением
            h.erase_with(paint.mix(th.c("overlay"), th.c("surface"), th.glass("modal_scrim")))
            h.set_alpha(self._card_h, th.glass("modal_alpha")[th.name], key)
            self._shade_img = None
            self._layout(cw_, ch_)
            h.follow(self._follow)                    # новый размер окна — расставить в его WndProc
        else:
            self._place(x, y, cw_, ch_)
        # своё «Configure» только у самого окна программы (тег окна получает события ВСЕХ виджетов)
        self._tag = f"ModalRoot{id(self)}"
        root.bind_class(self._tag, "<Configure>", self._on_root)
        root.bindtags((self._tag,) + root.bindtags())
        for tl in (s, sh, c):
            if tl is not None:
                tl.bind("<Escape>", lambda e: (C.note_key("Escape"), self.close(), "break")[2])
                tl.bind("<MouseWheel>", self._wheel)
        for tl in (s, sh):                            # клик по затемнению или тени — закрыть
            if tl is not None:
                tl.bind("<ButtonPress-1>", lambda e, tl=tl: self.close() if e.widget is tl else None)
        c.bind("<Tab>", lambda e: self._cycle(1))
        c.bind("<Shift-Tab>", lambda e: self._cycle(-1))
        if not self.host:
            self._hooked = True
            for f in C.Popup.hooks["open"]:          # отдельное окно берёт фокус — рамка не «тускнеет»
                f(self)
            c.focus_force()
        C.focus_auto(self.close_btn)                  # первый элемент — ✕; кольцо — только с клавиатуры

    def _build_card(self, cw_, ch_):
        th, c = self.th, self.card
        for w in c.winfo_children():
            w.destroy()
        p = self.plan = self._plan(cw_, ch_)
        W, H, pad, top = p["W"], p["H"], p["pad"], p["top"]
        tone = th.c("surface-raised")
        cv = tk.Canvas(c, width=W, height=H, bg=th.tech("transparent_key"), highlightthickness=0, bd=0,
                       takefocus=0)
        cv.pack()
        cv.create_image(0, 0, anchor="nw", image=paint.rounded_hard(W, H, th.r("lg"), tone,
                                                                   th.tech("transparent_key")))
        cv.create_text(pad, top + p["head_h"] // 2, anchor="w", text=self.title, fill=th.c("text-primary"),
                       font=th.font("title", "strong"))
        self.close_btn = C.IconButton(cv, th, "close", tr("Закрыть"), command=self.close)
        self.close_btn.bg = tone
        self.close_btn.configure(bg=tone)
        self.close_btn.paint()
        cv.create_window(W - top - p["btn"] + th.sp(2), top + (p["head_h"] - p["btn"]) // 2, anchor="nw",
                         window=self.close_btn)
        self.inner = None
        if not p["scroll"]:
            self.content.draw(cv, pad, p["body_y"], p["cols"], width=W - 2 * pad)
        else:
            sbw = th.size("scrollbar")
            iw, ih = W - 2 * pad - sbw - th.sp(1), H - p["body_y"] - th.sp(3)
            self.inner = ic = tk.Canvas(cv, width=iw, height=ih, bg=tone, highlightthickness=0, bd=0, takefocus=0)
            inset = th.sp(1) // 2                     # глифы у края не должны вылезать за холст
            self.content.draw(ic, inset, 0, p["cols"], width=iw - 2 * inset)
            ic.configure(scrollregion=(0, 0, iw, p["content_h"] + th.sp(2)))
            sb = C.Scrollbar(cv, th, "vertical", command=ic.yview)
            sb.configure(bg=tone)
            ic.configure(yscrollcommand=sb.set)
            cv.create_window(pad, p["body_y"], anchor="nw", window=ic)
            cv.create_window(W - pad - sbw + th.sp(1), p["body_y"], anchor="nw", window=sb, height=ih)
        self.cv = cv
        C.window_badge(cv, th, self.kind)
        c.geometry(f"{W}x{H}")

    def _card_pos(self, x, y, cw_, ch_):
        p = self.plan
        return x + (cw_ - p["W"]) // 2, y + (ch_ - p["H"]) // 2

    def _shadow(self):
        """Картинка окна тени и её поле m (кэш по размеру карточки)."""
        th = self.th
        return paint.modal_shadow(
            self.plan["W"], self.plan["H"], th.r("lg"),
            {k: (th.px(th.shadow(k)) if k != "alpha" else th.shadow(k)) for k in ("blur", "offset", "alpha")},
            th.c("surface-raised"), th.glass("modal_alpha")[th.name])

    def _layout(self, cw_, ch_):
        """Дочерние окна в клиентской области окна программы. Затемнение — сразу размером с
        весь экран (окно программы его обрезает): при растягивании окна ему не нужно ни
        меняться, ни перерисовываться — оно уже на месте (иначе DWM мог показать кадр, где окно
        выросло, а затемнение ещё нет, — светлая полоса по краю). Карточка и тень — по центру.
        Одной пачкой, поверх содержимого окна. Чистый WinAPI (можно из WndProc)."""
        p = self.plan
        cx, cy = (cw_ - p["W"]) // 2, (ch_ - p["H"]) // 2
        img, m = self._shadow()
        if self._shade_img is not img:                # карточка нового размера — нарисовать тень
            self.host.show_layered(self._shade_h, img)
            self._shade_img = img
        items = [(self._shade_h, cx - m, cy - m, None, None), (self._card_h, cx, cy, None, None)]
        if not self._scrim_set:
            sw, sh = self.host.screen_size()
            items.insert(0, (self._scrim_h, 0, 0, max(sw, cw_), max(sh, ch_)))
        self.host.place_children(items)
        if not self._scrim_set:
            self._fill.paint_now()
            self._scrim_set = True
        self._size = (cw_, ch_)

    def _follow(self, x, y, cw_, ch_):
        """Из оконной процедуры окна программы: новый размер — карточку и тень по центру; если
        карточка перестала влезать (или снова влезает шире) — пометить, пересоберёт Tk."""
        if (cw_, ch_) == self._size:
            return                                    # просто сдвиг: дочерние окна едут сами
        new = self._plan(cw_, ch_)
        old = self.plan
        if (new["cols"], new["scroll"]) != (old["cols"], old["scroll"]) or                 new["W"] < old["W"] or new["H"] < old["H"] and old["scroll"]:
            self._size = (cw_, ch_)
            self._need_rebuild = True                 # пересоберёт Tk (_on_root): здесь Tk звать нельзя
            return
        self._layout(cw_, ch_)

    def _rebuild(self):
        self._rebuild_job = None
        self._need_rebuild = False
        if not self.is_open():
            return
        _x, _y, cw_, ch_ = self._client()
        self._build_card(cw_, ch_)
        self.card.update_idletasks()
        # размер — заново: пока карточка собиралась, окно могло снова измениться (и WndProc уже
        # расставил по новому); старый размер вернул бы карточку не туда
        _x, _y, cw_, ch_ = self._client()
        self._layout(cw_, ch_)
        C.focus_auto(self.close_btn)

    # --- без WinAPI (витрина, тесты платформы): отдельные окна поверх, следим средствами Tk ---
    def _place(self, x, y, cw_, ch_):
        cx, cy = self._card_pos(x, y, cw_, ch_)
        self.scrim.geometry(f"{cw_}x{ch_}+{x}+{y}")
        self.card.geometry(f"+{cx}+{cy}")
        self._at = (x, y, cw_, ch_)

    def _on_root(self, e):
        if not self.is_open():
            return
        if self.host:                                 # WinAPI-путь: окна расставляет WndProc;
            if self._need_rebuild and not self._rebuild_job:   # здесь — только пересборка карточки
                self._rebuild_job = self.root.after_idle(self._rebuild)
            return
        x, y, cw_, ch_ = self._client()
        new = self._plan(cw_, ch_)
        old = self.plan
        if (new["cols"], new["scroll"]) != (old["cols"], old["scroll"]) or new["W"] < old["W"]:
            self._build_card(cw_, ch_)
            self.card.update_idletasks()
        self._place(x, y, cw_, ch_)

    # --- клавиатура и колесо ---
    def _focusables(self):
        out = []

        def walk(x):
            for c in x.winfo_children():
                if isinstance(c, C.Control) and int(c.cget("takefocus") or 0):
                    out.append(c)
                walk(c)
        walk(self.card)
        return out

    def _cycle(self, d):
        """Tab по кругу внутри окна: фокус не уходит на страницу под ним."""
        items = self._focusables()
        if items:
            cur = self.root.focus_get()
            i = items.index(cur) if cur in items else -1
            nxt = items[(i + d) % len(items)]
            nxt._quiet = False
            nxt.focus_set()
        return "break"

    def _wheel(self, e):
        if self.inner is not None:
            self.inner.yview_scroll(-e.delta // 120, "units")
        return "break"                                # страницу под окном колесо не прокручивает

    def is_open(self):
        try:
            return self.scrim is not None and bool(self.scrim.winfo_exists())
        except tk.TclError:
            return False

    def close(self):
        if self.host:
            self.host.unfollow(self._follow)
            self.host.erase_with(None)
            fill, self._fill = getattr(self, "_fill", None), None
            if fill is not None:
                fill.release()
        tag = getattr(self, "_tag", None)
        if tag:
            try:
                self.root.bindtags(tuple(x for x in self.root.bindtags() if x != tag))
                self.root.unbind_class(tag, "<Configure>")
            except tk.TclError:
                pass
        if self._rebuild_job:
            self.root.after_cancel(self._rebuild_job)
            self._rebuild_job = None
        if getattr(self, "_hooked", False):
            self._hooked = False
            for f in C.Popup.hooks["close"]:
                f(self)
        # фокус — обратно на кнопку, открывшую окно, ДО удаления окон: если удалить окно с фокусом,
        # Windows оставит фокус ни на чём, Tk сочтёт, что программа его потеряла, и клавиатура
        # (Esc, Tab) не работает до клика мышью
        if self.return_focus is not None and self.return_focus.winfo_exists():
            C.focus_auto(self.return_focus)
        # с host карточка и тень — окна от root, а не дети затемнения: удалять каждое явно
        for name in ("card", "shade", "scrim"):
            w = getattr(self, name)
            setattr(self, name, None)
            try:
                if w is not None and w.winfo_exists():
                    w.destroy()
            except tk.TclError:
                pass


def shortcuts_modal(root, th, registry, title=None, return_focus=None):
    """Окно «Все клавиши»: KeysSheet из Registry.shortcut_groups() на стекле Modal."""
    title = title or tr("Клавиши в окне")      # не в значении по умолчанию: язык меняется на лету
    groups = registry.shortcut_groups()
    return Modal(root, th, title, KeysSheet(th, groups), return_focus=return_focus, kind="keys")


# ==========================================================================
# Диалог
# ==========================================================================
# Хуки оформления окон уровня ОС (например, тёмный заголовок Windows).
# Программа добавляет сюда функции f(window, th); платформа зовёт их для каждого диалога.
window_hooks = []


class Dialog(tk.Toplevel):
    """Модальный диалог. buttons: [(текст, variant, value)] — основная последней.
    Enter — основная кнопка, Esc — отмена (value None)."""

    def __init__(self, root, th, title, build=None, text=None, buttons=(("OK", "primary", True),),
                 icon=None, kind="dialog", danger=False):
        """danger=True — опасное решение: красные рамка, заголовок и текст; Enter ничего не подтверждает."""
        super().__init__(root)
        self.withdraw()
        self.th = th
        self.result = None
        self.title(title)
        self.configure(bg=th.c("surface-raised"))
        self.resizable(False, False)
        self.transient(root)
        self.protocol("WM_DELETE_WINDOW", lambda: self.close(None))
        outer = tk.Frame(self, bg=th.c("surface-raised"), padx=th.sp(6), pady=th.sp(4))
        if danger:
            outer.configure(highlightthickness=th.size("focus"), highlightbackground=th.c("danger-fg"),
                            highlightcolor=th.c("danger-fg"))
        outer.pack(fill="both", expand=True)
        self.body = tk.Frame(outer, bg=th.c("surface-raised"))
        self.body.pack(fill="both", expand=True)
        if danger:
            head = tk.Frame(self.body, bg=th.c("surface-raised"))
            head.pack(anchor="w", pady=(0, th.sp(3)))
            tk.Label(head, image=get_icon("warning", th.size("icon"), th.c("danger-fg")),
                     bg=head.cget("bg")).pack(side="left", padx=(0, th.sp(2)))
            C.Text(head, th, title, "title", "danger", "strong").pack(side="left")
        if text:
            row = tk.Frame(self.body, bg=th.c("surface-raised"))
            row.pack(fill="x")
            if icon:
                tone = {"warning": "warning", "error": "danger-fg", "info": "text-secondary",
                        "success": "success"}[icon]
                tk.Label(row, image=get_icon(icon, th.size("icon"), th.c(tone)),
                         bg=row.cget("bg")).pack(side="left", anchor="n", padx=(0, th.sp(3)))
            C.Text(row, th, text, "body", "danger" if danger else "primary",
                   wrap=th.size("dialog_min_w")).pack(side="left", anchor="w")
        if build:
            build(self.body, self)
        foot = tk.Frame(outer, bg=th.c("surface-raised"))
        foot.pack(fill="x", pady=(th.sp(4), 0))
        self.primary = None
        for text_, variant, value in reversed(list(buttons)):
            b = C.Button(foot, th, text_, variant=variant, command=lambda v=value: self.close(v))
            b.pack(side="right", padx=(th.sp(2), 0))
            if variant == "primary" and self.primary is None:
                self.primary = (b, value)
        self.bind("<Escape>", lambda e: (C.note_key("Escape"), self.close(None)))
        self.bind("<Return>", self._enter)
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), th.size("dialog_min_w"))
        h = self.winfo_reqheight()
        x = root.winfo_rootx() + (root.winfo_width() - w) // 2
        y = root.winfo_rooty() + (root.winfo_height() - h) // 3
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = max(0, min(x, sw - w))
        y = max(0, min(y, sh - h))
        self.geometry(f"{w}x{h}+{x}+{y}")
        for hook in window_hooks:
            hook(self, th)
        C.window_badge(self, th, kind)                # режим «номера окон»
        self.deiconify()
        self.grab_set()
        if self.primary:
            C.focus_auto(self.primary[0])   # Enter нажмёт её; кольцо — только если пришли с клавиатуры
        else:
            self.focus_force()

    def _enter(self, e):
        if C.is_text_input(e.widget) or isinstance(e.widget, C.Control) and e.widget is not \
                (self.primary and self.primary[0]):
            return None
        if self.primary:
            self.close(self.primary[1])
        return "break"

    def close(self, value):
        self.result = value
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def wait(self):
        self.master.wait_window(self)
        return self.result


def changes_list(parent, dlg, th, versions):
    """Содержимое окна «Что нового». versions: [(номер, [(раздел, [пункты])])], новые сверху."""
    tone, wrap = "surface-raised", th.size("changes_w")
    area = C.ScrollArea(parent, th, tone, wheel=False)
    area.cv.configure(width=wrap + th.sp(3), height=th.size("changes_h"))
    area.pack(fill="both", expand=True)
    dlg.bind("<MouseWheel>", lambda e: area.cv.yview_scroll(-e.delta // 120, "units"))
    for n, (version, sections) in enumerate(versions):
        C.Text(area.body, th, f"V{version}", "title", weight="strong").pack(
            anchor="w", pady=(th.sp(6) if n else 0, 0))
        for title, items in sections:
            C.Text(area.body, th, tr(title), "body", "secondary", "strong").pack(
                anchor="w", pady=(th.sp(4), th.sp(1)))
            for item in items:
                row = tk.Frame(area.body, bg=th.c(tone))
                row.pack(fill="x", pady=(th.sp(1), 0))
                dot = C.Text(row, th, "•", "body", "secondary")
                dot.pack(side="left", anchor="n", padx=(0, th.sp(2)))
                C.Text(row, th, tr(item), "body", wrap=wrap - dot.winfo_reqwidth() - th.sp(2)).pack(
                    side="left", anchor="w")


def ask(root, th, title, text, buttons, icon="warning", kind="ask", danger=False):
    return Dialog(root, th, title, text=text, buttons=buttons, icon=icon, kind=kind, danger=danger).wait()


# ==========================================================================
# HUD на холсте оверлея (настоящее стекло)
# ==========================================================================
class CanvasHud:
    """Стеклянная панель с кнопками-иконками на холсте поверх известного фона.

    items:  [(id, icon, label, hotkey[, tone])]; tone="danger" — кнопка с заливкой опасности.
    hint:   строка или сегменты [(текст, роль, начертание, тон)] — справка/таймер.
    dot:    тон индикатора перед справкой (например "danger" — идёт запись) или None.
    hint_first: справка слева от кнопок (панель записи) или справа (панель режимов).
    reserve: сегменты максимальной длины — ширина панели не «прыгает», когда текст меняется.
    hard_edges: углы без полупрозрачности — для отдельного окна с цветом-ключом прозрачности.
    hover_label: "inline" — подпись наведённой кнопки вместо справки (панель режимов);
                 "below" — стеклянной плашкой под кнопкой, справка (таймер) всегда видна.
    Клавиатура: ←/→ — фокус, Enter/Space — выбрать, цифры 1..N — сразу выбрать."""

    def __init__(self, canvas, background, th, items, selected, on_pick, hint="", tag="hud",
                 dot=None, hint_first=False, reserve=None, hard_edges=False, hover_label="inline"):
        self.cv, self.bgimg, self.th = canvas, background, th
        self.items, self.selected, self.on_pick = items, selected, on_pick
        self.hint, self.tag, self.dot = hint, tag, dot
        self.hint_first, self.reserve, self.hard_edges = hint_first, reserve, hard_edges
        self.hover_label = hover_label
        self.dot_on = True
        self.focus = None
        self.hover = None
        self._imgs = []
        self._glass = None          # (box, PhotoImage) — размытие считается один раз
        self.rects = []

    # --- размеры ---
    def _segments(self, hint):
        if not hint:
            return []
        if isinstance(hint, str):
            return [(hint, "caption", "regular", "primary")]
        return list(hint)

    def _hint_width(self):
        th = self.th
        segs = self._segments(self.reserve or self.hint)
        if not segs:
            return 0
        w = sum(th.measure(t, r, wgt) for t, r, wgt, _ in segs) + th.sp(2) * (len(segs) - 1)
        if self.dot:
            w += th.sp(3) + th.sp(2)
        return w + 2 * th.sp(3)

    def measure(self):
        th = self.th
        btn = th.size("control")
        pad = th.sp(2)
        w = pad * 2 + len(self.items) * (btn + th.sp(1)) + self._hint_width()
        return w, btn + 2 * pad

    def place_at(self, l, t):
        w, h = self.measure()
        self.box = (l, t, l + w, t + h)
        self.draw()
        return self.box

    def place_top_center(self, cx, top):
        w, _ = self.measure()
        return self.place_at(cx - w // 2, top)

    def _tint_colors(self):
        th = self.th
        return paint.glass_worst_bg(th.c("glass-tint"), th.glass("fill_alpha"))

    # --- отрисовка ---
    def draw(self):
        th = self.th
        cv = self.cv
        cv.delete(self.tag)
        self._imgs = []
        l, t, r, b = self.box
        if not self._glass or self._glass[0] != self.box:
            g = paint.glass(self.bgimg, self.box, th.c("glass-tint"), th.glass("fill_alpha"),
                            th.c("glass-border"), th.glass("border_alpha"), th.r("lg"),
                            th.px(th.glass("blur")))
            if self.hard_edges:
                g.putalpha(g.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
            self._glass = (self.box, ImageTk.PhotoImage(g))
        cv.create_image(l, t, anchor="nw", image=self._glass[1], tags=self.tag)
        btn = th.size("control")
        pad = th.sp(2)
        hint_w = self._hint_width()
        x = l + pad + (hint_w if self.hint_first else 0)
        self.rects = []
        under = self._tint_colors()
        for i, item in enumerate(self.items):
            iid, ic, label, hk = item[:4]
            tone = item[4] if len(item) > 4 else None
            rect = (x, t + pad, x + btn, t + pad + btn)
            self.rects.append((rect, iid))
            sel = iid == self.selected
            hov = self.hover == iid
            fill = None
            if tone == "danger":
                fill = th.c("danger-hover" if hov else "danger")
            elif sel:
                fill = th.c("accent")
            elif hov:
                fill = paint.mix(th.c("text-primary"), under, 0.14)
            if fill:
                im = ImageTk.PhotoImage(_rounded_pil(btn, btn, th.r("md"), fill))
                self._imgs.append(im)
                cv.create_image(x, t + pad, anchor="nw", image=im, tags=self.tag)
            if self.focus == i:
                cv.create_rectangle(x - 2, t + pad - 2, x + btn + 2, t + pad + btn + 2,
                                    outline=th.c("focus-ring"), width=th.size("focus"), tags=self.tag)
            col = th.c("text-on-danger") if tone == "danger" else                 th.c("text-on-accent") if sel else th.c("text-primary")
            ii = ImageTk.PhotoImage(pil_icon(ic, th.size("icon"), col))
            self._imgs.append(ii)
            cv.create_image(x + btn // 2, t + pad + btn // 2, image=ii, tags=self.tag)
            x += btn + th.sp(1)
        segs = self._segments(self.hint)
        hover_text = None
        for item in self.items:
            if item[0] == self.hover:
                hover_text = f"{item[2]}  ·  {item[3]}" if item[3] else item[2]
        self.cv.delete(self.tag + "_tip")
        if hover_text and self.hover_label == "inline":   # подпись вместо справки
            segs = [(hover_text, "caption", "regular", "primary")]
        elif hover_text:                                   # подпись плашкой под кнопкой
            (bl, bt, br, bb), _ = [rc for rc in self.rects if rc[1] == self.hover][0]
            w = th.measure(hover_text, "caption") + 2 * th.sp(2)
            self._tip_img = glass_chip(cv, self.bgimg, th, (bl + br) // 2 - w // 2, b + th.sp(1),
                                       hover_text, tag=self.tag + "_tip", hard_edges=self.hard_edges)
        if not segs:
            return
        hx = (l + pad + th.sp(3)) if self.hint_first else (x + th.sp(2))
        cy = (t + b) // 2
        if self.dot and (self.hover is None or self.hover_label != "inline"):
            d = th.sp(3)
            if self.dot_on:
                cv.create_oval(hx, cy - d // 2, hx + d, cy + d // 2, fill=th.c(
                    {"danger": "danger-fg", "warning": "warning", "accent": "accent-fg"}[self.dot]),
                    outline="", tags=self.tag)
            hx += d + th.sp(2)
        for text, role, weight, tone in segs:
            cv.create_text(hx, cy, anchor="w", text=text, fill=th.c(C.TONES[tone]),
                           font=th.font(role, weight), tags=self.tag)
            hx += th.measure(text, role, weight) + th.sp(2)

    def hit(self, x, y):
        for (l, t, r, b), iid in self.rects:
            if l <= x < r and t <= y < b:
                return iid
        return None

    def contains(self, x, y):
        l, t, r, b = self.box
        return l <= x < r and t <= y < b

    def motion(self, x, y):
        h = self.hit(x, y)
        if h != self.hover:
            self.hover = h
            self.draw()

    def click(self, x, y):
        h = self.hit(x, y)
        if h is not None:
            self.on_pick(h)
            return True
        return self.contains(x, y)

    def key(self, keysym):
        n = len(self.items)
        if keysym.isdigit() and 1 <= int(keysym) <= n:
            self.on_pick(self.items[int(keysym) - 1][0])
            return True
        if keysym in ("Left", "Right", "Tab"):
            if self.focus is None:
                self.focus = 0
            else:
                self.focus = (self.focus + (-1 if keysym == "Left" else 1)) % n
            self.draw()
            return True
        if keysym in ("Return", "space") and self.focus is not None:
            self.on_pick(self.items[self.focus][0])
            return True
        return False


def _rounded_pil(w, h, radius, fill):
    from PIL import ImageDraw
    s = paint.SUPERSAMPLE
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=radius * s,
                                          fill=paint.hex_rgb(fill) + (255,))
    return img.resize((w, h), Image.LANCZOS)


def glass_chip(canvas, background, th, x, y, text, tag="chip", hard_edges=False):
    """Компактная стеклянная плашка с текстом (размер выделения, подсказка кнопки)."""
    canvas.delete(tag)
    w = th.measure(text, "caption") + 2 * th.sp(2)
    h = th.line("caption") + th.sp(2)
    W, H = background.size
    x = max(0, min(x, W - w))
    y = max(0, min(y, H - h))
    g = paint.glass(background, (x, y, x + w, y + h), th.c("glass-tint"), th.glass("fill_alpha"),
                    th.c("glass-border"), th.glass("border_alpha"), th.r("sm"), th.px(th.glass("blur")))
    if hard_edges:
        g.putalpha(g.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
    img = ImageTk.PhotoImage(g)
    canvas.create_image(x, y, anchor="nw", image=img, tags=tag)
    canvas.create_text(x + w // 2, y + h // 2, text=text, fill=th.c("text-primary"),
                       font=th.font("caption"), tags=tag)
    return img
