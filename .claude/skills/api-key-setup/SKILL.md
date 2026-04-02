---
name: api-key-setup
description: >
  APIキーやクレデンシャルの取得・設定を支援するスキル。
  開発者コンソールへのナビゲート、OAuthアプリ登録フォームの記入（リダイレクトURL、スコープ、アプリ名など）、
  .envファイルへの書き込みまでの一連のワークフローをガイドする。
  ユーザーがAPIキーを取得したい、シークレットを設定したい、OAuthの設定をしたい、
  開発者コンソールの設定が面倒、.envを整えたい、と言ったときに使うこと。
  「APIキー」「シークレット」「クレデンシャル」「OAuth設定」「開発者コンソール」
  「.env」「環境変数」といったキーワードが出たら積極的にこのスキルを使う。
---

# APIキー取得・設定スキル

このスキルは、プロジェクトに必要なAPIキーやクレデンシャルを取得して設定する作業を、
ユーザーとClaudeで効率よく分担するためのワークフローを定義している。

## 基本方針：CLI優先、ブラウザは最終手段

APIキーやクレデンシャルの取得には、可能な限りCLIツールを使う。
ブラウザ操作はCLIでは不可能な場合（OAuthアプリの登録、GCPコンソールでの設定など）にのみ行う。

## 役割分担

このワークフローでは、セキュリティ上の理由からClaudeとユーザーで明確に役割が分かれる。

### Claudeが担当すること

- プロジェクトの設定ファイルを読んで、必要なAPIキー・環境変数を特定する
- `.env.example`、`docker-compose.yml`、フレームワーク固有の設定ファイルなどから、リダイレクトURL・ポート番号・コールバックパスを割り出す
- CLIが使える場合はCLIコマンドを実行してキーを取得する
- ブラウザで開発者コンソールの該当ページまでナビゲートする
- OAuthアプリ登録やAPI有効化のフォームで、アプリ名・説明文・リダイレクトURI・許可スコープなどの入力欄を埋める
- 取得したキーを`.env`ファイルに正しいフォーマットで書き込む
- 既存の`.env`がある場合は壊さずに該当行だけ追加・更新する

### ユーザーが担当すること（Claudeは代行できない）

- 各サービスへのログイン（パスワード入力・2FA認証）
- APIキー・シークレットの値のコピー（画面に表示されたキーをコピーしてチャットに貼る）
- 課金設定や利用規約への同意

## ワークフロー

### Step 1: プロジェクトの調査

まずプロジェクトの現状を把握する。以下のファイルを確認して、何が必要かを整理する。

確認対象（プロジェクトによって異なるので、存在するものだけ見る）：

- `.env` / `.env.example` / `.env.local` — 必要な環境変数の一覧
- `package.json` — 使用しているSDKやライブラリからサービスを推定
- フレームワーク設定（`next.config.js`、`nuxt.config.ts`、`vite.config.ts`など）— リダイレクトURLやポート番号
- `docker-compose.yml` — サービス間の接続情報やポートマッピング
- `vercel.json` / `netlify.toml` — デプロイ先のURL情報
- 認証設定（`auth.config.ts`、`[...nextauth].ts`など）— OAuthプロバイダーの設定、コールバックURL

調査結果をユーザーに報告する形式：

【必要なAPIキー/シークレット一覧】
1. GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET — Google OAuth用（未設定）
2. DATABASE_URL — すでに設定済み、スキップ
3. STRIPE_SECRET_KEY — Stripe決済用（未設定）

【プロジェクトから読み取った情報】
- 開発サーバーURL: http://localhost:3000
- OAuthコールバック: /api/auth/callback/google
- リダイレクトURI（フル）: http://localhost:3000/api/auth/callback/google

### Step 2: 取得方法の決定

各キーについて、CLI or ブラウザのどちらで取得するか判断する。

CLIで取得可能な例：
- `gcloud` — GCPサービスアカウントキー、APIキー
- `gh` — GitHub Personal Access Token（スコープ制限付き）
- `supabase` — Supabase APIキー
- `firebase` — Firebase設定
- `stripe` CLI — Stripeテスト用キー
- `vercel env pull` — Vercelの環境変数

CLIツールが利用可能かどうかは `which <command>` で確認する。
インストールされていない場合はインストール手順を案内するか、ブラウザフローに切り替える。

### Step 3: CLI取得（可能な場合）

CLIが使える場合は、コマンドを組み立てて実行する。
ただし、認証が必要な場合（`gcloud auth login`など）はユーザーに認証操作を依頼する。

例（GCPサービスアカウント）：
gcloud auth list
gcloud config set project PROJECT_ID
gcloud services enable sheets.googleapis.com
gcloud iam service-accounts keys create ./credentials.json --iam-account=SA_NAME@PROJECT_ID.iam.gserviceaccount.com

### Step 4: ブラウザ取得（CLIでは不可能な場合）

ブラウザ操作が必要な場合の手順。

1. ナビゲーション — 開発者コンソールの該当ページをブラウザで開く
2. ログイン待ち — ログイン画面が表示されたらユーザーに通知する。「ログインをお願いします。完了したら教えてください」と伝える
3. フォーム記入 — ログイン後、アプリ登録やAPI設定のフォームを記入する。Step 1で調査した情報（リダイレクトURL、スコープなど）を使う
4. キー取得の依頼 — キーが画面に表示されたら、ユーザーにコピーを依頼する。「表示されているAPIキーをコピーしてチャットに貼ってください」

主要サービスのコンソールURL：
- GCP: https://console.cloud.google.com/apis/credentials
- GitHub OAuth: https://github.com/settings/developers
- Stripe: https://dashboard.stripe.com/apikeys
- Auth0: https://manage.auth0.com/

### Step 5: .envへの書き込み

キーを受け取ったら`.env`ファイルに書き込む。

書き込みルール：
- `.env`が存在しない場合は`.env.example`をコピーして作成する
- 既存の`.env`がある場合は該当行だけを追加・更新する（他の行は触らない）
- コメントで何のキーかを残す
- キーの値はダブルクォートで囲まない（値にスペースが含まれる場合のみ囲む）
- `.gitignore`に`.env`が含まれているか確認し、なければ追加するか警告する

書き込み後、設定が正しいことをユーザーと一緒に確認する。
可能であれば簡単な接続テスト（APIへのping、認証チェックなど）を実行する。

## GCPでよくあるパターン

GCPは特に設定項目が多いので、よくあるパターンをまとめておく。

### OAuth同意画面の設定
GCPでOAuthクライアントIDを作る前に、OAuth同意画面の設定が必要になることが多い。
- ユーザータイプ: 開発中は「外部」でOK
- アプリ名: プロジェクト名を使う
- ユーザーサポートメール: ユーザーのメールアドレスを使う
- 承認済みドメイン: 開発中は不要なことが多い
- スコープ: プロジェクトのコードから必要なスコープを読み取って設定する

### OAuthクライアントIDの作成
- アプリケーションの種類: 「ウェブアプリケーション」が多い
- 承認済みJavaScript生成元: http://localhost:3000（開発環境）
- 承認済みリダイレクトURI: Step 1で特定したコールバックURL

### APIの有効化
必要なAPIが有効化されていない場合、CLIまたはコンソールから有効化する。
gcloud services enable <API名> が使えるならCLIで。

## セキュリティに関する注意

- APIキーやシークレットの値をメモリ（auto-memory）に保存しない
- チャットで受け取ったキーは`.env`に書き込んだ後、会話の中で繰り返し表示しない
- `.env`ファイルがgitにコミットされないことを必ず確認する
- 本番環境のキーと開発環境のキーを明確に区別する
