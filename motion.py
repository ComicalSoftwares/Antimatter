from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QVariantAnimation
from PyQt6.QtWidgets import QGraphicsOpacityEffect

import settings

MAX_WIDTH = 16777215


def enabled():
    return bool(settings.get("animations"))


def curve(kind="out", overshoot=1.7):
    if kind == "back":
        easing = QEasingCurve(QEasingCurve.Type.OutBack)
        easing.setOvershoot(overshoot)
        return easing
    if kind == "in":
        return QEasingCurve(QEasingCurve.Type.InCubic)
    if kind == "inout":
        return QEasingCurve(QEasingCurve.Type.InOutCubic)
    return QEasingCurve(QEasingCurve.Type.OutQuint)


def fade_in(widget, duration=150):
    if not enabled():
        return
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
    anim.setEasingCurve(curve("out"))
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    widget._fade_anim = anim
    anim.start()


def fade_window(window, duration=120):
    if not enabled():
        return
    previous = getattr(window, "_fade_anim", None)
    if previous is not None:
        previous.stop()
    window.setWindowOpacity(0.0)
    anim = QPropertyAnimation(window, b"windowOpacity", window)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(curve("out"))
    window._fade_anim = anim
    anim.start()


def pop_in(window, duration=340, dy=18, overshoot=2.2):
    if not enabled():
        return
    previous = getattr(window, "_pop_anim", None)
    if previous is not None:
        previous.stop()
    end = window.pos()
    window.move(end.x(), end.y() - dy)
    anim = QPropertyAnimation(window, b"pos", window)
    anim.setDuration(duration)
    anim.setStartValue(window.pos())
    anim.setEndValue(end)
    anim.setEasingCurve(curve("back", overshoot))
    window._pop_anim = anim
    anim.start()
    fade_window(window, int(duration * 0.55))


def animate_dock(dock, show, width, on_done=None):
    previous = getattr(dock, "_dock_anim", None)
    if previous is not None:
        previous.stop()

    def release():
        dock.setMinimumWidth(0)
        dock.setMaximumWidth(MAX_WIDTH)
        if not show:
            dock.hide()
        if on_done:
            on_done()

    if not enabled():
        dock.setVisible(show)
        release()
        return

    start = dock.width() if dock.isVisible() else 0
    end = width if show else 0
    if show:
        dock.setMinimumWidth(start)
        dock.setMaximumWidth(max(start, 1))
        dock.show()

    anim = QVariantAnimation(dock)
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.setDuration(420 if show else 240)
    anim.setEasingCurve(curve("back", 1.1) if show else curve("inout"))

    def step(value):
        w = max(0, int(value))
        dock.setMinimumWidth(w)
        dock.setMaximumWidth(w)

    anim.valueChanged.connect(step)
    anim.finished.connect(release)
    dock._dock_anim = anim
    anim.start()
