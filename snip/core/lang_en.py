# -*- coding: utf-8 -*-
"""Английский перевод интерфейса (B26). Ключ — русский текст из кода (tr("…")) или из
settings_layout.json, значение — английский. Нет ключа — показывается русский текст.
Новый текст в коде — добавить сюда строку (проверка: tools/stress/lang_check.py)."""

EN = {
    # ---- название, файлы и папки
    "Ножницы XX": "ScreenShoterXX",
    "Снимок": "Screenshot",
    "Гифка": "GIF",
    "дата_время": "date_time",
    "гифки": "GIFs",
    "снимки": "Screenshots",
    "«снимки»": "\"Screenshots\"",
    "«гифки»": "\"GIFs\"",

    # ---- шапка и панели
    "Создать": "New",
    "Новый снимок экрана": "New screenshot",
    "Режим": "Mode",
    "Режим выделения": "Selection mode",
    "Произвольная форма": "Free-form",
    "Прямоугольник": "Rectangle",
    "Окно": "Window",
    "Весь экран": "Full screen",
    "Длительность записи GIF": "GIF recording length",
    "Пауза не считается; стоп — в любой момент": "Pauses don't count; stop at any time",
    "{} с": "{} s",
    "Без лимита": "No limit",
    "Курсор в GIF": "Cursor in GIF",
    "выключен": "off",
    "включён": "on",
    "Запись GIF": "Record GIF",
    "Записать область экрана в GIF": "Record a screen area as a GIF",
    "Открыть папку GIF": "Open GIF folder",
    "Сменить тему": "Switch theme",
    "Светлая тема": "Light theme",
    "Тёмная тема": "Dark theme",
    "Настройки": "Settings",
    "Ещё": "More",
    "Сохранить": "Save",
    "Сохранить снимок как…": "Save screenshot as…",
    "Копировать": "Copy",
    "Копировать в буфер обмена": "Copy to clipboard",
    "Перо": "Pen",
    "Цвет пера": "Pen color",
    "Маркер": "Highlighter",
    "Цвет маркера": "Highlighter color",
    "Ластик": "Eraser",
    "Стирает только пометки. Удерживайте для смены режима": "Erases only your marks. Hold to change the mode",
    "Стирать область": "Erase area",
    "Удалить объект целиком": "Delete whole object",
    "Ластик: ": "Eraser: ",
    "Размер": "Size",
    "Перо, Маркер, Ластик": "Pen, Highlighter, Eraser",
    "Недоступно: Ластик удаляет объект целиком": "Unavailable: the Eraser deletes whole objects",
    "Непрозрачность": "Opacity",
    "Перо и Маркер": "Pen and Highlighter",
    "Недоступно: выбран Ластик": "Unavailable: the Eraser is selected",
    "Отменить": "Undo",
    "Повторить": "Redo",
    "Вернуть отменённое": "Bring back what was undone",
    "Очистить пометки": "Clear marks",
    "По размеру окна": "Fit to window",
    "Масштаб 100 %": "Zoom 100 %",
    "Приблизить": "Zoom in",
    "Отдалить": "Zoom out",
    "Масштаб {} %": "Zoom {} %",
    "Пауза": "Pause",
    "Продолжить": "Resume",
    "Стоп и сохранить": "Stop and save",
    "Отменить запись": "Cancel recording",

    # ---- группы клавиш («Клавиши в окне»)
    "Общие": "General",
    "Файл": "File",
    "Правка": "Edit",
    "Инструменты": "Tools",
    "Вид": "View",
    "Прочее": "Other",
    "Пробел": "Space",

    # ---- главное окно, статус, уведомления
    "Снимка пока нет": "No screenshot yet",
    "Сделайте снимок экрана или запишите область в GIF.": "Take a screenshot or record an area as a GIF.",
    "{} — снимок": "{} — screenshot",
    "{} — весь экран": "{} — full screen",
    "{} — весь экран с редактором": "{} — full screen with editor",
    "Весь экран с редактором": "Full screen with editor",
    "Весь экран с редактором — везде": "Full screen with editor — anywhere",
    "Монитор под курсором — снимок сразу открывается в редакторе": "The monitor under the cursor opens straight in the editor",
    "{} — запись GIF": "{} — record GIF",
    "  (из любой программы)": "  (from any app)",
    " — снимок {}×{}": " — screenshot {}×{}",
    " — конструктор настроек": " — settings designer",
    " — настройки": " — settings",
    "Обведите область": "Draw around an area",
    "Выделите область": "Select an area",
    "Щёлкните по окну": "Click a window",
    "{}  ·  1–{} режим  ·  Esc отмена": "{}  ·  1–{} mode  ·  Esc cancel",
    "Новый снимок": "New screenshot",
    "Снимок всего экрана": "Full-screen screenshot",
    "Уже назначено на «{}»": "Already assigned to \"{}\"",
    "Сочетание занято другой программой — выберите другое или включите сильный режим": "This shortcut is taken by another app — choose another or turn on force mode",
    "Сильный режим сочетаний": "Force shortcuts mode",
    "Занятые сочетания программа забирает себе, пока запущена: другие программы их не получат. Антивирус может принять это за кейлоггер.\n": "While it runs, the app takes busy shortcuts for itself and other apps don't get them. An antivirus may mistake this for a keylogger.\n",
    "Программа запущена от имени администратора: сочетания работают во всех окнах": "The app runs as administrator: shortcuts work in all windows",
    "Режим работает от имени администратора: при включении Windows спросит разрешение": "This mode runs as administrator: Windows will ask for permission when you turn it on",
    "Второй вариант — сильный режим: программа заберёт клавишу сама": "Second option — force mode: the app will take the key itself",
    "Запускать от имени администратора?": "Run as administrator?",
    "Программа получит полный доступ к компьютеру, зато сильный режим заработает во всех окнах.\n\nWindows спросит разрешение один раз, дальше программа сама будет запускаться от имени администратора, без вопросов. Сейчас она перезапустится.": "The app will get full access to your computer, but force mode will work in all windows.\n\nWindows will ask for permission once. After that the app will run as administrator on its own, with no prompts. It will restart now.",
    "Разрешить": "Allow",
    "Нет": "No",
    "Не удалось создать задание Windows: программа работает как обычно": "Couldn't create the Windows task: the app keeps working as usual",
    "PrintScreen занят — как освободить": "PrintScreen is taken — how to free it",
    "Как освободить PrintScreen": "How to free PrintScreen",
    "Что нового": "What's new",
    "Список изменений": "Changelog",
    "Что менялось от версии к версии": "What changed from version to version",
    "Игры на весь экран": "Fullscreen games",
    "Снимки и GIF работают в полноэкранных играх. Раньше снимок брал устаревшую картинку, "
    "а GIF получался почти без движения.":
        "Screenshots and GIFs work in fullscreen games. Screenshots used to show an outdated picture, "
        "and GIFs had almost no motion.",
    "Снимок всего экрана не сворачивает игру.": "A full screen screenshot no longer minimizes the game.",
    "Снимок области и GIF выбираются на стоп-кадре, потом игра возвращается сама. Esc тоже её возвращает.":
        "The area for a screenshot or GIF is selected on a still frame, then the game comes back by itself. "
        "Esc brings it back too.",
    "Запись GIF поверх игры идёт без рамки и панели, чтобы игра не теряла фокус.":
        "GIF recording over a game runs without the frame and panel, so the game keeps focus.",
    "Сочетания клавиш": "Keyboard shortcuts",
    "Клавиши программы работают в любой раскладке, в том числе в русской.":
        "The program's keys work in any keyboard layout, including Russian.",
    "Вместо настройки «Показывать окно редактора» теперь отдельные сочетания: снимок с редактором "
    "и без него, для области и для всего экрана. Старая настройка переносится сама.":
        "Instead of the \"Show editor window\" setting there are now separate shortcuts: with and without "
        "the editor, for an area and for the full screen. The old setting is carried over automatically.",
    "Если при открытом редакторе сделать снимок без редактора, окно уходит в трей.":
        "If you take a screenshot without the editor while the editor is open, the window goes to the tray.",
    "GIF по сочетанию больше не открывает окно редактора.": "A GIF started by shortcut no longer opens the editor window.",
    "Если сочетание занято другой программой, это видно в настройках. Для PrintScreen в Windows 11 "
    "есть инструкция, как его освободить.":
        "If a shortcut is taken by another program, the settings show it. For PrintScreen in Windows 11 "
        "there are instructions on how to free it.",
    "Сильный режим в разделе «Windows»: занятое сочетание достаётся программе, пока она запущена. "
    "По желанию программа запускается с правами администратора.":
        "Strong mode in the Windows section: a taken shortcut goes to this program while it is running. "
        "Optionally, the program starts with administrator rights.",
    "Прямая линия: щелчок, затем Shift+щелчок. С зажатым Shift линия крутится за курсором, "
    "как стрелка часов, а рядом видны её длина и угол. Работает у пера, маркера и ластика.":
        "Straight line: click, then Shift+click. While Shift is held, the line rotates after the cursor "
        "like a clock hand and shows its length and angle. Works with the pen, marker and eraser.",
    "Правки на снимке сами попадают в буфер обмена. Файл снимка в папке при этом не меняется. "
    "Выключается в настройках.":
        "Edits go to the clipboard by themselves. The screenshot file in the folder does not change. "
        "Can be turned off in the settings.",
    "Ctrl+X в редакторе возвращает отменённое действие, в пару к Ctrl+Z.":
        "Ctrl+X in the editor brings back an undone action, as a pair to Ctrl+Z.",
    "Кисть рисует ровно выбранной толщины: щелчок в 1 px закрашивает 1 пиксель, а не 4.":
        "The brush draws at exactly the chosen size: a 1 px click paints 1 pixel, not 4.",
    "Точка ставится точно под острием курсора, в том числе при увеличении.":
        "A dot lands exactly under the cursor tip, including when zoomed in.",
    "На панели цвет каждого инструмента отделён линией от его названия.":
        "On the toolbar, each tool's color is separated from its name by a line.",
    "Новая вкладка «Редактор»: настройки, которые относятся к рисованию и закрытию снимка.":
        "New Editor tab: settings for drawing and closing a screenshot.",
    "Новая вкладка «О программе»: версия, автор, обновление и этот список.":
        "New About tab: version, author, update and this list.",
    "Подсказки больше не ложатся под курсор.": "Tooltips no longer appear under the cursor.",
    "Окно настроек сразу открывается нужной высоты и не меняет её при переходе по вкладкам.":
        "The settings window opens at the right height and keeps it when switching tabs.",
    "При разворачивании окна больше не мелькают чёрные прямоугольники.":
        "Black rectangles no longer flash when the window is restored.",
    "Скорость и память": "Speed and memory",
    "Повтор штриха огромной кистью стал примерно в 10 раз быстрее.":
        "Redoing a stroke with a huge brush is about 10 times faster.",
    "В трее программа отпускает лишние копии открытого снимка: на снимке 2560×1440 это 70 МБ "
    "вместо 108. Снимок и пометки остаются на месте.":
        "In the tray the program releases extra copies of the open screenshot: 70 MB instead of 108 "
        "for a 2560×1440 screenshot. The screenshot and marks stay in place.",
    "В Windows 11 эту клавишу забирают встроенные «Ножницы».\n\n"
    "1. Нажмите «Открыть параметры».\n"
    "2. В поиске параметров введите Print Screen и откройте найденный пункт.\n"
    "3. Не нашлось — посмотрите сами. Новые версии Windows 11: Bluetooth и устройства → "
    "Клавиатура. Старые: Специальные возможности → Клавиатура → «Экранная клавиатура, "
    "клавиши доступа и экран печати».\n"
    "4. Выключите переключатель про клавишу Print Screen: название зависит от версии Windows.\n"
    "5. Перезапустите программу. Не заработало — перезайдите в Windows.\n\n"
    "Не помогло — её держит другая программа: закройте её или выберите другое сочетание.":
        "In Windows 11 this key is taken by the built-in Snipping Tool.\n\n"
        "1. Click \"Open Settings\".\n"
        "2. Type Print Screen into the Settings search box and open what it finds.\n"
        "3. Nothing found? Look yourself. Newer Windows 11: Bluetooth & devices → Keyboard. "
        "Older: Accessibility → Keyboard → \"On-screen keyboard, access keys, and Print screen\".\n"
        "4. Turn off the switch about the Print Screen key: its name depends on your Windows version.\n"
        "5. Restart this app. Still not working? Sign out of Windows and back in.\n\n"
        "Still not working? Another app holds it: close that app or choose another shortcut.",
    "Открыть параметры": "Open Settings",
    "Снимок {} × {} px": "Screenshot {} × {} px",
    "скопирован в буфер обмена": "copied to clipboard",
    "буфер обмена занят": "clipboard is busy",
    "сохранён: {}": "saved: {}",
    "не удалось сохранить в папку": "could not save to the folder",
    "Не удалось сохранить снимок в папку: {}": "Could not save the screenshot to the folder: {}",
    "Открыть": "Open",
    "Папка": "Folder",
    "Сохранить как": "Save as",
    "Не удалось сохранить: {}": "Could not save: {}",
    "Снимок сохранён: {}": "Screenshot saved: {}",
    "Снимок скопирован в буфер обмена": "Screenshot copied to clipboard",
    "Буфер обмена занят другой программой": "The clipboard is busy with another app",
    "Палитра цветов (Перо)": "Color palette (Pen)",
    "Палитра цветов (Маркер)": "Color palette (Highlighter)",
    "Папка для сохранения GIF": "Folder for saving GIFs",
    "Папка для сохранения снимков": "Folder for saving screenshots",
    "Сохранить пометки на текущем снимке?": "Save the marks on the current screenshot?",
    "Сохранить пометки на снимке перед выходом?": "Save the marks on the screenshot before exiting?",
    "Не сохранять": "Don't save",
    "Отмена": "Cancel",
    "Запись GIF отменена": "GIF recording canceled",
    "Не записано ни одного кадра": "No frames were recorded",
    "{} кадр. · {} fps · {}×{}": "{} frames · {} fps · {}×{}",
    "Не удалось создать папку {}": "Could not create the folder {}",
    "  (достигнут лимит памяти)": "  (memory limit reached)",
    "Сохранение GIF №{} — {} кадров…": "Saving GIF #{} — {} frames…",
    "Не удалось сохранить GIF": "Could not save the GIF",
    "Ошибка сохранения GIF: {}": "GIF saving error: {}",
    "GIF №{}  ·  {:.1f} с  ·  {:.2f} МБ  ·  ": "GIF #{}  ·  {:.1f} s  ·  {:.2f} MB  ·  ",
    "GIF №{}: {}  ·  {:.1f} с  ·  {:.2f} МБ  ·  ": "GIF #{}: {}  ·  {:.1f} s  ·  {:.2f} MB  ·  ",
    "в буфере обмена": "in clipboard",
    "GIF скопирован в буфер обмена": "GIF copied to clipboard",
    "GIF №{} сохранён": "GIF #{} saved",
    " и скопирован в буфер": " and copied to clipboard",
    " (буфер обмена занят другой программой)": " (the clipboard is busy with another app)",
    "{} — двойной клик, чтобы открыть": "{} — double-click to open",
    "Выход": "Exit",
    "Не удалось записать автозапуск в реестр Windows": "Could not write autostart to the Windows registry",
    "Программа уже запущена без номеров окон. Закройте её и запустите «Номера окон» снова.":
        "The app is already running without window numbers. Close it and start \"Window numbers\" again.",
    "Программа уже запущена: сейчас идёт снимок или запись GIF.":
        "The app is already running: a screenshot or GIF recording is in progress.",
    "Пипетка: щёлкните по цвету  ·  стрелки — на пиксель  ·  Enter — взять  ·  Esc — отмена":
        "Eyedropper: click a color  ·  arrows — one pixel  ·  Enter — pick  ·  Esc — cancel",

    # ---- палитра цветов
    "Только Web-цвета": "Web colors only",
    "Вернуть текущий цвет": "Restore the current color",
    "новый": "new",
    "текущий": "current",
    "Добавить в образцы": "Add to swatches",
    "Пипетка": "Eyedropper",
    "Цвет с экрана или со снимка": "Pick a color from the screen or the screenshot",
    "Образцы:": "Swatches:",
    "Образцов пока нет — «Добавить в образцы» сохранит цвет": "No swatches yet — \"Add to swatches\" saves a color",
    "ПКМ или Delete — удалить": "Right-click or Delete — remove",
    "Прямая линия": "Straight line",
    "Shift+щелчок": "Shift+click",
    "Показывать на полосе": "Show on the strip",

    # ---- элементы управления
    "Очистить сочетание": "Clear shortcut",
    "Закрыть": "Close",
    "Нажмите сочетание…": "Press a shortcut…",
    "Не задано": "Not set",
    "Сочетания с Win заняты Windows — выберите другое": "Shortcuts with Win are reserved by Windows — choose another",
    "F12 зарезервирована Windows — выберите другую клавишу": "F12 is reserved by Windows — choose another key",
    "от {} до {}": "from {} to {}",
    ", можно дробное: 2,5": ", decimals allowed: 2.5",
    "  ·  Enter — сохранить, Esc — отмена": "  ·  Enter — save, Esc — cancel",
    "Меньше": "Less",
    "Больше": "More",
    "Своё значение…": "Custom value…",
    "Изменить…": "Change…",
    "Открыть папку": "Open folder",
    "По умолчанию": "Default",
    "выключено": "off",
    "включено": "on",

    # ---- настройки: разделы
    "Снимки": "Screenshots",
    "Редактор": "Editor",
    "О программе": "About",
    "Версия": "Version",
    "Автор": "Author",
    "Обновление": "Update",
    "Обновить приложение": "Update app",
    "Двойной щелчок — переименовать": "Double-click to rename",
    "Работает в программе, скачанной с GitHub. Сейчас она запущена из папки с кодом":
        "Works in the app downloaded from GitHub. This copy is running from the source folder",
    "Программа скачает новую версию с GitHub и перезапустится. Настройки останутся":
        "The app downloads the new version from GitHub and restarts. Your settings stay",
    "Проверяю…": "Checking…",
    "У вас последняя версия": "You have the latest version",
    "Скачиваю {}…": "Downloading {}…",
    "Скачиваю {}: {} %": "Downloading {}: {} %",
    "Устанавливаю {}…": "Installing {}…",
    "Сохранить пометки на снимке перед обновлением?": "Save the marks on the snip before updating?",
    "Обновление отменено": "Update cancelled",
    "Новая версия не запустилась. Программа не изменилась": "The new version didn't start. The app wasn't changed",
    "Не удалось узнать последнюю версию. Попробуйте позже": "Couldn't get the latest version. Try again later",
    "GitHub просит подождать. Попробуйте через час": "GitHub asks to wait. Try again in an hour",
    "Нет связи с GitHub. Проверьте интернет": "Can't reach GitHub. Check your internet connection",
    "Файл скачался с ошибкой. Программа не изменилась": "The download is damaged. The app wasn't changed",
    "Загрузка оборвалась. Программа не изменилась": "The download was interrupted. The app wasn't changed",
    "Нет права записи в папку программы. Скачайте новую версию вручную: {}":
        "No permission to write to the app folder. Download the new version manually: {}",
    "Не удалось заменить файл программы. Программа не изменилась": "Couldn't replace the app file. The app wasn't changed",
    "Внешний вид": "Appearance",
    "Клавиши": "Shortcuts",
    "Работа в фоне": "Background",
    "Быстрые действия": "Quick actions",

    # ---- настройки: снимки
    "Сохранять снимок в папку": "Save screenshots to a folder",
    "Снимок всегда копируется в буфер обмена. Включено — каждый новый снимок ещё и сохраняется в папку (PNG)":
        "A screenshot is always copied to the clipboard. On — every new screenshot is also saved to a folder (PNG)",
    "Папка для снимков": "Screenshot folder",
    "Сюда сохраняется каждый снимок, когда включено «Сохранять снимок в папку»":
        "Every screenshot is saved here when \"Save screenshots to a folder\" is on",
    "Имя файла": "File name",
    "Номер растёт с каждым снимком и не повторяется": "The number grows with every screenshot and never repeats",
    "Автосохранение правок": "Autosave edits",
    "Пометки на снимке сразу попадают в буфер обмена, и при закрытии вопроса нет. Файл в папке не меняется. Выключено — только по кнопке «Копировать»":
        "Marks on a screenshot go straight to the clipboard, so closing doesn't ask. The file in the folder doesn't change. Off — only with the Copy button",
    "Защита от случайного закрытия": "Protection from accidental closing",
    "Закрыли окно или сделали новый снимок, а на снимке есть пометки, — спросить «Сохранить?». "
    "Выключено — снимок с пометками молча копируется в буфер":
        "If you close the window or take a new screenshot while it has marks — ask \"Save?\". "
        "Off — the marked screenshot is silently copied to the clipboard",
    "При закрытии спрашивает, сохранить ли текущую работу в редакторе изображения": "On closing, asks whether to save the current work in the image editor",

    # ---- настройки: GIF
    "Сохранять GIF в папку": "Save GIFs to a folder",
    "GIF всегда копируется в буфер обмена как файл (вставляется анимированным). Выключено — в папку ничего не сохраняется":
        "A GIF is always copied to the clipboard as a file (pastes animated). Off — nothing is saved to a folder",
    "Если выкл, GIF сохраняется только в буфер обмена": "If off, the GIF goes only to the clipboard",
    "Папка для GIF": "GIF folder",
    "Сюда сохраняется каждая запись, когда включено «Сохранять GIF в папку»":
        "Every recording is saved here when \"Save GIFs to a folder\" is on",
    "Номер растёт с каждой записью и не повторяется": "The number grows with every recording and never repeats",
    "Кадров в секунду": "Frames per second",
    "Больше — плавнее, но тяжелее файл": "More — smoother, but a bigger file",
    "Масштаб GIF": "GIF scale",
    "Уменьшение размера кадра": "Reduces the frame size",
    "Уменьшение размера и веса кадра": "Reduces the frame size and file weight",
    "Показывать курсор": "Show cursor",

    # ---- настройки: внешний вид
    "Тема": "Theme",
    "Тёмная": "Dark",
    "Светлая": "Light",
    "Заголовок окна": "Window title bar",
    "Полоска Windows над окном: в цвет темы или всегда светлая": "The Windows bar above the window: theme-colored or always light",
    "Под тему": "Match theme",
    "Всегда светлый": "Always light",
    "Масштаб интерфейса": "Interface scale",
    "«Как в системе» следует масштабу Windows (100–200 %)": "\"As in system\" follows the Windows scale (100–200 %)",
    "Как в системе": "As in system",
    "Язык": "Language",
    "Как в Windows": "As in Windows",

    # ---- настройки: клавиши и Windows
    "Снимок с редактором — везде": "Screenshot with editor — anywhere",
    "Снимок без редактора — везде": "Screenshot without editor — anywhere",
    "Выбранная область — сразу в буфер обмена, окно редактора не открывается":
        "The selected area goes straight to the clipboard, the editor window doesn't open",
    "Скриншот без редактора": "Screenshot without editor",
    "Открывает меню «Создать», снимок сразу в буфер обмена, редактор не открывается":
        "Opens the \"New\" menu, the screenshot goes straight to the clipboard, the editor doesn't open",
    "Снимок с редактором": "Screenshot with editor",
    "Снимок без редактора": "Screenshot without editor",
    "{} — снимок без редактора": "{} — screenshot without editor",
    "Работает, даже когда окно программы не активно": "Works even when the app window is not active",
    "Создать скриншот": "Take a screenshot",
    "Открывает меню «Создать», после снимка — редактор": "Opens the \"New\" menu, then the editor after the screenshot",
    "Скриншот всего экрана": "Full-screen screenshot",
    "Снимает монитор под курсором и сразу открывает снимок в редакторе":
        "Captures the monitor under the cursor and opens it straight in the editor",
    "Снимок всего экрана — везде": "Full-screen screenshot — anywhere",
    "Монитор под курсором — сразу в буфер обмена, без выбора области и редактора": "The monitor under the cursor goes straight to the clipboard, no area selection or editor",
    "Улучшенная версия кнопки PS: копирует снимок активного монитора даже там, где PS не справляется": "An improved PrintScreen: copies the active monitor even where PrintScreen fails",
    "Запись GIF / стоп — везде": "Record GIF / stop — anywhere",
    "Enter — изменить, Backspace или ✕ — отключить": "Enter — change, Backspace or ✕ — turn off",
    "Открывает меню «Запись GIF» для быстрой записи экрана": "Opens the \"Record GIF\" menu for quick screen recording",
    "Клавиши в окне": "Shortcuts in the window",
    "Собираются автоматически из всех действий": "Collected automatically from all actions",
    "Быстрые действия внутри программы, не зависящие от ваших биндов": "Quick actions inside the app, independent of your bindings",
    "Показать все": "Show all",
    "Значок в трее": "Tray icon",
    "Закрытие окна прячет программу в трей — глобальные сочетания работают дальше. "
    "Открыть — двойной клик по значку, выйти — правый клик → «Выход»":
        "Closing the window hides the app in the tray — global shortcuts keep working. "
        "Open — double-click the icon, exit — right-click → \"Exit\"",
    "Фоновая работа в трее": "Run in the tray",
    "После закрытия окна программа остаётся в трее, и сочетания клавиш продолжают работать": "After the window is closed the app stays in the tray, and shortcuts keep working",
    "Автозапуск вместе с Windows": "Start with Windows",
    "Автозапуск в Windows": "Start with Windows",
    "При входе в Windows программа запускается сразу в трее": "On Windows sign-in, the app starts straight in the tray",
    "Доступно, когда включено «{}»": "Available when \"{}\" is on",

    # ---- конструктор настроек (обычно по-русски; на случай английского)
    "Новая группа": "New group",
    "Новый раздел": "New section",
    "Раздел": "Section",
    "Перетащить блок": "Drag the block",
    "Сбросить всё": "Reset all",
    "Вернуть разделы, группы и тексты настроек как в программе? Своя раскладка удалится.":
        "Restore the sections, groups and texts as shipped? Your layout will be deleted.",
    "Сбросить": "Reset",
    "Раздел ниже": "Section down",
    "Раздел выше": "Section up",
    "Удалить раздел": "Delete section",
    "Удалить можно только пустой раздел": "Only an empty section can be deleted",
    "Без группы": "No group",
    "Добавить описание": "Add a description",
    "уже в этом разделе": "already in this section",
    "останется на месте": "stays in place",
    "→ в раздел «{}»": "→ to section \"{}\"",
    "Встанет сюда": "Goes here",
    "Убрать группу (настройки останутся на месте)": "Remove the group (settings stay in place)",
    "Этот текст программа меняет сама — его не изменить": "The app changes this text itself — it can't be edited",
    "Раздел пуст: перетащите сюда настройку за ⠿ (на название раздела слева) или нажмите «Новая группа».":
        "The section is empty: drag a setting here by ⠿ (onto the section name on the left) or press \"New group\".",
    "Конструктор настроек: тащите блок за ⠿ — выше, ниже или на раздел слева. Щёлкните по тексту, чтобы изменить. "
    "Разделы слева тоже можно перетаскивать, двойной щелчок — переименовать. Всё сохраняется сразу.":
        "Settings designer: drag a block by ⠿ — up, down or onto a section on the left. Click a text to edit it. "
        "Sections on the left can be dragged too, double-click to rename. Everything is saved at once.",
    "Тащите, чтобы поменять порядок. Двойной щелчок — переименовать": "Drag to reorder. Double-click to rename",
}
