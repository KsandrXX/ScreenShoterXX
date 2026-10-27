# -*- coding: utf-8 -*-
"""Пипетка: «замороженный» экран, лупа с пикселями и HEX, выбор цвета мышью или клавиатурой."""

import tkinter as tk

from PIL import Image, ImageTk

from ..core.colors import rgb_to_hex
from ..core.i18n import tr
from ..core.winapi import monitor_under_cursor
from ..ui import paint
from ..ui import components as C
from ..ui.layouts import CanvasHud, glass_chip


class Eyedropper(tk.Toplevel):
    """on_done((r, g, b) | None). Экран показывается без затемнения — цвета точные."""

    HINT = "Пипетка: щёлкните по цвету  ·  стрелки — на пиксель  ·  Enter — взять  ·  Esc — отмена"

    def __init__(self, root, th, shot, origin, on_done):
        super().__init__(root)
        self.th, self.shot, self.on_done = th, shot, on_done
        self.vx, self.vy = origin
        self.pos = None
        self._done = False
        w, h = shot.size
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"{w}x{h}+{self.vx}+{self.vy}")
        self.shot_tk = ImageTk.PhotoImage(shot)
        self.cv = tk.Canvas(self, width=w, height=h, highlightthickness=0, bd=0, cursor="tcross")
        self.cv.pack(fill="both", expand=True)
        self.cv.create_image(0, 0, anchor="nw", image=self.shot_tk)
        mx, my, mw, _ = monitor_under_cursor()
        self.hud = CanvasHud(self.cv, shot, th, [], None, lambda v: None, tr(self.HINT))
        self.hud.place_top_center(mx - self.vx + mw // 2, my - self.vy + th.sp(4))
        C.window_badge(self, th, "eyedropper", x=mx - self.vx + th.sp(2), y=my - self.vy + th.sp(2))   # режим «номера окон»

        self.cv.bind("<Motion>", lambda e: self.show(e.x, e.y))
        self.cv.bind("<ButtonPress-1>", lambda e: (self.show(e.x, e.y), self.pick()))
        self.cv.bind("<ButtonPress-3>", lambda e: self.finish(None))
        self.bind("<Escape>", lambda e: self.finish(None))
        self.bind("<Return>", lambda e: self.pick())
        self.bind("<KeyPress-space>", lambda e: self.pick())
        for k, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            self.bind(f"<{k}>", lambda e, dx=dx, dy=dy: self.nudge(dx, dy))
        self.after(30, self._focus)

    def _focus(self):
        self.lift()
        self.focus_force()
        self.cv.focus_set()
        px, py = self.winfo_pointerxy()
        self.show(px - self.vx, py - self.vy)

    def nudge(self, dx, dy):
        if self.pos:
            x, y = self.pos[0] + dx, self.pos[1] + dy
            self.cv.event_generate("<Motion>", warp=True, x=x, y=y)   # двигаем и курсор мыши
            self.show(x, y)
        return "break"

    def color_at(self, x, y):
        return self.shot.getpixel((x, y))[:3]

    def show(self, x, y):
        th = self.th
        W, H = self.shot.size
        x, y = max(0, min(W - 1, int(x))), max(0, min(H - 1, int(y)))
        self.pos = (x, y)
        n = th.layout("loupe_cells")
        half = n // 2
        size = th.size("loupe")
        cell = size / n
        # кусок экрана n×n вокруг курсора (за краем — фон окна)
        crop = Image.new("RGB", (n, n), paint.hex_rgb(th.c("bg")))
        crop.paste(self.shot.crop((x - half, y - half, x + half + 1, y + half + 1)), (0, 0))
        self.loupe_tk = ImageTk.PhotoImage(crop.resize((size, size), Image.NEAREST))
        gap = th.sp(5)
        lx = x + gap if x + gap + size < W else x - gap - size
        ly = y + gap if y + gap + size + th.sp(8) < H else y - gap - size - th.sp(8)
        cv = self.cv
        cv.delete("loupe")
        cv.create_image(lx, ly, anchor="nw", image=self.loupe_tk, tags="loupe")
        cv.create_rectangle(lx, ly, lx + size, ly + size, outline=th.c("border-strong"),
                            width=th.size("border"), tags="loupe")
        rgb = self.color_at(x, y)
        here = rgb_to_hex(*rgb)
        a, b = th.c("text-primary"), th.c("bg")
        mark = a if paint.contrast(a, here) >= paint.contrast(b, here) else b
        c0 = lx + half * cell
        r0 = ly + half * cell
        cv.create_rectangle(c0, r0, c0 + cell, r0 + cell, outline=mark, width=th.size("focus"), tags="loupe")
        sw = th.size("swatch")
        chip_h = th.line("caption") + th.sp(2)
        cy = ly + size + th.sp(1)
        cv.delete("loupe_sw")
        cv.create_rectangle(lx, cy + (chip_h - sw) // 2, lx + sw, cy + (chip_h + sw) // 2,
                            fill=here, outline=th.c("border-strong"), tags="loupe_sw")
        self._chip = glass_chip(cv, self.shot, th, lx + sw + th.sp(1), cy,
                                f"{here.upper()}   RGB {rgb[0]}, {rgb[1]}, {rgb[2]}", tag="loupe_chip")
        cv.tag_raise("hud")

    def pick(self):
        if self.pos:
            self.finish(self.color_at(*self.pos))

    def finish(self, rgb):
        if self._done:
            return
        self._done = True
        self.destroy()
        self.on_done(rgb)
