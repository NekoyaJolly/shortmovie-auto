"""SQLite データベース初期化・CRUD操作"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from src.config import get_settings

# テーブル定義SQL
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    source TEXT NOT NULL,
    trivia_score INTEGER,
    selected BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER REFERENCES keywords(id),
    facts_json TEXT NOT NULL,
    total_reliability INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER REFERENCES keywords(id),
    research_id INTEGER REFERENCES research(id),
    script_json TEXT,
    video_path TEXT,
    metadata_json TEXT,
    status TEXT DEFAULT 'generating',
    review_note TEXT,
    youtube_video_id TEXT,
    youtube_url TEXT,
    tiktok_video_id TEXT,
    tiktok_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    published_at DATETIME
);

CREATE TABLE IF NOT EXISTS publish_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER REFERENCES videos(id),
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    response_json TEXT,
    published_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CURRENT_SCHEMA_VERSION = 1


def get_db_path() -> Path:
    return get_settings().db_path


def init_db(db_path: Path | None = None) -> None:
    """データベースを初期化（テーブル作成）"""
    if db_path is None:
        db_path = get_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(SCHEMA_SQL)
        # バージョン記録
        existing = conn.execute(
            "SELECT version FROM schema_version WHERE version = ?",
            (CURRENT_SCHEMA_VERSION,),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (CURRENT_SCHEMA_VERSION,),
            )
        conn.commit()


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """DB接続のコンテキストマネージャ"""
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Keywords CRUD ---


def insert_keyword(keyword: str, source: str, trivia_score: int | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO keywords (keyword, source, trivia_score) VALUES (?, ?, ?)",
            (keyword, source, trivia_score),
        )
        return cursor.lastrowid  # type: ignore


def select_keyword(keyword_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE keywords SET selected = TRUE WHERE id = ?", (keyword_id,))


def get_keywords(selected_only: bool = False) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if selected_only:
            rows = conn.execute(
                "SELECT * FROM keywords WHERE selected = TRUE ORDER BY trivia_score DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM keywords ORDER BY trivia_score DESC"
            ).fetchall()
        return [dict(row) for row in rows]


# --- Research CRUD ---


def insert_research(keyword_id: int, facts: list[dict], total_reliability: int) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO research (keyword_id, facts_json, total_reliability) VALUES (?, ?, ?)",
            (keyword_id, json.dumps(facts, ensure_ascii=False), total_reliability),
        )
        return cursor.lastrowid  # type: ignore


def get_research(research_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM research WHERE id = ?", (research_id,)).fetchone()
        if row:
            result = dict(row)
            result["facts"] = json.loads(result["facts_json"])
            return result
        return None


# --- Videos CRUD ---


def insert_video(
    keyword_id: int,
    research_id: int,
    script_json: dict | None = None,
    status: str = "generating",
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO videos (keyword_id, research_id, script_json, status) VALUES (?, ?, ?, ?)",
            (
                keyword_id,
                research_id,
                json.dumps(script_json, ensure_ascii=False) if script_json else None,
                status,
            ),
        )
        return cursor.lastrowid  # type: ignore


def update_video(video_id: int, **fields: Any) -> None:
    if not fields:
        return
    # JSON型フィールドのシリアライズ
    for key in ("script_json", "metadata_json"):
        if key in fields and isinstance(fields[key], (dict, list)):
            fields[key] = json.dumps(fields[key], ensure_ascii=False)

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [video_id]

    with get_connection() as conn:
        conn.execute(f"UPDATE videos SET {set_clause} WHERE id = ?", values)


def get_video(video_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        if row:
            result = dict(row)
            for key in ("script_json", "metadata_json"):
                if result.get(key):
                    result[key] = json.loads(result[key])
            return result
        return None


def get_videos_by_status(status: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM videos WHERE status = ? ORDER BY created_at DESC", (status,)
        ).fetchall()
        results = []
        for row in rows:
            r = dict(row)
            for key in ("script_json", "metadata_json"):
                if r.get(key):
                    r[key] = json.loads(r[key])
            results.append(r)
        return results


def get_all_videos() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        results = []
        for row in rows:
            r = dict(row)
            for key in ("script_json", "metadata_json"):
                if r.get(key):
                    r[key] = json.loads(r[key])
            results.append(r)
        return results


def approve_video(video_id: int) -> None:
    update_video(video_id, status="approved", reviewed_at=datetime.now().isoformat())


def reject_video(video_id: int, note: str = "") -> None:
    update_video(
        video_id, status="rejected", review_note=note, reviewed_at=datetime.now().isoformat()
    )


# --- Publish Log CRUD ---


def insert_publish_log(
    video_id: int, platform: str, status: str, response: dict | None = None
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO publish_log (video_id, platform, status, response_json) VALUES (?, ?, ?, ?)",
            (
                video_id,
                platform,
                status,
                json.dumps(response, ensure_ascii=False) if response else None,
            ),
        )
        return cursor.lastrowid  # type: ignore
