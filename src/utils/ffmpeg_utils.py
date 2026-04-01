"""FFmpegコマンド生成・実行ユーティリティ"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from src.config import get_settings

logger = logging.getLogger(__name__)


def check_ffmpeg() -> bool:
    """FFmpegがインストールされているか確認"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError:
        logger.error("FFmpegが見つかりません。システムにインストールしてください。")
        return False


def concat_audio_files(audio_paths: list[Path], output_path: Path) -> Path:
    """複数のWAVファイルを順番に結合"""
    if len(audio_paths) == 1:
        # 1ファイルならそのままコピー
        import shutil
        shutil.copy2(audio_paths[0], output_path)
        return output_path

    # FFmpegのconcatフィルタ用のリストファイルを作成
    list_file = output_path.parent / "audio_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for ap in audio_paths:
            f.write(f"file '{ap.resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]

    _run_ffmpeg(cmd)
    list_file.unlink(missing_ok=True)
    return output_path


def create_scene_video(
    image_path: Path,
    duration: float,
    output_path: Path,
    fps: int | None = None,
) -> Path:
    """静止画から指定時間の動画クリップを作成"""
    settings = get_settings()
    if fps is None:
        fps = settings.video.fps

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-t", str(duration),
        "-vf", f"scale={settings.video.width}:{settings.video.height}:force_original_aspect_ratio=decrease,pad={settings.video.width}:{settings.video.height}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    _run_ffmpeg(cmd)
    return output_path


def compose_final_video(
    scene_videos: list[Path],
    audio_path: Path,
    output_path: Path,
    transition: str = "crossfade",
    transition_duration_ms: int = 500,
) -> Path:
    """シーン動画と音声を結合して最終動画を生成"""
    settings = get_settings()

    if len(scene_videos) == 1:
        # シーンが1つだけの場合
        cmd = [
            "ffmpeg", "-y",
            "-i", str(scene_videos[0]),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ]
        _run_ffmpeg(cmd)
        return output_path

    # 複数シーンの結合（concatフィルタ使用）
    # まずシーン動画をconcat
    list_file = output_path.parent / "video_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for vp in scene_videos:
            f.write(f"file '{vp.resolve()}'\n")

    concat_video = output_path.parent / "concat_temp.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(concat_video),
    ]
    _run_ffmpeg(cmd)

    # 音声と結合
    cmd = [
        "ffmpeg", "-y",
        "-i", str(concat_video),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    _run_ffmpeg(cmd)

    # 一時ファイル削除
    list_file.unlink(missing_ok=True)
    concat_video.unlink(missing_ok=True)

    return output_path


def get_video_duration(video_path: Path) -> float:
    """動画の再生時間（秒）を取得"""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return float(result.stdout.strip())


def validate_output(video_path: Path) -> dict:
    """出力動画のバリデーション"""
    settings = get_settings()

    if not video_path.exists():
        return {"valid": False, "error": "ファイルが存在しません"}

    try:
        duration = get_video_duration(video_path)
    except Exception as e:
        return {"valid": False, "error": f"再生時間取得エラー: {e}"}

    issues = []
    if duration > settings.video.max_duration_sec:
        issues.append(f"動画が{settings.video.max_duration_sec}秒を超えています ({duration:.1f}秒)")

    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    return {
        "valid": len(issues) == 0,
        "duration_sec": duration,
        "file_size_mb": round(file_size_mb, 2),
        "issues": issues,
    }


def _run_ffmpeg(cmd: list[str]) -> None:
    """FFmpegコマンドを実行"""
    logger.debug("FFmpeg: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        logger.error("FFmpeg エラー: %s", result.stderr[-500:] if result.stderr else "不明")
        raise RuntimeError(f"FFmpeg実行エラー (code={result.returncode})")
