_api = None
_closed = []


def remember(path):
    if path and path in _closed:
        _closed.remove(path)
    if path:
        _closed.append(path)
        del _closed[:-20]


def forget(editor, path):
    if path in _closed:
        _closed.remove(path)


def reopen():
    if _closed:
        _api.open_file(_closed.pop())


def activate(api):
    global _api
    _api = api
    api.on("file_closed", remember)
    api.on("file_opened", forget)
    api.commands.register("antimatter.reopen-closed.reopen", reopen)


def deactivate():
    global _api
    _api = None
    _closed.clear()
