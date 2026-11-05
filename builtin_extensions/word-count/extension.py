_api = None


def count():
    editor = _api.current_editor()
    if editor is None:
        return
    text = editor.get()
    _api.message(f"Lines: {text.count(chr(10)) + 1}\nWords: {len(text.split())}\nCharacters: {len(text)}", "Word Count")


def activate(api):
    global _api
    _api = api
    api.commands.register("antimatter.word-count.count", count)


def deactivate():
    global _api
    _api = None
