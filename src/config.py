"""設定ファイル読み込み & バリデーション"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# .env読み込み
load_dotenv(PROJECT_ROOT / ".env", override=True)


# --- Pydantic設定モデル ---


class AppConfig(BaseModel):
    name: str = "Trivia Shorts Factory"
    output_dir: str = "./output"
    assets_dir: str = "./assets"
    db_path: str = "./data/trivia_shorts.db"
    max_videos_per_day: int = 10


class TTSConfig(BaseModel):
    engine: str = "voicevox"
    voicevox_url: str = "http://localhost:50021"
    speaker_id: int = 1
    speed_scale: float = 1.0


class VideoConfig(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    max_duration_sec: int = 60
    font: str = "NotoSansJP-Bold.ttf"
    font_size: int = 48
    transition: str = "crossfade"
    transition_duration_ms: int = 500


class AIConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096


class TwitterTrendConfig(BaseModel):
    enabled: bool = True
    woeid: int = 23424856


class GoogleTrendsConfig(BaseModel):
    enabled: bool = True
    geo: str = "JP"


class YouTubeTrendConfig(BaseModel):
    enabled: bool = True
    region_code: str = "JP"


class TrendSourcesConfig(BaseModel):
    twitter: TwitterTrendConfig = Field(default_factory=TwitterTrendConfig)
    google_trends: GoogleTrendsConfig = Field(default_factory=GoogleTrendsConfig)
    youtube: YouTubeTrendConfig = Field(default_factory=YouTubeTrendConfig)


class ImageSourceConfig(BaseModel):
    name: str
    api_key_env: str
    priority: int


class YouTubeConfig(BaseModel):
    credentials_path: str = "./credentials/youtube_oauth.json"
    default_privacy: Literal["private", "public", "unlisted"] = "private"
    default_category: str = "27"


class SourceWeights(BaseModel):
    academic: int = 10
    wikipedia: int = 8
    government: int = 8
    web: int = 5


class FactCheckConfig(BaseModel):
    min_sources: int = 3
    min_reliability_score: int = 15
    source_weights: SourceWeights = Field(default_factory=SourceWeights)


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    trend_sources: TrendSourcesConfig = Field(default_factory=TrendSourcesConfig)
    image_sources: list[ImageSourceConfig] = Field(default_factory=list)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    fact_check: FactCheckConfig = Field(default_factory=FactCheckConfig)

    def resolve_path(self, relative_path: str) -> Path:
        """相対パスをプロジェクトルートからの絶対パスに変換"""
        return (PROJECT_ROOT / relative_path).resolve()

    @property
    def db_path(self) -> Path:
        return self.resolve_path(self.app.db_path)

    @property
    def output_dir(self) -> Path:
        return self.resolve_path(self.app.output_dir)

    @property
    def assets_dir(self) -> Path:
        return self.resolve_path(self.app.assets_dir)


def load_settings(config_path: Path | None = None) -> Settings:
    """config.yamlを読み込んでSettingsオブジェクトを返す"""
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "config.yaml"

    if not config_path.exists():
        return Settings()

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return Settings.model_validate(raw)


def get_env(key: str, default: str = "") -> str:
    """環境変数を取得"""
    return os.environ.get(key, default)


# シングルトン的に使えるグローバル設定
_settings: Settings | None = None


def get_settings() -> Settings:
    """グローバル設定を取得（遅延初期化）"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
