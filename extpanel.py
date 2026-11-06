import html
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QTextBrowser, QVBoxLayout
)

import motion
import skin
import themes
from widgets import AnimatedButton

class ExtensionsDialog(QDialog):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Extensions")
        self.resize(860, 540)
        self.setStyleSheet(skin.dialog_qss(themes.chrome()))
        self._popped = False

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
        self.toggle_btn = AnimatedButton("Disable", primary=True)
        self.toggle_btn.clicked.connect(self._toggle)
        self.uninstall_btn = AnimatedButton("Uninstall")
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
            button = AnimatedButton(label)
            button.clicked.connect(handler)
            footer.addWidget(button)
        footer.addStretch()
        close = AnimatedButton("Close", primary=True)
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)

        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._popped:
            self._popped = True
            motion.pop_in(self, 380, 22, 2.2)

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
            self.details.setHtml("<p style='color:#8a8fa3'>No extensions found.</p>")
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
            f"<p style='color:#8a8fa3'>{html.escape(ext.id)}  ·  v{html.escape(ext.version)}  ·  {'Built-in' if ext.builtin else 'Installed'}</p>",
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
