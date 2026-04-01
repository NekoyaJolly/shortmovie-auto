"""Trivia Shorts Factory - CLIエントリーポイント"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from src.config import PROJECT_ROOT

# ロギング設定
def setup_logging(verbose: bool = False) -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO

    # ファイルハンドラ（ローテーション）
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        log_dir / "trivia_shorts.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # フォーマット
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="詳細ログを出力")
def cli(verbose: bool) -> None:
    """Trivia Shorts Factory - 雑学ショート動画自動生成ツール"""
    setup_logging(verbose)


@cli.command()
def generate() -> None:
    """パイプライン実行（Phase 1→6: トレンド収集→動画生成）"""
    from src.database import init_db
    from src.pipeline.orchestrator import run_pipeline

    init_db()
    click.echo("トレンド収集を開始します...")
    run_pipeline()
    click.echo("キーワード候補を生成しました。'trivia-shorts select' で選択してください。")


@cli.command()
@click.argument("keyword_ids", nargs=-1, type=int, required=True)
def select(keyword_ids: tuple[int, ...]) -> None:
    """選択したキーワードから動画を生成

    KEYWORD_IDS: 処理するキーワードのID（スペース区切りで複数指定可）
    """
    from src.pipeline.orchestrator import run_pipeline

    click.echo(f"キーワード {list(keyword_ids)} の動画生成を開始...")
    video_ids = run_pipeline(list(keyword_ids))
    if video_ids:
        click.echo(f"動画生成完了: {video_ids}")
        click.echo("'trivia-shorts gui' でレビューしてください。")
    else:
        click.echo("動画の生成に失敗しました。ログを確認してください。")


@cli.command()
def gui() -> None:
    """レビューGUIを起動"""
    try:
        from src.database import init_db
        from src.gui.app import run_gui

        init_db()
        run_gui()
    except ImportError as e:
        click.echo(f"GUI起動エラー: {e}")
        click.echo("PyQt6がインストールされているか確認してください: pip install PyQt6")
        sys.exit(1)


@cli.command()
def publish() -> None:
    """承認済み動画をYouTube Shortsに投稿"""
    from src.pipeline.publisher import publish_approved_videos

    click.echo("承認済み動画の投稿を開始...")
    published = publish_approved_videos()
    if published:
        click.echo(f"投稿完了: {len(published)}本")
    else:
        click.echo("投稿する動画がありません。")


@cli.command()
def status() -> None:
    """現在の動画一覧・ステータスを表示"""
    from src.database import get_all_videos, init_db

    init_db()
    videos = get_all_videos()

    if not videos:
        click.echo("動画データはまだありません。")
        return

    # ステータス別カウント
    status_counts: dict[str, int] = {}
    for v in videos:
        s = v.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    click.echo(f"\n動画一覧 (合計: {len(videos)}本)")
    click.echo("-" * 60)

    for v in videos:
        meta = v.get("metadata_json", {})
        title = meta.get("title", v.get("script_json", {}).get("title", "無題")) if meta else "無題"
        click.echo(f"  [{v['id']}] {title}")
        click.echo(f"       ステータス: {v['status']} | 作成: {v['created_at']}")

    click.echo("-" * 60)
    for s, count in sorted(status_counts.items()):
        click.echo(f"  {s}: {count}本")


@cli.command()
def init() -> None:
    """データベースを初期化"""
    from src.database import init_db

    init_db()
    click.echo("データベースを初期化しました。")


if __name__ == "__main__":
    cli()
