"""Phase 2: リサーチ & ファクトチェック"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.config import get_settings
from src.database import insert_research
from src.services.ai_client import AIClient
from src.services.search_client import (
    DuckDuckGoInstantClient,
    DuckDuckGoSearchClient,
    SearchResult,
    WikipediaClient,
)

logger = logging.getLogger(__name__)


@dataclass
class FactSource:
    source_type: str  # academic / wikipedia / government / web
    url: str
    title: str
    reliability: int


@dataclass
class VerifiedFact:
    statement: str
    sources: list[FactSource]
    total_reliability: int
    verified: bool


@dataclass
class ResearchResult:
    keyword: str
    facts: list[VerifiedFact] = field(default_factory=list)
    excluded_claims: list[dict] = field(default_factory=list)


RESEARCH_PROMPT = """以下のキーワードについて、ショート動画で紹介できる雑学・豆知識を3〜5個リストアップしてください。

キーワード: {keyword}

以下の情報を参考にしてください:
{search_context}

各雑学は以下の条件を満たすこと:
- 事実に基づいていること（出典を明記）
- 多くの人が知らない・驚く内容であること
- 60秒以内のナレーションで伝えられる簡潔さ

JSON配列で回答:
[
  {{
    "statement": "雑学の内容（1〜2文）",
    "confidence": "high/medium/low",
    "category": "科学/歴史/文化/自然/技術/etc"
  }}
]
"""

VERIFY_PROMPT = """以下の「雑学」が事実として正しいかを検証してください。

雑学: {statement}

以下の検索結果を参考に判断してください:
{search_context}

JSON形式で回答:
{{
  "is_accurate": true/false,
  "corrected_statement": "正確な表現（修正が必要な場合）",
  "confidence": "high/medium/low",
  "reason": "判断理由"
}}
"""


def _collect_search_results(keyword: str) -> list[SearchResult]:
    """複数ソースから検索結果を収集"""
    all_results: list[SearchResult] = []

    # Wikipedia検索（日本語 + 英語）
    wiki = WikipediaClient()
    all_results.extend(wiki.search(keyword, lang="ja", limit=3))
    all_results.extend(wiki.search(keyword, lang="en", limit=2))

    # DuckDuckGo Web検索（メイン）
    ddg = DuckDuckGoSearchClient()
    all_results.extend(ddg.search(f"{keyword} 雑学 豆知識", max_results=8))

    # DuckDuckGo Instant Answer（補助）
    if len(all_results) < 5:
        instant = DuckDuckGoInstantClient()
        all_results.extend(instant.search(f"{keyword} trivia facts"))

    return all_results


def _format_search_context(results: list[SearchResult]) -> str:
    """検索結果をプロンプト用テキストに整形"""
    lines = []
    for i, r in enumerate(results[:10], 1):
        lines.append(f"{i}. [{r.source_type}] {r.title}")
        lines.append(f"   URL: {r.url}")
        lines.append(f"   {r.snippet[:200]}")
        lines.append("")
    return "\n".join(lines)


def _calculate_reliability(sources: list[SearchResult]) -> tuple[list[FactSource], int]:
    """ソースの信頼度スコアを計算"""
    settings = get_settings()
    weights = settings.fact_check.source_weights

    weight_map = {
        "academic": weights.academic,
        "wikipedia": weights.wikipedia,
        "government": weights.government,
        "web": weights.web,
    }

    fact_sources = []
    total = 0
    for s in sources:
        reliability = weight_map.get(s.source_type, weights.web)
        fact_sources.append(
            FactSource(
                source_type=s.source_type,
                url=s.url,
                title=s.title,
                reliability=reliability,
            )
        )
        total += reliability

    return fact_sources, total


def _verify_fact(
    statement: str, keyword: str, ai_client: AIClient
) -> tuple[bool, str, list[SearchResult]]:
    """個別の雑学を検索で検証"""
    # 検証用検索（DuckDuckGo + Wikipedia）
    ddg = DuckDuckGoSearchClient()
    verify_results = ddg.search(f"{keyword} {statement[:30]}", max_results=5)

    wiki = WikipediaClient()
    verify_results.extend(wiki.search(f"{keyword} {statement[:20]}", lang="ja", limit=2))

    search_context = _format_search_context(verify_results)

    try:
        result = ai_client.generate_json(
            VERIFY_PROMPT.format(statement=statement, search_context=search_context)
        )
        is_accurate = result.get("is_accurate", False)
        corrected = result.get("corrected_statement", statement)
        return is_accurate, corrected, verify_results
    except Exception as e:
        logger.error("ファクト検証エラー: %s", e)
        return False, statement, verify_results


def research_keyword(keyword: str, keyword_id: int, ai_client: AIClient) -> ResearchResult:
    """キーワードに対するリサーチ & ファクトチェックを実行"""
    logger.info("リサーチ開始: %s", keyword)
    settings = get_settings()
    result = ResearchResult(keyword=keyword)

    # 1. 検索結果収集
    search_results = _collect_search_results(keyword)
    search_context = _format_search_context(search_results)

    # 2. AIで雑学候補を生成
    try:
        trivia_candidates = ai_client.generate_json(
            RESEARCH_PROMPT.format(keyword=keyword, search_context=search_context)
        )
    except Exception as e:
        logger.error("雑学候補生成エラー: %s", e)
        return result

    # 3. 各候補をファクトチェック
    for candidate in trivia_candidates:
        statement = candidate.get("statement", "")
        if not statement:
            continue

        is_accurate, corrected, verify_sources = _verify_fact(statement, keyword, ai_client)

        fact_source_list, total_reliability = _calculate_reliability(verify_sources)

        if (
            is_accurate
            and len(verify_sources) >= settings.fact_check.min_sources
            and total_reliability >= settings.fact_check.min_reliability_score
        ):
            result.facts.append(
                VerifiedFact(
                    statement=corrected,
                    sources=fact_source_list,
                    total_reliability=total_reliability,
                    verified=True,
                )
            )
        else:
            reasons = []
            if not is_accurate:
                reasons.append("正確性に疑問")
            if len(verify_sources) < settings.fact_check.min_sources:
                reasons.append(f"ソース数不足({len(verify_sources)}件)")
            if total_reliability < settings.fact_check.min_reliability_score:
                reasons.append(f"信頼度スコア不足({total_reliability})")
            result.excluded_claims.append(
                {"statement": statement, "reason": "、".join(reasons)}
            )

    # 4. DB保存
    if result.facts:
        facts_data = [
            {
                "statement": f.statement,
                "sources": [
                    {"type": s.source_type, "url": s.url, "title": s.title, "reliability": s.reliability}
                    for s in f.sources
                ],
                "total_reliability": f.total_reliability,
                "verified": f.verified,
            }
            for f in result.facts
        ]
        max_reliability = max(f.total_reliability for f in result.facts)
        insert_research(keyword_id, facts_data, max_reliability)

    logger.info(
        "リサーチ完了: %s → 検証済み %d件, 除外 %d件",
        keyword,
        len(result.facts),
        len(result.excluded_claims),
    )
    return result
