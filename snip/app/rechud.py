# -*- coding: utf-8 -*-
"""Панель записи GIF: стеклянный HUD сверху экрана (как панель режимов на оверлее).

Отдельное окно без рамки: выезжает сверху над монитором, где идёт запись,
исключено из захвата (в GIF не попадает), фокус у других программ не забирает."""

import tkinter as tk

from ..core import winapi as W
from ..ui import components as C
from ..ui.layouts import CanvasHud
from ..ui.tokens import TECH


class RecHud(tk.Toplevel):
    """actions: действия поверхности «rec» из реестра (порядок = порядок кнопок)."""

    def __init__(self, root, th, region, actions, segments, reserve, stop_key=""):
        super().__init__(root)
        self.th, self.actions, self.stop_key = th, actions, stop_key
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        key = TECH["transparent_key"]
        self.attributes("-transparentcolor", key)
        self.cv = tk.Canvas(self, bg=key, highlightthickness=0, bd=0)
        self.cv.pack(fill="both", expand=True)

        x, y, w, h = region
        mx, my, mw, mh = W.monitor_at(x + w // 2, y + h // 2)
        self.hud = CanvasHud(self.cv, None, th, self._items(), None, self._pick, segments,
                             dot="danger", hint_first=True, reserve=reserve, hard_edges=True,
                             hover_label="below")       # подпись кнопки под панелью — таймер не закрыт
        hw, hh = self.hud.measure()
        tip_h = th.line("caption") + th.sp(2) + th.sp(1)  # место под плашку подписи (прозрачное)
        self.x = mx + (mw - hw) // 2
        self.y = my + th.sp(4)
        self.hud.bgimg = W.grab(self.x, self.y, hw, hh + tip_h)   # фон под стеклом
        self.cv.configure(width=hw, height=hh + tip_h)
        self.hud.place_at(0, 0)
        C.window_badge(self, th, "rechud", corner="nw")   # режим «номера окон»
        self.hh = hh
        self.cv.bind("<Motion>", lambda e: self.hud.motion(e.x, e.y))
        self.cv.bind("<Leave>", lambda e: self.hud.motion(-1, -1))
        self.cv.bind("<ButtonPress-1>", lambda e: self.hud.click(e.x, e.y))

        self.geometry(f"{hw}x{hh + tip_h}+{self.x}+{self.y - hh - th.sp(4)}")
        self.deiconify()
        W.set_capture_excluded(self)
        self._slide(0)

    def _items(self):
        """Кнопки из записей реестра. При наведении — подпись; у «Стоп» ещё и глобальная клавиша."""
        out = []
        for a in self.actions:
            title, icon = a.label() if a.label else (a.title, a.icon)
            danger = a.kind == "danger"
            out.append((a.id, icon, title, self.stop_key if danger else "", "danger" if danger else None))
        return out

    def _pick(self, aid):
        for a in self.actions:
            if a.id == aid and a.handler:
                a.handler()

    def _slide(self, step):
        """Выезд сверху за время MOTION.fast, с замедлением в конце."""
        th = self.th
        frames = max(1, th.motion("fast") // th.timing("frame"))
        k = min(1.0, (step + 1) / frames)
        ease = 1 - (1 - k) ** 3
        top = self.y - self.hh - th.sp(4)
        try:
            self.geometry(f"+{self.x}+{round(top + (self.y - top) * ease)}")
        except tk.TclError:
            return
        if k < 1:
            self.after(th.timing("frame"), lambda: self._slide(step + 1))

    def refresh(self, segments, paused):
        """Обновить таймер/справку и состояние паузы."""
        h = self.hud
        h.hint = segments
        h.dot = "warning" if paused else "danger"
        h.dot_on = paused or not h.dot_on       # мигает, пока идёт запись
        h.items = self._items()
        h.draw()

    def close(self):
        try:
            self.destroy()
        except tk.TclError:
            pass
