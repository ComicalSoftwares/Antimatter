from PyQt6.QtCore import Qt, QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import QGraphicsOpacityEffect

MENU_QSS = """
QMenu {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 10px;
    padding: 4px;
}
QMenu::item {
    padding: 5px 24px 5px 14px;
    margin: 1px 2px;
    border-radius: 6px;
}
QMenu::item:selected {
    background-color: #313244;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #313244;
    margin: 4px 8px;
}
"""


def round_menu(menu):
    menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setStyleSheet(MENU_QSS)
    menu.aboutToShow.connect(lambda: fade_window(menu, 110))
    return menu


def fade_in(widget, duration=150):
    previous = getattr(widget, "_fade_anim", None)
    if previous is not None:
        previous.stop()
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._fade_anim = anim
    anim.start()


def fade_window(window, duration=120):
    previous = getattr(window, "_fade_anim", None)
    if previous is not None:
        previous.stop()
    window.setWindowOpacity(0.0)
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    window._fade_anim = anim
    anim.start()
