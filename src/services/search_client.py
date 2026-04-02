"""Web検索・学術検索クライアント

Google Custom Search API は新規取得不可のため、
DuckDuckGo Search (duckduckgo-search) をメインのWeb検索として使用。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

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


class DuckDuckGoSearchClient:
    """duckduckgo-search ライブラリによるWeb検索（メイン検索エンジン）

    APIキー不要。Google Custom Search の代替。
    """

    def search(self, query: str, max_results: int = 10, region: str = "jp-jp") -> list[SearchResult]:
        """DuckDuckGoでWeb検索"""
        try:
            from ddgs import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, region=region, max_results=max_results):
                    url_str = r.get("href", "")
                    results.append(
                        SearchResult(
                            title=r.get("title", ""),
                            url=url_str,
                            snippet=r.get("body", ""),
                            source_type=_classify_source(url_str),
                        )
                    )

            logger.info("DuckDuckGo検索: '%s' → %d件", query[:40], len(results))
            return results

        except ImportError:
            logger.error("ddgs がインストールされていません: pip install ddgs")
            return []
        except Exception as e:
            logger.error("DuckDuckGo検索エラー: %s", e)
            # レート制限時はリトライ
            if "ratelimit" in str(e).lower():
                logger.info("レート制限検出。5秒後にリトライ...")
                time.sleep(5)
                try:
                    from ddgs import DDGS
                    results = []
                    with DDGS() as ddgs:
                        for r in ddgs.text(query, region=region, max_results=max_results):
                            url_str = r.get("href", "")
                            results.append(
                                SearchResult(
                                    title=r.get("title", ""),
                                    url=url_str,
                                    snippet=r.get("body", ""),
                                    source_type=_classify_source(url_str),
                                )
                            )
                    return results
                except Exception:
                    pass
            return []


class DuckDuckGoInstantClient:
    """DuckDuckGo Instant Answer API（補助用）"""

    def search(self, query: str) -> list[SearchResult]:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            if data.get("Abstract"):
                results.append(
                    SearchResult(
                        title=data.get("Heading", query),
                        url=data.get("AbstractURL", ""),
                        snippet=data["Abstract"],
                        source_type=_classify_source(data.get("AbstractURL", "")),
                    )
                )
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
            logger.error("DuckDuckGo Instant Answer エラー: %s", e)
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
