import shlex
import subprocess
import platform
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QMessageBox

BASE_DIR = Path(__file__).resolve().parent


class _BuildSignals(QObject):
    finished = pyqtSignal(bool, str)


_signals = _BuildSignals()


def _report(ok, detail):
    if ok:
        QMessageBox.information(None, "Build Successful", "Build software successful !")
    else:
        QMessageBox.critical(None, "Build Error", f"Build failed:\n{detail}")


_signals.finished.connect(_report)


def run_command(path):
    if platform.system() == "Windows":
        return f'python "{path}"'
    return f"python3 {shlex.quote(path)}"


def run():
    path, _ = QFileDialog.getOpenFileName(None, "Choose file to run", "", "Python (*.py);;All files (*.*)")
    if path:
        subprocess.Popen(run_command(path), shell=True)

def _build(content, dest):
    try:
        result = subprocess.run(content, shell=True, cwd=dest, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception as e:
        _signals.finished.emit(False, str(e))
        return
    if result.returncode == 0:
        _signals.finished.emit(True, "")
    else:
        detail = (result.stderr or result.stdout or "").strip()[-1500:]
        _signals.finished.emit(False, detail or f"Command exited with code {result.returncode}")

def compile():
    build_template, _ = QFileDialog.getOpenFileName(None, "Choose build template to use", "", "Text file (*.txt);;All files (*.*)")
    if not build_template:
        return
    dest = QFileDialog.getExistingDirectory(None, "Select destination folder")
    if build_template and dest:
        try:
            with open(build_template, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(None, "Build Error", f"Build failed:\n{e}")
            return
        threading.Thread(target=_build, args=(content, dest), daemon=True).start()
