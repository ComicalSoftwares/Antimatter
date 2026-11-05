import html
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QTextBrowser, QVBoxLayout, QWidget
)

STYLE = """
QDialog { background-color: #1e1e1e; }
QLineEdit { background-color: #19191a; color: #cdd6f4; border: 1px solid #313244; border-radius: 8px; padding: 6px 10px;
            font-family: 'Consolas', 'Cantarell'; font-size: 13px; }
QLineEdit:focus { border: 1px solid #5400ba; }
QListWidget { background-color: #19191a; color: #cdd6f4; border: 1px solid #2a2a2e; border-radius: 10px; padding: 4px;
              font-family: 'Consolas', 'Cantarell'; font-size: 13px; outline: none; }
QListWidget::item { padding: 8px 10px; border-radius: 8px; }
QListWidget::item:hover { background-color: #2a2a2e; }
QListWidget::item:selected { background-color: #313244; color: #ffffff; }
QTextBrowser { background-color: #19191a; color: #cdd6f4; border: 1px solid #2a2a2e; border-radius: 10px; padding: 8px;
               font-family: 'Consolas', 'Cantarell'; font-size: 13px; }
QPushButton { background-color: #313244; color: #cdd6f4; border: none; padding: 7px 14px; border-radius: 8px;
              font-family: 'Consolas', 'Cantarell'; font-size: 12px; }
QPushButton:hover { background-color: #45475a; }
QPushButton:disabled { background-color: #26262b; color: #6c7086; }
QPushButton#primary { background-color: #5400ba; color: #ffffff; }
QPushButton#primary:hover { background-color: #6a1fd6; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0px; border: none; border-radius: 5px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #585b70; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none; border: none; height: 0px; }
"""


class ExtensionsDialog(QDialog):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Extensions")
        self.resize(860, 540)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        body = QHBoxLayout()
        body.setSpacing(10)
        root.addLayout(body, 1)

        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search installed extensions")
        self.search.textChanged.connect(self.refresh)
        left.addWidget(self.search)
        self.list = QListWidget()
        self.list.setFixedWidth(300)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.list.currentItemChanged.connect(self._show_details)
        left.addWidget(self.list, 1)
        body.addLayout(left)

        right = QVBoxLayout()
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(False)
        right.addWidget(self.details, 1)
        actions = QHBoxLayout()
        self.toggle_btn = QPushButton("Disable")
        self.toggle_btn.setObjectName("primary")
        self.toggle_btn.clicked.connect(self._toggle)
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.clicked.connect(self._uninstall)
        actions.addWidget(self.toggle_btn)
        actions.addWidget(self.uninstall_btn)
        actions.addStretch()
        right.addLayout(actions)
        body.addLayout(right, 1)

        footer = QHBoxLayout()
        for label, handler in (
            ("Install from File...", self._install),
            ("Open Folder", self.manager.open_folder),
            ("Reload", self._reload),
        ):
            button = QPushButton(label)
            button.clicked.connect(handler)
            footer.addWidget(button)
        footer.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)

        self.refresh()

    def _current(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh(self, *_):
        selected = self._current()
        query = self.search.text().lower()
        self.list.clear()
        for ext in sorted(self.manager.records.values(), key=lambda e: e.name.lower()):
            if query and query not in ext.name.lower() and query not in ext.description.lower():
                continue
            state = "" if ext.enabled else "   (disabled)"
            if ext.error:
                state = "   (error)"
            item = QListWidgetItem(f"{ext.name}  {ext.version}{state}\n{ext.publisher}  ·  {ext.description[:60]}")
            item.setData(Qt.ItemDataRole.UserRole, ext)
            self.list.addItem(item)
            if ext is selected:
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        elif self.list.count() == 0:
            self._show_details(None, None)

    def _show_details(self, item, _previous):
        ext = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.toggle_btn.setEnabled(ext is not None)
        self.uninstall_btn.setEnabled(ext is not None and not ext.builtin)
        if ext is None:
            self.details.setHtml("<p style='color:#6c7086'>No extensions found.</p>")
            return
        self.toggle_btn.setText("Disable" if ext.enabled else "Enable")
        c = ext.contributes
        rows = []
        if c.get("commands"):
            rows.append(f"{len(c['commands'])} command(s)")
        if c.get("keybindings"):
            rows.append(f"{len(c['keybindings'])} keybinding(s)")
        if c.get("themes"):
            rows.append("themes: " + ", ".join(html.escape(t.get("label", "")) for t in c["themes"]))
        if c.get("snippets"):
            rows.append("snippets: " + ", ".join(sorted({s["language"] for s in c["snippets"]})))
        if c.get("languages"):
            rows.append("languages: " + ", ".join(html.escape(l["id"]) for l in c["languages"]))
        status = "Disabled" if not ext.enabled else ("Active" if ext.activated else "Enabled (activates on demand)")
        if ext.error:
            status = "Failed"
        parts = [
            f"<h2 style='margin:0'>{html.escape(ext.name)}</h2>",
            f"<p style='color:#6c7086'>{html.escape(ext.id)}  ·  v{html.escape(ext.version)}  ·  {'Built-in' if ext.builtin else 'Installed'}</p>",
            f"<p>{html.escape(ext.description)}</p>",
            f"<p><b>Status:</b> {status}</p>",
            f"<p><b>Activation:</b> {html.escape(', '.join(ext.events) or 'none')}</p>",
        ]
        if rows:
            parts.append("<p><b>Contributes:</b></p><ul>" + "".join(f"<li>{r}</li>" for r in rows) + "</ul>")
        if ext.error:
            parts.append(f"<pre style='color:#f38ba8'>{html.escape(ext.error)}</pre>")
        self.details.setHtml("".join(parts))

    def _toggle(self):
        ext = self._current()
        if ext:
            self.manager.set_enabled(ext, not ext.enabled)
            self.refresh()
            self._show_details(self.list.currentItem(), None)

    def _uninstall(self):
        ext = self._current()
        if ext and QMessageBox.question(self, "Uninstall", f"Uninstall {ext.name}?") == QMessageBox.StandardButton.Yes:
            self.manager.uninstall(ext)
            self.refresh()

    def _install(self):
        self.parent().install_extension_dialog()
        self.refresh()

    def _reload(self):
        self.manager.reload_all()
        self.refresh()
