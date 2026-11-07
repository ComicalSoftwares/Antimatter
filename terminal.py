import sys
import os
import pty
import fcntl
import re
from pathlib import Path
from PyQt6.QtCore import QSocketNotifier, Qt
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QPlainTextEdit, QMenu

def is_sandboxed() -> bool:
    return "FLATPAK_ID" in os.environ or Path("/.flatpak-info").exists()

# Combined regex to match and filter out OSC metadata and CSI escape codes
COMBINED_ESCAPE = re.compile(r'''
    (\x1b\].*?(?:\x07|\x1b\\))|    # OSC sequences (window title, shell integration)
    (\x1b\[([?0-9;]*)([A-Za-z]))   # CSI sequences (colors, cursor, modes)
''', re.VERBOSE)

PROMPT_PATTERN = re.compile(r'\[[\w\-]+@[\w\-]+\s+[^\]]+\][\$#]')

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
        self.prompt_end_position = 0
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
                    if is_sandboxed():
                        os.execvp("flatpak-spawn", ["flatpak-spawn", "--host", "env", "TERM=xterm-256color", "bash"])
                    else:
                        os.execvp("bash", ["bash"])
                    sys.exit(0)
                else:
                    fcntl.fcntl(self.master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
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
        
        last_idx = 0
        for match in COMBINED_ESCAPE.finditer(text):
            start, end = match.span()
            if start > last_idx:
                self._insert_plain_chunk(cursor, text[last_idx:start])
            
            osc_seq, csi_seq, params_str, command = match.groups()
            if osc_seq:
                pass
            elif csi_seq:
                if command == 'm':
                    self.apply_sgr(params_str)
                elif command == 'J':
                    if params_str in ('2', '2J', '0J', ''):
                        self.clear()
                        self.prompt_end_position = 0
            
            last_idx = end

        if last_idx < len(text):
            self._insert_plain_chunk(cursor, text[last_idx:])

        # Update prompt input boundary
        self.prompt_end_position = self.document().characterCount() - 1
        self.ensureCursorVisible()

    def _insert_plain_chunk(self, cursor, chunk):
        i = 0
        while i < len(chunk):
            if chunk[i] == '\b':
                cursor.deletePreviousChar()
                i += 1
                if i + 1 < len(chunk) and chunk[i] == ' ' and chunk[i+1] == '\b':
                    i += 2
            else:
                prompt_match = PROMPT_PATTERN.match(chunk, i)
                if prompt_match:
                    p_text = prompt_match.group(0)
                    green_format = QTextCharFormat(self.current_format)
                    green_format.setForeground(QColor("#a6e3a1"))
                    cursor.insertText(p_text, green_format)
                    i += len(p_text)
                else:
                    cursor.insertText(chunk[i], self.current_format)
                    i += 1

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
                    QColor("#585b70"), QColor("#f38ba8"), QColor("#a6e3a1"), QColor("#f9e2af"),
                    QColor("#89b4fa"), QColor("#cba6f7"), QColor("#94e2d5"), QColor("#ffffff")
                ]
                self.current_format.setForeground(bright_colors[p - 90])
            elif p == 39:
                self.current_format.clearForeground()

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()

        cursor = self.textCursor()

        # Prevent backspace/delete if nothing is typed or if selection crosses into prompt
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            if cursor.hasSelection() and cursor.selectionStart() < self.prompt_end_position:
                event.ignore()
                return
            if not cursor.hasSelection() and cursor.position() <= self.prompt_end_position:
                event.ignore()
                return

        # Snap cursor to end if typing before the prompt area
        if not cursor.hasSelection() and cursor.position() < self.prompt_end_position:
            if key not in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down, 
                           Qt.Key.Key_Home, Qt.Key.Key_End) and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.setTextCursor(cursor)

        if sys.platform == "win32":
            super().keyPressEvent(event)
        else:
            if self.master_fd is not None:
                try:
                    if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                        os.write(self.master_fd, b"\n")
                    elif key == Qt.Key.Key_Backspace:
                        os.write(self.master_fd, b"\x7f")
                    elif key == Qt.Key.Key_Tab:
                        os.write(self.master_fd, b"\t")
                    elif key == Qt.Key.Key_Up:
                        os.write(self.master_fd, b"\x1b[A")
                    elif key == Qt.Key.Key_Down:
                        os.write(self.master_fd, b"\x1b[B")
                    elif key == Qt.Key.Key_Right:
                        os.write(self.master_fd, b"\x1b[C")
                    elif key == Qt.Key.Key_Left:
                        if cursor.position() > self.prompt_end_position:
                            os.write(self.master_fd, b"\x1b[D")
                    elif text:
                        os.write(self.master_fd, text.encode("utf-8"))
                except OSError:
                    pass
        event.accept()

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

        copy_act = menu.addAction("Copy\tCtrl + C")
        copy_act.triggered.connect(self.copy)
        cut_act = menu.addAction("Cut\tCtrl + X")
        cut_act.triggered.connect(self.cut)
        paste_act = menu.addAction("Paste\tCtrl + V")
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
