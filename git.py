import subprocess
import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QDialog, QVBoxLayout, QPlainTextEdit, QPushButton


def add():
    project_dir = QFileDialog.getExistingDirectory(None, "Select project folder")
    if not project_dir:
        return
    try:
        subprocess.run("git add .", cwd=project_dir, shell=True, check=True)
        QMessageBox.information(None, "Git action successful", "Action 'git add .' completed successfully")
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f"Action 'git add .' couldn't be completed for the following reason: {e}")

def commit():
    project_dir = QFileDialog.getExistingDirectory(None, "Select current working directory")
    if not project_dir:
        return
        
    message, ok = QInputDialog.getText(None, "Git Commit", "Enter commit message:")
    if not ok or not message:
        return

    try:
        subprocess.run("git add .", cwd=project_dir, shell=True, check=True)
        subprocess.run(f'git commit -m "{message}"', cwd=project_dir, shell=True, check=True)
        QMessageBox.information(None, "Git action successful", f'''Action 'git commit -m "{message}"' completed successfully''')
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f'''Action 'git commit -m "{message}"' couldn't be completed for the following reason: {e}''')

def set_repo():
    project_dir = QFileDialog.getExistingDirectory(None, "Select project folder")
    if not project_dir:
        return
        
    url, ok = QInputDialog.getText(None, "Connect to a remote git repository", "Enter the remote repository's URL:")
    if not ok or not url:
        return

    try:
        subprocess.run("git init", cwd=project_dir, shell=True, check=True)
        subprocess.run(f'git remote add origin "{url}"', cwd=project_dir, shell=True, check=True)
        QMessageBox.information(None, "Git action successful", f'''Action 'git remote add origin "{url}"' completed successfully''')
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f'''Action 'git remote add origin "{url}"' couldn't be completed for the following reason: {e}''')

def push():
    project_dir = QFileDialog.getExistingDirectory(None, "Select project folder")
    if not project_dir:
        return

    branch, ok = QInputDialog.getText(None, "Specify the branch to push changes to", "Enter the name of the branch that you wish to push changes to (e.g. main):")
    if not ok or not branch:
        return
    
    try:
        subprocess.run(f"git push origin {branch}", cwd=project_dir, shell=True, check=True)
        QMessageBox.information(None, "Git action successful", "Changes pushed to remote repository successfully!")
    except Exception as e:
        QMessageBox.critical(None, "Git action unsuccessful", f"Push couldn't be completed for the following reason: {e}")


def _show_text_dialog(title, content):
    dlg = QDialog()
    dlg.resize(650, 450)
    dlg.setWindowTitle(title)
    dlg.setStyleSheet("background-color: #181825; color: #cdd6f4;")
    layout = QVBoxLayout(dlg)
    
    edit = QPlainTextEdit(dlg)
    edit.setPlainText(content)
    edit.setReadOnly(True)
    edit.setStyleSheet("""
        QPlainTextEdit {
            background-color: #1e1e2e;
            color: #cdd6f4;
            border: 1px solid #313244;
            font-family: Consolas;
            font-size: 12px;
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
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
            border: none;
            width: 0px;
            height: 0px;
        }
    """)
    layout.addWidget(edit)
    
    btn = QPushButton("Close", dlg)
    btn.setStyleSheet("""
        QPushButton {
            background-color: #313244;
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

def show_file_diff(file_path):
    if not file_path or not os.path.exists(file_path):
        _show_text_dialog("Git Diff Error", "File path does not exist.")
        return
    root_dir = os.path.dirname(os.path.abspath(file_path))
    rel_path = os.path.relpath(file_path, root_dir)
    try:
        result = subprocess.run(
            f'git diff "{rel_path}"',
            cwd=root_dir, shell=True, capture_output=True, text=True, check=True
        )
        output = result.stdout if result.stdout else "No changes detected for this file."
        _show_text_dialog("Git Diff", output)
    except Exception as e:
        _show_text_dialog("Git Diff Error", str(e))

def show_file_blame(file_path):
    if not file_path or not os.path.exists(file_path):
        _show_text_dialog("Git Blame Error", "File path does not exist.")
        return
    root_dir = os.path.dirname(os.path.abspath(file_path))
    rel_path = os.path.relpath(file_path, root_dir)
    try:
        result = subprocess.run(
            f'git blame "{rel_path}"',
            cwd=root_dir, shell=True, capture_output=True, text=True, check=True
        )
        _show_text_dialog("Git Blame", result.stdout)
    except subprocess.CalledProcessError:
        _show_text_dialog("Git Blame", "Cannot run blame: File is untracked or has not been committed yet.")
    except Exception as e:
        _show_text_dialog("Git Blame Error", str(e))

def get_status(file_path):
    if not file_path:
        return
    root_dir = os.path.dirname(os.path.abspath(file_path))
    try:
        result = subprocess.run(
            "git status --porcelain",
            cwd=root_dir, shell=True, capture_output=True, text=True, check=True
        )
        output = result.stdout if result.stdout else "Working tree clean. No uncommitted files."
        _show_text_dialog("Uncommitted Files (Git Status)", output)
    except Exception as e:
        _show_text_dialog("Git Status Error", str(e))
