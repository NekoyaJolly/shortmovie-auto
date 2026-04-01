# Trivia Shorts Factory

雑学に特化したショート動画（YouTube Shorts / TikTok）を、トレンド収集から動画生成・投稿までを自動化するパイプラインシステム。

## 必要環境

- Python 3.11+
- FFmpeg（システムにインストール済みであること）
- VOICEVOX（Docker or ネイティブで別途起動）

## セットアップ

```bash
# 依存関係インストール
pip install -e ".[dev]"

# 環境変数設定
cp .env.example .env
# .env を編集してAPIキーを設定

# データベース初期化
python -m src.main init
```

## 使い方

```bash
# 1. トレンド収集 & キーワード候補生成
python -m src.main generate

# 2. キーワードを選択して動画生成（IDはgenerateで表示される）
python -m src.main select 1 3 5

# 3. レビューGUIで承認/却下
python -m src.main gui

# 4. 承認済み動画をYouTubeに投稿
python -m src.main publish

# ステータス確認
python -m src.main status
```

## パイプライン

1. **トレンド収集** - Google Trends / Twitter / YouTube からキーワード取得
2. **リサーチ** - 複数ソースから情報収集 & ファクトチェック
3. **スクリプト生成** - AIで60秒以内の台本作成
4. **アセット生成** - VOICEVOX音声 + フリー画像取得
5. **動画合成** - FFmpegで最終MP4生成
6. **メタデータ生成** - タイトル・説明・タグ自動生成
7. **レビューGUI** - 人間による承認/却下
8. **投稿** - YouTube Shorts API

## 必要なAPIキー

| サービス | 環境変数 | 用途 |
|---------|---------|------|
| Anthropic | `ANTHROPIC_API_KEY` | AI処理（必須） |
| Twitter | `TWITTER_BEARER_TOKEN` | トレンド取得 |
| YouTube | `YOUTUBE_API_KEY` | トレンド取得 |
| Unsplash | `UNSPLASH_API_KEY` | 画像取得 |
| Pexels | `PEXELS_API_KEY` | 画像取得 |
| Pixabay | `PIXABAY_API_KEY` | 画像取得 |
| Google | `GOOGLE_CUSTOM_SEARCH_API_KEY` / `GOOGLE_CUSTOM_SEARCH_CX` | Web検索 |

## YouTube投稿設定

1. Google Cloud Console でOAuth 2.0クライアントIDを作成
2. JSONファイルを `credentials/youtube_oauth.json` に配置
3. 初回投稿時にブラウザ認証フローが起動
