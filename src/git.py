import subprocess
import os
import html
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QTextBrowser, QPushButton,
    QLineEdit, QLabel, QMessageBox, QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QColor

BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = str(BASE_DIR / "AppIcon.png")

class GitManagerDialog(QDialog):
    def __init__(self, project_dir=None, parent=None):
        super().__init__(parent)
        self.project_dir = project_dir or os.getcwd()
        self.setWindowTitle(f"Git - {os.path.basename(self.project_dir)}")
        self.resize(800, 550)
        self.setStyleSheet("background-color: #1e1e1e; color: #cdd6f4;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #313244; background: #19191a; border-radius: 6px; }
            QTabBar::tab { background: #2a2a2e; color: #a6adc8; padding: 6px 14px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #19191a; color: #cdd6f4; border-bottom: 2px solid #89b4fa; }
        """)
        
        self.init_status_tab()
        self.init_log_tab()
        self.init_remote_tab()
        
        layout.addWidget(self.tabs)
        
        bottom_layout = QHBoxLayout()
        repo_lbl = QLabel(f"Repository: <b>{self.project_dir}</b>")
        repo_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #1f1f1f; color: #cdd6f4; border: none; padding: 6px 14px; border-radius: 4px;")
        close_btn.clicked.connect(self.accept)
        
        bottom_layout.addWidget(repo_lbl)
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)
        
        self.refresh_status()

    def init_status_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<b>Working Tree & Changes</b>"))
        
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(2)
        self.status_table.setHorizontalHeaderLabels(["Status", "File Path"])
        self.status_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.status_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.status_table.setStyleSheet(self.table_stylesheet())
        self.status_table.itemSelectionChanged.connect(self.load_selected_diff)
        self.status_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        left_layout.addWidget(self.status_table)
        
        btn_box = QHBoxLayout()
        stage_btn = QPushButton("Stage Selected Files")
        stage_btn.setStyleSheet("background-color: #313244; color: #a6e3a1; border: none; padding: 5px; border-radius: 4px;")
        stage_btn.clicked.connect(self.stage_selected)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("background-color: #313244; color: #cdd6f4; border: none; padding: 5px; border-radius: 4px;")
        refresh_btn.clicked.connect(self.refresh_status)
        
        btn_box.addWidget(stage_btn)
        btn_box.addWidget(refresh_btn)
        left_layout.addLayout(btn_box)
        
        left_layout.addWidget(QLabel("<b>Commit Changes</b>"))
        self.commit_input = QLineEdit()
        self.commit_input.setPlaceholderText("Enter commit message...")
        self.commit_input.setStyleSheet("background-color: #19191a; color: #cdd6f4; border: 1px solid #313244; padding: 6px; border-radius: 4px;")
        left_layout.addWidget(self.commit_input)
        
        commit_btn = QPushButton("Commit Staged Changes")
        commit_btn.setStyleSheet("background-color: #89b4fa; color: #1e1e1e; font-weight: bold; border: none; padding: 6px; border-radius: 4px;")
        commit_btn.clicked.connect(self.do_commit)
        left_layout.addWidget(commit_btn)
        
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("<b>File Diff Preview</b>"))
        self.diff_browser = QTextBrowser()
        self.diff_browser.setStyleSheet("background-color: #141415; color: #cdd6f4; border: 1px solid #313244; font-family: Consolas; font-size: 11px; border-radius: 4px;")
        right_layout.addWidget(self.diff_browser)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        w1, w2 = QWidget(), QWidget()
        w1.setLayout(left_layout)
        w2.setLayout(right_layout)
        splitter.addWidget(w1)
        splitter.addWidget(w2)
        splitter.setSizes([400, 350])
        
        layout.addWidget(splitter)
        self.tabs.addTab(widget, "Status and Commit")

    def init_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("<b>Commit History</b>"))
        self.log_browser = QTextBrowser()
        self.log_browser.setStyleSheet("background-color: #141415; color: #cdd6f4; border: 1px solid #313244; font-family: Consolas; font-size: 12px; border-radius: 4px;")
        layout.addWidget(self.log_browser)
        
        log_btn = QPushButton("Refresh Log")
        log_btn.setStyleSheet("background-color: #313244; color: #cdd6f4; border: none; padding: 6px; border-radius: 4px;")
        log_btn.clicked.connect(self.refresh_log)
        layout.addWidget(log_btn)
        
        self.tabs.addTab(widget, "History")
        self.refresh_log()

    def init_remote_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("<b>Remote Synchronization and Branching</b>"))
        
        form_layout = QVBoxLayout()
        self.remote_url_input = QLineEdit()
        self.remote_url_input.setPlaceholderText("https://github.com/username/repo.git")
        self.remote_url_input.setStyleSheet("background-color: #19191a; color: #cdd6f4; border: 1px solid #313244; padding: 6px; border-radius: 4px;")
        
        init_repo_btn = QPushButton("Initialize and Set Remote")
        init_repo_btn.setStyleSheet("background-color: #313244; color: #89b4fa; border: none; padding: 8px; border-radius: 4px;")
        init_repo_btn.clicked.connect(self.set_remote_repo)
        
        form_layout.addWidget(QLabel("Remote Repository URL:"))
        form_layout.addWidget(self.remote_url_input)
        form_layout.addWidget(init_repo_btn)
        form_layout.addSpacing(15)
        
        sync_box = QHBoxLayout()
        pull_btn = QPushButton("Pull Changes (Git pull)")
        pull_btn.setStyleSheet("background-color: #313244; color: #a6e3a1; border: none; padding: 8px; border-radius: 4px;")
        pull_btn.clicked.connect(self.do_pull)
        
        self.branch_input = QLineEdit("main")
        self.branch_input.setStyleSheet("background-color: #19191a; color: #cdd6f4; border: 1px solid #313244; padding: 6px; border-radius: 4px;")
        
        push_btn = QPushButton("Push Changes (git push)")
        push_btn.setStyleSheet("background-color: #89b4fa; color: #1e1e1e; font-weight: bold; border: none; padding: 8px; border-radius: 4px;")
        push_btn.clicked.connect(self.do_push)
        
        sync_box.addWidget(pull_btn)
        sync_box.addWidget(QLabel("Branch:"))
        sync_box.addWidget(self.branch_input)
        sync_box.addWidget(push_btn)
        
        form_layout.addLayout(sync_box)
        form_layout.addStretch()
        layout.addLayout(form_layout)
        self.tabs.addTab(widget, "Remote and Sync")

    def table_stylesheet(self):
        return """
            QTableWidget {
                background-color: #19191a; color: #cdd6f4; gridline-color: #313244;
                border: 1px solid #313244; border-radius: 4px; font-family: Consolas; font-size: 11px;
            }
            QHeaderView::section { background-color: #2a2a2e; color: #cdd6f4; padding: 4px; border: none; border-bottom: 1px solid #313244; }
            QTableWidget::item:selected { background-color: #313244; color: white; }
        """

    def refresh_status(self):
        self.status_table.setRowCount(0)
        try:
            res = subprocess.run("git status --porcelain", cwd=self.project_dir, shell=True, Text=True, check=True, capture_output=True)
            lines = res.stdout.strip().splitlines()
            row = 0
            for line in lines:
                if len(line) < 3:
                    continue
                status_code = line[:2]
                filepath = line[3:]
                
                self.status_table.insertRow(row)
                s_item = QTableWidgetItem(status_code)
                s_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if "M" in status_code: s_item.setForeground(QColor("#fab387"))
                elif "??" in status_code: s_item.setForeground(QColor("#a6e3a1"))
                elif "A" in status_code: s_item.setForeground(QColor("#89b4fa"))
                elif "D" in status_code: s_item.setForeground(QColor("#f38ba8"))
                
                self.status_table.setItem(row, 0, s_item)
                self.status_table.setItem(row, 1, QTableWidgetItem(filepath))
                row += 1
        except Exception:
            pass

    def load_selected_diff(self):
        items = self.status_table.selectedItems()
        if not items: return
        filepath = self.status_table.item(items[0].row(), 1).text()
        try:
            res = subprocess.run(f'git diff "{filepath}"', cwd=self.project_dir, shell=True, Text=True, capture_output=True)
            diff_text = res.stdout.strip() or subprocess.run(f'git diff --cached "{filepath}"', cwd=self.project_dir, shell=True, Text=True, capture_output=True).stdout.strip()
            if not diff_text: diff_text = "(No diff available)"
            
            formatted = []
            for line in diff_text.splitlines():
                safe = html.escape(line)
                if line.startswith("+") and not line.startswith("+++"): formatted.append(f'<font color="#a6e3a1">{safe}</font>')
                elif line.startswith("-") and not line.startswith("---"): formatted.append(f'<font color="#f38ba8">{safe}</font>')
                elif line.startswith("@@"): formatted.append(f'<font color="#cba6f7"><b>{safe}</b></font>')
                else: formatted.append(f'<font color="#cdd6f4">{safe}</font>')
            self.diff_browser.setHtml(f"<pre>{'<br>'.join(formatted)}</pre>")
        except Exception as e:
            self.diff_browser.setPlainText(str(e))

    def stage_selected(self):
        items = self.status_table.selectedItems()
        if not items: return
        filepath = self.status_table.item(items[0].row(), 1).text()
        try:
            subprocess.run(f'git add "{filepath}"', cwd=self.project_dir, shell=True, check=True, Text=True, capture_output=True)
            self.refresh_status()
        except Exception as e:
            QMessageBox.critical(self, "Git Error", str(e))

    def do_commit(self):
        msg = self.commit_input.text().strip()
        if not msg:
            QMessageBox.warning(self, "Commit message is required", "A commit message is required to commit changes.")
            return
        try:
            subprocess.run(f'git commit -m "{msg}"', cwd=self.project_dir, shell=True, check=True, capture_output=True)
            self.commit_input.clear()
            self.refresh_status()
            self.refresh_log()
            QMessageBox.information(self, "Success", "Committed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Commit Error", str(e))

    def refresh_log(self):
        try:
            res = subprocess.run('git log -n 30 --oneline', cwd=self.project_dir, shell=True, Text=True, capture_output=True)
            self.log_browser.setPlainText(res.stdout or "No commits yet.")
        except Exception:
            self.log_browser.setPlainText("Not a git repository.")

    def set_remote_repo(self):
        url = self.remote_url_input.text().strip()
        if not url: return
        try:
            subprocess.run("git init", cwd=self.project_dir, shell=True, check=True)
            subprocess.run(f'git remote add origin "{url}"', cwd=self.project_dir, shell=True, check=True)
            QMessageBox.information(self, "Success", "Remote origin added!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def do_pull(self):
        try:
            subprocess.run("git pull", cwd=self.project_dir, shell=True, check=True)
            QMessageBox.information(self, "Success", "Pulled successfully!")
            self.refresh_log()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def do_push(self):
        branch = self.branch_input.text().strip() or "main"
        try:
            subprocess.run(f"git push origin {branch}", cwd=self.project_dir, shell=True, check=True)
            QMessageBox.information(self, "Success", f"Pushed to origin/{branch}!")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

def open_git_manager(parent_window=None):
    current_path = parent_window.get_current_path() if parent_window and hasattr(parent_window, "get_current_path") else None
    if current_path and os.path.isfile(current_path):
        current_path = os.path.dirname(current_path)
        
    dlg = GitManagerDialog(current_path, parent_window)
    dlg.exec()