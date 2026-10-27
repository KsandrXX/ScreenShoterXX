# -*- coding: utf-8 -*-
"""Язык интерфейса (B26): русский и английский.

Тексты в коде пишутся по-русски и проходят через tr("…"): при английском языке берётся перевод
из lang_en.EN (ключ — сам русский текст), нет перевода — остаётся русский. Текст с подстановкой —
tr("Снимок {w} × {h} px").format(...), не f-строкой (иначе ключ не найдётся).

Язык по умолчанию — по Windows: русская Windows — русский, ЛЮБАЯ другая — английский (решение
пользователя). Настройка «lang»: "" — как в Windows, "ru", "en". Смена на лету — App.set_language
(реестр действий собирается заново: тексты вычисляются при регистрации)."""

import ctypes

from .lang_en import EN

LANGS = ("ru", "en")
_lang = "ru"
_layout_en = {}                         # свои переводы текстов раскладки (settings_layout.json, "en")


def system_lang():
    """Язык интерфейса Windows: "ru" только для русского (основной язык 0x19), иначе "en"."""
    try:
        lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError):
        return "en"
    return "ru" if lid & 0x3FF == 0x19 else "en"


def resolve(setting):
    """Значение настройки lang ("" / "ru" / "en") -> язык."""
    return setting if setting in LANGS else system_lang()


def set_lang(lang):
    global _lang
    _lang = lang if lang in LANGS else "ru"


def lang():
    return _lang


def set_layout_texts(en):
    """Переводы текстов раскладки настроек из settings_layout.json (важнее общего словаря)."""
    global _layout_en
    _layout_en = dict(en or {})


def tr(text):
    """Перевод русского текста на текущий язык (нет перевода — как есть)."""
    if _lang == "ru" or not text:
        return text
    return _layout_en.get(text) or EN.get(text, text)
