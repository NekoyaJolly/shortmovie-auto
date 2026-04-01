"""Web検索・学術検索クライアント"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from src.config import get_env

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source_type: str  # academic / wikipedia / government / web


class WikipediaClient:
    """Wikipedia API検索（日本語 + 英語）"""

    def search(self, keyword: str, lang: str = "ja", limit: int = 5) -> list[SearchResult]:
        """Wikipediaで検索"""
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("query", {}).get("search", []):
                results.append(
                    SearchResult(
                        title=item["title"],
                        url=f"https://{lang}.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                        snippet=item.get("snippet", ""),
                        source_type="wikipedia",
                    )
                )
            return results
        except Exception as e:
            logger.error("Wikipedia検索エラー (%s): %s", lang, e)
            return []

    def get_article_extract(self, title: str, lang: str = "ja") -> str | None:
        """Wikipedia記事の要約を取得"""
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "format": "json",
            "utf8": 1,
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                return page.get("extract")
        except Exception as e:
            logger.error("Wikipedia記事取得エラー: %s", e)
        return None


class GoogleCustomSearchClient:
    """Google Custom Search API"""

    def __init__(self) -> None:
        self.api_key = get_env("GOOGLE_CUSTOM_SEARCH_API_KEY")
        self.cx = get_env("GOOGLE_CUSTOM_SEARCH_CX")

    def search(self, query: str, num: int = 10) -> list[SearchResult]:
        if not self.api_key or not self.cx:
            logger.warning("Google Custom Search API キーが未設定")
            return []

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(num, 10),
            "lr": "lang_ja",
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 429:
                    time.sleep(2 ** (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()

                results = []
                for item in data.get("items", []):
                    url_str = item.get("link", "")
                    source_type = _classify_source(url_str)
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=url_str,
                            snippet=item.get("snippet", ""),
                            source_type=source_type,
                        )
                    )
                return results
            except Exception as e:
                logger.error("Google検索エラー (試行 %d): %s", attempt + 1, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** (attempt + 1))

        return []


class DuckDuckGoClient:
    """DuckDuckGo Instant Answer API（フォールバック）"""

    def search(self, query: str) -> list[SearchResult]:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            # Abstract（メイン結果）
            if data.get("Abstract"):
                results.append(
                    SearchResult(
                        title=data.get("Heading", query),
                        url=data.get("AbstractURL", ""),
                        snippet=data["Abstract"],
                        source_type=_classify_source(data.get("AbstractURL", "")),
                    )
                )
            # Related Topics
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(
                        SearchResult(
                            title=topic.get("Text", "")[:100],
                            url=topic.get("FirstURL", ""),
                            snippet=topic.get("Text", ""),
                            source_type="web",
                        )
                    )
            return results
        except Exception as e:
            logger.error("DuckDuckGo検索エラー: %s", e)
            return []


def _classify_source(url: str) -> str:
    """URLからソースタイプを分類"""
    url_lower = url.lower()
    if any(d in url_lower for d in ["scholar.google", "pubmed", "ncbi", "doi.org", "jstage", "cinii"]):
        return "academic"
    if "wikipedia.org" in url_lower:
        return "wikipedia"
    if any(d in url_lower for d in [".go.jp", ".gov", ".ac.jp", ".edu"]):
        return "government"
    return "web"
