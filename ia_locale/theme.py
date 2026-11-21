"""Thème sombre de l'application."""

QSS = """
* {
    font-family: "Noto Sans", "DejaVu Sans", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #e6e6eb;
}
QMainWindow, QDialog {
    background: #17181d;
}
QWidget#barre_laterale {
    background: #1e1f26;
    border-right: 1px solid #2e2f38;
}
QLabel#titre_app {
    font-size: 17px;
    font-weight: 700;
    color: #a99df5;
    padding: 10px 12px 4px 12px;
}
QLabel#etat_modele {
    color: #9a9ba6;
    padding: 6px 12px;
    font-size: 12px;
}
QPushButton {
    background: #26272f;
    border: 1px solid #34353f;
    border-radius: 8px;
    padding: 8px 12px;
    text-align: left;
}
QPushButton:hover { background: #2f3039; border-color: #4a4b58; }
QPushButton:pressed { background: #383943; }
QPushButton:disabled { color: #6d6e78; background: #202129; }
QPushButton#bouton_nav {
    text-align: left;
    font-size: 14px;
    padding: 10px 14px;
}
QPushButton#bouton_nav:checked {
    background: #342f56;
    border-color: #7c6cf0;
    color: #cfc6ff;
}
QPushButton#bouton_principal {
    background: #5b4bd4;
    border-color: #7c6cf0;
    color: #ffffff;
    font-weight: 600;
    text-align: center;
}
QPushButton#bouton_principal:hover { background: #6a5ae0; }
QPushButton#bouton_secondaire { text-align: center; }
QFrame#page {
    background: #17181d;
}
QLabel#titre_page {
    font-size: 18px;
    font-weight: 700;
    color: #e8e8ee;
    padding: 4px 2px;
}
QLabel#sous_titre {
    color: #9a9ba6;
    font-size: 12px;
}
QGroupBox {
    background: #1e1f26;
    border: 1px solid #2e2f38;
    border-radius: 10px;
    margin-top: 14px;
    padding: 12px;
    font-weight: 600;
    color: #cfc6ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 2px 8px;
    color: #a99df5;
}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #121319;
    border: 1px solid #34353f;
    border-radius: 7px;
    padding: 6px 8px;
    color: #e6e6eb;
    selection-background-color: #5b4bd4;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #7c6cf0;
}
QComboBox QAbstractItemView {
    background: #26272f;
    border: 1px solid #34353f;
    selection-background-color: #5b4bd4;
}
QListWidget, QTreeWidget {
    background: #121319;
    border: 1px solid #34353f;
    border-radius: 8px;
    outline: none;
}
QTreeWidget::item, QListWidget::item {
    padding: 7px 8px;
    border-radius: 6px;
}
QTreeWidget::item:selected, QListWidget::item:selected {
    background: #342f56;
    color: #e6e6eb;
}
QTreeWidget::item:hover, QListWidget::item:hover { background: #26272f; }
QHeaderView::section {
    background: #1e1f26;
    color: #a99df5;
    border: none;
    border-bottom: 1px solid #2e2f38;
    padding: 6px 8px;
    font-weight: 600;
}
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #1e1f26;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #3a3b47;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #4a4b58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSlider::groove:horizontal {
    height: 6px;
    background: #2e2f38;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #7c6cf0;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #5b4bd4; border-radius: 3px; }
QProgressBar {
    background: #121319;
    border: 1px solid #34353f;
    border-radius: 7px;
    text-align: center;
    height: 16px;
}
QProgressBar::chunk { background: #5b4bd4; border-radius: 6px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #4a4b58;
    border-radius: 4px;
    background: #121319;
}
QCheckBox::indicator:checked { background: #5b4bd4; border-color: #7c6cf0; }
QFrame#bandeau {
    background: #1e1f26;
    border: 1px solid #2e2f38;
    border-radius: 10px;
}
QLabel#etat_vide_titre {
    font-size: 16px;
    font-weight: 700;
    color: #cfc6ff;
}
QLabel#etat_vide_detail {
    color: #9a9ba6;
    font-size: 13px;
}
QFrame#bulle_utilisateur {
    background: #2c2a4a;
    border: 1px solid #4a4390;
    border-radius: 12px;
}
QFrame#bulle_assistant {
    background: #22232b;
    border: 1px solid #34353f;
    border-radius: 12px;
}
QLabel#bulle_texte { color: #ececf2; background: transparent; border: none; padding: 2px; }
QLabel#bulle_role {
    color: #8f90a0;
    font-size: 11px;
    font-weight: 700;
    background: transparent;
    border: none;
    padding: 2px;
}
QLabel#avertissement {
    color: #f0c36d;
    background: #2b2620;
    border: 1px solid #4d4132;
    border-radius: 8px;
    padding: 8px 10px;
}
QLabel#info {
    color: #7fd0a8;
    background: #1d2a24;
    border: 1px solid #2f4a3d;
    border-radius: 8px;
    padding: 8px 10px;
}
QTextBrowser {
    background: #121319;
    border: 1px solid #34353f;
    border-radius: 8px;
    color: #c9c9d4;
    padding: 6px;
}
QSplitter::handle { background: #2e2f38; }
QSplitter::handle:horizontal { width: 1px; }
QToolTip {
    background: #26272f;
    color: #e6e6eb;
    border: 1px solid #4a4b58;
    padding: 6px;
}
"""


def appliquer_theme(app) -> None:
    app.setStyleSheet(QSS)
