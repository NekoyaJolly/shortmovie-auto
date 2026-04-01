# Trivia Shorts Factory - プロジェクト仕様書

## 1. プロジェクト概要

**プロジェクト名:** Trivia Shorts Factory
**目的:** 雑学に特化したショート動画（YouTube Shorts / TikTok）を、トレンド収集から動画生成・投稿までを自動化するパイプラインシステム
**言語:** Python 3.11+
**規模:** 1日最大10本の動画生成・投稿

### 核心原則
- 社会通念上、間違った情報は絶対に発信しない
- 意見が分かれるトピックは扱わない
- 最終投稿には必ず人間の承認を経る（Human-in-the-loop）
- ランニングコストは最小限（無料枠・セルフホスト優先）

---

## 2. システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    Trivia Shorts Factory                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Phase 1]        [Phase 2]        [Phase 3]               │
│  トレンド収集 ──→ リサーチ ──→ スクリプト生成              │
│  & キーワード      & ファクト       & 台本作成               │
│    提案            チェック                                  │
│      │                                                      │
│      ▼ (ユーザーがキーワード選択)                            │
│                                                             │
│  [Phase 4]        [Phase 5]        [Phase 6]               │
│  アセット生成 ──→ 動画合成 ──→ メタデータ生成              │
│  (音声・画像)     (FFmpeg)        (タイトル・タグ等)        │
│                                                             │
│      │                                                      │
│      ▼                                                      │
│  ┌─────────────────────────────────┐                        │
│  │  [Phase 7] レビューGUI (PyQt6)  │                        │
│  │  ・動画一覧リスト               │                        │
│  │  ・プレビュー再生               │                        │
│  │  ・メタデータ編集               │                        │
│  │  ・承認 / 却下 / 編集           │                        │
│  └──────────────┬──────────────────┘                        │
│                 │ (承認時のみ)                               │
│                 ▼                                            │
│  [Phase 8] 投稿パイプライン                                 │
│  YouTube Shorts API → (将来) TikTok API                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 各フェーズ詳細設計

### Phase 1: トレンド収集 & キーワード提案

**目的:** 流行りのトピックから雑学コンテンツに適したキーワード候補を抽出する

**入力:** なし（自動実行）
**出力:** キーワード候補リスト（10〜20件）+ 各候補のスコア・理由

**データソース:**
| ソース | API | 無料枠 |
|--------|-----|--------|
| Twitter/X | Twitter API v2 (Basic) | 月10,000ツイート読取 |
| Google Trends | `pytrends` ライブラリ | 無料（非公式） |
| YouTube Trending | YouTube Data API v3 | 10,000units/日 |

**処理フロー:**
1. 各ソースからトレンドキーワードを取得
2. キーワードをマージ・重複除去
3. AIフィルタリング（Claude API）:
   - 雑学コンテンツに適しているか判定
   - 意見が分かれるトピックを除外
   - 政治・宗教・論争的テーマを除外
   - 「雑学適性スコア」を付与（1-10）
4. スコア上位10〜20件をユーザーに提示

**AIフィルタリングプロンプト方針:**
```
以下のキーワードについて、雑学ショート動画のトピックとして適切かを判定してください。
判定基準:
- 事実ベースの雑学が存在するか
- 意見が分かれるトピックではないか
- 多くの人が「へぇ」と思える内容か
- 60秒以内で伝えられる内容か
```

---

### Phase 2: リサーチ & ファクトチェック

**目的:** 選択されたキーワードに対して、信頼性の高い情報を複数ソースから収集・検証する

**入力:** ユーザーが選択したキーワード（1つ以上）
**出力:** 検証済み雑学データ（JSON形式）

**情報ソース（優先順位順）:**
1. **学術系:** Google Scholar, CiNii（日本語論文）, PubMed
2. **百科事典:** Wikipedia API（日本語・英語）
3. **Web検索:** Google Custom Search API / DuckDuckGo

**ファクトチェックルール:**
- 最低3つのソースが同一の事実を裏付けていること
- 学術ソースが1つ以上含まれることが望ましい（必須ではない）
- ソースごとに信頼度スコアを付与:
  - 学術論文: 10
  - Wikipedia（出典あり）: 8
  - 公的機関サイト: 8
  - 一般Webサイト（複数一致）: 5
- 合計信頼度スコアが15以上で「検証済み」とする

**出力フォーマット:**
```json
{
  "keyword": "猫のヒゲ",
  "facts": [
    {
      "statement": "猫のヒゲは空間認識センサーとして機能し、体の幅とほぼ同じ長さがある",
      "sources": [
        {"type": "academic", "url": "...", "title": "...", "reliability": 10},
        {"type": "wikipedia", "url": "...", "title": "...", "reliability": 8},
        {"type": "web", "url": "...", "title": "...", "reliability": 5}
      ],
      "total_reliability": 23,
      "verified": true
    }
  ],
  "excluded_claims": [
    {
      "statement": "...",
      "reason": "ソースが1つしか見つからなかった"
    }
  ]
}
```

---

### Phase 3: スクリプト生成（台本作成）

**目的:** 検証済みの雑学データから60秒以内のショート動画用台本を生成する

**入力:** Phase 2の検証済み雑学データ
**出力:** 台本（テキスト）+ シーン分割データ

**台本構造:**
```json
{
  "title": "猫のヒゲの秘密",
  "total_duration_sec": 55,
  "scenes": [
    {
      "scene_id": 1,
      "type": "hook",
      "narration": "猫のヒゲ、ただの飾りだと思っていませんか？",
      "duration_sec": 5,
      "visual_description": "猫のアップ、ヒゲにフォーカス",
      "text_overlay": "猫のヒゲの秘密"
    },
    {
      "scene_id": 2,
      "type": "main",
      "narration": "実は猫のヒゲは...",
      "duration_sec": 20,
      "visual_description": "...",
      "text_overlay": "..."
    },
    {
      "scene_id": 3,
      "type": "conclusion",
      "narration": "...",
      "duration_sec": 10,
      "visual_description": "...",
      "text_overlay": "..."
    }
  ]
}
```

**台本生成ルール:**
- 最初の3秒で視聴者の興味を引く「フック」を入れる
- ナレーション全体で200〜300文字程度（60秒以内に収まるペース）
- 各シーンに `visual_description`（画像検索用キーワード）を含める
- 各シーンに `text_overlay`（テロップ用テキスト）を含める

---

### Phase 4: アセット生成

**目的:** 台本に基づいて音声ファイルと画像素材を生成・取得する

#### 4-A: 音声生成（TTS）

**ツール:** VOICEVOX（セルフホスト、無料）
**理由:**
- 日本語対応が優秀
- 完全無料・オープンソース
- RESTful API でローカル実行可能
- 複数のキャラクターボイスから選択可能

**処理:**
1. VOICEVOXエンジンをローカルで起動（Docker or ネイティブ）
2. 各シーンの `narration` テキストをAPIに送信
3. WAVファイルとして保存
4. シーンごとの実測再生時間を取得し、台本の `duration_sec` を更新

**VOICEVOXのAPI利用例:**
```python
# 音声合成クエリ作成
query = requests.post(
    f"http://localhost:50021/audio_query?text={text}&speaker={speaker_id}"
).json()
# 音声合成実行
audio = requests.post(
    f"http://localhost:50021/synthesis?speaker={speaker_id}",
    json=query
)
```

#### 4-B: 画像素材取得

**ソース（優先順位順）:**
1. **Unsplash API** - 高品質フリー画像（無料、50リクエスト/時）
2. **Pexels API** - フリー画像（無料、200リクエスト/時）
3. **Pixabay API** - フリー画像・イラスト（無料、100リクエスト/分）

**処理:**
1. 各シーンの `visual_description` をキーワードとして画像検索
2. 縦型（9:16）に適した画像を優先選択
3. ダウンロードして `assets/images/` に保存
4. 画像が見つからない場合は、汎用的な背景画像にテロップのみで構成

**将来拡張:** Canva APIを使ったテンプレートベースのデザイン生成

---

### Phase 5: 動画合成

**ツール:** FFmpeg（Python `subprocess` 経由）
**補助:** Pillow（テロップ画像生成）, moviepy（オプション）

**出力仕様:**
| 項目 | 値 |
|------|-----|
| 解像度 | 1080x1920 (9:16) |
| フレームレート | 30fps |
| 動画コーデック | H.264 |
| 音声コーデック | AAC |
| コンテナ | MP4 |
| 最大長 | 60秒 |

**合成処理フロー:**
1. 各シーンの画像を1080x1920にリサイズ・クロップ（Pillow）
2. テロップ用テキスト画像を生成（Pillow, フォント: Noto Sans JP）
3. テロップ画像を元画像に合成
4. 各シーン画像の表示時間をナレーション音声の長さに合わせて調整
5. クロスフェード等のシンプルなトランジションを追加
6. FFmpegで全シーンの画像+音声を結合して最終MP4を生成

**FFmpegコマンド例（概念）:**
```bash
ffmpeg -i scene1.png -i scene2.png ... \
       -i narration_full.wav \
       -filter_complex "[0:v]...[1:v]...concat..." \
       -c:v libx264 -c:a aac \
       -s 1080x1920 \
       output.mp4
```

---

### Phase 6: メタデータ生成

**目的:** 動画に付随するタイトル、説明文、タグ、サムネイルテキストを自動生成する

**入力:** 台本データ + 動画ファイルパス
**出力:** メタデータJSON

**生成項目:**
```json
{
  "video_file": "output/猫のヒゲの秘密_20260402.mp4",
  "title": "【衝撃】猫のヒゲには驚きの秘密が...! #雑学 #猫",
  "description": "猫のヒゲが空間認識センサーだって知ってましたか？\n\n今回は猫のヒゲの意外な役割について解説します。\n\n#猫 #雑学 #豆知識 #shorts",
  "tags": ["猫", "雑学", "豆知識", "動物", "サイエンス", "shorts"],
  "thumbnail_text": "猫のヒゲの秘密",
  "category": "Education",
  "language": "ja",
  "sources_used": ["https://...", "https://..."],
  "fact_check_score": 23,
  "created_at": "2026-04-02T10:30:00+09:00",
  "status": "pending_review"
}
```

**タイトル生成ルール:**
- 30文字以内
- 冒頭に【】で注目ワード
- 末尾にハッシュタグ1〜2個
- クリックベイトは避けるが興味を引く表現にする

---

### Phase 7: レビューGUI（デスクトップアプリ）

**ツール:** PyQt6
**目的:** 生成された動画をリスト表示し、人間がレビュー・承認するためのインターフェース

**画面構成:**
```
┌─────────────────────────────────────────────────────────┐
│  Trivia Shorts Factory - Review Dashboard               │
├──────────────────────┬──────────────────────────────────┤
│                      │                                  │
│  📋 動画リスト       │  🎬 プレビュー                   │
│  ──────────────      │  ┌──────────────────────┐       │
│  ☐ 猫のヒゲの秘密   │  │                      │       │
│    → pending_review  │  │   動画プレビュー      │       │
│  ☐ 蜂蜜の不思議     │  │   エリア              │       │
│    → pending_review  │  │                      │       │
│  ✓ 宇宙の雑学       │  └──────────────────────┘       │
│    → approved        │                                  │
│  ✗ 天気の仕組み     │  タイトル: [編集可能フィールド]   │
│    → rejected        │  説明文:   [編集可能テキスト]     │
│                      │  タグ:     [編集可能リスト]       │
│                      │                                  │
│                      │  信頼度スコア: 23/30             │
│                      │  ソース: [リンクリスト]           │
│                      │                                  │
│                      │  [✓ 承認] [✗ 却下] [✎ 再生成]  │
│                      │                                  │
├──────────────────────┴──────────────────────────────────┤
│  ステータスバー: 承認済み 3/10 | 投稿待ち 2 | 却下 1   │
└─────────────────────────────────────────────────────────┘
```

**機能要件:**
- 動画リストの表示（ステータスでフィルタリング可能）
- 動画のインラインプレビュー再生
- タイトル・説明文・タグの直接編集
- ファクトチェックスコア・ソースリンクの表示
- 承認 → 投稿キューに追加
- 却下 → 理由入力（オプション）→ アーカイブ
- 再生成 → Phase 3に戻してスクリプトから再生成
- 一括承認・一括却下

**データ管理:**
- SQLite でローカルDB管理（動画メタデータ、ステータス、レビュー履歴）
- 動画ファイルはローカルファイルシステムに保存

---

### Phase 8: 投稿パイプライン

**Phase 8-A: YouTube Shorts（優先）**

**API:** YouTube Data API v3
**認証:** OAuth 2.0

**処理フロー:**
1. GUIで承認された動画を投稿キューから取得
2. YouTube Data API でアップロード:
   - `videos.insert` エンドポイント
   - snippet: タイトル、説明文、タグ、カテゴリ
   - status: `public` or `private`（設定可能）
3. アップロード結果（動画ID、URL）をDBに保存
4. ステータスを `published` に更新

**Phase 8-B: TikTok（将来拡張）**

**API:** TikTok Content Posting API
**実装時期:** YouTube Shortsパイプライン安定後

**追加対応事項:**
- TikTok用のメタデータ調整（タイトル文字数制限等）
- TikTokアカウント認証フロー
- 同一動画のマルチプラットフォーム投稿管理

---

## 4. データ構造

### SQLite テーブル設計

```sql
-- キーワード候補
CREATE TABLE keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    source TEXT NOT NULL,           -- twitter / google_trends / youtube
    trivia_score INTEGER,           -- 1-10
    selected BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- リサーチ結果
CREATE TABLE research (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER REFERENCES keywords(id),
    facts_json TEXT NOT NULL,       -- JSON: 検証済み事実データ
    total_reliability INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 動画
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER REFERENCES keywords(id),
    research_id INTEGER REFERENCES research(id),
    script_json TEXT,               -- JSON: 台本データ
    video_path TEXT,                -- ローカルファイルパス
    metadata_json TEXT,             -- JSON: タイトル・説明・タグ等
    status TEXT DEFAULT 'generating', -- generating / pending_review / approved / rejected / publishing / published / failed
    review_note TEXT,               -- レビューコメント
    youtube_video_id TEXT,
    youtube_url TEXT,
    tiktok_video_id TEXT,
    tiktok_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    published_at DATETIME
);

-- 投稿ログ
CREATE TABLE publish_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER REFERENCES videos(id),
    platform TEXT NOT NULL,         -- youtube / tiktok
    status TEXT NOT NULL,           -- success / failed
    response_json TEXT,
    published_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. 技術スタック

| カテゴリ | 技術 | 理由 |
|----------|------|------|
| 言語 | Python 3.11+ | ユーザー希望、エコシステム充実 |
| TTS | VOICEVOX | 日本語対応、無料、セルフホスト |
| 動画合成 | FFmpeg + Pillow | 無料、高機能、業界標準 |
| GUI | PyQt6 | 動画プレビュー対応、モダンUI |
| DB | SQLite | 軽量、セットアップ不要 |
| AI | Claude API (Anthropic) | ユーザーが契約済み |
| 画像取得 | Unsplash / Pexels / Pixabay API | 無料枠で十分 |
| トレンド | Twitter API v2 + pytrends | トレンド取得 |
| 投稿 | YouTube Data API v3 | OAuth 2.0 |
| タスク管理 | SQLiteベースのキュー | シンプル、外部依存なし |

---

## 6. 設定ファイル

```yaml
# config.yaml
app:
  name: "Trivia Shorts Factory"
  output_dir: "./output"
  assets_dir: "./assets"
  db_path: "./data/trivia_shorts.db"
  max_videos_per_day: 10

tts:
  engine: "voicevox"
  voicevox_url: "http://localhost:50021"
  speaker_id: 1            # VOICEVOXキャラクター選択
  speed_scale: 1.0

video:
  width: 1080
  height: 1920
  fps: 30
  max_duration_sec: 60
  font: "NotoSansJP-Bold.ttf"
  font_size: 48
  transition: "crossfade"
  transition_duration_ms: 500

ai:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  max_tokens: 4096

trend_sources:
  twitter:
    enabled: true
    woeid: 23424856          # Japan
  google_trends:
    enabled: true
    geo: "JP"
  youtube:
    enabled: true
    region_code: "JP"

image_sources:
  - name: "unsplash"
    api_key_env: "UNSPLASH_API_KEY"
    priority: 1
  - name: "pexels"
    api_key_env: "PEXELS_API_KEY"
    priority: 2
  - name: "pixabay"
    api_key_env: "PIXABAY_API_KEY"
    priority: 3

youtube:
  credentials_path: "./credentials/youtube_oauth.json"
  default_privacy: "private"   # private で投稿→手動で public も可
  default_category: "27"       # Education

fact_check:
  min_sources: 3
  min_reliability_score: 15
  source_weights:
    academic: 10
    wikipedia: 8
    government: 8
    web: 5
```

---

## 7. 環境変数

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
TWITTER_BEARER_TOKEN=...
YOUTUBE_API_KEY=...
UNSPLASH_API_KEY=...
PEXELS_API_KEY=...
PIXABAY_API_KEY=...
GOOGLE_CUSTOM_SEARCH_API_KEY=...
GOOGLE_CUSTOM_SEARCH_CX=...
```

---

## 8. 非機能要件

- **エラーハンドリング:** 各フェーズで失敗した場合、動画のステータスを `failed` に更新し、エラー内容をログに記録。他の動画の処理は継続する。
- **リトライ:** API呼び出しは最大3回リトライ（指数バックオフ）
- **ロギング:** Python `logging` モジュールで `logs/` ディレクトリにローテーションログを出力
- **冪等性:** 同一キーワードで再実行しても二重投稿しない（DB上のステータスで管理）
- **セキュリティ:** APIキーは環境変数管理、`.env` は `.gitignore` に含める
