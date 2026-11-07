# Antimatter's utilities module (which I forgot existed)

import json
import webbrowser
import platform
import subprocess
import urllib.request
import re
from PyQt6.QtWidgets import QFileDialog, QMessageBox

CURRENT_VERSION = "1.7"

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
        QMessageBox.critical(None, "Error", f"Couldn't configure project: \n{e}")

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
        QMessageBox.critical(None, "Update", f"Failed to check for updates: \n{e}")
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
        res = QMessageBox.question(None, "Update", "Couldn't parse latest release version. Do you want to open pages on Github ?")
        if res == QMessageBox.StandardButton.Yes:
            webbrowser.open(data.get("html_url", "https://github.com/ComicalSoftwares/Antimatter/releases"))
        return

    compare = cmp_ver(latest_version_nums, current_version_nums)
    if compare <= 0:
        QMessageBox.information(None, "Update", "Antimatter is up-to-date.")
    else:
        release_name = data.get("name") or latest_tag
        QMessageBox.information(None, "Update available", f"Version {release_name} is available for download.")
