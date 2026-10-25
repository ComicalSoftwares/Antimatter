import platform
from PyQt6.QtCore import QProcess
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
        self.output_box.setStyleSheet(
            "background-color: #19191a; color: white; border: none; font-family: 'Consolas', 'Cantarell'; font-size: 14px;"
        )
        layout.addWidget(self.output_box)
        self.output_box.appendPlainText("-- Comical Antimatter v.1.7 Alpha --\n==========================================================\nCodeviewer module v.4.0 - Stable: Initialized\nTerminal module v.2.0 - Beta: Initialized\n==========================================================\n-- Ready for execution --\n==========================================================\n")

        self.term_entry = QLineEdit()
        self.term_entry.setPlaceholderText("Waiting for orders...")
        self.term_entry.setStyleSheet("background-color: #19191a; color: #cdd6f4; border: none; padding: 4px; font-family: Consolas; font-size: 14px;")
        self.term_entry.returnPressed.connect(self._send_command)
        layout.addWidget(self.term_entry)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)

        if platform.system() == "Windows":
            self.process.start("cmd.exe")
        else:
            self.process.start("bash", ["-i"])

        

    def _send_command(self):
        cmd = self.term_entry.text()
        if not cmd:
            return
        
        self.term_entry.clear()
        full_cmd = (cmd + "\n").encode("utf-8")
        self.process.write(full_cmd)

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        if data:
            self.output_box.moveCursor(QTextCursor.MoveOperation.End)
            self.output_box.insertPlainText(data)

    def _handle_stderr(self):
        raw_data = self.process.readAllStandardError().data().decode("utf-8", errors="ignore")
    
        if raw_data:
            self.output_box.moveCursor(QTextCursor.MoveOperation.End)
            self.output_box.insertPlainText(raw_data)

    def set_focus(self):
        self.term_entry.setFocus()
