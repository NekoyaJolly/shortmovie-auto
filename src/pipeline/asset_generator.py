"""Phase 4: アセット生成（TTS音声 + 画像素材）"""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import get_settings
from src.services.image_client import ImageClient
from src.services.tts_client import TTSClient

logger = logging.getLogger(__name__)


def generate_assets(script: dict, video_id: int) -> dict:
    """台本に基づいてTTS音声と画像素材を生成・取得

    Returns:
        更新された台本データ（ファイルパス付き）
    """
    settings = get_settings()
    assets_dir = settings.assets_dir / str(video_id)
    audio_dir = assets_dir / "audio"
    image_dir = assets_dir / "images"
    audio_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    tts = TTSClient()
    image_client = ImageClient()

    # VOICEVOXヘルスチェック
    if not tts.health_check():
        raise RuntimeError("VOICEVOXエンジンが起動していません。先にVOICEVOXを起動してください。")

    scenes = script.get("scenes", [])

    for scene in scenes:
        scene_id = scene["scene_id"]

        # --- TTS音声生成 ---
        narration = scene.get("narration", "")
        if narration:
            audio_path = audio_dir / f"scene_{scene_id}.wav"
            duration = tts.synthesize(narration, audio_path)
            scene["audio_path"] = str(audio_path)
            scene["actual_duration_sec"] = duration
        else:
            scene["audio_path"] = None
            scene["actual_duration_sec"] = scene.get("duration_sec", 5)

        # --- 画像取得 ---
        visual_desc = scene.get("visual_description", "")
        image_path = image_dir / f"scene_{scene_id}.jpg"

        if visual_desc:
            success = image_client.search_and_download(visual_desc, image_path)
            if success:
                scene["image_path"] = str(image_path)
            else:
                scene["image_path"] = None
                logger.warning("シーン %d の画像取得失敗。フォールバック使用。", scene_id)
        else:
            scene["image_path"] = None

    # 合計実測時間を更新
    total_actual = sum(s.get("actual_duration_sec", 0) for s in scenes)
    script["actual_total_duration_sec"] = total_actual

    logger.info("アセット生成完了: video_id=%d, 合計 %.1f秒", video_id, total_actual)
    return script
