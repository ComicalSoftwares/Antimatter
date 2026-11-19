# Preferences dialog

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QCheckBox,
    QSpinBox, QFontComboBox, QDialogButtonBox
)
import settings
import theme

STYLE = theme.settings


class PreferencesDialog(QDialog):
    def __init__(self, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setStyleSheet(STYLE)
        self.setMinimumWidth(440)
        self.result_settings = dict(current)

        self.font_box = QFontComboBox()
        self.font_box.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)

        self.font_size = QSpinBox()
        self.font_size.setRange(6, 72)

        self.tab_width = QSpinBox()
        self.tab_width.setRange(1, 8)

        self.use_spaces = QCheckBox("Indent with spaces")
        self.word_wrap = QCheckBox("Word wrap")
        self.show_line_numbers = QCheckBox("Show line numbers")
        self.highlight_line = QCheckBox("Highlight current line")
        self.auto_indent = QCheckBox("Keep indentation on Enter")

        self.discord_rpc = QCheckBox("Discord Rich Presence")
        self.lsp_enabled = QCheckBox("Code completions (Python)")

        editor_box = QGroupBox("Editor")
        form = QFormLayout(editor_box)
        form.addRow("Font:", self.font_box)
        form.addRow("Font size:", self.font_size)
        form.addRow("Tab width:", self.tab_width)
        for box in (self.use_spaces, self.word_wrap, self.show_line_numbers,
                    self.highlight_line, self.auto_indent):
            form.addRow(box)

        integ_box = QGroupBox("Integrations")
        integ_layout = QVBoxLayout(integ_box)
        integ_layout.addWidget(self.discord_rpc)
        integ_layout.addWidget(self.lsp_enabled)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            lambda: self.load_values(settings.DEFAULTS))

        root = QVBoxLayout(self)
        root.addWidget(editor_box)
        root.addWidget(integ_box)
        root.addWidget(buttons)

        self.load_values(current)

    def _checkboxes(self):
        return {
            "use_spaces": self.use_spaces,
            "word_wrap": self.word_wrap,
            "show_line_numbers": self.show_line_numbers,
            "highlight_line": self.highlight_line,
            "auto_indent": self.auto_indent,
            "discord_rpc": self.discord_rpc,
            "lsp_enabled": self.lsp_enabled,
        }

    def load_values(self, s):
        self.font_box.setCurrentFont(QFont(s["font_family"]))
        self.font_size.setValue(s["font_size"])
        self.tab_width.setValue(s["tab_width"])
        for key, box in self._checkboxes().items():
            box.setChecked(s[key])

    def accept(self):
        s = dict(self.result_settings)
        s["font_family"] = self.font_box.currentFont().family()
        s["font_size"] = self.font_size.value()
        s["tab_width"] = self.tab_width.value()
        for key, box in self._checkboxes().items():
            s[key] = box.isChecked()
        self.result_settings = s
        super().accept()