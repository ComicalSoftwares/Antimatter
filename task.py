import subprocess
import os
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

BASE_DIR = Path(__file__).resolve().parent

def is_sandboxed() -> bool:
    return "FLATPAK_ID" in os.environ or Path("/.flatpak-info").exists()

class BuildWorker(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, full_cmd, shell, cwd):
        super().__init__()
        self.full_cmd = full_cmd
        self.shell = shell
        self.cwd = cwd

    def run(self):
        try:
            subprocess.run(self.full_cmd, shell=self.shell, cwd=self.cwd, text=True, check=True)
            self.finished.emit(True, "Build software successful !")
        except Exception as e:
            self.finished.emit(False, str(e))

def compile():
    build_template, _ = QFileDialog.getOpenFileName(None, "Choose build template to use", "", "Text file (*.txt);;All files (*.*)")
    dest = QFileDialog.getExistingDirectory(None, "Select destination folder")
    if not build_template or not dest:
        return

    try:
        with open(build_template, "r", encoding="utf-8") as f:
            content = f.read().strip()

        sandboxed = is_sandboxed()
        if sandboxed:
            full_cmd = f"flatpak-spawn --host {content}"
            shell = False
        else:
            full_cmd = content
            shell = True

        progress = QProgressDialog("Building project, please wait...", None, 0, 0, None)
        progress.setWindowTitle("Compiling project...")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setCancelButton(None)
        progress.setRange(0, 0)
        progress.show()

        worker = BuildWorker(full_cmd, shell, dest)

        def on_finished(success, message):
            progress.close()
            if success:
                QMessageBox.information(None, "Build Successful", message)
            else:
                QMessageBox.critical(None, "Build Error", f"Build failed:\n{message}")

        worker.finished.connect(on_finished)
        worker.start()

        compile._active_worker = worker

    except Exception as e:
        QMessageBox.critical(None, "Build Error", f"Failed to initialize build:\n{e}")
