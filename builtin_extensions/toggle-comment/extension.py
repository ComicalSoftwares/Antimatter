import os
from PyQt6.QtGui import QTextCursor

PREFIXES = {
    ".py": "# ", ".sh": "# ", ".rb": "# ", ".yml": "# ", ".yaml": "# ", ".toml": "# ", ".ini": "; ", ".cfg": "# ",
    ".js": "// ", ".jsx": "// ", ".ts": "// ", ".tsx": "// ", ".c": "// ", ".h": "// ", ".cpp": "// ", ".hpp": "// ",
    ".java": "// ", ".cs": "// ", ".go": "// ", ".rs": "// ", ".kt": "// ", ".php": "// ",
    ".sql": "-- ", ".lua": "-- ", ".bat": "REM ",
}

_api = None


def toggle():
    editor = _api.current_editor()
    if editor is None:
        return
    prefix = PREFIXES.get(os.path.splitext(_api.current_path() or "")[1].lower(), "# ")
    bare = prefix.rstrip()
    cursor = editor.text.textCursor()
    doc = editor.text.document()
    first = doc.findBlock(cursor.selectionStart())
    end_pos = cursor.selectionEnd()
    last = doc.findBlock(end_pos)
    if last != first and end_pos == last.position():
        last = last.previous()

    blocks = []
    block = first
    while block.isValid() and block.blockNumber() <= last.blockNumber():
        blocks.append(block)
        block = block.next()

    targets = [b for b in blocks if b.text().strip()]
    uncomment = bool(targets) and all(b.text().lstrip().startswith(bare) for b in targets)

    cursor.beginEditBlock()
    for block in targets:
        text = block.text()
        indent = len(text) - len(text.lstrip())
        edit = QTextCursor(block)
        edit.setPosition(block.position() + indent)
        if uncomment:
            remove = len(prefix) if text.lstrip().startswith(prefix) else len(bare)
            edit.setPosition(edit.position() + remove, QTextCursor.MoveMode.KeepAnchor)
            edit.removeSelectedText()
        else:
            edit.insertText(prefix)
    cursor.endEditBlock()


def activate(api):
    global _api
    _api = api
    api.commands.register("antimatter.toggle-comment.toggle", toggle)


def deactivate():
    global _api
    _api = None
