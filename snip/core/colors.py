# -*- coding: utf-8 -*-
"""Цветовая математика для палитры: HEX, Lab, CMYK."""


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return "#%02x%02x%02x" % (int(r), int(g), int(b))


def rgb_to_lab(r, g, b):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    R, G, B = lin(r), lin(g), lin(b)
    X = (R * 0.4124 + G * 0.3576 + B * 0.1805) / 0.95047
    Y = R * 0.2126 + G * 0.7152 + B * 0.0722
    Z = (R * 0.0193 + G * 0.1192 + B * 0.9505) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(X), f(Y), f(Z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def lab_to_rgb(L, a, b):
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200

    def finv(t):
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787
    X, Y, Z = finv(fx) * 0.95047, finv(fy), finv(fz) * 1.08883
    R = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    G = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    B = 0.0557 * X - 0.2040 * Y + 1.0570 * Z

    def gam(c):
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return tuple(round(gam(c) * 255) for c in (R, G, B))


def rgb_to_cmyk(r, g, b):
    r, g, b = r / 255, g / 255, b / 255
    k = 1 - max(r, g, b)
    if k >= 1:
        return 0, 0, 0, 100
    return tuple(round(v * 100) for v in ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k),
                                         (1 - b - k) / (1 - k), k))


def cmyk_to_rgb(c, m, y, k):
    c, m, y, k = c / 100, m / 100, y / 100, k / 100
    return tuple(round(255 * (1 - v) * (1 - k)) for v in (c, m, y))
