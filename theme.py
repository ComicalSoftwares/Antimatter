"""One palette + one app-wide stylesheet. Per-widget stylesheets are slow to repolish,
so everything lives in APP_QSS and is applied once on the QApplication."""

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


APP_QSS = f"""
QMainWindow, QDialog {{ background: {BG_CHROME}; }}
QMessageBox, QInputDialog {{ background: {BG_MENU}; }}
QLabel {{ color: {FG_BRIGHT}; }}
QToolTip {{ background: {BG_MENU}; color: {FG_BRIGHT}; border: 1px solid {BORDER}; padding: 3px; }}

QMenuBar {{ background: {BG_CHROME}; color: {FG_BRIGHT}; }}
QMenuBar::item:selected {{ background: {ACCENT}; }}
QMenu {{ background: {BG_MENU}; color: {FG_BRIGHT}; border: 1px solid {BORDER}; }}
QMenu::item {{ padding: 4px 22px 4px 18px; }}
QMenu::item:selected {{ background: {BORDER}; color: white; }}
QMenu::item:disabled {{ color: {GUTTER}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 3px 6px; }}

QDockWidget {{ color: {FG_BRIGHT}; font-size: 12px; }}
QDockWidget::title {{ background: {BG_PANEL}; padding: 4px 8px; border-bottom: 1px solid #1e1e1e; }}

QTreeView, QListWidget {{ background: {BG_ALT}; color: {FG_BRIGHT}; border: none; font-size: 12px; outline: 0; }}
QTreeView::item:hover, QListWidget::item:hover {{ background: {BG_PANEL}; }}
QTreeView::item:selected, QListWidget::item:selected {{ background: {BORDER}; color: white; }}

QPlainTextEdit {{ background: {BG}; color: {FG}; border: none; selection-background-color: {SELECTION}; }}

QLineEdit {{ background: {BG}; color: {FG_BRIGHT}; border: 1px solid {BORDER}; border-radius: 3px;
            padding: 3px 5px; selection-background-color: {SELECTION}; }}
QLineEdit:focus {{ border-color: {ACCENT_SOFT}; }}

QPushButton, QToolButton {{ background: {BORDER}; color: {FG_BRIGHT}; border: none; padding: 4px 10px; border-radius: 3px; }}
QPushButton:hover, QToolButton:hover {{ background: {GUTTER}; }}
QToolButton:checked {{ background: {ACCENT}; color: white; }}
QToolButton#tabClose {{ background: transparent; color: {FG_DIM}; padding: 0; font-weight: bold; font-size: 14px; }}
QToolButton#tabClose:hover {{ color: {ERROR}; }}

QTabWidget::pane {{ border: none; background: {BG}; }}
QTabBar {{ background: {BG_CHROME}; }}
QTabBar::tab {{ background: {BG_CHROME}; color: {FG_DIM}; padding: 7px 10px 7px 12px; font-size: 13px; border: none; }}
QTabBar::tab:selected {{ background: {BG}; color: {FG_BRIGHT}; }}
QTabBar::tab:hover:!selected {{ background: {BG_PANEL}; }}

QStatusBar {{ background: {BG_CHROME}; color: {FG_DIM}; font-size: 12px; }}
QStatusBar::item {{ border: none; }}

QScrollBar:vertical {{ background: {BG}; width: 10px; margin: 0; border: none; }}
QScrollBar:horizontal {{ background: {BG}; height: 10px; margin: 0; border: none; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {GUTTER}; border-radius: 4px; min-height: 20px; min-width: 20px; }}
QScrollBar::handle:hover {{ background: #585b70; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; border: none; width: 0; height: 0; }}
"""
