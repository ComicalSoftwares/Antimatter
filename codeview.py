import asyncio
import os
import re
from pygments.lexers.python import PythonLexer
from pygments.token import Comment, Keyword, Name, Number, Operator, String
from PyQt6.QtCore import Qt, QRect, QSize, QEasingCurve, QPropertyAnimation, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextFormat
from PyQt6.QtWidgets import (QWidget, QPlainTextEdit, QListWidget, QMenu, QHBoxLayout, QFrame, QTextEdit)
import languages
import lsp
from lsp import LspClient
import git
import shapes
import themes

INDENT = "    "
WORD_RE = re.compile(r"[A-Za-z0-9_]+$")
STRING_PREFIX = {1: "'''", 2: '"""'}
_MISSING = object()
SNIPPET_RE = re.compile(r"\$\{(\d+)(?::([^}]*))?\}|\$(\d+)")
TOKEN_KEYS = (
    ("function", Name.Function),
    ("namespace", Name.Namespace),
    ("class", Name.Class),
    ("builtin", Name.Builtin),
    ("tag", Name.Tag),
    ("keyword", Keyword),
    ("string", String),
    ("number", Number),
    ("comment", Comment),
    ("operator", Operator),
)


def build_snippet(body, indent):
    if isinstance(body, (list, tuple)):
        body = "\n".join(body)
    body = body.replace("\n", "\n" + indent)
    parts = []
    stops = {}
    length = 0
    last = 0
    for match in SNIPPET_RE.finditer(body):
        chunk = body[last:match.start()]
        parts.append(chunk)
        length += len(chunk)
        number = int(match.group(1) or match.group(3))
        default = match.group(2) or ""
        stops.setdefault(number, (length, len(default)))
        parts.append(default)
        length += len(default)
        last = match.end()
    parts.append(body[last:])
    text = "".join(parts)
    order = [n for n in sorted(stops) if n > 0] or ([0] if 0 in stops else [])
    start, size = stops[order[0]] if order else (len(text), 0)
    return text, start, size


def _triple_quote_state(text, state):
    delim = STRING_PREFIX.get(state)
    i = 0
    n = len(text)
    while i < n:
        if delim:
            j = text.find(delim, i)
            if j == -1:
                return state
            i = j + 3
            delim = None
            state = 0
            continue
        c = text[i]
        if c == "#":
            break
        if c in "'\"":
            triple = c * 3
            if text.startswith(triple, i):
                delim = triple
                state = 1 if c == "'" else 2
                i += 3
                continue
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\":
                    j += 1
                j += 1
            i = j + 1
            continue
        i += 1
    return state


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document, lexer=None):
        super().__init__(document)
        self.formats = {}
        self._cache = {}
        self.apply_colors(themes.get()["tokenColors"], rehighlight=False)
        self.lexer = None
        self.track_strings = False
        self.set_lexer(lexer or PythonLexer(stripnl=False), rehighlight=False)

    def apply_colors(self, token_colors, rehighlight=True):
        self.formats = {}
        for key, token in TOKEN_KEYS:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(token_colors[key]))
            self.formats[token] = fmt
        self._cache = {}
        if rehighlight:
            self.rehighlight()

    def set_lexer(self, lexer, rehighlight=True):
        self.lexer = lexer
        self.track_strings = isinstance(lexer, PythonLexer)
        if rehighlight:
            self.rehighlight()

    def _format_for(self, ttype):
        fmt = self._cache.get(ttype, _MISSING)
        if fmt is _MISSING:
            fmt = None
            current = ttype
            while current is not None:
                if current in self.formats:
                    fmt = self.formats[current]
                    break
                current = current.parent
            self._cache[ttype] = fmt
        return fmt

    def highlightBlock(self, text):
        state = max(0, self.previousBlockState())
        if self.track_strings:
            self.setCurrentBlockState(_triple_quote_state(text, state))
        else:
            self.setCurrentBlockState(0)
            state = 0
        if not text or self.lexer is None:
            return
        prefix = STRING_PREFIX.get(state, "")
        offset = len(prefix)
        for index, ttype, value in self.lexer.get_tokens_unprocessed(prefix + text):
            fmt = self._format_for(ttype)
            if fmt is None:
                continue
            start = index - offset
            length = len(value)
            if start < 0:
                length += start
                start = 0
            if length > 0:
                self.setFormat(start, length, fmt)

class AntimatterTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_family = "Consolas"
        self.font_size = 13
        self.auto_indent_colon = True
        self.language_id = "python"
        self.snippet_lookup = None
        self.colors = dict(themes.get()["colors"])

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._apply_font()
        self._apply_colors()

        self._scroll_target = 0
        self._scroll_anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._scroll_anim.setDuration(130)
        self._scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.verticalScrollBar().sliderPressed.connect(self._scroll_anim.stop)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)
        self.verticalScrollBar().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.horizontalScrollBar().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    def _apply_colors(self):
        c = self.colors
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {c['editor.background']};
                color: {c['editor.foreground']};
                border: none;
                selection-background-color: {c['editor.selectionBackground']};
            }}
        """)
        self._highlight_current_line()

    def apply_theme(self, theme):
        self.colors = dict(theme["colors"])
        self._apply_colors()
        self.line_number_area.update()

    def _highlight_current_line(self):
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(self.colors["editor.lineHighlightBackground"]))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])
        area = getattr(self, "line_number_area", None)
        if area is not None:
            area.update()

    def _insert_snippet(self, body, prefix_length):
        cursor = self.textCursor()
        block_text = cursor.block().text()
        indent = block_text[:len(block_text) - len(block_text.lstrip(" \t"))]
        text, start, size = build_snippet(body, indent)
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, prefix_length)
        origin = cursor.selectionStart()
        cursor.insertText(text)
        cursor.setPosition(origin + start)
        if size:
            cursor.setPosition(origin + start + size, QTextCursor.MoveMode.KeepAnchor)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _apply_font(self):
        self.setFont(QFont(self.font_family, self.font_size))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * len(INDENT))

    def _shift_lines(self, dedent):
        cursor = self.textCursor()
        doc = self.document()
        start_block = doc.findBlock(cursor.selectionStart())
        end_pos = cursor.selectionEnd()
        end_block = doc.findBlock(end_pos)
        if end_block != start_block and end_pos == end_block.position():
            end_block = end_block.previous()

        cursor.beginEditBlock()
        block = start_block
        last = end_block.blockNumber()
        while block.isValid() and block.blockNumber() <= last:
            edit = QTextCursor(block)
            text = block.text()
            if dedent:
                count = 0
                while count < len(INDENT) and count < len(text) and text[count] == " ":
                    count += 1
                if count == 0 and text.startswith("\t"):
                    count = 1
                if count:
                    edit.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, count)
                    edit.removeSelectedText()
            elif text.strip():
                edit.insertText(INDENT)
            block = block.next()
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        blocked = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier

        if key == Qt.Key.Key_Tab and not mods & blocked:
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._shift_lines(False)
                return
            col = cursor.positionInBlock()
            if self.snippet_lookup:
                match = WORD_RE.search(cursor.block().text()[:col])
                if match:
                    body = self.snippet_lookup(self.language_id, match.group())
                    if body is not None:
                        self._insert_snippet(body, len(match.group()))
                        return
            spaces_to_insert = len(INDENT) - (col % len(INDENT))
            cursor.insertText(" " * spaces_to_insert)
            return

        if key == Qt.Key.Key_Backtab:
            self._shift_lines(True)
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not mods & blocked:
            cursor = self.textCursor()
            before = cursor.block().text()[:cursor.positionInBlock()]
            stripped = before.lstrip(" \t")
            indent = before[:len(before) - len(stripped)]
            if self.auto_indent_colon and stripped.rstrip().endswith(":"):
                indent += INDENT
            cursor.beginEditBlock()
            cursor.insertBlock()
            cursor.insertText(indent)
            cursor.endEditBlock()
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            return

        if key == Qt.Key.Key_Backspace and not mods & blocked:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                col = cursor.positionInBlock()
                prefix = cursor.block().text()[:col]
                if prefix and not prefix.strip(" "):
                    spaces_to_delete = col % len(INDENT) or len(INDENT)
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
        width = self.line_number_area_width()
        if self.viewportMargins().left() != width:
            self.setViewportMargins(width, 0, 0, 0)

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
        painter.fillRect(event.rect(), QColor(self.colors["editor.background"]))
        normal = QColor(self.colors["editorLineNumber.foreground"])
        active = QColor(self.colors["editorLineNumber.activeForeground"])
        current = self.textCursor().blockNumber()
        painter.setFont(self.font())
        line_height = self.fontMetrics().height()
        width = self.line_number_area.width()

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(active if blockNumber == current else normal)
                painter.drawText(0, top, width, line_height, Qt.AlignmentFlag.AlignCenter, str(blockNumber + 1))
            block = block.next()
            if not block.isValid():
                break
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            blockNumber += 1
        painter.end()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.font_size = min(48, self.font_size + 1)
            elif delta < 0:
                self.font_size = max(6, self.font_size - 1)
            self._apply_font()
            self.update_line_number_area_width(0)
            self.line_number_area.update()
            event.accept()
        elif event.angleDelta().y() and not event.pixelDelta().y() and not event.modifiers():
            bar = self.verticalScrollBar()
            base = self._scroll_target if self._scroll_anim.state() == QPropertyAnimation.State.Running else bar.value()
            target = int(max(bar.minimum(), min(bar.maximum(), round(base - event.angleDelta().y() / 120 * 3))))
            self._scroll_anim.stop()
            self._scroll_anim.setStartValue(bar.value())
            self._scroll_anim.setEndValue(target)
            self._scroll_target = target
            self._scroll_anim.start()
            event.accept()
        else:
            super().wheelEvent(event)

class LspSignals(QObject):
    completions_ready = pyqtSignal(list)

class AntimatterEditor(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {themes.get()['colors']['editor.background']};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text = AntimatterTextEdit(self)
        layout.addWidget(self.text)

        self.highlighter = PythonHighlighter(self.text.document())

        self.lsp = LspClient()
        self.loop = lsp.get_loop()
        self.lsp_signals = LspSignals()
        self.lsp_signals.completions_ready.connect(self._display_popup)
        self._lsp_lock = asyncio.Lock()
        self._opened_path = None
        self._language = "python"

        self.text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self._show_context_menu)
        self.text.cursorPositionChanged.connect(self._close_popup)

        self.text.installEventFilter(self)
        self.comp_popup = None
        self._current_completions = []
        self._current_file_path = None

    def eventFilter(self, obj, event):
        if obj == self.text:
            kind = event.type()
            if kind == event.Type.FocusOut:
                self._close_popup()
            elif kind == event.Type.KeyPress:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Space:
                    self.show_completions()
                    return True

                if self.comp_popup and self.comp_popup.isVisible():
                    if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                        row = self.comp_popup.currentRow()
                        if row >= 0:
                            self._apply_completion(row)
                        return True
                    elif event.key() == Qt.Key.Key_Escape:
                        self._close_popup()
                        return True
                    elif event.key() == Qt.Key.Key_Down:
                        self.comp_popup.setCurrentRow(min(self.comp_popup.count() - 1, self.comp_popup.currentRow() + 1))
                        return True
                    elif event.key() == Qt.Key.Key_Up:
                        self.comp_popup.setCurrentRow(max(0, self.comp_popup.currentRow() - 1))
                        return True

        return super().eventFilter(obj, event)

    def apply_theme(self, theme):
        self.setStyleSheet(f"background-color: {theme['colors']['editor.background']};")
        self.text.apply_theme(theme)
        self.highlighter.apply_colors(theme["tokenColors"])

    def set_language_from_path(self, path):
        self.text.language_id = languages.language_id(path)
        lexer = languages.lexer_for(path)
        current = self.highlighter.lexer
        if (lexer is None) != (current is None) or (lexer is not None and type(lexer) is not type(current)):
            self.highlighter.set_lexer(lexer)
        self.text.auto_indent_colon = isinstance(lexer, PythonLexer)
        self._language = languages.language_for(path)

    def set_content(self, content):
        self.text.setPlainText(content)
        self.text.document().clearUndoRedoStacks()
        self.text.document().setModified(False)

    def start_lsp(self, file_path=None):
        if file_path:
            self._current_file_path = file_path
        self.set_language_from_path(self._current_file_path)

    def shutdown(self):
        self._close_popup()
        if self.lsp.running:
            future = asyncio.run_coroutine_threadsafe(self._stop_lsp(), self.loop)
            try:
                future.result(timeout=3)
            except Exception:
                pass

    async def _stop_lsp(self):
        async with self._lsp_lock:
            await self.lsp.stop()
            self._opened_path = None

    def show_completions(self):
        if not self._language or self._language not in lsp.LANG_SERVERS:
            return

        cursor = self.text.textCursor()
        line = cursor.blockNumber()
        col = cursor.positionInBlock()
        text = self.text.toPlainText()
        path = self._current_file_path or os.path.join(os.getcwd(), "untitled.py")
        language = self._language

        async def get_comp():
            async with self._lsp_lock:
                if not self.lsp.running:
                    self._opened_path = None
                    started = await self.lsp.start(language, os.path.dirname(os.path.abspath(path)))
                    if not started:
                        return
                if self._opened_path != path:
                    await self.lsp.did_close()
                    await self.lsp.did_open(path, text)
                    self._opened_path = path
                else:
                    await self.lsp.did_change(text)
                completions = await self.lsp.complete(line, col)
            if completions:
                self.lsp_signals.completions_ready.emit(completions)

        asyncio.run_coroutine_threadsafe(get_comp(), self.loop)

    def _close_popup(self):
        if self.comp_popup is not None:
            popup, self.comp_popup = self.comp_popup, None
            popup.close()
            popup.deleteLater()

    def _display_popup(self, completions):
        self._close_popup()

        if not self.text.hasFocus():
            return

        self._current_completions = completions

        popup = QListWidget(self.text)
        popup.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        popup.viewport().setAutoFillBackground(False)

        popup.setStyleSheet("""
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 10px;
                padding: 3px;
                outline: none;
            }
            QListWidget::item {
                padding: 2px 4px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background-color: #313244;
                color: #ffffff;
            }
        """)

        for item in completions:
            popup.addItem(f" {item['label']} ")

        if completions:
            popup.setCurrentRow(0)

        cursor_rect = self.text.cursorRect()
        popup.move(self.text.viewport().mapToGlobal(cursor_rect.bottomLeft()))
        shapes.fade_window(popup, 110)

        popup.itemClicked.connect(lambda item: self._apply_completion(popup.row(item)))
        self.comp_popup = popup
        popup.show()

    def _apply_completion(self, row):
        if row < 0 or row >= len(self._current_completions):
            self._close_popup()
            return
        insert_text = self._current_completions[row]["insert"]

        cursor = self.text.textCursor()
        before = cursor.block().text()[:cursor.positionInBlock()]
        match = WORD_RE.search(before)
        self._close_popup()
        if match:
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(match.group()))
        cursor.insertText(insert_text)
        self.text.setTextCursor(cursor)
        self.text.setFocus()

    def _show_context_menu(self, pos):
        menu = shapes.round_menu(QMenu(self))

        copy_act = menu.addAction("Copy")
        copy_act.triggered.connect(self.text.copy)
        cut_act = menu.addAction("Cut")
        cut_act.triggered.connect(self.text.cut)
        paste_act = menu.addAction("Paste")
        paste_act.triggered.connect(self.text.paste)
        menu.addSeparator()
        comp_act = menu.addAction("Show Completions")
        comp_act.triggered.connect(self.show_completions)
        menu.addSeparator()

        diff_act = menu.addAction("View Git Diff")
        diff_act.triggered.connect(lambda: git.show_file_diff(self._current_file_path))
        blame_act = menu.addAction("View Git Blame")
        blame_act.triggered.connect(lambda: git.show_file_blame(self._current_file_path))
        status_act = menu.addAction("View Uncommitted Files")
        status_act.triggered.connect(self._show_git_status)

        menu.addSeparator()
        select_act = menu.addAction("Select All")
        select_act.triggered.connect(self.text.selectAll)

        menu.exec(self.text.mapToGlobal(pos))

    def _show_git_status(self):
        if not self._current_file_path:
            return
        git.get_status(self._current_file_path)

    def get(self, start="0.0", end="end-1c"):
        return self.text.toPlainText()

    def insert(self, pos, content):
        self.text.insertPlainText(content)

    def delete(self, start, end):
        self.text.clear()
