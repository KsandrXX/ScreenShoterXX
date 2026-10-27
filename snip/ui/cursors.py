# -*- coding: utf-8 -*-
"""
Курсоры инструментов из реестра иконок.

Как у обычного курсора: «горячая точка» (место нажатия) — в левом верхнем
углу, значок уходит вправо-вниз от неё. Иконки пера/маркера в реестре нарисованы
острием вниз-влево, поэтому для курсора они отражаются по вертикали, и острие
оказывается сверху-слева. Курсор рисуется сразу в системном размере
(SM_CXCURSOR: 32 px при 100 %, 40 при 125 %, 48 при 150 %) — Windows не растягивает
его, и горячая точка совпадает с острием пиксель в пиксель.

Tk принимает курсор из файла: cursor="@путь.cur".
"""

import ctypes
import io
import os
import struct
import tempfile

from PIL import Image, ImageFilter

from .icons import GRID, pil_icon
from .paint import hex_rgb
from .tokens import CURSOR

# имя курсора -> иконка (рисуется острием вниз-влево; для курсора отражается по вертикали)
SHAPES = {"pen": "pen", "marker": "marker_body"}

_cache = {}
_DIR = os.path.join(tempfile.gettempdir(), "snipxx_cursors")


def system_cursor_px():
    try:
        return max(16, ctypes.windll.user32.GetSystemMetrics(13))   # SM_CXCURSOR
    except Exception:
        return 32


def _tip(ink):
    """Самый крайний сверху-слева пиксель «туши» — видимое острие, туда и ставим горячую точку."""
    a = ink.getchannel("A")
    w, h = ink.size
    best = None
    for y in range(h):
        for x in range(w):
            if a.getpixel((x, y)) >= 128 and (best is None or x + y < best[0] + best[1]):
                best = (x, y)
    return best or (0, 0)


def render(name, px):
    """PIL-изображение курсора и его горячая точка (x, y) в пикселях."""
    ink = pil_icon(SHAPES[name], px, CURSOR["ink"]).transpose(Image.FLIP_TOP_BOTTOM)
    s = px / GRID
    hx, hy = _tip(ink)
    # белая обводка, чтобы курсор был виден на любом фоне
    halo_w = max(3, int(round(CURSOR["halo"] * s)) * 2 + 1)
    alpha = ink.getchannel("A").filter(ImageFilter.MaxFilter(halo_w))
    out = Image.new("RGBA", (px, px), hex_rgb(CURSOR["halo_color"]) + (0,))
    out.putalpha(alpha)
    out.alpha_composite(ink)
    return out, (hx, hy)


def _write_cur(img, hotspot, path):
    """ICO -> CUR: тип 2, а в полях planes/bitcount записи — горячая точка."""
    buf = io.BytesIO()
    img.save(buf, "ICO", sizes=[img.size])
    data = bytearray(buf.getvalue())
    struct.pack_into("<H", data, 2, 2)                     # тип ресурса: курсор
    struct.pack_into("<HH", data, 6 + 4, hotspot[0], hotspot[1])
    with open(path, "wb") as f:
        f.write(bytes(data))


def cursor(name, px=None):
    """Строка курсора для Tk ("@путь.cur") или стандартный курсор, если что-то пошло не так."""
    px = px or system_cursor_px()
    key = (name, px)
    if key not in _cache:
        try:
            os.makedirs(_DIR, exist_ok=True)
            img, hot = render(name, px)
            path = os.path.join(_DIR, f"{name}_{px}.cur")
            _write_cur(img, hot, path)
            _cache[key] = "@" + path.replace("\\", "/")
        except Exception:
            _cache[key] = "pencil"
    return _cache[key]
