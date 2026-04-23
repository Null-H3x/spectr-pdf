"""
Spectr PDF — SPECTR Qt Stylesheet
Applies the SPECTR cyberpunk palette to the entire Qt application.
Import and call apply(app) after creating QApplication.
"""

PALETTE = {
    "bg":          "#0A0E1A",
    "surface":     "#111827",
    "surface_alt": "#1A2235",
    "border":      "#1F2D40",
    "border_hi":   "#2A3F58",
    "cyan":        "#00F0FF",
    "cyan_dim":    "#007A84",
    "violet":      "#7B2FFF",
    "violet_dim":  "#3D1880",
    "pink":        "#FF2D6B",
    "green":       "#00FF88",
    "amber":       "#FFB800",
    "text_hi":     "#E2E8F0",
    "text_mid":    "#8899AA",
    "text_lo":     "#445566",
    "scrollbar":   "#1F2D40",
}

QSS = """
/* ── Global ─────────────────────────────────────────────────── */
QWidget {{
    background-color: {bg};
    color: {text_hi};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
    selection-background-color: {violet_dim};
    selection-color: {text_hi};
    border: none;
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {bg};
}}

/* ── Menu bar ────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {surface};
    color: {text_hi};
    padding: 2px;
    border-bottom: 1px solid {border};
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{
    background-color: {surface_alt};
    color: {cyan};
}}
QMenu {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {surface_alt};
    color: {cyan};
}}
QMenu::separator {{
    height: 1px;
    background-color: {border};
    margin: 4px 8px;
}}

/* ── Toolbar ─────────────────────────────────────────────────── */
QToolBar {{
    background-color: {surface};
    border-bottom: 1px solid {border};
    spacing: 2px;
    padding: 3px 6px;
}}
QToolBar::separator {{
    width: 1px;
    background-color: {border};
    margin: 4px 6px;
}}
QToolButton {{
    background-color: transparent;
    color: {text_mid};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
}}
QToolButton:hover {{
    background-color: {surface_alt};
    color: {cyan};
    border-color: {border};
}}
QToolButton:pressed, QToolButton:checked {{
    background-color: {border};
    color: {cyan};
    border-color: {border_hi};
}}

/* ── Sidebar / dock ──────────────────────────────────────────── */
QDockWidget {{
    color: {text_hi};
    font-weight: 500;
    titlebar-close-icon: url(none);
    titlebar-normal-icon: url(none);
}}
QDockWidget::title {{
    background-color: {surface};
    padding: 6px 10px;
    border-bottom: 1px solid {border};
    font-size: 11px;
    font-weight: 600;
    color: {text_mid};
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

/* ── Tab widget ──────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {border};
    border-top: none;
    background-color: {surface};
}}
QTabBar::tab {{
    background-color: {bg};
    color: {text_mid};
    padding: 7px 18px;
    border: 1px solid {border};
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background-color: {surface};
    color: {cyan};
    border-bottom: 2px solid {cyan};
}}
QTabBar::tab:hover:!selected {{
    background-color: {surface_alt};
    color: {text_hi};
}}

/* ── Scroll bars ─────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {bg};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background-color: {border};
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {border_hi};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background-color: {bg};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {border};
    min-width: 20px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {border_hi};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Push button ─────────────────────────────────────────────── */
QPushButton {{
    background-color: {cyan};
    color: {bg};
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: #22F7FF;
}}
QPushButton:pressed {{
    background-color: {cyan_dim};
}}
QPushButton:disabled {{
    background-color: {border};
    color: {text_lo};
}}
QPushButton[flat="true"] {{
    background-color: transparent;
    color: {text_mid};
    border: 1px solid {border};
}}
QPushButton[flat="true"]:hover {{
    background-color: {surface_alt};
    color: {cyan};
    border-color: {cyan_dim};
}}
QPushButton[danger="true"] {{
    background-color: {pink};
    color: white;
}}
QPushButton[danger="true"]:hover {{
    background-color: #FF5580;
}}

/* ── Line edit / text input ──────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {surface_alt};
    color: {text_hi};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {violet_dim};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {cyan};
}}

/* ── Combo box ───────────────────────────────────────────────── */
QComboBox {{
    background-color: {surface_alt};
    color: {text_hi};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
}}
QComboBox:focus {{
    border-color: {cyan};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {surface};
    border: 1px solid {border};
    selection-background-color: {surface_alt};
    selection-color: {cyan};
}}

/* ── Spin box ────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {surface_alt};
    color: {text_hi};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 8px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {cyan};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {border};
    border-radius: 2px;
    width: 16px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {border_hi};
}}

/* ── Slider ──────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background-color: {border};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background-color: {cyan};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background-color: {cyan_dim};
    border-radius: 2px;
}}

/* ── List / tree views ───────────────────────────────────────── */
QListWidget, QListView, QTreeWidget, QTreeView {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 6px;
    alternate-background-color: {surface_alt};
    show-decoration-selected: 1;
}}
QListWidget::item, QListView::item,
QTreeWidget::item, QTreeView::item {{
    padding: 4px 8px;
    border-radius: 3px;
}}
QListWidget::item:selected, QListView::item:selected,
QTreeWidget::item:selected, QTreeView::item:selected {{
    background-color: {surface_alt};
    color: {cyan};
}}
QListWidget::item:hover, QListView::item:hover,
QTreeWidget::item:hover, QTreeView::item:hover {{
    background-color: {surface_alt};
}}
QTreeView::branch {{
    background-color: transparent;
}}

/* ── Group box ───────────────────────────────────────────────── */
QGroupBox {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    margin-top: 16px;
    padding: 12px;
    font-size: 11px;
    font-weight: 600;
    color: {text_mid};
    letter-spacing: 0.5px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {text_mid};
    left: 12px;
    top: -8px;
}}

/* ── Check / radio ───────────────────────────────────────────── */
QCheckBox, QRadioButton {{
    color: {text_hi};
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border_hi};
    border-radius: 3px;
    background-color: {surface_alt};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {cyan};
    border-color: {cyan};
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}

/* ── Progress bar ────────────────────────────────────────────── */
QProgressBar {{
    background-color: {border};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    font-size: 11px;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {cyan};
    border-radius: 4px;
}}

/* ── Status bar ──────────────────────────────────────────────── */
QStatusBar {{
    background-color: {surface};
    color: {text_mid};
    border-top: 1px solid {border};
    font-size: 11px;
    padding: 0 8px;
}}
QStatusBar::item {{
    border: none;
}}

/* ── Splitter ────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {border};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── Tool tip ────────────────────────────────────────────────── */
QToolTip {{
    background-color: {surface};
    color: {text_hi};
    border: 1px solid {border};
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
}}

/* ── Message box ─────────────────────────────────────────────── */
QMessageBox {{
    background-color: {surface};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ── Label ───────────────────────────────────────────────────── */
QLabel {{
    color: {text_hi};
    background-color: transparent;
}}
QLabel[muted="true"] {{
    color: {text_mid};
    font-size: 11px;
}}
QLabel[heading="true"] {{
    font-size: 14px;
    font-weight: 600;
    color: {cyan};
}}

/* ── Separator ───────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    border: none;
    background-color: {border};
    max-height: 1px;
    min-height: 1px;
}}
"""


def stylesheet() -> str:
    """Return the fully resolved QSS string."""
    return QSS.format(**PALETTE)


def apply(app) -> None:
    """Apply the SPECTR theme to a QApplication instance."""
    app.setStyleSheet(stylesheet())
    # Set application-wide font
    from PyQt6.QtGui import QFont
    font = QFont("Segoe UI", 10)
    app.setFont(font)
