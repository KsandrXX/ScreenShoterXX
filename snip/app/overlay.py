# -*- coding: utf-8 -*-
"""Оверлей захвата: «замороженный» экран, тонкая рамка выделения, стеклянный HUD."""

import tkinter as tk

from PIL import Image, ImageTk

from ..core.winapi import monitor_under_cursor
from ..ui import components as C
from ..ui.layouts import CanvasHud, glass_chip


class Overlay(tk.Toplevel):
    """modes: [(id, icon, label, hotkey)] — переключатель режима на HUD.
    on_done(result | None): result = {"box": (l, t, r, b), "poly": [...] | None}
    on_mode(mode_id) — пользователь сменил режим на HUD."""

    def __init__(self, root, th, shot, origin, mode, windows, modes, on_mode, on_done, hint):
        super().__init__(root)
        self.th, self.shot = th, shot
        self.vx, self.vy = origin
        self.mode, self.windows = mode, windows
        self.on_done, self.on_mode = on_done, on_mode
        self.start, self.points, self.box = None, [], None
        self._pending = self._finished = False

        w, h = shot.size
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"{w}x{h}+{self.vx}+{self.vy}")
        dim = Image.blend(shot, Image.new("RGB", shot.size, th.c("overlay")), th.glass("scrim_alpha"))
        self.dim = dim
        self.dim_tk = ImageTk.PhotoImage(dim)

        self.cv = tk.Canvas(self, width=w, height=h, highlightthickness=0, bd=0, cursor="crosshair")
        self.cv.pack(fill="both", expand=True)
        self.cv.create_image(0, 0, anchor="nw", image=self.dim_tk)
        self.bright = self.cv.create_image(0, 0, anchor="nw")
        sb = th.size("selection_border")
        self.rect = self.cv.create_rectangle(0, 0, 0, 0, outline=th.c("accent"), width=sb, state="hidden")
        self.line = self.cv.create_line(0, 0, 0, 0, fill=th.c("accent"), width=th.size("focus"), state="hidden")

        mx, my, mw, _ = monitor_under_cursor()
        self.hud = CanvasHud(self.cv, dim, th, modes, mode, self._pick_mode, hint)
        self.hud.place_top_center(mx - self.vx + mw // 2, my - self.vy + th.sp(4))
        C.window_badge(self, th, "overlay", x=mx - self.vx + th.sp(2), y=my - self.vy + th.sp(2))   # режим «номера окон»

        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Motion>", self.on_move)
        self.cv.bind("<ButtonPress-3>", lambda e: self.finish(None))
        self.bind("<Escape>", lambda e: self.finish(None))
        self.bind("<KeyPress>", self._key)
        self.after(30, self._focus)

    def _focus(self):
        self.lift()
        self.focus_force()
        self.cv.focus_set()

    def _key(self, e):
        if e.keysym != "Escape" and self.hud.key(e.keysym):
            return "break"
        return None

    def _pick_mode(self, mode):
        self.mode = mode
        self.hud.selected = mode
        self.hud.draw()
        self.box = None
        self.cv.itemconfigure(self.rect, state="hidden")
        self.cv.itemconfigure(self.bright, state="hidden")
        self.cv.delete("chip")
        self.on_mode(mode)

    # --- отрисовка ---
    def show_box(self, l, t, r, b):
        th = self.th
        l, t = max(0, l), max(0, t)
        r, b = min(self.shot.width, r), min(self.shot.height, b)
        if r - l < 1 or b - t < 1:
            return
        self.box = (l, t, r, b)
        self.cv.coords(self.rect, l, t, r, b)
        self.cv.itemconfigure(self.rect, state="normal")
        chip_h = th.line("caption") + th.sp(2)
        y = t - chip_h - th.sp(1) if t > chip_h + th.sp(2) else b + th.sp(1)
        self._chip = glass_chip(self.cv, self.dim, th, l, y, f"{r - l} × {b - t}")
        self.cv.tag_raise("hud")
        if not self._pending:
            self._pending = True
            self.after_idle(self._update_bright)

    def _update_bright(self):
        self._pending = False
        if self._finished or not self.box:
            return
        l, t, r, b = self.box
        self.bright_tk = ImageTk.PhotoImage(self.shot.crop(self.box))
        self.cv.itemconfigure(self.bright, image=self.bright_tk, state="normal")
        self.cv.coords(self.bright, l, t)
        self.cv.tag_raise(self.rect)
        self.cv.tag_raise("chip")
        self.cv.tag_raise("hud")

    def window_at(self, x, y):
        sx, sy = x + self.vx, y + self.vy
        for (l, t, r, b) in self.windows:
            if l <= sx < r and t <= sy < b:
                return (l - self.vx, t - self.vy, r - self.vx, b - self.vy)
        return None

    # --- мышь ---
    def on_move(self, e):
        if self.hud.contains(e.x, e.y):
            self.hud.motion(e.x, e.y)
            self.cv.configure(cursor="hand2")
            return
        self.hud.motion(-1, -1)
        self.cv.configure(cursor="crosshair")
        if self.mode == "window" and not self.start:
            wr = self.window_at(e.x, e.y)
            if wr:
                self.show_box(*wr)

    def on_press(self, e):
        if self.hud.contains(e.x, e.y):
            self.hud.click(e.x, e.y)
            return
        if self.mode == "window":
            wr = self.window_at(e.x, e.y)
            if wr:
                self.show_box(*wr)
                self.finish({"box": self.box, "poly": None})
            return
        self.start = (e.x, e.y)
        if self.mode == "free":
            self.points = [(e.x, e.y)]
            self.cv.itemconfigure(self.line, state="normal")

    def on_drag(self, e):
        if not self.start:
            return
        if self.mode == "free":
            self.points.append((e.x, e.y))
            flat = [c for p in self.points for c in p]
            if len(flat) >= 4:
                self.cv.coords(self.line, *flat)
        else:
            x0, y0 = self.start
            self.show_box(min(x0, e.x), min(y0, e.y), max(x0, e.x) + 1, max(y0, e.y) + 1)

    def on_release(self, e):
        if not self.start:
            return
        self.start = None
        if self.mode == "free":
            if len(self.points) < 3:
                self.cv.itemconfigure(self.line, state="hidden")
                return
            xs = [p[0] for p in self.points]
            ys = [p[1] for p in self.points]
            box = (max(0, min(xs)), max(0, min(ys)),
                   min(self.shot.width, max(xs) + 1), min(self.shot.height, max(ys) + 1))
            if box[2] - box[0] >= 3 and box[3] - box[1] >= 3:
                self.finish({"box": box, "poly": list(self.points)})
        elif self.box and self.box[2] - self.box[0] >= 3 and self.box[3] - self.box[1] >= 3:
            self.finish({"box": self.box, "poly": None})
        else:
            self.box = None
            self.cv.itemconfigure(self.rect, state="hidden")
            self.cv.itemconfigure(self.bright, state="hidden")
            self.cv.delete("chip")

    def finish(self, result):
        if self._finished:
            return
        self._finished = True
        self.destroy()
        self.on_done(result)
