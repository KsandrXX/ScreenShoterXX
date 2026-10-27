# -*- coding: utf-8 -*-
"""
Отрисовка поверх токенов: сглаженные скруглённые фигуры, «стекло», контраст.

Tk не умеет полупрозрачность отдельных виджетов и сглаживание, поэтому формы
рисуются через Pillow с суперсэмплингом и заранее смешиваются с цветом фона
родителя. Результаты кэшируются.
"""

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk

from .tokens import EXTREMES

SUPERSAMPLE = 4
_cache = {}


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb[:3])


def mix(top, bottom, alpha):
    """Цвет top с непрозрачностью alpha поверх bottom (hex -> hex)."""
    a, b = hex_rgb(top), hex_rgb(bottom)
    return rgb_hex([a[i] * alpha + b[i] * (1 - alpha) for i in range(3)])


def luminance(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in hex_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def rounded(w, h, radius, fill, bg, border=None, border_w=0, ring=None, ring_w=0, ring_gap=0):
    """Скруглённый прямоугольник w×h на фоне bg (всё hex). ring — внешнее кольцо фокуса,
    рисуется внутри тех же w×h, сама фигура тогда уменьшается на ring_w + ring_gap."""
    key = ("r", w, h, radius, fill, bg, border, border_w, ring, ring_w, ring_gap)
    if key in _cache:
        return _cache[key]
    s = SUPERSAMPLE
    img = Image.new("RGB", (max(1, w * s), max(1, h * s)), hex_rgb(bg))
    d = ImageDraw.Draw(img)
    inset = 0
    if ring and ring_w:
        d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=(radius + ring_w + ring_gap) * s,
                            outline=hex_rgb(ring), width=ring_w * s)
        inset = (ring_w + ring_gap) * s
    box = (inset, inset, w * s - 1 - inset, h * s - 1 - inset)
    if box[2] > box[0] and box[3] > box[1]:
        d.rounded_rectangle(box, radius=radius * s, fill=hex_rgb(fill),
                            outline=hex_rgb(border) if border and border_w else None,
                            width=border_w * s if border and border_w else 0)
    img = img.resize((max(1, w), max(1, h)), Image.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    _cache[key] = photo
    return photo


def circle(d, fill, bg, border=None, border_w=0):
    key = ("c", d, fill, bg, border, border_w)
    if key in _cache:
        return _cache[key]
    s = SUPERSAMPLE
    img = Image.new("RGB", (d * s, d * s), hex_rgb(bg))
    ImageDraw.Draw(img).ellipse((0, 0, d * s - 1, d * s - 1), fill=hex_rgb(fill),
                                outline=hex_rgb(border) if border else None,
                                width=border_w * s if border else 0)
    photo = ImageTk.PhotoImage(img.resize((d, d), Image.LANCZOS))
    _cache[key] = photo
    return photo


def glass(background, box, tint, fill_alpha, border, border_alpha, radius, blur):
    """Настоящее стекло: кусок известного фона (PIL RGB) размывается, тонируется,
    получает тонкую границу и скругление. Возвращает (PIL RGBA, контраст-худший цвет)."""
    l, t, r, b = [int(v) for v in box]
    w, h = max(1, r - l), max(1, b - t)
    region = background.crop((l, t, r, b)).convert("RGB")
    if blur:
        region = region.filter(ImageFilter.GaussianBlur(blur))
    tinted = Image.blend(region, Image.new("RGB", (w, h), hex_rgb(tint)), fill_alpha)
    s = SUPERSAMPLE
    mask = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=radius * s,
                                           fill=255)
    mask = mask.resize((w, h), Image.LANCZOS)
    edge = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(edge).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=radius * s,
                                           outline=255, width=s)
    edge = edge.resize((w, h), Image.LANCZOS).point(lambda v: int(v * border_alpha))
    out = Image.composite(Image.new("RGB", (w, h), hex_rgb(border)), tinted, edge)
    out = out.convert("RGBA")
    out.putalpha(mask)
    return out


def rounded_rgba(w, h, radius, fill, border=None, border_w=0):
    """Скруглённый прямоугольник с ПРОЗРАЧНЫМИ углами (PhotoImage RGBA) — кладётся на любой фон
    холста, например на стекло."""
    key = ("ra", w, h, radius, fill, border, border_w)
    if key in _cache:
        return _cache[key]
    s = SUPERSAMPLE
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        (0, 0, w * s - 1, h * s - 1), radius=radius * s, fill=hex_rgb(fill) + (255,),
        outline=hex_rgb(border) + (255,) if border and border_w else None, width=border_w * s if border else 0)
    photo = ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS))
    _cache[key] = photo
    return photo


def rounded_hard(w, h, radius, fill, key, border=None, border_w=0):
    """Скруглённый прямоугольник БЕЗ сглаживания на цвете-ключе key (снаружи — ровно key):
    для окна с прозрачным цветом-ключом. Сглаженный край даёт окно тени под ним (modal_shadow)."""
    k = ("rh", w, h, radius, fill, key, border, border_w)
    if k in _cache:
        return _cache[k]
    img = Image.new("RGB", (w, h), hex_rgb(key))
    ImageDraw.Draw(img).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=hex_rgb(fill),
                                          outline=hex_rgb(border) if border and border_w else None,
                                          width=border_w if border else 0)
    photo = ImageTk.PhotoImage(img)
    _cache[k] = photo
    return photo


def line_sample(w, h, cell, c1, c2, border, line_w, color, alpha, pad):
    """Образец линии (подсказка размера): шахматный фон из клеток cell (c1/c2), рамка 1 px
    border, по центру — линия толщиной line_w цвета color с непрозрачностью alpha (0…1),
    с круглыми концами, отступ от краёв pad."""
    k = ("ls", w, h, cell, c1, c2, border, line_w, color, alpha, pad)
    if k in _cache:
        return _cache[k]
    img = Image.new("RGB", (w, h), hex_rgb(c1))
    d = ImageDraw.Draw(img)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2:
                d.rectangle((x, y, x + cell - 1, y + cell - 1), fill=hex_rgb(c2))
    s = SUPERSAMPLE
    mask = Image.new("L", (w * s, h * s), 0)
    r = line_w * s / 2
    cy = h * s / 2
    ImageDraw.Draw(mask).rounded_rectangle((pad * s, cy - r, (w - pad) * s, cy + r), radius=r,
                                           fill=int(round(255 * alpha)))
    mask = mask.resize((w, h), Image.LANCZOS)
    img = Image.composite(Image.new("RGB", (w, h), hex_rgb(color)), img, mask)
    ImageDraw.Draw(img).rectangle((0, 0, w - 1, h - 1), outline=hex_rgb(border))
    photo = ImageTk.PhotoImage(img)
    _cache[k] = photo
    return photo


_shadow_cache = {}


def modal_shadow(cw, ch, radius, shadow, card, card_alpha):
    """Окно тени модальной карточки cw × ch (RGBA) и поле m вокруг неё: мягкая тень
    (shadow = {"blur", "offset", "alpha"}) и сглаженный край карточки (card × card_alpha там, где
    окно карточки со своим жёстким краем уже не рисует). Внутри карточки — прозрачно (страница
    видна сквозь полупрозрачную карточку). Зависит только от размера — рисуется один раз, при
    перетаскивании и растягивании окна только переезжает."""
    m = shadow["blur"] * 2 + shadow["offset"]
    key = (cw, ch, radius, shadow["blur"], shadow["offset"], shadow["alpha"], card, card_alpha)
    if key in _shadow_cache:
        return _shadow_cache[key], m
    pw, ph = cw + 2 * m, ch + 2 * m
    s = SUPERSAMPLE
    cov = Image.new("L", (cw * s, ch * s), 0)
    ImageDraw.Draw(cov).rounded_rectangle((0, 0, cw * s - 1, ch * s - 1), radius=radius * s, fill=255)
    cov = cov.resize((cw, ch), Image.LANCZOS)                     # сглаженное покрытие
    hard = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(hard).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=radius, fill=255)
    inside = Image.new("L", (pw, ph), 0)
    inside.paste(hard, (m, m))
    sh = Image.new("L", (pw, ph), 0)
    sh.paste(cov, (m, m + shadow["offset"]))
    sh = sh.filter(ImageFilter.GaussianBlur(shadow["blur"])).point(lambda v: int(v * shadow["alpha"]))
    sh = ImageChops.subtract(sh, inside)                             # тень — только снаружи карточки
    black = Image.new("L", (pw, ph), 0)
    out = Image.merge("RGBA", (black, black, black, sh))
    skirt = ImageChops.subtract(cov, hard).point(lambda v: int(v * card_alpha))
    edge = Image.new("L", (pw, ph), 0)
    edge.paste(skirt, (m, m))
    c = Image.new("RGBA", (pw, ph), hex_rgb(card) + (0,))
    c.putalpha(edge)
    out = Image.alpha_composite(out, c)
    if len(_shadow_cache) > 8:
        _shadow_cache.clear()
    _shadow_cache[key] = out
    return out, m


def modal_text_pairs(fg, card, card_alpha, scrim, scrim_alpha, pages):
    """(текст, фон) на полупрозрачной карточке над затемнённой страницей — для проверки
    контраста. Окно карточки целиком полупрозрачно: и текст, и фон смешаны с тем, что под ним."""
    out = []
    for page in pages:
        under = mix(scrim, page, scrim_alpha)
        out.append((mix(fg, under, card_alpha), mix(card, under, card_alpha)))
    return out


def glass_worst_bg(tint, fill_alpha):
    """Самый неблагоприятный фон под стеклом: противоположный тонировке крайний цвет."""
    lum = luminance(tint)
    worst = EXTREMES["white"] if lum < 0.5 else EXTREMES["black"]
    return mix(tint, worst, fill_alpha)
