import sys
import os
import platform
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QTextBrowser,
    QCheckBox, QRadioButton, QMessageBox, QProgressBar
)

import slaves

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = str(BASE_DIR / "AppIcon.png")

class AntimatterInstaller(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Comical Antimatter Setup")
        self.resize(700, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #363636;
                color: #cdd6f4;
                font-family: 'Consolas', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #ffffff;
            }
            QPushButton#primaryBtn {
                background-color: #5400ba;
                color: #ffffff;
            }
            QPushButton#primaryBtn:hover {
                background-color: #6a0dad;
            }
            QTextBrowser {
                background-color: #19191a;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 10px;
            }
            QProgressBar {
                background-color: #19191a;
                border: 1px solid #313244;
                border-radius: 4px;
                text-align: center;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background-color: #5400ba;
                border-radius: 3px;
            }
        """)

        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)

        self._build_welcome_page()
        self._build_license_page()
        self._build_config_page()
        self._build_progress_page()

    def _create_header(self, title_text: str) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(10)

        if os.path.exists(ICON_PATH):
            logo = QLabel()
            logo.setPixmap(QPixmap(ICON_PATH).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(logo)

        title = QLabel(title_text)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        vbox.addWidget(title)
        return container

    def _build_welcome_page(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 20, 20, 20)

        vbox.addWidget(self._create_header("Welcome to Antimatter Setup"))

        desc = QLabel("This wizard will guide you through installing Antimatter on your system.\nClick 'Start Setup' to proceed.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #a6adc8; font-size: 14px;")
        vbox.addWidget(desc)
        vbox.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        start_btn = QPushButton("Start Setup")
        start_btn.setObjectName("primaryBtn")
        start_btn.setFixedWidth(140)
        start_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_layout.addWidget(start_btn)
        vbox.addLayout(btn_layout)

        self.stack.addWidget(page)

    def _build_license_page(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(10, 10, 10, 10)

        header = QLabel("License Agreement")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        vbox.addWidget(header)

        lic_browser = QTextBrowser()
        lic_browser.setPlainText('''
            MIT License

Copyright (c) 2026 Anir El Haddaj (ComicalSoftwares)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

        ''')
        vbox.addWidget(lic_browser)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        decline_btn = QPushButton("I decline, cancel setup")
        decline_btn.clicked.connect(self.close)

        accept_btn = QPushButton("I accept, continue")
        accept_btn.setObjectName("primaryBtn")
        accept_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        btn_layout.addWidget(decline_btn)
        btn_layout.addWidget(accept_btn)
        vbox.addLayout(btn_layout)

        self.stack.addWidget(page)

    def _build_config_page(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 20, 20, 20)
        vbox.setSpacing(12)

        header = QLabel("Installation Scope & Optional Dependencies")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        vbox.addWidget(header)

        scope_label = QLabel("Installation Scope:")
        scope_label.setStyleSheet("font-weight: bold; color: #8a79a3;")
        vbox.addWidget(scope_label)

        self.user_radio = QRadioButton("User-only (Recommended)")
        self.user_radio.setChecked(True)
        self.system_radio = QRadioButton("System-wide (Requires Administrator privileges)")
        vbox.addWidget(self.user_radio)
        vbox.addWidget(self.system_radio)

        dep_label = QLabel("Optional Components:")
        dep_label.setStyleSheet("font-weight: bold; color: #8a79a3; margin-top: 10px;")
        vbox.addWidget(dep_label)

        self.chk_pyflakes = QCheckBox("pyflakes (Static syntax & issue checker)")
        self.chk_git = QCheckBox("Git CLI integration tools")
        self.chk_pyflakes.setChecked(True)

        vbox.addWidget(self.chk_pyflakes)
        vbox.addWidget(self.chk_git)

        vbox.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        install_btn = QPushButton("Install Now")
        install_btn.setObjectName("primaryBtn")
        install_btn.clicked.connect(self._run_install)

        btn_layout.addWidget(back_btn)
        btn_layout.addWidget(install_btn)
        vbox.addLayout(btn_layout)

        self.stack.addWidget(page)

    def _build_progress_page(self):
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(30, 40, 30, 40)
        vbox.setSpacing(20)

        vbox.addWidget(self._create_header("Installing Antimatter"))

        self.status_label = QLabel("Initializing setup...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        vbox.addWidget(self.progress_bar)

        vbox.addStretch()
        self.stack.addWidget(page)

    def _run_install(self):
        scope = "system" if self.system_radio.isChecked() else "user"
        deps = []
        if self.chk_pyflakes.isChecked():
            deps.append("pyflakes")
        if self.chk_git.isChecked():
            deps.append("git")

        self.stack.setCurrentIndex(3)

        self.worker = install_backend.InstallWorker(scope, deps, BASE_DIR, ICON_PATH)
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.finished.connect(self._install_completed)
        self.worker.start()

    def _update_progress(self, message: str, value: int):
        self.status_label.setText(message)
        self.progress_bar.setValue(value)

    def _install_completed(self, success: bool, message: str):
        if success:
            QMessageBox.information(self, "Setup Complete", message)
            self.close()
        else:
            QMessageBox.critical(self, "Setup Error", f"Installation failed:\n{message}")
            self.stack.setCurrentIndex(2)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if platform.system() != "Windows":
        QMessageBox.critical(
            None,
            "Unsupported Platform",
            "This installer is designed exclusively for Windows operating systems."
        )
        sys.exit(1)

    wizard = AntimatterInstaller()
    wizard.show()
    sys.exit(app.exec())