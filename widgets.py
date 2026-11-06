from PyQt6.QtCore import QRectF, QSize, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QAbstractButton, QPushButton

import motion
import themes


def _tween(widget, start, end, duration, kind, setter, overshoot=1.7):
    previous = getattr(widget, "_tween_" + kind + setter.__name__, None)
    if previous is not None:
        previous.stop()
    if not motion.enabled():
        setter(end)
        return
    anim = QVariantAnimation(widget)
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.setDuration(duration)
    anim.setEasingCurve(motion.curve(kind, overshoot))
    anim.valueChanged.connect(setter)
    setattr(widget, "_tween_" + kind + setter.__name__, anim)
    anim.start()


class AnimatedButton(QPushButton):
    def __init__(self, text, primary=False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self._hover = 0.0
        self._scale = 1.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def _set_hover(self, value):
        self._hover = value
        self.update()

    def _set_scale(self, value):
        self._scale = value
        self.update()

    def sizeHint(self):
        return QSize(self.fontMetrics().horizontalAdvance(self.text()) + 32, 34)

    def enterEvent(self, event):
        _tween(self, self._hover, 1.0, 160, "out", self._set_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        _tween(self, self._hover, 0.0, 220, "out", self._set_hover)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        _tween(self, self._scale, 0.93, 90, "out", self._set_scale)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        _tween(self, self._scale, 1.0, 420, "back", self._set_scale, 4.0)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        c = themes.chrome()
        if not self.isEnabled():
            base = hover = c["surface"]
            text = c["muted"]
        elif self.primary:
            base, hover, text = c["accent"], c["accent_hover"], "#ffffff"
        else:
            base, hover, text = c["select"], c["handle"], c["text"]
        color = QColor(themes.mix(base, hover, self._hover))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self._scale, self._scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 10, 10)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(c["accent_hover"]), 1.5))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 9, 9)
        painter.setPen(QColor(text))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(52, 30)
        self.setChecked(checked)
        self._t = 1.0 if checked else 0.0
        self._glow = 0.0
        self.toggled.connect(self._animate)

    def _set_t(self, value):
        self._t = value
        self.update()

    def _animate(self, state):
        _tween(self, self._t, 1.0 if state else 0.0, 460, "back", self._set_t, 2.4)

    def mousePressEvent(self, event):
        _tween(self, self._glow, 1.0, 100, "out", self._set_glow)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        _tween(self, self._glow, 0.0, 260, "out", self._set_glow)
        super().mouseReleaseEvent(event)

    def _set_glow(self, value):
        self._glow = value
        self.update()

    def setCheckedInstant(self, state):
        self.blockSignals(True)
        self.setChecked(state)
        self.blockSignals(False)
        self._t = 1.0 if state else 0.0
        self.update()

    def paintEvent(self, event):
        c = themes.chrome()
        t = max(0.0, min(1.0, self._t))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QRectF(5, 5, 42, 20)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(themes.mix(c["handle"], c["accent"], t)))
        painter.drawRoundedRect(track, 10, 10)
        grow = 2.0 * self._glow
        radius = 7.0 + grow
        x = 15 + 22 * self._t
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(x - radius, 15 - radius, radius * 2, radius * 2))
