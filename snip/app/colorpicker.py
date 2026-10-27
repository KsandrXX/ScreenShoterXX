# -*- coding: utf-8 -*-
"""Палитра цветов в духе Photoshop, собранная из компонентов платформы."""

import colorsys
import re
import tkinter as tk

from PIL import Image, ImageTk

from ..core.colors import (cmyk_to_rgb, hex_to_rgb, lab_to_rgb, rgb_to_cmyk, rgb_to_hex,
                           rgb_to_lab)
from ..core.i18n import tr
from ..ui import components as C
from ..ui import paint
from ..core.winapi import grab, virtual_screen
from ..ui.layouts import Dialog, window_hooks
from ..ui.tokens import SIZE
from .eyedropper import Eyedropper

_GV = Image.linear_gradient("L").rotate(180)   # сверху 255 -> снизу 0
_GH = Image.linear_gradient("L").rotate(90)    # слева 0 -> справа 255
WEB_STEP = 51
SWATCH_LIMIT = 24


def _const(v, size):
    return Image.new("L", size, max(0, min(255, int(round(v)))))


class ColorPicker:
    """Модальный выбор цвета. ask() -> "#rrggbb" или None."""

    CHANNELS = [("H", "H:", "°"), ("S", "S:", "%"), ("V", "B:", "%"),
                ("R", "R:", ""), ("G", "G:", ""), ("B", "B:", "")]
    EXTRA = [("L", "L:", ""), ("A", "a:", ""), ("BB", "b:", ""),
             ("C", "C:", "%"), ("M", "M:", "%"), ("Y", "Y:", "%"), ("K", "K:", "%")]

    def __init__(self, root, th, settings, initial, title):
        self.root, self.th, self.settings = root, th, settings
        self.current = hex_to_rgb(initial)
        self.h = self.s = self.v = 0.0
        self.r = self.g = self.b = 0
        self.fields = {}
        self.web = False
        self.mode = C.RadioGroup("H", lambda v: self.redraw())
        self.dlg = Dialog(root, th, title, build=self._build,
                          buttons=((tr("Отмена"), "secondary", None), ("OK", "primary", True)), kind="colorpicker")
        self.set_rgb(*self.current)

    def ask(self):
        res = self.dlg.wait()
        return rgb_to_hex(self.r, self.g, self.b) if res else None

    # --- построение ---
    def _build(self, body, dlg):
        th = self.th
        bg = body.cget("bg")
        N = th.size("picker_field")
        bar = th.size("picker_bar")
        left = tk.Frame(body, bg=bg)
        left.grid(row=0, column=0, sticky="n")
        self.sq = tk.Canvas(left, width=N, height=N, highlightthickness=th.size("border"),
                            highlightbackground=th.c("border-strong"), bd=0, cursor="tcross",
                            takefocus=1)
        self.sq.grid(row=0, column=0)
        self.sq_img = self.sq.create_image(0, 0, anchor="nw")
        self.sq_mark = self.sq.create_oval(0, 0, 0, 0, width=th.size("border"))
        self.sq_mark2 = self.sq.create_oval(0, 0, 0, 0, width=th.size("border"))
        self.sq.bind("<ButtonPress-1>", self._sq_mouse)
        self.sq.bind("<B1-Motion>", self._sq_mouse)
        for k, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            self.sq.bind(f"<{k}>", lambda e, dx=dx, dy=dy: self._sq_key(dx, dy))
        self._focus_ring(self.sq)

        arrow = th.sp(2)
        self.sl = tk.Canvas(left, width=bar + 2 * arrow + 2, height=N + 2 * th.sp(1), bg=bg,
                            highlightthickness=0, bd=0, cursor="sb_v_double_arrow", takefocus=1)
        self.sl.grid(row=0, column=1, padx=(th.sp(2), 0))
        self.sl_img = self.sl.create_image(arrow + 1, th.sp(1), anchor="nw")
        self.sl.create_rectangle(arrow, th.sp(1) - 1, arrow + bar + 1, th.sp(1) + N,
                                 outline=th.c("border-strong"))
        self.sl_a1 = self.sl.create_polygon(0, 0, 0, 0, 0, 0, fill=th.c("text-primary"), outline=bg)
        self.sl_a2 = self.sl.create_polygon(0, 0, 0, 0, 0, 0, fill=th.c("text-primary"), outline=bg)
        self.sl.bind("<ButtonPress-1>", self._sl_mouse)
        self.sl.bind("<B1-Motion>", self._sl_mouse)
        self.sl.bind("<Up>", lambda e: self._sl_key(1))
        self.sl.bind("<Down>", lambda e: self._sl_key(-1))
        self._focus_ring(self.sl)

        self.web_cb = C.Checkbox(left, th, tr("Только Web-цвета"), on_change=self._web_changed)
        self.web_cb.grid(row=1, column=0, sticky="w", pady=(th.sp(2), 0))

        right = tk.Frame(body, bg=bg)
        right.grid(row=0, column=1, sticky="n", padx=(th.sp(4), 0))
        top = tk.Frame(right, bg=bg)
        top.pack(fill="x")
        pw, ph = th.size("picker_preview")
        pv = tk.Frame(top, bg=bg)
        pv.pack(side="left", anchor="n")
        C.Text(pv, th, tr("новый"), "caption", "secondary", anchor="center").pack()
        self.sw_new = tk.Frame(pv, width=pw, height=ph, highlightthickness=th.size("border"),
                               highlightbackground=th.c("border-strong"))
        self.sw_new.pack()
        cur = tk.Frame(pv, width=pw, height=ph, bg=rgb_to_hex(*self.current), cursor="hand2",
                       highlightthickness=th.size("border"), highlightbackground=th.c("border-strong"))
        cur.pack()
        cur.bind("<Button-1>", lambda e: self.set_rgb(*self.current))
        C.Tooltip(cur, th, tr("Вернуть текущий цвет"))
        C.Text(pv, th, tr("текущий"), "caption", "secondary", anchor="center").pack()
        acts = tk.Frame(top, bg=bg)
        acts.pack(side="left", anchor="n", padx=(th.sp(4), 0), pady=(th.line("caption"), 0))
        C.Button(acts, th, tr("Добавить в образцы"), icon="plus", command=self.add_swatch).pack(anchor="w")
        C.Button(acts, th, tr("Пипетка"), icon="eyedropper", command=self.eyedrop,
                 tooltip=(tr("Пипетка"), tr("Цвет с экрана или со снимка")), hotkey="I").pack(anchor="w")
        dlg.bind("<KeyPress-i>", lambda e: None if C.is_text_input(e.widget) else self.eyedrop())

        grid = tk.Frame(right, bg=bg)
        grid.pack(anchor="w", pady=(th.sp(3), 0))
        for i, (key, label, unit) in enumerate(self.CHANNELS):
            C.Radio(grid, th, self.mode, key, label, tooltip=(label, tr("Показывать на полосе"))
                    ).grid(row=i, column=0, sticky="w")
            self._field(grid, key).grid(row=i, column=1, padx=th.sp(1))
            C.Text(grid, th, unit, "caption", "secondary").grid(row=i, column=2, sticky="w")
        for i, (key, label, unit) in enumerate(self.EXTRA):
            C.Text(grid, th, label, "body", "secondary", anchor="e").grid(row=i, column=3, sticky="e",
                                                                         padx=(th.sp(4), th.sp(1)))
            self._field(grid, key).grid(row=i, column=4)
            C.Text(grid, th, unit, "caption", "secondary").grid(row=i, column=5, sticky="w",
                                                                padx=(th.sp(1), 0))
        hx = tk.Frame(right, bg=bg)
        hx.pack(anchor="w", pady=(th.sp(2), 0))
        C.Text(hx, th, "#", "body", "secondary").pack(side="left", padx=(th.sp(1), th.sp(1)))
        self._field(hx, "HEX", chars=SIZE["field_chars_hex"]).pack(side="left")

        self.sw_row = tk.Frame(body, bg=bg)
        self.sw_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(th.sp(3), 0))
        self._draw_swatches()

    def _field(self, parent, key, chars=None):
        f = C.TextField(parent, self.th, "", chars=chars or SIZE["field_chars"],
                        on_commit=lambda v, k=key: self.commit(k),
                        on_nudge=lambda d, k=key: self._nudge(k, d))
        self.fields[key] = f
        return f

    def _focus_ring(self, cv):
        """Кольцо фокуса — только при работе с клавиатуры (клик мышью его не зажигает)."""
        th = self.th
        cv._quiet = False

        def ring(on):
            cv.configure(highlightthickness=th.size("focus") if on else th.size("border"),
                         highlightbackground=th.c("focus-ring") if on else th.c("border-strong"))
        cv.bind("<FocusIn>", lambda e: ring(not cv._quiet), add="+")
        cv.bind("<FocusOut>", lambda e: (setattr(cv, "_quiet", False), ring(False)), add="+")
        cv.bind("<KeyPress>", lambda e: (setattr(cv, "_quiet", False), ring(True)), add="+")

    @staticmethod
    def _quiet_focus(cv):
        cv._quiet = True
        cv.focus_set()

    def _draw_swatches(self):
        th = self.th
        for w in self.sw_row.winfo_children():
            w.destroy()
        sw = self.settings["swatches"]
        if not sw:
            C.Text(self.sw_row, th, tr("Образцов пока нет — «Добавить в образцы» сохранит цвет"),
                   "caption", "secondary").pack(side="left")
            return
        C.Text(self.sw_row, th, tr("Образцы:"), "caption", "secondary").pack(side="left", padx=(0, th.sp(1)))
        for c in sw:
            f = C.ColorField(self.sw_row, th, c, small=True, tooltip=(c.upper(), tr("ПКМ или Delete — удалить")),
                             on_pick=lambda fld, c=c: self.set_rgb(*hex_to_rgb(c)))
            f.bind("<Button-3>", lambda e, c=c: self._remove_swatch(c))
            f.bind("<Delete>", lambda e, c=c: self._remove_swatch(c))
            f.pack(side="left")

    # --- модель ---
    def set_rgb(self, r, g, b):
        r, g, b = (max(0, min(255, int(round(c)))) for c in (r, g, b))
        if self.web:
            r, g, b = (int(round(c / WEB_STEP)) * WEB_STEP for c in (r, g, b))
        self.r, self.g, self.b = r, g, b
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if v > 0:
            if s > 0:
                self.h = h * 360
            self.s = s * 100
        self.v = v * 100
        self.redraw()

    def set_hsv(self, h, s, v):
        self.h, self.s, self.v = max(0.0, min(360.0, h)), max(0.0, min(100.0, s)), max(0.0, min(100.0, v))
        r, g, b = colorsys.hsv_to_rgb((self.h % 360) / 360, self.s / 100, self.v / 100)
        r, g, b = round(r * 255), round(g * 255), round(b * 255)
        if self.web:
            self.set_rgb(r, g, b)
            return
        self.r, self.g, self.b = r, g, b
        self.redraw()

    def _web_changed(self, v):
        self.web = v
        self.set_rgb(self.r, self.g, self.b)

    # --- отрисовка ---
    def redraw(self):
        th = self.th
        m = self.mode.value
        N = th.size("picker_field")
        size = (N, N)
        gv, gh = _GV.resize(size), _GH.resize(size)
        h8, s8, v8 = self.h / 360 * 255, self.s * 2.55, self.v * 2.55
        if m == "H":
            sq = Image.merge("HSV", (_const(h8, size), gh, gv)).convert("RGB")
            pos = (self.s / 100, 1 - self.v / 100)
        elif m == "S":
            sq = Image.merge("HSV", (gh, _const(s8, size), gv)).convert("RGB")
            pos = (self.h / 360, 1 - self.v / 100)
        elif m == "V":
            sq = Image.merge("HSV", (gh, gv, _const(v8, size))).convert("RGB")
            pos = (self.h / 360, 1 - self.s / 100)
        elif m == "R":
            sq = Image.merge("RGB", (_const(self.r, size), gv, gh))
            pos = (self.b / 255, 1 - self.g / 255)
        elif m == "G":
            sq = Image.merge("RGB", (gv, _const(self.g, size), gh))
            pos = (self.b / 255, 1 - self.r / 255)
        else:
            sq = Image.merge("RGB", (gh, gv, _const(self.b, size)))
            pos = (self.r / 255, 1 - self.g / 255)
        self._sq_tk = ImageTk.PhotoImage(sq)
        self.sq.itemconfigure(self.sq_img, image=self._sq_tk)
        x, y = pos[0] * (N - 1), pos[1] * (N - 1)
        here = rgb_to_hex(self.r, self.g, self.b)
        a, b_ = th.c("text-primary"), th.c("bg")
        near, far = (a, b_) if paint.contrast(a, here) >= paint.contrast(b_, here) else (b_, a)
        r1, r2 = th.sp(1) + 1, th.sp(1) + 2
        self.sq.coords(self.sq_mark, x - r1, y - r1, x + r1, y + r1)
        self.sq.coords(self.sq_mark2, x - r2, y - r2, x + r2, y + r2)
        self.sq.itemconfigure(self.sq_mark, outline=near)
        self.sq.itemconfigure(self.sq_mark2, outline=far)

        bw = th.size("picker_bar")
        bsize = (bw, N)
        col = gv.crop((0, 0, bw, N))
        full = _const(255, bsize)
        if m == "H":
            sl = Image.merge("HSV", (col, full, full)).convert("RGB")
            val = self.h / 360
        elif m == "S":
            sl = Image.merge("HSV", (_const(h8, bsize), col, _const(v8, bsize))).convert("RGB")
            val = self.s / 100
        elif m == "V":
            sl = Image.merge("HSV", (_const(h8, bsize), _const(s8, bsize), col)).convert("RGB")
            val = self.v / 100
        elif m == "R":
            sl = Image.merge("RGB", (col, _const(self.g, bsize), _const(self.b, bsize)))
            val = self.r / 255
        elif m == "G":
            sl = Image.merge("RGB", (_const(self.r, bsize), col, _const(self.b, bsize)))
            val = self.g / 255
        else:
            sl = Image.merge("RGB", (_const(self.r, bsize), _const(self.g, bsize), col))
            val = self.b / 255
        self._sl_tk = ImageTk.PhotoImage(sl)
        self.sl.itemconfigure(self.sl_img, image=self._sl_tk)
        arrow = th.sp(2)
        yy = th.sp(1) + (1 - val) * (N - 1)
        xr = arrow + bw + 2
        self.sl.coords(self.sl_a1, 0, yy - arrow // 2 - 1, arrow - 1, yy, 0, yy + arrow // 2 + 1)
        self.sl.coords(self.sl_a2, xr + arrow - 1, yy - arrow // 2 - 1, xr, yy, xr + arrow - 1, yy + arrow // 2 + 1)
        self.sw_new.configure(bg=here)
        self._update_fields()

    def _update_fields(self):
        L, a, bb = rgb_to_lab(self.r, self.g, self.b)
        c, m, y, k = rgb_to_cmyk(self.r, self.g, self.b)
        vals = {"H": round(self.h) % 360, "S": round(self.s), "V": round(self.v),
                "R": self.r, "G": self.g, "B": self.b, "L": round(L), "A": round(a), "BB": round(bb),
                "C": c, "M": m, "Y": y, "K": k, "HEX": rgb_to_hex(self.r, self.g, self.b)[1:]}
        for key, v in vals.items():
            f = self.fields[key]
            f.set(str(v))
            f.configure_state(error=False)

    # --- мышь и клавиатура ---
    def _apply_xy(self, fx, fy):
        m = self.mode.value
        if m == "H":
            self.set_hsv(self.h, fx * 100, (1 - fy) * 100)
        elif m == "S":
            self.set_hsv(fx * 360, self.s, (1 - fy) * 100)
        elif m == "V":
            self.set_hsv(fx * 360, (1 - fy) * 100, self.v)
        elif m == "R":
            self.set_rgb(self.r, (1 - fy) * 255, fx * 255)
        elif m == "G":
            self.set_rgb((1 - fy) * 255, self.g, fx * 255)
        else:
            self.set_rgb(fx * 255, (1 - fy) * 255, self.b)

    def _xy(self):
        m = self.mode.value
        return {"H": (self.s / 100, 1 - self.v / 100), "S": (self.h / 360, 1 - self.v / 100),
                "V": (self.h / 360, 1 - self.s / 100), "R": (self.b / 255, 1 - self.g / 255),
                "G": (self.b / 255, 1 - self.r / 255), "B": (self.r / 255, 1 - self.g / 255)}[m]

    def _sq_mouse(self, e):
        self._quiet_focus(self.sq)
        N = self.th.size("picker_field") - 1
        self._apply_xy(max(0, min(N, e.x)) / N, max(0, min(N, e.y)) / N)

    def _sq_key(self, dx, dy):
        fx, fy = self._xy()
        step = 1 / 100
        self._apply_xy(min(1, max(0, fx + dx * step)), min(1, max(0, fy + dy * step)))
        return "break"

    def _apply_val(self, val):
        m = self.mode.value
        if m == "H":
            self.set_hsv(val * 360, self.s, self.v)
        elif m == "S":
            self.set_hsv(self.h, val * 100, self.v)
        elif m == "V":
            self.set_hsv(self.h, self.s, val * 100)
        elif m == "R":
            self.set_rgb(val * 255, self.g, self.b)
        elif m == "G":
            self.set_rgb(self.r, val * 255, self.b)
        else:
            self.set_rgb(self.r, self.g, val * 255)

    def _sl_mouse(self, e):
        self._quiet_focus(self.sl)
        N = self.th.size("picker_field") - 1
        self._apply_val(1 - max(0, min(N, e.y - self.th.sp(1))) / N)

    def _sl_key(self, d):
        m = self.mode.value
        cur = {"H": self.h / 360, "S": self.s / 100, "V": self.v / 100,
               "R": self.r / 255, "G": self.g / 255, "B": self.b / 255}[m]
        self._apply_val(min(1, max(0, cur + d / 100)))
        return "break"

    # --- поля ---
    def _num(self, key, lo, hi):
        try:
            return max(lo, min(hi, float(self.fields[key].get().replace(",", "."))))
        except ValueError:
            return None

    def commit(self, key):
        g = self._num
        ok = False
        if key in ("H", "S", "V"):
            vals = g("H", 0, 360), g("S", 0, 100), g("V", 0, 100)
            if None not in vals:
                self.set_hsv(*vals)
                ok = True
        elif key in ("R", "G", "B"):
            vals = g("R", 0, 255), g("G", 0, 255), g("B", 0, 255)
            if None not in vals:
                self.set_rgb(*vals)
                ok = True
        elif key in ("L", "A", "BB"):
            vals = g("L", 0, 100), g("A", -128, 127), g("BB", -128, 127)
            if None not in vals:
                self.set_rgb(*lab_to_rgb(*vals))
                ok = True
        elif key in ("C", "M", "Y", "K"):
            vals = g("C", 0, 100), g("M", 0, 100), g("Y", 0, 100), g("K", 0, 100)
            if None not in vals:
                self.set_rgb(*cmyk_to_rgb(*vals))
                ok = True
        elif key == "HEX":
            t = self.fields["HEX"].get().strip().lstrip("#")
            if len(t) == 3:
                t = "".join(ch * 2 for ch in t)
            if re.fullmatch(r"[0-9a-fA-F]{6}", t):
                self.set_rgb(*hex_to_rgb(t))
                ok = True
        if not ok:
            self.fields[key].configure_state(error=True)   # неверный ввод — подсветить

    def _nudge(self, key, d):
        if key == "HEX":
            return
        try:
            self.fields[key].set(str(int(float(self.fields[key].get())) + d))
        except ValueError:
            return
        self.commit(key)

    # --- пипетка ---
    def eyedrop(self):
        """Спрятать палитру, «заморозить» экран (окно со снимком остаётся видно) и взять цвет."""
        dlg = self.dlg
        dlg.grab_release()
        dlg.withdraw()
        dlg.after(200, self._eyedrop_start)

    def _eyedrop_start(self):
        vx, vy, vw, vh = virtual_screen()
        Eyedropper(self.root, self.th, grab(vx, vy, vw, vh), (vx, vy), self._eyedrop_done)

    def _eyedrop_done(self, rgb):
        dlg = self.dlg
        dlg.deiconify()
        for hook in window_hooks:
            hook(dlg, self.th)
        dlg.grab_set()
        dlg.focus_force()
        if rgb:
            self.set_rgb(*rgb)

    # --- образцы ---
    def add_swatch(self):
        c = rgb_to_hex(self.r, self.g, self.b)
        sw = list(self.settings["swatches"])
        if c in sw:
            sw.remove(c)
        sw.append(c)
        self.settings["swatches"] = sw[-SWATCH_LIMIT:]
        self._draw_swatches()

    def _remove_swatch(self, c):
        sw = list(self.settings["swatches"])
        if c in sw:
            sw.remove(c)
            self.settings["swatches"] = sw
        self._draw_swatches()
