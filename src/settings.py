# Antimatter's settings module

import json
from pathlib import Path
from PyQt6.QtCore import QStandardPaths

DEFAULTS = {
    "font_family": "Consolas",
    "font_size": 12,
    "tab_width": 4,
    "use_spaces": True,
    "word_wrap": False,
    "show_line_numbers": True,
    "highlight_line": True,
    "auto_indent": True,
    "discord_rpc": True,
    "lsp_enabled": True,
}

LIMITS = {"font_size": (6, 72), "tab_width": (1, 8)}

PATH = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)) / "settings.json"


def _coerce(key, default, value):
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, int):
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        lo, hi = LIMITS.get(key, (-10**9, 10**9))
        return min(max(value, lo), hi)
    if isinstance(default, str):
        return value if isinstance(value, str) and value else default
    return default


def load():
    data = dict(DEFAULTS)
    try:
        stored = json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return data
    if not isinstance(stored, dict):
        return data
    for key, default in DEFAULTS.items():
        data[key] = _coerce(key, default, stored.get(key, default))
    return data


def save(data):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")