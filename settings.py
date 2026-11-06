import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".antimatter" / "settings.json"

DEFAULTS = {
    "theme": "Antimatter Dark",
    "font_family": "Consolas",
    "font_size": 13,
    "font_files": [],
    "tab_size": 4,
    "word_wrap": False,
    "highlight_current_line": True,
    "smooth_scrolling": True,
    "animations": True,
    "sidebar_position": "left",
    "sidebar_visible": True,
    "sidebar_width": 260,
    "window_geometry": "",
}

_data = dict(DEFAULTS)
_observers = []


def load():
    global _data
    _data = dict(DEFAULTS)
    try:
        stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        for key, value in stored.items():
            if key in DEFAULTS and type(value) is type(DEFAULTS[key]):
                _data[key] = value
    except Exception:
        pass


def get(key):
    return _data.get(key, DEFAULTS.get(key))


def set(key, value, persist=True):
    if _data.get(key) == value:
        return
    _data[key] = value
    if persist:
        save()
    for callback in list(_observers):
        callback(key, value)


def save():
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(_data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Settings] Could not save settings: {e}")


def reset():
    keep = {"font_files": _data.get("font_files", []), "window_geometry": _data.get("window_geometry", "")}
    _data.update(DEFAULTS)
    _data.update(keep)
    save()
    for callback in list(_observers):
        callback(None, None)


def observe(callback):
    _observers.append(callback)


def unobserve(callback):
    if callback in _observers:
        _observers.remove(callback)
