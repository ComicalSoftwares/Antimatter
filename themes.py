import json

import settings

DEFAULT_NAME = "Antimatter Dark"

DEFAULT = {
    "name": DEFAULT_NAME,
    "type": "dark",
    "colors": {
        "editor.background": "#19191a",
        "editor.foreground": "#D8DEE9",
        "editor.selectionBackground": "#2e3c64",
        "editor.lineHighlightBackground": "#1f1f21",
        "editorLineNumber.foreground": "#45475a",
        "editorLineNumber.activeForeground": "#a6adc8",
    },
    "tokenColors": {
        "function": "#61afef",
        "namespace": "#61afef",
        "class": "#e5c07b",
        "builtin": "#e5c07b",
        "tag": "#e06c75",
        "keyword": "#c678dd",
        "string": "#98c379",
        "number": "#d19a66",
        "comment": "#5c6370",
        "operator": "#56b6c2",
    },
    "chrome": {
        "window": "#363636",
        "surface": "#2a2a2e",
        "sidebar": "#1e1e1e",
        "select": "#313244",
        "handle": "#45475a",
        "handle_hover": "#585b70",
        "text": "#cdd6f4",
        "muted": "#6c7086",
        "popup": "#181825",
        "input": "#1e1e2e",
        "border": "#313244",
    },
}

SCOPE_RULES = (
    ("keyword.operator", "operator"),
    ("entity.name.function", "function"),
    ("support.function", "function"),
    ("entity.name.class", "class"),
    ("entity.name.type", "class"),
    ("support.class", "class"),
    ("support.type", "builtin"),
    ("variable.language", "builtin"),
    ("entity.name.tag", "tag"),
    ("entity.name.namespace", "namespace"),
    ("entity.name.module", "namespace"),
    ("constant.numeric", "number"),
    ("keyword", "keyword"),
    ("storage", "keyword"),
    ("string", "string"),
    ("comment", "comment"),
)

_themes = {DEFAULT_NAME: (DEFAULT, None)}
_current = DEFAULT_NAME
_saved = DEFAULT_NAME


def _normalize(raw):
    theme = {
        "name": raw.get("name") or raw.get("label") or "Untitled",
        "type": raw.get("type", "dark"),
        "colors": dict(DEFAULT["colors"]),
        "tokenColors": dict(DEFAULT["tokenColors"]),
        "chrome": {k: v for k, v in raw.get("chrome", {}).items() if isinstance(v, str)},
    }
    if raw.get("type") == "light":
        theme["colors"].update({
            "editor.background": "#ffffff",
            "editor.foreground": "#24292e",
            "editor.selectionBackground": "#c8dcf8",
            "editor.lineHighlightBackground": "#f3f5f8",
            "editorLineNumber.foreground": "#b0b7c3",
            "editorLineNumber.activeForeground": "#57606a",
        })
    theme["colors"].update({k: v for k, v in raw.get("colors", {}).items() if isinstance(v, str)})
    tokens = raw.get("tokenColors", {})
    if isinstance(tokens, dict):
        theme["tokenColors"].update({k: v for k, v in tokens.items() if k in DEFAULT["tokenColors"] and isinstance(v, str)})
    else:
        for rule in tokens:
            color = (rule.get("settings") or {}).get("foreground")
            scopes = rule.get("scope", [])
            if isinstance(scopes, str):
                scopes = [s.strip() for s in scopes.split(",")]
            if not color:
                continue
            for scope in scopes:
                for prefix, key in SCOPE_RULES:
                    if scope.startswith(prefix):
                        theme["tokenColors"][key] = color[:7]
                        break
    for key, value in theme["colors"].items():
        theme["colors"][key] = value[:7] if value.startswith("#") and len(value) > 7 else value
    return theme


def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return _normalize(json.load(f))


def register(theme, source=None, label=None):
    if label:
        theme = dict(theme, name=label)
    _themes[theme["name"]] = (theme, source)


def unregister_source(source):
    for name in [n for n, (_, src) in _themes.items() if src == source]:
        del _themes[name]
    global _current
    if _current not in _themes:
        _current = DEFAULT_NAME


def names():
    return list(_themes)


def get(name=None):
    return _themes.get(name or _current, _themes[DEFAULT_NAME])[0]


def current_name():
    return _current


def set_current(name, persist=True):
    global _current, _saved
    if name not in _themes:
        return False
    _current = name
    if persist:
        _saved = name
        save_settings()
    return True


def load_settings():
    global _saved
    _saved = settings.get("theme")


def restore():
    global _current
    if _saved in _themes:
        _current = _saved
    return _current


def save_settings():
    settings.set("theme", _saved)


def _hex(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, amount):
    ra, rb = _hex(a), _hex(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * amount) for x, y in zip(ra, rb))


def is_dark(color):
    r, g, b = _hex(color)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def chrome(theme=None):
    theme = theme or get()
    colors = theme["colors"]
    bg = colors["editor.background"][:7]
    fg = colors["editor.foreground"][:7]
    dark = is_dark(bg)
    derived = {
        "window": mix(bg, fg, 0.17),
        "surface": mix(bg, fg, 0.10),
        "sidebar": mix(bg, fg, 0.04),
        "select": mix(bg, fg, 0.20),
        "handle": mix(bg, fg, 0.25),
        "handle_hover": mix(bg, fg, 0.36),
        "text": mix(bg, fg, 0.90),
        "muted": mix(bg, fg, 0.50),
        "popup": mix(bg, fg, 0.03),
        "input": mix(bg, fg, 0.07),
        "border": mix(bg, fg, 0.16),
    }
    derived.update(theme.get("chrome", {}))
    derived["bg"] = bg
    derived["fg"] = fg
    derived["dark"] = dark
    derived["accent"] = colors.get("accent", "#5400ba")
    derived["accent_hover"] = mix(derived["accent"], "#ffffff", 0.18)
    derived["select_text"] = "#ffffff" if dark else fg
    derived["danger"] = "#f38ba8" if dark else "#d73a49"
    return derived
