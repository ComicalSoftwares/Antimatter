import sys
import os
import platform
import subprocess
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal # ts gonna be soooo fast and smooth
from PyQt6.QtGui import QIcon, QPixmap, QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QToolBar, QLineEdit, QPlainTextEdit,
    QFileDialog, QMessageBox, QPushButton
)

import codeview # My beloved codeviewer
import task # Gotta need to debug
import util # Whatever ts is
from tkinter import messagebox

BASE_DIR = Path(__file__).resolve().parent

RPC = None

def discord():
    global RPC
    try:
        from pypresence import Presence
        client_id = "1487828344480464957"
        for pipe_num in range(10):
            RPC = Presence(client_id, pipe=pipe_num)
            RPC.connect()
            RPC.update(
                details="Doing nothing.", # Gotta flex my laziness
                start=time.time(),
                large_image="image",
                large_text="Antimatter",
            )
    except Exception as e:
        print(f"Discord RPC Error: {e}")

def update_rpc(file_name="an unnamed file"):
    if RPC:
        try:
            RPC.update(
                details=f"Editing {file_name}", # Gotta flex my hardwork, lol
                large_image="image",
                large_text="Antimatter",
            )
        except Exception as e:
            print(f"Discord RPC Error: {e}")

class TerminalReaderThread(QThread):
    output_signal = pyqtSignal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True

    def run(self):
        while self.running and self.process.poll() is None:
            char = self.process.stdout.read(1)
            if char:
                self.output_signal.emit(char)
            else:
                time.sleep(0.01)

    def stop(self):
        self.running = False


class AntimatterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("Comical")
        self.setWindowTitle("Comical Antimatter 2026")
        self.resize(1050, 650)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #363636;
            }
            QScrollBar:vertical {
                background: #19191a;
                width: 10px;
                margin: 0px;
                border: none;
            }

            QScrollBar:horizontal {
                background: #19191a;
                height: 10px;
                margin: 0px;
                border: none;
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
            }
        """)

        icon_path = str(BASE_DIR / "AppIcon.png") # Modified to make sure it works on Windows AND Linux !
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.tabs_data = {}

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar for old shit you can use using shortcuts
        self.sidebar = QToolBar("Sidebar")
        self.sidebar.setMovable(False)
        self.sidebar.setOrientation(Qt.Orientation.Vertical)
        self.sidebar.setStyleSheet("""
            QToolBar {
                background-color: #363636;
                border: none;
                padding-top: 5px;
                spacing: 6px;
            }
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px;
            }
            QToolButton:hover {
                background-color: #5400ba;
            }
        """)
        self.sidebar.setIconSize(QSize(20, 20))
        main_layout.addWidget(self.sidebar)

        # Main Container
        self.main_container = QWidget()
        self.container_layout = QVBoxLayout(self.main_container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        main_layout.addWidget(self.main_container)

        # Tab bar with close button
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab_by_index)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #19191a;
            }
            QTabBar {
                background: #363636;
            }
            QTabBar::tab {
                background: #363636;
                color: #a6adc8;
                padding: 7px 12px;
                font-family: 'Consolas', 'Cantarell';
                font-size: 13px;
                border: none;
            }
            QTabBar::tab:selected {
                background: #19191a;
                color: #cdd6f4;
            }
            QTabBar::close-button {
                image: none;
                subcontrol-position: right;
                width: 14px;
                height: 14px;
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
        self.container_layout.addWidget(self.tabs)

        # Integrated Terminal Box
        self.terminal_container = QWidget()
        term_layout = QVBoxLayout(self.terminal_container)
        term_layout.setContentsMargins(5, 5, 5, 5)
        
        self.output_box = QPlainTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setStyleSheet("background-color: #19191a; color: #cdd6f4; border: none; font-family: Consolas;")
        term_layout.addWidget(self.output_box)

        self.term_entry = QLineEdit()
        self.term_entry.setPlaceholderText("Type a command...")
        self.term_entry.setStyleSheet("background-color: #19191a; color: #cdd6f4; border: none; solid #313244; padding: 4px;")
        self.term_entry.returnPressed.connect(self._exec_terminal_cmd)
        term_layout.addWidget(self.term_entry)

        self.terminal_container.hide()
        self.container_layout.addWidget(self.terminal_container)

        self._setup_sidebar_buttons()
        self._setup_menubar()
        self._setup_shortcuts()

        # Start terminal
        self._init_interactive_terminal()

        self.create_new_tab()
        discord()

    def _init_interactive_terminal(self):
        shell_cmd = "cmd.exe" if platform.system() == "Windows" else "/bin/bash"
        try:
            self.term_process = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.term_reader = TerminalReaderThread(self.term_process)
            self.term_reader.output_signal.connect(self._append_term_output)
            self.term_reader.start()
        except Exception as e:
            self.output_box.appendPlainText(f"Failed to launch shell: {e}\n")

    def _append_term_output(self, text):
        self.output_box.moveCursor(self.output_box.textCursor().MoveOperation.End)
        self.output_box.insertPlainText(text)

    def _setup_sidebar_buttons(self):
        def add_btn(icon_filename, func, tooltip=""):
            pixmap = QPixmap(str(BASE_DIR / icon_filename))
            icon = QIcon(pixmap)
            act = QAction(icon, "", self)
            act.setToolTip(tooltip)
            act.triggered.connect(func)
            self.sidebar.addAction(act)
            return act

        add_btn("undo.png", self.do_undo, "Undo")
        add_btn("redo.png", self.do_redo, "Redo")
        add_btn("copy.png", lambda: self.get_current_editor().text.copy() if self.get_current_editor() else None, "Copy")
        add_btn("paste.png", lambda: self.get_current_editor().text.paste() if self.get_current_editor() else None, "Paste")
        add_btn("cut.png", lambda: self.get_current_editor().text.cut() if self.get_current_editor() else None, "Cut")
        
        self.term_act = add_btn("term.png", self.toggle_terminal, "Terminal")
        add_btn("issue.png", self.issues, "Issues")

    def _setup_menubar(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { background-color: #363636; color: #cdd6f4; }
            QMenuBar::item:selected { background-color: #5400ba; }
            QMenu { background-color: #181825; color: #cdd6f4; border: none solid #313244; }
            QMenu::item:selected { background-color: #313244; }
        """)

        file_menu = menubar.addMenu("File")
        file_menu.addAction("New File", self.new_file)
        file_menu.addAction("Open File", self.open_file)
        file_menu.addAction("Save", self.save_file)
        file_menu.addAction("Save As", self.save_file_as)
        file_menu.addAction("Close current Tab", self.close_current_tab)

        task_menu = menubar.addMenu("Task")
        task_menu.addAction("Run", self.Drun)
        task_menu.addAction("Run without debugger (Only for GUI apps)", task.run)
        task_menu.addAction("Build project", task.compile)
        task_menu.addAction("Open new terminal window", task.Terminal)

        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Configure Project", util.project)
        tools_menu.addAction("Update Antimatter", util.update)
        tools_menu.addAction("Refresh RPC", discord)

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
            ("Ctrl+B", self.restore_codeview),
        ]
        for seq, fn in binds:
            action = QAction(self)
            action.setShortcut(QKeySequence(seq))
            action.triggered.connect(fn)
            self.addAction(action)

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
        if content:
            editor.insert("0.0", content)

        index = self.tabs.addTab(editor, title)
        
        # Close tab
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

        editor.text.textChanged.connect(lambda: self.mark_tab_modified(editor))

        if file_path and hasattr(editor, "start_lsp"):
            editor.start_lsp(file_path)

        self.tabs.setCurrentIndex(index)
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
            return
        path = self.tabs_data[editor]["path"]
        title_name = self.tabs_data[editor]["title"]

        if path:
            self.setWindowTitle(f"{path} - Comical Antimatter 2026")
        else:
            self.setWindowTitle("Comical Antimatter 2026")

        update_rpc(file_name=Path(path).name if path else title_name)

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
            self.create_new_tab()

    def close_current_tab(self):
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
            self, "Open file", "", "Python (*.py);;Text (*.txt);;All files (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open file:\n{e}")
            return

        filename = Path(path).name
        self.create_new_tab(title=filename, content=content, file_path=path)

    def save_file_as(self):
        editor = self.get_current_editor()
        if not editor:
            return False

        path2, _ = QFileDialog.getSaveFileName(
            self, "Save file As", "", "Python (*.py);;Text (*.txt);;All files (*.*)"
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
            self.setWindowTitle(f"{path2} - Comical Antimatter 2026")
            update_rpc(filename)
            if hasattr(editor, "start_lsp"):
                editor.start_lsp(path2)
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
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")
            return False
        return True

    def toggle_terminal(self):
        if self.terminal_container.isVisible():
            self.restore_codeview()
        else:
            self.tabs.hide()
            self.terminal_container.show()
            self.term_entry.setFocus()

    def restore_codeview(self):
        self.terminal_container.hide()
        self.tabs.show()

    def _exec_terminal_cmd(self):
        cmd = self.term_entry.text()
        self.term_entry.clear()

        if hasattr(self, "term_process") and self.term_process.poll() is None:
            try:
                self.term_process.stdin.write(cmd + "\n")
                self.term_process.stdin.flush()
            except Exception as e:
                self.output_box.appendPlainText(f"\nError writing to terminal: {e}\n")

    def Drun(self):
        self.toggle_terminal()
        path3, _ = QFileDialog.getOpenFileName(
            self, "Choose file to run", "", "Python (*.py);;All files (*.*)"
        )
        if path3:
            cmd = f'python "{path3}"' if platform.system() == "Windows" else f"python3 {path3}"
            self.term_entry.setText(cmd)

    def issues(self):
        iss_win = QMainWindow(self)
        iss_win.resize(700, 400)
        iss_win.setWindowTitle("Issues - Comical Antimatter 2026")

        txt = QPlainTextEdit(iss_win)
        txt.setReadOnly(True)
        txt.setStyleSheet("background-color: #19191a; color: #D8DEE9;")
        iss_win.setCentralWidget(txt)

        actual_path = self.get_current_path() or ""
        if platform.system() == "Windows":
            Out = subprocess.run(f'%appdata%/Python/Python314/Scripts/pyflakes.exe "{actual_path}"', capture_output=True, text=True, shell=True)
        else:
            Out = subprocess.run(f'pyflakes "{actual_path}"', capture_output=True, text=True, shell=True)

        output_str = Out.stdout + Out.stderr
        if not output_str.strip():
            txt.setPlainText("Nothing wrong with this file. Nice work !")
        elif output_str.strip() == ": No such file or directory":
            txt.setPlainText("Save the file first before exploring issues.")
        else:
            txt.setPlainText(output_str)

        iss_win.show()

    def closeEvent(self, event):
        if hasattr(self, "term_reader"):
            self.term_reader.stop()
        if hasattr(self, "term_process"):
            self.term_process.terminate()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AntimatterApp()
    window.show()
    sys.exit(app.exec())