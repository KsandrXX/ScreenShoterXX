# -*- coding: utf-8 -*-
"""WinAPI через ctypes: захват экрана, буфер обмена, окна, мониторы, горячие клавиши."""

import ctypes
import ctypes.wintypes as wt
import io
import os
import sys
import subprocess
import threading

from PIL import Image

from .i18n import tr

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi
HANDLE = ctypes.c_void_p


def init_process(app_id):
    """DPI-осведомлённость (физические пиксели) и свой AppUserModelID для панели задач."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def system_scale():
    try:
        return user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


# ---- сигнатуры (важно для 64-битных хэндлов) ----
user32.GetDC.argtypes = [HANDLE]
user32.GetDC.restype = HANDLE
user32.ReleaseDC.argtypes = [HANDLE, HANDLE]
gdi32.CreateCompatibleDC.argtypes = [HANDLE]
gdi32.CreateCompatibleDC.restype = HANDLE
gdi32.CreateCompatibleBitmap.argtypes = [HANDLE, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = HANDLE
gdi32.SelectObject.argtypes = [HANDLE, HANDLE]
gdi32.SelectObject.restype = HANDLE
gdi32.BitBlt.argtypes = [HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         HANDLE, ctypes.c_int, ctypes.c_int, wt.DWORD]
gdi32.GetDIBits.argtypes = [HANDLE, HANDLE, wt.UINT, wt.UINT, ctypes.c_void_p,
                            ctypes.c_void_p, wt.UINT]
gdi32.DeleteObject.argtypes = [HANDLE]
gdi32.DeleteDC.argtypes = [HANDLE]
gdi32.CreateDIBSection.argtypes = [HANDLE, ctypes.c_void_p, wt.UINT, ctypes.c_void_p, HANDLE, wt.DWORD]
gdi32.CreateDIBSection.restype = HANDLE
user32.UpdateLayeredWindow.argtypes = [HANDLE, HANDLE, ctypes.c_void_p, ctypes.c_void_p, HANDLE,
                                       ctypes.c_void_p, wt.DWORD, ctypes.c_void_p, wt.DWORD]
user32.GetWindowLongW.argtypes = [HANDLE, ctypes.c_int]
user32.GetWindowLongPtrW.argtypes = [HANDLE, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_void_p
user32.SetWindowLongW.argtypes = [HANDLE, ctypes.c_int, ctypes.c_long]
user32.GetClientRect.argtypes = [HANDLE, ctypes.c_void_p]
user32.BeginDeferWindowPos.restype = HANDLE
gdi32.CreateSolidBrush.restype = HANDLE
user32.FillRect.argtypes = [HANDLE, ctypes.c_void_p, HANDLE]
user32.BeginPaint.argtypes = [HANDLE, ctypes.c_void_p]
user32.BeginPaint.restype = HANDLE
user32.EndPaint.argtypes = [HANDLE, ctypes.c_void_p]
user32.RedrawWindow.argtypes = [HANDLE, ctypes.c_void_p, HANDLE, wt.UINT]
user32.SetParent.argtypes = [HANDLE, HANDLE]
user32.SetParent.restype = HANDLE
user32.SetLayeredWindowAttributes.argtypes = [HANDLE, wt.DWORD, ctypes.c_ubyte, wt.DWORD]
user32.DeferWindowPos.argtypes = [HANDLE, HANDLE, HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.DeferWindowPos.restype = HANDLE
user32.EndDeferWindowPos.argtypes = [HANDLE]
user32.ClientToScreen.argtypes = [HANDLE, ctypes.c_void_p]
user32.DrawIconEx.argtypes = [HANDLE, ctypes.c_int, ctypes.c_int, HANDLE, ctypes.c_int,
                              ctypes.c_int, wt.UINT, HANDLE, wt.UINT]
user32.GetAncestor.argtypes = [HANDLE, wt.UINT]
user32.GetAncestor.restype = HANDLE
user32.SetWindowDisplayAffinity.argtypes = [HANDLE, wt.DWORD]
user32.OpenClipboard.argtypes = [HANDLE]
user32.SetClipboardData.argtypes = [wt.UINT, HANDLE]
user32.SetClipboardData.restype = HANDLE
user32.RegisterClipboardFormatW.argtypes = [wt.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wt.UINT
kernel32.GlobalAlloc.argtypes = [wt.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = HANDLE
kernel32.GlobalLock.argtypes = [HANDLE]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [HANDLE]
kernel32.GlobalFree.argtypes = [HANDLE]
user32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
user32.MonitorFromPoint.restype = HANDLE
user32.GetMonitorInfoW.argtypes = [HANDLE, ctypes.c_void_p]
dwmapi.DwmGetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
dwmapi.DwmSetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hCursor", HANDLE),
                ("ptScreenPos", wt.POINT)]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD), ("yHotspot", wt.DWORD),
                ("hbmMask", HANDLE), ("hbmColor", HANDLE)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT),
                ("dwFlags", wt.DWORD)]


class DROPFILES(ctypes.Structure):
    _fields_ = [("pFiles", wt.DWORD), ("pt", wt.POINT), ("fNC", wt.BOOL), ("fWide", wt.BOOL)]


user32.GetIconInfo.argtypes = [HANDLE, ctypes.POINTER(ICONINFO)]

SRCCOPY = 0x00CC0020
CAPTUREBLT = 0x40000000


# ---------------------------------------------------------------- экран
def virtual_screen():
    """(x, y, w, h) всего рабочего стола (все мониторы)."""
    return (user32.GetSystemMetrics(76), user32.GetSystemMetrics(77),
            user32.GetSystemMetrics(78), user32.GetSystemMetrics(79))


def monitor_under_cursor(work=False):
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    hmon = user32.MonitorFromPoint(pt, 2)
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    r = mi.rcWork if work else mi.rcMonitor
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def monitor_at(x, y, work=False):
    """Монитор, на котором лежит точка (x, y): (x, y, w, h)."""
    hmon = user32.MonitorFromPoint(wt.POINT(int(x), int(y)), 2)
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    r = mi.rcWork if work else mi.rcMonitor
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def _draw_cursor(mdc, ox, oy):
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if not user32.GetCursorInfo(ctypes.byref(ci)) or not (ci.flags & 1) or not ci.hCursor:
        return
    ii = ICONINFO()
    hx = hy = 0
    if user32.GetIconInfo(ci.hCursor, ctypes.byref(ii)):
        hx, hy = ii.xHotspot, ii.yHotspot
        if ii.hbmMask:
            gdi32.DeleteObject(ii.hbmMask)
        if ii.hbmColor:
            gdi32.DeleteObject(ii.hbmColor)
    user32.DrawIconEx(mdc, ci.ptScreenPos.x - ox - hx, ci.ptScreenPos.y - oy - hy,
                      ci.hCursor, 0, 0, 0, None, 3)


def grab(x, y, w, h, cursor=False):
    """Снимок прямоугольника экрана в абсолютных координатах -> PIL.Image RGB."""
    w, h = max(1, int(w)), max(1, int(h))
    hdc = user32.GetDC(None)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    old = gdi32.SelectObject(mdc, bmp)
    try:
        gdi32.BitBlt(mdc, 0, 0, w, h, hdc, int(x), int(y), SRCCOPY | CAPTUREBLT)
        if cursor:
            _draw_cursor(mdc, int(x), int(y))
        gdi32.SelectObject(mdc, old)
        bi = BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi.biWidth = w
        bi.biHeight = -h
        bi.biPlanes = 1
        bi.biBitCount = 32
        bi.biCompression = 0
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
        return Image.frombytes("RGB", (w, h), buf.raw, "raw", "BGRX")
    finally:
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(None, hdc)


# ---------------------------------------------------------------- буфер обмена
def _set_clipboard(items):
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        for fmt, data in items:
            hmem = kernel32.GlobalAlloc(0x0042, len(data))
            ptr = kernel32.GlobalLock(hmem)
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(hmem)
            if not user32.SetClipboardData(fmt, hmem):
                kernel32.GlobalFree(hmem)
                return False
        return True
    finally:
        user32.CloseClipboard()


def copy_image(img):
    out = io.BytesIO()
    img.convert("RGB").save(out, "BMP")
    return _set_clipboard([(8, out.getvalue()[14:])])  # CF_DIB


def copy_file(path):
    """Файл в буфер (как «Копировать» в проводнике) — GIF вставляется анимированным."""
    df = DROPFILES()
    df.pFiles = ctypes.sizeof(DROPFILES)
    df.fWide = 1
    data = bytes(df) + (os.path.abspath(path) + "\0").encode("utf-16-le") + b"\0\0"
    effect = user32.RegisterClipboardFormatW("Preferred DropEffect")
    return _set_clipboard([(15, data), (effect, (1).to_bytes(4, "little"))])


# ---------------------------------------------------------------- окна
def list_windows(exclude=()):
    """Видимые окна верхнего уровня в порядке Z: [(l, t, r, b), ...]. exclude — свои hwnd."""
    result = []
    skip = {int(h) for h in exclude if h}
    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, _):
        if (hwnd or 0) in skip or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        cloaked = ctypes.c_int(0)
        dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4)
        if cloaked.value or user32.GetWindowTextLengthW(hwnd) == 0:
            return True
        r = wt.RECT()
        if dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
            user32.GetWindowRect(hwnd, ctypes.byref(r))
        if r.right - r.left < 20 or r.bottom - r.top < 20:
            return True
        result.append((r.left, r.top, r.right, r.bottom))
        return True

    proc = WNDENUMPROC(cb)
    user32.EnumWindows(proc, 0)
    return result


def hwnd_of(win):
    win.update_idletasks()
    return user32.GetAncestor(win.winfo_id(), 2)


def set_capture_excluded(win, excluded=True):
    """Окно не попадает в снимки/запись (Windows 10 2004+). True — если Windows это приняла."""
    try:
        return bool(user32.SetWindowDisplayAffinity(hwnd_of(win), 0x11 if excluded else 0))
    except Exception:
        return False


DWMWA_USE_IMMERSIVE_DARK_MODE = 20          # Windows 10 2004+ / 11
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19      # Windows 10 1809–1909
SWP_REFRESH_FRAME = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020  # NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED
user32.SetWindowPos.argtypes = [HANDLE, HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.GetForegroundWindow.restype = HANDLE
user32.SendMessageW.argtypes = [HANDLE, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SetParent.argtypes = [HANDLE, HANDLE]
user32.SetParent.restype = HANDLE
user32.SetLayeredWindowAttributes.argtypes = [HANDLE, wt.DWORD, ctypes.c_ubyte, wt.DWORD]
WM_NCACTIVATE = 0x0086
RDW_FRAME_NOW = 0x0400 | 0x0001 | 0x0100   # FRAME | INVALIDATE | UPDATENOW


def set_titlebar_dark(win, dark):
    """Системный заголовок окна в тёмном или светлом варианте (как у тем Windows)."""
    try:
        hwnd = hwnd_of(win)
        val = ctypes.c_int(1 if dark else 0)
        # Уже такой — ничего не трогаем: «переактивация» рамки ниже — это мигание
        # «неактивно → активно», и при каждой смене вида оно было бы заметно.
        cur = ctypes.c_int(-1)
        if dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), DWMWA_USE_IMMERSIVE_DARK_MODE,
                                        ctypes.byref(cur), ctypes.sizeof(cur)) == 0 \
                and bool(cur.value) == bool(val.value):
            return
        for attr in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD):
            if dwmapi.DwmSetWindowAttribute(wt.HWND(hwnd), attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                break
        user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_REFRESH_FRAME)
        # Windows 10 не перерисовывает заголовок уже показанного окна сама:
        # «переактивируем» рамку с текущим состоянием активности и перерисовываем её.
        active = 1 if user32.GetForegroundWindow() == hwnd else 0
        user32.SendMessageW(hwnd, WM_NCACTIVATE, 1 - active, 0)
        user32.SendMessageW(hwnd, WM_NCACTIVATE, active, 0)
        user32.RedrawWindow(hwnd, None, None, RDW_FRAME_NOW)
    except Exception:
        pass


WM_NCACTIVATE_MSG = 0x0086
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
user32.SetWindowLongPtrW.argtypes = [HANDLE, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.CallWindowProcW.restype = LRESULT


class KeepFrameActive:
    """Пока открыт выпадающий список (отдельное окно, которое берёт фокус), рамка и заголовок
    главного окна остаются в «активных» цветах — без мигания при каждом клике.

    1) Перехват WM_NCACTIVATE(FALSE) у главного окна, пока hold > 0: окно рисуется активным
       (активация при этом проходит как обычно). Обработчик минимальный — без вызовов Tk.
    2) Запасной путь: сразу после захвата фокуса списком — синхронно WM_NCACTIVATE(TRUE).
    Когда список закрыт, а активна другая программа, окно честно рисуется неактивным."""

    def __init__(self, win):
        self.win = win
        self.hwnd = hwnd_of(win)
        self.hold = 0
        self.suppressed = 0           # сколько раз «неактивную» перерисовку не допустили (для тестов)
        self._old = None
        try:
            self._proc = WNDPROC(self._wndproc)
            self._old = user32.SetWindowLongPtrW(self.hwnd, -4, ctypes.cast(self._proc, ctypes.c_void_p))
        except Exception:
            self._old = None          # не вышло — остаётся запасной путь

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == WM_NCACTIVATE_MSG and not wp and self.hold > 0:
            self.suppressed += 1
            wp = 1                    # рисовать как активное
        return user32.CallWindowProcW(self._old, hwnd, msg, wp, lp)

    def acquire(self):
        self.hold += 1
        user32.SendMessageW(self.hwnd, WM_NCACTIVATE_MSG, 1, 0)

    def release(self):
        self.hold = max(0, self.hold - 1)
        if self.hold == 0:
            self.win.after(1, self._sync)

    def _sync(self):
        """Список закрыт: если активна уже чужая программа — показать окно неактивным."""
        try:
            fg = user32.GetForegroundWindow()
            if fg != self.hwnd and user32.GetAncestor(fg, 3) != self.hwnd:   # GA_ROOTOWNER
                user32.SendMessageW(self.hwnd, WM_NCACTIVATE_MSG, 0, 0)
        except Exception:
            pass


# ---------------------------------------------------------------- слои поверх окна (модальное окно)
WM_WINDOWPOSCHANGED = 0x0047
WM_WINDOWPOSCHANGING = 0x0046


class _WINDOWPOS(ctypes.Structure):
    _fields_ = [("hwnd", wt.HWND), ("hwndInsertAfter", wt.HWND), ("x", ctypes.c_int), ("y", ctypes.c_int),
                ("cx", ctypes.c_int), ("cy", ctypes.c_int), ("flags", wt.UINT)]


def client_rect(hwnd):
    """Клиентская область окна на экране: (x, y, w, h). Чистый WinAPI — можно звать из WndProc."""
    r = wt.RECT()
    user32.GetClientRect(ctypes.c_void_p(hwnd), ctypes.byref(r))
    p = wt.POINT(0, 0)
    user32.ClientToScreen(ctypes.c_void_p(hwnd), ctypes.byref(p))
    return p.x, p.y, r.right - r.left, r.bottom - r.top


class FrameWatch:
    """Слушатели перемещения и размера окна, вызываемые ПРЯМО из его оконной процедуры.
    Работают и пока окно тащат за заголовок или тянут за край: Windows крутит свой цикл, и
    after() Tk в это время не срабатывают (так оверлей отставал и терялся под окном).
    Слушатель f(x, y, w, h) получает клиентскую область на экране и трогает только WinAPI —
    не Tk. Подключается один раз на всё время жизни окна (поверх KeepFrameActive)."""

    def __init__(self, win):
        self.hwnd = hwnd_of(win)
        self.listeners = []
        self._erase = None            # кисть: чем заливать новую (ещё пустую) часть окна
        self._old = None
        try:
            self._proc = WNDPROC(self._wndproc)
            self._old = user32.SetWindowLongPtrW(self.hwnd, -4, ctypes.cast(self._proc, ctypes.c_void_p))
        except Exception:
            self._old = None

    def erase_with(self, color):
        """Пока задан цвет, новая (ещё не нарисованная) часть окна при растягивании заливается
        им, а не обычным фоном. None — как обычно."""
        if self._erase:
            gdi32.DeleteObject(ctypes.c_void_p(self._erase))
        self._erase = gdi32.CreateSolidBrush(_colorref(color)) if color else None

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == 0x0014 and self._erase:            # WM_ERASEBKGND
            r = wt.RECT()
            user32.GetClientRect(ctypes.c_void_p(hwnd), ctypes.byref(r))
            user32.FillRect(ctypes.c_void_p(wp), ctypes.byref(r), ctypes.c_void_p(self._erase))
            return 1
        if msg == WM_WINDOWPOSCHANGING and self.listeners:
            # ДО того, как Windows применит новый размер: оверлей переезжает в тот же кадр DWM,
            # что и окно (в WM_WINDOWPOSCHANGED он отставал на кадр — полоса по краю, рывки).
            # Сначала Tk (он может поправить размер под свои пределы), потом — итоговые числа.
            res = user32.CallWindowProcW(self._old, hwnd, msg, wp, lp)
            rect = self._predict(hwnd, lp)
            if rect:
                self._notify(rect)
            return res
        res = user32.CallWindowProcW(self._old, hwnd, msg, wp, lp)
        if msg == WM_WINDOWPOSCHANGED and self.listeners:
            self._notify(client_rect(hwnd))           # сверка с тем, что получилось на самом деле
        return res

    # f(exc_type, exc, tb) — куда сообщать ошибки слушателей (программа подключает журнал):
    # исключение из WndProc наружу пробросить нельзя, а молча глотать — значит искать вслепую
    on_error = None

    def _notify(self, rect):
        for f in list(self.listeners):
            try:
                f(*rect)
            except Exception:
                if FrameWatch.on_error:
                    try:
                        FrameWatch.on_error(*sys.exc_info())
                    except Exception:
                        pass

    @staticmethod
    def _predict(hwnd, lp):
        """Клиентская область, какой она станет после этого WM_WINDOWPOSCHANGING."""
        pos = ctypes.cast(lp, ctypes.POINTER(_WINDOWPOS)).contents
        if pos.flags & 0x0001 and pos.flags & 0x0002:          # NOSIZE и NOMOVE — не наш случай
            return None
        wr = wt.RECT()
        user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(wr))
        cx, cy, cw, ch = client_rect(hwnd)
        x, y = (wr.left, wr.top) if pos.flags & 0x0002 else (pos.x, pos.y)
        w, h = (wr.right - wr.left, wr.bottom - wr.top) if pos.flags & 0x0001 else (pos.cx, pos.cy)
        return (x + cx - wr.left, y + cy - wr.top,
                w - (wr.right - wr.left - cw), h - (wr.bottom - wr.top - ch))


class _BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


def _wrapper(handle):
    """Внешнее окно Tk для внутреннего handle (winfo_id) — его непосредственный родитель (верно и
    после переподчинения другому окну). Tk может пересоздать внешнее окно после показа — поэтому
    его каждый раз находим заново (чистый WinAPI, можно из WndProc)."""
    return user32.GetAncestor(ctypes.c_void_p(handle), 1)


def _ensure(handle, owner=None, layered=False):
    """Владелец (окно остаётся над ним) и стиль слоя — на ТЕКУЩЕМ внешнем окне. Возвращает его."""
    h = _wrapper(handle)
    if owner is not None:
        o = _wrapper(owner)
        if user32.GetWindowLongPtrW(ctypes.c_void_p(h), -8) != o:
            user32.SetWindowLongPtrW(ctypes.c_void_p(h), -8, ctypes.c_void_p(o))   # GWLP_HWNDPARENT
            # новый владелец — встать над ним сразу (иначе порядок обновится лишь при активации)
            user32.SetWindowPos(ctypes.c_void_p(h), None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
    if layered:
        ex = user32.GetWindowLongW(ctypes.c_void_p(h), -20)
        want = ex | 0x00080000 | 0x08000000                                       # LAYERED | NOACTIVATE
        if ex != want:
            user32.SetWindowLongW(ctypes.c_void_p(h), -20, want)
    return h


def show_layered(handle, img, x=None, y=None):
    """Окно с попиксельной прозрачностью (UpdateLayeredWindow): img — PIL RGBA, окно встаёт в
    (x, y) экрана размером с картинку; сквозь прозрачные места видно живое содержимое под ним."""
    from PIL import ImageChops
    hwnd = _ensure(handle, layered=True)
    w, h = img.size
    r, g, b, a = img.split()
    # Windows ждёт BGRA с цветом, уже умноженным на прозрачность
    data = Image.merge("RGBA", (ImageChops.multiply(b, a), ImageChops.multiply(g, a),
                                ImageChops.multiply(r, a), a)).tobytes()
    screen = user32.GetDC(None)
    mdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(screen))
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount, bi.biCompression = w, -h, 1, 32, 0
    bits = ctypes.c_void_p()
    dib = gdi32.CreateDIBSection(ctypes.c_void_p(mdc), ctypes.byref(bi), 0, ctypes.byref(bits), None, 0)
    try:
        ctypes.memmove(bits, data, len(data))
        old = gdi32.SelectObject(ctypes.c_void_p(mdc), ctypes.c_void_p(dib))
        blend = _BLENDFUNCTION(0, 0, 255, 1)                # AC_SRC_OVER, AC_SRC_ALPHA
        dst = None if x is None else ctypes.byref(wt.POINT(int(x), int(y)))
        ok = user32.UpdateLayeredWindow(ctypes.c_void_p(hwnd), ctypes.c_void_p(screen),
                                        dst, ctypes.byref(wt.SIZE(w, h)),
                                        ctypes.c_void_p(mdc), ctypes.byref(wt.POINT(0, 0)), 0,
                                        ctypes.byref(blend), 2)                      # ULW_ALPHA
        gdi32.SelectObject(ctypes.c_void_p(mdc), ctypes.c_void_p(old))
        return bool(ok)
    finally:
        gdi32.DeleteObject(ctypes.c_void_p(dib))
        gdi32.DeleteDC(ctypes.c_void_p(mdc))
        user32.ReleaseDC(None, ctypes.c_void_p(screen))


def move_window(handle, x, y):
    """Переставить окно Tk (handle = winfo_id), не трогая размер, порядок и фокус (можно из WndProc)."""
    user32.SetWindowPos(ctypes.c_void_p(_wrapper(handle)), None, int(x), int(y), 0, 0,
                        0x0001 | 0x0004 | 0x0010 | 0x0200)


class SolidFill:
    """Внешнее окно Tk без содержимого (затемнение) закрашивается сплошным цветом СРАЗУ — в его
    оконной процедуре. Иначе при растягивании новая часть окна пуста (прозрачна), пока Tk не
    растянет и не перерисует своё внутреннее окно: по краю видна незатемнённая полоса."""

    def __init__(self, handle, color):
        self.hwnd = _wrapper(handle)
        self.brush = gdi32.CreateSolidBrush(_colorref(color))
        self._proc = WNDPROC(self._wndproc)
        self._old = user32.SetWindowLongPtrW(ctypes.c_void_p(self.hwnd), -4, ctypes.cast(self._proc, ctypes.c_void_p))

    def _fill(self, hdc):
        r = wt.RECT()
        user32.GetClientRect(ctypes.c_void_p(self.hwnd), ctypes.byref(r))
        user32.FillRect(ctypes.c_void_p(hdc), ctypes.byref(r), ctypes.c_void_p(self.brush))

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == 0x0014:                             # WM_ERASEBKGND
            self._fill(wp)
            return 1
        if msg == 0x000F:                             # WM_PAINT
            ps = (ctypes.c_byte * 72)()               # PAINTSTRUCT
            hdc = user32.BeginPaint(ctypes.c_void_p(hwnd), ps)
            self._fill(hdc)
            user32.EndPaint(ctypes.c_void_p(hwnd), ps)
            return 0
        return user32.CallWindowProcW(self._old, hwnd, msg, wp, lp)

    def paint_now(self):
        """Закрасить немедленно, в этом же кадре (после растягивания). Чистый WinAPI."""
        user32.RedrawWindow(ctypes.c_void_p(self.hwnd), None, None, 0x0001 | 0x0004 | 0x0100)   # INVALIDATE|ERASE|UPDATENOW

    def release(self):
        try:
            if user32.IsWindow(ctypes.c_void_p(self.hwnd)):
                user32.SetWindowLongPtrW(ctypes.c_void_p(self.hwnd), -4, ctypes.c_void_p(self._old))
        finally:
            gdi32.DeleteObject(ctypes.c_void_p(self.brush))


def adopt(handle, parent_handle):
    """Сделать окно Tk ДОЧЕРНИМ окну parent (WS_CHILD | WS_EX_LAYERED, Windows 8+): DWM рисует его
    в одном дереве с родителем — при перетаскивании оно едет вместе с окном само, при растягивании
    обновляется в том же кадре (отдельные окна верхнего уровня отставали на кадр — полоса по краю).
    Координаты дочернего окна — в клиентской области родителя."""
    h, parent = _wrapper(handle), _wrapper(parent_handle)
    st = user32.GetWindowLongW(ctypes.c_void_p(h), -16)
    user32.SetWindowLongW(ctypes.c_void_p(h), -16, (st & ~0x80000000) | 0x40000000 | 0x04000000)  # -POPUP +CHILD +CLIPSIBLINGS
    user32.SetParent(ctypes.c_void_p(h), ctypes.c_void_p(parent))
    # слой — заново, уже у дочернего окна: прозрачность, выставленная ему верхнего уровня,
    # после переподчинения не действует (окно рисовалось сплошным)
    ex = user32.GetWindowLongW(ctypes.c_void_p(h), -20)
    user32.SetWindowLongW(ctypes.c_void_p(h), -20, ex & ~0x00080000)
    user32.SetWindowLongW(ctypes.c_void_p(h), -20, ex | 0x00080000)                             # LAYERED
    return h


def set_alpha(handle, alpha, key=None):
    """Общая прозрачность окна (и цвет-ключ — сквозные места)."""
    flags = 0x2 | (0x1 if key else 0)
    user32.SetLayeredWindowAttributes(ctypes.c_void_p(_wrapper(handle)), _colorref(key) if key else 0,
                                      int(round(255 * alpha)), flags)


def _colorref(color):
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return r | (g << 8) | (b << 16)


def place_children(items):
    """Расставить дочерние окна ОДНОЙ пачкой и поднять их над содержимым родителя в порядке
    списка (последнее — сверху). items: [(handle, x, y, w или None, h или None)] в координатах
    клиентской области родителя. Чистый WinAPI — можно из WndProc."""
    hdwp = user32.BeginDeferWindowPos(len(items))
    for handle, x, y, w, h in items:
        flags = 0x0010 | 0x0040 | (0x0001 if w is None else 0)            # NOACTIVATE | SHOWWINDOW
        hdwp = user32.DeferWindowPos(ctypes.c_void_p(hdwp), ctypes.c_void_p(_wrapper(handle)), None,
                                     int(x), int(y), int(w or 0), int(h or 0), flags)          # HWND_TOP
        if not hdwp:
            return False
    return bool(user32.EndDeferWindowPos(ctypes.c_void_p(hdwp)))


def screen_size():
    """Размер виртуального экрана (все мониторы) — больше любого окна программы."""
    return user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)


def widget_rect(widget):
    """Настоящее положение виджета на экране (x, y, w, h) — верно и внутри переподчинённого окна,
    где у Tk свои (неверные) экранные координаты."""
    r = wt.RECT()
    user32.GetWindowRect(ctypes.c_void_p(widget.winfo_id()), ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def move_many(items):
    """Переставить несколько окон Tk ОДНОЙ пачкой (DeferWindowPos): DWM покажет их новое
    положение в одном кадре — без «разъезжания». items: [(handle, x, y, w или None, h или None)].
    Чистый WinAPI — можно из WndProc."""
    hdwp = user32.BeginDeferWindowPos(len(items))
    for handle, x, y, w, h in items:
        flags = 0x0004 | 0x0010 | 0x0200 | (0x0001 if w is None else 0)   # NOZORDER|NOACTIVATE|NOOWNERZORDER
        hdwp = user32.DeferWindowPos(ctypes.c_void_p(hdwp), ctypes.c_void_p(_wrapper(handle)), None,
                                     int(x), int(y), int(w or 0), int(h or 0), flags)
        if not hdwp:
            return False
    return bool(user32.EndDeferWindowPos(ctypes.c_void_p(hdwp)))


class OverlayHost:
    """WinAPI для модального окна платформы (layouts.Modal): живое затемнение и следование
    за окном без отставания. Платформа не знает WinAPI — программа подключает этот объект.
    Окна Tk передаются как handle = winfo_id (не меняется, в отличие от внешнего окна)."""

    def __init__(self, frame_watch):
        self.watch = frame_watch

    @staticmethod
    def handle(win):
        win.update_idletasks()
        return win.winfo_id()

    @staticmethod
    def client_rect(handle):
        return client_rect(_wrapper(handle))

    own = staticmethod(lambda handle, owner, layered=False: _ensure(handle, owner, layered))
    show_layered = staticmethod(show_layered)
    move = staticmethod(move_window)
    move_many = staticmethod(move_many)
    adopt = staticmethod(adopt)
    set_alpha = staticmethod(set_alpha)
    place_children = staticmethod(place_children)
    solid = staticmethod(lambda handle, color: SolidFill(handle, color))
    screen_size = staticmethod(screen_size)

    def erase_with(self, color):
        self.watch.erase_with(color)

    def follow(self, f):
        self.watch.listeners.append(f)

    def unfollow(self, f):
        if f in self.watch.listeners:
            self.watch.listeners.remove(f)


user32.SetForegroundWindow.argtypes = [HANDLE]
user32.IsWindow.argtypes = [HANDLE]


def foreground():
    """Окно, которое сейчас активно (hwnd)."""
    return user32.GetForegroundWindow()


def set_foreground(hwnd):
    """Вернуть фокус окну hwnd (можно, пока наш процесс — активный)."""
    try:
        if hwnd and user32.IsWindow(hwnd):
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


# ---------------------------------------------------------------- одна копия программы
_instance_mutex = None


def single_instance(name):
    """True — это первая копия программы. Именованный мьютекс держится до конца процесса:
    вторая копия держала бы те же глобальные клавиши, и Windows отдавала бы нажатия ей."""
    global _instance_mutex
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = HANDLE
    _instance_mutex = k32.CreateMutexW(None, False, name)
    return ctypes.get_last_error() != 183          # ERROR_ALREADY_EXISTS


def show_existing(title, skip=()):
    """Показать окно уже запущенной копии (заголовок начинается с title; title — строка или кортеж
    вариантов: название программы на разных языках). False — окна не видно
    (свёрнутое разворачивается; скрытое — значит, идёт снимок или запись, его не трогаем).
    Копия со значком в трее показывает окно сама, даже спрятанное в трей (TrayIcon.ask_show)."""
    if TrayIcon.ask_show():
        return True
    found = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(h, _):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, buf, 256)
        if buf.value == "TkTopLevel":
            user32.GetWindowTextW(h, buf, 256)
            if buf.value.startswith(title) and not any(s in buf.value for s in skip):
                found.append(h)
        return True
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    for h in found:
        if user32.IsIconic(h):
            user32.ShowWindow(h, 9)                 # SW_RESTORE
        if user32.IsWindowVisible(h):
            user32.SetForegroundWindow(h)
            return True
    return False


def message_box(title, text):
    user32.MessageBoxW(None, text, title, 0x40)    # MB_ICONINFORMATION


# ---------------------------------------------------------------- значок в трее (B19)
# Свои сигнатуры на отдельной копии user32: argtypes общего user32 менять нельзя — на них
# рассчитан остальной код (SendMessageW и др. зовутся без объявлений).
_u32 = ctypes.WinDLL("user32", use_last_error=True)
_shell = ctypes.WinDLL("shell32")
_k32 = ctypes.WinDLL("kernel32")
_k32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
_k32.GetModuleHandleW.restype = wt.HMODULE
_u32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
_u32.DefWindowProcW.restype = LRESULT
_u32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD, ctypes.c_int, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
_u32.CreateWindowExW.restype = wt.HWND
_u32.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT]
_u32.LoadImageW.restype = wt.HANDLE
_u32.LoadIconW.argtypes = [wt.HINSTANCE, ctypes.c_void_p]
_u32.LoadIconW.restype = wt.HICON
_u32.DestroyIcon.argtypes = [wt.HICON]
_u32.CreatePopupMenu.restype = wt.HMENU
_u32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
_u32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, ctypes.c_void_p]
_u32.DestroyMenu.argtypes = [wt.HMENU]
_u32.SetForegroundWindow.argtypes = [wt.HWND]
_u32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
_u32.DestroyWindow.argtypes = [wt.HWND]
_u32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
_u32.FindWindowW.restype = wt.HWND
_u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
_u32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT,
                                     ctypes.POINTER(ctypes.c_size_t)]
_u32.SendMessageTimeoutW.restype = LRESULT
_u32.GetMessageW.argtypes = [ctypes.c_void_p, wt.HWND, wt.UINT, wt.UINT]
_u32.TranslateMessage.argtypes = [ctypes.c_void_p]
_u32.DispatchMessageW.argtypes = [ctypes.c_void_p]
_u32.DispatchMessageW.restype = LRESULT


class _WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE), ("hbrBackground", wt.HANDLE), ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]


class _NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("hWnd", wt.HWND), ("uID", wt.UINT), ("uFlags", wt.UINT),
                ("uCallbackMessage", wt.UINT), ("hIcon", wt.HICON), ("szTip", wt.WCHAR * 128),
                ("dwState", wt.DWORD), ("dwStateMask", wt.DWORD), ("szInfo", wt.WCHAR * 256),
                ("uVersion", wt.UINT), ("szInfoTitle", wt.WCHAR * 64), ("dwInfoFlags", wt.DWORD),
                ("guidItem", ctypes.c_byte * 16), ("hBalloonIcon", wt.HICON)]


_shell.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(_NOTIFYICONDATAW)]
_shell.Shell_NotifyIconW.restype = wt.BOOL

NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP = 1, 2, 4
WM_TRAY = 0x8000 + 10             # WM_APP+10: щелчки по значку (lParam — сообщение мыши)
WM_TRAY_SHOW = 0x8000 + 11        # от второй копии программы: «покажи окно» (ответ 1 — показано)
WM_CLOSE_MSG, WM_DESTROY_MSG, WM_ENDSESSION, WM_NULL = 0x0010, 0x0002, 0x0016, 0
WM_LBUTTONDBLCLK, WM_RBUTTONUP = 0x0203, 0x0205
TRAY_CLASS = "ScreenshoterXX.TrayWindow"
TRAY_TITLE = "ScreenshoterXX.Tray"          # тесты задают свой: вторая копия ищет окно по нему


class TrayIcon:
    """Значок программы в области уведомлений. Своё скрытое окно-владелец в ОТДЕЛЬНОМ потоке с
    очередью сообщений (как HotkeyService): оконная процедура не трогает Tk, а кладёт событие
    в queue ("show" — двойной клик или повторный запуск, "exit" — пункт меню «Выход») и будит
    главный поток notify().

    Ловушки: значок пропадает при перезапуске проводника — по сообщению TaskbarCreated (оно
    рассылается окнам верхнего уровня, поэтому окно не message-only) значок добавляется заново;
    при выходе, через меню и при завершении сеанса Windows — NIM_DELETE, иначе в трее остаётся
    «призрак» до наведения мыши. Меню — родное (TrackPopupMenu): перед показом окно-владелец
    делается активным, после — WM_NULL, иначе меню не закрывается кликом мимо."""

    _instances = {}               # hwnd -> TrayIcon: оконная процедура класса одна на процесс
    _proc = None
    _taskbar_created = 0

    def __init__(self, icon_path, tip, queue, notify=None, can_show=lambda: True, title=None):
        self.icon_path, self.tip, self.queue, self.notify = icon_path, tip, queue, notify
        self.can_show = can_show                  # чистый Python, без Tk: зовётся из потока значка
        self.title = title or TRAY_TITLE
        self.hwnd = None
        self.hicon = None
        self.added = False
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(2)
        import atexit
        atexit.register(self.close)              # окно закрыли не через quit (тесты) — без «призрака»

    # --- окно в своём потоке ---
    @classmethod
    def _register(cls, hinst):
        if cls._proc is not None:
            return
        cls._proc = WNDPROC(cls._dispatch)        # держим до конца процесса: класс окна его помнит
        wc = _WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(wc)
        wc.lpfnWndProc = cls._proc
        wc.hInstance = hinst
        wc.lpszClassName = TRAY_CLASS
        _u32.RegisterClassExW(ctypes.byref(wc))
        cls._taskbar_created = _u32.RegisterWindowMessageW("TaskbarCreated")

    @classmethod
    def _dispatch(cls, hwnd, msg, wp, lp):
        self = cls._instances.get(hwnd)
        if self is not None:
            try:
                res = self._wndproc(hwnd, msg, wp, lp)
                if res is not None:
                    return res
            except Exception:
                if FrameWatch.on_error:
                    FrameWatch.on_error(*sys.exc_info())
        return _u32.DefWindowProcW(hwnd, msg, wp, lp)

    def _run(self):
        hinst = _k32.GetModuleHandleW(None)
        TrayIcon._register(hinst)
        self.hwnd = _u32.CreateWindowExW(0, TRAY_CLASS, self.title, 0x80000000,   # WS_POPUP, не показывается
                                         0, 0, 0, 0, None, None, hinst, None)
        if not self.hwnd:
            self._ready.set()
            return
        TrayIcon._instances[self.hwnd] = self
        self._load_icon()
        self._add()
        self._ready.set()
        msg = wt.MSG()
        while _u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _u32.TranslateMessage(ctypes.byref(msg))
            _u32.DispatchMessageW(ctypes.byref(msg))
        TrayIcon._instances.pop(self.hwnd, None)
        if self.hicon:
            _u32.DestroyIcon(self.hicon)

    def _load_icon(self):
        size = user32.GetSystemMetrics(49)             # SM_CXSMICON (физические px: процесс DPI-aware)
        h = None
        if self.icon_path and os.path.exists(self.icon_path):
            h = _u32.LoadImageW(None, self.icon_path, 1, size, size, 0x10)   # IMAGE_ICON, LR_LOADFROMFILE
        self.hicon = h or None
        if not h:
            h = _u32.LoadIconW(None, ctypes.c_void_p(32512))                # IDI_APPLICATION
        self._icon = h

    def _nid(self, flags=0):
        nid = _NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = flags
        if flags:
            nid.uCallbackMessage = WM_TRAY
            nid.hIcon = self._icon
            nid.szTip = self.tip[:127]
        return nid

    def _add(self):
        self.added = bool(_shell.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid(NIF_MESSAGE | NIF_ICON | NIF_TIP))))

    def _delete(self):
        if self.hwnd:
            _shell.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid()))
        self.added = False

    def _post(self, event):
        self.queue.put(event)
        if self.notify:
            try:
                self.notify()
            except Exception:
                pass                  # главный поток подхватит из очереди по опросу

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == WM_TRAY:
            m = lp & 0xFFFF
            if m == WM_LBUTTONDBLCLK:
                self._post("show")
            elif m == WM_RBUTTONUP:
                self._menu()
            return 0
        if msg == WM_TRAY_SHOW:
            if not self.can_show():
                return 2                              # идёт снимок или запись
            self._post("show")
            return 1
        if msg == TrayIcon._taskbar_created and msg:  # проводник перезапущен — значок пропал
            self._add()
            return 0
        if msg == WM_ENDSESSION and wp:               # сеанс Windows завершается
            self._delete()
            return 0
        if msg == WM_CLOSE_MSG:
            self._delete()
            _u32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY_MSG:
            _u32.PostQuitMessage(0)
            return 0
        return None

    def _menu(self):
        """Родное меню Windows с единственным пунктом «Выход»."""
        m = _u32.CreatePopupMenu()
        _u32.AppendMenuW(m, 0, 1, tr("Выход"))            # MF_STRING
        pt = wt.POINT()
        _u32.GetCursorPos(ctypes.byref(pt))
        _u32.SetForegroundWindow(self.hwnd)           # без этого меню не закрывается кликом мимо
        cmd = _u32.TrackPopupMenu(m, 0x0100 | 0x0002 | 0x0080, pt.x, pt.y, 0, self.hwnd, None)
        _u32.PostMessageW(self.hwnd, WM_NULL, 0, 0)   # TPM_RETURNCMD|TPM_RIGHTBUTTON|TPM_NONOTIFY
        _u32.DestroyMenu(m)
        if cmd == 1:
            self._post("exit")

    # --- из главного потока ---
    def visible(self):
        """Значок действительно есть в трее — спрашиваем проводник, а не верим флагу: NIM_MODIFY
        удаётся только для существующего значка. (Shell_NotifyIconGetRect не годится: для значка,
        убранного Windows под стрелку «^», он возвращает ошибку, хотя значок есть.)"""
        return bool(self.hwnd) and bool(_shell.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(
            self._nid(NIF_MESSAGE | NIF_ICON | NIF_TIP))))

    def close(self):
        """Убрать значок (NIM_DELETE — сразу, из любого потока) и закрыть окно-владелец."""
        if not self.hwnd:
            return
        self._delete()
        _u32.PostMessageW(self.hwnd, WM_CLOSE_MSG, 0, 0)
        self._thread.join(2)
        self.hwnd = None

    @staticmethod
    def ask_show(title=None):
        """Вторая копия программы: попросить первую показать окно (в т. ч. спрятанное в трей).
        True — показано; False — значка нет (трей выключен) или идёт снимок/запись."""
        h = _u32.FindWindowW(TRAY_CLASS, title or TRAY_TITLE)
        if not h:
            return False
        pid = wt.DWORD()
        _u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        user32.AllowSetForegroundWindow(pid.value)    # фокус сейчас у нас — отдать его первой копии
        res = ctypes.c_size_t()
        ok = _u32.SendMessageTimeoutW(h, WM_TRAY_SHOW, 0, 0, 0x0002, 3000, ctypes.byref(res))  # SMTO_ABORTIFHUNG
        return bool(ok) and res.value == 1


# ---------------------------------------------------------------- автозапуск (B19)
# HKCU\…\Run: только для текущего пользователя, без прав администратора. Тесты подменяют RUN_KEY
# на временный ключ — в настоящий автозапуск пользователя тесты не пишут.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "ScreenshoterXX"


def autostart_get():
    """Команда автозапуска программы или None."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, RUN_NAME)[0]
    except OSError:
        return None


def autostart_set(command):
    import winreg
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, command)
        return True
    except OSError:
        return False


def autostart_remove():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, RUN_NAME)
    except OSError:
        pass


def open_in_explorer(path):
    try:
        if os.path.isdir(path):
            os.startfile(path)
        else:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    except Exception:
        pass


def open_file(path):
    try:
        os.startfile(path)
    except Exception:
        pass


# ---------------------------------------------------------------- горячие клавиши
MOD = {"Alt": 0x1, "Ctrl": 0x2, "Shift": 0x4}
MOD_NOREPEAT = 0x4000
VK_NAMED = {"Print": 0x2C, "Pause": 0x13, "Scroll_Lock": 0x91, "space": 0x20, "Insert": 0x2D,
            "Home": 0x24, "End": 0x23, "Prior": 0x21, "Next": 0x22}
WM_HOTKEY = 0x0312
WM_APP_RELOAD = 0x8001


def parse_hotkey(text):
    """"Ctrl+Alt+S" -> (mods, vk) или None."""
    if not text:
        return None
    parts = text.split("+")
    mods = 0
    for p in parts[:-1]:
        if p not in MOD:
            return None
        mods |= MOD[p]
    key = parts[-1]
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x6F + int(key[1:])
    elif key in VK_NAMED:
        vk = VK_NAMED[key]
    else:
        return None
    return mods, vk


class HotkeyService:
    """Глобальные горячие клавиши в отдельном потоке с очередью сообщений.
    bindings: {id: "Ctrl+Alt+S"}. События кладутся в queue как id."""

    def __init__(self, queue, notify=None):
        self.queue = queue
        self.notify = notify          # будит главный поток сразу (без ожидания опроса)
        self.bindings = {}
        self.status = {}
        self.paused = False
        self.tid = None
        self._ready = threading.Event()
        self._sent = self._done = 0               # номера заказанных и применённых перерегистраций
        self._applied = threading.Condition()
        threading.Thread(target=self._run, daemon=True).start()
        self._ready.wait(2)

    def update(self, bindings, wait=False):
        """Новые сочетания. wait=True — дождаться регистрации (до 1 с) и вернуть status."""
        self.bindings = dict(bindings)
        n = self._poke()
        if wait and n:
            with self._applied:
                self._applied.wait_for(lambda: self._done >= n, 1)
        return dict(self.status)

    def pause(self, paused):
        """Временно снять все клавиши (например, пока пользователь вводит новое сочетание)."""
        self.paused = paused
        self._poke()

    def _poke(self):
        if not self.tid:
            return 0
        with self._applied:
            self._sent += 1
            n = self._sent
        user32.PostThreadMessageW(self.tid, WM_APP_RELOAD, n, 0)
        return n

    def _apply(self, ids):
        for i in list(ids):
            user32.UnregisterHotKey(None, i)
        ids.clear()
        self.status = {}
        if self.paused:
            return
        for n, (name, text) in enumerate(sorted(self.bindings.items()), start=1):
            hk = parse_hotkey(text)
            ok = False
            if hk:
                ok = bool(user32.RegisterHotKey(None, n, hk[0] | MOD_NOREPEAT, hk[1]))
                if ok:
                    ids[n] = name
            self.status[name] = ok or not text

    def _run(self):
        self.tid = kernel32.GetCurrentThreadId()
        msg = wt.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # создать очередь сообщений
        ids = {}
        self._ready.set()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_APP_RELOAD:
                self._apply(ids)
                with self._applied:
                    self._done = max(self._done, int(msg.wParam))
                    self._applied.notify_all()
            elif msg.message == WM_HOTKEY and int(msg.wParam) in ids:
                self.queue.put(ids[int(msg.wParam)])
                if self.notify:
                    try:
                        self.notify()
                    except Exception:
                        pass              # главный поток подхватит из очереди по опросу
