import re

PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s]*(.*)")

_api = None


def find():
    editor = _api.current_editor()
    if editor is None:
        return
    found = []
    for number, line in enumerate(editor.get().split("\n"), 1):
        match = PATTERN.search(line)
        if match:
            found.append({"title": f"{number}: {match.group(1)} {match.group(2).strip()}".rstrip(), "line": number})
    if not found:
        _api.message("Nothing to do. Nice.", "TODO Finder")
        return
    _api.quick_pick(found, "Jump to a TODO", jump)


def jump(entry):
    editor = _api.current_editor()
    if editor is None:
        return
    block = editor.text.document().findBlockByNumber(entry["line"] - 1)
    cursor = editor.text.textCursor()
    cursor.setPosition(block.position())
    editor.text.setTextCursor(cursor)
    editor.text.centerCursor()
    editor.text.setFocus()


def activate(api):
    global _api
    _api = api
    api.commands.register("antimatter.todo-finder.find", find)


def deactivate():
    global _api
    _api = None
