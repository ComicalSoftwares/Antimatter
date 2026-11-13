# Inherited from a random repo online, gotta clean up this or make use of it later

from PyQt6.QtGui import QFont

BG = "#19191a"            # editor / terminal
BG_ALT = "#1e1e1e"        # sidebar
BG_CHROME = "#363636"     # window, tab bar
BG_PANEL = "#2a2a2e"      # dock titles, hover
BG_MENU = "#181825"
BORDER = "#313244"
FG = "#D8DEE9"
FG_BRIGHT = "#cdd6f4"
FG_DIM = "#a6adc8"
GUTTER = "#45475a"
SELECTION = "#2e3c64"
CURRENT_LINE = "#212125"
BRACKET = "#3b3b5c"
FIND_HIT = "#4a4420"
ACCENT = "#5400ba"
ACCENT_SOFT = "#8a79a3"
ERROR = "#f38ba8"
WARN = "#e5c07b"
OK = "#98c379"

SYNTAX = {
    "kw": "#c678dd", "const": "#d19a66", "builtin": "#e5c07b", "func": "#61afef",
    "defn": "#61afef", "cls": "#e5c07b", "str": "#98c379", "comment": "#5c6370",
    "num": "#d19a66", "deco": "#56b6c2", "self": "#e06c75",
}

MONO_FAMILIES = ["Consolas", "Cascadia Mono", "JetBrains Mono", "DejaVu Sans Mono", "Menlo", "Monospace"]


def mono_font(size=13):
    f = QFont()
    f.setFamilies(MONO_FAMILIES)
    f.setPointSize(size)
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setFixedPitch(True)
    return f
