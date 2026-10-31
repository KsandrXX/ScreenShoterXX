# -*- coding: utf-8 -*-
"""Главное окно: собирает экраны из шаблонов и реестра, держит состояние программы."""

import os
import queue
import re
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog

from PIL import Image, ImageDraw

from ..core import i18n
from ..core.i18n import tr
from ..core import winapi as W
from ..core.changes import CHANGES
from ..core.dxgi import Duplicator
from ..core.gif import GifCapture, save_gif_async
from ..core.settings import Settings
from ..ui import components as C
from ..ui.layouts import (AppShell, Dialog, HudToolbar, Modal, SettingsLayout, action_tip, ask, changes_list,
                          window_hooks)
from ..ui.registry import Registry
from ..ui.tokens import ANNOTATION, TECH, Theme
from . import features
from .colorpicker import ColorPicker
from .editor import EditorModel, EditorView
from .layout_store import LayoutEditor, LayoutStore
from .overlay import Overlay
from .rechud import RecHud
from .update import Updater

_DEFAULT_REPORT = tk.Tk.report_callback_exception
APP_NAME = "Ножницы XX"
APP_VERSION = "1.02"            # версия релиза, публичная нумерация: с ней сверяется обновление (B24)
APP_ID = "ScreenshoterXX.Snipper"
SNIP_HINTS = {"free": "Обведите область", "rect": "Выделите область", "window": "Щёлкните по окну",
              "full": "Весь экран"}


class App:
    def __init__(self, app_dir, settings_path=None, hidden=False, layout_path=None, layout_edit=False,
                 data_dir=None, media_dir=None, media_root=None):
        """hidden=True — запуск сразу в трее (автозапуск, `snipper.pyw --tray`), если значок включён.
        layout_path — раскладка настроек (B23; по умолчанию settings_layout.json рядом с настройками:
        у тестов — своя, пустая). layout_edit=True — конструктор настроек (`snipper.pyw --layout`):
        сразу настройки с ручками ⠿; глобальные клавиши, трей и автозапуск не включаются.
        app_dir — файлы программы (иконка); data_dir — settings.json и logs; media_dir — папки
        «гифки» и «снимки» по умолчанию. Без них всё рядом с программой; у exe — AppData и «Изображения»
        (media_root — «Изображения»: папка программы в нём называется на языке интерфейса)."""
        self.app_dir = app_dir
        self.data_dir = data_dir or app_dir
        self.layout_edit = layout_edit
        self.updater = Updater(self, APP_VERSION)
        self.settings = Settings(settings_path or os.path.join(self.data_dir, "settings.json"),
                                 media_dir or self.data_dir)
        self.media_root = media_root
        # язык (B26) — до регистрации действий: тексты вычисляются при ней. Конструктор — всегда русский
        self._apply_lang("ru" if layout_edit else self.settings["lang"])
        self.root = tk.Tk()
        self.root.withdraw()
        # без консоли (pythonw) ошибки пропадали бы бесследно — пишем их в logs/errors.log
        # (если обработчик ошибок уже подменён, например тестами, — его не трогаем)
        if tk.Tk.report_callback_exception is _DEFAULT_REPORT:
            self.root.report_callback_exception = self._log_exception
        self.root.title(tr(APP_NAME))
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        if not layout_edit:                 # конструктор не трогает GIF запущенной программы
            self.settings.clean_gif_temp()  # временные GIF прошлого запуска (B17)
        self.model = EditorModel(self.settings)
        self.capture = None
        self.rec_border = None
        self.busy = False
        self.view = "empty"
        self.prev_view = "empty"
        self._status = ("", "secondary", (), False)
        self._overlay = None
        self._geom_before_rec = None
        self.rec_hud = None
        self._silent = None
        self._game = None                   # (x, y, w, h) монитора игры на весь экран: снимок и GIF (B38, B39)
        self._snip_editor = False           # снимок идёт в редактор (в игре окно показывается только потом)
        self._auto_job = None               # отложенное автосохранение
        self._auto_version = None           # версия модели, которая уже в буфере
        self._geom_before_settings = None
        self._gif_saving = None
        self.tray = None
        self.in_tray = False                # окно спрятано в трей (крестиком при включённом значке)
        self.hk_queue = queue.Queue()
        # клавиша будит главный поток сразу: виртуальное событие из потока клавиш
        # (tkinter передаёт вызов в главный поток); опрос очереди — запасной путь
        self._wake = lambda: self.root.event_generate("<<GlobalHotkey>>", when="tail")
        self.hotkeys = W.HotkeyService(self.hk_queue, notify=self._wake)
        self.reg = Registry()
        features.register(self, self.reg)
        # раскладка страниц настроек из конструктора (B23): только место и тексты настроек
        self.layout_store = LayoutStore(layout_path or os.path.join(
            os.path.dirname(os.path.abspath(self.settings.path)), LayoutStore.FILE))
        i18n.set_layout_texts((self.layout_store.data or {}).get("en"))
        self.layout_store.apply(self.reg)
        self.layout_editor = LayoutEditor(self.layout_store, self.reg) if layout_edit else None
        window_hooks.append(lambda win, th: W.set_titlebar_dark(win, self.titlebar_dark(th)))
        self._set_icon()
        self.build()
        # пока открыт выпадающий список, рамка главного окна не «мигает» неактивной
        self.keep_active = W.KeepFrameActive(self.root)
        C.Popup.hooks["open"].append(lambda pop: self.keep_active.acquire())
        C.Popup.screen_bounds = lambda x, y: (lambda m: (m[0], m[1], m[0] + m[2], m[1] + m[3]))(
            W.monitor_at(x, y, work=True))   # всплывающие окна — в пределах монитора под кнопкой
        C.Popup.hooks["close"].append(lambda pop: self.keep_active.release())
        # модальное окно: живое затемнение и следование за окном прямо из его оконной процедуры
        self.frame_watch = W.FrameWatch(self.root)
        W.FrameWatch.on_error = self._log_exception   # ошибки из оконной процедуры — в журнал
        self.root.bind("<Map>", self._restored, add="+")
        Modal.host = W.OverlayHost(self.frame_watch)
        C.Tooltip.screen_rect = W.widget_rect   # подсказки — по настоящему положению виджета
        self.settings.listeners.append(self._setting_changed)
        self.reg.bind_hotkeys(self.root, self.active_surfaces)
        if not layout_edit:                 # клавиши держит запущенная программа
            self.apply_global_hotkeys()
        self.root.bind("<<GlobalHotkey>>", lambda e: self._drain_hotkeys())
        self.root.after(self.th.timing("hotkey_poll"), self._poll_hotkeys)
        self.apply_tray()
        self.show_view("empty")
        self._center_top()
        if hidden and self.tray:            # автозапуск: окно не показываем, программа — в трее
            self.in_tray = True
        else:
            self.root.deiconify()
        if layout_edit:
            self.toggle_settings()

    # ================================================================ сборка
    def make_theme(self):
        sc = self.settings["ui_scale"]
        scale = W.system_scale() if sc == "auto" else int(sc) / 100
        return Theme(self.settings["theme"], self.settings["accent"], scale)

    def build(self):
        """(Пере)собрать интерфейс целиком из реестра. Состояние (снимок, запись) сохраняется."""
        for w in self.root.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        th = self.th = self.make_theme()
        self.root.configure(bg=th.c("bg"))
        self.apply_titlebar()
        shell = self.shell = AppShell(self.root, th)
        shell.pack(fill="both", expand=True)

        self.header = HudToolbar(shell.header, th, self.reg.for_surface("header"))
        self.header.pack(fill="x")

        # пустое состояние
        empty = C.Frame(shell.main, th, "bg", pad=8)
        acts = []
        for a in self.reg.list_for("empty"):
            acts.append(lambda p, a=a: C.Button(p, th, a.title, icon=a.icon, size="lg",
                                               variant="primary" if a.kind == "primary" else "secondary",
                                               tooltip=action_tip(a), hotkey=a.hotkey,
                                               command=a.handler))
        C.EmptyState(empty, th, "image", tr("Снимка пока нет"),
                     tr("Сделайте снимок экрана или запишите область в GIF."), acts,
                     hint=self._hotkey_hint()).pack(expand=True)
        shell.add_view("empty", empty)

        # редактор
        ed = C.Frame(shell.main, th, "surface")
        self.editor_bar = HudToolbar(ed, th, self.reg.for_surface("editor"))
        self.editor_bar.pack(fill="x")
        C.Divider(ed, th).pack(fill="x")
        self.editor_view = EditorView(ed, th, self.model, on_change=self._editor_changed,
                                      on_zoom=lambda z: self.shell.status.set_meta(
                                          tr("Масштаб {} %").format(round(z * 100))))
        self.editor_view.pack(fill="both", expand=True)
        shell.add_view("image", ed)

        # настройки
        self.settings_view = SettingsLayout(shell.main, th, self.reg, self.settings,
                                            page=self.settings["settings_page"],
                                            on_page=lambda p: self.settings.set("settings_page", p),
                                            on_built=self._fit_settings_height, editor=self.layout_editor)
        shell.add_view("settings", self.settings_view)
        if not self.layout_edit:
            self.root.after(self.th.timing("settings_measure"), self._measure_settings)

        self.set_status(*self._status)

    def _apply_lang(self, setting):
        i18n.set_lang(i18n.resolve(setting))
        if self.media_root:                 # «Изображения\Ножницы XX» / «Pictures\ScreenShoterXX»
            self.settings.app_dir = os.path.join(self.media_root, tr(APP_NAME))

    def set_language(self):
        """Смена языка на лету: реестр собирается заново (тексты вычисляются при регистрации),
        раскладка настроек — поверх, интерфейс — перестраивается. Привязки клавиш окна остаются
        от прежнего реестра: их обработчики — те же методы App."""
        self._apply_lang(self.settings["lang"])
        self.reg = Registry()
        features.register(self, self.reg)
        self.layout_store.defaults = None
        self.layout_store.apply(self.reg)
        if self.tray:                       # подсказка и меню значка — на новом языке
            self.tray.close()
            self.tray = None
            self.apply_tray()
        self.rebuild_later()

    def rebuild_later(self):
        self.root.after_idle(self.rebuild)

    def rebuild(self):
        view = self.view
        self.build()
        self.show_view(view, resize=False)

    def _set_icon(self):
        ico = os.path.join(self.app_dir, "иконка", "icon.ico")
        try:
            self.root.iconbitmap(default=ico)
        except tk.TclError:
            from ..ui.icons import icon as get_icon
            th = self.make_theme()
            self._icon = get_icon("app", th.size("app_icon"), th.c("accent"))
            self.root.iconphoto(True, self._icon)

    def _hotkey_hint(self):
        s = self.settings
        parts = []
        if s["hk_snip"]:
            parts.append(tr("{} — снимок").format(s["hk_snip"]))
        if s["hk_quick"]:
            parts.append(tr("{} — снимок без редактора").format(s["hk_quick"]))
        if s["hk_full"]:
            parts.append(tr("{} — весь экран").format(s["hk_full"]))
        if s["hk_full_edit"]:
            parts.append(tr("{} — весь экран с редактором").format(s["hk_full_edit"]))
        if s["hk_gif"]:
            parts.append(tr("{} — запись GIF").format(s["hk_gif"]))
        return "  ·  ".join(parts) + (tr("  (из любой программы)") if parts else "")

    # ================================================================ виды
    def active_surfaces(self):
        extra = {"image": "editor", "empty": "empty"}.get(self.view)
        return {"header"} | ({extra} if extra else set())

    def show_view(self, view, resize=True):
        self.view = view
        self.shell.layout()
        self.shell.show(view)
        title = tr(APP_NAME)
        if view == "image" and self.model.base:
            title += tr(" — снимок {}×{}").format(self.model.base.width, self.model.base.height)
        elif view == "settings":
            title += tr(" — конструктор настроек") if self.layout_edit else tr(" — настройки")
        self.root.title(title)
        C.window_badge(self.root, self.th, f"view:{view}", corner="se")   # режим «номера окон»
        self.header.refresh()
        self.apply_titlebar()
        if view != "image":
            self.shell.status.set_meta("")
        if view == "image":
            self.editor_view.render(reset=resize)
            self.editor_bar.refresh()
        if not resize:
            return
        if view == "image":
            self._size_for_image()
        elif view == "empty":
            self._natural_size()

    # --- журнал ошибок ---
    LOG_LIMIT = 256 * 1024     # байт; при переполнении журнал начинается заново

    def _log_exception(self, exc, val, tb):
        """Ошибка в обработчике интерфейса: записать в logs/errors.log (дата + стек)."""
        import traceback
        text = "".join(traceback.format_exception(exc, val, tb))
        try:
            folder = os.path.join(self.data_dir, "logs")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, "errors.log")
            mode = "w" if os.path.exists(path) and os.path.getsize(path) > self.LOG_LIMIT else "a"
            with open(path, mode, encoding="utf-8") as f:
                f.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S}  вид: {self.view}\n{text}\n")
        except OSError:
            pass

    # --- системный заголовок окна ---
    def titlebar_dark(self, th=None):
        """Тёмный ли заголовок: режим «под тему» + тёмная тема. Режим «всегда светлый» — нет."""
        th = th or self.th
        return self.settings["titlebar"] == "theme" and th.dark_titlebar

    def apply_titlebar(self):
        """Применить заголовок к главному окну. Вызывается после любой смены вида и режима окна:
        Windows сбрасывает тёмную рамку, когда окно становится полупрозрачным (HUD записи)."""
        W.set_titlebar_dark(self.root, self.titlebar_dark())

    def _natural_size(self):
        """Окно по содержимому; ширина — не меньше полной ширины панели (без «Ещё»)."""
        # Окно НЕ переводится в geometry(""): в «естественном» режиме ширина окна следовала бы
        # за перекладкой панели, а панель — за шириной окна (бесконечный цикл, мерцание, падение).
        x, y = self.root.winfo_x(), self.root.winfo_y()
        bar = self.header
        bar.expand()
        self.root.update_idletasks()
        w = max(self.root.winfo_reqwidth(), bar.full_width())
        if self.view == "empty":
            # стартовое окно сразу шириной настроек: вход в них не двигает окно вбок
            w = max(w, self.th.size("settings_window")[0])
        self.root.geometry(f"{w}x{self.root.winfo_reqheight()}+{x}+{y}")

    def _center_top(self):
        self.root.update_idletasks()
        mx, my, mw, mh = W.monitor_under_cursor(work=True)
        self.root.geometry(f"+{mx + (mw - self.root.winfo_reqwidth()) // 2}+{my + mh // 8}")

    def _size_for_image(self):
        self.header.expand()
        self.editor_bar.expand()
        self.root.update_idletasks()
        img = self.model.base
        th = self.th
        mx, my, mw, mh = W.monitor_under_cursor(work=True)
        fill = th.layout("window_fill")
        # нужно: снимок в 100 % + поля холста; рамку окна меряем по факту (шапка, панели, статус)
        pad = 2 * th.sp(4)
        cv = self.editor_view.cv
        chrome_w = max(0, self.root.winfo_width() - cv.winfo_width())
        chrome_h = max(0, self.root.winfo_height() - cv.winfo_height())
        if cv.winfo_width() <= 1:   # окно ещё не показано — оценка по запрошенным размерам
            chrome_w = 0
            chrome_h = (self.shell.header.winfo_reqheight() + self.shell.status.winfo_reqheight()
                        + self.editor_bar.winfo_reqheight() + 3 * th.size("border"))
        min_w = max(self.header.full_width(), self.editor_bar.full_width())
        w = min(max(img.width + pad + chrome_w, min_w), int(mw * fill))
        h = min(img.height + pad + chrome_h, int(mh * fill))
        self.root.geometry(f"{w}x{h}+{mx + (mw - w) // 2}+{my + (mh - h) // 2}")
        ev = self.editor_view
        ev._need_fit = True                     # подогнать, когда холст получит новый размер
        self.root.after(self.th.timing("poll"), ev.fit)

    def toggle_settings(self):
        if self.capture:
            return
        # Правый край окна неподвижен: шестерёнка остаётся под курсором, можно войти в настройки
        # и выйти тем же кликом. Окно расширяется ВЛЕВО и вниз; при выходе — прежний размер.
        if self.view == "settings":
            if self._geom_before_settings:
                self.root.geometry(self._geom_before_settings)
            self.show_view(self.prev_view, resize=False)
        else:
            self.prev_view = self.view
            self.root.update_idletasks()
            self._geom_before_settings = self.root.geometry()
            w, h, x, y = (int(v) for v in re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)",
                                                   self._geom_before_settings).groups())
            need_w, need_h = self.th.size("settings_window")
            if self.layout_edit:                    # ручки ⠿ слева от блоков — строки не переносятся
                need_w += self.th.size("icon") + 2 * self.th.sp(2)
            mx, my, mw, mh = W.monitor_under_cursor(work=True)
            frame = self.root.winfo_rooty() - y     # системный заголовок окна
            new_w = min(max(w, need_w), mw)
            if not self.layout_edit:                # сразу по самой длинной странице: при переходах окно не растёт
                need_h = self.settings_view.tallest(new_w) + h - self.shell.main.winfo_height()
            new_h = min(max(h, need_h), mh - frame)
            new_x = max(mx, x + w - new_w)          # растём влево, но не за край монитора
            new_y = max(my, min(y, my + mh - frame - new_h))   # у нижнего края — подняться
            self.root.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")   # сначала размер, потом содержимое
            self.root.update_idletasks()
            self.show_view("settings", resize=False)    # страница подгонит высоту (on_built)

    def _measure_settings(self):
        """Замер страниц заранее: на первом входе в настройки он стоил бы заметных 0,4 с."""
        if self.idle() and self.view != "settings" and self.settings_view.winfo_exists():
            self.settings_view.tallest(self.th.size("settings_window")[0])

    def _fit_settings_height(self):
        """Страница настроек не влезает по высоте — дорастить окно вниз (до края монитора).
        Ширина не меняется, поэтому строки не перекладываются; всё — до перерисовки окна."""
        if self.view != "settings":
            return
        r, sv = self.root, self.settings_view
        # нужная высота = рамки окна вокруг вида + нужная высота вида; обе из одного снимка
        # размеров, поэтому повторный вызов до применения размера не растит окно дважды
        need = r.winfo_height() - sv.winfo_height() + sv.need_height()
        w, h, x, y = (int(v) for v in re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)",
                                               r.geometry()).groups())
        if need <= h:
            return
        mx, my, mw, mh = W.monitor_at(x + w // 2, y, work=True)
        frame = r.winfo_rooty() - y          # системный заголовок окна
        new_h = min(need, mh - frame)
        new_y = max(my, min(y, my + mh - frame - new_h))   # у нижнего края — подняться
        if new_h != h:
            self.root.geometry(f"{w}x{new_h}+{x}+{new_y}")
            self.root.update_idletasks()

    def _setting_changed(self, key, value):
        """Любая смена настройки — все её контролы в окне показывают новое значение: строка
        настроек сразу, панель — один раз после обработчика (он мог пересобрать интерфейс)."""
        sv = getattr(self, "settings_view", None)
        if sv is not None and sv.winfo_exists():
            sv.sync_row(key)
        if not getattr(self, "_header_sync", None):
            self._header_sync = self.root.after_idle(self._refresh_bars)

    def _refresh_bars(self):
        self._header_sync = None
        for bar in (getattr(self, "header", None), getattr(self, "editor_bar", None)):
            if bar is not None and bar.winfo_exists():
                bar.refresh()

    # ================================================================ статус / уведомления
    def set_status(self, text, tone="secondary", actions=(), busy=False):
        self._status = (text, tone, tuple(actions), busy)
        self.shell.status.set(text, tone, actions, busy)

    def toast(self, text, kind="info", actions=(), sticky=False):
        self.shell.toasts.show(text, kind, actions, sticky)

    def idle(self):
        return not self.busy and self.capture is None

    # ================================================================ глобальные клавиши
    HOTKEY_KEYS = {"hk_snip": "Снимок с редактором", "hk_quick": "Снимок без редактора",
                   "hk_full": "Снимок всего экрана", "hk_full_edit": "Весь экран с редактором",
                   "hk_gif": "Запись GIF"}
    KEYBOARD_PAGE = "ms-settings:easeofaccess-keyboard"

    def apply_global_hotkeys(self, wait=False):
        return self.hotkeys.update({k: self.settings[k] for k in self.HOTKEY_KEYS}, wait=wait,
                                   force=bool(self.settings["hk_force"]))

    def force_changed(self):
        self.apply_global_hotkeys(wait=True)
        self.settings_view.refresh_errors()   # строки сочетаний: «занято» пропало или вернулось
        if self.settings["hk_force"]:
            self.root.after_idle(self.ask_admin)

    def ask_admin(self):
        """Сильный режим включили: спросить про запуск от имени администратора (B44). admin_task — команда, на
        которую создано задание; папку перенесли — команда другая, спрашиваем снова. Любой ответ, кроме согласия
        (и окно, закрытое мимо кнопок), выключает режим: при следующем включении вопрос будет снова."""
        exe, args = W.program_command(self.app_dir)
        cmd = f"{exe} {args}"
        if self.settings["admin_task"] == cmd:
            return
        answer = ask(self.root, self.th, tr("Запускать от имени администратора?"),
                     tr("Программа получит полный доступ к компьютеру, зато сильный режим заработает во всех окнах.\n\n"
                        "Windows спросит разрешение один раз, дальше программа сама будет запускаться "
                        "от имени администратора, без вопросов. Сейчас она перезапустится."),
                     ((tr("Нет"), "ghost", None), (tr("Разрешить"), "danger", True)), icon=None, kind="admin_ask",
                     danger=True)
        h = None
        path = os.path.join(self.data_dir, "admin_task.xml")
        if answer:
            with open(path, "w", encoding="utf-16") as f:
                f.write(W.admin_task_xml(exe, args, self.app_dir))
            h = W.run_elevated("schtasks.exe", W.admin_task_args(path))
        if h:
            self._admin_wait(h, cmd, path)
        else:
            self._force_refused()

    def _force_refused(self):
        self.settings.set("hk_force", False)  # Settings.set сам вернёт ползунок влево
        self.force_changed()

    def _admin_wait(self, h, cmd, path):
        code = W.process_exit(h)
        if code is None:
            self.root.after(self.th.timing("poll"), self._admin_wait, h, cmd, path)
            return
        try:
            os.remove(path)
        except OSError:
            pass
        if code:
            self.toast(tr("Не удалось создать задание Windows: программа работает как обычно"), "error")
            self._force_refused()
            return
        self.settings.set("admin_task", cmd)
        if not W.is_admin():
            self.restart_as_admin()

    def restart_as_admin(self):
        mark = os.path.join(self.data_dir, W.ADMIN_MARK)
        with open(mark, "w", encoding="utf-8") as f:
            f.write("restart")
        if W.admin_task_run():
            self.exit_app()
        else:
            os.remove(mark)
            self.toast(tr("Не удалось создать задание Windows: программа работает как обычно"), "error")

    def show_force(self):
        """Ссылка «второй вариант»: раздел, где лежит сильный режим (его могли переложить в конструкторе)."""
        sv = self.settings_view
        sv.set_page(self.reg.settings["hk_force"].page)
        row = sv.rows.get("hk_force")
        if row is not None and row.control is not None:
            C.focus_auto(row.control)

    def set_global_hotkey(self, key, value):
        """Назначить глобальное сочетание. Если Windows его не приняла — вернуть прежнее
        (рабочее) и текст ошибки для строки настройки; иначе None."""
        if self.layout_edit:                # конструктор: только запомнить (временные настройки)
            self.settings.set(key, value)
            return None
        other = next((k for k in self.HOTKEY_KEYS if k != key and self.settings[k] == value), None)
        if value and other:
            return tr("Уже назначено на «{}»").format(tr(self.HOTKEY_KEYS[other]))
        old = self.settings[key]
        self.settings.set(key, value)
        if self.apply_global_hotkeys(wait=True).get(key) or not value:
            return None
        self.settings.set(key, old)
        self.apply_global_hotkeys(wait=True)
        return self.hotkey_problem(value)

    def hotkey_problem(self, value):
        """Почему Windows не приняла сочетание — для строки настроек. У PrintScreen — ссылка (текст, по клику):
        в Windows 11 его по умолчанию держат «Ножницы» (B34). Вне настроек программа об этом молчит."""
        if value.split("+")[-1] == "Print":
            return tr("PrintScreen занят — как освободить"), self.print_help
        return tr("Сочетание занято другой программой — выберите другое или включите сильный режим"), self.show_force

    def show_changes(self):
        Dialog(self.root, self.th, tr("Что нового"), buttons=((tr("Закрыть"), "primary", None),), kind="changes",
               build=lambda body, dlg: changes_list(body, dlg, self.th, CHANGES)).wait()

    def print_help(self):
        def second(body, dlg):
            C.Link(body, self.th, tr("Второй вариант — сильный режим: программа заберёт клавишу сама"),
                   lambda: dlg.close("force"), role="body", wrap=self.th.size("dialog_min_w")).pack(
                anchor="w", pady=(self.th.sp(4), 0))

        answer = Dialog(self.root, self.th, tr("Как освободить PrintScreen"),
                        text=tr("В Windows 11 эту клавишу забирают встроенные «Ножницы».\n\n"
                                "1. Нажмите «Открыть параметры».\n"
                                "2. В поиске параметров введите Print Screen и откройте найденный пункт.\n"
                                "3. Не нашлось — посмотрите сами. Новые версии Windows 11: Bluetooth и устройства → "
                                "Клавиатура. Старые: Специальные возможности → Клавиатура → «Экранная клавиатура, "
                                "клавиши доступа и экран печати».\n"
                                "4. Выключите переключатель про клавишу Print Screen: название зависит от версии Windows.\n"
                                "5. Перезапустите программу. Не заработало — перезайдите в Windows.\n\n"
                                "Не помогло — её держит другая программа: закройте её или выберите другое сочетание."),
                        buttons=((tr("Закрыть"), "ghost", None), (tr("Открыть параметры"), "primary", True)),
                        icon="info", kind="print_help", build=second).wait()
        if answer == "force":
            self.show_force()
        elif answer:
            W.open_file(self.KEYBOARD_PAGE)

    def _restored(self, e):
        """Свёрнутое окно развернули: показать, когда Tk его нарисует (`FrameWatch.cloak`)."""
        if e.widget is self.root and self.frame_watch.cloaked:
            self.root.after(self.th.timing("restore_settle"), lambda: self.frame_watch.cloak(False))

    def _poll_hotkeys(self):
        if self.frame_watch.cloaked and self.root.state() != "iconic":   # окно не должно остаться скрытым
            self.root.after(self.th.timing("restore_settle"), lambda: self.frame_watch.cloak(False))
        self._drain_hotkeys()
        # в трее — реже: основной путь и так событие из потока, опрос лишь запасной
        self.root.after(self.th.timing("hotkey_poll_tray" if self.in_tray else "hotkey_poll"), self._poll_hotkeys)

    def _drain_hotkeys(self):
        try:
            while True:
                k = self.hk_queue.get_nowait()
                if isinstance(k, tuple):        # сильный режим поймал сочетание для поля записи
                    field = self.root.focus_get()
                    if isinstance(field, C.HotkeyField):
                        field.take([name for _, _, name in field.MODS if k[1] & W.MOD[name]], k[2])
                elif k == "show":               # значок в трее: двойной клик / повторный запуск
                    self.show_window()
                elif k == "exit":               # значок в трее: «Выход»
                    self.exit_app()
                elif k == "hk_snip":
                    self.new_snip(hotkey=True)
                elif k == "hk_quick":
                    self.new_snip(quiet=True)
                elif k == "hk_full":            # монитор под курсором, без оверлея; mode не меняется
                    self.new_snip(quiet=True, full=True)
                elif k == "hk_full_edit":
                    self.new_snip(hotkey=True, full=True)
                elif k == "hk_gif":
                    self.rec_stop() if self.capture else self.start_gif(source="hotkey")
        except queue.Empty:
            pass

    # ================================================================ режим, тема
    def set_mode(self, v):
        self.settings["mode"] = v
        self.header.refresh()

    def toggle_theme(self):
        self.settings["theme"] = "light" if self.settings["theme"] == "dark" else "dark"
        self.rebuild()

    # ================================================================ тихий режим (глобальная клавиша)
    def _begin_silent(self, quiet):
        """quiet — сочетание без редактора (B41) или GIF по клавише (B37): окно программы остаётся как было
        (свёрнутым, за другими окнами…), не поднимается и не забирает фокус. Если окно открыто,
        на время захвата оно только исключается из снимка/записи."""
        self._silent = None
        if not quiet:
            return False
        self._silent = {"fg": W.foreground(), "state": self.root.state(), "game": bool(self._game)}
        if self._silent["state"] in ("normal", "zoomed"):
            W.set_capture_excluded(self.root, True)
        return True

    def _end_silent(self, cancelled=False, focus=True):
        """Вернуть всё как было: снять исключение из захвата, отдать фокус прежнему окну (focus).
        state "hidden" — редактор спрятан под оверлеем, исключение уже снято (снимать его со
        скрытого окна нельзя — «призрак»); отменили снимок — окно возвращается."""
        sil, self._silent = self._silent, None
        if not sil:
            return
        if sil["state"] in ("normal", "zoomed"):
            W.set_capture_excluded(self.root, False)
        if not focus:
            return
        if sil["state"] == "hidden":
            if cancelled:
                self.root.deiconify()
                self.apply_titlebar()
            elif sil["fg"] == W.hwnd_of(self.root):
                return                            # фокус был у окна, которое уходит в трей
        W.set_foreground(sil["fg"], restore=sil["game"])

    # ================================================================ снимок
    def new_snip(self, quiet=False, full=False, hotkey=False):
        """Новый снимок. full=True — сразу весь монитор под курсором, без оверлея и меню режима
        (глобальное сочетание «Снимок всего экрана», B18); настройку mode не меняет.
        quiet=True — без редактора, только буфер обмена и папка (B41).
        hotkey=True (и quiet) — глобальным сочетанием: возможна игра на весь экран (B39). Она
        сворачивается от любого чужого окна, поэтому своё окно не показывается и не прячется:
        выбор области на стоп-кадре, потом игра возвращается; редактор — только в конце."""
        if not self.idle():
            return
        self._game = W.fullscreen_window(exclude=(W.hwnd_of(self.root),)) if quiet or hotkey else None
        self._snip_editor = not quiet
        silent = self._begin_silent(quiet or bool(self._game))
        if silent and not self._game and self.tray and self.view == "image" and self._silent["state"] in ("normal", "zoomed"):
            self._hide_after_overlay = True       # открытый редактор уходит в трей: уже под оверлеем
        # в тихом режиме снимок в редактор не попадает, поэтому пометки текущего снимка не трогаем
        if not silent and not self._resolve_unsaved(tr("Сохранить пометки на текущем снимке?")):
            return
        self.busy = True
        # задержки снимка больше нет (её место в шапке занял «Длительность GIF»):
        # ключ "delay" в settings.json сохранён, но не используется
        self.root.after(0 if silent else self._hide_for_capture(), lambda: self._do_snip(full))

    def _hide_for_capture(self):
        """Убрать главное окно из будущего снимка экрана. Возвращает, сколько мс ждать.

        Быстрый путь (Windows 10 2004+): окно мгновенно исключается из захвата и прячется
        позже — уже под оверлеем. Иначе — спрятать и переждать анимацию скрытия Windows."""
        if self.root.state() == "withdrawn":          # окно в трее — прятать нечего, ждать нечего
            self._hide_after_overlay = False
            return 0
        if self.root.state() == "normal" and W.set_capture_excluded(self.root, True):
            self._hide_after_overlay = True
            return 0
        self._hide_after_overlay = False
        self.root.withdraw()
        return self.th.timing("hide_anim")

    def _after_overlay_shown(self):
        """Оверлей на экране: теперь можно спрятать главное окно (под оверлеем это не видно)."""
        if getattr(self, "_hide_after_overlay", False):
            self._hide_after_overlay = False
            # Порядок важен: сначала снять исключение из захвата, потом прятать. Если спрятать
            # исключённое окно и снять исключение уже со скрытого, DWM показывает его «призрак» —
            # белое окно с заголовком поверх всего (снимок для оверлея к этому моменту уже сделан).
            W.set_capture_excluded(self.root, False)
            if self._silent:
                self._silent["state"] = "hidden"
            # Прятать — чуть позже, когда DWM точно применил снятие исключения (иначе гонка →
            # призрак). Не DwmFlush: он блокирует программу до следующего кадра — бывает ~1 с.
            # Оверлей закрывает экран, так что пауза не видна.
            self.root.after(self.th.timing("dwm_settle"), self._hide_if_still_capturing)

    def _hide_if_still_capturing(self):
        """Отложенное скрытие: только если съёмка ещё идёт (её могли успеть отменить)."""
        if self.busy or self.capture is not None:
            self.root.withdraw()

    def _overlay_modes(self, gif):
        from .features import MODES
        hk = {m: str(i + 1) for i, (m, _, _) in enumerate(MODES)}
        return [(m, ic, tr(t), hk[m]) for m, t, ic in MODES if not (gif and m == "free")]

    def _open_overlay(self, gif, on_done):
        vx, vy, vw, vh = W.virtual_screen()
        windows = W.list_windows(exclude=(W.hwnd_of(self.root),))   # своё окно не выбирается
        shot = W.grab(vx, vy, vw, vh)
        if self._game:
            self._game_shot(shot, vx, vy)
        mode = self.settings["mode"]
        if gif and mode == "free":
            mode = "rect"
        modes = self._overlay_modes(gif)
        prefix = "GIF: " if gif else ""
        hint = prefix + tr("{}  ·  1–{} режим  ·  Esc отмена").format(tr(SNIP_HINTS[mode]), len(modes))

        def on_mode(m):
            # выбор на оверлее — только для этого снимка: настройку mode меняет лишь «Режим» в шапке
            # (B18: выбранный на оверлее «Весь экран» запоминался, и оверлей потом не появлялся)
            if m == "full":
                mx, my, mw, mh = W.monitor_under_cursor()
                self._overlay.finish({"box": (mx - vx, my - vy, mx - vx + mw, my - vy + mh), "poly": None})
            else:
                self._overlay.hud.hint = prefix + tr("{}  ·  1–{} режим  ·  Esc отмена").format(
                    tr(SNIP_HINTS[m]), len(modes))
                self._overlay.hud.place_top_center(*self._hud_pos(vx, vy))

        self._overlay = Overlay(self.root, self.th, shot, (vx, vy), mode, windows, modes, on_mode,
                                lambda res: on_done(res, shot, vx, vy), hint)
        self._overlay.hold = bool(self._game)
        self._overlay.bind("<Map>", lambda e: self.root.after_idle(self._after_overlay_shown), add="+")

    def _hud_pos(self, vx, vy):
        mx, my, mw, _ = W.monitor_under_cursor()
        return mx - vx + mw // 2, my - vy + self.th.sp(4)

    def _do_snip(self, full=False):
        if full or self.settings["mode"] == "full":
            img = self._game and self._game_frame()   # игра на весь экран без оверлея не сворачивается
            if not img:
                img = W.grab(*(self._game or W.monitor_under_cursor()))
            self._after_overlay_shown()
            self.busy = False
            self._snip_ready(img)
            return

        def cut(res, shot):
            l, t, r, b = res["box"]
            img = shot.crop((l, t, r, b))
            if res["poly"]:
                mask = Image.new("L", img.size, 0)
                ImageDraw.Draw(mask).polygon([(px - l, py - t) for px, py in res["poly"]], fill=255)
                bg = Image.new("RGB", img.size, ANNOTATION["freeform_bg"])
                bg.paste(img, mask=mask)
                img = bg
            return img

        def done(res, shot, vx, vy):
            ov, self._overlay = self._overlay, None

            def finish():
                self.busy = False
                if res:
                    self._snip_ready(cut(res, shot))
                    return
                self._game = None
                if self._silent:
                    self._end_silent(cancelled=True)
                elif not self.in_tray:          # отменили снимок из трея — окно остаётся в трее
                    self.root.deiconify()
                self.header.refresh()

            if not self._game:
                finish()
            elif res and self._snip_editor:     # дальше редактор: игре незачем возвращаться
                ov.destroy()
                finish()
            else:                               # оверлей закрывается ПОСЛЕ возврата игры: без пустого экрана
                def back():
                    ov.destroy()
                    finish()
                W.set_foreground(self._silent["fg"], restore=True)
                self._when_game_back(self._silent["fg"], back)

        self._open_overlay(False, done)

    def _snip_ready(self, img):
        """Снимок готов. В игре окно не показывалось и при снимке с редактором: теперь можно."""
        if self._silent and self._snip_editor:
            self._end_silent(focus=False)
            if self.in_tray:
                self.show_window()              # вопрос «Сохранить пометки?» — при видимом окне
            if not self._resolve_unsaved(tr("Сохранить пометки на текущем снимке?")):
                self._game = None
                return
        self._game = None
        self._deliver_snip(img)

    def _deliver_snip(self, img):
        """Всегда — в буфер обмена (и в папку, если включено). Обычно ещё и в редактор; в тихом
        режиме окно не показывается."""
        copied, path, err = self._keep_snip(img)
        note = self._snip_note(copied, path, err)
        if not self._silent:
            self.load_image(img, note)
            if path:
                self.set_status(f"{img.width} × {img.height} px" + note, "success",
                                [(tr("Открыть"), lambda: W.open_file(path)), (tr("Папка"), lambda: W.open_in_explorer(path))])
            if err:
                self.toast(tr("Не удалось сохранить снимок в папку: {}").format(err), "error", sticky=True)
            return
        self.set_status(tr("Снимок {} × {} px").format(img.width, img.height) + note,
                        "success" if copied else "warning")
        sil = self._silent                        # из-под игры окно не прячем заранее, только теперь
        hidden = sil["state"] == "hidden" or (sil["game"] and self.tray and self.view == "image"
                                              and sil["state"] in ("normal", "zoomed"))
        self._end_silent()
        if hidden:
            self.root.after(self.th.timing("dwm_settle"), self._editor_to_tray)

    def _editor_to_tray(self):
        """Спрятать окно редактора в трей — с паузой после снятия исключения из захвата (иначе
        DWM оставляет «призрак») и без анимации Windows: без оверлея (весь экран) она видна.
        Без значка не звать: крестик тогда закрывает программу."""
        if self.tray and self.idle() and self.view == "image":
            W.set_transitions(self.root, False)
            self.close_window()
            self.root.after(self.th.timing("hide_anim"), lambda: W.set_transitions(self.root, True))

    def load_image(self, img, note=""):
        self._autosave_now()
        self.model.load(img)
        self._auto_version = self.model.version
        self.show_view("image")
        self.in_tray = False
        self.root.deiconify()
        self.set_status(f"{img.width} × {img.height} px" + note)
        self.root.lift()
        self.root.focus_force()

    def _keep_snip(self, img):
        """Новый снимок (любым способом): ВСЕГДА в буфер обмена; при snip_save — ещё и в папку
        (PNG, «Снимок_номер_дата_время»). Возвращает (скопирован, путь или None, ошибка или None)."""
        s = self.settings
        copied = not s["clipboard_off"] and W.copy_image(img)
        path = err = None
        if s["snip_save"]:
            folder = s.snip_dir()
            num = s.next_snip_number()
            path = os.path.join(folder, s.file_name("Снимок", num, "png", datetime.now()))
            try:
                os.makedirs(folder, exist_ok=True)
                img.save(path, "PNG")
                s["snip_counter"] = num
            except Exception as ex:
                path, err = None, str(ex)
        return copied, path, err

    def _snip_note(self, copied, path, err):
        parts = [tr("скопирован в буфер обмена") if copied else tr("буфер обмена занят")]
        if path:
            parts.append(tr("сохранён: {}").format(os.path.basename(path)))
        if err:
            parts.append(tr("не удалось сохранить в папку"))
        return "  ·  " + "  ·  ".join(parts)

    # --- редактор ---
    def _editor_changed(self):
        self.editor_bar.refresh()
        self._autosave_later()

    def _autosave_later(self):
        """Правка в редакторе: через паузу готовая картинка — в буфер обмена. Новая правка откладывает
        сохранение: на каждый мазок картинку не собираем."""
        if self._auto_job:
            self.root.after_cancel(self._auto_job)
            self._auto_job = None
        if self.settings["snip_autosave"] and self.model.base and self.model.version != self._auto_version:
            self._auto_job = self.root.after(self.th.timing("autosave"), self._autosave)

    def _autosave(self):
        """Только сама картинка снимка (`export`): нарисованное за краем в неё не входит (B7)."""
        self._auto_job = None
        if self.editor_view.live:             # ещё рисуют: сохранит отпускание кнопки
            return
        s, version = self.settings, self.model.version
        if not s["snip_autosave"] or not self.model.base or version == self._auto_version:
            return
        # в буфере уже всё: спрашивать «Сохранить?» при закрытии незачем. Файл снимка в папке не меняется
        if not s["clipboard_off"] and W.copy_image(self.model.export()):
            self.model.saved = True
            self._auto_version = version      # буфер занят — сохранит следующая правка, вопрос останется

    def _autosave_now(self):
        """Снимок сейчас сменится или закроется: не потерять правку, ждущую паузы."""
        if self._auto_job:
            self.root.after_cancel(self._auto_job)
            self._autosave()

    def set_tool(self, tool):
        self.model.tool = tool
        self.editor_view.refresh_cursor()
        self.editor_bar.refresh()

    ERASER_MODES = (("brush", "Стирать область", "eraser"), ("stroke", "Удалить объект целиком", "eraser_object"))

    def set_eraser_option(self, v):
        """Режим ластика: "brush" — область, "stroke" — объект целиком. Выбирает ластик."""
        self.settings.set("eraser_mode", v)
        self.set_tool("eraser")

    def eraser_menu(self, button):
        """Удержание кнопки «Ластик»: под ней — режимы (текущий отмечен)."""
        items = [(v, t, "check" if v == self.settings["eraser_mode"] else ic, None)
                 for v, t, ic in self.ERASER_MODES]
        items = [(v, tr(t), ic, x) for v, t, ic, x in items]
        C.menu(button, self.th, items, self.set_eraser_option, kind="eraser")

    def eraser_key(self, hotkey):
        """E — ластик; если он уже выбран (или Shift+E) — сменить режим."""
        if hotkey == "E" and self.model.tool != "eraser":
            self.set_tool("eraser")
            return
        self.set_eraser_option("stroke" if self.settings["eraser_mode"] == "brush" else "brush")
        self.set_status(tr("Ластик: ") + tr(next(t for v, t, _ in self.ERASER_MODES
                                             if v == self.settings["eraser_mode"])).lower())

    def quick_values(self, key, defaults):
        """Плашки окошка значения: свои (settings.quick_values[key]) или по умолчанию. Испорченное
        (не тот размер, не числа, повторы) — значения по умолчанию; число плашек всегда как у них."""
        vals = self.settings["quick_values"].get(key) if isinstance(self.settings["quick_values"], dict) else None
        if (not isinstance(vals, list) or len(vals) != len(defaults)
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals)
                or len(set(vals)) != len(vals)):
            return list(defaults)
        return vals

    def set_quick_values(self, key, vals):
        d = dict(self.settings["quick_values"]) if isinstance(self.settings["quick_values"], dict) else {}
        d[key] = list(vals)
        self.settings.set("quick_values", d)          # сохраняется сразу

    def quick_spec(self, spec, key):
        """Спецификация числа с СВОИМИ плашками: читаются при каждом открытии окошка,
        новые значения из окошка сохраняются сразу."""
        lo, hi = spec["min"], spec["max"]
        return {**spec, "quick": lambda: [min(hi, max(lo, v)) for v in self.quick_values(key, spec["quick"])],
                "save_quick": lambda vals: self.set_quick_values(key, vals)}

    def set_tool_param(self, name, v):
        """Размер или прозрачность ВЫБРАННОГО инструмента (у каждого свои; на новые штрихи)."""
        key = self.model.param_key(name)
        if key:
            self.settings.set(key, v)
            self.editor_view.refresh_cursor()     # круг области ластика — нового размера
            self.editor_bar.refresh()

    def undo(self):
        if self.model.undo():
            self.editor_view.render()
            self._editor_changed()

    def redo(self):
        if self.model.redo():
            self.editor_view.render()
            self._editor_changed()

    def clear_marks(self):
        if self.model.clear():
            self.editor_view.render()
            self._editor_changed()

    def pick_color(self, key, field=None):
        title = tr("Палитра цветов (Перо)") if key == "pen_color" else tr("Палитра цветов (Маркер)")
        c = ColorPicker(self.root, self.th, self.settings, self.settings[key], title).ask()
        if c:
            self.settings[key] = c
            self.set_tool("pen" if key == "pen_color" else "marker")

    def save_image(self):
        if not self.model.base:
            return False
        s = self.settings
        name = tr("Снимок") + "_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = filedialog.asksaveasfilename(
            parent=self.root, title=tr("Сохранить как"), initialdir=s["last_dir"], initialfile=name,
            defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"),
                                                ("GIF", "*.gif"), ("BMP", "*.bmp")])
        if not path:
            return False
        img = self.model.export()
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".jpg", ".jpeg"):
                img.save(path, "JPEG", quality=95)
            elif ext in (".gif", ".bmp"):
                img.save(path, ext[1:].upper())
            else:
                if ext != ".png":
                    path += ".png"
                img.save(path, "PNG", optimize=True)
        except Exception as ex:
            self.toast(tr("Не удалось сохранить: {}").format(ex), "error", sticky=True)
            return False
        s["last_dir"] = os.path.dirname(path)
        self.model.saved = True
        self.set_status(tr("Снимок сохранён: {}").format(path), "success",
                        [(tr("Открыть"), lambda: W.open_file(path)), (tr("Папка"), lambda: W.open_in_explorer(path))])
        return True

    def copy_image(self):
        if not self.model.base:
            return
        if W.copy_image(self.model.export()):
            self.toast(tr("Снимок скопирован в буфер обмена"), "success")
        else:
            self.toast(tr("Буфер обмена занят другой программой"), "error")

    # ================================================================ GIF
    def browse_gif_dir(self):
        d = filedialog.askdirectory(parent=self.root, initialdir=self.settings.gif_dir(),
                                    title=tr("Папка для сохранения GIF"))
        return os.path.normpath(d) if d else None

    def browse_snip_dir(self):
        d = filedialog.askdirectory(parent=self.root, initialdir=self.settings.snip_dir(),
                                    title=tr("Папка для сохранения снимков"))
        return os.path.normpath(d) if d else None

    def open_snip_dir(self):
        d = self.settings.snip_dir()
        os.makedirs(d, exist_ok=True)
        W.open_in_explorer(d)

    def open_gif_dir(self):
        d = self.settings.gif_dir()
        os.makedirs(d, exist_ok=True)
        W.open_in_explorer(d)

    def start_gif(self, source="window"):
        if not self.idle():
            return
        # игра на весь экран сворачивается, как только другое окно получает фокус: выбор области
        # идёт на её стоп-кадре, потом игра возвращается, а рамки и панели записи нет (B38)
        self._game = W.fullscreen_window(exclude=(W.hwnd_of(self.root),)) if source == "hotkey" else None
        silent = self._begin_silent(source == "hotkey")      # GIF по клавише окно не открывает (B37)
        self.busy = True
        self.prev_view = self.view if self.view in ("empty", "image") else "empty"
        self._geom_before_rec = self.root.geometry()
        self.root.after(0 if silent else self._hide_for_capture(), self._gif_select)

    def _gif_select(self):
        if self.settings["mode"] == "full":
            self._after_overlay_shown()
            if self._game:                    # без оверлея игра даже не сворачивается
                self._gif_begin(*self._game, windows=False)
            else:
                self._gif_begin(*W.monitor_under_cursor())
            return

        def cancel():
            self.busy = False
            self._game = None
            if self._silent:
                self._end_silent()
            elif not self.in_tray:
                self.root.deiconify()
            self.header.refresh()

        def done(res, shot, vx, vy):
            ov, self._overlay = self._overlay, None
            box = None
            if res:
                l, t, r, b = res["box"]
                box = (l + vx, t + vy, r - l, b - t)
            if self._game:                    # оверлей закрывается ПОСЛЕ возврата игры: без пустого экрана
                def back():
                    ov.destroy()
                    self._gif_begin(*box, windows=False) if box else cancel()
                W.set_foreground(self._silent["fg"], restore=True)
                self._when_game_back(self._silent["fg"], back)
            elif box:
                self.root.after(80, lambda: self._gif_begin(*box))
            else:
                cancel()

        self._open_overlay(True, done)

    def _when_game_back(self, hwnd, then, waited=0):
        """Игра свернулась на время выбора области: начать запись, когда она снова на весь экран."""
        th = self.th
        if W.is_ready(hwnd) or waited >= th.timing("game_return"):
            self.root.after(th.timing("game_settle"), then)
            return
        W.set_foreground(hwnd, restore=True)
        self.root.after(th.timing("poll"), lambda: self._when_game_back(hwnd, then, waited + th.timing("poll")))

    def _game_frame(self):
        """Кадр монитора игры: GDI видит её устаревший кадр (B38). None — не вышло."""
        try:
            d = Duplicator(*self._game)
            try:
                return d.grab()
            finally:
                d.close()
        except Exception:
            return None

    def _game_shot(self, shot, vx, vy):
        """Стоп-кадр игры для выбора области. Не вышло — останется кадр GDI."""
        frame = self._game_frame()
        if frame:
            shot.paste(frame, (self._game[0] - vx, self._game[1] - vy))

    def _make_border(self, x, y, w, h):
        th = self.th
        t, g = th.size("rec_border"), 1
        key = TECH["transparent_key"]
        b = tk.Toplevel(self.root)
        b.overrideredirect(True)
        b.attributes("-topmost", True)
        b.configure(bg=th.c("danger-fg"))
        b.attributes("-transparentcolor", key)
        Wd, Hd = w + 2 * (t + g), h + 2 * (t + g)
        b.geometry(f"{Wd}x{Hd}+{x - t - g}+{y - t - g}")
        tk.Frame(b, bg=key).place(x=t, y=t, width=Wd - 2 * t, height=Hd - 2 * t)
        W.set_capture_excluded(b)
        C.window_badge(b, th, "rec_border", corner="nw")
        return b

    def _gif_begin(self, x, y, w, h, windows=True):
        """Запись: рамка вокруг области + стеклянная панель сверху экрана.
        Главное окно спрятано до конца записи; панель и рамка в GIF не попадают.
        windows=False — поверх игры: ни одного своего окна (забрали бы фокус)."""
        s = self.settings
        self.capture = c = GifCapture(x, y, w, h, s["fps"], float(s["gif_scale"]) / 100, s["gif_cursor"],
                                      limit=s["gif_limit"])
        if not windows:
            self.capture.start()
            self._rec_tick()
            return
        self.rec_border = self._make_border(x, y, w, h)
        reserve = self._rec_segments(c, c.max_frames, 0, wide=True)    # ширина под самый длинный текст
        self.rec_hud = RecHud(self.root, self.th, (x, y, w, h), self.reg.list_for("rec"),
                              self._rec_segments(c, 0, 0), reserve, stop_key=s["hk_gif"])
        if self._silent:   # пока идёт запись — фокус у программы, с которой работали
            W.set_foreground(self._silent["fg"])
        self.capture.start()
        self._rec_tick()

    @staticmethod
    def _rec_segments(c, frames, sec, wide=False):
        def mmss(v):           # 7.5 -> "00:07,5": у лимита могут быть десятые
            t = f"{int(v) // 60:02d}:{int(v) % 60:02d}"
            return t + C.num_text(v % 1)[1:] if v % 1 else t
        time_txt = "000:00" if wide else mmss(sec)
        if c.limit:                                  # «прошло / лимит»
            time_txt += " / " + mmss(c.limit)
        return [(time_txt, "title", "strong", "primary"),
                (tr("{} кадр. · {} fps · {}×{}").format(frames, C.num_text(c.fps), c.out_w, c.out_h),
                 "caption", "regular",
                 "secondary")]

    def rec_paused(self):
        return bool(self.capture and self.capture.paused)

    def _rec_tick(self, n=0):
        """Каждые TIMING.poll: проверка конца записи; раз в TIMING.blink — обновление панели."""
        c = self.capture
        if not c or c.stop_flag:
            return
        if c.limit_hit or c.limit_reached:   # память кончилась или вышло время — сохранить как по «Стоп»
            self.rec_stop()
            return
        every = max(1, self.th.timing("blink") // self.th.timing("poll"))
        if n % every == 0 and self.rec_hud:
            self.rec_hud.refresh(self._rec_segments(c, len(c.frames), c.elapsed()), c.paused)
        self.root.after(self.th.timing("poll"), lambda: self._rec_tick(n + 1))

    def rec_pause(self):
        if self.capture:
            c = self.capture
            c.toggle_pause()
            if self.rec_hud:
                self.rec_hud.refresh(self._rec_segments(c, len(c.frames), int(c.elapsed())), c.paused)

    def _end_recording(self):
        cap = self.capture
        self.capture = None
        self._game = None
        for w in (self.rec_border, self.rec_hud):
            if w:
                w.destroy()
        self.rec_border = self.rec_hud = None
        frames, times = cap.stop()
        self.busy = False
        if self._silent:          # окно не показываем — всё остаётся как до нажатия клавиши
            self._end_silent()
            return cap, frames, times
        self.show_view(self.prev_view, resize=False)
        if self._geom_before_rec:
            self.root.geometry(self._geom_before_rec)
        self.in_tray = False                  # итог записи — в окне (как и без трея)
        self._restore_editor()
        self.root.deiconify()
        self.apply_titlebar()
        self.header.refresh()
        self.root.lift()
        return cap, frames, times

    def rec_cancel(self):
        if not self.capture:
            return
        self._end_recording()
        self.set_status(tr("Запись GIF отменена"))

    def rec_stop(self):
        if not self.capture:
            return
        silent = self._silent is not None
        cap, frames, times = self._end_recording()
        if not frames:
            self.set_status(tr("Не записано ни одного кадра"), "warning")
            return
        s = self.settings
        to_folder = bool(s["gif_save"])     # выключено — только в буфер: временный файл (B17)
        folder = s.gif_dir() if to_folder else s.gif_temp_dir()
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as ex:
            self.set_status(tr("Не удалось создать папку {}").format(folder), "danger")
            self.toast(str(ex), "error", sticky=True)
            return
        num = s.next_gif_number()
        s["gif_counter"] = num
        path = os.path.join(folder, s.file_name("Гифка", num, "gif", datetime.now()))
        durs = cap.durations(times, len(frames))
        note = tr("  (достигнут лимит памяти)") if cap.limit_hit else ""
        self.set_status(tr("Сохранение GIF №{} — {} кадров…").format(num, len(frames)) + note, busy=True)
        result = {}
        if not to_folder:
            s.clean_gif_temp()                # во временной папке — только последняя запись
        th = self._gif_saving = save_gif_async(path, frames, durs, lambda err: result.update(err=err))

        def poll():
            if th.is_alive():
                self.root.after(self.th.timing("poll"), poll)
                return
            frames.clear()
            if result.get("err"):
                self.set_status(tr("Не удалось сохранить GIF"), "danger")
                self.toast(tr("Ошибка сохранения GIF: {}").format(result["err"]), "error", sticky=True)
                return
            self._gif_saved(path, num, sum(durs) / 1000, silent, to_folder)
        poll()

    def _gif_saved(self, path, num, seconds, silent=False, to_folder=True):
        try:
            size = os.path.getsize(path) / 1024 / 1024
        except OSError:
            size = 0
        # GIF ВСЕГДА кладётся в буфер как файл — вставляется анимированным (отключить нельзя).
        # В папке — сам этот файл, без второй копии; иначе — временный файл (B17)
        copied = W.copy_file(path)
        if not to_folder:
            self.set_status(tr("GIF №{}  ·  {:.1f} с  ·  {:.2f} МБ  ·  ").format(num, seconds, size)
                            + (tr("в буфере обмена") if copied else tr("буфер обмена занят")),
                            "success" if copied else "danger", [(tr("Открыть"), lambda: W.open_file(path))])
            if not silent:
                if copied:
                    self.toast(tr("GIF скопирован в буфер обмена"), "success")
                else:
                    self.toast(tr("Буфер обмена занят другой программой"), "error")
            return
        acts = [(tr("Открыть"), lambda: W.open_file(path)), (tr("Папка"), lambda: W.open_in_explorer(path))]
        self.set_status(tr("GIF №{}: {}  ·  {:.1f} с  ·  {:.2f} МБ  ·  ").format(
                        num, os.path.basename(path), seconds, size)
                        + (tr("в буфере обмена") if copied else tr("буфер обмена занят")), "success", acts)
        if not silent:            # в тихом режиме уведомлений в окне нет
            self.toast(tr("GIF №{} сохранён").format(num) + (tr(" и скопирован в буфер") if copied
                                                 else tr(" (буфер обмена занят другой программой)")),
                       "success", acts)

    # ================================================================ трей и автозапуск (B19)
    TRAY_TIP = "{} — двойной клик, чтобы открыть"

    def apply_tray(self):
        """Значок в трее — по настройке tray (включить / убрать). В конструкторе — никогда."""
        if self.layout_edit:
            return
        if self.settings["tray"] and not self.tray:
            self.tray = W.TrayIcon(os.path.join(self.app_dir, "иконка", "icon.ico"),
                                   tr(self.TRAY_TIP).format(tr(APP_NAME)),
                                   self.hk_queue, notify=self._wake, can_show=self.idle)
        elif not self.settings["tray"] and self.tray:
            self.tray.close()
            self.tray = None

    def tray_changed(self):
        self.apply_tray()
        self.sync_autostart(explicit=True)    # без трея автозапуска нет: запись убирается
        self.settings_view.refresh_rows()     # «Автозапуск» доступен только при значке
        self.root.update_idletasks()
        self._fit_settings_height()           # подпись могла стать длиннее — без полосы прокрутки

    def autostart_changed(self):
        if not self.sync_autostart(explicit=True):
            self.toast(tr("Не удалось записать автозапуск в реестр Windows"), "error")

    def autostart_command(self):
        """Команда автозапуска: pythonw (без консоли) + snipper.pyw + --tray (сразу в трей); пути в кавычках.
        У exe — сам exe + --tray."""
        exe, args = W.program_command(self.app_dir)
        return " ".join(p for p in (f'"{exe}"', args, "--tray") if p)

    def sync_autostart(self, explicit=False):
        """Запись автозапуска в реестре — по настройкам. Нужна (трей + автозапуск) — проверить путь
        и обновить (папку программы могли перенести). Не нужна — убрать; при запуске программы
        (explicit=False) — только если запись ведёт на ЭТУ копию: чужую копию не трогаем.
        Вызывается из snipper.pyw и при смене настроек — не из конструктора: тесты создают App
        на временных настройках и не должны трогать автозапуск пользователя."""
        if self.layout_edit:                # конструктор работает на временных настройках
            return True
        cmd = self.autostart_command()
        cur = W.autostart_get()
        if self.settings["tray"] and self.settings["autostart"]:
            return cur == cmd or W.autostart_set(cmd)
        script = os.path.normcase(sys.executable if getattr(sys, "frozen", False)
                                  else os.path.join(self.app_dir, "snipper.pyw"))
        if cur is not None and (explicit or script in os.path.normcase(cur)):
            W.autostart_remove()
        return True

    def close_window(self):
        """Крестик окна: при значке в трее окно прячется (программа и глобальные сочетания
        работают дальше, пометки не теряются); без значка — выход, как раньше."""
        if self.tray and not self.capture:
            self.in_tray = True
            W.hand_off_focus()
            self.root.withdraw()              # не destroy: показать снова — двойной клик по значку
            self.editor_view.release()
        else:
            self.quit()

    def _restore_editor(self):
        if self.view == "image":
            self.editor_view.restore()

    def show_window(self):
        """Показать окно из трея (двойной клик по значку, повторный запуск ярлыка)."""
        if not self.idle():                   # идёт снимок или запись — окно покажется само
            return
        self.in_tray = False
        self._restore_editor()
        self.root.deiconify()                 # и спрятанное, и свёрнутое
        self.apply_titlebar()
        self.root.lift()
        self.root.focus_force()

    def exit_app(self):
        """«Выход» в меню значка — завершить программу полностью. Идёт запись GIF — сначала
        остановить и сохранить её (как «Стоп»), выйти после сохранения."""
        if self.capture:
            self.rec_stop()
        if self._gif_saving is not None and self._gif_saving.is_alive():
            self.root.after(self.th.timing("poll"), self.exit_app)
            return
        if self.in_tray and self.model.has_unsaved_marks() and not self.settings["copy_on_close"]:
            self.show_window()                # вопрос «Сохранить пометки?» — при видимом окне
        self.quit()

    # ================================================================ выход
    def quit(self):
        if self.capture:
            self.rec_cancel()
            return
        if not self._resolve_unsaved(tr("Сохранить пометки на снимке перед выходом?")):
            return
        if self.tray:                         # иначе в трее остаётся «призрак» значка
            self.tray.close()
            self.tray = None
        W.hand_off_focus()
        self.root.destroy()

    def _resolve_unsaved(self, question):
        """Что делать с несохранёнными пометками. True — можно продолжать (закрыть / новый снимок).
        Настройка «copy_on_close»: молча скопировать снимок с пометками в буфер обмена."""
        self._autosave_now()
        if not self.model.has_unsaved_marks():
            return True
        if self.settings["copy_on_close"]:
            if not self.settings["clipboard_off"]:
                W.copy_image(self.model.export())
            self.model.saved = True
            return True
        ans = ask(self.root, self.th, tr(APP_NAME), question,
                  ((tr("Отмена"), "ghost", None), (tr("Не сохранять"), "secondary", "no"),
                   (tr("Сохранить"), "primary", "yes")))
        return ans is not None and (ans != "yes" or self.save_image())

    def run(self):
        self.root.mainloop()
