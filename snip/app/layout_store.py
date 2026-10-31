# -*- coding: utf-8 -*-
"""Раскладка страниц настроек, которую пользователь собрал в конструкторе (B23).

Файл `settings_layout.json` (рядом с settings.json; в git — это дизайн программы, а не
данные пользователя). Меняет ТОЛЬКО место и тексты: раздел (страницу), группу, порядок,
название и описание настройки, название раздела. Что делает настройка, задаёт features.py —
блок привязан к ключу настройки и не ломается. Формат:

    {"pages": [{"id": "capture", "title": "Снимки", "icon": "snip",
                "items": ["snip_save", {"section": "Работа в фоне"}, "tray", ...]}, ...],
     "texts": {"snip_save": {"title": "...", "description": "..."}},
     "en": {"Русский текст": "English text"}}

Тексты в файле — русские; при английском языке они идут через i18n.tr: сначала свои переводы
из "en" (важнее), потом общий словарь lang_en. Конструктор работает всегда по-русски.

Элемент {"section": имя} начинает группу: настройки после него — в ней (до следующей).
Настройки, которых нет в файле (появились в программе позже), остаются на своём месте из
features.py — в конце своего раздела; неизвестные ключи (настройку убрали) пропускаются."""

import json
import os

from ..core.i18n import tr


class LayoutStore:
    FILE = "settings_layout.json"

    def __init__(self, path):
        self.path = path
        self.data = None
        self.defaults = None           # как было в features.py — для «Сбросить всё»
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and isinstance(d.get("pages"), list):
                self.data = d
        except (OSError, ValueError):
            pass                       # нет файла или он испорчен — раскладка из features.py

    # --- снимок и применение ---
    def remember_defaults(self, reg):
        if self.defaults is None:
            self.defaults = {
                "pages": {p.id: (p.title, p.icon, p.order, p.bottom) for p in reg.pages.values()},
                "settings": {s.key: (s.page, s.section, s.order, s.title, s.description)
                             for s in reg.settings.values()}}

    def apply(self, reg, data=None):
        """Разложить реестр по раскладке data (по умолчанию — из файла). None — как в features.py."""
        self.remember_defaults(reg)
        self._restore(reg)
        data = self.data if data is None else data
        reg.page_layout = {}
        if not data:
            return
        texts = data.get("texts") or {}
        seen = set()
        for pi, p in enumerate(data.get("pages", [])):
            pid = p.get("id")
            if not isinstance(pid, str) or not pid:
                continue
            if pid in reg.pages:
                pg = reg.pages[pid]
                pg.title = tr(p.get("title")) or pg.title
                pg.icon = p.get("icon") or pg.icon
                pg.order = pi
            else:
                reg.page(pid, tr(p.get("title")) or tr("Раздел"), icon=p.get("icon") or "settings", order=pi)
            section, n, items = None, 0, []
            for it in p.get("items", []):
                if isinstance(it, dict) and "section" in it:
                    section = tr(str(it["section"] or "")) or None
                    items.append({"section": section or ""})
                elif isinstance(it, str) and it in reg.settings and it not in seen:
                    s = reg.settings[it]
                    s.page, s.section, s.order = pid, section, n
                    n += 1
                    seen.add(it)
                    items.append(it)
            reg.page_layout[pid] = items          # с пустыми группами и их местом
        for pid, pg in reg.pages.items():           # разделы программы, которых нет в файле, — в конце
            if pid not in {p.get("id") for p in data.get("pages", [])}:
                pg.order = 1000 + pg.order
        for key, s in reg.settings.items():         # новые настройки — в конце своего раздела
            if key not in seen:
                s.order = 1000 + s.order
        listed = {p.get("id") for p in data.get("pages", [])}
        for pid in list(reg.pages):                 # раздел удалён в конструкторе и пуст — убрать
            if pid not in listed and not reg.settings_for(pid):
                del reg.pages[pid]
        for key, t in texts.items():
            s = reg.settings.get(key)
            if s is None or not isinstance(t, dict):
                continue
            if t.get("title"):
                s.title = tr(t["title"])
            # описание, которое программа меняет сама (функция), из файла не подменяется
            if "description" in t and not callable(self.defaults["settings"][key][4]):
                s.description = tr(t["description"]) or None

    def _restore(self, reg):
        for pid in list(reg.pages):
            if pid not in self.defaults["pages"]:
                del reg.pages[pid]                  # раздел, созданный в конструкторе
        for pid, (title, icon, order, bottom) in self.defaults["pages"].items():
            if pid not in reg.pages:
                reg.page(pid, title, icon=icon, order=order, bottom=bottom)   # раздел удалили в конструкторе
            pg = reg.pages[pid]
            pg.title, pg.icon, pg.order = title, icon, order
        for key, v in self.defaults["settings"].items():
            if key in reg.settings:
                s = reg.settings[key]
                s.page, s.section, s.order, s.title, s.description = v

    def capture(self, reg):
        """Текущая раскладка реестра в формате файла. Где раскладка уже из файла — она же (с
        пустыми группами на их месте); настройки, которых в ней нет, — в конце раздела."""
        pages = []
        raw = getattr(reg, "page_layout", {})
        for p in reg.page_list():
            if p.id in raw:
                items = [it for it in raw[p.id] if isinstance(it, dict)
                         or (it in reg.settings and reg.settings[it].page == p.id)]
                items += [s.key for s in reg.settings_for(p.id) if s.key not in items]
            else:
                items, section = [], None
                for s in reg.settings_for(p.id):
                    if s.section != section:
                        items.append({"section": s.section or ""})
                        section = s.section
                    items.append(s.key)
            pages.append({"id": p.id, "title": p.title, "icon": p.icon, "items": items})
        texts = {}
        for key, s in reg.settings.items():
            d = self.defaults["settings"].get(key)
            if d is None:
                continue
            t = {}
            if s.title != d[3]:
                t["title"] = s.title
            if not callable(d[4]) and s.description != d[4]:
                t["description"] = s.description or ""
            if t:
                texts[key] = t
        return {"pages": pages, "texts": texts}

    # --- файл ---
    def save(self, data):
        self.data = data
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)                  # не оставить полуфайл при сбое

    def reset(self, reg):
        """«Сбросить всё»: раскладка и тексты — как в программе, файл удаляется."""
        self.data = None
        try:
            os.remove(self.path)
        except OSError:
            pass
        self.apply(reg)


class LayoutEditor:
    """Действия конструктора настроек над раскладкой (без Tk). Каждое действие сразу
    применяется к реестру и записывается в файл; интерфейс после него пересобирает страницу."""

    def __init__(self, store, reg):
        self.store, self.reg = store, reg
        store.remember_defaults(reg)
        self.data = store.capture(reg)

    def _commit(self):
        self.store.apply(self.reg, self.data)
        self.store.save(self.data)

    def _page(self, pid):
        return next((p for p in self.data["pages"] if p["id"] == pid), None)

    def page_ids(self):
        return [p["id"] for p in self.data["pages"]]

    def items(self, pid):
        """[("section", имя) | ("setting", Setting)] — по порядку, с пустыми группами."""
        p = self._page(pid)
        out = []
        for it in (p["items"] if p else []):
            if isinstance(it, dict):
                out.append(("section", it.get("section") or ""))
            elif it in self.reg.settings:
                out.append(("setting", self.reg.settings[it]))
        return out

    def has_settings(self, pid):
        return any(k == "setting" for k, _ in self.items(pid))

    # --- блоки ---
    def move(self, pid, i, to_pid, j=None):
        """Блок i раздела pid — на место j раздела to_pid (None — в конец)."""
        src, dst = self._page(pid), self._page(to_pid)
        if not src or not dst or not 0 <= i < len(src["items"]):
            return False
        if src is dst and j is not None and j in (i, i + 1):
            return False                      # на то же место
        it = src["items"].pop(i)
        if j is None:
            j = len(dst["items"])
        elif src is dst and j > i:
            j -= 1
        dst["items"].insert(j, it)
        self._commit()
        return True

    def add_section(self, pid, name="Новая группа"):      # в файле раскладки — по-русски
        self._page(pid)["items"].append({"section": name})
        self._commit()

    def rename_section(self, pid, i, name):
        self._page(pid)["items"][i] = {"section": name}
        self._commit()

    def remove_section(self, pid, i):
        """Убрать заголовок группы: её настройки остаются и переходят к группе выше."""
        self._page(pid)["items"].pop(i)
        self._commit()

    # --- тексты ---
    def default_text(self, key, field):
        d = self.store.defaults["settings"][key]
        return d[3] if field == "title" else d[4]

    def editable(self, key, field):
        """Описание, которое программа меняет сама (функция), правке не подлежит."""
        return field == "title" or not callable(self.default_text(key, field))

    def set_text(self, key, field, value):
        texts = self.data.setdefault("texts", {})
        t = texts.setdefault(key, {})
        if value == (self.default_text(key, field) or "") or (field == "title" and not value):
            t.pop(field, None)                # как в программе — запись не нужна
        else:
            t[field] = value
        if not t:
            texts.pop(key, None)
        self._commit()

    # --- разделы ---
    def add_page(self, title="Новый раздел"):
        n = 1
        while self._page(f"user_{n}") or f"user_{n}" in self.reg.pages:
            n += 1
        pid = f"user_{n}"
        ps = self.data["pages"]
        at = next((i for i, p in enumerate(ps) if p["id"] in self.reg.pages and self.reg.pages[p["id"]].bottom), len(ps))
        ps.insert(at, {"id": pid, "title": title, "icon": "settings", "items": []})
        self._commit()
        return pid

    def rename_page(self, pid, title):
        if title:
            self._page(pid)["title"] = title
            self._commit()

    def move_page(self, pid, d):
        ps = self.data["pages"]
        i = ps.index(self._page(pid))
        j = i + d
        if not 0 <= j < len(ps) or any(self.reg.pages[ps[k]["id"]].bottom for k in (i, j)):
            return False
        ps[i], ps[j] = ps[j], ps[i]
        self._commit()
        return True

    def place_page(self, pid, j):
        """Раздел pid — перед разделом с номером j (номера — до переноса, как блоки в move)."""
        ps = self.data["pages"]
        p = self._page(pid)
        i = ps.index(p)
        if j in (i, i + 1):
            return False                      # на то же место
        ps.pop(i)
        ps.insert(j - 1 if j > i else j, p)
        self._commit()
        return True

    def remove_page(self, pid):
        """Удалить раздел — только пустой (без настроек): иначе настройки пропали бы из окна."""
        if self.has_settings(pid) or len(self.data["pages"]) < 2:
            return False
        self.data["pages"].remove(self._page(pid))
        self._commit()
        return True

    def reset(self):
        self.store.reset(self.reg)
        self.data = self.store.capture(self.reg)
