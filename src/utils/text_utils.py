"""テキスト処理ユーティリティ"""

from __future__ import annotations

import re


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """テキストをファイル名に安全な文字列に変換"""
    # ファイル名に使えない文字を除去
    sanitized = re.sub(r'[\\/:*?"<>|\n\r]', "", text)
    sanitized = sanitized.strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized or "untitled"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """テキストを指定長で切り詰め"""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def count_narration_duration_estimate(text: str, chars_per_second: float = 5.0) -> float:
    """ナレーションテキストの推定読み上げ時間（秒）"""
    char_count = len(text.replace(" ", "").replace("\n", ""))
    return char_count / chars_per_second
