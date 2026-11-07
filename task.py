import subprocess
import platform
from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox

BASE_DIR = Path(__file__).resolve().parent

def is_sandboxed() -> bool:
    return "FLATPAK_ID" in os.environ or Path("/.flatpak-info").exists()

def compile():
    build_template, _ = QFileDialog.getOpenFileName(None, "Choose build template to use", "", "Text file (*.txt);;All files (*.*)")
    dest = QFileDialog.getExistingDirectory(None, "Select destination folder")
    if build_template and dest:
        try:
            with open(build_template, "r", encoding="utf-8") as f:
                content = f.read().strip()
            
            if is_sandboxed():
                full_cmd = ["flatpak-spawn", "--host", "bash", "-c", content]
            else:
                full_cmd = content

            subprocess.run(full_cmd, shell=not is_sandboxed(), cwd=dest, text=True, check=True)
            QMessageBox.information(None, "Build Successful", "Build software successful !")
        except Exception as e:
            QMessageBox.critical(None, "Build Error", f"Build failed:\n{e}")