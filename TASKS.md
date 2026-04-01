# Trivia Shorts Factory - 実装タスクリスト

> このファイルはClaude Codeが実装作業を進めるためのタスクリストです。
> 各タスクはSPEC.mdの詳細設計に基づいています。
> 依存関係を守り、上から順に実装してください。

---

## マイルストーン 0: プロジェクト初期セットアップ

### T-000: リポジトリ初期化
- [ ] Gitリポジトリ初期化
- [ ] `.gitignore` 作成（Python, .env, credentials/, output/, assets/, logs/, *.db）
- [ ] `pyproject.toml` 作成（プロジェクトメタデータ、依存関係）
- [ ] `requirements.txt` 生成
- [ ] ディレクトリ構造を作成（T-001参照）

### T-001: ディレクトリ構造作成
```
trivia-shorts-factory/
├── src/
│   ├── __init__.py
│   ├── main.py                    # エントリーポイント（CLI）
│   ├── config.py                  # 設定ファイル読み込み
│   ├── database.py                # SQLite DB初期化・マイグレーション
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # パイプライン全体の制御
│   │   ├── trend_collector.py     # Phase 1: トレンド収集
│   │   ├── researcher.py          # Phase 2: リサーチ & ファクトチェック
│   │   ├── script_generator.py    # Phase 3: スクリプト生成
│   │   ├── asset_generator.py     # Phase 4: アセット生成（TTS + 画像）
│   │   ├── video_composer.py      # Phase 5: 動画合成
│   │   ├── metadata_generator.py  # Phase 6: メタデータ生成
│   │   └── publisher.py           # Phase 8: 投稿
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── app.py                 # PyQt6 メインウィンドウ
│   │   ├── video_list.py          # 動画リストウィジェット
│   │   ├── preview_panel.py       # プレビュー・編集パネル
│   │   └── styles.py              # QSSスタイル定義
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_client.py           # Claude API ラッパー
│   │   ├── tts_client.py          # VOICEVOX APIラッパー
│   │   ├── image_client.py        # 画像検索API統合
│   │   ├── twitter_client.py      # Twitter API ラッパー
│   │   ├── youtube_client.py      # YouTube API ラッパー
│   │   └── search_client.py       # Web検索・学術検索
│   └── utils/
│       ├── __init__.py
│       ├── ffmpeg_utils.py        # FFmpegコマンド生成・実行
│       ├── image_utils.py         # 画像リサイズ・テロップ合成
│       └── text_utils.py          # テキスト処理ユーティリティ
├── config/
│   └── config.yaml                # 設定ファイル
├── credentials/                   # OAuth認証ファイル（.gitignore対象）
├── assets/
│   ├── fonts/                     # フォントファイル
│   └── templates/                 # 動画テンプレート素材
├── output/                        # 生成された動画・メタデータ
├── data/                          # SQLite DBファイル
├── logs/                          # ログファイル
├── tests/
│   ├── __init__.py
│   ├── test_trend_collector.py
│   ├── test_researcher.py
│   ├── test_script_generator.py
│   ├── test_video_composer.py
│   └── test_publisher.py
├── .env.example                   # 環境変数テンプレート
├── SPEC.md                        # プロジェクト仕様書
├── TASKS.md                       # このファイル
└── README.md
```

### T-002: 設定管理の実装
- [ ] `config/config.yaml` をSPEC.md §6に従って作成
- [ ] `src/config.py` で YAML読み込み + 環境変数マージ（`python-dotenv`）
- [ ] `.env.example` を作成
- [ ] 設定値のバリデーション（Pydantic推奨）

### T-003: データベース初期化
- [ ] `src/database.py` でSQLiteテーブル作成（SPEC.md §4参照）
- [ ] マイグレーション機能（テーブルバージョン管理）
- [ ] CRUD操作のヘルパー関数

**依存:** T-002

---

## マイルストーン 1: トレンド収集 & キーワード提案（Phase 1）

### T-100: Twitterトレンド取得
- [ ] `src/services/twitter_client.py` 実装
- [ ] Twitter API v2 Bearer Token認証
- [ ] 日本のトレンド取得（WOEID: 23424856）
- [ ] レート制限対応（リトライ + 指数バックオフ）

### T-101: Google Trends取得
- [ ] `pytrends` を使ったトレンドキーワード取得
- [ ] 日本（geo="JP"）の日次トレンド取得
- [ ] 関連クエリの取得

### T-102: YouTubeトレンド取得
- [ ] YouTube Data API v3 でトレンド動画取得
- [ ] 動画タイトルからキーワード抽出

### T-103: トレンド統合 & AIフィルタリング
- [ ] `src/pipeline/trend_collector.py` 実装
- [ ] 各ソースのキーワードをマージ・正規化・重複除去
- [ ] `src/services/ai_client.py` でClaude APIラッパー実装
- [ ] AIによる雑学適性判定プロンプト実装（SPEC.md §3 Phase1参照）
- [ ] スコア付きキーワードリストの生成・DB保存

**依存:** T-100, T-101, T-102, T-002, T-003

---

## マイルストーン 2: リサーチ & ファクトチェック（Phase 2）

### T-200: 学術検索クライアント
- [ ] `src/services/search_client.py` 実装
- [ ] Google Scholar検索（`scholarly` ライブラリ or スクレイピング）
- [ ] Wikipedia API検索（日本語 + 英語）

### T-201: Web検索クライアント
- [ ] Google Custom Search API 統合
- [ ] DuckDuckGo APIフォールバック
- [ ] 検索結果のパース・構造化

### T-202: ファクトチェックエンジン
- [ ] `src/pipeline/researcher.py` 実装
- [ ] ソース優先順位に基づく情報収集
- [ ] 信頼度スコア計算ロジック（SPEC.md §3 Phase2参照）
- [ ] 3ソース以上の裏付け検証
- [ ] 検証済み/除外データのJSON出力
- [ ] DB保存

**依存:** T-200, T-201, T-103

---

## マイルストーン 3: スクリプト & アセット生成（Phase 3-4）

### T-300: スクリプト生成
- [ ] `src/pipeline/script_generator.py` 実装
- [ ] Claude APIで台本生成プロンプト実装
- [ ] シーン分割データ構造の生成（hook → main → conclusion）
- [ ] 60秒以内制約のバリデーション
- [ ] `visual_description` と `text_overlay` の自動生成

**依存:** T-202

### T-301: VOICEVOX TTS統合
- [ ] `src/services/tts_client.py` 実装
- [ ] VOICEVOX REST API接続
- [ ] テキスト → WAVファイル変換
- [ ] 実測再生時間の取得
- [ ] スピーカーID選択機能
- [ ] ヘルスチェック（VOICEVOXエンジン起動確認）

### T-302: 画像素材取得
- [ ] `src/services/image_client.py` 実装
- [ ] Unsplash / Pexels / Pixabay API統合（優先順位フォールバック）
- [ ] キーワード検索 → 画像ダウンロード
- [ ] 縦型画像の優先選択ロジック

### T-303: アセット生成オーケストレーション
- [ ] `src/pipeline/asset_generator.py` 実装
- [ ] 台本の各シーンに対してTTS + 画像を並列取得
- [ ] 取得結果のファイルパスを台本データに紐付け
- [ ] 失敗時のフォールバック処理（汎用背景画像 + テロップのみ）

**依存:** T-300, T-301, T-302

---

## マイルストーン 4: 動画合成 & メタデータ（Phase 5-6）

### T-400: 画像処理ユーティリティ
- [ ] `src/utils/image_utils.py` 実装
- [ ] 画像の1080x1920リサイズ・クロップ
- [ ] テロップ画像生成（Pillow + Noto Sans JPフォント）
- [ ] テロップの位置・スタイル設定（下部中央、背景半透明帯）

### T-401: FFmpegユーティリティ
- [ ] `src/utils/ffmpeg_utils.py` 実装
- [ ] FFmpegコマンド生成関数
- [ ] 画像+音声の結合処理
- [ ] クロスフェードトランジション
- [ ] 出力MP4のバリデーション（解像度・長さ確認）

### T-402: 動画合成パイプライン
- [ ] `src/pipeline/video_composer.py` 実装
- [ ] シーンごとの画像+テロップ合成
- [ ] 音声の結合（シーン順）
- [ ] FFmpegで最終動画生成
- [ ] 生成結果の検証（ファイル存在・サイズ・再生時間）

**依存:** T-303, T-400, T-401

### T-403: メタデータ生成
- [ ] `src/pipeline/metadata_generator.py` 実装
- [ ] Claude APIでタイトル・説明文・タグを自動生成
- [ ] タイトル30文字以内制約
- [ ] ハッシュタグ生成
- [ ] メタデータJSONの保存
- [ ] DBステータスを `pending_review` に更新

**依存:** T-402

---

## マイルストーン 5: パイプラインオーケストレーション

### T-500: オーケストレーター実装
- [ ] `src/pipeline/orchestrator.py` 実装
- [ ] Phase 1〜6を順序通りに実行する制御ロジック
- [ ] 各フェーズの成功/失敗ハンドリング
- [ ] フェーズ間のデータ受け渡し
- [ ] 並列処理対応（複数キーワードを同時処理、最大ワーカー数設定）

### T-501: CLIエントリーポイント
- [ ] `src/main.py` 実装
- [ ] コマンド: `generate` - パイプライン実行（Phase 1→6）
- [ ] コマンド: `gui` - レビューGUI起動
- [ ] コマンド: `publish` - 承認済み動画の投稿実行
- [ ] コマンド: `status` - 現在の動画一覧・ステータス表示
- [ ] `argparse` or `click` でCLI構築

**依存:** T-403, T-103

### T-502: ロギング設定
- [ ] Python `logging` 設定
- [ ] ファイルローテーション（日次、7日保持）
- [ ] コンソール出力 + ファイル出力の両対応
- [ ] 各フェーズのログレベル設定

---

## マイルストーン 6: レビューGUI（Phase 7）

### T-600: PyQt6メインウィンドウ
- [ ] `src/gui/app.py` 実装
- [ ] メインウィンドウレイアウト（左: リスト、右: プレビュー）
- [ ] メニューバー（設定、ヘルプ）
- [ ] ステータスバー（承認数/総数、投稿待ち数）

### T-601: 動画リストウィジェット
- [ ] `src/gui/video_list.py` 実装
- [ ] SQLiteから動画一覧を読み込み・表示
- [ ] ステータスアイコン表示（pending/approved/rejected）
- [ ] ステータスフィルタリング
- [ ] リスト選択 → プレビューパネル連動

### T-602: プレビュー・編集パネル
- [ ] `src/gui/preview_panel.py` 実装
- [ ] QMediaPlayer での動画インラインプレビュー
- [ ] タイトル・説明文・タグの編集フォーム
- [ ] ファクトチェックスコア・ソースリンク表示
- [ ] 「承認」「却下」「再生成」ボタン
- [ ] 編集内容のDB保存

### T-603: 承認・却下フロー
- [ ] 承認ボタン → ステータス `approved` に更新、投稿キューに追加
- [ ] 却下ボタン → 理由入力ダイアログ → ステータス `rejected` に更新
- [ ] 再生成ボタン → Phase 3に戻して再実行（バックグラウンド）
- [ ] 一括承認・一括却下機能

### T-604: GUIスタイリング
- [ ] `src/gui/styles.py` でQSSテーマ定義
- [ ] ダークモード対応（オプション）
- [ ] アイコンリソースの追加

**依存:** T-500, T-003

---

## マイルストーン 7: 投稿パイプライン（Phase 8）

### T-700: YouTube認証
- [ ] `src/services/youtube_client.py` 実装
- [ ] OAuth 2.0フロー実装（初回認証 → トークン保存 → 自動更新）
- [ ] `google-auth-oauthlib` 利用

### T-701: YouTube投稿機能
- [ ] `videos.insert` APIで動画アップロード
- [ ] Resumable upload対応（大きなファイルの分割アップロード）
- [ ] アップロード進捗の表示
- [ ] 投稿結果（動画ID、URL）のDB保存
- [ ] エラー時のリトライ処理

### T-702: 投稿キュー管理
- [ ] 承認済み動画の投稿キュー取得
- [ ] 順次投稿実行
- [ ] 投稿間隔の設定（レート制限回避）
- [ ] 投稿ログの記録

**依存:** T-603, T-700

---

## マイルストーン 8: テスト & 品質保証

### T-800: ユニットテスト
- [ ] 各サービスクライアントのモックテスト
- [ ] ファクトチェックロジックのテスト
- [ ] スクリプト生成のバリデーションテスト
- [ ] DB操作のテスト

### T-801: 統合テスト
- [ ] パイプライン全体のE2Eテスト（モックAPI使用）
- [ ] GUI操作のテスト（pytest-qt）

### T-802: ドライランモード
- [ ] `--dry-run` フラグの実装
- [ ] 各フェーズの処理結果を確認できるが、外部APIへの投稿は行わない
- [ ] 動画プレビュー生成まで実行、投稿はスキップ

---

## 実装順序ガイド

```
M0 (セットアップ) → M1 (トレンド) → M2 (リサーチ) → M3 (スクリプト・アセット)
                                                              ↓
M5 (オーケストレーション) ← M4 (動画合成) ←─────────────────┘
         ↓
M6 (GUI) → M7 (投稿) → M8 (テスト)
```

各マイルストーンが完了するたびに動作確認を行い、次のマイルストーンに進むこと。
特にM3（VOICEVOX + FFmpeg）は環境依存が大きいため、早期に動作確認すること。

---

## 注意事項（実装者へ）

1. **APIキーは絶対にハードコードしない** → 全て環境変数 or config.yaml 経由
2. **FFmpegはシステムにインストール済みであることを前提とする** → READMEに記載
3. **VOICEVOXはDockerまたはネイティブで別途起動する前提** → 起動確認のヘルスチェックを実装
4. **各フェーズは独立してテスト可能な設計にする** → 依存注入パターン推奨
5. **エラー時は握りつぶさない** → 必ずログに記録し、ステータスに反映
6. **日本語テキスト処理に注意** → エンコーディングはUTF-8統一
