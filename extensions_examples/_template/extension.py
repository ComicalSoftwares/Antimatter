_api = None


def hello():
    name = _api.current_path() or "an unsaved file"
    _api.message(f"Hello from {name}")


def on_saved(editor, path):
    print(f"saved {path}")


def activate(api):
    global _api
    _api = api
    api.commands.register("me.my-extension.hello", hello)
    api.on("file_saved", on_saved)


def deactivate():
    global _api
    _api = None
