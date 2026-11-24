import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, QDir, QUrl
from PyQt6.QtGui import QIcon, QAction, QKeySequence, QFileSystemModel, QDesktopServices, QPixmap, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QFileDialog, QMessageBox, QPushButton, QTreeView,
    QDockWidget, QMenu, QInputDialog, QStackedWidget,
    QGraphicsColorizeEffect, QLabel)

# Anything imported here are the custom modules that
# Antimatter depends on..

import codeview
import task
import util
import terminal
import git
import discord
from issues import IssuesDialog
import theme
import settings
import preferences

# Make Antimatter find out its parent directory
# so it can load its own stuff
BASE_DIR = util.BASE_DIR
icon_path = str(BASE_DIR / "AppIcon.png")

# The main app window and it's core functions

class AntimatterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = settings.load()
        self.setObjectName("Comical")
        self.setWindowTitle("Comical Antimatter")
        self.resize(1050, 650)
        
        self.copied_path = None
        self.setDockNestingEnabled(True)

        self.setStyleSheet(theme.window)

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
        self.welcome_widget.setStyleSheet("background-color: #363636;")
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

        center_container = QWidget()
        center_container.setStyleSheet("background: transparent;")
        center_layout = QVBoxLayout(center_container)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(12)
        start_label = QLabel("To get started, open a project/file.", center_container)
        start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        start_label.setStyleSheet("color: #8a79a3; font-family: 'Consolas', 'Cantarell'; font-size: 15px; font-weight: bold; background: transparent;")
        
        center_layout.addWidget(logo_label)
        center_layout.addWidget(title_label)
        center_layout.addWidget(start_label)
        center_layout.addSpacing(8)

        welcome_layout.addStretch()
        welcome_layout.addWidget(center_container)
        welcome_layout.addStretch()

        footer_label = QLabel(f"v.{util.CURRENT_VERSION}")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #8a79a3; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        footer_label2 = QLabel("Developed by Comical | This project is open-source & licensed under the MIT license.")
        footer_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label2.setStyleSheet("color: white; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        welcome_layout.addWidget(footer_label)
        welcome_layout.addWidget(footer_label2)

        self.stack.addWidget(self.welcome_widget)

        # File System Viewer
        self.file_model = QFileSystemModel()
        self.tree = QTreeView()
        self.tree.setModel(None)  # So we can force user to chose a folder, which will allow the git module to
                                  # be able to get the folder's abs path so it can finally manage it.
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        self.tree.header().hide()
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)
        
        self.project_root = None

        for col in range(1, 4):
            self.tree.setColumnHidden(col, True)

        self.tree.header().hide()
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)

        # File Dock Sidebar
        self.sidebar_dock = QDockWidget("File Manager", self)
        self.sidebar_dock.setWidget(self.tree)
        self.sidebar_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable | QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.sidebar_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)
        self.sidebar_dock.hide()

        # Tab bar
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_by_index)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet(theme.tab_bar)
        self.stack.addWidget(self.tabs)

        # Live Terminal Widget
        self.terminal_container = QWidget()
        term_layout = QVBoxLayout(self.terminal_container)
        term_layout.setContentsMargins(5, 5, 5, 5)
        
        self.terminal_widget = terminal.AntimatterTerminal(self)
        term_layout.addWidget(self.terminal_widget)

        self.terminal_container.hide()
        self.central_layout.addWidget(self.terminal_container)

        self.sidebar_was_visible = True

        self._setup_menubar()
        self._setup_shortcuts()
        self.handle_startup_arguments()
    
    def handle_startup_arguments(self):
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                resolved_path = os.path.abspath(arg)
                if os.path.isdir(resolved_path):
                    self.load_project_folder(resolved_path)
                elif os.path.isfile(resolved_path):
                    parent_dir = str(Path(resolved_path).parent)
                    self.load_project_folder(parent_dir)
                    self.open_file_by_path(resolved_path)
    def load_project_folder(self, folder):
        self.project_root = folder
        self.file_model.setRootPath(folder)
        self.tree.setModel(self.file_model)
        self.tree.setRootIndex(self.file_model.index(folder))
        for col in range(1, 4):
            self.tree.setColumnHidden(col, True)
    
        name = os.path.basename(folder.rstrip(os.sep)) or folder
        self.sidebar_dock.setWindowTitle(f"{name} | File Manager")
        self.setWindowTitle(f"{name} - Comical Antimatter")
        self.sidebar_dock.toggleViewAction().setText("File Manager")

    def open_project_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Project Folder", QDir.homePath())
        if folder:
            self.load_project_folder(folder)
            self.sidebar_dock.show()

    def get_project_root(self):
        return self.project_root

    def _show_tree_context_menu(self, position):
        index = self.tree.indexAt(position)
        path = self.file_model.filePath(index) if index.isValid() else QDir.currentPath()
        is_dir = self.file_model.isDir(index) if index.isValid() else True

        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet(theme.context_menu)

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
        act_reveal = menu.addAction("Show in System's File Manager")

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
        name, ok = QInputDialog.getText(self, "New File", "Give your new file a name with an extension (e.g: test.py):")
        if ok and name.strip():
            target = os.path.join(parent_dir, name.strip())
            try:
                open(target, "w", encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Something went really wrong", f"Couldn't create file for the following reason:\n{e}")

    def _tree_create_folder(self, parent_dir):
        name, ok = QInputDialog.getText(self, "New Folder", "Give your new folder a name:")
        if ok and name.strip():
            target = os.path.join(parent_dir, name.strip())
            try:
                os.makedirs(target, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "uh oh", f"Can't create folder for this reason:\n{e}")

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
            QMessageBox.critical(self, "Error", f"Failed to paste element:\n{e}")

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
                QMessageBox.critical(self, "Error", f"Failed to delete item:\n{e}")

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
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open file:\n{e}")
            return

        filename = Path(path).name
        self.create_new_tab(title=filename, content=content, file_path=path)

    
    # Top menubar (For file/View/Task and that other stuff)

    def _setup_menubar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(theme.menubar)

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New File\tCtrl + N", self.new_file)
        file_menu.addAction("Open File\tCtrl + O", self.open_file)
        file_menu.addAction("Open Project Folder\tCtrl + Shift + O", self.open_project_folder)
        file_menu.addSeparator()
        file_menu.addAction("Save\tCtrl + S", self.save_file)
        file_menu.addAction("Save As\tCtrl + Shift + S", self.save_file_as)
        file_menu.addSeparator()
        file_menu.addAction("Close current Tab\tCtrl + W", self.close_current_tab)

        view_menu = menubar.addMenu("View")
        view_menu.addAction(self.sidebar_dock.toggleViewAction())
        if not task.is_sandboxed():
            view_menu.addAction("Toggle Terminal/Code view\tCtrl + T", self.toggle_terminal)
        else:
            pass

        task_menu = menubar.addMenu("Task")
        if not task.is_sandboxed():
            task_menu.addAction("Run\t F5", self.Drun)
            task_menu.addAction("Build project\tCtrl + F5", task.compile)
        else:
            pass
        task_menu.addAction("Find issues\tCtrl + I", self.issues)

        tools_menu = menubar.addMenu("Tools")
        if not task.is_sandboxed():
            tools_menu.addAction("Set up .venv environment", util.project)
            tools_menu.addAction("Check for updates", util.update)
            tools_menu.addSeparator()
        else:
            pass
        tools_menu.addAction("Reset Discord RPC", discord.init_discord)
        tools_menu.addAction("Set custom Discord RPC Status", discord.custom)
        tools_menu.addSeparator()
        tools_menu.addAction("Preferences...\tCtrl + ,", self.open_preferences)
        tools_menu.addSeparator()
        tools_menu.addAction("Open official Antimatter Documentation\tF1", util.docs)
        tools_menu.addAction("About Antimatter\tF2", util.about)

        if not task.is_sandboxed():
            git_menu = menubar.addMenu("Git")
            git_menu.addAction("Open Git Dashboard\tCtrl + G", lambda: git.open_git_manager(self))
        else:
            pass

    def _setup_shortcuts(self):
        if not task.is_sandboxed():
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
                ("Ctrl+B", self.toggle_sidebar),
                ("Ctrl+F", lambda: self._ed(lambda ed: ed.open_find(False))),
                ("Ctrl+R", lambda: self._ed(lambda ed: ed.open_find(True))),
                ("F1", util.docs),
                ("Ctrl+T", self.toggle_terminal),
                ("Ctrl+G", lambda: git.open_git_manager(self)),
                ("F2", util.about),
                ("Ctrl+,", self.open_preferences),
                ("Ctrl+Shift+O", self.open_project_folder)
            ]
        else:
            binds = [
                ("Ctrl+S", self.save_file),
                ("Ctrl+Shift+S", self.save_file_as),
                ("Ctrl+O", self.open_file),
                ("Ctrl+N", self.new_file),
                ("Ctrl+W", self.close_current_tab),
                ("Ctrl+Tab", self.cycle_next_tab),
                ("Ctrl+I", self.issues),
                ("Ctrl+B", self.toggle_sidebar),
                ("Ctrl+F", lambda: self._ed(lambda ed: ed.open_find(False))),
                ("Ctrl+R", lambda: self._ed(lambda ed: ed.open_find(True))),
                ("F1", util.docs),
                ("F2", util.about),
                ("Ctrl+,", self.open_preferences),
                ("Ctrl+Shift+O", self.open_project_folder)
            ]
        for seq, fn in binds:
            action = QAction(self)
            action.setShortcut(QKeySequence(seq))
            action.triggered.connect(fn)
            self.addAction(action)

    def _ed(self, fn):
        ed = self.get_current_editor()
        if ed:
            fn(ed)

    def toggle_sidebar(self):
        if self.sidebar_dock.isVisible():
            self.sidebar_dock.hide()
        else:
            self.sidebar_dock.show()

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
        
        if file_path and hasattr(editor, "set_file_path"):
            editor.set_file_path(file_path)
           
        editor.apply_settings(self.settings)
        index = self.tabs.addTab(editor, title)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(theme.close)
        close_btn.clicked.connect(lambda: self.close_tab_by_widget(editor))
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().ButtonPosition.RightSide, close_btn)

        self.tabs_data[editor] = {
            "editor": editor,
            "path": file_path,
            "title": title,
            "modified": False
        }

        if content:
            editor.insert("0.0", content)

        editor.text.document().setModified(False)

        editor.text.textChanged.connect(lambda: self.mark_tab_modified(editor))

        if file_path and hasattr(editor, "start_lsp"):
            editor.start_lsp(file_path)

        self.stack.setCurrentIndex(1)
        self.tabs.setCurrentIndex(index)

        if file_path and not discord.is_custom:
            discord.update_rpc(file_path, is_file_path=True)
        elif not discord.is_custom:
            discord.update_rpc(None)
        else:
            pass

        return editor
        
    def open_preferences(self):
        dlg = preferences.PreferencesDialog(self.settings, self)
        if not dlg.exec():
            return
        old = self.settings
        self.settings = dlg.result_settings
        settings.save(self.settings)
        self.apply_settings(old)

    def apply_settings(self, old):
        for editor in list(self.tabs_data):
            editor.apply_settings(self.settings)
            if not self.settings["lsp_enabled"]:
                editor.stop_lsp()
            elif not old["lsp_enabled"] and editor._current_file_path \
                    and editor._current_file_path.lower().endswith(".py"):
                editor.start_lsp(editor._current_file_path)
    
        if old["discord_rpc"] != self.settings["discord_rpc"]:
            if self.settings["discord_rpc"]:
                discord.init_discord()
            else:
                discord.disconnect()

    def mark_tab_modified(self, editor):
        if editor in self.tabs_data and not self.tabs_data[editor]["modified"]:
            self.tabs_data[editor]["modified"] = True
            idx = self.tabs.indexOf(editor)
            title = self.tabs_data[editor]["title"]
            self.tabs.setTabText(idx, f"• {title}")

    def mark_tab_saved(self, editor):
        if editor in self.tabs_data:
            self.tabs_data[editor]["modified"] = False
            idx = self.tabs.indexOf(editor)
            title = self.tabs_data[editor]["title"]
            self.tabs.setTabText(idx, title)

    def _on_tab_changed(self, index):
        editor = self.get_current_editor()
        if not editor:
            discord.update_rpc(None)
            return
        path = self.tabs_data[editor]["path"]

        if path and not discord.is_custom:
            discord.update_rpc(path, is_file_path=True)
        elif not discord.is_custom:
            discord.update_rpc(None)
        else:
            pass

    def close_tab_by_widget(self, widget):
        idx = self.tabs.indexOf(widget)
        if idx != -1:
            self.close_tab_by_index(idx)

    def _confirm_discard(self, widget):
        data = self.tabs_data.get(widget)
        if not data or not data["modified"]:
            return True
        self.tabs.setCurrentWidget(widget)
        answer = QMessageBox.question(
            self, "Unsaved changes",
            f'"{data["title"]}" has unsaved changes. Close anyways without saving?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def close_tab_by_index(self, index):
        widget = self.tabs.widget(index)
        if not self._confirm_discard(widget):
            return
        widget.shutdown()
        if widget in self.tabs_data:
            del self.tabs_data[widget]
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.stack.setCurrentIndex(0)
            discord.update_rpc(None)

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
            self, "Open file", "", "Python (*.py);;Markdown (*.md);;Text (*.txt);;All files (*.*)"
        )
        if not path:
            return
        self.open_file_by_path(path)

    def save_file_as(self):
        EXTENSION_MAP = {
            "Python (*.py)": ".py",
            "Markdown (*.md)": ".md",
            "Text (*.txt)": ".txt",
        }
        editor = self.get_current_editor()
        if not editor:
            return False
    
        filters = "Python (*.py);;Markdown (*.md);;Text (*.txt);;All files (*.*)"
        path2, selected_filter = QFileDialog.getSaveFileName(self, "Save file As", "", filters)
        if not path2:
            return False
    
        file_path = Path(path2)
        if not file_path.suffix:
            ext = EXTENSION_MAP.get(selected_filter, "")
            if ext:
                file_path = file_path.with_suffix(ext)
    
        path2 = str(file_path)
    
        try:
            content = editor.get()
            with open(path2, "w", encoding="utf-8") as f:
                f.write(content)
    
            filename = file_path.name
            self.tabs_data[editor]["path"] = path2
            self.tabs_data[editor]["title"] = filename
            self.mark_tab_saved(editor)
            if hasattr(editor, "start_lsp"):
                editor.start_lsp(path2)
            if hasattr(editor, "set_file_path"):
                editor.set_file_path(path2)
            discord.update_rpc(filename)
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
            content = editor.get()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.mark_tab_saved(editor)
            discord.update_rpc(Path(path).name)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")
            return False
        return True

    def show_terminal(self):
        if not self.terminal_container.isVisible():
            self.sidebar_was_visible = self.sidebar_dock.isVisible()
            self.stack.hide()
            self.terminal_container.show()
            self.terminal_widget.set_focus()

    def toggle_terminal(self):
        if self.terminal_container.isVisible():
            self.restore_codeview()
        else:
            self.show_terminal()

    def restore_codeview(self):
        self.terminal_container.hide()
        self.stack.show()

    def Drun(self):
        self.show_terminal()
        path3, _ = QFileDialog.getOpenFileName(
            self, "Choose file to run", "", "Python (*.py);;All files (*.*)"
        )
        if path3:
            cmd = f'python "{path3}"' if platform.system() == "Windows" else f"python3 {path3}"
            if hasattr(self.terminal_widget, "write"):
                self.terminal_widget.write((cmd).encode("utf-8"))
            self.terminal_widget.set_focus()

    def closeEvent(self, event):
        for widget in list(self.tabs_data):
            widget.shutdown()
            if not self._confirm_discard(widget):
                event.ignore()
                return
        super().closeEvent(event)

    def show_files(self):
        self.sidebar_dock.toggleViewAction()
    
    def issues(self):
        ed = self.get_current_editor()
        dlg = IssuesDialog(ed, self)
        dlg.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("io.github.comicalsoftwares.antimatter")
    window = AntimatterApp()
    window.show()
    if window.settings["discord_rpc"]:
       discord.init_discord()
    sys.exit(app.exec())