# Antimatter's utilities module (which I forgot existed)

import json
import webbrowser
import platform
import subprocess
import urllib.request
import re
import os
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QPushButton, QLabel, QGraphicsColorizeEffect, QTextBrowser
from pathlib import Path
from PyQt6.QtCore import Qt
import html

CURRENT_VERSION = "1.7" # The new fire release
BASE_DIR = Path(__file__).resolve().parent

def project():
    folder = QFileDialog.getExistingDirectory(None, "Choose project folder")
    if folder:
        try:
            print(f"Folder: {folder}")
            py_bin = "python" if platform.system() == "Windows" else "python3"
            subprocess.run([py_bin, "-m", "venv", ".venv"], cwd=folder, check=True)
            
            QMessageBox.information(None, "Done", "Project .venv configured successfully!")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Couldn't configure project: \n{e}")
    else:
        QMessageBox.critical(None, "Error", "Couldn't configure project: Invalid Directory")

def docs():
    webbrowser.open("https://antimatter.codelyteam.com/#docs/Quick-Start-Guide")

def update():
    update_url = "https://api.github.com/repos/ComicalSoftwares/Antimatter/releases/latest"
    try:
        with urllib.request.urlopen(update_url, timeout=10) as resp:
            if resp.status != 200:
                QMessageBox.critical(None, "Update", f"Couldn't check for updates (HTTP {resp.status}).")
                return
            data = json.load(resp)
    except Exception as e:
        QMessageBox.critical(None, "Update check failed", f"Failed to check for updates: \n{e}")
        return

    latest_tag = data.get("tag_name") or data.get("name") or ""
    latest_version_nums = re.findall(r'\d+', latest_tag)
    current_version_nums = re.findall(r'\d+', CURRENT_VERSION)

    def cmp_ver(a_list, b_list):
        a = [int(x) for x in a_list]
        b = [int(x) for x in b_list]
        L = max(len(a), len(b))
        a += [0] * (L - len(a))
        b += [0] * (L - len(b))
        if a == b: return 0
        return 1 if a > b else -1

    if not latest_version_nums:
        res = QMessageBox.question(None, "Update check failed", "Couldn't fetch latest release version. Do you want to check the Github repository instead ?")
        if res == QMessageBox.StandardButton.Yes:
            webbrowser.open(data.get("html_url", "https://github.com/ComicalSoftwares/Antimatter"))
        return

    compare = cmp_ver(latest_version_nums, current_version_nums)
    if compare <= 0:
        QMessageBox.information(None, "Update", "Antimatter is up-to-date.")
    else:
        release_name = data.get("name") or latest_tag
        QMessageBox.information(None, "Update available", f"Version {release_name} is available for download.")

def about_window(content, is_html=False):
    dlg = QDialog()
    dlg.resize(650, 550)
    dlg.setWindowTitle("About Antimatter")
    dlg.setStyleSheet("background-color: #363636; color: purple;")
    layout = QVBoxLayout(dlg)
    icon_path = str(BASE_DIR / "AppIcon.png")
    if os.path.exists(icon_path):
        dlg.setWindowIcon(QIcon(icon_path))
    logo_label = QLabel()
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path).scaled(130, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        effect = QGraphicsColorizeEffect(logo_label)
        effect.setColor(QColor("#363636"))
        effect.setStrength(0)
        logo_label.setGraphicsEffect(effect)
    logo_label.setStyleSheet("background: transparent;")
    logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn = QPushButton("Close", dlg)
    btn.setStyleSheet("""
        QPushButton {
            background-color: #1f1f1f;
            color: #cdd6f4;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45475a;
        }
    """)
    btn2 = QPushButton("Visit the Github repository", dlg)
    btn2.setStyleSheet("""
        QPushButton {
            background-color: #1f1f1f;
            color: #cdd6f4;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45475a;
        }
    """)
    title_label = QLabel("Comical Antimatter")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setStyleSheet("color: white; font-family: 'Consolas', 'Cantarell'; font-size: 30px; font-weight: bold; background: transparent;")
    footer_label = QLabel("Version 1.7 - Alpha")
    footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    footer_label.setStyleSheet("color: #8a79a3; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
    footer_label2 = QLabel("This project is open-source and licensed under the MIT license.")
    footer_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
    footer_label2.setStyleSheet("color: white; font-family: 'Consolas', 'Cantarell'; font-size: 13px; background: transparent;")
    about_text = QTextBrowser(dlg)
    if is_html:
        about_text.setHtml(content)
    else:
        about_text.setPlainText(content)
        
    about_text.setReadOnly(True)
    about_text.setStyleSheet("""
        QTextBrowser {
            background-color: #19191a;
            color: #cdd6f4;
            border: None;
            font-family: Consolas;
            font-size: 14px;
            border-radius: 7px;
        }
        QScrollBar:vertical {
            background: #19191a;
            width: 10px;
            margin: 0px;
            border: none;
        }
        QScrollBar:horizontal {
            background: #19191a;
            height: 10px;
            margin: 0px;
            border: none;
        }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #45475a;
            border-radius: 4px;
            min-height: 20px;
            min-width: 20px;
            border: none;
        }
        QScrollBar::handle:hover {
            background: #585b70;
        }
    """)
    btn.clicked.connect(dlg.accept)
    btn2.clicked.connect(lambda: webbrowser.open("https://github.com/ComicalSoftwares/Antimatter/"))
    layout.addWidget(logo_label)
    layout.addWidget(title_label)
    layout.addWidget(footer_label)
    layout.addWidget(footer_label2)
    layout.addWidget(about_text)
    layout.addWidget(btn2)
    layout.addWidget(btn)
    dlg.exec()

def about():
    info = str(BASE_DIR / "about.txt")
    try:
        with open(info, "r", encoding="utf-8") as f:
            content = f.read()

        formatted_lines = []
        for line in content.splitlines():
            safe_line = html.escape(line)
            
            if line.startswith("D"):
                formatted_lines.append(f'<font color="#a6e3a1"><b>- Developed by Project owner:</b></font> {safe_line[1:]}')
            elif line.startswith("C"):
                formatted_lines.append(f'<font color="#a6e3a1"><b>- Co-developed by contributor:</b></font> {safe_line[1:]}')
            elif line.startswith("T"):
                formatted_lines.append(f'<font color="#f38ba8"><b>- Translated by:</b></font> {safe_line[1:]}')
            else:
                formatted_lines.append(f'<font color="#cdd6f4">{safe_line}</font>')

        html_body = f"<pre style='font-family: Consolas;'>{'<br>'.join(formatted_lines)}</pre>"
        about_window(html_body, is_html=True)
    except Exception as e:
        about_window(str(e))
