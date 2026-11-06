import sys
import os
import platform
import subprocess
import time
import shutil
import threading
from pathlib import Path
from PyQt6.QtCore import Qt, QDir, QUrl, QTimer, QByteArray
from PyQt6.QtGui import QIcon, QAction, QKeySequence, QFileSystemModel, QDesktopServices, QPixmap, QColor, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QPlainTextEdit,
    QFileDialog, QMessageBox, QPushButton, QTreeView,
    QDockWidget, QMenu, QInputDialog, QStackedWidget,
    QGraphicsColorizeEffect, QLabel
)
import codeview # My beloved codeviewer
import task # For debugging
import util # Whatever this even is
import terminal # sudo rm -rf /* --yes-preserve-root
import git
import languages
import shapes
import extensions
import settings
import motion
import skin
import prefs
import extpanel
import palette
import themes

BASE_DIR = Path(__file__).resolve().parent

RPC = None

def _connect_discord():
    global RPC
    try:
        from pypresence import Presence
        client_id = "1487828344480464957"
        if RPC is not None:
            try:
                RPC.close()
            except Exception:
                pass
            RPC = None
        for pipe_num in range(10):
            try:
                client = Presence(client_id, pipe=pipe_num)
                client.connect()
            except Exception:
                continue
            client.update(
                details="Inside the editor",
                start=time.time(),
                large_image="image",
                large_text="Antimatter",
            )
            RPC = client
            return
        print("Discord RPC Error: no Discord client found")
    except Exception as e:
        print(f"Discord RPC Error: {e}")

def discord():
    threading.Thread(target=_connect_discord, daemon=True).start()

class AntimatterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        settings.load()
        themes.load_settings()
        self._load_font_files()
        self.setObjectName("Comical")
        self.setWindowTitle("Comical Antimatter 2026")
        self.resize(1050, 650)
        
        self.copied_path = None
        self._closing = False
        self.setDockNestingEnabled(True)

        self.setStyleSheet(skin.main_qss(themes.chrome()))

        icon_path = str(BASE_DIR / "AppIcon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.tabs_data = {}

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.central_layout = QVBoxLayout(central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)

        # Stacked Widget to toggle between Welcome Screen and Editor Tabs
        self.stack = QStackedWidget()
        self.central_layout.addWidget(self.stack)

        # Welcome Screen Widget
        self.welcome_widget = QWidget()
        self.welcome_widget.setStyleSheet(f"background-color: {themes.chrome()['window']};")
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setContentsMargins(0, 0, 0, 20)

        logo_label = QLabel()
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(130, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            effect = QGraphicsColorizeEffect(logo_label)
            effect.setColor(QColor("#363636"))
            effect.setStrength(0)
            logo_label.setGraphicsEffect(effect)
        logo_label.setStyleSheet("background: transparent;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel("Welcome to Antimatter")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: white; font-family: 'Consolas', 'Cantarell'; font-size: 30px; font-weight: bold; background: transparent;")

        self.welcome_title = title_label
        center_container = QWidget()
        center_container.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center_container)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(12)
        center_layout.addWidget(logo_label)
        center_layout.addWidget(title_label)

        welcome_layout.addStretch()
        welcome_layout.addWidget(center_container)
        welcome_layout.addStretch()

        footer_label = QLabel("Version 1.7 - Alpha")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #8a79a3; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        self.welcome_footer = footer_label
        footer_label2 = QLabel("This project is open-source and licensed under the MIT license.")
        footer_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label2.setStyleSheet("color: white; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        self.welcome_footer2 = footer_label2
        welcome_layout.addWidget(footer_label)
        welcome_layout.addWidget(footer_label2)

        self.stack.addWidget(self.welcome_widget)

        # File System Viewer
        self.file_model = QFileSystemModel()
        root_path = str(Path.home())
        self.file_model.setRootPath(root_path)

        self.tree = QTreeView()
        self.tree.setModel(self.file_model)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(True)
        self.tree.setRootIndex(self.file_model.index(root_path))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_tree_context_menu)

        for col in range(1, 4):
            self.tree.setColumnHidden(col, True)

        self.tree.header().hide()
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)

        # File Dock Sidebar
        self.sidebar_dock = QDockWidget("File Manager", self)
        self.sidebar_dock.setWidget(self.tree)
        self.sidebar_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable | 
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.sidebar_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        side = Qt.DockWidgetArea.RightDockWidgetArea if settings.get("sidebar_position") == "right" else Qt.DockWidgetArea.LeftDockWidgetArea
        self.addDockWidget(side, self.sidebar_dock)
        self.sidebar_dock.dockLocationChanged.connect(self._on_dock_moved)
        self._sidebar_toggle_action = QAction("File Manager", self)
        self._sidebar_toggle_action.setCheckable(True)
        self._sidebar_toggle_action.setChecked(settings.get("sidebar_visible"))
        self._sidebar_toggle_action.triggered.connect(lambda: self.toggle_sidebar())
        self.sidebar_dock.visibilityChanged.connect(self._on_sidebar_visibility)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(settings.save)

        # Tab bar
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_by_index)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet(skin.tabs_qss(themes.chrome()))
        self.stack.addWidget(self.tabs)

        # Live Terminal Widget Integration
        self.terminal_container = QWidget()
        term_layout = QVBoxLayout(self.terminal_container)
        term_layout.setContentsMargins(5, 5, 5, 5)
        
        self.terminal_widget = terminal.AntimatterTerminal(self)
        term_layout.addWidget(self.terminal_widget)

        self.terminal_container.hide()
        self.central_layout.addWidget(self.terminal_container)

        self.sidebar_was_visible = True

        self._setup_statusbar()

        self.extensions = extensions.ExtensionManager(self)

        self._setup_menubar()
        self._setup_shortcuts()
        self.extensions.load_all()
        themes.restore()
        self.apply_theme()
        settings.observe(self._on_setting_changed)

        geometry = settings.get("window_geometry")
        if geometry:
            self.restoreGeometry(QByteArray.fromHex(geometry.encode()))
        if not settings.get("sidebar_visible"):
            self.sidebar_dock.hide()
        else:
            QTimer.singleShot(0, lambda: self.resizeDocks([self.sidebar_dock], [settings.get("sidebar_width")], Qt.Orientation.Horizontal))

        discord()

    def _setup_statusbar(self):
        bar = self.statusBar()
        bar.setSizeGripEnabled(False)
        bar.setStyleSheet(skin.statusbar_qss(themes.chrome()))
        self.status_pos = QLabel("")
        self.status_lang = QLabel("")
        self.status_enc = QLabel("")
        for label in (self.status_pos, self.status_lang, self.status_enc):
            bar.addPermanentWidget(label)
            label.hide()

    def _update_status(self):
        editor = self.get_current_editor()
        labels = (self.status_pos, self.status_lang, self.status_enc)
        if editor is None:
            for label in labels:
                label.hide()
            return
        cursor = editor.text.textCursor()
        data = self.tabs_data[editor]
        self.status_pos.setText(f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}")
        self.status_lang.setText(languages.language_name(data["path"]))
        self.status_enc.setText(f"{data['encoding'].upper().replace('-SIG', ' BOM')}  {'CRLF' if data['newline'] == chr(13) + chr(10) else 'LF'}")
        for label in labels:
            label.show()

    def apply_theme(self):
        theme = themes.get()
        c = themes.chrome(theme)
        self.setStyleSheet(skin.main_qss(c))
        self.menuBar().setStyleSheet(skin.menubar_qss(c))
        self.statusBar().setStyleSheet(skin.statusbar_qss(c))
        self.tabs.setStyleSheet(skin.tabs_qss(c))
        self.welcome_widget.setStyleSheet(f"background-color: {c['window']};")
        self.welcome_title.setStyleSheet(f"color: {c['text']}; font-family: 'Consolas', 'Cantarell'; font-size: 30px; font-weight: bold; background: transparent;")
        self.welcome_footer.setStyleSheet(f"color: {c['accent_hover']}; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        self.welcome_footer2.setStyleSheet(f"color: {c['text']}; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        self.terminal_widget.apply_theme(c)
        shapes.apply_chrome()
        self._style_tab_buttons()
        for editor in self.tabs_data:
            editor.apply_theme(theme)

    def _style_tab_buttons(self):
        qss = skin.close_button_qss(themes.chrome())
        bar = self.tabs.tabBar()
        for index in range(self.tabs.count()):
            button = bar.tabButton(index, bar.ButtonPosition.RightSide)
            if button is not None:
                button.setStyleSheet(qss)

    def _load_font_files(self):
        for path in settings.get("font_files"):
            self.register_font_file(path)

    def register_font_file(self, path):
        font_id = QFontDatabase.addApplicationFont(path)
        return QFontDatabase.applicationFontFamilies(font_id) if font_id != -1 else []

    def apply_settings(self):
        for editor in self.tabs_data:
            editor.text.apply_settings()
        self.terminal_widget.apply_theme(themes.chrome())

    def _on_setting_changed(self, key, value):
        if key == "sidebar_position":
            self._move_sidebar("right" if value == "right" else "left")
        elif key == "sidebar_visible":
            if bool(value) != self.sidebar_dock.isVisible():
                self.toggle_sidebar(bool(value))
        elif key in ("font_family", "font_size", "tab_size", "word_wrap", "highlight_current_line", "smooth_scrolling") or key is None:
            self.apply_settings()
            if key is None:
                self._move_sidebar(settings.get("sidebar_position"))

    def _move_sidebar(self, position):
        area = Qt.DockWidgetArea.RightDockWidgetArea if position == "right" else Qt.DockWidgetArea.LeftDockWidgetArea
        if self.dockWidgetArea(self.sidebar_dock) != area:
            self.addDockWidget(area, self.sidebar_dock)
            self.sidebar_dock.show()
            QTimer.singleShot(0, lambda: self.resizeDocks([self.sidebar_dock], [settings.get("sidebar_width")], Qt.Orientation.Horizontal))
            motion.fade_in(self.sidebar_dock, 260)

    def _on_dock_moved(self, area):
        position = "right" if area == Qt.DockWidgetArea.RightDockWidgetArea else "left"
        settings.set("sidebar_position", position)

    def _on_sidebar_visibility(self, visible):
        if not self.isVisible() or self._closing:
            return
        self._sidebar_toggle_action.setChecked(visible)
        settings.set("sidebar_visible", visible)

    def _on_zoom(self, size):
        settings.set("font_size", size, persist=False)
        self._save_timer.start()
        self.apply_settings()

    def show_preferences(self):
        dialog = prefs.PreferencesDialog(self)
        dialog.exec()

    def choose_theme(self):
        items = [{"title": name} for name in themes.names()]
        self.quick_pick(items, "Select a color theme", self._set_theme)

    def _set_theme(self, entry):
        themes.set_current(entry["title"])
        self.apply_theme()

    def quick_pick(self, items, placeholder, callback):
        picker = palette.QuickPick(self, items, placeholder, callback)
        picker.popup()

    def builtin_commands(self):
        return [
            ("File: New File", self.new_file, "Ctrl+N"),
            ("File: Open File", self.open_file, "Ctrl+O"),
            ("File: Open Folder", self.open_project_folder, ""),
            ("File: Save", self.save_file, "Ctrl+S"),
            ("File: Save As", self.save_file_as, "Ctrl+Shift+S"),
            ("File: Close Tab", self.close_current_tab, "Ctrl+W"),
            ("View: Toggle Terminal", self.toggle_terminal, "Ctrl+T"),
            ("View: Toggle Sidebar", self.toggle_sidebar, "Ctrl+B"),
            ("View: Color Theme", self.choose_theme, "Ctrl+K Ctrl+T"),
            ("Preferences: Open Settings", self.show_preferences, "Ctrl+,"),
            ("Preferences: Move Sidebar to the Left", lambda: settings.set("sidebar_position", "left"), ""),
            ("Preferences: Move Sidebar to the Right", lambda: settings.set("sidebar_position", "right"), ""),
            ("Preferences: Toggle Animations", lambda: settings.set("animations", not settings.get("animations")), ""),
            ("Preferences: Toggle Word Wrap", lambda: settings.set("word_wrap", not settings.get("word_wrap")), ""),
            ("Task: Run", self.Drun, "F5"),
            ("Task: Find Issues", self.issues, "Ctrl+I"),
            ("Task: Build Project", task.compile, "Ctrl+F5"),
            ("Git: Add All Files", git.add, ""),
            ("Git: Commit", git.commit, ""),
            ("Git: Push", git.push, ""),
            ("Extensions: Manage Extensions", self.show_extensions_panel, "Ctrl+Shift+X"),
            ("Extensions: Install From File", self.install_extension_dialog, ""),
            ("Extensions: Reload Extensions", self.extensions.reload_all, ""),
        ]

    def show_palette(self):
        items = [{"title": t, "key": k, "callable": fn} for t, fn, k in self.builtin_commands()]
        items += self.extensions.palette_items()
        items.sort(key=lambda i: i["title"].lower())
        self.quick_pick(items, "Type a command", self._run_palette_entry)

    def _run_palette_entry(self, entry):
        if "callable" in entry:
            entry["callable"]()
        else:
            self.extensions.execute(entry["command"])

    def show_extensions_panel(self):
        dialog = extpanel.ExtensionsDialog(self.extensions, self)
        dialog.exec()

    def install_extension_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Install extension", "", "Extension packages (*.amext *.zip);;All files (*)")
        if not path:
            return
        reply = QMessageBox.question(
            self, "Install extension",
            "Extensions can run any code on your computer. Only install extensions from sources you trust.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            ext_id = self.extensions.install(path)
            QMessageBox.information(self, "Install extension", f"Installed {ext_id}")
        except Exception as e:
            QMessageBox.critical(self, "Install extension", f"Could not install the extension:\n{e}")

    def _show_tree_context_menu(self, position):
        index = self.tree.indexAt(position)
        path = self.file_model.filePath(index) if index.isValid() else QDir.currentPath()
        is_dir = self.file_model.isDir(index) if index.isValid() else True

        menu = shapes.round_menu(QMenu(self))

        act_new_file = menu.addAction("New File")
        act_new_folder = menu.addAction("New Folder")
        menu.addSeparator()

        act_copy = None
        act_paste = None
        act_duplicate = None
        act_rename = None
        act_delete = None

        if index.isValid():
            act_copy = menu.addAction("Copy")
            act_duplicate = menu.addAction("Duplicate")

        target_folder = path if is_dir else str(Path(path).parent)
        if self.copied_path and os.path.exists(self.copied_path):
            act_paste = menu.addAction("Paste")

        if index.isValid():
            menu.addSeparator()
            act_rename = menu.addAction("Rename")
            act_delete = menu.addAction("Delete")

        menu.addSeparator()
        act_reveal = menu.addAction("Show in File Manager")

        action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if action == act_new_file:
            self._tree_create_file(target_folder)
        elif action == act_new_folder:
            self._tree_create_folder(target_folder)
        elif action == act_copy and path:
            self.copied_path = path
        elif action == act_paste:
            self._tree_paste_item(target_folder)
        elif action == act_duplicate and path:
            self._tree_duplicate_item(path)
        elif action == act_rename and path:
            self._tree_rename_item(path)
        elif action == act_delete and path:
            self._tree_delete_item(path)
        elif action == act_reveal:
            self._tree_show_in_explorer(path or target_folder)

    def _tree_create_file(self, parent_dir):
        name, ok = QInputDialog.getText(self, "New File", "Give your new file a name (don't forget the extension):")
        if ok and name.strip():
            target = os.path.join(parent_dir, name.strip())
            try:
                with open(target, "x", encoding="utf-8"):
                    pass
            except Exception as e:
                QMessageBox.critical(self, "Something went really wrong", f"Couldn't create file for the following reason:\n{e}")

    def _tree_create_folder(self, parent_dir):
        name, ok = QInputDialog.getText(self, "New Folder", "Give your new folder a name:")
        if ok and name.strip():
            target = os.path.join(parent_dir, name.strip())
            try:
                os.makedirs(target, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "uh oh", f"Can't create folder for this exact reason:\n{e}")

    def _tree_paste_item(self, target_folder):
        if not self.copied_path or not os.path.exists(self.copied_path):
            return
        src = Path(self.copied_path)
        dest = Path(target_folder) / src.name
        
        counter = 1
        while dest.exists():
            dest = Path(target_folder) / f"{src.stem}_copy{counter}{src.suffix}"
            counter += 1

        try:
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to paste:\n{e}")

    def _tree_duplicate_item(self, path):
        src = Path(path)
        parent = src.parent
        dest = parent / f"{src.stem}_copy{src.suffix}"
        
        counter = 1
        while dest.exists():
            dest = parent / f"{src.stem}_copy{counter}{src.suffix}"
            counter += 1

        try:
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to duplicate:\n{e}")

    def _tree_rename_item(self, old_path):
        p = Path(old_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "New Name:", text=p.name)
        if ok and new_name.strip() and new_name.strip() != p.name:
            new_path = p.parent / new_name.strip()
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename:\n{e}")

    def _tree_delete_item(self, path):
        reply = QMessageBox.question(
            self, "Confirm Delete", f"Are you sure you want to delete:\n{path}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete:\n{e}")

    def _tree_show_in_explorer(self, path):
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", os.path.normpath(path)])
        else:
            if os.path.isfile(path):
                parent_dir = os.path.dirname(path)
            else:
                parent_dir = path
            QDesktopServices.openUrl(QUrl.fromLocalFile(parent_dir))

    def _on_tree_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            self.open_file_by_path(file_path)

    def open_file_by_path(self, path):
        for widget, data in self.tabs_data.items():
            if data.get("path") == path:
                self.tabs.setCurrentWidget(widget)
                self.stack.setCurrentIndex(1)
                return

        try:
            with open(path, "rb") as f:
                raw = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open file:\n{e}")
            return

        if b"\x00" in raw[:8192]:
            QMessageBox.warning(self, "Open Error", "This looks like a binary file and can't be opened in the editor.")
            return

        if len(raw) > 20 * 1024 * 1024:
            reply = QMessageBox.question(
                self, "Large file", "This file is larger than 20 MB and may be slow to edit. Open it anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        encoding = "utf-8"
        if raw.startswith(b"\xef\xbb\xbf"):
            encoding = "utf-8-sig"
        try:
            content = raw.decode(encoding)
        except UnicodeDecodeError:
            encoding = "latin-1"
            content = raw.decode(encoding)

        newline = "\r\n" if b"\r\n" in raw else "\n"
        filename = Path(path).name
        editor = self.create_new_tab(title=filename, content=content, file_path=path)
        self.tabs_data[editor]["encoding"] = encoding
        self.tabs_data[editor]["newline"] = newline
        self.extensions.emit("file_opened", editor=editor, path=path)

    def open_project_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Project Folder", QDir.homePath())
        if folder:
            self.file_model.setRootPath(folder)
            self.tree.setRootIndex(self.file_model.index(folder))

    def _setup_menubar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(skin.menubar_qss(themes.chrome()))

        file_menu = shapes.round_menu(menubar.addMenu("File"))
        file_menu.addAction("New File", self.new_file)
        file_menu.addAction("Open File", self.open_file)
        file_menu.addAction("Open Folder...", self.open_project_folder)
        file_menu.addAction("Save", self.save_file)
        file_menu.addAction("Save As", self.save_file_as)
        file_menu.addSeparator()
        file_menu.addAction("Preferences...", self.show_preferences)
        file_menu.addSeparator()
        file_menu.addAction("Close current Tab", self.close_current_tab)

        view_menu = shapes.round_menu(menubar.addMenu("View"))
        view_menu.addAction(self._sidebar_toggle_action)
        view_menu.addAction("Toggle Terminal/Code view", self.toggle_terminal)

        task_menu = shapes.round_menu(menubar.addMenu("Task"))
        task_menu.addAction("Run", self.Drun)
        task_menu.addAction("Run with no debugger", task.run)
        task_menu.addAction("Build project", task.compile)
        task_menu.addAction("Find issues", self.issues)

        tools_menu = shapes.round_menu(menubar.addMenu("Tools"))
        tools_menu.addAction("Configure Project", util.project)
        tools_menu.addAction("Update Antimatter", util.update)
        tools_menu.addAction("Refresh RPC", discord)

        git_menu = shapes.round_menu(menubar.addMenu("Git"))
        git_menu.addAction("Connect to a remote git repository", git.set_repo)
        git_menu.addSeparator()
        git_menu.addAction("Add all files to commit", git.add)
        git_menu.addAction("Commit with message", git.commit)
        git_menu.addAction("Push to remote repository", git.push)

        self.extensions.build_menu(menubar)

    def _setup_shortcuts(self):
        binds = [
            ("Ctrl+S", self.save_file),
            ("Ctrl+Shift+S", self.save_file_as),
            ("Ctrl+O", self.open_file),
            ("Ctrl+N", self.new_file),
            ("Ctrl+W", self.close_current_tab),
            ("Ctrl+Tab", self.cycle_next_tab),
            ("F5", self.Drun),
            ("Ctrl+F5", task.compile),
            ("Ctrl+I", self.issues),
            ("Ctrl+T", self.toggle_terminal),
            ("Ctrl+B", self.toggle_sidebar),
            ("Ctrl+Shift+P", self.show_palette),
            ("F1", self.show_palette),
            ("Ctrl+Shift+X", self.show_extensions_panel),
            ("Ctrl+K, Ctrl+T", self.choose_theme),
            ("Ctrl+,", self.show_preferences),
        ]
        for seq, fn in binds:
            action = QAction(self)
            action.setShortcut(QKeySequence(seq))
            action.triggered.connect(fn)
            self.addAction(action)

    def toggle_sidebar(self, show=None):
        visible = self.sidebar_dock.isVisible()
        show = (not visible) if show is None else show
        if show == visible:
            return
        if visible and self.sidebar_dock.width() >= 150:
            settings.set("sidebar_width", self.sidebar_dock.width(), persist=False)
        width = settings.get("sidebar_width")
        motion.animate_dock(
            self.sidebar_dock, show, width,
            lambda: self.resizeDocks([self.sidebar_dock], [width], Qt.Orientation.Horizontal) if show else None
        )

    def get_current_editor(self):
        widget = self.tabs.currentWidget()
        if widget and widget in self.tabs_data:
            return self.tabs_data[widget]["editor"]
        return None

    def get_current_path(self):
        widget = self.tabs.currentWidget()
        if widget and widget in self.tabs_data:
            return self.tabs_data[widget]["path"]
        return None

    def create_new_tab(self, title="Untitled", content="", file_path=None):
        editor = codeview.AntimatterEditor()
        editor.set_language_from_path(file_path)
        editor.text.snippet_lookup = self.extensions.snippet_for
        self.extensions.activate_event(f"onLanguage:{editor.text.language_id}")
        if content:
            editor.set_content(content)

        index = self.tabs.addTab(editor, title)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(skin.close_button_qss(themes.chrome()))
        close_btn.clicked.connect(lambda: self.close_tab_by_widget(editor))
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().ButtonPosition.RightSide, close_btn)

        self.tabs_data[editor] = {
            "editor": editor,
            "path": file_path,
            "title": title,
            "modified": False,
            "encoding": "utf-8",
            "newline": "\n"
        }

        editor.text.zoomed.connect(self._on_zoom)
        editor.text.cursorPositionChanged.connect(
            lambda: self._update_status() if self.get_current_editor() is editor else None
        )
        editor.text.document().modificationChanged.connect(
            lambda changed: self.mark_tab_modified(editor) if changed else self.mark_tab_saved(editor)
        )

        if file_path and hasattr(editor, "start_lsp"):
            editor.start_lsp(file_path)

        if self.stack.currentIndex() != 1:
            self.stack.setCurrentIndex(1)
            shapes.fade_in(self.tabs, 220)
        self.tabs.setCurrentIndex(index)
        self._update_status()
        return editor

    def mark_tab_modified(self, editor):
        if editor in self.tabs_data and not self.tabs_data[editor]["modified"]:
            self.tabs_data[editor]["modified"] = True
            idx = self.tabs.indexOf(editor)
            title = self.tabs_data[editor]["title"]
            self.tabs.setTabText(idx, f"• {title}")

    def mark_tab_saved(self, editor):
        if editor in self.tabs_data:
            self.tabs_data[editor]["modified"] = False
            editor.text.document().setModified(False)
            idx = self.tabs.indexOf(editor)
            title = self.tabs_data[editor]["title"]
            self.tabs.setTabText(idx, title)

    def _on_tab_changed(self, index):
        editor = self.get_current_editor()
        self._update_status()
        if not editor:
            return
        if editor.text.blockCount() < 6000:
            shapes.fade_in(editor, 220)
        path = self.tabs_data[editor]["path"]

        if path:
            self.setWindowTitle(f"{path} - Comical Antimatter 2026")
        else:
            self.setWindowTitle("Comical Antimatter 2026")

    def close_tab_by_widget(self, widget):
        idx = self.tabs.indexOf(widget)
        if idx != -1:
            self.close_tab_by_index(idx)

    def _confirm_close(self, widget):
        data = self.tabs_data.get(widget)
        if not data or not data["modified"]:
            return True
        reply = QMessageBox.question(
            self, "Unsaved changes", f"Do you want to save the changes made to {data['title']}?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.Save:
            self.tabs.setCurrentWidget(widget)
            return self.save_file()
        return True

    def close_tab_by_index(self, index):
        widget = self.tabs.widget(index)
        if not self._confirm_close(widget):
            return
        if widget in self.tabs_data:
            path = self.tabs_data[widget]["path"]
            del self.tabs_data[widget]
            self.extensions.emit("file_closed", path=path)
        if hasattr(widget, "shutdown"):
            widget.shutdown()
        self.tabs.removeTab(index)
        widget.deleteLater()
        if self.tabs.count() == 0:
            self.stack.setCurrentIndex(0)
            self.setWindowTitle("Comical Antimatter 2026")

    def close_current_tab(self):
        if self.tabs.count() > 0:
            self.close_tab_by_index(self.tabs.currentIndex())

    def cycle_next_tab(self):
        count = self.tabs.count()
        if count > 1:
            next_idx = (self.tabs.currentIndex() + 1) % count
            self.tabs.setCurrentIndex(next_idx)

    def do_undo(self):
        ed = self.get_current_editor()
        if ed: ed.text.undo()

    def do_redo(self):
        ed = self.get_current_editor()
        if ed: ed.text.redo()

    def new_file(self):
        self.create_new_tab(title="Untitled")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", languages.file_filter()
        )
        if not path:
            return
        self.open_file_by_path(path)

    def save_file_as(self):
        editor = self.get_current_editor()
        if not editor:
            return False

        path2, _ = QFileDialog.getSaveFileName(
            self, "Save file As", "", languages.file_filter()
        )
        if not path2:
            return False

        try:
            data = self.tabs_data[editor]
            with open(path2, "w", encoding=data["encoding"], newline=data["newline"]) as f:
                f.write(editor.get())

            filename = Path(path2).name
            self.tabs_data[editor]["path"] = path2
            self.tabs_data[editor]["title"] = filename
            self.mark_tab_saved(editor)
            self.setWindowTitle(f"{path2} - Comical Antimatter 2026")
            if hasattr(editor, "start_lsp"):
                editor.start_lsp(path2)
            self.extensions.emit("file_saved", editor=editor, path=path2)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")
            return False

    def save_file(self):
        editor = self.get_current_editor()
        path = self.get_current_path()
        if not editor:
            return False
        if not path:
            return self.save_file_as()
        try:
            data = self.tabs_data[editor]
            with open(path, "w", encoding=data["encoding"], newline=data["newline"]) as f:
                f.write(editor.get())
            self.mark_tab_saved(editor)
            self.extensions.emit("file_saved", editor=editor, path=path)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")
            return False
        return True

    def show_terminal(self):
        if not self.terminal_container.isVisible():
            self.sidebar_was_visible = self.sidebar_dock.isVisible()
            self.stack.hide()
            self.terminal_container.show()
            shapes.fade_in(self.terminal_container, 160)
            self.terminal_widget.set_focus()

    def toggle_terminal(self):
        if self.terminal_container.isVisible():
            self.restore_codeview()
        else:
            self.show_terminal()

    def restore_codeview(self):
        self.terminal_container.hide()
        self.stack.show()
        shapes.fade_in(self.stack, 160)

    def Drun(self):
        self.show_terminal()
        path3 = self.get_current_path()
        if path3 and path3.lower().endswith((".py", ".pyw")):
            if not self.save_file():
                return
        else:
            path3, _ = QFileDialog.getOpenFileName(
                self, "Choose file to run", "", "Python (*.py);;All files (*.*)"
            )
        if path3:
            self.terminal_widget.term_entry.setText(task.run_command(path3))
            self.terminal_widget.set_focus()

    def issues(self):
        editor = self.get_current_editor()
        actual_path = self.get_current_path() or ""

        iss_win = QMainWindow(self)
        iss_win.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        iss_win.resize(700, 400)
        iss_win.setWindowTitle("Issues - Comical Antimatter 2026")

        txt = QPlainTextEdit(iss_win)
        txt.setReadOnly(True)
        txt.setStyleSheet("background-color: #19191a; color: #D8DEE9;")
        iss_win.setCentralWidget(txt)

        if editor is None or not actual_path:
            txt.setPlainText("[!]: Save the file first before exploring issues.")
        elif not actual_path.lower().endswith((".py", ".pyw")):
            txt.setPlainText("[!]: The issues finder only supports Python files.")
        else:
            Out = subprocess.run(
                [util.python_exe(), "-m", "pyflakes"], input=editor.get(),
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            output_str = (Out.stdout + Out.stderr).replace("<stdin>", actual_path)
            if "No module named pyflakes" in output_str:
                txt.setPlainText("[!]: Pyflakes isn't installed. Install it with: pip install pyflakes")
            elif not output_str.strip():
                txt.setPlainText("[✓]: No issues detected. Looks good !")
            else:
                txt.setPlainText(f"[!]: Issues with the current file:\n==============================\n{output_str}")

        iss_win.show()

    def closeEvent(self, event):
        for widget in list(self.tabs_data):
            if not self._confirm_close(widget):
                event.ignore()
                return
        self._closing = True
        if self.sidebar_dock.isVisible() and self.sidebar_dock.width() >= 150:
            settings.set("sidebar_width", self.sidebar_dock.width(), persist=False)
        settings.set("window_geometry", bytes(self.saveGeometry().toHex()).decode(), persist=False)
        settings.save()
        for widget in list(self.tabs_data):
            widget.shutdown()
        self.terminal_widget.shutdown()
        super().closeEvent(event)

    def show_files(self):
        self.toggle_sidebar()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("com.comicalsoftwares.antimatter")
    window = AntimatterApp()
    window.show()
    sys.exit(app.exec())