"""VOICEVOX TTS APIラッパー"""

from __future__ import annotations

import logging
import wave
from pathlib import Path

import requests

from src.config import get_settings

logger = logging.getLogger(__name__)


class TTSClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.tts.voicevox_url
        self.speaker_id = settings.tts.speaker_id
        self.speed_scale = settings.tts.speed_scale

    def health_check(self) -> bool:
        """VOICEVOXエンジンの起動確認"""
        try:
            resp = requests.get(f"{self.base_url}/version", timeout=5)
            resp.raise_for_status()
            logger.info("VOICEVOX エンジン接続OK (version: %s)", resp.text.strip('"'))
            return True
        except Exception as e:
            logger.error("VOICEVOX エンジンに接続できません: %s", e)
            return False

    def synthesize(self, text: str, output_path: Path, speaker_id: int | None = None) -> float:
        """テキストからWAVファイルを生成し、再生時間（秒）を返す"""
        sid = speaker_id or self.speaker_id

        # 1. 音声合成クエリ作成
        query_resp = requests.post(
            f"{self.base_url}/audio_query",
            params={"text": text, "speaker": sid},
            timeout=30,
        )
        query_resp.raise_for_status()
        query = query_resp.json()

        # スピード調整
        query["speedScale"] = self.speed_scale

        # 2. 音声合成実行
        synth_resp = requests.post(
            f"{self.base_url}/synthesis",
            params={"speaker": sid},
            json=query,
            timeout=60,
        )
        synth_resp.raise_for_status()

        # 3. WAVファイル保存
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(synth_resp.content)

        # 4. 再生時間を取得
        duration = _get_wav_duration(output_path)
        logger.info("音声生成: %s (%.1f秒)", output_path.name, duration)
        return duration

    def get_speakers(self) -> list[dict]:
        """利用可能なスピーカー一覧を取得"""
        try:
            resp = requests.get(f"{self.base_url}/speakers", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("スピーカー一覧取得エラー: %s", e)
            return []


def _get_wav_duration(path: Path) -> float:
    """WAVファイルの再生時間（秒）を取得"""
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate
