_api = None


def _selected_or_all():
    editor = _api.current_editor()
    if editor is None:
        return None, None
    cursor = editor.text.textCursor()
    if not cursor.hasSelection():
        cursor.select(cursor.SelectionType.Document)
    return editor, cursor


def _replace(transform):
    editor, cursor = _selected_or_all()
    if editor is None:
        return
    text = cursor.selectedText().replace("\u2029", "\n")
    cursor.insertText(transform(text))


def activate(api):
    global _api
    _api = api
    commands = api.commands
    commands.register("antimatter.text-tools.sort", lambda: _replace(lambda t: "\n".join(sorted(t.split("\n"), key=str.lower))))
    commands.register("antimatter.text-tools.dedupe", lambda: _replace(lambda t: "\n".join(dict.fromkeys(t.split("\n")))))
    commands.register("antimatter.text-tools.upper", lambda: _replace(str.upper))
    commands.register("antimatter.text-tools.lower", lambda: _replace(str.lower))
    commands.register("antimatter.text-tools.trim", lambda: _replace(lambda t: "\n".join(line.rstrip() for line in t.split("\n"))))


def deactivate():
    global _api
    _api = None
