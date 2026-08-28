import subprocess
import platform
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit, QFileDialog, QMessageBox

BASE_DIR = Path(__file__).resolve().parent

def run():
    path, _ = QFileDialog.getOpenFileName(None, "Choose file to run", "", "Python (*.py);;All files (*.*)")
    if path:
        cmd = f'python "{path}"' if platform.system() == "Windows" else f"python3 {path}"
        subprocess.run(cmd, shell=True)

def compile():
    build_template, _ = QFileDialog.getOpenFileName(None, "Choose build template to use", "", "Text file (*.txt);;All files (*.*)")
    dest = QFileDialog.getExistingDirectory(None, "Select destination folder")
    if build_template and dest:
        try:
            with open(build_template, "r", encoding="utf-8") as f:
                content = f.read()
                subprocess.run(f"{content}", shell=True, cwd=dest, text=True, check=True)
            QMessageBox.information(None, "Build Successful", "Build software successful !")
        except Exception as e:
            QMessageBox.critical(None, "Build Error", f"Build failed:\n{e}")

class StandaloneTerminal(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(750, 600)
        self.setWindowTitle("Terminal - Comical Antimatter 2026")

        layout = QVBoxLayout(self)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Type a command")
        self.entry.returnPressed.connect(self.command)
        layout.addWidget(self.entry)

    def command(self):
        en = self.entry.text()
        if not en: return

        self.output.appendPlainText(f"\n> {en}\n")
        try:
            out = subprocess.run(en, shell=True, capture_output=True, text=True)
            self.output.appendPlainText(out.stdout + out.stderr)
        except Exception as e:
            self.output.appendPlainText(f"Erreur : {str(e)}")

        self.entry.clear()

_term_window = None
def Terminal():
    global _term_window
    _term_window = StandaloneTerminal()
    _term_window.show()
