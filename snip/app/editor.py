# -*- coding: utf-8 -*-
"""Редактор снимка: модель (штрихи, история) отдельно от вида (холст).

Координаты штрихов — в пикселях снимка; штрихи могут выходить за его края.
Вид: колесо — масштаб вокруг курсора, правая кнопка — перетаскивание
рабочего пространства, стрелки — сдвиг."""

import math
import tkinter as tk

from PIL import Image, ImageChops, ImageDraw, ImageTk

from ..core.colors import hex_to_rgb
from ..ui.cursors import cursor
from ..ui.tokens import ANNOTATION


def crop(img, box):
    """img.crop без проверки PIL «бомба распаковки» (вырезка больше ~179 Мп — ошибка): картинки
    редактора свои, а после штриха далеко за краем видимая часть бывает больше."""
    lim, Image.MAX_IMAGE_PIXELS = Image.MAX_IMAGE_PIXELS, None
    try:
        return img.crop(box)
    finally:
        Image.MAX_IMAGE_PIXELS = lim


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


class EditorModel:
    """Состояние снимка. Живёт дольше виджетов (переживает смену темы/масштаба)."""

    def __init__(self, settings):
        self.settings = settings
        self.base = None
        self.strokes, self.history = [], []
        self.redo_stack = []      # отменённые действия; новое действие очищает
        self.saved = True
        self.tool = "pen"
        self.version = 0          # растёт при каждом изменении — для кэша отрисовки
        # Кэши слоя пометок и готовой картинки. После правки пересобирается только прямоугольник
        # изменённого штриха (_dirty_*: список прямоугольников; None — всё заново). Иначе после
        # штриха далеко за краем (картинка 100+ Мп) каждое нажатие, отпускание и отмена стоили
        # секунды (B13).
        self.drop_caches()

    def drop_caches(self):
        self._layer_cache = self._layer_key = self._comp_cache = self._comp_key = None
        self._dirty_layer = self._dirty_comp = None

    @property
    def pen_color(self):
        return self.settings["pen_color"]

    @property
    def marker_color(self):
        return self.settings["marker_color"]

    # Свои размер и прозрачность у каждого инструмента: ключи настроек. Нет ключа — у
    # инструмента нет такого параметра (поле на панели неактивно).
    PARAMS = {"pen": {"size": "pen_size", "opacity": "pen_opacity"},
              "marker": {"size": "marker_size", "opacity": "marker_opacity"},
              "eraser": {"size": "eraser_size"}}

    def param_key(self, name, tool=None):
        tool = tool or self.tool
        if tool == "eraser" and not self.eraser_brush:
            return None                 # «удалить объект целиком» — без размера
        return self.PARAMS.get(tool, {}).get(name)

    def param(self, name, tool=None):
        key = self.param_key(name, tool)
        return self.settings[key] if key else None

    @property
    def eraser_brush(self):
        """Ластик «область» (стирает только там, где провели) или «удалить объект целиком»."""
        return self.settings["eraser_mode"] == "brush"

    def new_erase(self, x, y):
        """Штрих-стирание: вырезает пометки по пути кисти; снимок под ними не трогает."""
        return {"kind": "erase", "width": float(self.param("size", "eraser")), "pts": [(x, y)]}

    def _changed(self, s=None, done=None):
        """s — добавленный или убранный штрих: пересобрать только его прямоугольник; None — всё.
        done — готовый результат этого места (LiveStroke.done): взять его, а не пересчитывать;
        годится, только если кэш до штриха был свежим (ничего не ждёт пересборки)."""
        self.version += 1
        if s is None:
            self._dirty_layer = self._dirty_comp = None
            return
        r = self.stroke_area(s)
        if r is None:
            return                   # штрих весь за краем: в картинке ничего не изменилось
        fresh = done is not None and self._dirty_layer == [] and self._dirty_comp == []
        item = (r, done if fresh else None)
        self._dirty_layer = None if self._dirty_layer is None else self._dirty_layer + [item]
        self._dirty_comp = None if self._dirty_comp is None else self._dirty_comp + [item]

    def stroke_area(self, s):
        """Где штрих меняет картинку: объединение прямоугольников его отрезков, задевающих снимок;
        None — не задевает. По отрезкам, а не по всему штриху: обводка снимка снаружи охватывает
        его целиком, но ничего в нём не меняет (иначе — пересборка всего снимка, ~0,5 с)."""
        box, out = self.bounds(), None
        r = s["width"] / 2 + 2
        pts = s["pts"]
        for p, q in zip([pts[0]] + pts[:-1], pts):
            seg = self._clip((math.floor(min(p[0], q[0]) - r), math.floor(min(p[1], q[1]) - r),
                              math.ceil(max(p[0], q[0]) + r), math.ceil(max(p[1], q[1]) + r)), box)
            if seg:
                out = seg if out is None else (min(out[0], seg[0]), min(out[1], seg[1]),
                                               max(out[2], seg[2]), max(out[3], seg[3]))
        return out

    @staticmethod
    def _from_done(done, r, part):
        """Кусок r из готового результата штриха (part: 1 — слой, 2 — картинка) или None."""
        if done is None:
            return None
        b = done[0]
        if not (b[0] <= r[0] and b[1] <= r[1] and r[2] <= b[2] and r[3] <= b[3]):
            return None
        return crop(done[part], (r[0] - b[0], r[1] - b[1], r[2] - b[0], r[3] - b[1]))

    @staticmethod
    def stroke_rect(s):
        """Прямоугольник, который штрих может закрасить (с запасом на округление и толщину)."""
        r = s["width"] / 2 + 2
        xs, ys = [p[0] for p in s["pts"]], [p[1] for p in s["pts"]]
        return math.floor(min(xs) - r), math.floor(min(ys) - r), math.ceil(max(xs) + r), math.ceil(max(ys) + r)

    def load(self, img):
        self.base = img.convert("RGB")
        self.strokes, self.history, self.redo_stack = [], [], []
        self.saved = False
        self._changed()

    def has_unsaved_marks(self):
        return bool(self.base) and bool(self.strokes) and not self.saved

    def new_stroke(self, x, y):
        """Штрих пера или маркера со СВОИМИ размером и прозрачностью: смена параметров
        потом не меняет уже нарисованное."""
        t = self.tool
        return {"kind": t, "color": self.pen_color if t == "pen" else self.marker_color,
                "width": float(self.param("size", t)), "alpha": self.param("opacity", t) / 100,
                "pts": [(x, y)]}

    def _record(self, act):
        """Новое действие пользователя: в историю; повторять отменённое больше нечего."""
        self.history.append(act)
        self.redo_stack.clear()

    def add(self, s, done=None):
        self.strokes.append(s)
        self._record(("add", s))
        self.saved = False
        self._changed(s, done)

    def erase_at(self, x, y, extra=5):
        for i in range(len(self.strokes) - 1, -1, -1):
            s = self.strokes[i]
            if s["kind"] == "erase":
                continue
            tol = s["width"] / 2 + extra
            pts = s["pts"]
            if len(pts) == 1:
                hit = seg_dist(x, y, *pts[0], *pts[0]) <= tol
            else:
                hit = any(seg_dist(x, y, *a, *b) <= tol for a, b in zip(pts, pts[1:]))
            if hit:
                del self.strokes[i]
                self._record(("erase", s, i))
                self.saved = False
                self._changed(s)
                return True
        return False

    def undo(self):
        if not self.history:
            return False
        act = self.history.pop()
        if act[0] == "add" and act[1] in self.strokes:
            self.strokes.remove(act[1])
        elif act[0] == "erase":
            self.strokes.insert(min(act[2], len(self.strokes)), act[1])
        elif act[0] == "clear":
            self.strokes = list(act[1])
        self.redo_stack.append(act)
        self.saved = False
        self._changed(None if act[0] == "clear" else act[1])
        return True

    def redo(self):
        """Вернуть последнее отменённое действие."""
        if not self.redo_stack:
            return False
        act = self.redo_stack.pop()
        if act[0] == "add":
            self.strokes.append(act[1])
        elif act[0] == "erase" and act[1] in self.strokes:
            self.strokes.remove(act[1])
        elif act[0] == "clear":
            self.strokes = []
        self.history.append(act)
        self.saved = False
        self._changed(None if act[0] == "clear" else act[1])
        return True

    def clear(self):
        if not self.strokes:
            return False
        self._record(("clear", list(self.strokes)))
        self.strokes = []
        self._changed()
        return True

    def bounds(self):
        """Область картинки: всегда снимок (x0, y0, x1, y1). Штрихи за краем в картинку не
        попадают (B7: рисовать за краем можно, сохраняется только снимок) — их видно только на
        экране (EditorView._out_sync). Раньше картинка росла до самого далёкого штриха — 100+ Мп,
        и всё, что делалось на всю картинку, лагало (B13)."""
        return 0, 0, self.base.width, self.base.height

    @classmethod
    def dab(cls, mask, s, p, q, x0, y0, changed=False):
        """Отрезок штриха p→q в маску mask (L) со сдвигом (x0, y0): линия + круг в конце.
        Отрезок рисуется на СВОЁМ холсте с полями (начало зависит только от отрезка) и
        переносится в маску как есть: PIL у края холста округляет толстую линию иначе, и штрих
        на холстах разного размера (картинка, кусочек, буфер живого штриха) расходился на 1 px.
        Так же рисует и живой штрих, поэтому превью и итог совпадают пиксель в пиксель.
        changed=True — вернуть прямоугольник маски, где она реально изменилась (None — нигде):
        кисть больше снимка после первой точки уже ничего не добавляет (B16)."""
        w = s["width"]
        r = w / 2
        a = (round(p[0]), round(p[1]))           # координата СНИМКА: округление «,5» к чётному
        b = (round(q[0]), round(q[1]))           # не зависит от начала холста
        pad = int(r) + 5                         # фигура (не дальше r от отрезка) не касается края
        ox, oy = min(a[0], b[0]) - pad, min(a[1], b[1]) - pad
        seg = Image.new("L", (abs(a[0] - b[0]) + 2 * pad + 1, abs(a[1] - b[1]) + 2 * pad + 1), 0)
        d = ImageDraw.Draw(seg)
        A, B = (a[0] - ox, a[1] - oy), (b[0] - ox, b[1] - oy)
        if A != B:
            d.line((A, B), fill=255, width=max(1, int(w + 0.5)))   # PIL — только целая толщина
        d.ellipse((B[0] - r, B[1] - r, B[0] + r, B[1] + r), fill=255)
        px, py = ox - x0, oy - y0
        box = cls._clip((px, py, px + seg.width, py + seg.height), (0, 0) + mask.size)
        if not box:
            return None
        seg = crop(seg, (box[0] - px, box[1] - py, box[2] - px, box[3] - py))
        old = crop(mask, box)
        if changed:
            nb = ImageChops.subtract(seg, old).getbbox()   # где отрезок ярче того, что было
            if nb is None:
                return None
            seg, old = crop(seg, nb), crop(old, nb)
            box = (box[0] + nb[0], box[1] + nb[1], box[0] + nb[2], box[1] + nb[3])
        mask.paste(ImageChops.lighter(old, seg), box[:2])
        return box

    @classmethod
    def _mask(cls, s, size, x0, y0):
        """Маска штриха на холсте size со сдвигом (x0, y0)."""
        mask = Image.new("L", size, 0)
        pts = s["pts"]
        for p, q in zip([pts[0]] + pts[:-1], pts):
            cls.dab(mask, s, p, q, x0, y0)
        return mask

    @staticmethod
    def alpha_of(s):
        """Непрозрачность штриха 0…1 (у старых штрихов — по виду)."""
        return s.get("alpha", ANNOTATION["marker_alpha"] if s["kind"] == "marker" else 1.0)

    @classmethod
    def _apply(cls, layer, s, x0, y0):
        """Нанести штрих на слой пометок (меняет слой): краска — поверх, стирание — вырезает
        из слоя. Только в прямоугольнике штриха — не на всю картинку."""
        r = cls.stroke_rect(s)
        box = cls._clip((r[0] - x0, r[1] - y0, r[2] - x0, r[3] - y0), (0, 0) + layer.size)
        if box is None:
            return layer
        mask = cls._mask(s, (box[2] - box[0], box[3] - box[1]), x0 + box[0], y0 + box[1])
        region = crop(layer, box)
        if s["kind"] == "erase":
            region.putalpha(ImageChops.subtract(region.getchannel("A"), mask))
        else:
            a = cls.alpha_of(s)
            if a < 1:
                mask = mask.point(lambda v: int(v * a))
            paint_ = Image.new("RGBA", region.size, hex_to_rgb(s["color"]) + (255,))
            paint_.putalpha(mask)
            region = Image.alpha_composite(region, paint_)
        layer.paste(region, box[:2])
        return layer

    @staticmethod
    def _moved(img, at, box, fill):
        """Кэш с границами от точки at перенести на новые границы box (расширить фоном или обрезать)."""
        out = Image.new(img.mode, (box[2] - box[0], box[3] - box[1]), fill)
        out.paste(img, (at[0] - box[0], at[1] - box[1]))
        return out

    @staticmethod
    def _clip(r, box):
        r = max(r[0], box[0]), max(r[1], box[1]), min(r[2], box[2]), min(r[3], box[3])
        return r if r[2] > r[0] and r[3] > r[1] else None

    def _under(self, r, rgb):
        """Снимок на фоне rgb в прямоугольнике r (RGBA) — то, что под пометками."""
        out = Image.new("RGBA", (r[2] - r[0], r[3] - r[1]), rgb + (255,))
        b = self._clip(r, (0, 0) + self.base.size)
        if b:   # сначала вырезать: paste переводит в RGBA ВСЮ вставляемую картинку (весь снимок)
            out.paste(crop(self.base, b), (b[0] - r[0], b[1] - r[1]))
        return out

    def _layer(self, x0, y0, x1, y1):
        """Прозрачный слой со всеми пометками (кэш по версии модели и границам). После правки
        пересобирается только прямоугольник изменённого штриха: все штрихи, задевающие его, —
        по порядку, на холсте этого прямоугольника (рисование не зависит от начала холста)."""
        key = (self.version, x0, y0, x1, y1)
        if self._layer_key == key:
            return self._layer_cache
        box = key[1:]
        if self._layer_cache is None or self._dirty_layer is None:
            layer = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
            for s in self.strokes:
                layer = self._apply(layer, s, x0, y0)
        else:
            old = self._layer_key[1:]
            layer = self._layer_cache if old == box else self._moved(self._layer_cache, old, box, (0, 0, 0, 0))
            for r, done in self._dirty_layer:
                r = self._clip(r, box)
                if r is None:
                    continue
                sub = self._from_done(done, r, 1)
                if sub is None:
                    sub = Image.new("RGBA", (r[2] - r[0], r[3] - r[1]), (0, 0, 0, 0))
                    for s in self.strokes:
                        if self._clip(self.stroke_rect(s), r):
                            sub = self._apply(sub, s, r[0], r[1])
                layer.paste(sub, (r[0] - x0, r[1] - y0))
        self._layer_cache, self._layer_key, self._dirty_layer = layer, key, []
        return layer

    def view_image(self, bg):
        """Картинка для показа на фоне bg (RGB) и её начало (x0, y0). Кэш; после правки
        пересобирается только прямоугольник изменённого штриха."""
        box = self.bounds()
        key = (self.version, bg) + tuple(box)
        if self._comp_key == key:
            return self._comp_cache, box[:2]
        layer, rgb = self._layer(*box), hex_to_rgb(bg)
        old = self._comp_key
        if self._comp_cache is None or self._dirty_comp is None or old[1] != bg:
            comp = Image.alpha_composite(self._under(box, rgb), layer).convert("RGB")
        else:
            comp = self._comp_cache if old[2:] == box else self._moved(self._comp_cache, old[2:4], box, rgb)
            for r, done in self._dirty_comp:
                r = self._clip(r, box)
                if r is None:
                    continue
                part = self._from_done(done, r, 2) if done is not None and done[3] == bg else None
                if part is None:
                    la = crop(layer, (r[0] - box[0], r[1] - box[1], r[2] - box[0], r[3] - box[1]))
                    part = Image.alpha_composite(self._under(r, rgb), la).convert("RGB")
                comp.paste(part, (r[0] - box[0], r[1] - box[1]))
        self._comp_cache, self._comp_key, self._dirty_comp = comp, key, []
        return comp, box[:2]

    def composite(self, bg=None, preview=None):
        """Снимок с пометками. Пометки — на отдельном слое поверх снимка, поэтому
        ластик-кисть стирает только их. Пометки за краем снимка обрезаются по краю.
        preview — незавершённый штрих (показ во время рисования).
        Возвращает (картинка, (x0, y0)) — где на ней точка (0, 0) снимка."""
        x0, y0, x1, y1 = self.bounds()
        bg = bg or ANNOTATION["outside_bg"]
        layer = self._layer(x0, y0, x1, y1)
        if preview:
            layer = self._apply(layer.copy(), preview, x0, y0)
        img = Image.new("RGBA", (x1 - x0, y1 - y0), hex_to_rgb(bg) + (255,))
        img.paste(self.base, (-x0, -y0))
        img = Image.alpha_composite(img, layer)
        return img.convert("RGB"), (x0, y0)

    def export(self):
        """Итоговая картинка для сохранения и буфера обмена."""
        return self.composite(ANNOTATION["outside_bg"])[0]


class LiveStroke:
    """Незавершённый штрих — как кисть в Photoshop: рабочий буфер на время штриха,
    каждый новый отрезок дорисовывается в маску и пересчитывается ТОЛЬКО его прямоугольник
    (раньше на каждое движение мыши заново собиралась вся картинка — ластик «лагал»).
    Буфер — только вокруг штриха и только в пределах снимка: часть за краем в картинку не
    попадает (её показывает вид, EditorView._out_sync), и штрих далеко от снимка ничего не
    выделяет и не пересобирает (B13). Буфера может не быть (box None), пока штрих за краем.
    Пометки под буфером — вырезка из слоя модели; показ — поверх готовой картинки модели."""

    def __init__(self, model, stroke, bg):
        self.m, self.s, self.bg = model, stroke, bg
        self.erase = stroke["kind"] == "erase"
        a = model.alpha_of(stroke)
        self.lut = [int(v * a) for v in range(256)]
        self.rgb = hex_to_rgb(stroke["color"]) if not self.erase else None
        self.full = model.bounds()    # снимок и его слой пометок до штриха (не меняем)
        self.layer_full = model._layer(*self.full)
        self.box = self.comp = self.mask = None
        self.covered = False          # маска — вся 255 во весь снимок: дальше штрих ничего не меняет
        p = stroke["pts"][0]
        seg = self._seg(p, p)
        if seg:
            self._alloc(self._fit(seg))

    def _seg(self, p, q):
        """Прямоугольник отрезка p→q с кругом кисти, обрезанный по снимку; None — весь за краем."""
        r = self.s["width"] / 2 + 2
        return EditorModel._clip((math.floor(min(p[0], q[0]) - r), math.floor(min(p[1], q[1]) - r),
                                  math.ceil(max(p[0], q[0]) + r), math.ceil(max(p[1], q[1]) + r)), self.full)

    def _fit(self, seg):
        """Буфер, в который помещается прямоугольник seg: прежний или расширенный с запасом —
        только в ту сторону, куда вышли, на половину размера буфера; не шире снимка."""
        r = self.s["width"] / 2 + 2
        pad = int(4 * r) + 64
        if self.box is None:
            out = (seg[0] - pad, seg[1] - pad, seg[2] + pad, seg[3] + pad)
        else:
            x0, y0, x1, y1 = self.box
            px, py = max(pad, (x1 - x0) // 2), max(pad, (y1 - y0) // 2)
            out = (seg[0] - px if seg[0] < x0 else x0, seg[1] - py if seg[1] < y0 else y0,
                   seg[2] + px if seg[2] > x1 else x1, seg[3] + py if seg[3] > y1 else y1)
        return EditorModel._clip(out, self.full)

    def _layer0(self, box):
        """Пометки до штриха в прямоугольнике box."""
        f = self.full
        return crop(self.layer_full, (box[0] - f[0], box[1] - f[1], box[2] - f[0], box[3] - f[1]))

    def _comp0(self, box):
        """Картинка до штриха в прямоугольнике box — вырезка из готовой картинки модели (она
        уже собрана для показа): не собирать снимок с пометками заново."""
        img, o = self.m.view_image(self.bg)
        return crop(img, (box[0] - o[0], box[1] - o[1], box[2] - o[0], box[3] - o[1]))

    def _alloc(self, box):
        x0, y0, x1, y1 = self.box = box
        size = (x1 - x0, y1 - y0)
        self.layer0 = self._layer0(box)
        self.under = self.m._under(box, hex_to_rgb(self.bg))     # снимок без пометок
        self.comp = self._comp0(box)
        self.mask = Image.new("L", size, 0)
        pts = self.s["pts"]
        for p, q in zip([pts[0]] + pts[:-1], pts):        # повторить уже нарисованное
            EditorModel.dab(self.mask, self.s, p, q, x0, y0)
        bb = self.mask.getbbox()                 # вне штриха comp уже верная (картинка до него)
        if bb:
            self._update(bb)
        self.covered = box == self.full and self.mask.getextrema()[0] == 255

    def _grow(self, box):
        """Расширить буфер до box: старое — вставкой (без пересчёта), новое поле — вырезка
        пометок и снимка, без штриха (он весь внутри старого буфера)."""
        x0, y0, x1, y1 = box
        at = (self.box[0] - x0, self.box[1] - y0)
        self.layer0 = self._layer0(box)
        self.under = self.m._under(box, hex_to_rgb(self.bg))
        comp = self._comp0(box)
        comp.paste(self.comp, at)
        self.comp = comp
        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        mask.paste(self.mask, at)
        self.mask, self.box = mask, box

    def _update(self, box):
        """Пересчитать прямоугольник box (в координатах буфера) картинки comp."""
        mk = crop(self.mask, box)
        la = crop(self.layer0, box)
        if self.erase:
            la.putalpha(ImageChops.subtract(la.getchannel("A"), mk))
        else:
            # в том же порядке, что модель: (пометки + штрих) поверх снимка. Порядок
            # (снимок + пометки) + штрих давал у полупрозрачного маркера ±1 оттенка
            paint_ = Image.new("RGBA", mk.size, self.rgb + (255,))
            paint_.putalpha(mk.point(self.lut))
            la = Image.alpha_composite(la, paint_)
        region = Image.alpha_composite(crop(self.under, box), la)
        self.comp.paste(region.convert("RGB"), box[:2])

    def done(self):
        """Готовый результат в буфере: (прямоугольник, слой пометок, картинка, фон) — модель
        берёт его вместо пересчёта места штриха (рисование одинаково на любом холсте).
        None — штрих весь за краем, в картинке ничего не изменилось."""
        if self.box is None:
            return None
        la = self.layer0.copy()
        if self.erase:
            la.putalpha(ImageChops.subtract(la.getchannel("A"), self.mask))
        else:
            paint_ = Image.new("RGBA", self.mask.size, self.rgb + (255,))
            paint_.putalpha(self.mask.point(self.lut))
            la = Image.alpha_composite(la, paint_)
        return tuple(self.box), la, self.comp, self.bg

    def add(self, x, y):
        """Новая точка. Возвращает изменённый прямоугольник снимка (только где маска реально
        изменилась), (0, 0, 0, 0) — в картинке ничего (отрезок за краем или кисть уже покрыла
        это место), None — буфер создан или расширен (нужна полная перерисовка)."""
        p, q = self.s["pts"][-1], (x, y)
        self.s["pts"].append(q)
        if self.covered:                         # кисть больше снимка уже закрыла его целиком
            return (0, 0, 0, 0)
        seg = self._seg(p, q)
        if seg is None:
            return (0, 0, 0, 0)
        if self.box is None:                     # первый отрезок, задевший снимок
            self._alloc(self._fit(seg))
            return None
        box = self._fit(seg)
        grown = box != tuple(self.box)
        if grown:
            self._grow(box)
        x0, y0 = self.box[:2]
        r = EditorModel.dab(self.mask, self.s, p, q, x0, y0, changed=True)
        if r is None:                            # маска не изменилась (кисть уже покрыла всё)
            return None if grown else (0, 0, 0, 0)
        self._update(r)
        if seg == self.full and self.box == self.full:   # отрезок накрыл весь снимок (B16)
            self.covered = self.mask.getextrema()[0] == 255
        return None if grown else (r[0] + x0, r[1] + y0, r[2] + x0, r[3] + y0)


class EditorView(tk.Frame):
    """Рабочее пространство: снимок, пометки, масштаб и перетаскивание."""

    def __init__(self, parent, th, model, on_change=None, on_zoom=None):
        super().__init__(parent, bg=th.c("canvas"))
        self.th, self.model, self.on_change, self.on_zoom = th, model, on_change, on_zoom
        self._zt = None            # целевой масштаб плавного зума
        self._zc = (0, 0)          # точка, вокруг которой зумим
        self._anim = None
        self.cur = None
        self.z, self.ox, self.oy = 1.0, 0.0, 0.0
        self._pan = None
        self._need_fit = True
        self._pending = False
        self.live = None                          # незавершённый штрих (LiveStroke)
        self._shown = None                        # какой прямоугольник снимка сейчас на экране
        self.cv = tk.Canvas(self, bg=th.c("canvas"), highlightthickness=0, bd=0, takefocus=1)
        self.cv.pack(fill="both", expand=True)
        self.img_item = self.cv.create_image(0, 0, anchor="nw")
        # пометки за краем снимка — линии холста ПОД картинкой снимка (см. _out_sync)
        self._out_items = []                      # [(штрих, линия холста)] в порядке штрихов
        self._out_view = None                     # (z, ox, oy), для которого посчитаны линии
        self._out_rough = False                   # линии растянуты на кадре зума — пересчитать в конце
        self._ocache = {}                         # id штриха -> (штрих, снимок, его часть за краем)
        self._live_item = None                    # линия незавершённого штриха за краем
        self._key = None                          # (версия модели, вид) показанного кадра
        self.frame_item = self.cv.create_rectangle(0, 0, 0, 0, outline=th.c("border-strong"),
                                                   width=th.size("border"))
        cv = self.cv
        cv.bind("<ButtonPress-1>", self.on_press)
        cv.bind("<B1-Motion>", self.on_drag)
        cv.bind("<ButtonRelease-1>", self.on_release)
        cv.bind("<ButtonPress-3>", self._pan_start)
        cv.bind("<B3-Motion>", self._pan_move)
        cv.bind("<ButtonRelease-3>", self._pan_end)
        cv.bind("<MouseWheel>", self._wheel)
        cv.bind("<Motion>", self._ring_at, add="+")
        cv.bind("<Leave>", lambda e: cv.delete("ring"), add="+")
        cv.bind("<Configure>", self._on_resize)
        step = th.sp(8)
        for k, dx, dy in (("Up", 0, step), ("Down", 0, -step), ("Left", step, 0), ("Right", -step, 0)):
            cv.bind(f"<{k}>", lambda e, dx=dx, dy=dy: self.pan_by(dx, dy))
        # кольцо фокуса — только при переходе с клавиатуры (Tab), не при рисовании мышью
        self._mouse_focus = False
        cv.bind("<FocusIn>", lambda e: None if self._mouse_focus else cv.configure(
            highlightthickness=th.size("focus"), highlightcolor=th.c("focus-ring")))
        cv.bind("<FocusOut>", lambda e: (cv.configure(highlightthickness=0),
                                         setattr(self, "_mouse_focus", False)))
        self.refresh_cursor()

    # ------------------------------------------------------------ координаты и масштаб
    def to_img(self, sx, sy):
        return (sx - self.ox) / self.z, (sy - self.oy) / self.z

    def _size(self):
        return self.cv.winfo_width(), self.cv.winfo_height()

    def fit(self):
        """Весь снимок в окне, не крупнее 100 %."""
        if not self.winfo_exists():   # вид уже пересобран (смена темы) — подгонять нечего
            return
        m = self.model
        W, H = self._size()
        if not m.base or W <= 1:
            self._need_fit = True
            return
        pad = self.th.sp(4)
        z = min(1.0, (W - 2 * pad) / m.base.width, (H - 2 * pad) / m.base.height)
        self._zt = None
        self.z = max(self.th.layout("zoom_min"), z)
        self.ox = (W - m.base.width * self.z) / 2
        self.oy = (H - m.base.height * self.z) / 2
        self._need_fit = False
        self.render()

    def _clamp(self, z):
        return min(self.th.layout("zoom_max"), max(self.th.layout("zoom_min"), z))

    def _apply_zoom(self, z, cx, cy):
        ix, iy = self.to_img(cx, cy)
        self.z = self._clamp(z)
        self.ox, self.oy = cx - ix * self.z, cy - iy * self.z
        self.schedule()

    def zoom_to(self, z, cx=None, cy=None, smooth=True):
        """Масштаб z вокруг точки (cx, cy) холста. smooth — плавно, за время MOTION.fast."""
        W, H = self._size()
        cx = W / 2 if cx is None else cx
        cy = H / 2 if cy is None else cy
        self._zt, self._zc = self._clamp(z), (cx, cy)
        if not smooth or self._pan:
            # во время перетаскивания анимация зума не нужна: она бы спорила со сдвигом
            self._finish_zoom()
            self._apply_zoom(z, cx, cy)
            if self._pan:      # перенести опорную точку, чтобы картинка не прыгнула
                lx, ly = self._pan_last
                self._pan = (lx, ly, self.ox, self.oy)
            return
        if self._anim is None:
            self._zoom_tick()

    def zoom_by(self, steps, cx=None, cy=None):
        base = self._zt if self._zt is not None else self.z   # шаги колеса складываются
        self.zoom_to(base * self.th.layout("zoom_step") ** steps, cx, cy)

    def _zoom_tick(self):
        """Кадр плавного зума: экспоненциально «доезжаем» до цели (~MOTION.fast)."""
        self._anim = None
        if self._zt is None:
            return
        frame = self.th.timing("frame")
        k = 1 - math.exp(-frame / (self.th.motion("fast") / 3))
        z = self.z + (self._zt - self.z) * k
        if abs(self._zt - z) / self._zt < 0.003:
            z, self._zt = self._zt, None
        self._apply_zoom(z, *self._zc)
        if self._zt is not None:
            self._anim = self.after(frame, self._zoom_tick)

    def _wheel(self, e):
        self.zoom_by(e.delta / 120, e.x, e.y)
        return "break"

    def pan_by(self, dx, dy):
        self.ox += dx
        self.oy += dy
        self.schedule()
        return "break"

    def _finish_zoom(self):
        """Остановить плавный зум (если «доезжает») — сразу в его конечной точке."""
        if self._anim is not None:
            self.after_cancel(self._anim)
            self._anim = None
        if self._zt is not None:
            zt, self._zt = self._zt, None
            self._apply_zoom(zt, *self._zc)

    def _pan_start(self, e):
        # Иначе кадры анимации зума пересчитывали бы сдвиг поверх перетаскивания —
        # картинка «уезжала» мимо курсора (причина бага с потерей движений).
        self._finish_zoom()
        self._pan = (e.x, e.y, self.ox, self.oy)   # сдвиг считается от точки нажатия
        self._pan_last = (e.x, e.y)
        self.cv.configure(cursor="fleur")

    def _pan_move(self, e):
        if self._pan:
            x0, y0, ox, oy = self._pan
            self._pan_last = (e.x, e.y)
            self.ox, self.oy = ox + e.x - x0, oy + e.y - y0
            self.schedule()

    def _pan_end(self, e):
        self._pan = None
        self.refresh_cursor()

    def _on_resize(self, e):
        if self._need_fit:
            self.fit()
        else:
            self.schedule()

    def refresh_cursor(self):
        """Курсор инструмента: острие пера/маркера — точно в точке рисования (горячая точка).
        Ластик «Область» — без курсора, только круг области, которую он стирает."""
        tool = self.model.tool
        if tool in ("pen", "marker"):
            cur = cursor(tool)
        elif self.model.eraser_brush:
            cur = "none"          # без перекрестия: видна только область стирания
        else:
            cur = "dotbox"
        self.cv.configure(cursor=cur)
        if not (tool == "eraser" and self.model.eraser_brush):
            self.cv.delete("ring")

    def _ring_at(self, e):
        """Круг области ластика вокруг курсора (две обводки — видно на любом фоне)."""
        cv = self.cv
        cv.delete("ring")
        if self.model.tool != "eraser" or not self.model.eraser_brush or self._pan:
            return
        r = max(2, self.model.param("size", "eraser") * self.z / 2)
        b = self.th.size("border")
        cv.create_oval(e.x - r - b, e.y - r - b, e.x + r + b, e.y + r + b, outline=self.th.c("bg"),
                       width=b, tags="ring")
        cv.create_oval(e.x - r, e.y - r, e.x + r, e.y + r, outline=self.th.c("text-primary"),
                       width=b, tags="ring")

    # ------------------------------------------------------------ отрисовка
    def schedule(self):
        if not self._pending:
            self._pending = True
            self.after_idle(self._render_now)

    def render(self, reset=False):
        if reset:
            self._need_fit = True
            self.fit()
            return
        self.schedule()

    def _display(self):
        """Готовая картинка модели (без незавершённого штриха) и её начало."""
        return self.model.view_image(self.th.c("canvas"))

    def _render_now(self):
        self._pending = False
        m = self.model
        if not m.base or not self.winfo_exists():
            return
        comp, (gx, gy) = self._display()
        ext = (gx, gy, gx + comp.width, gy + comp.height)
        lv = self.live
        W, H = self._size()
        z = self.z
        # видимая часть холста в координатах снимка, пересечённая с картинкой
        vx0, vy0 = self.to_img(0, 0)
        vx1, vy1 = self.to_img(W, H)
        x0, y0 = max(math.floor(vx0), ext[0]), max(math.floor(vy0), ext[1])
        x1, y1 = min(math.ceil(vx1), ext[2]), min(math.ceil(vy1), ext[3])
        if x1 > x0 and y1 > y0:
            vis = (x0 - gx, y0 - gy, x1 - gx, y1 - gy)
            # снимок виден целиком и штриха нет — без копии (resize картинку не меняет)
            part = comp if vis == (0, 0) + comp.size and not (lv and lv.box) else crop(comp, vis)
            if lv and lv.box:        # незавершённый штрих — поверх
                part.paste(lv.comp, (lv.box[0] - x0, lv.box[1] - y0))
            size = (max(1, round((x1 - x0) * z)), max(1, round((y1 - y0) * z)))
            self.tk_img = ImageTk.PhotoImage(self._scaled(part, size))
            self.cv.itemconfigure(self.img_item, image=self.tk_img, state="normal")
            self.cv.coords(self.img_item, round(self.ox + x0 * z), round(self.oy + y0 * z))
            self._shown = (x0, y0, x1, y1)
        else:
            self.cv.itemconfigure(self.img_item, state="hidden")
            self._shown = None
        self._out_sync()
        self._key = (m.version,) + self._view_key()
        b = m.base
        self.cv.coords(self.frame_item, self.ox - 1, self.oy - 1, self.ox + b.width * z, self.oy + b.height * z)
        self.cv.tag_raise(self.frame_item)
        self.cv.tag_raise("ring")
        if self.on_zoom:
            self.on_zoom(z)

    def _changed(self):
        self.schedule()
        if self.on_change:
            self.on_change()

    def _scaled(self, part, size):
        """Кусок снимка в размер экрана: крупно — чёткими пикселями; мелко — сглаженно, с грубым
        предуменьшением (reducing_gap): при отдалении в 10 раз заметно быстрее, на глаз так же."""
        if size == part.size:
            return part                  # масштаб 1:1 — без пересчёта (кадр на весь экран ~10 мс)
        if self.z >= self.th.layout("zoom_pixel"):
            return part.resize(size, Image.NEAREST)
        gap = self.th.layout("zoom_reduce_gap") if self.z < 1 else None
        return part.resize(size, Image.BILINEAR, reducing_gap=gap)

    def _view_key(self):
        W, H = self._size()
        return self.z, self.ox, self.oy, W, H

    # ------------------------------------------------------------ пометки за краем снимка
    # В картинку они не попадают (B7), но видны на экране — линиями холста Tk ПОД картинкой
    # снимка: внутри снимка их закрывает сам снимок. Сдвиг — один вызов move, зум — пересчёт
    # координат; цена не зависит от того, сколько и как далеко нарисовано (картинка во весь
    # экран с прозрачностью стоила до 5 с на кадр). Tk не умеет полупрозрачные линии: маркер и
    # тонкие при отдалении линии — сплошным цветом, смешанным с фоном; ластик-кисть — линией
    # цвета фона (за краем под пометками только фон).
    def _orect(self, s):
        """Часть штриха s за краем снимка: прямоугольник в px снимка или None (весь на снимке)."""
        size = self.model.base.size
        c = self._ocache.get(id(s))
        if c is not None and c[0] is s and c[1] == size and len(s["pts"]) == c[3]:
            return c[2]
        box, out = (0, 0) + size, None
        r = s["width"] / 2 + 2
        pts = s["pts"]
        for p, q in zip([pts[0]] + pts[:-1], pts):
            seg = (math.floor(min(p[0], q[0]) - r), math.floor(min(p[1], q[1]) - r),
                   math.ceil(max(p[0], q[0]) + r), math.ceil(max(p[1], q[1]) + r))
            if EditorModel._clip(seg, box) == seg:
                continue                     # отрезок весь на снимке
            out = seg if out is None else (min(out[0], seg[0]), min(out[1], seg[1]),
                                           max(out[2], seg[2]), max(out[3], seg[3]))
        self._ocache[id(s)] = (s, size, out, len(pts))
        return out

    def _out_style(self, s):
        """Цвет и толщина линии штриха s за краем при текущем масштабе."""
        bg = hex_to_rgb(self.th.c("canvas"))
        w = s["width"] * self.z
        if s["kind"] == "erase":
            return self.th.c("canvas"), max(1.0, w)
        a = self.model.alpha_of(s) * min(1.0, w)  # тонкая при отдалении — бледнее, как на снимке
        c = hex_to_rgb(s["color"])
        return "#%02x%02x%02x" % tuple(round(b + (x - b) * a) for x, b in zip(c, bg)), max(1.0, w)

    def _out_coords(self, pts):
        z, ox, oy = self.z, self.ox, self.oy
        flat = [v for x, y in pts for v in (ox + x * z, oy + y * z)]
        return flat if len(flat) > 2 else flat * 2          # точка — линия нулевой длины

    def _out_make(self, s, pts=None):
        """Линия штриха s (по точкам pts) под картинкой снимка, над прежними линиями."""
        fill, width = self._out_style(s)
        item = self.cv.create_line(*self._out_coords(pts or s["pts"]), fill=fill, width=width,
                                   capstyle="round", joinstyle="round", tags=("out",))
        self.cv.tag_lower(item, self.img_item)
        return item

    def _out_sync(self):
        """Линии за краем — по штрихам модели (добавлен, отменён, удалён) и по виду."""
        m = self.model
        want = [s for s in m.strokes if self._orect(s)]
        have = self._out_items
        k = 0
        while k < len(have) and k < len(want) and have[k][0] is want[k]:
            k += 1
        for _, item in have[k:]:                 # отменённые / удалённые / не на своём месте
            self.cv.delete(item)
        view = (self.z, self.ox, self.oy)
        old = self._out_view
        if old is not None and k and (old != view or (self._out_rough and self._anim is None)):
            if old[0] == self.z and not (self._out_rough and self._anim is None):
                self.cv.move("out", self.ox - old[1], self.oy - old[2])     # сдвиг — все разом
            elif self._anim is not None:
                # кадр плавного зума: растянуть все линии одним вызовом Tk (толщина — прежняя);
                # точно — в конце зума. Пересчёт каждой линии на каждом кадре — до 0,5 с на деление
                f = self.z / old[0]
                self.cv.scale("out", old[1], old[2], f, f)
                self.cv.move("out", self.ox - old[1], self.oy - old[2])
                self._out_rough = True
            else:                                # масштаб — заново координаты и толщина
                for s, item in have[:k]:
                    fill, width = self._out_style(s)
                    self.cv.coords(item, *self._out_coords(s["pts"]))
                    self.cv.itemconfigure(item, fill=fill, width=width)
                self._out_rough = False
        if self._live_item is not None and self.cur is not None:
            fill, width = self._out_style(self.cur)
            self.cv.coords(self._live_item, *self._out_coords(self.cur["pts"]))
            self.cv.itemconfigure(self._live_item, fill=fill, width=width)
            self.cv.tag_lower(self._live_item, self.img_item)
        new = []
        for s in want[k:]:
            new.append((s, self._out_make(s)))
        if self._live_item is not None:          # незавершённый штрих — над сохранёнными
            self.cv.tag_lower(self._live_item, self.img_item)
        self._out_items = have[:k] + new
        self._out_view = view

    def _live_out(self, p, q):
        """Отрезок незавершённого штриха: если штрих вышел за снимок — его линия за краем."""
        s = self.cur
        if self._live_item is None:
            r = s["width"] / 2 + 2
            seg = (math.floor(min(p[0], q[0]) - r), math.floor(min(p[1], q[1]) - r),
                   math.ceil(max(p[0], q[0]) + r), math.ceil(max(p[1], q[1]) + r))
            if EditorModel._clip(seg, (0, 0) + self.model.base.size) == seg:
                return                           # пока весь на снимке — линии не нужно
            self._live_item = self._out_make(s)
            return
        self.cv.coords(self._live_item, *self._out_coords(s["pts"]))

    def _patch(self, box):
        """Вывести на экран только изменившийся прямоугольник живого штриха (координаты снимка):
        кусочек копируется прямо в показанную картинку (Tk «photo copy») — без новых объектов
        на холсте и без пересборки всего кадра."""
        if box is None or self._shown is None:   # буфер расширен / кадра ещё нет — полная перерисовка
            self.schedule()
            return
        bx0, by0, bx1, by1 = box
        x0, y0, x1, y1 = self._shown               # что показано: прямоугольник снимка
        px0, py0 = max(math.floor(bx0), x0), max(math.floor(by0), y0)
        px1, py1 = min(math.ceil(bx1), x1), min(math.ceil(by1), y1)
        if px1 <= px0 or py1 <= py0:
            if (bx0, by0) != (bx1, by1) and not (x0 <= bx0 and bx1 <= x1 and y0 <= by0 and by1 <= y1):
                self.schedule()                    # штрих вышел за показанную часть
            return
        z = self.z
        dx0, dy0 = round((px0 - x0) * z), round((py0 - y0) * z)    # та же сетка, что у полного кадра
        dx1, dy1 = round((px1 - x0) * z), round((py1 - y0) * z)
        if dx1 <= dx0 or dy1 <= dy0:
            return
        gx, gy = self.live.box[:2]
        part = crop(self.live.comp, (px0 - gx, py0 - gy, px1 - gx, py1 - gy))
        piece = ImageTk.PhotoImage(self._scaled(part, (dx1 - dx0, dy1 - dy0)))
        self.tk.call(str(self.tk_img), "copy", str(piece), "-to", dx0, dy0)

    # ------------------------------------------------------------ рисование
    def on_press(self, e):
        m = self.model
        if not m.base:
            return
        if self.cv.focus_get() is not self.cv:
            self._mouse_focus = True
            self.cv.focus_set()   # стрелки после клика двигают холст
        x, y = self.to_img(e.x, e.y)
        if m.tool == "eraser" and not m.eraser_brush:
            if m.erase_at(x, y, extra=5 / self.z):
                self._changed()
            return
        self.cur = m.new_erase(x, y) if m.tool == "eraser" else m.new_stroke(x, y)
        self.live = LiveStroke(m, self.cur, self.th.c("canvas"))
        self._live_item = None
        if self._pending or self._key != (m.version,) + self._view_key():
            self._render_now()                       # кадр устарел — целиком
        lv = self.live                               # иначе — только точка под кистью
        p = self.cur["pts"][0]
        if lv.box and self._shown:
            self._patch(lv._seg(p, p))
        self._live_out(p, p)

    def on_drag(self, e):
        m = self.model
        if not m.base:
            return
        x, y = self.to_img(e.x, e.y)
        self._ring_at(e)
        if m.tool == "eraser" and not m.eraser_brush:
            if m.erase_at(x, y, extra=5 / self.z):
                self._changed()
            return
        if not self.live:
            return
        p = self.cur["pts"][-1]
        if abs(p[0] - x) * self.z < 1 and abs(p[1] - y) * self.z < 1:
            return
        self._patch(self.live.add(x, y))
        self._live_out(p, (x, y))

    def on_release(self, e):
        if not self.cur:
            return
        # модель обновит только прямоугольник нового штриха — готовым результатом из буфера
        m = self.model
        fresh = not self._pending and self._key == (m.version,) + self._view_key()
        s, item = self.cur, self._live_item
        m.add(s, self.live.done() if self.live else None)
        self.cur = self.live = self._live_item = None
        if item is not None:                         # линия штриха за краем остаётся его линией
            if fresh and self._orect(s):
                self._out_items.append((s, item))
            else:
                self.cv.delete(item)
        if fresh:
            # на экране уже итог: снимок — кусочки буфера, за краем — линия штриха. Кадр
            # целиком не нужен — только отметить, что он свежий
            self._key = (m.version,) + self._view_key()
        else:
            self._render_now()
        if self.on_change:
            self.on_change()
