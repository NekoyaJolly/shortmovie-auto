"""Phase 1: トレンド収集 & キーワード提案"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pytrends.request import TrendReq

from src.config import get_settings
from src.database import insert_keyword
from src.services.ai_client import AIClient

logger = logging.getLogger(__name__)


@dataclass
class KeywordCandidate:
    keyword: str
    source: str
    trivia_score: int
    reason: str


def collect_google_trends() -> list[str]:
    """Google Trendsから日本のトレンドキーワードを取得"""
    settings = get_settings()
    if not settings.trend_sources.google_trends.enabled:
        return []

    try:
        pytrends = TrendReq(hl="ja-JP")
        # 日本の日次トレンド
        df = pytrends.trending_searches(pn="japan")
        keywords = df[0].tolist()
        logger.info("Google Trends: %d件のトレンド取得", len(keywords))
        return keywords
    except Exception as e:
        logger.error("Google Trends エラー: %s", e)
        return []


def collect_twitter_trends() -> list[str]:
    """Twitter/Xからトレンドキーワードを取得"""
    settings = get_settings()
    if not settings.trend_sources.twitter.enabled:
        return []

    try:
        from src.services.twitter_client import TwitterClient

        client = TwitterClient()
        return client.get_trends()
    except ValueError:
        logger.warning("Twitter API キーが未設定のためスキップ")
        return []
    except Exception as e:
        logger.error("Twitter トレンド取得エラー: %s", e)
        return []


def collect_youtube_trends() -> list[str]:
    """YouTubeトレンドからキーワードを取得"""
    settings = get_settings()
    if not settings.trend_sources.youtube.enabled:
        return []

    try:
        from src.services.youtube_client import YouTubeTrendClient

        client = YouTubeTrendClient()
        return client.get_trending_keywords()
    except ValueError:
        logger.warning("YouTube API キーが未設定のためスキップ")
        return []
    except Exception as e:
        logger.error("YouTube トレンド取得エラー: %s", e)
        return []


def merge_keywords(sources: dict[str, list[str]]) -> list[dict[str, str]]:
    """各ソースのキーワードをマージ・正規化・重複除去"""
    seen: set[str] = set()
    merged: list[dict[str, str]] = []

    for source_name, keywords in sources.items():
        for kw in keywords:
            normalized = kw.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                merged.append({"keyword": normalized, "source": source_name})

    return merged


FILTER_PROMPT = """以下のキーワードリストについて、雑学ショート動画のトピックとして適切かを判定してください。

判定基準:
- 事実ベースの雑学が存在するか
- 意見が分かれるトピックではないか
- 政治・宗教・論争的テーマではないか
- 多くの人が「へぇ」と思える内容か
- 60秒以内で伝えられる内容か

各キーワードに対して以下のJSON配列で回答してください:
[
  {{
    "keyword": "キーワード",
    "trivia_score": 1-10の整数,
    "reason": "判定理由（1文）",
    "suitable": true/false
  }}
]

キーワードリスト:
{keywords}
"""


def filter_keywords_with_ai(
    keywords: list[dict[str, str]], ai_client: AIClient
) -> list[KeywordCandidate]:
    """AIで雑学適性を判定"""
    if not keywords:
        return []

    # 50件ずつバッチ処理
    batch_size = 50
    all_candidates: list[KeywordCandidate] = []

    for i in range(0, len(keywords), batch_size):
        batch = keywords[i : i + batch_size]
        kw_list = "\n".join(f"- {item['keyword']}" for item in batch)

        try:
            result = ai_client.generate_json(FILTER_PROMPT.format(keywords=kw_list))

            # ソース情報をマッピング
            source_map = {item["keyword"]: item["source"] for item in batch}

            for item in result:
                if item.get("suitable", False):
                    source = source_map.get(item["keyword"], "unknown")
                    all_candidates.append(
                        KeywordCandidate(
                            keyword=item["keyword"],
                            source=source,
                            trivia_score=item.get("trivia_score", 5),
                            reason=item.get("reason", ""),
                        )
                    )
        except Exception as e:
            logger.error("AIフィルタリングエラー (バッチ %d): %s", i // batch_size, e)

    # スコア降順ソート
    all_candidates.sort(key=lambda c: c.trivia_score, reverse=True)
    return all_candidates


def run_trend_collection(max_candidates: int = 20) -> list[KeywordCandidate]:
    """Phase 1のメイン処理: トレンド収集 → AIフィルタリング → DB保存"""
    logger.info("=== Phase 1: トレンド収集開始 ===")

    # 各ソースからキーワード収集
    sources = {
        "google_trends": collect_google_trends(),
        "twitter": collect_twitter_trends(),
        "youtube": collect_youtube_trends(),
    }

    total = sum(len(v) for v in sources.values())
    logger.info("合計 %d 件のキーワードを収集", total)

    # マージ・重複除去
    merged = merge_keywords(sources)
    logger.info("重複除去後: %d 件", len(merged))

    # AIフィルタリング
    ai_client = AIClient()
    candidates = filter_keywords_with_ai(merged, ai_client)
    logger.info("AIフィルタリング後: %d 件（適性あり）", len(candidates))

    # 上位をDB保存
    top_candidates = candidates[:max_candidates]
    for c in top_candidates:
        insert_keyword(c.keyword, c.source, c.trivia_score)

    logger.info("=== Phase 1 完了: %d 件のキーワード候補を保存 ===", len(top_candidates))
    return top_candidates
