import subprocess
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QDialog, QVBoxLayout, QPushButton, QTextBrowser
from PyQt6.QtGui import QIcon
import re
import html
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
icon = str(BASE_DIR / "AppIcon.png")

# Git add
def add():
    project_dir = QFileDialog.getExistingDirectory(None, "Select project folder")
    if not project_dir:
        return

    files, ok = QInputDialog.getText(None, "Specify the files to stage (Git add)", "Enter the name of the files that you wish to stage (e.g. main.py test.c):")
    if not ok or not files:
        return
    
    try:
        subprocess.run(f"git add {files}", cwd=project_dir, shell=True, check=True, text=True, capture_output=True)
        QMessageBox.information(None, "Git action successful", f"Action 'git add {files}' completed successfully")
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f"Action 'git add {files}' couldn't be completed for the following reason: {e}")

# Git commit
def commit():
    project_dir = QFileDialog.getExistingDirectory(None, "Select current working directory")
    if not project_dir:
        return
        
    message, ok = QInputDialog.getText(None, "Git Commit", "Enter commit message:")
    if not ok or not message:
        return

    try:
        subprocess.run(f'git commit -m "{message}"', cwd=project_dir, shell=True, check=True, text=True, capture_output=True)
        QMessageBox.information(None, "Git action successful", f'''Action 'git commit -m "{message}"' completed successfully''')
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f'''Action 'git commit -m "{message}"' couldn't be completed for the following reason: {e}''')

# Git remote add origin
def set_repo():
    project_dir = QFileDialog.getExistingDirectory(None, "Select project folder")
    if not project_dir:
        return
        
    url, ok = QInputDialog.getText(None, "Connect to a remote git repository", "Enter the remote repository's URL:")
    if not ok or not url:
        return

    try:
        subprocess.run("git init", cwd=project_dir, shell=True, check=True, text=True, capture_output=True)
        subprocess.run(f'git remote add origin "{url}"', cwd=project_dir, shell=True, check=True, text=True, capture_output=True)
        QMessageBox.information(None, "Git action successful", f'''Action 'git remote add origin "{url}"' completed successfully''')
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f'''Action 'git remote add origin "{url}"' couldn't be completed for the following reason: {e}''')

# Git push
def push():
    project_dir = QFileDialog.getExistingDirectory(None, "Select project folder")
    if not project_dir:
        return

    branch, ok = QInputDialog.getText(None, "Specify the branch to push changes to", "Enter the name of the branch that you wish to push changes to (e.g. main):")
    if not ok or not branch:
        return
    
    try:
        subprocess.run(f"git push origin {branch}", cwd=project_dir, shell=True, check=True, text=True, capture_output=True)
        QMessageBox.information(None, "Git action successful", "Changes pushed to remote repository successfully!")
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f"Push couldn't be completed for the following reason: {e}")

# Git Clone
def clone():
    project_dir = QFileDialog.getExistingDirectory(None, "Select parent destination folder")
    if not project_dir:
        return

    url, ok = QInputDialog.getText(None, "Enter repository URL", "Enter the remote repository's URL:")
    if not ok or not url:
        return

    try:
        subprocess.run(f'git clone "{url}"', cwd=project_dir, shell=True, check=True, text=True, capture_output=True)
        QMessageBox.information(None, "Git action successful", f'''Action 'git clone "{url}"' completed successfully''')
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f'''Action 'git clone "{url}"' couldn't be completed for the following reason: {e}''')

# Git pull
def sync():
    project_dir = QFileDialog.getExistingDirectory(None, "Select the folder where your repository lives")
    if not project_dir:
        return

    try:
        subprocess.run('git pull', cwd=project_dir, shell=True, check=True, text=True, capture_output=True)
        QMessageBox.information(None, "Git action successful", "Sync action via 'git pull' completed successfully")
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f'''Sync action via 'git pull"' couldn't be completed for the following reason: {e}''')

# Window for Git status/Doff/Blame
def _show_text_dialog(title, content, is_html=False):
    dlg = QDialog()
    dlg.resize(650, 450)
    dlg.setWindowTitle(title)
    dlg.setStyleSheet("background-color: #363636; color: purple;")
    dlg.setWindowIcon(QIcon(icon))
    layout = QVBoxLayout(dlg)
    
    edit = QTextBrowser(dlg)
    if is_html:
        edit.setHtml(content)
    else:
        edit.setPlainText(content)
        
    edit.setReadOnly(True)
    edit.setStyleSheet("""
        QTextBrowser {
            background-color: #19191a;
            color: #cdd6f4;
            border: 1px solid #313244;
            font-family: Consolas;
            font-size: 12px;
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
    layout.addWidget(edit)
    
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
    btn.clicked.connect(dlg.accept)
    layout.addWidget(btn)
    dlg.exec()

# Git status (For viewing uncommited files only)
def get_status(file_path):
    if not file_path:
        return
    if os.path.isdir(file_path):
        root_dir = os.path.abspath(file_path)
    else:
        root_dir = os.path.dirname(os.path.abspath(file_path))
        
    try:          
        result = subprocess.run("git status --porcelain", cwd=root_dir, shell=True, text=True, check=True, capture_output=True)
        raw_output = result.stdout.strip()
        if not raw_output:
            _show_text_dialog("Git Status", "Working tree clean. No uncommitted files... yet")
            return

        formatted_lines = []
        for line in raw_output.splitlines():
            safe_line = html.escape(line)
            if line.startswith(" M") or line.startswith("M "):
                formatted_lines.append(f'<font color="#f69d50"><b>M</b></font> {safe_line[2:]}')
            elif line.startswith("??"):
                formatted_lines.append(f'<font color="#a6e3a1"><b>??</b></font> {safe_line[2:]}')
            elif line.startswith(" A") or line.startswith("A "):
                formatted_lines.append(f'<font color="#89b4fa"><b>A</b></font> {safe_line[2:]}')
            elif line.startswith(" D") or line.startswith("D "):
                formatted_lines.append(f'<font color="#f38ba8"><b>D</b></font> {safe_line[2:]}')
            else:
                formatted_lines.append(safe_line)

        html_body = f"<pre style='font-family: Consolas;'>{'<br>'.join(formatted_lines)}</pre>"
        _show_text_dialog("Git Status", html_body, is_html=True)
    except Exception as e:
        _show_text_dialog("Git Status Error", str(e))

# Git Blame
def show_file_blame(file_path):
    if not file_path or not os.path.exists(file_path):
        _show_text_dialog("Git Blame Error", "File doesn't exist.")
        return
    root_dir = os.path.dirname(os.path.abspath(file_path))
    rel_path = os.path.relpath(file_path, root_dir)
    try:
        result = subprocess.run(f'git blame "{rel_path}"', cwd=root_dir, shell=True, text=True, check=True, capture_output=True)
        formatted_lines = []
        for line in result.stdout.splitlines():
            safe_line = html.escape(line)
            line_html = re.sub(
                r'^([a-f0-9^]+)\s+\((.*?)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+[-+]\d{4})\s+(\d+)\)(.*)$',
                r'<font color="#89b4fa"><b>\1</b></font> (<font color="#cba6f7">\2</font> <font color="#f9e2af">\3</font> <font color="#74c7ec">\4</font>)\5',
                safe_line
            )
            formatted_lines.append(line_html)

        html_body = f"<pre style='font-family: Consolas;'>{'<br>'.join(formatted_lines)}</pre>"
        _show_text_dialog("Git Blame", html_body, is_html=True)
    except subprocess.CalledProcessError:
        _show_text_dialog("Git Blame", "Cannot get Git Blame: File is either untracked or has not been committed yet.\n (A quick fix for this is to 'git add' then 'git commit' your files)")
    except Exception as e:
        _show_text_dialog("Git Blame Error", str(e))

# Git Diff
def show_file_diff(file_path):
    if not file_path or not os.path.exists(file_path):
        _show_text_dialog("Git Diff Error", "File path does not exist.")
        return
    root_dir = os.path.dirname(os.path.abspath(file_path))
    rel_path = os.path.relpath(file_path, root_dir)
    try:
        result = subprocess.run(f'git diff "{rel_path}"', cwd=root_dir, shell=True, text=True, check=True, capture_output=True)
        raw_output = result.stdout.strip()
        if not raw_output:
            _show_text_dialog("Git Diff", "No changes detected for this file.")
            return

        formatted_lines = []
        for line in raw_output.splitlines():
            safe_line = html.escape(line)
            
            if line.startswith("+") and not line.startswith("+++"):
                formatted_lines.append(f'<font color="#a6e3a1"><b>+</b></font> {safe_line[1:]}')
            elif line.startswith("-") and not line.startswith("---"):
                formatted_lines.append(f'<font color="#f38ba8"><b>-</b></font> {safe_line[1:]}')
            elif line.startswith("@@"):
                formatted_lines.append(f'<font color="#cba6f7"><b>{safe_line}</b></font>')
            else:
                formatted_lines.append(f'<font color="#cdd6f4">{safe_line}</font>')

        html_body = f"<pre style='font-family: Consolas;'>{'<br>'.join(formatted_lines)}</pre>"
        _show_text_dialog("Git Diff", html_body, is_html=True)
    except Exception as e:
        _show_text_dialog("Git Diff Error", str(e))
