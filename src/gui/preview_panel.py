"""プレビュー・編集パネル"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.database import approve_video, reject_video, update_video


class PreviewPanel(QWidget):
    """動画プレビュー・メタデータ編集パネル"""

    video_updated = pyqtSignal()  # 動画ステータスが変わったことを通知

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_video: dict | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # --- プレビューエリア ---
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(320)
        layout.addWidget(self.video_widget)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # 再生コントロール
        controls = QHBoxLayout()
        self.play_btn = QPushButton("再生")
        self.play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self.play_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._stop)
        controls.addWidget(self.stop_btn)

        controls.addStretch()
        layout.addLayout(controls)

        # --- メタデータ編集 ---
        meta_group = QGroupBox("メタデータ")
        meta_layout = QVBoxLayout(meta_group)

        meta_layout.addWidget(QLabel("タイトル:"))
        self.title_edit = QLineEdit()
        meta_layout.addWidget(self.title_edit)

        meta_layout.addWidget(QLabel("説明文:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        meta_layout.addWidget(self.desc_edit)

        meta_layout.addWidget(QLabel("タグ:"))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("カンマ区切りで入力")
        meta_layout.addWidget(self.tags_edit)

        layout.addWidget(meta_group)

        # --- 信頼度・ソース ---
        info_group = QGroupBox("情報")
        info_layout = QVBoxLayout(info_group)
        self.score_label = QLabel("信頼度スコア: -")
        info_layout.addWidget(self.score_label)
        self.status_label = QLabel("ステータス: -")
        info_layout.addWidget(self.status_label)
        layout.addWidget(info_group)

        # --- アクションボタン ---
        btn_layout = QHBoxLayout()

        self.approve_btn = QPushButton("承認")
        self.approve_btn.setObjectName("approveBtn")
        self.approve_btn.clicked.connect(self._approve)
        btn_layout.addWidget(self.approve_btn)

        self.reject_btn = QPushButton("却下")
        self.reject_btn.setObjectName("rejectBtn")
        self.reject_btn.clicked.connect(self._reject)
        btn_layout.addWidget(self.reject_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self._save_metadata)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def load_video(self, video: dict) -> None:
        """動画データをパネルに読み込み"""
        self.current_video = video

        # プレビュー
        video_path = video.get("video_path")
        if video_path and Path(video_path).exists():
            self.player.setSource(QUrl.fromLocalFile(str(Path(video_path).resolve())))

        # メタデータ
        meta = video.get("metadata_json", {}) or {}
        self.title_edit.setText(meta.get("title", ""))
        self.desc_edit.setPlainText(meta.get("description", ""))
        tags = meta.get("tags", [])
        self.tags_edit.setText(", ".join(tags) if isinstance(tags, list) else "")

        # 情報
        self.score_label.setText(f"信頼度スコア: {meta.get('fact_check_score', '-')}")
        self.status_label.setText(f"ステータス: {video.get('status', '-')}")

    def _toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("再生")
        else:
            self.player.play()
            self.play_btn.setText("一時停止")

    def _stop(self) -> None:
        self.player.stop()
        self.play_btn.setText("再生")

    def _save_metadata(self) -> None:
        if not self.current_video:
            return

        meta = self.current_video.get("metadata_json", {}) or {}
        meta["title"] = self.title_edit.text()
        meta["description"] = self.desc_edit.toPlainText()
        meta["tags"] = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]

        update_video(self.current_video["id"], metadata_json=meta)
        QMessageBox.information(self, "保存", "メタデータを保存しました。")

    def _approve(self) -> None:
        if not self.current_video:
            return
        self._save_metadata()
        approve_video(self.current_video["id"])
        self.video_updated.emit()

    def _reject(self) -> None:
        if not self.current_video:
            return
        reject_video(self.current_video["id"], "GUI から却下")
        self.video_updated.emit()
