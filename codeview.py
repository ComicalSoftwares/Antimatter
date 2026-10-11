import asyncio
import os
import threading
from pygments.lexers import PythonLexer
from pygments import lex
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (QWidget, QPlainTextEdit, QListWidget, QMenu, QHBoxLayout, QFrame)
from lsp import LspClient

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.lexer = PythonLexer()
        self.theme_map = {
            "Token.Keyword": "#c678dd",
            "Token.Name.Function": "#61afef",
            "Token.Literal.String": "#98c379",
            "Token.Comment": "#5c6370",
            "Token.Operator": "#56b6c2",
            "Token.Literal.Number": "#d19a66",
            "Token.Name.Builtin": "#e5c07b",
            "Token.Name.Namespace": "#61afef",
            "Token.Name.Class": "#e5c07b"
        }
        self.formats = {}
        for token, color_hex in self.theme_map.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_hex))
            self.formats[token] = fmt

    def highlightBlock(self, text):
        if not text:
            return
        for token, value in lex(text, self.lexer):
            token_str = f"Token.{token}"
            matched_tag = next((t for t in self.theme_map.keys() if t in token_str), None)
            if matched_tag:
                length = len(value)
                start = 0
                while True:
                    idx = text.find(value, start)
                    if idx == -1:
                        break
                    self.setFormat(idx, length, self.formats[matched_tag])
                    start = idx + length

class AntimatterTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_family = "Consolas"
        self.font_size = 13
        
        self.setFont(QFont(self.font_family, self.font_size))
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #19191a;
                color: #D8DEE9;
                border: none;
                selection-background-color: #2e3c64;
            }
        """)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)
        self.verticalScrollBar().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.horizontalScrollBar().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            col = cursor.columnNumber()
            spaces_to_insert = 4 - (col % 4)
            cursor.insertText(" " * spaces_to_insert)
            return

        if event.key() == Qt.Key.Key_Backspace:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                block_text = cursor.block().text()
                col = cursor.columnNumber()
                prefix = block_text[:col]
                if prefix and prefix.isspace():
                    spaces_to_delete = col % 4 or 4
                    cursor.setPosition(cursor.position() - spaces_to_delete, QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
                    return

        super().keyPressEvent(event)

    def line_number_area_width(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        space = 25 + self.fontMetrics().horizontalAdvance('9') * digits
        return max(45, space)

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#19191a"))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#45475a"))
                painter.setFont(self.font())
                painter.drawText(0, top, self.line_number_area.width(), self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignCenter, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size += 1
            elif delta < 0:
                self.font_size = max(6, self.font_size - 1)
            self.setFont(QFont(self.font_family, self.font_size))
            self.line_number_area.update()
            event.accept()
        else:
            super().wheelEvent(event)

class LspSignals(QObject):
    completions_ready = pyqtSignal(list)

class AntimatterEditor(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #19191a;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text = AntimatterTextEdit(self)
        layout.addWidget(self.text)

        self.highlighter = PythonHighlighter(self.text.document())

        self.lsp = LspClient()
        self.loop = asyncio.new_event_loop()
        self.lsp_signals = LspSignals()
        self.lsp_signals.completions_ready.connect(self._display_popup)
        
        threading.Thread(target=self._run_async_loop, daemon=True).start()

        self.text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self._show_context_menu)
        self.text.textChanged.connect(self._on_text_changed)
        
        self.text.installEventFilter(self)
        self.comp_popup = None
        self._current_completions = []
        self._current_file_path = None

    def eventFilter(self, obj, event):
        if obj == self.text and event.type() == event.Type.KeyPress:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space:
                self.show_completions()
                return True

            if self.comp_popup and self.comp_popup.isVisible():
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                    current_item = self.comp_popup.currentItem()
                    if current_item:
                        self._apply_completion(current_item.text().strip())
                    return True
                elif event.key() == Qt.Key.Key_Escape:
                    self.comp_popup.close()
                    return True
                elif event.key() == Qt.Key.Key_Down:
                    self.comp_popup.setCurrentRow(min(self.comp_popup.count() - 1, self.comp_popup.currentRow() + 1))
                    return True
                elif event.key() == Qt.Key.Key_Up:
                    self.comp_popup.setCurrentRow(max(0, self.comp_popup.currentRow() - 1))
                    return True

        return super().eventFilter(obj, event)

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_lsp(self, file_path=None):
        if not file_path:
            file_path = os.path.join(os.getcwd(), "untitled.py")
            
        self._current_file_path = file_path
        root_path = os.path.dirname(os.path.abspath(file_path))

        async def init_sequence():
            started = await self.lsp.start("python", root_path)
            if started:
                await self.lsp.did_open(self._current_file_path, self.text.toPlainText())

        asyncio.run_coroutine_threadsafe(init_sequence(), self.loop)

    def _on_text_changed(self):
        if not self.lsp.running:
            return
        content = self.text.toPlainText()
        asyncio.run_coroutine_threadsafe(self.lsp.did_change(content), self.loop)

    def show_completions(self):
        if not self.lsp.running:
            return

        cursor = self.text.textCursor()
        line = cursor.blockNumber()
        col = cursor.columnNumber()

        async def get_comp():
            completions = await self.lsp.complete(line, col)
            if completions:
                self.lsp_signals.completions_ready.emit(completions)

        asyncio.run_coroutine_threadsafe(get_comp(), self.loop)

    def _display_popup(self, completions):
        if self.comp_popup:
            self.comp_popup.close()

        self._current_completions = completions

        # Attach parent widget directly to support Wayland subsurfaces
        self.comp_popup = QListWidget(self.text)
        self.comp_popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        
        # Explicitly declare transient parent window for Hyprland
        if self.text.window().windowHandle():
            self.comp_popup.create()
            self.comp_popup.windowHandle().setTransientParent(self.text.window().windowHandle())

        self.comp_popup.setStyleSheet("""
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
            }
            QListWidget::item:selected {
                background-color: #313244;
                color: #ffffff;
            }
        """)
        
        for item in completions:
            self.comp_popup.addItem(f" {item['label']} ")

        if completions:
            self.comp_popup.setCurrentRow(0)

        cursor_rect = self.text.cursorRect()
        global_pos = self.text.mapToGlobal(cursor_rect.bottomLeft())
        self.comp_popup.move(global_pos)
        
        self.comp_popup.itemClicked.connect(lambda item: self._apply_completion(item.text().strip()))
        self.comp_popup.show()

    def _apply_completion(self, label):
        insert_text = next(
            (c["insert"] for c in self._current_completions if c["label"] == label), label
        )

        cursor = self.text.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.insertText(insert_text)

        if self.comp_popup:
            self.comp_popup.close()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
            }
            QMenu::item:selected {
                background-color: #313244;
                color: white;
            }
        """)
        
        cut_act = menu.addAction("Cut")
        cut_act.triggered.connect(self.text.cut)
        copy_act = menu.addAction("Copy")
        copy_act.triggered.connect(self.text.copy)
        paste_act = menu.addAction("Paste")
        paste_act.triggered.connect(self.text.paste)
        menu.addSeparator()
        comp_act = menu.addAction("Show completions")
        comp_act.triggered.connect(self.show_completions)
        menu.addSeparator()
        select_act = menu.addAction("Select All")
        select_act.triggered.connect(self.text.selectAll)

        menu.exec(self.text.mapToGlobal(pos))

    def get(self, start="0.0", end="end-1c"):
        return self.text.toPlainText()

    def insert(self, pos, content):
        self.text.insertPlainText(content)

    def delete(self, start, end):
        self.text.clear()