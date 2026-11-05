import codecs
import platform
from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit
from PyQt6.QtGui import QTextCursor

class AntimatterTerminal(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.output_box = QPlainTextEdit()
        self.output_box.setReadOnly(True)
        self.output_box.setMaximumBlockCount(5000)
        self.output_box.setStyleSheet(
            "background-color: #19191a; color: white; border: none; border-top-left-radius: 8px; border-top-right-radius: 8px; font-family: 'Consolas', 'Cantarell'; font-size: 14px;"
        )
        layout.addWidget(self.output_box)
        self.output_box.appendPlainText("-- Comical Antimatter v.1.7 Alpha --\n==========================================================\nCodeviewer module v.4.0 - Stable: Initialized\nTerminal module v.2.0 - Beta: Initialized\n==========================================================\n-- Ready for execution --\n==========================================================\n")

        self.term_entry = QLineEdit()
        self.term_entry.setPlaceholderText("Waiting for orders...")
        self.term_entry.setStyleSheet("background-color: #19191a; color: #cdd6f4; border: none; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; padding: 4px 8px; font-family: Consolas; font-size: 14px;")
        self.term_entry.returnPressed.connect(self._send_command)
        self.term_entry.installEventFilter(self)
        layout.addWidget(self.term_entry)

        self.history = []
        self.history_pos = 0
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)

        if platform.system() == "Windows":
            self.process.start("cmd.exe")
        else:
            self.process.start("bash", ["-i"])

    def eventFilter(self, obj, event):
        if obj is self.term_entry and event.type() == event.Type.KeyPress and self.history:
            if event.key() == Qt.Key.Key_Up:
                self.history_pos = max(0, self.history_pos - 1)
                self.term_entry.setText(self.history[self.history_pos])
                return True
            if event.key() == Qt.Key.Key_Down:
                self.history_pos = min(len(self.history), self.history_pos + 1)
                self.term_entry.setText(self.history[self.history_pos] if self.history_pos < len(self.history) else "")
                return True
        return super().eventFilter(obj, event)

    def _send_command(self):
        cmd = self.term_entry.text()
        if not cmd:
            return

        if not self.history or self.history[-1] != cmd:
            self.history.append(cmd)
        self.history_pos = len(self.history)
        self.term_entry.clear()
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self._restart_shell()
        full_cmd = (cmd + "\n").encode("utf-8")
        self.process.write(full_cmd)

    def _restart_shell(self):
        if platform.system() == "Windows":
            self.process.start("cmd.exe")
        else:
            self.process.start("bash", ["-i"])

    def _handle_stdout(self):
        data = self.decoder.decode(bytes(self.process.readAllStandardOutput().data()))
        if data:
            self.output_box.moveCursor(QTextCursor.MoveOperation.End)
            self.output_box.insertPlainText(data)
            self.output_box.moveCursor(QTextCursor.MoveOperation.End)

    def set_focus(self):
        self.term_entry.setFocus()

    def shutdown(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
