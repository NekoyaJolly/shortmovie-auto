"""画像検索API統合（Unsplash / Pexels / Pixabay）"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from src.config import get_env, get_settings

logger = logging.getLogger(__name__)


class ImageClient:
    """複数画像APIを優先順位でフォールバック検索"""

    def __init__(self) -> None:
        settings = get_settings()
        self.sources = sorted(settings.image_sources, key=lambda s: s.priority)

    def search_and_download(self, query: str, output_path: Path, orientation: str = "portrait") -> bool:
        """キーワードで画像を検索・ダウンロード。成功したらTrue"""
        for source in self.sources:
            api_key = get_env(source.api_key_env)
            if not api_key:
                continue

            try:
                if source.name == "unsplash":
                    url = self._search_unsplash(query, api_key, orientation)
                elif source.name == "pexels":
                    url = self._search_pexels(query, api_key, orientation)
                elif source.name == "pixabay":
                    url = self._search_pixabay(query, api_key, orientation)
                else:
                    continue

                if url:
                    return self._download(url, output_path)
            except Exception as e:
                logger.warning("%s 検索エラー: %s", source.name, e)
                continue

        logger.warning("画像が見つかりませんでした: %s", query)
        return False

    def _search_unsplash(self, query: str, api_key: str, orientation: str) -> str | None:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "orientation": orientation, "per_page": 1},
            headers={"Authorization": f"Client-ID {api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            return results[0]["urls"]["regular"]
        return None

    def _search_pexels(self, query: str, api_key: str, orientation: str) -> str | None:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "orientation": orientation, "per_page": 1},
            headers={"Authorization": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large2x"]
        return None

    def _search_pixabay(self, query: str, api_key: str, orientation: str) -> str | None:
        pixabay_orientation = "vertical" if orientation == "portrait" else "horizontal"
        resp = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key,
                "q": query,
                "orientation": pixabay_orientation,
                "per_page": 3,
                "image_type": "photo",
            },
            timeout=15,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        if hits:
            return hits[0]["largeImageURL"]
        return None

    def _download(self, url: str, output_path: Path) -> bool:
        """画像をダウンロード"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("画像ダウンロード: %s", output_path.name)
        return True
