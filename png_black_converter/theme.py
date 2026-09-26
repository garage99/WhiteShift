"""Application theme (light / dark) for WhiteShift.

The theme is applied once at the QApplication level so individual widgets
carry no stylesheets of their own. It follows the OS colour scheme and
switches live when the user toggles light/dark mode.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPalette, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

ACCENT = "#ff5a4e"

LIGHT = {
    "window": "#f4f5f8",
    "card": "#ffffff",
    "border": "#e3e6ec",
    "divider": "#eceef2",
    "control": "#ffffff",
    "control_border": "#d7dbe3",
    "hover": "#f1f3f7",
    "text": "#1d2330",
    "muted": "#6b7280",
    "faint": "#9aa1ad",
    "disabled_text": "#b4b9c4",
    "disabled_bg": "#f6f7f9",
    "accent": ACCENT,
    "accent_hover": "#f24a3e",
    "accent_disabled": "#ffc9c4",
    "accent_text": "#ffffff",
    "selection": "#ffe3e0",
    "danger": "#d64545",
}

DARK = {
    "window": "#16181d",
    "card": "#1f2229",
    "border": "#2e323b",
    "divider": "#2a2e36",
    "control": "#272b33",
    "control_border": "#3a3f4a",
    "hover": "#2f343e",
    "text": "#e8eaef",
    "muted": "#9aa1ad",
    "faint": "#6f7682",
    "disabled_text": "#5c626d",
    "disabled_bg": "#22252c",
    "accent": ACCENT,
    "accent_hover": "#ff6f64",
    "accent_disabled": "#5a2e2b",
    "accent_text": "#ffffff",
    "selection": "#4a2623",
    "danger": "#ff7a7a",
}


def is_dark() -> bool:
    hints = QGuiApplication.styleHints()
    return hints.colorScheme() == Qt.ColorScheme.Dark


def _arrow_files(color: str, check_color: str = "#ffffff") -> dict[str, str]:
    """Draw small arrow icons for spin boxes / combo boxes.

    Qt stylesheets need image files for arrows once the control is styled,
    so they are rendered at runtime into a temp folder. This keeps the
    PyInstaller builds free of extra data files.
    """
    folder = Path(gettempdir()) / "whiteshift-theme"
    folder.mkdir(parents=True, exist_ok=True)
    shapes = {
        "up": [(2, 7), (6, 3), (10, 7)],
        "down": [(2, 4), (6, 8), (10, 4)],
        "check": [(2.5, 6.2), (5, 8.6), (9.5, 3.4)],
    }
    paths: dict[str, str] = {}
    for name, points in shapes.items():
        tint = check_color if name == "check" else color
        target = folder / f"{name}-{tint.lstrip('#')}.png"
        if not target.is_file():
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = painter.pen()
            pen.setColor(QColor(check_color if name == "check" else color))
            pen.setWidthF(3.2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(QPolygonF([QPointF(x * 2, y * 2) for x, y in points]))
            painter.end()
            pixmap.save(str(target))
        paths[name] = target.as_posix()
    return paths


def stylesheet(c: dict[str, str]) -> str:
    arrows = _arrow_files(c["muted"])
    return f"""
QMainWindow, QDialog, QMessageBox, QWidget#appRoot {{ background: {c['window']}; color: {c['text']}; }}
QWidget {{ color: {c['text']}; }}
QStatusBar {{ background: {c['window']}; color: {c['muted']}; }}
QStatusBar::item {{ border: none; }}
QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 4px 6px; border-radius: 6px; }}

QFrame#settingsPanel, QFrame#previewCard {{
    background: {c['card']}; border: 1px solid {c['border']}; border-radius: 14px;
}}
QFrame#previewCard QScrollArea, QFrame#previewCard QScrollArea > QWidget > QWidget {{
    border: none; background: transparent;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel#previewTitle {{ font-weight: bold; }}
QLabel#sectionTitle {{ font-weight: bold; }}
QLabel#valueBadge {{ font-weight: bold; }}
QLabel#noteLabel {{ color: {c['muted']}; }}
QLabel#hintLabel {{ color: {c['faint']}; }}
QLabel#countBadge {{
    background: {c['hover']}; color: {c['muted']}; border-radius: 9px;
    padding: 1px 8px; font-size: 11px; font-weight: bold;
}}
QLabel#profileLabel {{ color: {c['muted']}; font-size: 11px; }}

QFrame#toolbarCard {{
    background: {c['card']}; border: 1px solid {c['border']}; border-radius: 12px;
}}
QFrame#divider {{ background: {c['divider']}; border: none; max-height: 1px; min-height: 1px; }}

QListWidget {{
    background: {c['window']}; border: 1px dashed {c['control_border']}; border-radius: 10px;
    padding: 5px; outline: none;
}}
QListWidget::item {{ min-height: 30px; padding: 3px 8px; border-radius: 6px; color: {c['text']}; }}
QListWidget::item:hover {{ background: {c['hover']}; }}
QListWidget::item:selected {{ background: {c['selection']}; color: {c['text']}; font-weight: bold; }}

QGraphicsView {{ border: 1px solid {c['divider']}; border-radius: 10px; }}
QSplitter::handle {{ background: transparent; width: 10px; }}

QGroupBox {{
    border: none; border-top: 1px solid {c['divider']};
    margin-top: 16px; padding-top: 8px; font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 0px; padding: 0px;
    color: {c['faint']}; font-size: 11px;
}}

QPushButton {{
    border-radius: 8px; padding: 6px 14px; min-height: 18px;
    border: 1px solid {c['control_border']}; background: {c['control']}; color: {c['text']};
}}
QPushButton:hover {{ background: {c['hover']}; }}
QPushButton:pressed {{ background: {c['divider']}; }}
QPushButton:disabled {{ color: {c['disabled_text']}; background: {c['disabled_bg']}; border-color: {c['divider']}; }}
QPushButton#primaryButton {{
    background: {c['accent']}; border: 1px solid {c['accent']}; color: {c['accent_text']}; font-weight: bold;
    min-height: 26px;
}}
QPushButton#primaryButton:hover {{ background: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QPushButton#primaryButton:disabled {{
    background: {c['accent_disabled']}; border-color: {c['accent_disabled']}; color: {c['accent_text']};
}}
QPushButton#secondaryButton {{ font-weight: bold; }}
QPushButton#resetButton {{ color: {c['danger']}; }}
QPushButton#resetButton:disabled {{ color: {c['disabled_text']}; }}
QPushButton#modeButton {{
    border: 1px solid transparent; background: transparent;
    padding: 7px 18px; color: {c['muted']}; font-weight: bold;
}}
QPushButton#modeButton:hover {{ color: {c['text']}; }}
QPushButton#modeButton:checked {{ background: {c['card']}; color: {c['text']}; border-color: {c['border']}; }}

QComboBox, QAbstractSpinBox {{
    border: 1px solid {c['control_border']}; border-radius: 7px;
    padding: 4px 8px; background: {c['control']}; min-height: 20px;
    selection-background-color: {c['selection']}; selection-color: {c['text']};
}}
QComboBox:hover, QAbstractSpinBox:hover {{ border-color: {c['faint']}; }}
QComboBox:focus, QAbstractSpinBox:focus {{ border-color: {c['accent']}; }}
QComboBox:disabled, QAbstractSpinBox:disabled {{ color: {c['disabled_text']}; background: {c['disabled_bg']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url("{arrows['down']}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {c['card']}; border: 1px solid {c['border']}; border-radius: 8px;
    selection-background-color: {c['selection']}; selection-color: {c['text']}; outline: none; padding: 4px;
}}
QAbstractSpinBox {{ padding-right: 22px; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    subcontrol-origin: border; width: 20px; border: none; background: transparent;
}}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; margin-top: 2px; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; margin-bottom: 2px; }}
QAbstractSpinBox::up-arrow {{ image: url("{arrows['up']}"); width: 10px; height: 10px; }}
QAbstractSpinBox::down-arrow {{ image: url("{arrows['down']}"); width: 10px; height: 10px; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {c['hover']}; border-radius: 4px; }}

QSlider::groove:horizontal {{ height: 4px; background: {c['border']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {c['card']}; border: 1px solid {c['control_border']};
    width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ border-color: {c['accent']}; }}

QCheckBox, QRadioButton {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {c['control_border']}; background: {c['control']};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:checked {{
    background: {c['accent']}; border-color: {c['accent']}; image: url("{arrows['check']}");
}}
QRadioButton::indicator:checked {{ background: {c['card']}; border: 5px solid {c['accent']}; width: 8px; height: 8px; }}

QProgressBar {{
    border: none; background: {c['border']}; border-radius: 3px;
    max-height: 6px; min-height: 6px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {c['control_border']}; border-radius: 3px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {c['faint']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def _palette(c: dict[str, str]) -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.Window: c["window"],
        QPalette.WindowText: c["text"],
        QPalette.Base: c["control"],
        QPalette.AlternateBase: c["hover"],
        QPalette.Text: c["text"],
        QPalette.Button: c["control"],
        QPalette.ButtonText: c["text"],
        QPalette.ToolTipBase: c["card"],
        QPalette.ToolTipText: c["text"],
        QPalette.Highlight: c["accent"],
        QPalette.HighlightedText: c["accent_text"],
        QPalette.PlaceholderText: c["faint"],
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, QColor(c["disabled_text"]))
    return palette


def apply_theme(app: QApplication, dark: bool | None = None) -> None:
    """Apply the theme now and keep it in sync with the OS colour scheme.

    ``dark`` forces light (False) or dark (True); None follows the OS.
    """
    app.setStyle("Fusion")
    app._whiteshift_theme_forced = dark

    def refresh(*_args) -> None:
        forced = getattr(app, "_whiteshift_theme_forced", None)
        colors = DARK if (is_dark() if forced is None else forced) else LIGHT
        app.setPalette(_palette(colors))
        app.setStyleSheet(stylesheet(colors))

    refresh()
    if not getattr(app, "_whiteshift_theme_connected", False):
        QGuiApplication.styleHints().colorSchemeChanged.connect(refresh)
        app._whiteshift_theme_connected = True
