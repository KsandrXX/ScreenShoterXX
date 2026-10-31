# -*- coding: utf-8 -*-
"""Захват экрана через DXGI Desktop Duplication (B38): кадры полноэкранных игр для записи GIF.

GDI (`winapi.grab`, BitBlt) не видит то, что игра выводит напрямую через видеокарту в обход
рабочего стола: кадр обновляется раз в десятки секунд («гифка в 0,02 fps»). Desktop Duplication
отдаёт кадры самого композитора. Только ctypes, без новых библиотек; COM — по номерам в таблице
методов (порядок методов в заголовках Windows SDK).

Ограничения — область целиком на одном мониторе, монитор без поворота, Windows 8+. Иначе
`Duplicator(...)` бросает DxgiError, и запись идёт через GDI (`GifCapture`). Весь объект живёт в
одном потоке (потоке записи). Курсор Desktop Duplication не снимает: он рисуется поверх кадра.
"""

import ctypes
import ctypes.wintypes as wt
import time

from PIL import Image

from .winapi import BITMAPINFOHEADER, _draw_cursor, gdi32

WAIT_TIMEOUT = 0x887A0027 - (1 << 32)           # за это время нового кадра не было — это не ошибка
FORMAT_BGRA = 87                                # DXGI_FORMAT_B8G8R8A8_UNORM
USAGE_STAGING, CPU_READ, MAP_READ = 3, 0x20000, 1
ROTATION_IDENTITY = 1
DRIVER_UNKNOWN = 0
SDK_VERSION = 7
FIRST_FRAME_MS = 500                            # первый кадр отдаётся сразу; запас на медленный старт


class DxgiError(Exception):
    """Захват недоступен или потерян (смена режима экрана, UAC): запись перейдёт на GDI."""


class GUID(ctypes.Structure):
    _fields_ = [("a", ctypes.c_ulong), ("b", ctypes.c_ushort), ("c", ctypes.c_ushort), ("d", ctypes.c_ubyte * 8)]


def _guid(a, b, c, d):
    return GUID(a, b, c, (ctypes.c_ubyte * 8)(*bytes.fromhex(d)))


IID_FACTORY1 = _guid(0x770aae78, 0xf26f, 0x4dba, "a829253c83d1b387")
IID_OUTPUT1 = _guid(0x00cddea8, 0x939b, 0x4b83, "a340a685226666cc")
IID_TEXTURE2D = _guid(0x6f15aaf2, 0xd208, 0x4e89, "9ab4489535d34f9c")


class OUTPUT_DESC(ctypes.Structure):
    _fields_ = [("DeviceName", wt.WCHAR * 32), ("Desktop", wt.RECT), ("Attached", wt.BOOL),
                ("Rotation", wt.UINT), ("Monitor", ctypes.c_void_p)]


class FRAME_INFO(ctypes.Structure):
    _fields_ = [("LastPresentTime", ctypes.c_longlong), ("LastMouseUpdateTime", ctypes.c_longlong),
                ("AccumulatedFrames", wt.UINT), ("RectsCoalesced", wt.BOOL), ("Protected", wt.BOOL),
                ("PointerX", wt.LONG), ("PointerY", wt.LONG), ("PointerVisible", wt.BOOL),
                ("TotalMetadataBufferSize", wt.UINT), ("PointerShapeBufferSize", wt.UINT)]


class TEXTURE2D_DESC(ctypes.Structure):
    _fields_ = [("Width", wt.UINT), ("Height", wt.UINT), ("MipLevels", wt.UINT), ("ArraySize", wt.UINT),
                ("Format", wt.UINT), ("SampleCount", wt.UINT), ("SampleQuality", wt.UINT), ("Usage", wt.UINT),
                ("BindFlags", wt.UINT), ("CPUAccessFlags", wt.UINT), ("MiscFlags", wt.UINT)]


class MAPPED(ctypes.Structure):
    _fields_ = [("pData", ctypes.c_void_p), ("RowPitch", wt.UINT), ("DepthPitch", wt.UINT)]


class BOX(ctypes.Structure):
    _fields_ = [("left", wt.UINT), ("top", wt.UINT), ("front", wt.UINT),
                ("right", wt.UINT), ("bottom", wt.UINT), ("back", wt.UINT)]


def _com(ptr, index, restype, *argtypes):
    """Метод COM-объекта ptr по номеру в таблице методов."""
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[index])


def _hr(ptr, index, *args, argtypes=()):
    """Вызов метода, возвращающего HRESULT (число; ctypes.HRESULT бросал бы исключение)."""
    return _com(ptr, index, ctypes.c_long, *argtypes)(ptr, *args)


def _release(ptr):
    if ptr:
        _com(ptr, 2, wt.ULONG)(ptr)


def _check(hr, what):
    if hr < 0:
        raise DxgiError(f"{what}: 0x{hr & 0xFFFFFFFF:08X}")


def _find_output(x, y, w, h):
    """(адаптер, выход) с областью целиком на этом мониторе; ссылки — вызывающему."""
    try:
        create = ctypes.WinDLL("dxgi").CreateDXGIFactory1
    except (OSError, AttributeError) as ex:
        raise DxgiError(str(ex))
    create.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    create.restype = ctypes.c_long
    factory = ctypes.c_void_p()
    _check(create(ctypes.byref(IID_FACTORY1), ctypes.byref(factory)), "CreateDXGIFactory1")
    try:
        ai = 0
        while True:
            adapter = ctypes.c_void_p()
            if _hr(factory, 12, ai, ctypes.byref(adapter),            # IDXGIFactory1::EnumAdapters1
                   argtypes=(wt.UINT, ctypes.POINTER(ctypes.c_void_p))) < 0:
                raise DxgiError("область не на одном мониторе")
            oi = 0
            while True:
                output = ctypes.c_void_p()
                if _hr(adapter, 7, oi, ctypes.byref(output),          # IDXGIAdapter::EnumOutputs
                       argtypes=(wt.UINT, ctypes.POINTER(ctypes.c_void_p))) < 0:
                    break
                d = OUTPUT_DESC()
                hr = _hr(output, 7, ctypes.byref(d), argtypes=(ctypes.POINTER(OUTPUT_DESC),))   # GetDesc
                r = d.Desktop
                if hr >= 0 and d.Attached and r.left <= x and r.top <= y and x + w <= r.right and y + h <= r.bottom:
                    if d.Rotation not in (0, ROTATION_IDENTITY):
                        _release(output)
                        _release(adapter)
                        raise DxgiError("монитор повёрнут")
                    return adapter, output, (r.left, r.top)
                _release(output)
                oi += 1
            _release(adapter)
            ai += 1
    finally:
        _release(factory)


class Duplicator:
    """Кадры прямоугольника экрана (абсолютные координаты) как PIL.Image RGB."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = int(x), int(y), max(1, int(w)), max(1, int(h))
        self.device = self.context = self.dup = self.staging = None
        self.mdc = self.bmp = self.old = self.bits = None
        self.have_frame = False
        adapter, output, origin = _find_output(self.x, self.y, self.w, self.h)
        self.box = BOX(self.x - origin[0], self.y - origin[1], 0,
                       self.x - origin[0] + self.w, self.y - origin[1] + self.h, 1)
        try:
            self._open(adapter, output)
        except Exception:
            self.close()
            raise
        finally:
            _release(output)
            _release(adapter)

    def _open(self, adapter, output):
        try:
            create = ctypes.WinDLL("d3d11").D3D11CreateDevice
        except (OSError, AttributeError) as ex:
            raise DxgiError(str(ex))
        create.restype = ctypes.c_long
        create.argtypes = [ctypes.c_void_p, wt.UINT, ctypes.c_void_p, wt.UINT, ctypes.c_void_p, wt.UINT, wt.UINT,
                           ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        device, context = ctypes.c_void_p(), ctypes.c_void_p()
        # устройство — на том адаптере, к которому подключён монитор (ноутбуки с двумя видеокартами)
        _check(create(adapter, DRIVER_UNKNOWN, None, 0, None, 0, SDK_VERSION, ctypes.byref(device), None,
                      ctypes.byref(context)), "D3D11CreateDevice")
        self.device, self.context = device, context
        out1 = ctypes.c_void_p()
        _check(_hr(output, 0, ctypes.byref(IID_OUTPUT1), ctypes.byref(out1),
                   argtypes=(ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))), "IDXGIOutput1")
        try:
            dup = ctypes.c_void_p()
            _check(_hr(out1, 22, device, ctypes.byref(dup),           # IDXGIOutput1::DuplicateOutput
                       argtypes=(ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))), "DuplicateOutput")
            self.dup = dup
        finally:
            _release(out1)
        desc = TEXTURE2D_DESC(self.w, self.h, 1, 1, FORMAT_BGRA, 1, 0, USAGE_STAGING, 0, CPU_READ, 0)
        tex = ctypes.c_void_p()
        _check(_hr(device, 5, ctypes.byref(desc), None, ctypes.byref(tex),   # ID3D11Device::CreateTexture2D
                   argtypes=(ctypes.POINTER(TEXTURE2D_DESC), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))),
               "CreateTexture2D")
        self.staging = tex
        # DIB: кадр копируется сюда, поверх — курсор тем же кодом, что у GDI (_draw_cursor)
        bi = BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount, bi.biCompression = self.w, -self.h, 1, 32, 0
        self.mdc = gdi32.CreateCompatibleDC(None)
        bits = ctypes.c_void_p()
        self.bmp = gdi32.CreateDIBSection(self.mdc, ctypes.byref(bi), 0, ctypes.byref(bits), None, 0)
        if not self.bmp or not bits:
            raise DxgiError("CreateDIBSection")
        self.bits = bits
        self.old = gdi32.SelectObject(self.mdc, self.bmp)

    def _acquire(self, timeout_ms):
        """Взять новый кадр в staging-текстуру. Нового нет — там остаётся прежний."""
        info, res = FRAME_INFO(), ctypes.c_void_p()
        hr = _hr(self.dup, 8, timeout_ms, ctypes.byref(info), ctypes.byref(res),   # AcquireNextFrame
                 argtypes=(wt.UINT, ctypes.POINTER(FRAME_INFO), ctypes.POINTER(ctypes.c_void_p)))
        if hr == WAIT_TIMEOUT:
            return
        _check(hr, "AcquireNextFrame")               # ACCESS_LOST: смена режима экрана, UAC
        tex = ctypes.c_void_p()
        try:
            if not info.LastPresentTime:             # двинулась только мышь: картинки нет, текстура чёрная
                return
            _check(_hr(res, 0, ctypes.byref(IID_TEXTURE2D), ctypes.byref(tex),
                       argtypes=(ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))), "ID3D11Texture2D")
            _com(self.context, 46, None, ctypes.c_void_p, wt.UINT, wt.UINT, wt.UINT, wt.UINT,   # CopySubresourceRegion
                 ctypes.c_void_p, wt.UINT, ctypes.POINTER(BOX))(
                self.context, self.staging, 0, 0, 0, 0, tex, 0, ctypes.byref(self.box))
            self.have_frame = True
        finally:
            _release(tex)
            _release(res)
            _hr(self.dup, 14)                        # ReleaseFrame

    def grab(self, cursor=False, wait_ms=0):
        """Кадр сейчас. wait_ms — сколько ждать нового; нет нового — повтор прежнего (картинка не менялась)."""
        self._acquire(wait_ms)
        deadline = time.perf_counter() + FIRST_FRAME_MS / 1000
        while not self.have_frame:                   # первое событие Windows — обычно только мышь
            if time.perf_counter() > deadline:
                raise DxgiError("нет первого кадра")
            self._acquire(20)
        m = MAPPED()
        _check(_hr(self.context, 14, self.staging, 0, MAP_READ, 0, ctypes.byref(m),    # ID3D11DeviceContext::Map
                   argtypes=(ctypes.c_void_p, wt.UINT, wt.UINT, wt.UINT, ctypes.POINTER(MAPPED))), "Map")
        try:
            row = self.w * 4
            for i in range(self.h):
                ctypes.memmove(self.bits.value + i * row, m.pData + i * m.RowPitch, row)
        finally:
            _com(self.context, 15, None, ctypes.c_void_p, wt.UINT)(self.context, self.staging, 0)   # Unmap
        if cursor:
            gdi32.GdiFlush()
            _draw_cursor(self.mdc, self.x, self.y)
            gdi32.GdiFlush()
        data = ctypes.string_at(self.bits.value, self.w * self.h * 4)
        return Image.frombytes("RGB", (self.w, self.h), data, "raw", "BGRX")

    def close(self):
        if self.old:
            gdi32.SelectObject(self.mdc, self.old)
        if self.bmp:
            gdi32.DeleteObject(self.bmp)
        if self.mdc:
            gdi32.DeleteDC(self.mdc)
        for p in (self.staging, self.dup, self.context, self.device):
            _release(p)
        self.device = self.context = self.dup = self.staging = None
        self.mdc = self.bmp = self.old = self.bits = None
