import os
import re
import asyncio
import threading
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument, QTextFormat
from PyQt6.QtWidgets import (
    QWidget, QPlainTextEdit, QTextEdit, QListWidget, QMenu, QHBoxLayout, 
    QFrame, QVBoxLayout, QLabel, QLineEdit, QToolButton
)
from lsp import LspClient
import theme
import builtins
import keyword

KEYWORDS = frozenset(keyword.kwlist)
CONSTANTS = frozenset({"True", "False", "None"})
BUILTINS = frozenset(n for n in dir(builtins) if not n.startswith("_")) - KEYWORDS

_PREFIX = r"[rRbBuUfF]{0,2}"
_TOKEN = re.compile("|".join([
    r"(?P<comment>\#[^\n]*)",
    rf"(?P<tri>{_PREFIX}(?:\"\"\"|'''))",
    rf"(?P<str>{_PREFIX}(?:\"(?:\\.|[^\"\\])*\"?|'(?:\\.|[^'\\])*'?))",
    r"(?P<deco>^[ \t]*@[\w.]+)",
    r"(?P<defn>\b(?:def|class)[ \t]+[A-Za-z_]\w*)",
    r"(?P<num>\b(?:0[xX][\da-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?[jJ]?))",
    r"(?P<word>[A-Za-z_]\w*)",
]))

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class PythonHighlighter(QSyntaxHighlighter):
    TRIPLE = {1: '"""', 2: "'''"}

    def __init__(self, document):
        super().__init__(document)
        self.f = {}
        for name, color in theme.SYNTAX.items():
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if name in ("comment", "self"):
                fmt.setFontItalic(True)
            self.f[name] = fmt

    def highlightBlock(self, text):
        f, fmt = self.f, self.setFormat
        pos = 0
        prev = self.previousBlockState()
        if prev in self.TRIPLE:
            end = text.find(self.TRIPLE[prev])
            if end < 0:
                fmt(0, len(text), f["str"])
                self.setCurrentBlockState(prev)
                return
            pos = end + 3
            fmt(0, pos, f["str"])
        self.setCurrentBlockState(0)

        search = _TOKEN.search
        while True:
            m = search(text, pos)
            if not m:
                return
            kind, s, e = m.lastgroup, m.start(), m.end()
            pos = e
            if kind == "word":
                w = m.group()
                if w in KEYWORDS:
                    fmt(s, e - s, f["const"] if w in CONSTANTS else f["kw"])
                elif w in BUILTINS:
                    fmt(s, e - s, f["builtin"])
                elif w in ("self", "cls"):
                    fmt(s, e - s, f["self"])
                elif text[e:e + 1] == "(":
                    fmt(s, e - s, f["func"])
            elif kind == "tri":
                delim = m.group()[-3:]
                end = text.find(delim, e)
                if end < 0:
                    fmt(s, len(text) - s, f["str"])
                    self.setCurrentBlockState(1 if delim == '"""' else 2)
                    return
                pos = end + 3
                fmt(s, pos - s, f["str"])
            elif kind == "defn":
                kw_end = s + (3 if m.group().startswith("def") else 5)
                fmt(s, kw_end - s, f["kw"])
                fmt(kw_end, e - kw_end, f["defn"] if m.group().startswith("def") else f["cls"])
            else:
                fmt(s, e - s, f[kind])


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        def fmt(color, bold=False, italic=False, underline=False, bg=None):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold: f.setFontWeight(700)
            if italic: f.setFontItalic(True)
            if underline: f.setFontUnderline(True)
            if bg: f.setBackground(QColor(bg))
            return f

        self.rules.append((re.compile(r"^#{1,6}\s+.*$"), fmt("#61afef", bold=True)))
        self.rules.append((re.compile(r"\*\*.*?\*\*|__.*?__"), fmt("#e5c07b", bold=True)))
        self.rules.append((re.compile(r"\*[^\*\n]+\*|_[^_\n]+_"), fmt("#c678dd", italic=True)))
        self.rules.append((re.compile(r"`[^`]+`"), fmt("#3ab557", bg="#23272e")))
        self.rules.append((re.compile(r"^\s*>.*$"), fmt("#5c6370", italic=True)))
        self.rules.append((re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), fmt("#56b6c2", underline=True)))
        self.rules.append((re.compile(r"^\s*([\*\-\+]|\d+\.)\s+"), fmt("#d19a66", bold=True)))

    def highlightBlock(self, text):
        for pattern, fmt_style in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt_style)


class AntimatterTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.font_family = "Consolas"
        self.font_size = 12
        self.tab_width = 4
        self.use_spaces = True
        self.word_wrap = False
        self.show_line_numbers = True
        self.highlight_line = True
        self.auto_indent = True
        self.is_markdown = False
        self.highlighter = None
        self.python_mode = False
        self.comment_prefix = "#"

        self.setStyleSheet(theme.code)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setCursorWidth(2)

        self.line_number_area = LineNumberArea(self)
        self._apply_font()
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self._refresh_selections)
        self.cursorPositionChanged.connect(self.line_number_area.update)
        self.update_line_number_area_width(0)
        self._refresh_selections()
        self.verticalScrollBar().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.horizontalScrollBar().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

    @property
    def INDENT(self):
        return " " * self.tab_width if self.use_spaces else "\t"

    def apply_wrap(self):
        wrap = self.is_markdown or self.word_wrap
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth if wrap
                         else QPlainTextEdit.LineWrapMode.NoWrap)
                         
    def apply_settings(self, s):
        self.font_family = s["font_family"]
        self.font_size = s["font_size"]
        self.tab_width = s["tab_width"]
        self.use_spaces = s["use_spaces"]
        self.word_wrap = s["word_wrap"]
        self.show_line_numbers = s["show_line_numbers"]
        self.highlight_line = s["highlight_line"]
        self.auto_indent = s["auto_indent"]
        self._apply_font()
        self.apply_wrap()
        self.line_number_area.setVisible(self.show_line_numbers)
        self.update_line_number_area_width(0)
        self._refresh_selections()

    def keyPressEvent(self, event):
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)

        if key == Qt.Key.Key_Tab and not ctrl:
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._shift_lines(indent=True)
            elif self.use_spaces:
                cursor.insertText(" " * (self.tab_width - cursor.columnNumber() % self.tab_width))
            else:
                cursor.insertText("\t")
            return

        if key == Qt.Key.Key_Backtab:
            self._shift_lines(indent=False)
            return

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not ctrl:
            self._smart_newline()
            return

        if key == Qt.Key.Key_Slash and ctrl:
            self._toggle_comment()
            return

        if key == Qt.Key.Key_Backspace:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                col = cursor.columnNumber()
                prefix = cursor.block().text()[:col]
                if prefix and prefix.isspace():
                    cursor.setPosition(cursor.position() - (col % self.tab_width or self.tab_width), QTextCursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
                    return

        super().keyPressEvent(event)


    def _smart_newline(self):
        cursor = self.textCursor()
        before = cursor.block().text()[:cursor.positionInBlock()]
        indent = ""
        if self.auto_indent:
            indent = before[:len(before) - len(before.lstrip(" \t"))]
            if self.python_mode and before.rstrip().endswith(":") and not before.lstrip().startswith("#"):
                indent += self.INDENT
        cursor.insertText("\n" + indent)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def _selected_blocks(self):
        cursor = self.textCursor()
        doc = self.document()
        first = doc.findBlock(cursor.selectionStart())
        last = doc.findBlock(cursor.selectionEnd())
        if (cursor.hasSelection() and last.blockNumber() > first.blockNumber()
                and cursor.selectionEnd() == last.position()):
            last = last.previous()
        blocks, block = [], first
        while block.isValid():
            blocks.append(block)
            if block.blockNumber() >= last.blockNumber():
                break
            block = block.next()
        return blocks
    
    def _shift_lines(self, indent):
        blocks = self._selected_blocks()
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for block in blocks:
            text = block.text()
            c = QTextCursor(block)
            if indent:
                if text.strip() or len(blocks) == 1:
                    c.insertText(self.INDENT)
            else:
                n = 1 if text.startswith("\t") else min(self.tab_width, len(text) - len(text.lstrip(" ")))
                if n:
                    c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, n)
                    c.removeSelectedText()
        edit.endEditBlock()
    
    def _toggle_comment(self):
        prefix = self.comment_prefix
        blocks = [b for b in self._selected_blocks() if b.text().strip()]
        if not blocks:
            return
        all_commented = all(b.text().lstrip().startswith(prefix) for b in blocks)
        min_indent = min(len(b.text()) - len(b.text().lstrip()) for b in blocks)
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for block in blocks:
            text = block.text()
            c = QTextCursor(block)
            if all_commented:
                i = len(text) - len(text.lstrip())
                n = len(prefix) + (1 if text[i + len(prefix):i + len(prefix) + 1] == " " else 0)
                c.setPosition(block.position() + i)
                c.setPosition(block.position() + i + n, QTextCursor.MoveMode.KeepAnchor)
                c.removeSelectedText()
            else:
                c.setPosition(block.position() + min_indent)
                c.insertText(prefix + " ")
        edit.endEditBlock()
    
    def _apply_font(self):
        f = theme.mono_font(self.font_size)
        f.setFamilies([self.font_family] + theme.MONO_FAMILIES)
        self.setFont(f)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * self.tab_width)
        self.update_line_number_area_width(0)
        self.line_number_area.update()

    def line_number_area_width(self):
        digits = 1
        max_val = max(1, self.blockCount())
        while max_val >= 10:
            max_val //= 10
            digits += 1
        space = 25 + self.fontMetrics().horizontalAdvance('9') * digits
        return max(45, space)

    def update_line_number_area_width(self, _):
        width = self.line_number_area_width() if self.show_line_numbers else 0
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
        painter.fillRect(event.rect(), QColor("#19191a"))

        current = self.textCursor().blockNumber()
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#cdd6f4") if blockNumber == current else QColor("#45475a"))
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
            self._apply_font()
            event.accept()
        else:
            super().wheelEvent(event)

    def set_search_highlights(self, ranges):
        self._find_ranges = ranges[:500]
        self._refresh_selections()

    _OPEN = {"(": ")", "[": "]", "{": "}"}
    _CLOSE = {v: k for k, v in _OPEN.items()}
    
    def _bracket_pair(self):
        doc = self.document()
        pos = self.textCursor().position()
        for p in (pos, pos - 1):
            if p < 0:
                continue
            ch = doc.characterAt(p)
            if ch in self._OPEN:
                other, step = self._OPEN[ch], 1
            elif ch in self._CLOSE:
                other, step = self._CLOSE[ch], -1
            else:
                continue
            depth = 0
            stop = min(doc.characterCount(), p + 20000) if step > 0 else max(-1, p - 20000)
            for i in range(p, stop, step):
                c = doc.characterAt(i)
                if c == ch:
                    depth += 1
                elif c == other:
                    depth -= 1
                    if depth == 0:
                        return [p, i]
        return []
    
    def _refresh_selections(self):
        sels = []
    
        if self.highlight_line:
            line = QTextEdit.ExtraSelection()
            line.format.setBackground(QColor(theme.CURRENT_LINE))
            line.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            c = self.textCursor()
            c.clearSelection()
            line.cursor = c
            sels.append(line)
    
        for pos in self._bracket_pair():
            s = QTextEdit.ExtraSelection()
            c = QTextCursor(self.document())
            c.setPosition(pos)
            c.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
            s.cursor = c
            s.format.setBackground(QColor(theme.BRACKET))
            sels.append(s)
    
        for start, end in getattr(self, "_find_ranges", []):
            s = QTextEdit.ExtraSelection()
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            s.cursor = c
            s.format.setBackground(QColor("#313244"))
            sels.append(s)
    
        self.setExtraSelections(sels)


class FindBar(QFrame):
    def __init__(self, editor_container):
        super().__init__()
        self.editor = editor_container
        self.setStyleSheet(theme.findbar)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        row1 = QHBoxLayout()
        self.find = QLineEdit(placeholderText="Find")
        self.count = QLabel("")
        self.count.setMinimumWidth(70)
        self.case = QToolButton(text="Aa", checkable=True, toolTip="Match case")
        prev = QToolButton(text="↑", toolTip="Previous (Shift+Enter)")
        nxt = QToolButton(text="↓", toolTip="Next (Enter)")
        close = QToolButton(text="×", toolTip="Close (Esc)")

        for btn in (self.case, prev, nxt, close):
            btn.setStyleSheet(theme.flat_button_style)

        for w in (self.find, self.count, self.case, prev, nxt, close):
            row1.addWidget(w)
        outer.addLayout(row1)

        self.row2 = QWidget()
        r2 = QHBoxLayout(self.row2)
        r2.setContentsMargins(0, 0, 0, 0)
        self.repl = QLineEdit(placeholderText="Replace with")
        self.repl.setStyleSheet(theme.flat_input_style)
        b_rep, b_all = QToolButton(text="Replace"), QToolButton(text="Replace all")
        for btn in (b_rep, b_all):
            btn.setStyleSheet(theme.flat_button_style)
        self.find.setStyleSheet(theme.flat_input_style)

        r2.addWidget(self.repl)
        r2.addWidget(b_rep)
        r2.addWidget(b_all)
        outer.addWidget(self.row2)

        self.find.textChanged.connect(lambda: self.editor.refresh_find(select=True))
        self.case.toggled.connect(lambda: self.editor.refresh_find(select=True))
        self.find.returnPressed.connect(lambda: self.editor.step_find(False))
        self.repl.returnPressed.connect(self.editor.replace_one)
        prev.clicked.connect(lambda: self.editor.step_find(True))
        nxt.clicked.connect(lambda: self.editor.step_find(False))
        close.clicked.connect(self.close_bar)
        b_rep.clicked.connect(self.editor.replace_one)
        b_all.clicked.connect(self.editor.replace_all)
        self.find.installEventFilter(self)
        self.repl.installEventFilter(self)
        self.hide()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.close_bar()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and obj is self.find \
                    and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.editor.step_find(True)
                return True
        return super().eventFilter(obj, event)

    def open_bar(self, replace=False):
        sel = self.editor.text.textCursor().selectedText()
        if sel and "\u2029" not in sel:
            self.find.setText(sel)
        self.row2.setVisible(replace)
        self.show()
        self.find.setFocus()
        self.find.selectAll()
        self.editor.refresh_find()

    def close_bar(self):
        self.hide()
        self.editor.text.set_search_highlights([])
        self.editor.text.setFocus()


class LspSignals(QObject):
    completions_ready = pyqtSignal(list)


class AntimatterEditor(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #19191a; ")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.text = AntimatterTextEdit(self)
        self.findbar = FindBar(self)

        layout.addWidget(self.findbar)
        layout.addWidget(self.text)

        self.highlighter = None
        self._current_file_path = None

        self.lsp_timer = QTimer(self)
        self.lsp_timer.setSingleShot(True)
        self.lsp_timer.setInterval(250)
        self.lsp_timer.timeout.connect(self._send_lsp_change)

        self.lsp = LspClient()
        self.loop = asyncio.new_event_loop()
        self.lsp_signals = LspSignals()
        self.lsp_signals.completions_ready.connect(self._display_popup)
        
        threading.Thread(target=self._run_async_loop, daemon=True).start()

        self.text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self._show_context_menu)
        self.text.textChanged.connect(self._on_text_changed)
        self.text.document().contentsChanged.connect(self._on_document_changed)
        
        self.text.installEventFilter(self)
        self.text.viewport().installEventFilter(self)
        self.text.verticalScrollBar().valueChanged.connect(self._close_popup)
        self.text.horizontalScrollBar().valueChanged.connect(self._close_popup)
        self.comp_popup = None
        self.lsp_enabled = True
        self._current_completions = []

    def _send_lsp_change(self):
        if self.lsp.running:
            asyncio.run_coroutine_threadsafe(
                self.lsp.did_change(self.text.toPlainText()), self.loop)
                
    def apply_settings(self, s):
        self.text.apply_settings(s)
        self.lsp_enabled = s["lsp_enabled"]

    def stop_lsp(self):
        asyncio.run_coroutine_threadsafe(self.lsp.stop(), self.loop)

    def set_file_path(self, file_path):
        self._current_file_path = file_path
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""

        if self.highlighter:
            self.highlighter.setDocument(None)
            self.highlighter = None
            self.text.highlighter = None

        if ext == ".py":
            self.highlighter = PythonHighlighter(self.text.document())
            self.text.highlighter = self.highlighter
            self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        elif ext in (".md", ".markdown"):
            self.highlighter = MarkdownHighlighter(self.text.document())
            self.text.highlighter = self.highlighter
            self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.text.highlighter = None
            self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text.python_mode = (ext == ".py")
        self.text.comment_prefix = "//" if ext in (".c", ".h", ".cpp", ".hpp", ".js", ".ts", ".java", ".rs", ".go") else "#"
        self.text.is_markdown = ext in (".md", ".markdown")
        self.text.apply_wrap()

    def open_find(self, replace=False):
        self.findbar.open_bar(replace)

    def _find_flags(self):
        return QTextDocument.FindFlag.FindCaseSensitively if self.findbar.case.isChecked() else QTextDocument.FindFlag(0)

    def _all_matches(self, limit=5000):
        text, out = self.findbar.find.text(), []
        if not text:
            return out
        doc, flags = self.text.document(), self._find_flags()
        c = QTextCursor(doc)
        while len(out) < limit:
            c = doc.find(text, c, flags)
            if c.isNull():
                break
            out.append((c.selectionStart(), c.selectionEnd()))
        return out

    def refresh_find(self, select=False):
        matches = self._all_matches()
        self.text.set_search_highlights(matches)
        if select and matches:
            pos = self.text.textCursor().selectionStart()
            hit = next((m for m in matches if m[0] >= pos), matches[0])
            c = self.text.textCursor()
            c.setPosition(hit[0])
            c.setPosition(hit[1], QTextCursor.MoveMode.KeepAnchor)
            self.text.setTextCursor(c)
            self.text.centerCursor()
        cur = self.text.textCursor().selectionStart()
        idx = next((i + 1 for i, m in enumerate(matches) if m[0] == cur), 0)
        self.findbar.count.setText("" if not self.findbar.find.text() else
                                   ("No results" if not matches else f"{idx or '–'} / {len(matches)}"))
        self.findbar.find.setStyleSheet("border-color: #f38ba8;" if self.findbar.find.text() and not matches else "")

    def step_find(self, backwards):
        text = self.findbar.find.text()
        if not text:
            return
        flags = self._find_flags()
        if backwards:
            flags |= QTextDocument.FindFlag.FindBackward
        if not self.text.find(text, flags):
            c = self.text.textCursor()
            c.movePosition(QTextCursor.MoveOperation.End if backwards else QTextCursor.MoveOperation.Start)
            self.text.setTextCursor(c)
            self.text.find(text, flags)
        self.text.centerCursor()
        self.refresh_find()

    def replace_one(self):
        c = self.text.textCursor()
        sel, text = c.selectedText(), self.findbar.find.text()
        if c.hasSelection() and (sel == text if self.findbar.case.isChecked() else sel.lower() == text.lower()):
            c.insertText(self.findbar.repl.text())
        self.step_find(False)

    def replace_all(self):
        text = self.findbar.find.text()
        if not text:
            return
            
        content = self.text.toPlainText()
        repl_text = self.findbar.repl.text()

        if self.findbar.case.isChecked():
            n = content.count(text)
            new_content = content.replace(text, repl_text)
        else:
            pattern = re.compile(re.escape(text), re.IGNORECASE)
            matches = pattern.findall(content)
            n = len(matches)
            new_content = pattern.sub(repl_text, content)
            
        if n == 0:
            self.findbar.count.setText("No results")
            return

        cursor = self.text.textCursor()
        pos = cursor.position()
        anchor = cursor.anchor()

        self.text.setUpdatesEnabled(False)
        self.text.setPlainText(new_content)
        self.text.setUpdatesEnabled(True)
        max_len = len(new_content)
        cursor.setPosition(min(anchor, max_len))
        if pos != anchor:
            cursor.setPosition(min(pos, max_len), QTextCursor.MoveMode.KeepAnchor)
        else:
            cursor.setPosition(min(pos, max_len))
        self.text.setTextCursor(cursor)

        self.findbar.count.setText(f"{n} replaced")

        self.findbar.close_bar()

    def eventFilter(self, obj, event):
        popup_open = bool(self.comp_popup) and self.comp_popup.isVisible()
        etype = event.type()

        if obj is self.text.viewport():
            if popup_open and etype == event.Type.MouseButtonPress:
                self.comp_popup.close()
            return super().eventFilter(obj, event)

        if obj is self.text:
            if etype == event.Type.FocusOut and popup_open:
                self.comp_popup.close()
            elif etype == event.Type.KeyPress:
                key = event.key()
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Space:
                    self.show_completions()
                    return True
    
                if popup_open:
                    if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab, Qt.Key.Key_Space):
                        item = self.comp_popup.currentItem()
                        if item:
                            self._apply_completion(item.text().strip())
                        return True
                    if key == Qt.Key.Key_Escape:
                        self.comp_popup.close()
                        return True
                    if key == Qt.Key.Key_Down:
                        self.comp_popup.setCurrentRow(min(self.comp_popup.count() - 1, self.comp_popup.currentRow() + 1))
                        return True
                    if key == Qt.Key.Key_Up:
                        self.comp_popup.setCurrentRow(max(0, self.comp_popup.currentRow() - 1))
                        return True
                    if key not in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
                        self.comp_popup.close()
    
        return super().eventFilter(obj, event)

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_lsp(self, file_path=None):
        if not self.lsp_enabled:
            return
        if file_path and not file_path.lower().endswith(".py"):
            return
        if not file_path:
            file_path = os.path.join(os.getcwd(), "untitled.py")

        self._current_file_path = file_path
        root_path = os.path.dirname(os.path.abspath(file_path))
        text = self.text.toPlainText()

        async def init_sequence():
            await self.lsp.stop()
            if await self.lsp.start("python", root_path):
                await self.lsp.did_open(file_path, text)

        asyncio.run_coroutine_threadsafe(init_sequence(), self.loop)

    def _on_text_changed(self):
        self.text.set_search_highlights([])
        if self.lsp.running:
            self.lsp_timer.start()

    def _on_document_changed(self):
        if self.findbar.isVisible() and self.findbar.find.text():
            self.refresh_find(select=False)

    def show_completions(self):
        if self.lsp_timer.isActive():
            self.lsp_timer.stop()
            self._send_lsp_change()
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
        self._close_popup()
        if self.comp_popup:
            self.comp_popup.deleteLater()
    
        self._current_completions = completions
        viewport = self.text.viewport()
    
        popup = QListWidget(viewport)
        popup.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        popup.setStyleSheet(theme.popup)
        for item in completions:
            popup.addItem(f" {item['label']} ")
        popup.setCurrentRow(0)
        popup.itemClicked.connect(lambda item: self._apply_completion(item.text().strip()))
    
        rect = self.text.cursorRect()
        width = 280
        height = min(200, popup.sizeHintForRow(0) * min(len(completions), 8) + 6)
        x = min(rect.left(), max(0, viewport.width() - width))
        y = rect.bottom() + 2
        if y + height > viewport.height():
            y = max(0, rect.top() - height - 2)
    
        popup.setGeometry(x, y, width, height)
        popup.show()
        popup.raise_()
        self.comp_popup = popup
    
    def _apply_completion(self, label):
        insert_text = next(
        (c["insert"] for c in self._current_completions if c["label"] == label), label)

        cursor = self.text.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.insertText(insert_text)

        if self.comp_popup:
            self.comp_popup.close()

    def _close_popup(self, *_):
        if self.comp_popup:
            self.comp_popup.close()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setStyleSheet(theme.context_menu)

        copy_act = menu.addAction("Copy\tCtrl + C")
        copy_act.triggered.connect(self.text.copy)
        cut_act = menu.addAction("Cut\tCtrl + X")
        cut_act.triggered.connect(self.text.cut)
        paste_act = menu.addAction("Paste\tCtrl + V")
        paste_act.triggered.connect(self.text.paste)
        
        menu.addSeparator()
        select_act = menu.addAction("Select All\tCtrl + A")
        select_act.triggered.connect(self.text.selectAll)
        
        menu.addSeparator()
        find = menu.addAction("Find\tCtrl + F")
        find.triggered.connect(lambda: self.open_find(False))
        rep = menu.addAction("Replace\tCtrl + R")
        rep.triggered.connect(lambda: self.open_find(True))
        
        menu.addSeparator()
        comp_act = menu.addAction("Show Completions")
        comp_act.triggered.connect(self.show_completions)
        
        menu.exec(self.text.mapToGlobal(pos))

    def get(self, start="0.0", end="end-1c"):
        return self.text.toPlainText()

    def insert(self, pos, content):
        self.text.insertPlainText(content)

    def delete(self, start, end):
        self.text.clear()

    def shutdown(self):
        fut = asyncio.run_coroutine_threadsafe(self.lsp.stop(), self.loop)
        fut.add_done_callback(lambda _f: self.loop.call_soon_threadsafe(self.loop.stop))