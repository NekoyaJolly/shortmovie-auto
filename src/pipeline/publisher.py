"""Phase 8: 投稿パイプライン"""

from __future__ import annotations

import logging
from pathlib import Path

from src.database import get_videos_by_status, insert_publish_log, update_video

logger = logging.getLogger(__name__)


def publish_approved_videos() -> list[int]:
    """承認済み動画をYouTube Shortsに投稿

    Returns:
        投稿成功した動画IDのリスト
    """
    approved = get_videos_by_status("approved")
    if not approved:
        logger.info("投稿待ちの動画はありません")
        return []

    published_ids = []
    for video in approved:
        video_id = video["id"]
        video_path = video.get("video_path")
        metadata = video.get("metadata_json", {})

        if not video_path or not Path(video_path).exists():
            logger.error("動画ファイルが見つかりません: video_id=%d", video_id)
            update_video(video_id, status="failed", review_note="動画ファイルが見つかりません")
            continue

        try:
            update_video(video_id, status="publishing")

            # YouTube投稿（T-700/701で実装予定）
            youtube_id, youtube_url = _upload_to_youtube(video_path, metadata)

            update_video(
                video_id,
                status="published",
                youtube_video_id=youtube_id,
                youtube_url=youtube_url,
            )
            insert_publish_log(video_id, "youtube", "success", {"video_id": youtube_id})
            published_ids.append(video_id)
            logger.info("投稿成功: video_id=%d, youtube=%s", video_id, youtube_url)

        except Exception as e:
            logger.error("投稿エラー: video_id=%d, %s", video_id, e)
            update_video(video_id, status="failed", review_note=f"投稿エラー: {e}")
            insert_publish_log(video_id, "youtube", "failed", {"error": str(e)})

    return published_ids


def _upload_to_youtube(video_path: str, metadata: dict) -> tuple[str, str]:
    """YouTube Data API v3で動画をアップロード"""
    from src.services.youtube_client import YouTubeUploader

    uploader = YouTubeUploader()
    return uploader.upload(video_path, metadata)
