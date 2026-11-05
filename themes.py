import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".antimatter" / "settings.json"
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
    try:
        _saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8")).get("theme", DEFAULT_NAME)
    except Exception:
        _saved = DEFAULT_NAME


def restore():
    global _current
    if _saved in _themes:
        _current = _saved
    return _current


def save_settings():
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        data["theme"] = _saved
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Themes] Could not save settings: {e}")
