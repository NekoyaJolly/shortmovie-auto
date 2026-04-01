"""Phase 3: スクリプト生成（台本作成）"""

from __future__ import annotations

import logging

from src.services.ai_client import AIClient

logger = logging.getLogger(__name__)

SCRIPT_PROMPT = """以下の検証済み雑学データから、60秒以内のショート動画用台本を作成してください。

キーワード: {keyword}

検証済み雑学:
{facts}

台本の構造ルール:
- 最初の3秒で視聴者の興味を引く「フック」を入れる
- ナレーション全体で200〜300文字程度（60秒以内に収まるペース）
- シーンは3〜5個に分割
- 各シーンにvisual_description（画像検索用キーワード）を含める
- 各シーンにtext_overlay（テロップ用テキスト）を含める

JSON形式で回答してください:
{{
  "title": "動画タイトル（短く魅力的に）",
  "total_duration_sec": 推定合計秒数,
  "scenes": [
    {{
      "scene_id": 1,
      "type": "hook",
      "narration": "ナレーションテキスト",
      "duration_sec": 推定秒数,
      "visual_description": "画像検索に使えるキーワード（英語または日本語）",
      "text_overlay": "画面に表示するテロップ"
    }},
    {{
      "scene_id": 2,
      "type": "main",
      "narration": "...",
      "duration_sec": ...,
      "visual_description": "...",
      "text_overlay": "..."
    }},
    ...
    {{
      "scene_id": N,
      "type": "conclusion",
      "narration": "...",
      "duration_sec": ...,
      "visual_description": "...",
      "text_overlay": "..."
    }}
  ]
}}
"""


def generate_script(keyword: str, facts: list[dict], ai_client: AIClient) -> dict:
    """検証済み雑学データから台本を生成"""
    logger.info("スクリプト生成開始: %s", keyword)

    facts_text = "\n".join(
        f"- {f['statement']}" for f in facts
    )

    script = ai_client.generate_json(
        SCRIPT_PROMPT.format(keyword=keyword, facts=facts_text)
    )

    # バリデーション
    total_duration = sum(s.get("duration_sec", 0) for s in script.get("scenes", []))
    if total_duration > 60:
        logger.warning("台本が60秒を超えています (%d秒)。調整が必要です。", total_duration)
        script["total_duration_sec"] = total_duration

    # ナレーション文字数チェック
    total_chars = sum(len(s.get("narration", "")) for s in script.get("scenes", []))
    logger.info("スクリプト生成完了: %s (シーン数: %d, 文字数: %d, 推定秒数: %d)",
                keyword, len(script.get("scenes", [])), total_chars, total_duration)

    return script
