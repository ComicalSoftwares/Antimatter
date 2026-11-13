import sys
import os
import pty
import fcntl
import termios
import re
from PyQt6.QtCore import QSocketNotifier, Qt
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont, QGuiApplication
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QPlainTextEdit, QMenu

COMBINED_ESCAPE = re.compile(r'''
    (\x1b\].*?(?:\x07|\x1b\\))|
    (\x1b\[([?0-9;]*)([A-Za-z])) 
''', re.VERBOSE)

PROMPT_PATTERN = re.compile(r'\[[\w\-]+@[\w\-]+\s+[^\]]+\][\$#]')
SUDO_PROMPT_PATTERN = re.compile(r'(?i)\[sudo\] password for .*:|password:')

class NativeTerminalWidget(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monospace';
                font-size: 11pt;
            }
        """)
        self.setUndoRedoEnabled(False)
        self.master_fd = None
        self.notifier = None
        self.current_format = QTextCharFormat()
        self.input_start_pos = 0
        self.is_password_prompt = False
        self.init_terminal()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def init_terminal(self):
        if sys.platform == "win32":
            from PyQt6.QtCore import QProcess
            self.process = QProcess(self)
            self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            self.process.readyReadStandardOutput.connect(self.handle_windows_output)
            self.process.start("cmd.exe", [])
        else:
            try:
                os.environ["TERM"] = "xterm-256color"
                pid, self.master_fd = pty.fork()
                if pid == 0:
                    os.execvp("bash", ["bash"])
                    sys.exit(0)
                else:
                    fcntl.fcntl(self.master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
                    try:
                        attr = termios.tcgetattr(self.master_fd)
                        attr[3] &= ~termios.ECHO
                        termios.tcsetattr(self.master_fd, termios.TCSANOW, attr)
                    except Exception:
                        pass

                    self.notifier = QSocketNotifier(self.master_fd, QSocketNotifier.Type.Read, self)
                    self.notifier.activated.connect(self.handle_pty_output)
            except Exception as e:
                self.appendPlainText(f"[Antimatter Terminal Error] PTY initialization failed: {e}\n")

    def handle_pty_output(self, socket):
        try:
            data = os.read(self.master_fd, 4096)
            if data:
                text = data.decode("utf-8", errors="ignore")
                self.append_ansi_text(text)
        except OSError:
            pass

    def handle_windows_output(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        self.append_ansi_text(data)

    def append_ansi_text(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if SUDO_PROMPT_PATTERN.search(text):
            self.is_password_prompt = True
        elif "\n" in text or "\r" in text:
            self.is_password_prompt = False
        
        i = 0
        n = len(text)
        while i < n:
            match = COMBINED_ESCAPE.match(text, i)
            if match:
                start, end = match.span()
                osc_seq, csi_seq, params_str, command = match.groups()
                if csi_seq:
                    if command == 'm':
                        self.apply_sgr(params_str)
                    elif command == 'J':
                        if params_str in ('2', '2J', '0J', ''):
                            self.clear()
                            self.input_start_pos = 0
                i = end
            else:
                prompt_match = PROMPT_PATTERN.match(text, i)
                if prompt_match:
                    p_text = prompt_match.group(0)
                    green_format = QTextCharFormat(self.current_format)
                    green_format.setForeground(QColor("#a6e3a1"))
                    cursor.insertText(p_text, green_format)
                    i += len(p_text)
                else:
                    if text[i] != '\r' and text[i] != '\b':
                        cursor.insertText(text[i], self.current_format)
                    i += 1

        self.input_start_pos = self.document().characterCount() - 1
        self.ensureCursorVisible()

    def apply_sgr(self, params_str):
        if not params_str:
            params = [0]
        else:
            clean_params = params_str.replace('?', '')
            params = [int(p) if p.isdigit() else 0 for p in clean_params.split(';') if p]
        
        for p in params:
            if p == 0:
                self.current_format = QTextCharFormat()
            elif p == 1:
                self.current_format.setFontWeight(QFont.Weight.Bold)
            elif p == 22:
                self.current_format.setFontWeight(QFont.Weight.Normal)
            elif 30 <= p <= 37:
                colors = [
                    QColor("#1e1e1e"), QColor("#f38ba8"), QColor("#a6e3a1"), QColor("#f9e2af"),
                    QColor("#89b4fa"), QColor("#cba6f7"), QColor("#94e2d5"), QColor("#cdd6f4")
                ]
                self.current_format.setForeground(colors[p - 30])
            elif 90 <= p <= 97:
                bright_colors = [
                    QColor("#585b70"), QColor("#f38ba8"), QColor("#a6e3a1"), QColor("#a6e3a1"),
                    QColor("#89b4fa"), QColor("#cba6f7"), QColor("#94e2d5"), QColor("#ffffff")
                ]
                self.current_format.setForeground(bright_colors[p - 90])
            elif p == 39:
                self.current_format.clearForeground()

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        cursor = self.textCursor()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                if key == Qt.Key.Key_C:
                    self.copy()
                    event.accept()
                    return
                elif key == Qt.Key.Key_V:
                    self.paste()
                    event.accept()
                    return
                elif key == Qt.Key.Key_X:
                    self.cut()
                    event.accept()
                    return
                elif key == Qt.Key.Key_A:
                    self.selectAll()
                    event.accept()
                    return
            elif key == Qt.Key.Key_C:
                if self.master_fd is not None:
                    try:
                        os.write(self.master_fd, b"\x03")
                    except OSError:
                        pass
                elif hasattr(self, "process"):
                    self.process.write(b"\x03")
                event.accept()
                return

        if sys.platform == "win32":
            super().keyPressEvent(event)
            event.accept()
            return

        if self.master_fd is not None:
            try:
                if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                    self.is_password_prompt = False
                    os.write(self.master_fd, b"\n")
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    self.setTextCursor(cursor)
                elif key == Qt.Key.Key_Backspace:
                    if cursor.position() > self.input_start_pos:
                        cursor.deletePreviousChar()
                        os.write(self.master_fd, b"\x7f")
                elif key == Qt.Key.Key_Tab:
                    os.write(self.master_fd, b"\t")
                elif key == Qt.Key.Key_Up:
                    os.write(self.master_fd, b"\x1b[A")
                elif key == Qt.Key.Key_Down:
                    os.write(self.master_fd, b"\x1b[B")
                elif key == Qt.Key.Key_Right:
                    if cursor.position() < self.document().characterCount() - 1:
                        cursor.movePosition(QTextCursor.MoveOperation.Right)
                        self.setTextCursor(cursor)
                        os.write(self.master_fd, b"\x1b[C")
                elif key == Qt.Key.Key_Left:
                    if cursor.position() > self.input_start_pos:
                        cursor.movePosition(QTextCursor.MoveOperation.Left)
                        self.setTextCursor(cursor)
                        os.write(self.master_fd, b"\x1b[D")
                else:
                    text = event.text()
                    if text and text.isprintable():
                        if not self.is_password_prompt:
                            cursor.insertText(text, self.current_format)
                        os.write(self.master_fd, text.encode("utf-8"))
            except OSError:
                pass
        event.accept()

    def paste(self):
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text()
        if text and self.master_fd is not None:
            try:
                cursor = self.textCursor()
                if not self.is_password_prompt:
                    cursor.insertText(text, self.current_format)
                os.write(self.master_fd, text.encode("utf-8"))
            except OSError:
                pass

    def write_command(self, cmd: str):
        if sys.platform != "win32" and self.master_fd is not None:
            os.write(self.master_fd, (cmd + "\n").encode("utf-8"))
        elif sys.platform == "win32" and hasattr(self, "process"):
            self.process.write((cmd + "\n").encode("utf-8"))
            
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
            }
            QMenu::item:selected {
                background-color: #313244;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #89b4fa;
                margin: 4px 8px;
            }
        """)

        copy_act = menu.addAction("Copy\tCtrl + Shift + C")
        copy_act.triggered.connect(self.copy)
        cut_act = menu.addAction("Cut\tCtrl + X")
        cut_act.triggered.connect(self.cut)
        paste_act = menu.addAction("Paste\tCtrl + Shift + V")
        paste_act.triggered.connect(self.paste)
        
        menu.addSeparator()
        select_act = menu.addAction("Select All\tCtrl + A")
        select_act.triggered.connect(self.selectAll)

        menu.exec(self.mapToGlobal(pos))


class AntimatterTerminal(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.term = NativeTerminalWidget(self)
        layout.addWidget(self.term)

    def set_focus(self):
        self.term.setFocus()

    def write(self, data: bytes):
        self.term.write_command(data.decode("utf-8", errors="ignore").strip())