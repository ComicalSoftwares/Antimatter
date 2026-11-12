import os
import re
import hashlib
import asyncio
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QObject, QTimer, QStandardPaths
from PyQt6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QWidget, QPlainTextEdit, QTextEdit, QListWidget, QMenu, QHBoxLayout, 
    QFrame, QVBoxLayout, QLabel, QLineEdit, QToolButton
)
from lsp import LspClient
import git
import theme
import builtins
import keyword
import task

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
        global sandboxed
        sandboxed = task.is_sandboxed()
        self.font_family = "Consolas"
        self.font_size = 13
        self.highlighter = None
        
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

    def set_search_highlights(self, ranges):
        self._find_ranges = ranges[:500]
        self._refresh_selections()

    def _refresh_selections(self):
        sels = []
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
        self.setStyleSheet('''
            FindBar { 
                background: #19191a; 
                border-bottom: 3px solid #313244; 
            }
            QToolTip {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                padding: 5px;
                font-size: 15px;
            }''')
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
        for w in (self.find, self.count, self.case, prev, nxt, close):
            row1.addWidget(w)
        outer.addLayout(row1)

        self.row2 = QWidget()
        r2 = QHBoxLayout(self.row2)
        r2.setContentsMargins(0, 0, 0, 0)
        self.repl = QLineEdit(placeholderText="Replace with")
        b_rep, b_all = QToolButton(text="Replace"), QToolButton(text="Replace all")
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

        # Setup sandbox-friendly recovery cache (~/.cache/antimatter/recovery/)
        base_cache = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        self.cache_dir = Path(base_cache) / "antimatter" / "recovery"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = None

        # 5-second debounce timer for typing inactivity auto-save
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.setInterval(5000)
        self.auto_save_timer.timeout.connect(self.write_to_cache)

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
        self.comp_popup = None
        self._current_completions = []

    def set_file_path(self, file_path):
        self._current_file_path = file_path
        ext = os.path.splitext(file_path)[1].lower() if file_path else ""

        if file_path:
            file_hash = hashlib.md5(file_path.encode('utf-8')).hexdigest()[:8]
            clean_name = Path(file_path).name
            self.cache_file = self.cache_dir / f"{clean_name}_{file_hash}.recovery"
        else:
            self.cache_file = self.cache_dir / "unsaved_scratch.py.recovery"

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

    def write_to_cache(self):
        if not self.cache_file:
            return
        content = self.text.toPlainText()
        try:
            self.cache_file.write_text(content, encoding="utf-8")
        except Exception as e:
            print(f"[Antimatter] Recovery write error: {e}")

    def clear_cache(self):
        if self.cache_file and self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass

    def reload_from_cache(self):
        if not self.cache_file or not self.cache_file.exists():
            return
        try:
            cached_text = self.cache_file.read_text(encoding="utf-8")
            
            cursor = self.text.textCursor()
            pos = cursor.position()
            anchor = cursor.anchor()
            
            v_scroll = self.text.verticalScrollBar().value()
            h_scroll = self.text.horizontalScrollBar().value()
            
            self.text.setPlainText(cached_text)
            
            max_len = len(cached_text)
            cursor.setPosition(min(anchor, max_len))
            if pos != anchor:
                cursor.setPosition(min(pos, max_len), QTextCursor.MoveMode.KeepAnchor)
            else:
                cursor.setPosition(min(pos, max_len))
            self.text.setTextCursor(cursor)
            
            self.text.verticalScrollBar().setValue(v_scroll)
            self.text.horizontalScrollBar().setValue(h_scroll)
            
            if self.highlighter:
                self.highlighter.rehighlight()
        except Exception as e:
            print(f"[Antimatter] Cache reload error: {e}")

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
            self.write_to_cache()
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

        self.write_to_cache()
        self.findbar.close_bar()

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
        self.text.set_search_highlights([])
        self.auto_save_timer.start()

        if not self.lsp.running:
            return
        content = self.text.toPlainText()
        asyncio.run_coroutine_threadsafe(self.lsp.did_change(content), self.loop)

    def _on_document_changed(self):
        if self.findbar.isVisible() and self.findbar.find.text():
            self.refresh_find(select=False)

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

        self.comp_popup = QListWidget(self.text)
        self.comp_popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        
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
            QMenu::separator {
                height: 1px;
                background-color: #89b4fa;
                margin: 4px 8px;
            }
        """)

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
        
        if not sandboxed:
            menu.addSeparator()
            diff_act = menu.addAction("View this file's Git Diff")
            diff_act.triggered.connect(lambda: git.show_file_diff(self._current_file_path))
            blame_act = menu.addAction("View this file's Git Blame")
            blame_act.triggered.connect(lambda: git.show_file_blame(self._current_file_path))
            status_act = menu.addAction("View Git Status")
            status_act.triggered.connect(self._show_git_status)
        else:
            pass
        menu.exec(self.text.mapToGlobal(pos))

    def _show_git_status(self):
        if not self._current_file_path:
            return
        root_dir = os.path.dirname(os.path.abspath(self._current_file_path))
        status_output = git.get_status(root_dir)

    def get(self, start="0.0", end="end-1c"):
        return self.text.toPlainText()

    def insert(self, pos, content):
        self.text.insertPlainText(content)

    def delete(self, start, end):
        self.text.clear()