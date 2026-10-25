import subprocess
import platform
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox

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