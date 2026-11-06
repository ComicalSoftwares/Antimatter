from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QFrame, QLineEdit, QListWidget, QListWidgetItem, QStyle,
    QStyledItemDelegate, QVBoxLayout
)

import motion
import skin
import themes

KEY_ROLE = Qt.ItemDataRole.UserRole + 1
DATA_ROLE = Qt.ItemDataRole.UserRole


def match_score(query, text):
    if not query:
        return 0
    q = query.lower()
    t = text.lower()
    index = t.find(q)
    if index != -1:
        return 1000 - index - len(t) * 0.01
    pos = 0
    gaps = 0
    last = -1
    for ch in q:
        found = t.find(ch, pos)
        if found == -1:
            return None
        if last != -1:
            gaps += found - last - 1
        last = found
        pos = found + 1
    return 500 - gaps


class _Delegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        c = themes.chrome()
        rect = option.rect.adjusted(4, 1, -4, -1)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setRenderHint(painter.RenderHint.Antialiasing)
            painter.setBrush(QColor(c["select"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 9, 9)
        text_rect = rect.adjusted(10, 0, -10, 0)
        key = index.data(KEY_ROLE)
        if key:
            painter.setPen(QColor(c["muted"]))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, key)
        painter.setPen(QColor(c["select_text"]) if option.state & QStyle.StateFlag.State_Selected else QColor(c["text"]))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, index.data(Qt.ItemDataRole.DisplayRole))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(0, 30)


class QuickPick(QDialog):
    def __init__(self, parent, items, placeholder, on_select):
        super().__init__(parent)
        self.items = items
        self.on_select = on_select
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QFrame(self)
        frame.setObjectName("pick")
        frame.setStyleSheet(skin.pick_qss(themes.chrome()))
        outer.addWidget(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText(placeholder)
        self.entry.textChanged.connect(self._refresh)
        self.entry.installEventFilter(self)
        layout.addWidget(self.entry)

        self.list = QListWidget()
        self.list.setItemDelegate(_Delegate(self.list))
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list.itemClicked.connect(lambda item: self._accept(item))
        layout.addWidget(self.list)

        self.setFixedWidth(580)
        self._refresh("")

    def eventFilter(self, obj, event):
        if obj is self.entry and event.type() == event.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                self.list.setCurrentRow(min(self.list.count() - 1, self.list.currentRow() + 1))
                return True
            if key == Qt.Key.Key_Up:
                self.list.setCurrentRow(max(0, self.list.currentRow() - 1))
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.list.currentItem()
                if item:
                    self._accept(item)
                return True
            if key == Qt.Key.Key_Escape:
                self.close()
                return True
        return super().eventFilter(obj, event)

    def _refresh(self, query):
        scored = []
        for entry in self.items:
            score = match_score(query, entry["title"])
            if score is not None:
                scored.append((score, entry))
        scored.sort(key=lambda pair: -pair[0])
        self.list.clear()
        for _, entry in scored:
            item = QListWidgetItem(entry["title"])
            item.setData(DATA_ROLE, entry)
            item.setData(KEY_ROLE, entry.get("key", ""))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        rows = min(10, max(1, self.list.count()))
        self.list.setFixedHeight(rows * 30 + 4)
        self.adjustSize()

    def _accept(self, item):
        entry = item.data(DATA_ROLE)
        self.close()
        QTimer.singleShot(0, lambda: self.on_select(entry))

    def popup(self):
        parent = self.parentWidget().window() if self.parentWidget() else None
        if parent is not None:
            geo = parent.geometry()
            self.move(geo.x() + (geo.width() - self.width()) // 2, geo.y() + 70)
        self.show()
        motion.pop_in(self, 360, 20, 2.4)
        self.entry.setFocus()
