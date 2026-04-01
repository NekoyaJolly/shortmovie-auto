"""動画リストウィジェット"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from src.database import get_all_videos, get_videos_by_status

STATUS_ICONS = {
    "generating": "\u2699",      # ⚙
    "pending_review": "\U0001f4cb",  # 📋
    "approved": "\u2705",        # ✅
    "rejected": "\u274c",        # ❌
    "publishing": "\U0001f4e4",  # 📤
    "published": "\U0001f680",   # 🚀
    "failed": "\u26a0",          # ⚠
}


class VideoListWidget(QWidget):
    """動画リスト表示ウィジェット"""

    video_selected = pyqtSignal(dict)  # 選択された動画データを通知

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # フィルター
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("フィルター:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["すべて", "レビュー待ち", "承認済み", "却下", "生成中", "公開済み", "失敗"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.filter_combo)
        layout.addLayout(filter_layout)

        # リスト
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

        # カウント表示
        self.count_label = QLabel()
        layout.addWidget(self.count_label)

    def refresh(self) -> None:
        """リストをDBから再読み込み"""
        self.list_widget.clear()
        filter_text = self.filter_combo.currentText()

        status_map = {
            "すべて": None,
            "レビュー待ち": "pending_review",
            "承認済み": "approved",
            "却下": "rejected",
            "生成中": "generating",
            "公開済み": "published",
            "失敗": "failed",
        }
        status = status_map.get(filter_text)

        if status:
            videos = get_videos_by_status(status)
        else:
            videos = get_all_videos()

        for video in videos:
            self._add_video_item(video)

        self.count_label.setText(f"{len(videos)} 件")

    def _add_video_item(self, video: dict) -> None:
        """動画アイテムをリストに追加"""
        status = video.get("status", "unknown")
        icon = STATUS_ICONS.get(status, "?")

        meta = video.get("metadata_json", {})
        script = video.get("script_json", {})
        title = "無題"
        if meta and isinstance(meta, dict):
            title = meta.get("title", title)
        elif script and isinstance(script, dict):
            title = script.get("title", title)

        item = QListWidgetItem(f"{icon} {title}")
        item.setData(Qt.ItemDataRole.UserRole, video)
        self.list_widget.addItem(item)

    def _on_item_changed(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current:
            video = current.data(Qt.ItemDataRole.UserRole)
            if video:
                self.video_selected.emit(video)

    def _on_filter_changed(self, _text: str) -> None:
        self.refresh()
