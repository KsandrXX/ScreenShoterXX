# -*- coding: utf-8 -*-
"""Кнопка «Обновить приложение» (B24): проверка и загрузка идут в потоке, строка настроек показывает,
что происходит, установка и перезапуск — в главном потоке. Поток Tk не трогает."""

import os
import sys
import threading

from ..core import updater, winapi as W
from ..core.i18n import tr


class Updater:
    def __init__(self, app, version):
        self.app, self.version = app, version
        self.exe = sys.executable if getattr(sys, "frozen", False) else None   # из исходников обновлять нечего
        self.thread = None
        self.text = None            # что показать в строке; None — обычное описание
        self.error = None
        self.ready = None           # скачанный релиз ждёт установки
        self.done = None            # итог потока: текст
        self.proc = None

    def available(self):
        return bool(self.exe)

    def busy(self):
        return self.thread is not None or self.ready is not None or self.proc is not None

    def description(self, st=None):
        if not self.available():
            return tr("Работает в программе, скачанной с GitHub. Сейчас она запущена из папки с кодом")
        return self.text or tr("Программа скачает новую версию с GitHub и перезапустится. Настройки останутся")

    def start(self):
        if self.busy() or not self.available():
            return
        self.text, self.error, self.done = tr("Проверяю…"), None, None
        self.thread = threading.Thread(target=self._work, daemon=True)
        self.thread.start()
        self._show()
        self._poll()

    def _work(self):
        try:
            rel = updater.latest()
            if updater.number(rel["tag"]) <= updater.number(self.version):
                self.done = tr("У вас последняя версия")
                return
            self.text = tr("Скачиваю {}…").format(rel["tag"])
            updater.download(rel, self.exe + ".new", self._progress(rel["tag"]))
            self.ready = rel
        except updater.UpdateError as ex:
            self.error = str(ex)

    def _progress(self, tag):
        def show(got, size):
            self.text = tr("Скачиваю {}: {} %").format(tag, got * 100 // max(1, size))
        return show

    def _poll(self):
        """Строка обновляется здесь: поток только меняет текст."""
        if self.thread.is_alive():
            self._show()
            self.app.root.after(self.app.th.timing("poll"), self._poll)
            return
        self.thread = None
        if self.ready:
            self.text = tr("Устанавливаю {}…").format(self.ready["tag"])
        else:
            self.text = self.done
        self._show()
        if self.ready:
            self._install()

    def _install(self):
        app = self.app
        if not app.idle():              # идёт снимок или запись — перезапуск дождётся конца
            app.root.after(app.th.timing("poll"), self._install)
            return
        if not app._resolve_unsaved(tr("Сохранить пометки на снимке перед обновлением?")):
            self._stop(tr("Обновление отменено"))
            return
        app.model.saved = True          # ответ уже дан: при выходе не спрашивать второй раз
        try:
            updater.swap(self.exe)
            self._admin_mark()
            self.proc = updater.launch(self.exe)
        except updater.UpdateError as ex:
            self._stop(None, str(ex))
            return
        except OSError:
            updater.revert(self.exe)
            self._stop(None, tr("Новая версия не запустилась. Программа не изменилась"))
            return
        app.root.after(app.th.timing("update_settle"), self._launched)

    def _launched(self):
        """Новая копия ждёт, пока эта выйдет; если она уже закрылась, значит, запуск не удался."""
        if self.proc.poll() is None:
            self.app.exit_app()
            return
        self.proc = None
        updater.revert(self.exe)
        self._stop(None, tr("Новая версия не запустилась. Программа не изменилась"))

    def _admin_mark(self):
        """Копия без прав при заданном запуске от администратора отдаст запуск заданию (snipper.pyw,
        admin_start): отметка велит копии с правами подождать, пока эта выйдет."""
        if self.app.settings["admin_task"] and not W.is_admin():
            with open(os.path.join(self.app.data_dir, W.ADMIN_MARK), "w", encoding="utf-8") as f:
                f.write("restart")

    def _stop(self, text, error=None):
        updater.discard(self.exe)
        self.ready, self.text, self.error = None, text, error
        self._show()

    def _show(self):
        sv = self.app.settings_view
        sv.refresh_rows()
        sv.refresh_errors()
