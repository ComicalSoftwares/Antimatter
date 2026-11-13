import subprocess
import os
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QColor

class IssuesDialog(QDialog):
    def __init__(self, editor_view, parent=None):
        super().__init__(parent)
        self.editor_view = editor_view
        self.file_path = editor_view._current_file_path if editor_view else None
        
        self.setWindowTitle("Issues - Comical Antimatter")
        self.resize(750, 450)
        self.setStyleSheet("background-color: #1e1e1e; color: #cdd6f4;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        file_name = os.path.basename(self.file_path) if self.file_path else "No active file"
        header_label = QLabel(f"Diagnostics for: <b>{file_name}</b>")
        header_label.setStyleSheet("font-size: 13px; color: #89b4fa;")
        layout.addWidget(header_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Line:Col", "Type", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #19191a;
                color: #cdd6f4;
                gridline-color: #313244;
                border: 1px solid #313244;
                border-radius: 6px;
                font-family: Consolas;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2a2a2e;
                color: #cdd6f4;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #313244;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #313244;
                color: white;
            }
        """)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.jump_to_issue)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Re-scan")
        self.refresh_btn.setStyleSheet("background-color: #313244; color: #cdd6f4; border: none; padding: 6px 14px; border-radius: 4px;")
        self.refresh_btn.clicked.connect(self.run_scan)
        
        hint_lbl = QLabel("Double-click an issue to jump to line")
        hint_lbl.setStyleSheet("color: #6c7086; font-size: 11px;")
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setStyleSheet("background-color: #1f1f1f; color: #cdd6f4; border: none; padding: 6px 14px; border-radius: 4px;")
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(hint_lbl)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        self.run_scan()

    def run_scan(self):
        self.table.setRowCount(0)
        if not self.file_path or not os.path.exists(self.file_path):
            self.table.insertRow(0)
            item = QTableWidgetItem("Save or open a Python file to run diagnostics.")
            item.setForeground(QColor("#f9e2af"))
            self.table.setItem(0, 2, item)
            return
            
        try:
            res = subprocess.run(f'pyflakes "{self.file_path}"', capture_output=True, text=True, shell=True)
            output = res.stdout + res.stderr
            lines = output.splitlines()
            
            row = 0
            pattern = re.compile(r'^(?:.*?:)?(\d+)(?::(\d+))?:\s*(.*)$')
            
            for line in lines:
                m = pattern.search(line)
                if m:
                    lineno = m.group(1)
                    col = m.group(2) or "1"
                    msg = m.group(3)
                    
                    self.table.insertRow(row)
                    
                    pos_item = QTableWidgetItem(f"{lineno}:{col}")
                    pos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    pos_item.setData(Qt.ItemDataRole.UserRole, (int(lineno), int(col)))
                    
                    type_item = QTableWidgetItem("Warning" if "undefined" in msg.lower() or "unused" in msg.lower() else "Error")
                    type_item.setForeground(QColor("#f38ba8") if "Error" in type_item.text() else QColor("#f9e2af"))
                    
                    msg_item = QTableWidgetItem(msg)
                    
                    self.table.setItem(row, 0, pos_item)
                    self.table.setItem(row, 1, type_item)
                    self.table.setItem(row, 2, msg_item)
                    row += 1
            
            if row == 0 and not output.strip():
                self.table.insertRow(0)
                item = QTableWidgetItem("No issues detected. Looking pristine! 🎉")
                item.setForeground(QColor("#a6e3a1"))
                self.table.setItem(0, 2, item)
        except Exception as e:
            self.table.insertRow(0)
            item = QTableWidgetItem(f"Error running linter: {e}")
            item.setForeground(QColor("#f38ba8"))
            self.table.setItem(0, 2, item)

    def jump_to_issue(self, index):
        row = index.row()
        pos_item = self.table.item(row, 0)
        if not pos_item or not self.editor_view:
            return
        data = pos_item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        lineno, col = data
        
        cursor = self.editor_view.text.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, lineno - 1)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, col - 1)
        self.editor_view.text.setTextCursor(cursor)
        self.editor_view.text.setFocus()
        self.accept()