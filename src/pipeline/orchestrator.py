"""パイプライン全体のオーケストレーション"""

from __future__ import annotations

import logging

from src.database import (
    get_keywords,
    get_research,
    get_videos_by_status,
    init_db,
    insert_video,
    select_keyword,
    update_video,
)
from src.pipeline.asset_generator import generate_assets
from src.pipeline.metadata_generator import generate_metadata
from src.pipeline.researcher import research_keyword
from src.pipeline.script_generator import generate_script
from src.pipeline.trend_collector import run_trend_collection
from src.pipeline.video_composer import compose_video
from src.services.ai_client import AIClient

logger = logging.getLogger(__name__)


def run_pipeline(keyword_ids: list[int] | None = None) -> list[int]:
    """Phase 1〜6のパイプラインを実行

    Args:
        keyword_ids: 処理するキーワードIDのリスト。Noneならトレンド収集から開始。

    Returns:
        生成された動画IDのリスト
    """
    init_db()
    ai_client = AIClient()
    video_ids: list[int] = []

    # Phase 1: トレンド収集（keyword_idsが指定されていない場合）
    if keyword_ids is None:
        logger.info("Phase 1: トレンド収集")
        candidates = run_trend_collection()
        if not candidates:
            logger.warning("キーワード候補が見つかりませんでした")
            return []

        # 全候補を取得してユーザー選択を待つ
        logger.info("キーワード候補:")
        keywords = get_keywords()
        for kw in keywords:
            logger.info("  [%d] %s (スコア: %s, ソース: %s)",
                        kw["id"], kw["keyword"], kw["trivia_score"], kw["source"])
        logger.info("CLIまたはGUIでキーワードを選択してください")
        return []

    # 選択されたキーワードを処理
    for keyword_id in keyword_ids:
        try:
            select_keyword(keyword_id)
            keywords = get_keywords(selected_only=True)
            kw_data = next((k for k in keywords if k["id"] == keyword_id), None)
            if not kw_data:
                logger.error("キーワードID %d が見つかりません", keyword_id)
                continue

            keyword = kw_data["keyword"]
            video_id = _process_keyword(keyword, keyword_id, ai_client)
            if video_id:
                video_ids.append(video_id)

        except Exception as e:
            logger.error("キーワード %d の処理に失敗: %s", keyword_id, e, exc_info=True)

    return video_ids


def _process_keyword(keyword: str, keyword_id: int, ai_client: AIClient) -> int | None:
    """個別キーワードの処理（Phase 2〜6）"""
    logger.info("=== キーワード処理開始: %s (ID: %d) ===", keyword, keyword_id)

    # Phase 2: リサーチ
    logger.info("Phase 2: リサーチ & ファクトチェック")
    research_result = research_keyword(keyword, keyword_id, ai_client)
    if not research_result.facts:
        logger.warning("検証済み雑学が見つかりませんでした: %s", keyword)
        return None

    # research IDを取得
    from src.database import get_connection
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM research WHERE keyword_id = ? ORDER BY id DESC LIMIT 1",
            (keyword_id,),
        ).fetchone()
    research_id = row["id"] if row else 0

    # Phase 3: スクリプト生成
    logger.info("Phase 3: スクリプト生成")
    facts_data = [{"statement": f.statement} for f in research_result.facts]
    script = generate_script(keyword, facts_data, ai_client)

    # 動画レコード作成
    video_id = insert_video(keyword_id, research_id, script, status="generating")

    try:
        # Phase 4: アセット生成
        logger.info("Phase 4: アセット生成")
        script = generate_assets(script, video_id)
        update_video(video_id, script_json=script)

        # Phase 5: 動画合成
        logger.info("Phase 5: 動画合成")
        video_path = compose_video(script, video_id)
        update_video(video_id, video_path=str(video_path))

        # Phase 6: メタデータ生成
        logger.info("Phase 6: メタデータ生成")
        sources = []
        for fact in research_result.facts:
            for s in fact.sources:
                if s.url:
                    sources.append(s.url)
        metadata = generate_metadata(script, sources, ai_client)
        update_video(video_id, metadata_json=metadata, status="pending_review")

        logger.info("=== キーワード処理完了: %s → video_id=%d ===", keyword, video_id)
        return video_id

    except Exception as e:
        logger.error("動画生成エラー (video_id=%d): %s", video_id, e, exc_info=True)
        update_video(video_id, status="failed", review_note=str(e))
        return None
