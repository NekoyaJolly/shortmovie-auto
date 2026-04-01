"""Phase 5: 動画合成"""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import get_settings
from src.utils.ffmpeg_utils import (
    check_ffmpeg,
    compose_final_video,
    concat_audio_files,
    create_scene_video,
    validate_output,
)
from src.utils.image_utils import add_text_overlay, create_blank_frame, resize_and_crop
from src.utils.text_utils import sanitize_filename

logger = logging.getLogger(__name__)


def compose_video(script: dict, video_id: int) -> Path:
    """台本データから最終動画を合成

    Args:
        script: アセット生成済みの台本データ（audio_path, image_path付き）
        video_id: 動画ID

    Returns:
        生成された動画ファイルのパス
    """
    if not check_ffmpeg():
        raise RuntimeError("FFmpegがインストールされていません")

    settings = get_settings()
    work_dir = settings.output_dir / str(video_id) / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    scenes = script.get("scenes", [])
    scene_videos: list[Path] = []
    audio_files: list[Path] = []

    for scene in scenes:
        scene_id = scene["scene_id"]
        duration = scene.get("actual_duration_sec", scene.get("duration_sec", 5))

        # 1. 画像の準備（リサイズ + テロップ）
        image_path = scene.get("image_path")
        resized_path = work_dir / f"scene_{scene_id}_resized.png"

        if image_path and Path(image_path).exists():
            resize_and_crop(Path(image_path), resized_path)
        else:
            create_blank_frame(resized_path)

        # テロップ追加
        text_overlay = scene.get("text_overlay", "")
        if text_overlay:
            telop_path = work_dir / f"scene_{scene_id}_telop.png"
            add_text_overlay(resized_path, text_overlay, telop_path)
            final_image = telop_path
        else:
            final_image = resized_path

        # 2. シーン動画作成
        scene_video = work_dir / f"scene_{scene_id}.mp4"
        create_scene_video(final_image, duration, scene_video)
        scene_videos.append(scene_video)

        # 3. 音声ファイル収集
        audio_path = scene.get("audio_path")
        if audio_path and Path(audio_path).exists():
            audio_files.append(Path(audio_path))

    # 4. 音声結合
    combined_audio = work_dir / "combined_audio.wav"
    if audio_files:
        concat_audio_files(audio_files, combined_audio)
    else:
        raise RuntimeError("音声ファイルが1つもありません")

    # 5. 最終動画合成
    title = sanitize_filename(script.get("title", f"video_{video_id}"))
    output_path = settings.output_dir / f"{title}_{video_id}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    compose_final_video(scene_videos, combined_audio, output_path)

    # 6. バリデーション
    validation = validate_output(output_path)
    if not validation["valid"]:
        logger.warning("動画バリデーション警告: %s", validation.get("issues"))
    else:
        logger.info(
            "動画合成完了: %s (%.1f秒, %.1fMB)",
            output_path.name,
            validation["duration_sec"],
            validation["file_size_mb"],
        )

    return output_path
