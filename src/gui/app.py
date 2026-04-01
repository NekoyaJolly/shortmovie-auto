"""PyQt6 メインウィンドウ"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QWidget,
)

from src.database import get_all_videos
from src.gui.preview_panel import PreviewPanel
from src.gui.styles import DARK_THEME
from src.gui.video_list import VideoListWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Trivia Shorts Factory - Review Dashboard")
        self.setMinimumSize(1100, 700)
        self._setup_ui()
        self._update_status_bar()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左: 動画リスト
        self.video_list = VideoListWidget()
        self.video_list.setMinimumWidth(280)
        splitter.addWidget(self.video_list)

        # 右: プレビュー・編集パネル
        self.preview_panel = PreviewPanel()
        splitter.addWidget(self.preview_panel)

        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

        # シグナル接続
        self.video_list.video_selected.connect(self.preview_panel.load_video)
        self.preview_panel.video_updated.connect(self._on_video_updated)

        # ステータスバー
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _on_video_updated(self) -> None:
        """動画ステータス変更時"""
        self.video_list.refresh()
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        videos = get_all_videos()
        total = len(videos)
        status_counts: dict[str, int] = {}
        for v in videos:
            s = v.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        approved = status_counts.get("approved", 0)
        pending = status_counts.get("pending_review", 0)
        rejected = status_counts.get("rejected", 0)
        published = status_counts.get("published", 0)

        self.status_bar.showMessage(
            f"合計: {total} | レビュー待ち: {pending} | 承認済み: {approved} | "
            f"却下: {rejected} | 公開済み: {published}"
        )


def run_gui() -> None:
    """GUIアプリケーションを起動"""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
