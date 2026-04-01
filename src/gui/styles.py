"""QSSスタイル定義"""

DARK_THEME = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Meiryo UI", sans-serif;
    font-size: 13px;
}

QLabel {
    color: #cdd6f4;
}

QListWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    margin: 2px 0;
}

QListWidget::item:selected {
    background-color: #45475a;
}

QListWidget::item:hover {
    background-color: #313244;
}

QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #585b70;
}

QPushButton:pressed {
    background-color: #313244;
}

QPushButton#approveBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
}

QPushButton#approveBtn:hover {
    background-color: #94d89a;
}

QPushButton#rejectBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
}

QPushButton#rejectBtn:hover {
    background-color: #e07a97;
}

QPushButton#regenerateBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
}

QTextEdit, QLineEdit {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 6px;
    color: #cdd6f4;
}

QTextEdit:focus, QLineEdit:focus {
    border-color: #89b4fa;
}

QGroupBox {
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}

QMenuBar {
    background-color: #181825;
    color: #cdd6f4;
}

QMenuBar::item:selected {
    background-color: #45475a;
}

QMenu {
    background-color: #1e1e2e;
    border: 1px solid #313244;
}

QMenu::item:selected {
    background-color: #45475a;
}

QComboBox {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px 8px;
    color: #cdd6f4;
}

QComboBox::drop-down {
    border: none;
}

QScrollBar:vertical {
    background-color: #181825;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
"""
