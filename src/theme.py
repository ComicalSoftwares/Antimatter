# Contains Antimatter's core QSS style

from PyQt6.QtGui import QFont
from pathlib import Path
ASSETS = (Path(__file__).resolve().parent / "assets").as_posix()

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

tab_bar = """
            QTabWidget::pane {
                border: none;
                background: #19191a;
                border-bottom-left-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QTabBar {
                background: #363636;
            }
            QTabBar::tab {
                background: #363636;
                color: #a6adc8;
                padding: 7px 7px;
                font-family: 'Consolas', 'Cantarell';
                font-size: 13px;
                border: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background: #19191a;
                color: #cdd6f4;
            }
            QTabBar::close-button {
                image: none;
                subcontrol-position: right;
                width: 14px;
                height: 14px;
            }
            QTabBar::tab:selected QTabBar::close-button {
                background: #f38ba8;
                border-radius: 7px;
            }
            QTabBar::tab:hover QTabBar::close-button {
                background: #f38ba8;
                border-radius: 7px;
            }
        """
        
window = """
            QMainWindow {
                background-color: #363636;
            }
            QDockWidget {
                color: #cdd6f4;
                font-family: 'Consolas', 'Cantarell';
                font-size: 12px;
            }
            QDockWidget::title {
                background: #2a2a2e;
                padding-left: 8px;
                padding-top: 4px;
                padding-bottom: 4px;
                border-bottom: 1px solid #1e1e1e;
                border-top-right-radius: 10px;
            }
            QTreeView {
                background-color: #1e1e1e;
                color: #cdd6f4;
                border: none;
                font-family: 'Consolas', 'Cantarell';
                font-size: 12px;
                
            }
            QTreeView::item:hover {
                background-color: #2a2a2e;
            }
            QTreeView::item:selected {
                background-color: #313244;
                color: #ffffff;
            }
            QScrollBar:vertical {
                background: #19191a;
                width: 10px;
                margin: 0px;
                border: none;
                
            }
            QScrollBar:horizontal {
                background: #19191a;
                height: 10px;
                margin: 0px;
                border: none;
                
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #45475a;
                border-radius: 4px;
                min-height: 20px;
                min-width: 20px;
                border: none;
            }
            QScrollBar::handle:hover {
                background: #585b70;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
                border: none;
                width: 0px;
                height: 0px;
                
            }
        """
        
context_menu = """
            QMenu {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                padding: 3px
            }
            QMenu::item:selected {
                background-color: #313244;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #89b4fa;
                margin: 4px 8px;
            }
        """
        
menubar = """
            QMenuBar { background-color: #363636; color: #cdd6f4; }
            QMenuBar::item:selected { background-color: #5400ba; }
            QMenu { background-color: #181825; color: #cdd6f4; border: 1px solid #313244; padding: 3px;}
            QMenu::item:selected { background-color: #313244; }
            QMenu::separator {
                height: 1px;
                background-color: #89b4fa;
                margin: 4px 8px;
            }
        """

close = """
            QPushButton {
                background: transparent;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 13px;
                margin-left: 0px;
            }
            QPushButton:hover {
                color: #d6544b;
            }
        """
        
code = """
            QPlainTextEdit {
                background-color: #19191a;
                color: #D8DEE9;
                border: none;
                border-radius: 15px;
                selection-background-color: #2e3c64;
            }
        """
        
findbar = """
            FindBar {
                background: #19191a;
                border-bottom: 3px solid #313244;
            }
            QLineEdit {
                background: #19191a;
                color: #cdd6f4;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QToolTip {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                padding: 5px;
                font-size: 15px;
            }"""
            
popup = """
            QListWidget { background-color: #181825; color: #cdd6f4; border: 1px solid #313244; }
            QListWidget::item:selected { background-color: #313244; color: #ffffff; }
        """
        
git_tab = """
            QTabWidget::pane { border: 1px solid #313244; background: #19191a; border-radius: 6px; }
            QTabBar::tab { background: #2a2a2e; color: #a6adc8; padding: 6px 14px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #19191a; color: #cdd6f4; border-bottom: 2px solid #89b4fa; }
        """
        
diff_browser = """
            background-color: #141415; color: #cdd6f4;
            font-family: Consolas;
            font-size: 11px; border-radius: 15px;"""

table = """
            QTableWidget {
                background-color: #19191a;
                color: #cdd6f4;
                gridline-color: #313244;
                border: 1px solid #313244;
                border-radius: 6px;
                font-family: Consolas;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2a2a2e;
                color: #cdd6f4;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #313244;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #313244;
                color: white;
            }
        """

issues = """
            QTableWidget {
                background-color: #19191a;
                color: #cdd6f4;
                gridline-color: #313244;
                border: 1px solid #313244;
                border-radius: 6px;
                font-family: Consolas;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2a2a2e;
                color: #cdd6f4;
                padding: 5px;
                border: none;
                border-bottom: 1px solid #313244;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #313244;
                color: white;
            }
        """
        
terminal = """
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monospace';
                font-size: 11pt;
                border-radius: 15px;
            }
        """
        
close_btn = """
        QPushButton {
            background-color: #1f1f1f;
            color: #cdd6f4;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45475a;
        }
    """
    
btn = '''
QPushButton {
    background-color: #242426;
    color: #f2f2f5;
    border: 1px solid #323236;
    padding: 6px 12px;
    border-radius: 15px;
}
QPushButton:hover {
    background-color: #2f2f33;
}
QPushButton:pressed {
    background-color: #1c1c1e;
}
'''
    
settings = """
QDialog { background: #1e1e1e; }
QGroupBox {
    color: #89b4fa; border: 1px solid #313244; border-radius: 6px;
    margin-top: 12px; padding: 10px; font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLabel, QCheckBox { color: #cdd6f4; }

QSpinBox, QFontComboBox, QComboBox {
    background: #19191a; color: #cdd6f4; border: 1px solid #313244;
    border-radius: 4px; padding: 3px 6px; min-height: 22px;
}
QSpinBox:focus, QFontComboBox:focus, QComboBox:focus { border: 1px solid #5400ba; }

QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border; width: 18px; border: none; background: #313244;
}
QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 4px; }
QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 4px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #45475a; }
QSpinBox::up-arrow { image: url(__ASSETS__/chevron-up.svg); width: 10px; height: 6px; }
QSpinBox::down-arrow { image: url(__ASSETS__/chevron-down.svg); width: 10px; height: 6px; }

QComboBox::drop-down, QFontComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 24px; border: none; background: transparent;
}
QComboBox::down-arrow, QFontComboBox::down-arrow {
    image: url(__ASSETS__/chevron-down.svg); width: 10px; height: 6px;
}

QComboBox QAbstractItemView, QFontComboBox QAbstractItemView {
    background: #181825; color: #cdd6f4; border: 1px solid #313244;
    selection-background-color: #313244; selection-color: #ffffff; outline: 0;
}
QComboBox QAbstractItemView::item, QFontComboBox QAbstractItemView::item {
    padding: 5px 8px; min-height: 20px;
}

QPushButton {
    background: #313244; color: #cdd6f4; border: none;
    padding: 6px 14px; border-radius: 4px;
}
QPushButton:hover { background: #45475a; }
""".replace("__ASSETS__", ASSETS)

flat_button_style = """
            QToolButton {
                background-color: transparent;
                color: #cdd6f4;
                border: none;
                outline: none;
                padding: 4px 8px;
                border-radius: 7px;
            }
            QToolButton:hover {
                background-color: #2a2a2e;
                border: none;
            }
            QToolButton:pressed, QToolButton:checked {
                background-color: #5400ba;
                color: #ffffff;
                border: none;
            }
        """