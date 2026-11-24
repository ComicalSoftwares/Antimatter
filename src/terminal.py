import os
import struct
import sys

import pyte
from PyQt6.QtCore import QObject, QSocketNotifier, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QGuiApplication, QPen
from PyQt6.QtWidgets import QMenu, QVBoxLayout, QWidget

import theme

IS_WINDOWS = sys.platform == "win32"

if not IS_WINDOWS:
    import fcntl
    import pty
    import termios
else:
    try:
        from winpty import PtyProcess
    except ImportError:
        PtyProcess = None

PALETTE = {
    "black": "#1e1e1e", "red": "#f38ba8", "green": "#a6e3a1", "brown": "#f9e2af",
    "yellow": "#f9e2af", "blue": "#89b4fa", "magenta": "#cba6f7", "cyan": "#94e2d5",
    "white": "#bac2de",
    "brightblack": "#585b70", "brightred": "#f38ba8", "brightgreen": "#a6e3a1",
    "brightbrown": "#f9e2af", "brightyellow": "#f9e2af", "brightblue": "#89b4fa",
    "brightmagenta": "#cba6f7", "brightcyan": "#94e2d5", "brightwhite": "#ffffff",
}
DEFAULT_FG = "#d4d4d4"
DEFAULT_BG = "#1e1e1e"


def resolve_color(value, default):
    if not value or value == "default":
        return default
    if isinstance(value, str) and len(value) == 6 and all(c in "0123456789abcdefABCDEF" for c in value):
        return "#" + value
    return PALETTE.get(value, default)


class TerminalScreen(pyte.HistoryScreen):
    def __init__(self, columns, lines, history=5000):
        super().__init__(columns, lines, history=history, ratio=0.3)

class UnixPtyBackend(QObject):
    data_received = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, shell_cmd=None, parent=None):
        super().__init__(parent)
        self.master_fd = None
        self.pid = None
        self.notifier = None
        self.shell_cmd = shell_cmd or [os.environ.get("SHELL", "/bin/bash")]

    def start(self):
        os.environ["TERM"] = "xterm-256color"
        pid, master_fd = pty.fork()
        if pid == 0:
            try:
                os.execvp(self.shell_cmd[0], self.shell_cmd)
            except Exception:
                os._exit(1)
        self.pid = pid
        self.master_fd = master_fd
        fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)
        self.notifier = QSocketNotifier(master_fd, QSocketNotifier.Type.Read)
        self.notifier.activated.connect(self._on_readable)

    def _on_readable(self):
        try:
            data = os.read(self.master_fd, 65536)
        except OSError:
            self.notifier.setEnabled(False)
            self.closed.emit()
            return
        if not data:
            self.notifier.setEnabled(False)
            self.closed.emit()
            return
        self.data_received.emit(data.decode("utf-8", errors="replace"))

    def write(self, text):
        if self.master_fd is None:
            return
        try:
            os.write(self.master_fd, text.encode("utf-8"))
        except OSError:
            pass

    def resize(self, rows, cols):
        if self.master_fd is None:
            return
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            pass

    def close(self):
        if self.notifier:
            self.notifier.setEnabled(False)
        if self.pid:
            try:
                os.kill(self.pid, 15)
            except OSError:
                pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass


class _WindowsReaderThread(QThread):
    data = pyqtSignal(str)
    finished_reading = pyqtSignal()

    def __init__(self, process):
        super().__init__()
        self.process = process
        self._running = True

    def run(self):
        while self._running:
            try:
                chunk = self.process.read(4096)
            except Exception:
                break
            if not chunk:
                break
            self.data.emit(chunk)
        self.finished_reading.emit()

    def stop(self):
        self._running = False


class WindowsPtyBackend(QObject):
    data_received = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, shell_cmd=None, parent=None):
        super().__init__(parent)
        if PtyProcess is None:
            raise RuntimeError(
                "Module pywinpty is required for the terminal module to work on Windows. "
                "Try installing it with: 'pip install pywinpty'"
            )
        self.shell_cmd = shell_cmd or (os.environ.get("COMSPEC") or "cmd.exe")
        self.process = None
        self.reader = None

    def start(self):
        self.process = PtyProcess.spawn(self.shell_cmd)
        self.reader = _WindowsReaderThread(self.process)
        self.reader.data.connect(self.data_received.emit)
        self.reader.finished_reading.connect(self.closed.emit)
        self.reader.start()

    def write(self, text):
        if self.process is None:
            return
        try:
            self.process.write(text)
        except Exception:
            pass

    def resize(self, rows, cols):
        if self.process is None:
            return
        try:
            self.process.setwinsize(rows, cols)
        except Exception:
            pass

    def close(self):
        if self.reader:
            self.reader.stop()
        if self.process:
            try:
                self.process.close()
            except Exception:
                pass


def make_backend(shell_cmd=None):
    return WindowsPtyBackend(shell_cmd) if IS_WINDOWS else UnixPtyBackend(shell_cmd)

class TerminalWidget(QWidget):
    def __init__(self, parent=None, shell_cmd=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setMouseTracking(False)

        self.font = theme.mono_font(11)
        self.setFont(self.font)
        metrics = QFontMetrics(self.font)
        self.char_w = metrics.horizontalAdvance("M")
        self.char_h = metrics.height()

        self.cols = 80
        self.rows = 24
        self.screen = TerminalScreen(self.cols, self.rows)
        self.stream = pyte.Stream(self.screen)

        self.backend = make_backend(shell_cmd)
        self.backend.data_received.connect(self._on_data)
        self.backend.closed.connect(self._on_closed)
        self.backend.start()
        self.backend.resize(self.rows, self.cols)

        self._selecting = False
        self._sel_start = None
        self._sel_end = None
        self._scroll_offset = 0

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _on_data(self, text):
        self.stream.feed(text)
        self._scroll_offset = 0
        self.update()

    def _on_closed(self):
        self.update()

    def write_command(self, cmd):
        self.backend.write(cmd + "\r")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.char_w <= 0 or self.char_h <= 0:
            return
        cols = max(10, self.width() // self.char_w)
        rows = max(3, self.height() // self.char_h)
        if (cols, rows) != (self.cols, self.rows):
            self.cols, self.rows = cols, rows
            self.screen.resize(rows, cols)
            self.backend.resize(rows, cols)
            self.update()

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QPainterPath, QColor
        from PyQt6.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        painter.setClipPath(path)

        painter.fillRect(self.rect(), QColor(DEFAULT_BG))
        painter.setFont(self.font)

        lines = self._history_lines() if self._scroll_offset else \
            [self.screen.buffer[y] for y in range(self.screen.lines)]

        for row, line in enumerate(lines):
            y_top = row * self.char_h
            for col in range(self.cols):
                char = line.get(col) if hasattr(line, "get") else (line[col] if col in line else None)
                text = char.data if char else " "
                fg = resolve_color(char.fg if char else "default", DEFAULT_FG)
                bg = resolve_color(char.bg if char else "default", DEFAULT_BG)
                if char and char.reverse:
                    fg, bg = bg, fg
                x = col * self.char_w
                if bg != DEFAULT_BG:
                    painter.fillRect(x, y_top, self.char_w, self.char_h, QColor(bg))
                if self._in_selection(row, col):
                    painter.fillRect(x, y_top, self.char_w, self.char_h, QColor("#3a3a5a"))
                if text and text != " ":
                    painter.setPen(QPen(QColor(fg)))
                    painter.drawText(x, y_top + self.char_h - 3, text)

        if not self._scroll_offset and not self.screen.cursor.hidden:
            cx, cy = self.screen.cursor.x, self.screen.cursor.y
            painter.fillRect(cx * self.char_w, cy * self.char_h, self.char_w, self.char_h,
                              QColor(255, 255, 255, 90))
        painter.end()

    def _history_lines(self):
        hist = list(self.screen.history.top)
        start = max(0, len(hist) - self._scroll_offset * self.rows)
        page = hist[start:start + self.rows]
        while len(page) < self.rows:
            page.append({})
        return page

    def _cell_at(self, pos):
        col = max(0, min(self.cols - 1, pos.x() // self.char_w))
        row = max(0, min(self.rows - 1, pos.y() // self.char_h))
        return row, col

    def _in_selection(self, row, col):
        if not self._sel_start or not self._sel_end:
            return False
        a, b = sorted([self._sel_start, self._sel_end])
        return a <= (row, col) <= b

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            self._sel_start = self._cell_at(event.position().toPoint())
            self._sel_end = self._sel_start
            self.grabMouse()
            self.update()

    def mouseReleaseEvent(self, event):
        if self._selecting:
            self._selecting = False
            self.releaseMouse()

    def mouseMoveEvent(self, event):
        if self._selecting and (event.buttons() & Qt.MouseButton.LeftButton):
            self._sel_end = self._cell_at(event.position().toPoint())
            self.update()
        elif self._selecting:
            self._selecting = False
        
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._scroll_offset = min(self._scroll_offset + 1, max(0, len(self.screen.history.top) // self.rows))
        else:
            self._scroll_offset = max(0, self._scroll_offset - 1)
        self.update()

    def selected_text(self):
        if not self._sel_start or not self._sel_end:
            return ""
        a, b = sorted([self._sel_start, self._sel_end])
        out = []
        for row in range(a[0], b[0] + 1):
            line = self.screen.buffer.get(row, {})
            start_col = a[1] if row == a[0] else 0
            end_col = b[1] if row == b[0] else self.cols - 1
            text = "".join((line[c].data if c in line else " ") for c in range(start_col, end_col + 1))
            out.append(text.rstrip())
        return "\n".join(out)
        
    def select_all(self):
        total_rows = self.rows + len(self.screen.history.top)
        self._sel_start = (0, 0)
        self._sel_end = (total_rows - 1, self.cols - 1)
        self.update()

    KEY_SEQUENCES = {
        Qt.Key.Key_Up: "\x1b[A", Qt.Key.Key_Down: "\x1b[B",
        Qt.Key.Key_Right: "\x1b[C", Qt.Key.Key_Left: "\x1b[D",
        Qt.Key.Key_Home: "\x1b[H", Qt.Key.Key_End: "\x1b[F",
        Qt.Key.Key_PageUp: "\x1b[5~", Qt.Key.Key_PageDown: "\x1b[6~",
        Qt.Key.Key_Delete: "\x1b[3~", Qt.Key.Key_Insert: "\x1b[2~",
        Qt.Key.Key_F1: "\x1bOP", Qt.Key.Key_F2: "\x1bOQ",
        Qt.Key.Key_F3: "\x1bOR", Qt.Key.Key_F4: "\x1bOS",
    }

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()

        if mods & Qt.KeyboardModifier.ControlModifier and mods & Qt.KeyboardModifier.ShiftModifier:
            if key == Qt.Key.Key_C:
                QGuiApplication.clipboard().setText(self.selected_text())
                return
            if key == Qt.Key.Key_V:
                self.backend.write(QGuiApplication.clipboard().text())
                return
            if key == Qt.Key.Key_A:
                self.select_all()
                return

        if mods & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_C:
            self.backend.write("\x03")
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.backend.write("\r"); return
        if key == Qt.Key.Key_Backspace:
            self.backend.write("\x7f"); return
        if key == Qt.Key.Key_Tab:
            self.backend.write("\t"); return
        if key in self.KEY_SEQUENCES:
            self.backend.write(self.KEY_SEQUENCES[key]); return

        if mods & Qt.KeyboardModifier.ControlModifier:
            text = event.text()
            if text:
                code = ord(text.upper()) - 64
                if 0 <= code < 32:
                    self.backend.write(chr(code)); return

        text = event.text()
        if text:
            self.backend.write(text)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(theme.context_menu)
        copy_act = menu.addAction("Copy\tCtrl+Shift+C")
        copy_act.triggered.connect(lambda: QGuiApplication.clipboard().setText(self.selected_text()))
        paste_act = menu.addAction("Paste\tCtrl+Shift+V")
        paste_act.triggered.connect(lambda: self.backend.write(QGuiApplication.clipboard().text()))
        menu.addSeparator()
        select_act = menu.addAction("Select All\tCtrl+Shift+A")
        select_act.triggered.connect(self.select_all)
        menu.exec(self.mapToGlobal(pos))

    def shutdown(self):
        self.backend.close()


class AntimatterTerminal(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.term = TerminalWidget(self)
        layout.addWidget(self.term)

    def set_focus(self):
        self.term.setFocus()

    def write(self, data: bytes):
        self.term.write_command(data.decode("utf-8", errors="ignore").strip())

    def shutdown(self):
        self.term.shutdown()