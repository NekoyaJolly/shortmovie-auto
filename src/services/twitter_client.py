"""Twitter/X API v2 ラッパー - トレンド取得"""

from __future__ import annotations

import logging
import time

import requests

from src.config import get_env, get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class TwitterClient:
    def __init__(self) -> None:
        self.bearer_token = get_env("TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN が設定されていません")
        settings = get_settings()
        self.woeid = settings.trend_sources.twitter.woeid
        self.base_url = "https://api.twitter.com/2"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def get_trends(self) -> list[str]:
        """日本のトレンドキーワードを取得"""
        # Twitter API v2ではトレンドエンドポイントが限定的
        # v1.1のtrends/placeを使用
        url = f"https://api.twitter.com/1.1/trends/place.json?id={self.woeid}"

        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(url, headers=self._headers(), timeout=30)
                if resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    logger.warning("Twitter API レート制限。%d秒待機...", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                trends = data[0].get("trends", [])
                keywords = [t["name"].lstrip("#") for t in trends if t.get("name")]
                logger.info("Twitter: %d件のトレンド取得", len(keywords))
                return keywords
            except requests.RequestException as e:
                logger.error("Twitter API エラー (試行 %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** (attempt + 1))

        logger.warning("Twitter トレンド取得失敗")
        return []
