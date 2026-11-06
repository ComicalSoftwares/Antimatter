import shutil
from pathlib import Path
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFontComboBox, QFrame, QHBoxLayout, QLabel,
    QScrollArea, QSpinBox, QVBoxLayout, QWidget
)

import motion
import settings
import skin
import themes
from widgets import AnimatedButton, ToggleSwitch

FONTS_DIR = Path.home() / ".antimatter" / "fonts"
SAMPLE = 'def greet(name):\n    return f"Hello, {name}!"'


class PreferencesDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Preferences")
        self.resize(660, 760)
        self.setStyleSheet(skin.dialog_qss(themes.chrome()))
        self._popped = False
        self._building = True

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Preferences")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll, 1)
        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(0, 0, 8, 0)
        self.body.setSpacing(6)
        scroll.setWidget(body)

        self._section("Appearance")
        card = self._card()
        self.theme_box = QComboBox()
        self.theme_box.addItems(themes.names())
        self.theme_box.setCurrentText(themes.current_name())
        self.theme_box.currentTextChanged.connect(self._theme_changed)
        self._row(card, "Color theme", "Colors for the editor, sidebar, tabs and menus", self.theme_box)
        self.animations = ToggleSwitch(settings.get("animations"))
        self.animations.toggled.connect(lambda v: self._set("animations", v))
        self._row(card, "Animations", "Smooth transitions, fades and springy motion", self.animations, last=True)

        self._section("Font")
        card = self._card()
        self.font_box = QFontComboBox()
        self.font_box.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        self.font_box.setCurrentFont(QFont(settings.get("font_family")))
        self.font_box.currentFontChanged.connect(lambda f: self._set("font_family", f.family()))
        self._row(card, "Font family", "Monospaced fonts installed on this computer", self.font_box)
        self.all_fonts = ToggleSwitch(False)
        self.all_fonts.toggled.connect(self._toggle_all_fonts)
        self._row(card, "Show all fonts", "Include proportional fonts in the list", self.all_fonts)
        self.size_box = QSpinBox()
        self.size_box.setRange(6, 48)
        self.size_box.setValue(settings.get("font_size"))
        self.size_box.valueChanged.connect(lambda v: self._set("font_size", v))
        self._row(card, "Font size", "Also changes with Ctrl + mouse wheel in the editor", self.size_box)
        self.custom_label = QLabel()
        self.custom_label.setObjectName("hint")
        self.custom_label.setWordWrap(True)
        add_font = AnimatedButton("Add Custom Font...")
        add_font.clicked.connect(self._add_font)
        self._row(card, "Custom fonts", "Load a .ttf, .otf or .ttc file", add_font, extra=self.custom_label, last=True)
        self._refresh_custom_label()

        self.preview = QLabel(SAMPLE)
        self.preview.setContentsMargins(16, 14, 16, 14)
        self.body.addWidget(self.preview)
        self._update_preview()

        self._section("Editor")
        card = self._card()
        self.tab_box = QComboBox()
        self.tab_box.addItems(["2", "4", "8"])
        self.tab_box.setCurrentText(str(settings.get("tab_size")))
        self.tab_box.currentTextChanged.connect(lambda v: self._set("tab_size", int(v)))
        self._row(card, "Tab size", "Spaces inserted by the Tab key", self.tab_box)
        self.wrap = ToggleSwitch(settings.get("word_wrap"))
        self.wrap.toggled.connect(lambda v: self._set("word_wrap", v))
        self._row(card, "Word wrap", "Wrap long lines instead of scrolling sideways", self.wrap)
        self.line_hl = ToggleSwitch(settings.get("highlight_current_line"))
        self.line_hl.toggled.connect(lambda v: self._set("highlight_current_line", v))
        self._row(card, "Highlight current line", "Subtle background behind the cursor line", self.line_hl)
        self.smooth = ToggleSwitch(settings.get("smooth_scrolling"))
        self.smooth.toggled.connect(lambda v: self._set("smooth_scrolling", v))
        self._row(card, "Smooth scrolling", "Eased mouse wheel scrolling", self.smooth, last=True)

        self._section("Layout")
        card = self._card()
        self.side_box = QComboBox()
        self.side_box.addItems(["Left", "Right"])
        self.side_box.setCurrentText(settings.get("sidebar_position").capitalize())
        self.side_box.currentTextChanged.connect(lambda v: self._set("sidebar_position", v.lower()))
        self._row(card, "Sidebar position", "Where the File Manager sits. Dragging it also saves its position", self.side_box)
        self.side_visible = ToggleSwitch(settings.get("sidebar_visible"))
        self.side_visible.toggled.connect(lambda v: self._set("sidebar_visible", v))
        self._row(card, "Show sidebar", "Toggle the File Manager (Ctrl+B)", self.side_visible, last=True)

        self.body.addStretch()

        footer = QHBoxLayout()
        reset = AnimatedButton("Reset to Defaults")
        reset.clicked.connect(self._reset)
        raw = AnimatedButton("Open settings.json")
        raw.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(settings.SETTINGS_FILE))))
        done = AnimatedButton("Done", primary=True)
        done.clicked.connect(self.accept)
        footer.addWidget(reset)
        footer.addWidget(raw)
        footer.addStretch()
        footer.addWidget(done)
        root.addLayout(footer)

        settings.observe(self._external_change)
        self.finished.connect(lambda: settings.unobserve(self._external_change))
        self._building = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._popped:
            self._popped = True
            motion.pop_in(self, 420, 24, 2.3)

    def _section(self, name):
        label = QLabel(name.upper())
        label.setObjectName("heading")
        self.body.addWidget(label)

    def _card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(0)
        self.body.addWidget(card)
        return layout

    def _row(self, card, title, hint, control, extra=None, last=False):
        row = QWidget()
        outer = QVBoxLayout(row)
        outer.setContentsMargins(0, 10, 0, 10)
        outer.setSpacing(6)
        line = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(title)
        note = QLabel(hint)
        note.setObjectName("hint")
        note.setWordWrap(True)
        text.addWidget(name)
        text.addWidget(note)
        line.addLayout(text, 1)
        control.setMinimumWidth(control.minimumWidth())
        line.addWidget(control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(line)
        if extra is not None:
            outer.addWidget(extra)
        card.addWidget(row)
        if not last:
            divider = QFrame()
            divider.setObjectName("divider")
            divider.setFixedHeight(1)
            card.addWidget(divider)

    def _set(self, key, value):
        if self._building:
            return
        settings.set(key, value)

    def _theme_changed(self, name):
        if self._building or not name:
            return
        self.window._set_theme({"title": name})
        self.setStyleSheet(skin.dialog_qss(themes.chrome()))
        self._update_preview()

    def _toggle_all_fonts(self, state):
        filt = QFontComboBox.FontFilter.AllFonts if state else QFontComboBox.FontFilter.MonospacedFonts
        current = settings.get("font_family")
        self._building = True
        self.font_box.setFontFilters(filt)
        self.font_box.setCurrentFont(QFont(current))
        self._building = False

    def _add_font(self):
        path, _ = QFileDialog.getOpenFileName(self, "Add custom font", "", "Fonts (*.ttf *.otf *.ttc);;All files (*)")
        if not path:
            return
        FONTS_DIR.mkdir(parents=True, exist_ok=True)
        target = FONTS_DIR / Path(path).name
        if Path(path).resolve() != target.resolve():
            shutil.copy2(path, target)
        families = self.window.register_font_file(str(target))
        if not families:
            self.custom_label.setText("That file could not be loaded as a font.")
            return
        files = list(settings.get("font_files"))
        if str(target) not in files:
            files.append(str(target))
            settings.set("font_files", files)
        self.all_fonts.setChecked(True)
        self._building = True
        self.font_box.setCurrentFont(QFont(families[0]))
        self._building = False
        settings.set("font_family", families[0])
        self._refresh_custom_label()

    def _refresh_custom_label(self):
        names = [Path(f).name for f in settings.get("font_files")]
        self.custom_label.setText("Loaded: " + ", ".join(names) if names else "No custom fonts added yet.")

    def _update_preview(self):
        c = themes.chrome()
        font = QFont()
        font.setFamilies([settings.get("font_family"), "Consolas", "monospace"])
        font.setPointSize(settings.get("font_size"))
        self.preview.setFont(font)
        self.preview.setStyleSheet(
            f"background-color: {c['bg']}; color: {c['fg']}; border: 1px solid {c['border']}; border-radius: 14px;"
        )

    def _external_change(self, key, value):
        if key in ("font_family", "font_size", "theme") or key is None:
            self._update_preview()
        if key is None:
            self._building = True
            self.theme_box.setCurrentText(themes.current_name())
            self.animations.setCheckedInstant(settings.get("animations"))
            self.size_box.setValue(settings.get("font_size"))
            self.font_box.setCurrentFont(QFont(settings.get("font_family")))
            self.tab_box.setCurrentText(str(settings.get("tab_size")))
            self.wrap.setCheckedInstant(settings.get("word_wrap"))
            self.line_hl.setCheckedInstant(settings.get("highlight_current_line"))
            self.smooth.setCheckedInstant(settings.get("smooth_scrolling"))
            self.side_box.setCurrentText(settings.get("sidebar_position").capitalize())
            self.side_visible.setCheckedInstant(settings.get("sidebar_visible"))
            self._building = False
        elif key == "sidebar_position":
            self.side_box.blockSignals(True)
            self.side_box.setCurrentText(str(value).capitalize())
            self.side_box.blockSignals(False)
        elif key == "sidebar_visible":
            self.side_visible.setCheckedInstant(bool(value))
        elif key == "font_size":
            self.size_box.blockSignals(True)
            self.size_box.setValue(int(value))
            self.size_box.blockSignals(False)

    def _reset(self):
        settings.reset()
        themes.set_current(settings.get("theme"), persist=False)
        self.window.apply_theme()
        self.setStyleSheet(skin.dialog_qss(themes.chrome()))
