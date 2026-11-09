import sys
import os
import platform
import subprocess
import time
import shutil
from pypresence import Presence
from pathlib import Path
from PyQt6.QtCore import Qt, QDir, QUrl
from PyQt6.QtGui import QIcon, QAction, QKeySequence, QFileSystemModel, QDesktopServices, QPixmap, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QPlainTextEdit,
    QFileDialog, QMessageBox, QPushButton, QTreeView,
    QDockWidget, QMenu, QInputDialog, QStackedWidget,
    QGraphicsColorizeEffect, QLabel)

# To anyone looking at this mess, don't mind the comments on these imports,
# they're just internet jokes that I personally find funny lol

import codeview # Codeview, my beloved
import task # For debugging/compiling stuff
import util # I don't remember adding this but welp.
import terminal # sudo rm -rf /home/nyxiereal/metrolist-kmp.. Thank me later, Nyx
import git # git commit -m "Minor Changes" +12,73625 Insertions (+) -171537723572,1752662453 deletions (-)


# Make Antimatter find out it's parent directory
# so it can find its own stuff
BASE_DIR = util.BASE_DIR
icon_path = str(BASE_DIR / "AppIcon.png")


# Setup Discord Rich Presence
RPC = None
RPC_START_TIME = time.time()
is_custom=False

def update_rpc(filename=None, is_file_path=True):
    global is_custom
    if is_custom or not RPC:
        return
    try:
        if filename:
            display_name = Path(filename).name if is_file_path else filename
            details = f"Editing {display_name}"
        else:
            details = "Editing a New Untitled File"
            
        RPC.update(
            details=details,
            start=RPC_START_TIME,
            large_image="image",
            large_text="Antimatter",
        )
    except Exception as e:
        print(f"Couldn't update Discord RPC: {e}")

def discord():
    global RPC, is_custom
    is_custom=False
    try:
        client_id = "1487828344480464957"
        if not RPC:
            for pipe_num in range(10):
                try:
                    RPC = Presence(client_id, pipe=pipe_num)
                    RPC.connect()
                    RPC.update(
                        details="Doing absolutely nothing",
                        start=RPC_START_TIME,
                        large_image="image",
                        large_text="Antimatter",
                    )
                    break
                except Exception:
                    continue
    except Exception as e:
        print(f"Discord RPC Error: {e}")

# Custom Discord RPC status
def custom():
    global is_custom
    is_custom=True
    message, ok = QInputDialog.getText(None, "Custom Discord RPC Status", "Enter the message that you wish to have on your RPC Card")
    if not ok or not message:
        return
    try:
        RPC.update(
            details=message,
            start=RPC_START_TIME,
            large_image="image",
            large_text="Antimatter",
        )
        QMessageBox.information(None, "Complete !", "Done! Go check out your new status :)")
    except Exception as e:
        print(e)        
        QMessageBox.warning(None, "Failed to set RPC status", "Make sure that your Discord client is running and that you are not offline. If your status is less than two letters long then it will not work, just so you know.")

# The main app window and it's core functions

class AntimatterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        global is_sandboxed
        is_sandboxed = task.is_sandboxed()
        self.setObjectName("Comical")
        self.setWindowTitle("Comical Antimatter")
        self.resize(1050, 650)
        
        self.copied_path = None
        self.setDockNestingEnabled(True)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #363636;
            }
            QDockWidget {
                color: #cdd6f4;
                font-family: 'Consolas', 'Cantarell';
                font-size: 12px;
                border-radius=7px;
            }
            QDockWidget::title {
                background: #2a2a2e;
                padding-left: 8px;
                padding-top: 4px;
                padding-bottom: 4px;
                border-bottom: 1px solid #1e1e1e;
            }
            QTreeView {
                background-color: #1e1e1e;
                color: #cdd6f4;
                border: none;
                font-family: 'Consolas', 'Cantarell';
                font-size: 12px;
                border-radius=7px;
            }
            QTreeView::item:hover {
                background-color: #2a2a2e;
            }
            QTreeView::item:selected {
                background-color: #313244;
                color: #ffffff;
            }
            QScrollBar:vertical {
                background: #19191a;
                width: 10px;
                margin: 0px;
                border: none;
                border-radius=7px;
            }
            QScrollBar:horizontal {
                background: #19191a;
                height: 10px;
                margin: 0px;
                border: none;
                border-radius=7px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #45475a;
                border-radius: 4px;
                min-height: 20px;
                min-width: 20px;
                border: none;
            }
            QScrollBar::handle:hover {
                background: #585b70;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
                border: none;
                width: 0px;
                height: 0px;
                border-radius=7px;
            }
        """)

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
        center_layout.addWidget(logo_label)
        center_layout.addWidget(title_label)

        welcome_layout.addStretch()
        welcome_layout.addWidget(center_container)
        welcome_layout.addStretch()

        footer_label = QLabel("Version 1.7 - Alpha")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #8a79a3; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        footer_label2 = QLabel("This project is open-source and licensed under the MIT license.")
        footer_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label2.setStyleSheet("color: white; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
        welcome_layout.addWidget(footer_label)
        welcome_layout.addWidget(footer_label2)

        self.stack.addWidget(self.welcome_widget)

        # File System Viewer
        self.file_model = QFileSystemModel()
        root_path = str(Path.home())
        self.file_model.setRootPath(root_path)

        self.tree = QTreeView()
        self.tree.setModel(self.file_model)
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
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)

        # Tab bar
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_by_index)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #19191a;
                border-radius=7px;
            }
            QTabBar {
                background: #363636;
                border-radius=7px;
            }
            QTabBar::tab {
                background: #363636;
                color: #a6adc8;
                padding: 7px 12px;
                font-family: 'Consolas', 'Cantarell';
                font-size: 13px;
                border: none;
                border-radius=7px;
            }
            QTabBar::tab:selected {
                background: #19191a;
                color: #cdd6f4;
                border-radius=7px;
            }
            QTabBar::close-button {
                image: none;
                subcontrol-position: right;
                width: 14px;
                height: 14px;
                border-radius=7px;
            }
            QTabBar::tab:selected QTabBar::close-button {
                background: #f38ba8;
                border-radius: 7px;
            }
            QTabBar::tab:hover QTabBar::close-button {
                background: #f38ba8;
                border-radius: 7px;
            }
        """)
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

    def _show_tree_context_menu(self, position):
        index = self.tree.indexAt(position)
        path = self.file_model.filePath(index) if index.isValid() else QDir.currentPath()
        is_dir = self.file_model.isDir(index) if index.isValid() else True

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #181825; color: #cdd6f4; border: 1px solid #313244; }
            QMenu::item:selected { background-color: #313244; }
            QMenu::separator {
                height: 1px;
                background-color: #89b4fa;
                margin: 4px 8px;
            }
        """)

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
        name, ok = QInputDialog.getText(self, "New File", "Give your new file a name & an extension (e.g: test.py):")
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
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open file:\n{e}")
            return

        filename = Path(path).name
        self.create_new_tab(title=filename, content=content, file_path=path)

    def open_project_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Project Folder", QDir.homePath())
        if folder:
            self.file_model.setRootPath(folder)
            self.tree.setRootIndex(self.file_model.index(folder))

    
    # Top menubar (For file/View/Task and that other stuff)

    def _setup_menubar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background-color: #363636; color: #cdd6f4; }
            QMenuBar::item:selected { background-color: #5400ba; }
            QMenu { background-color: #181825; color: #cdd6f4; border: none solid #313244; }
            QMenu::item:selected { background-color: #313244; }
            QMenu::separator {
                height: 1px;
                background-color: #89b4fa;
                margin: 4px 8px;
            }
        """)

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New File\tCtrl + N", self.new_file)
        file_menu.addAction("Open File\tCtrl + O", self.open_file)
        file_menu.addAction("Open Folder...", self.open_project_folder)
        file_menu.addAction("Save\tCtrl + S", self.save_file)
        file_menu.addAction("Save As\tCtrl + Shift + S", self.save_file_as)
        file_menu.addSeparator()
        file_menu.addAction("Close current Tab\tCtrl + W", self.close_current_tab)

        view_menu = menubar.addMenu("View")
        view_menu.addAction(self.sidebar_dock.toggleViewAction())
        if not is_sandboxed:
            view_menu.addAction("Toggle Terminal/Code view\tCtrl + T", self.toggle_terminal)
        else:
            pass

        task_menu = menubar.addMenu("Task")
        if not is_sandboxed:
            task_menu.addAction("Run\t F5", self.Drun)
            task_menu.addAction("Build project\tCtrl + F5", task.compile)
        else:
            pass
        task_menu.addAction("Find issues\tCtrl + I", self.issues)

        tools_menu = menubar.addMenu("Tools")
        if not is_sandboxed:
            tools_menu.addAction("Set up .venv environment", util.project)
        else:
            pass
        tools_menu.addAction("Check for updates", util.update)
        tools_menu.addSeparator()
        tools_menu.addAction("Refresh Discord RPC", discord)
        tools_menu.addAction("Set custom Discord RPC Status", custom)
        tools_menu.addSeparator()
        tools_menu.addAction("Open official Antimatter Documentation\tF1", util.docs)
        tools_menu.addAction("About Antimatter", util.about)

        if not is_sandboxed:
            git_menu = menubar.addMenu("Git")
            git_menu.addAction("Add remote repository", git.set_repo)
            git_menu.addAction("Clone", git.clone)
            git_menu.addSeparator()
            git_menu.addAction("Add files (Git add)", git.add)
            git_menu.addAction("Commit", git.commit)
            git_menu.addAction("Sync (Pull)", git.sync)
            git_menu.addAction("Push", git.push)
        else:
            pass
        

    def _setup_shortcuts(self):
        if not is_sandboxed:
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
                ("Ctrl+Shift+P", lambda: self._ed(lambda ed: ed.toggle_preview())),
                ("F1", util.docs),
                ("Ctrl+T", self.toggle_terminal)
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
                ("Ctrl+Shift+P", lambda: self._ed(lambda ed: ed.toggle_preview())),
                ("F1", util.docs)
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

        index = self.tabs.addTab(editor, title)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 13px;
                margin-left: 0px;
            }
            QPushButton:hover {
                color: #d6544b;
            }
        """)
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

        if file_path and not is_custom:
            update_rpc(file_path, is_file_path=True)
        elif not is_custom:
            update_rpc(None)
        else:
            pass

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
            idx = self.tabs.indexOf(editor)
            title = self.tabs_data[editor]["title"]
            self.tabs.setTabText(idx, title)

    def _on_tab_changed(self, index):
        editor = self.get_current_editor()
        if not editor:
            update_rpc(None)
            self.setWindowTitle("Comical Antimatter")
            return
        path = self.tabs_data[editor]["path"]

        if path and not is_custom:
            self.setWindowTitle(f"{path} - Comical Antimatter")
            update_rpc(path, is_file_path=True)
        elif not is_custom:
            self.setWindowTitle("Comical Antimatter")
            update_rpc(None)
        else:
            self.setWindowTitle("Comical Antimatter")

    def close_tab_by_widget(self, widget):
        idx = self.tabs.indexOf(widget)
        if idx != -1:
            self.close_tab_by_index(idx)

    def close_tab_by_index(self, index):
        widget = self.tabs.widget(index)
        if widget in self.tabs_data:
            del self.tabs_data[widget]
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.stack.setCurrentIndex(0)
            self.setWindowTitle("Comical Antimatter")
            update_rpc(None)

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
        editor = self.get_current_editor()
        if not editor:
            return False

        path2, _ = QFileDialog.getSaveFileName(
            self, "Save file As", "", "Python (*.py);;Markdown (*.md);;Text (*.txt);;All files (*.*)"
        )
        if not path2:
            return False

        try:
            content = editor.get()
            with open(path2, "w", encoding="utf-8") as f:
                f.write(content)

            filename = Path(path2).name
            self.tabs_data[editor]["path"] = path2
            self.tabs_data[editor]["title"] = filename
            self.mark_tab_saved(editor)
            self.setWindowTitle(f"{path2} - Comical Antimatter")
            if hasattr(editor, "start_lsp"):
                editor.start_lsp(path2)
            if hasattr(editor, "set_file_path"):
                editor.set_file_path(path2)
            update_rpc(filename)
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
            update_rpc(Path(path).name)
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

    def issues(self):
        self.iss_win = QMainWindow(self)
        self.iss_win.resize(700, 400)
        self.iss_win.setWindowTitle("Issues - Comical Antimatter")

        txt = QPlainTextEdit(self.iss_win)
        txt.setReadOnly(True)
        txt.setStyleSheet("background-color: #19191a; color: #D8DEE9;")
        self.iss_win.setCentralWidget(txt)

        actual_path = self.get_current_path() or ""
        
        try:
            Out = subprocess.run(f'pyflakes "{actual_path}"', capture_output=True, text=True, shell=True)
        except Exception as e:
            print(f'[E]: {e}')
            QMessageBox.warning(None, "Pyflakes error", "Couldn't run pyflakes.")

        output_str = Out.stdout + Out.stderr
        if not output_str.strip():
            txt.setPlainText("[✓]: No issues detected. Looks good !")
        elif output_str.strip() == ": No such file or directory":
            txt.setPlainText("[!]: Open/Save the file first before exploring issues.")
        else:
            txt.setPlainText(f"[!]: Issues with the current file:\n==============================\n{output_str}")

        self.iss_win.show()

    def closeEvent(self, event):
        super().closeEvent(event)

    def show_files(self):
        self.sidebar_dock.toggleViewAction()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setDesktopFileName("io.github.comicalsoftwares.antimatter")
    window = AntimatterApp()
    window.show()
    discord()
    sys.exit(app.exec())