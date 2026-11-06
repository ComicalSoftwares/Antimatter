from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMenu

import skin
import themes
from motion import fade_in, fade_window


def round_menu(menu):
    menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setProperty("amx_round", True)
    menu.setStyleSheet(skin.menu_qss(themes.chrome()))
    menu.aboutToShow.connect(lambda: fade_window(menu, 120))
    return menu


def apply_chrome():
    qss = skin.menu_qss(themes.chrome())
    for widget in QApplication.allWidgets():
        if isinstance(widget, QMenu) and widget.property("amx_round"):
            widget.setStyleSheet(qss)
