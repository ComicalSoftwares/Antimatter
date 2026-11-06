FONT = "'Consolas', 'Cantarell'"


def main_qss(c):
    return f"""
        QMainWindow {{ background-color: {c['window']}; }}
        QDockWidget {{ color: {c['text']}; font-family: {FONT}; font-size: 12px; }}
        QDockWidget::title {{
            background: {c['surface']};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding-left: 8px;
            padding-top: 4px;
            padding-bottom: 4px;
            border-bottom: 1px solid {c['sidebar']};
        }}
        QTreeView {{
            background-color: {c['sidebar']};
            color: {c['text']};
            border: none;
            font-family: {FONT};
            font-size: 12px;
        }}
        QTreeView::item {{ border-radius: 6px; }}
        QTreeView::item:hover {{ background-color: {c['surface']}; border-radius: 6px; }}
        QTreeView::item:selected {{ background-color: {c['select']}; color: {c['select_text']}; border-radius: 6px; }}
        QScrollBar:vertical {{ background: {c['bg']}; width: 10px; margin: 0px; border: none; border-radius: 5px; }}
        QScrollBar:horizontal {{ background: {c['bg']}; height: 10px; margin: 0px; border: none; border-radius: 5px; }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background: {c['handle']};
            border-radius: 5px;
            min-height: 20px;
            min-width: 20px;
            border: none;
        }}
        QScrollBar::handle:hover {{ background: {c['handle_hover']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
            border: none;
            width: 0px;
            height: 0px;
        }}
    """


def menubar_qss(c):
    return f"""
        QMenuBar {{ background-color: {c['window']}; color: {c['text']}; }}
        QMenuBar::item {{ border-radius: 6px; padding: 4px 8px; background: transparent; }}
        QMenuBar::item:selected {{ background-color: {c['accent']}; color: #ffffff; }}
    """


def statusbar_qss(c):
    return f"""
        QStatusBar {{ background: {c['window']}; color: {c['muted']}; font-family: {FONT}; font-size: 12px; }}
        QStatusBar::item {{ border: none; }}
        QLabel {{ background: {c['surface']}; color: {c['text']}; border-radius: 8px; padding: 2px 10px; margin: 2px 3px; }}
    """


def tabs_qss(c):
    return f"""
        QTabWidget::pane {{ border: none; background: {c['bg']}; }}
        QTabBar {{ background: {c['window']}; }}
        QTabBar::tab {{
            background: {c['window']};
            color: {c['muted']};
            padding: 7px 12px;
            font-family: {FONT};
            font-size: 13px;
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            margin-right: 2px;
        }}
        QTabBar::tab:hover {{ background: {c['surface']}; color: {c['text']}; }}
        QTabBar::tab:selected {{ background: {c['bg']}; color: {c['text']}; }}
        QTabBar::close-button {{ image: none; subcontrol-position: right; width: 14px; height: 14px; }}
    """


def close_button_qss(c):
    return f"""
        QPushButton {{
            background: transparent;
            color: {c['text']};
            border: none;
            font-weight: bold;
            font-size: 13px;
            margin-left: 0px;
            border-radius: 10px;
        }}
        QPushButton:hover {{ color: {c['danger']}; background: {c['surface']}; }}
    """


def menu_qss(c):
    return f"""
        QMenu {{
            background-color: {c['popup']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 4px;
        }}
        QMenu::item {{ padding: 5px 24px 5px 14px; margin: 1px 2px; border-radius: 6px; }}
        QMenu::item:selected {{ background-color: {c['select']}; color: {c['select_text']}; }}
        QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 8px; }}
    """


def pick_qss(c):
    return f"""
        QFrame#pick {{ background-color: {c['popup']}; border: 1px solid {c['border']}; border-radius: 14px; }}
        QLineEdit {{
            background-color: {c['input']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 8px 12px;
            font-family: {FONT};
            font-size: 14px;
        }}
        QLineEdit:focus {{ border: 1px solid {c['accent']}; }}
        QListWidget {{ background: transparent; border: none; outline: none; font-family: {FONT}; font-size: 13px; }}
    """


def dialog_qss(c):
    return f"""
        QDialog {{ background-color: {c['sidebar']}; }}
        QLabel {{ color: {c['text']}; font-family: {FONT}; font-size: 13px; background: transparent; }}
        QLabel#heading {{ font-size: 12px; font-weight: bold; color: {c['accent_hover']}; padding-top: 6px; }}
        QLabel#hint {{ color: {c['muted']}; font-size: 12px; }}
        QFrame#card {{ background-color: {c['bg']}; border: 1px solid {c['border']}; border-radius: 14px; }}
        QFrame#divider {{ background-color: {c['border']}; max-height: 1px; border: none; }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}
        QLineEdit {{
            background-color: {c['input']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 6px 10px;
            font-family: {FONT};
            font-size: 13px;
        }}
        QLineEdit:focus {{ border: 1px solid {c['accent']}; }}
        QListWidget {{
            background-color: {c['bg']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 12px;
            padding: 4px;
            font-family: {FONT};
            font-size: 13px;
            outline: none;
        }}
        QListWidget::item {{ padding: 8px 10px; border-radius: 8px; }}
        QListWidget::item:hover {{ background-color: {c['surface']}; }}
        QListWidget::item:selected {{ background-color: {c['select']}; color: {c['select_text']}; }}
        QTextBrowser {{
            background-color: {c['bg']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 12px;
            padding: 8px;
            font-family: {FONT};
            font-size: 13px;
        }}
        QComboBox, QSpinBox, QFontComboBox {{
            background-color: {c['input']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 5px 10px;
            min-height: 20px;
            font-family: {FONT};
            font-size: 13px;
        }}
        QComboBox:hover, QSpinBox:hover, QFontComboBox:hover {{ border: 1px solid {c['handle']}; }}
        QComboBox:focus, QSpinBox:focus, QFontComboBox:focus {{ border: 1px solid {c['accent']}; }}
        QComboBox::drop-down, QFontComboBox::drop-down {{ border: none; width: 22px; }}
        QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; border: none; }}
        QComboBox QAbstractItemView, QFontComboBox QAbstractItemView {{
            background-color: {c['popup']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 10px;
            padding: 4px;
            outline: none;
            selection-background-color: {c['select']};
            selection-color: {c['select_text']};
        }}
        QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0px; border: none; border-radius: 5px; }}
        QScrollBar::handle:vertical {{ background: {c['handle']}; border-radius: 5px; min-height: 20px; }}
        QScrollBar::handle:vertical:hover {{ background: {c['handle_hover']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; border: none; height: 0px; }}
    """
