# -*- coding: utf-8 -*-
"""Запись области экрана в GIF (без интерфейса)."""

import threading
import time

from PIL import Image

from .dxgi import Duplicator
from .winapi import grab


class GifCapture:
    MEMORY_BUDGET = 1_500_000_000  # ~1.5 ГБ на кадры (1 байт/пиксель)
    MIN_FRAME_MS = 20              # браузеры показывают кадры короче 20 мс как 100 мс
    DXGI_RETRY_S = 1.0             # захват потерян (игра сменила режим экрана) — как часто пробовать снова

    def __init__(self, x, y, w, h, fps=10, scale=1.0, cursor=True, limit=0):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.fps, self.scale, self.cursor = float(fps), scale, cursor   # fps может быть дробным: 12.5
        self.out_w = max(1, round(w * scale))
        self.out_h = max(1, round(h * scale))
        self.max_frames = max(10, self.MEMORY_BUDGET // (self.out_w * self.out_h))
        self.frames, self.times = [], []
        self.stop_flag = self.paused = self.limit_hit = False
        self.limit = float(limit or 0)          # длительность записи, с (без пауз); 0 — без лимита
        self.limit_reached = False
        self.pause_start = 0.0
        self.paused_total = 0.0
        self.t_start = time.perf_counter()
        self.dup = None                         # Desktop Duplication (B38); None — кадры через GDI
        self.dup_retry = None                   # когда снова открыть потерянный захват
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self, warmup=0.15):
        self.warmup = warmup
        self.t_start = time.perf_counter() + warmup   # отсчёт — с первого кадра
        self.thread.start()

    def _open_dup(self):
        try:
            self.dup = Duplicator(self.x, self.y, self.w, self.h)
        except Exception:                       # старая система, два монитора, поворот — останется GDI
            self.dup = None

    def _close_dup(self):
        if self.dup:
            self.dup.close()
            self.dup = None

    def _frame(self):
        """Кадр: Desktop Duplication видит полноэкранные игры, GDI — нет (B38: «0,02 fps»).
        Захват потерян посреди записи — кадры идут через GDI, раз в DXGI_RETRY_S — попытка вернуть."""
        if self.dup is None and self.dup_retry and time.perf_counter() >= self.dup_retry:
            self._open_dup()
            self.dup_retry = None if self.dup else time.perf_counter() + self.DXGI_RETRY_S
        if self.dup is not None:
            try:
                return self.dup.grab(cursor=self.cursor)
            except Exception:
                self._close_dup()
                self.dup_retry = time.perf_counter() + self.DXGI_RETRY_S
        return grab(self.x, self.y, self.w, self.h, cursor=self.cursor)

    def _loop(self):
        self._open_dup()                        # в потоке записи: объект живёт в одном потоке
        try:
            self._record()
        finally:
            self._close_dup()

    def _record(self):
        interval = 1.0 / self.fps
        time.sleep(self.warmup)
        next_t = time.perf_counter()
        while not self.stop_flag:
            if self.paused:
                time.sleep(0.03)
                next_t = time.perf_counter()
                continue
            t = time.perf_counter()
            if self.limit and t - self.t_start - self.paused_total >= self.limit:
                self.limit_reached = True       # время вышло: больше кадров не снимаем
                break
            try:
                img = self._frame()
                if self.scale != 1:
                    img = img.resize((self.out_w, self.out_h), Image.BILINEAR)
                frame = img.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
            except Exception:
                time.sleep(interval)
                continue
            self.frames.append(frame)
            self.times.append(t - self.paused_total)
            if len(self.frames) >= self.max_frames:
                self.limit_hit = True
                break
            next_t += interval
            delay = next_t - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                next_t = time.perf_counter()

    def elapsed(self):
        now = self.pause_start if self.paused else time.perf_counter()
        e = max(0.0, now - self.t_start - self.paused_total)
        return min(e, self.limit) if self.limit else e

    def toggle_pause(self):
        if self.paused:
            self.paused_total += time.perf_counter() - self.pause_start
            self.paused = False
        else:
            self.pause_start = time.perf_counter()
            self.paused = True
        return self.paused

    def stop(self):
        self.stop_flag = True
        self.thread.join(timeout=3)
        frames, times = self.frames, self.times
        self.frames, self.times = [], []
        return frames, times

    def durations(self, times, count):
        interval_ms = 1000.0 / self.fps
        out = []
        for i in range(count):
            d = (times[i + 1] - times[i]) * 1000 if i + 1 < len(times) else interval_ms
            out.append(max(self.MIN_FRAME_MS, int(round(d / 10.0)) * 10))
        return out


def save_gif_async(path, frames, durations, done):
    """Сохранить в фоне; done(error_or_None) вызывается из рабочего потока."""
    def work():
        try:
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                           loop=0, optimize=False, disposal=1)
            done(None)
        except Exception as ex:
            done(ex)
    th = threading.Thread(target=work, daemon=True)
    th.start()
    return th
