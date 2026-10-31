# -*- coding: utf-8 -*-
"""Обновление exe с GitHub (B24), без Tk: узнать последнюю версию, скачать, подменить файл.

Работающий exe нельзя перезаписать, но можно переименовать: скачанное лежит рядом (<exe>.new), старый
становится <exe>.old, новый встаёт на его место, поэтому ярлыки и автозапуск ведут туда же. <exe>.old
удаляется при следующем запуске (cleanup). Ошибки — UpdateError с текстом для человека."""

import decimal
import hashlib
import json
import os
import re
import subprocess

from .i18n import tr

API = "https://api.github.com/repos/KsandrXX/ScreenShoterXX/releases/latest"
ASSET = "ScreenShoterXX.exe"
PAGE = "github.com/KsandrXX/ScreenShoterXX/releases"
TIMEOUT = 15                     # секунд на ответ сервера; при обрыве загрузка не висит вечно
CHUNK = 1 << 16
HEADERS = {"User-Agent": "ScreenShoterXX", "Accept": "application/vnd.github+json"}


class UpdateError(Exception):
    pass


def number(tag):
    """Номер версии: «V1.09» — Decimal: 1.10 новее 1.09, а 1.6 новее 1.54 (шаг +0,01 и +0,1)."""
    m = re.fullmatch(r"[vV]?(\d+\.\d+)", (tag or "").strip())
    if not m:
        raise UpdateError(tr("Не удалось узнать последнюю версию. Попробуйте позже"))
    return decimal.Decimal(m.group(1))


def _open(url):
    import urllib.error
    import urllib.request
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=TIMEOUT)
    except urllib.error.HTTPError as ex:
        if ex.code in (403, 429):        # лимит GitHub: 60 запросов в час с одного адреса
            raise UpdateError(tr("GitHub просит подождать. Попробуйте через час")) from ex
        raise UpdateError(tr("Не удалось узнать последнюю версию. Попробуйте позже")) from ex
    except OSError as ex:                # URLError и таймауты — потомки OSError
        raise UpdateError(tr("Нет связи с GitHub. Проверьте интернет")) from ex


def latest():
    """Последний релиз: {"tag", "url", "size", "digest"}."""
    try:
        with _open(API) as r:
            data = json.loads(r.read().decode("utf-8"))
        asset = next(a for a in data["assets"] if a["name"] == ASSET)
        rel = {"tag": data["tag_name"], "url": asset["browser_download_url"], "size": int(asset["size"]),
               "digest": asset.get("digest") or ""}
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as ex:
        if isinstance(ex, UpdateError):
            raise
        raise UpdateError(tr("Не удалось узнать последнюю версию. Попробуйте позже")) from ex
    number(rel["tag"])
    return rel


def download(rel, path, progress=None):
    """Скачать релиз в path и сверить размер и контрольную сумму. Не вышло — файла path нет."""
    sha = hashlib.sha256()
    got = 0
    try:
        with _open(rel["url"]) as r, open(path, "wb") as f:
            while True:
                part = r.read(CHUNK)
                if not part:
                    break
                f.write(part)
                sha.update(part)
                got += len(part)
                if progress:
                    progress(got, rel["size"])
        want = rel["digest"].partition("sha256:")[2].lower()
        if got != rel["size"] or (want and sha.hexdigest() != want):
            raise UpdateError(tr("Файл скачался с ошибкой. Программа не изменилась"))
    except PermissionError as ex:
        raise UpdateError(tr("Нет права записи в папку программы. Скачайте новую версию вручную: {}").format(PAGE)) from ex
    except OSError as ex:
        _remove(path)
        raise UpdateError(tr("Загрузка оборвалась. Программа не изменилась")) from ex
    except UpdateError:
        _remove(path)
        raise


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def discard(exe):
    """Скачанное не пригодилось."""
    _remove(exe + ".new")


def swap(exe):
    """Поставить <exe>.new на место exe; старый — <exe>.old. Сбой — всё как было."""
    new, old = exe + ".new", exe + ".old"
    try:
        _remove(old)                     # прошлое обновление, если его ещё не убрали
        os.replace(exe, old)
    except OSError as ex:
        discard(exe)
        raise UpdateError(tr("Не удалось заменить файл программы. Программа не изменилась")) from ex
    try:
        os.replace(new, exe)
    except OSError as ex:
        os.replace(old, exe)
        discard(exe)
        raise UpdateError(tr("Не удалось заменить файл программы. Программа не изменилась")) from ex


def revert(exe):
    """Новый exe не запустился: вернуть старый. Нового может уже не быть: его мог удалить антивирус."""
    os.replace(exe + ".old", exe)


def launch(exe):
    """Запустить новый exe. Без PYINSTALLER_RESET_ENVIRONMENT он взял бы временную папку этой копии,
    а она удаляется при выходе (документация PyInstaller, с версии 6.9)."""
    return subprocess.Popen([exe, "--updated"], cwd=os.path.dirname(exe),
                            env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"))


def cleanup(exe):
    """Следы прошлого обновления. False — файл ещё занят (закрывается старая копия, проверяет антивирус)."""
    _remove(exe + ".old")
    discard(exe)
    return not os.path.exists(exe + ".old")
