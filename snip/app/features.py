# -*- coding: utf-8 -*-
"""
ВСЁ, ЧТО УМЕЕТ ПРОГРАММА, — в одном месте, записями реестра.

Чтобы добавить кнопку, инструмент, настройку или вкладку настроек, допишите
запись сюда (см. DESIGN.md, раздел «Как добавить»). Экраны трогать не нужно.
"""

from ..core.i18n import tr
from ..ui.tokens import THEME_NAMES

MODES = [("free", "Произвольная форма", "mode_free"), ("rect", "Прямоугольник", "mode_rect"),
         ("window", "Окно", "mode_window"), ("full", "Весь экран", "mode_full")]
# Числовые поля с ползунком (NumberField): диапазон ползунка lo–hi, в поле можно ввести до max
# quick — плашки быстрых значений в окошке (по умолчанию; свои — двойным кликом), nudge — шаг − / +,
# chip_fmt — подпись плашек и краёв шкалы. Ввод больше max — ставится max, меньше min — min (B16).
GIF_LIMIT = {"lo": 0, "hi": 30, "step": 1, "min": 0, "max": 3600, "fmt": "{} с", "special": {0: "Без лимита"},
             "quick": [0, 5, 10, 30], "nudge": 1, "chip_fmt": "{} с"}
TOOL_SIZE = {"lo": 1, "hi": 30, "step": 1, "min": 1, "max": 3600, "fmt": "{} px",   # минимум кисти — 1
             "quick": [2, 4, 8, 16, 24], "nudge": 1}
TOOL_OPACITY = {"lo": 0, "hi": 100, "step": 1, "min": 0, "max": 100, "fmt": "{} %",
                "quick": [25, 50, 75, 100], "nudge": 5}
FPS = [5, 8, 10, 15, 20, 25, 30]
GIF_SCALES = [100, 75, 50, 33]
UI_SCALES = [("auto", "Как в системе")] + [(v, f"{v} %") for v in (100, 125, 150, 175, 200)]


def tr_spec(spec):
    """Числовая спецификация с подписями на языке интерфейса (fmt, chip_fmt, особые значения)."""
    out = dict(spec)
    for k in ("fmt", "chip_fmt"):
        if k in out:
            out[k] = tr(out[k])
    if "special" in out:
        out["special"] = {v: tr(t) for v, t in out["special"].items()}
    return out


def register(app, reg):
    s = app.settings

    # ---------------------------------------------------------------- шапка
    # keys= — группа в окне «Все клавиши» (для клавиш действий этой группы)
    reg.group("capture", "header", order=10, keys="Общие")
    reg.group("record", "header", order=20, keys="Общие")
    reg.group("more", "header", order=30, keys="Общие")
    reg.group("system", "header", order=90, align="right", keys="Общие")

    reg.action("snip", tr("Создать"), icon="snip", surface="header", group="capture", kind="primary",
               freq=3, value=3, hotkey="Ctrl+N", tooltip=tr("Новый снимок экрана"),
               handler=app.new_snip, enabled=app.idle, also=("empty",))
    reg.action("mode", tr("Режим"), icon="mode_rect", surface="header", group="capture", kind="select",
               freq=3, value=3, order=1, tooltip=tr("Режим выделения"),
               options=[(m, tr(t), ic) for m, t, ic in MODES], get=lambda: s["mode"], set=lambda v: app.set_mode(v))
    reg.action("gif_limit", tr("Длительность записи GIF"), icon="timer", surface="header", group="record",
               kind="number", freq=2, value=3, order=1, number=app.quick_spec(tr_spec(GIF_LIMIT), "gif_limit"),
               tooltip=tr("Пауза не считается; стоп — в любой момент"),
               get=lambda: s["gif_limit"], set=lambda v: s.set("gif_limit", v))
    # та же настройка, что «Запись GIF → Показывать курсор»: кнопка-переключатель между
    # длительностью и «…»
    reg.action("gif_cursor", tr("Курсор в GIF"), icon="cursor", surface="header", group="record",
               kind="toggle", freq=1, value=3, order=2, options=(tr("выключен"), tr("включён")),
               get=lambda: bool(s["gif_cursor"]), set=lambda v: s.set("gif_cursor", v))
    reg.action("gif", tr("Запись GIF"), icon="record", surface="header", group="record",
               freq=3, value=3, hotkey="Ctrl+G", tooltip=tr("Записать область экрана в GIF"),
               handler=app.start_gif, enabled=app.idle, also=("empty",))
    reg.action("open_gifs", tr("Открыть папку GIF"), icon="folder", surface="header", group="more",
               freq=1, value=2, handler=app.open_gif_dir)
    reg.action("theme", tr("Сменить тему"), icon="sun", surface="header", group="more",
               freq=1, value=2, hotkey="Ctrl+Shift+T",
               label=lambda: (tr("Светлая тема"), "sun") if s["theme"] == "dark" else (tr("Тёмная тема"), "moon"),
               handler=app.toggle_theme)
    reg.action("settings", tr("Настройки"), icon="settings", surface="header", group="system", kind="icon",
               freq=2, value=3, hotkey="Ctrl+,", handler=app.toggle_settings)

    # ---------------------------------------------------------------- редактор
    reg.group("file", "editor", order=10, keys="Файл")
    reg.group("tools", "editor", order=20, keys="Инструменты")
    reg.group("history", "editor", order=30, keys="Правка")

    reg.action("save", tr("Сохранить"), icon="save", surface="editor", group="file", freq=3, value=3,
               hotkey="Ctrl+S", tooltip=tr("Сохранить снимок как…"), handler=app.save_image)
    reg.action("copy", tr("Копировать"), icon="copy", surface="editor", group="file", freq=3, value=3,
               order=1, hotkey="Ctrl+C", tooltip=tr("Копировать в буфер обмена"), handler=app.copy_image)

    def tool_get():
        return app.model.tool

    reg.action("pen", tr("Перо"), icon="pen", surface="editor", group="tools", kind="tool", freq=3, value=3,
               order=1, hotkey="P", get=tool_get, set=app.set_tool)
    reg.action("pen_color", tr("Цвет пера"), surface="editor", group="tools", kind="color", freq=3, value=3,
               order=2, get=lambda: s["pen_color"], handler=lambda f: app.pick_color("pen_color", f))
    reg.action("marker", tr("Маркер"), icon="marker", surface="editor", group="tools", kind="tool",
               freq=3, value=3, order=3, hotkey="M", get=tool_get, set=app.set_tool)
    reg.action("marker_color", tr("Цвет маркера"), surface="editor", group="tools", kind="color", freq=3,
               value=3, order=4, get=lambda: s["marker_color"],
               handler=lambda f: app.pick_color("marker_color", f))
    # Ластик: клик — выбрать в текущем режиме; удержание — меню режимов; E — ластик,
    # повторное E или Shift+E — сменить режим. Иконка показывает режим.
    reg.action("eraser", tr("Ластик"), icon="eraser", surface="editor", group="tools", kind="tool",
               freq=3, value=2, order=5, hotkey="E", alt_hotkeys=("Shift+E",),
               tooltip=tr("Стирает только пометки. Удерживайте для смены режима"),
               label=lambda: (tr("Ластик"), "eraser" if s["eraser_mode"] == "brush" else "eraser_object"),
               get=tool_get, set=app.set_tool, hold=app.eraser_menu, key=app.eraser_key)
    # Размер и непрозрачность — у выбранного инструмента свои; нет параметра — поле неактивно

    def size_sample():
        """Образец линии в подсказке размера: толщина, цвет и непрозрачность текущего
        инструмента; у Ластика образца нет."""
        m = app.model
        if m.tool == "eraser" or m.param("size") is None:
            return None
        return {"width": m.param("size"), "color": m.pen_color if m.tool == "pen" else m.marker_color,
                "alpha": m.param("opacity") / 100}

    reg.action("width", tr("Размер"), icon="width", surface="editor", group="tools", kind="number",
               freq=2, value=2, order=6, number=app.quick_spec(TOOL_SIZE, "size"),
               tooltip=lambda: (tr("Перо, Маркер, Ластик") if app.model.param("size") is not None
                                else tr("Недоступно: Ластик удаляет объект целиком")),
               tip_sample=size_sample,
               get=lambda: app.model.param("size"), set=lambda v: app.set_tool_param("size", v),
               enabled=lambda: app.model.param("size") is not None)
    reg.action("opacity", tr("Непрозрачность"), icon="opacity", surface="editor", group="tools", kind="number",
               freq=2, value=2, order=7, number=app.quick_spec(TOOL_OPACITY, "opacity"),
               tooltip=lambda: (tr("Перо и Маркер") if app.model.param("opacity") is not None
                                else tr("Недоступно: выбран Ластик")),
               get=lambda: app.model.param("opacity"), set=lambda v: app.set_tool_param("opacity", v),
               enabled=lambda: app.model.param("opacity") is not None)
    reg.action("undo", tr("Отменить"), icon="undo", surface="editor", group="history", freq=3, value=2,
               show_label=False, hotkey="Ctrl+Z", handler=app.undo,
               enabled=lambda: bool(app.model.history))
    reg.action("redo", tr("Повторить"), icon="redo", surface="editor", group="history", freq=2, value=2,
               order=1, show_label=False, hotkey="Ctrl+Y", alt_hotkeys=("Ctrl+Shift+Z",),
               tooltip=tr("Вернуть отменённое"), handler=app.redo, enabled=lambda: bool(app.model.redo_stack))
    reg.action("clear", tr("Очистить пометки"), icon="trash", surface="editor", group="history",
               freq=1, value=2, handler=app.clear_marks, enabled=lambda: bool(app.model.strokes))

    # масштаб: колесо мыши — основной способ, эти пункты — в «Ещё» и на клавишах
    reg.group("view", "editor", order=40, keys="Вид")
    ev = lambda: app.editor_view
    reg.action("zoom_fit", tr("По размеру окна"), icon="scale", surface="editor", group="view",
               freq=1, value=2, hotkey="Ctrl+0", handler=lambda: ev().fit())
    reg.action("zoom_100", tr("Масштаб 100 %"), icon="image", surface="editor", group="view",
               freq=1, value=2, order=1, hotkey="Ctrl+1", handler=lambda: ev().zoom_to(1.0))
    # Ctrl+= / Ctrl+- — шаг в 2 «деления» колеса
    reg.action("zoom_in", tr("Приблизить"), icon="plus", surface="editor", group="view",
               freq=1, value=2, order=2, hotkey="Ctrl+=", handler=lambda: ev().zoom_by(2))
    reg.action("zoom_out", tr("Отдалить"), icon="minus", surface="editor", group="view",
               freq=1, value=2, order=3, hotkey="Ctrl+-", handler=lambda: ev().zoom_by(-2))

    # ---------------------------------------------------------------- запись (HUD)
    reg.group("rec", "rec", order=10)
    # Панель записи — отдельное стеклянное окно без фокуса (не отбирает его у других программ),
    # поэтому локальных клавиш нет; остановить запись можно глобальной клавишей (настройка hk_gif).
    reg.action("rec_pause", tr("Пауза"), icon="pause", surface="rec", group="rec", freq=3, value=3,
               label=lambda: (tr("Продолжить"), "play") if app.rec_paused() else (tr("Пауза"), "pause"),
               handler=app.rec_pause)
    reg.action("rec_stop", tr("Стоп и сохранить"), icon="stop", surface="rec", group="rec", kind="danger",
               freq=3, value=3, order=1, handler=app.rec_stop)
    reg.action("rec_cancel", tr("Отменить запись"), icon="close", surface="rec", group="rec", kind="icon",
               freq=1, value=3, order=2, handler=app.rec_cancel)

    # ---------------------------------------------------------------- настройки
    reg.page("capture", tr("Снимки"), icon="snip", order=10)
    reg.page("gif", tr("Запись GIF"), icon="film", order=20)
    reg.page("appearance", tr("Внешний вид"), icon="palette", order=30)
    reg.page("hotkeys", tr("Клавиши"), icon="keyboard", order=40)

    # каждый новый снимок всегда копируется в буфер обмена (настройки «Копировать снимок в буфер» нет)
    reg.setting("snip_save", tr("Сохранять снимок в папку"), "capture", kind="toggle", order=0, default=False,
                description=tr("Снимок всегда копируется в буфер обмена. Включено — каждый новый снимок "
                            "ещё и сохраняется в папку (PNG)"))
    reg.setting("snip_dir", tr("Папка для снимков"), "capture", kind="path", order=1,
                description=tr("Сюда сохраняется каждый снимок, когда включено «Сохранять снимок в папку»"),
                extra={"display": s.snip_dir, "on_browse": app.browse_snip_dir,
                       "on_open": app.open_snip_dir, "on_reset": lambda: s.set("snip_dir", ""),
                       "reset_text": tr("«снимки»")})
    reg.setting("snip_name", tr("Имя файла"), "capture", kind="info", order=2,
                description=tr("Номер растёт с каждым снимком и не повторяется"),
                text=lambda: s.file_name("Снимок", s.next_snip_number(), "png"))
    # в settings.json — copy_on_close (молча копировать пометки), в окне — наоборот: «защита» = вопрос
    reg.setting("copy_on_close", tr("Защита от случайного закрытия"), "capture", kind="toggle", order=3,
                default=True, extra={"invert": True},
                description=tr("Закрыли окно или сделали новый снимок, а на снимке есть пометки, — "
                            "спросить «Сохранить?». Выключено — снимок с пометками молча копируется в буфер"))

    reg.setting("gif_save", tr("Сохранять GIF в папку"), "gif", kind="toggle", order=0, default=False,
                description=tr("GIF всегда копируется в буфер обмена как файл (вставляется анимированным). "
                            "Выключено — в папку ничего не сохраняется"))
    reg.setting("gif_dir", tr("Папка для GIF"), "gif", kind="path", order=1,
                description=tr("Сюда сохраняется каждая запись, когда включено «Сохранять GIF в папку»"),
                extra={"display": s.gif_dir, "on_browse": app.browse_gif_dir,
                       "on_open": app.open_gif_dir, "on_reset": lambda: s.set("gif_dir", ""),
                       "reset_text": tr("«гифки»")})
    reg.setting("gif_name", tr("Имя файла"), "gif", kind="info", order=2,
                description=tr("Номер растёт с каждой записью и не повторяется"),
                text=lambda: s.file_name("Гифка", s.next_gif_number(), "gif"))
    reg.setting("fps", tr("Кадров в секунду"), "gif", kind="select", order=3,
                description=tr("Больше — плавнее, но тяжелее файл"),
                options=[(f, str(f)) for f in FPS], extra={"custom": {"lo": 1, "hi": 60, "fmt": "{}"}})
    reg.setting("gif_scale", tr("Масштаб GIF"), "gif", kind="select", order=4,
                description=tr("Уменьшение размера кадра"),
                options=[(v, f"{v} %") for v in GIF_SCALES], extra={"custom": {"lo": 10, "hi": 100, "fmt": "{} %"}})
    reg.setting("gif_cursor", tr("Показывать курсор"), "gif", kind="toggle", order=5,
                extra={"title_icon": "cursor"})      # значок — как у той же кнопки на панели

    reg.setting("theme", tr("Тема"), "appearance", kind="select", order=1,
                options=[(k, tr(v)) for k, v in THEME_NAMES.items()], on_change=lambda v: app.rebuild_later())
    reg.setting("titlebar", tr("Заголовок окна"), "appearance", kind="select", order=3,
                description=tr("Полоска Windows над окном: в цвет темы или всегда светлая"),
                options=[("theme", tr("Под тему")), ("light", tr("Всегда светлый"))],
                on_change=lambda v: app.apply_titlebar())
    reg.setting("ui_scale", tr("Масштаб интерфейса"), "appearance", kind="select", order=2,
                description=tr("«Как в системе» следует масштабу Windows (100–200 %)"),
                options=[(v, tr(t)) for v, t in UI_SCALES], on_change=lambda v: app.rebuild_later())
    # язык (B26): "" — как в Windows (русская — русский, любая другая — английский); названия языков не переводятся
    reg.setting("lang", tr("Язык"), "appearance", kind="select", order=4, default="",
                options=[("", tr("Как в Windows")), ("ru", "Русский"), ("en", "English")],
                on_change=lambda v: app.set_language())

    def hk_error(key):
        return lambda: None if app.hotkeys.status.get(key, True) else \
            tr("Сочетание занято другой программой — выберите другое")

    # в settings.json — hotkey_silent (не показывать окно), в окне — наоборот: «показывать»
    reg.setting("hotkey_silent", tr("Показывать окно редактора после клавиши"), "hotkeys", kind="toggle", order=0,
                default=False, extra={"invert": True},
                description=tr("Снимок и GIF по глобальной клавише открываются в окне программы. Выключено — "
                            "окно остаётся как было (например, свёрнутым), результат — в буфере обмена"))
    reg.setting("hk_snip", tr("Новый снимок — везде"), "hotkeys", kind="hotkey", order=1,
                description=tr("Работает, даже когда окно программы не активно"),
                extra={"on_capture": app.hotkeys.pause, "error": hk_error("hk_snip"),
                       "apply": lambda v: app.set_global_hotkey("hk_snip", v)})
    reg.setting("hk_full", tr("Снимок всего экрана — везде"), "hotkeys", kind="hotkey", order=2,
                description=tr("Монитор под курсором — сразу в редактор, без выбора области"),
                extra={"on_capture": app.hotkeys.pause, "error": hk_error("hk_full"),
                       "apply": lambda v: app.set_global_hotkey("hk_full", v)})
    reg.setting("hk_gif", tr("Запись GIF / стоп — везде"), "hotkeys", kind="hotkey", order=3,
                description=tr("Enter — изменить, Backspace или ✕ — отключить"),
                extra={"on_capture": app.hotkeys.pause, "error": hk_error("hk_gif"),
                       "apply": lambda v: app.set_global_hotkey("hk_gif", v)})
    reg.setting("shortcuts", tr("Клавиши в окне"), "hotkeys", kind="shortcuts", order=4,
                description=tr("Собираются автоматически из всех действий"),
                extra={"button": tr("Показать все")})
    # работа в фоне (B19): рядом с глобальными сочетаниями — без трея они живут, только пока открыто окно
    reg.setting("tray", tr("Значок в трее"), "hotkeys", kind="toggle", order=5, default=False,
                section=tr("Работа в фоне"),
                description=tr("Закрытие окна прячет программу в трей — глобальные сочетания работают дальше. "
                            "Открыть — двойной клик по значку, выйти — правый клик → «Выход»"),
                on_change=lambda v: app.tray_changed())
    reg.setting("autostart", tr("Автозапуск вместе с Windows"), "hotkeys", kind="toggle", order=6, default=False,
                section=tr("Работа в фоне"),
                description=lambda st: (tr("При входе в Windows программа запускается сразу в трее")
                                        if st["tray"] else
                                        # название — как у настройки трея сейчас (его меняют в конструкторе)
                                        tr("Доступно, когда включено «{}»").format(reg.settings["tray"].title)),
                extra={"enabled": lambda: bool(s["tray"])},
                on_change=lambda v: app.autostart_changed())
