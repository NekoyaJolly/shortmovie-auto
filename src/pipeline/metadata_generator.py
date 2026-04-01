"""Phase 6: メタデータ生成"""

from __future__ import annotations

import logging
from datetime import datetime

from src.services.ai_client import AIClient

logger = logging.getLogger(__name__)

METADATA_PROMPT = """以下のショート動画の台本から、YouTube Shorts用のメタデータを生成してください。

台本タイトル: {title}
ナレーション全文:
{narration}

ソース情報: {sources}

以下のルールに従ってJSON形式で回答:
- title: 30文字以内、冒頭に【】で注目ワード、末尾にハッシュタグ1〜2個、クリックベイトは避ける
- description: 動画の概要 + ハッシュタグ5個程度、改行で見やすく
- tags: 関連キーワード6〜10個の配列

{{
  "title": "【注目ワード】タイトル #雑学 #豆知識",
  "description": "説明文\\n\\n#タグ1 #タグ2 ...",
  "tags": ["タグ1", "タグ2", ...],
  "thumbnail_text": "サムネイルに表示する短いテキスト"
}}
"""


def generate_metadata(script: dict, sources: list[str], ai_client: AIClient) -> dict:
    """台本データからYouTube Shorts用メタデータを生成"""
    logger.info("メタデータ生成開始")

    title = script.get("title", "")
    narration = "\n".join(
        s.get("narration", "") for s in script.get("scenes", [])
    )
    sources_text = "\n".join(f"- {s}" for s in sources) if sources else "なし"

    metadata = ai_client.generate_json(
        METADATA_PROMPT.format(
            title=title,
            narration=narration,
            sources=sources_text,
        )
    )

    # メタデータの補完
    metadata["category"] = "Education"
    metadata["language"] = "ja"
    metadata["sources_used"] = sources
    metadata["created_at"] = datetime.now().isoformat()
    metadata["status"] = "pending_review"

    # タイトル文字数チェック
    if len(metadata.get("title", "")) > 30:
        logger.warning("タイトルが30文字を超えています: %s", metadata["title"])

    logger.info("メタデータ生成完了: %s", metadata.get("title", ""))
    return metadata
