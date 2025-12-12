# ebois-slack-ai-chatbot

Render経由でデプロイ可能なSlack AIチャットボット。OpenAI APIを使用してSlackメッセージに応答します。

## 機能

- SlackメンションまたはDMへの自動応答
- OpenAI API（GPT-4o-mini）との統合
- Renderへの簡単デプロイ
- 署名検証によるセキュリティ

## 必要な環境変数

以下の環境変数を設定する必要があります：

- `SLACK_BOT_TOKEN`: Slack Bot User OAuth Token（`xoxb-`で始まる）
- `SLACK_SIGNING_SECRET`: Slack AppのSigning Secret
- `OPENAI_API_KEY`: OpenAI APIキー（`sk-`で始まる）

## セットアップ手順

### 1. Slack Appの作成

1. [Slack API](https://api.slack.com/apps)にアクセス
2. "Create New App" → "From scratch"を選択
3. App名とワークスペースを選択

### 2. Bot Token Scopesの設定

1. "OAuth & Permissions"に移動
2. "Bot Token Scopes"に以下を追加：
   - `app_mentions:read` - メンションを読み取る
   - `chat:write` - メッセージを送信
   - `channels:history` - チャンネルの履歴を読み取る（オプション）
   - `im:history` - DMの履歴を読み取る（オプション）
   - `im:read` - DMを読み取る

### 3. Event Subscriptionsの設定

1. "Event Subscriptions"に移動
2. "Enable Events"をON
3. Request URL: `https://your-app.onrender.com/slack/events`
4. "Subscribe to bot events"に以下を追加：
   - `app_mentions` - メンションイベント
   - `message.im` - DMイベント（オプション）

### 4. Botのインストール

1. "Install to Workspace"をクリック
2. 権限を承認
3. "Bot User OAuth Token"をコピー（`SLACK_BOT_TOKEN`として使用）
4. "Signing Secret"をコピー（`SLACK_SIGNING_SECRET`として使用）

### 5. OpenAI APIキーの取得

1. [OpenAI Platform](https://platform.openai.com/)にアクセス
2. API Keysセクションで新しいキーを作成
3. キーをコピー（`OPENAI_API_KEY`として使用）

### 6. Renderへのデプロイ

1. [Render](https://render.com/)にログイン
2. "New +" → "Blueprint"を選択
3. このリポジトリを接続
4. `render.yaml`が自動的に読み込まれます
5. 環境変数を設定：
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`
   - `OPENAI_API_KEY`
6. "Apply"をクリックしてデプロイ

### 7. Slack AppのRequest URLを更新

1. Renderデプロイ後、URLを取得（例: `https://slack-ai-chatbot.onrender.com`）
2. Slack Appの"Event Subscriptions"に戻る
3. Request URLを更新: `https://your-app.onrender.com/slack/events`
4. SlackがURL検証を行い、成功すれば完了

## ローカル開発

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数を設定
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_SIGNING_SECRET="your-secret"
export OPENAI_API_KEY="sk-your-key"

# サーバー起動
uvicorn app:app --reload --port 8000
```

## 使用方法

1. Slackワークスペースでボットをメンション（`@your-bot-name`）
2. メッセージを送信
3. ボットがOpenAI APIを使用して応答

## カスタマイズ

### システムプロンプトの変更

`app.py`の`call_openai`関数内の`system_prompt`を編集：

```python
system_prompt = "あなたのカスタムプロンプト"
```

### モデルの変更

`call_openai`関数内の`model`パラメータを変更：

```python
model="gpt-4"  # または "gpt-3.5-turbo" など
```

## トラブルシューティング

### URL検証が失敗する

- RenderのURLが正しく設定されているか確認
- `render.yaml`の設定が正しいか確認
- ログを確認してエラーをチェック

### ボットが応答しない

- Bot Token Scopesが正しく設定されているか確認
- Event Subscriptionsが有効になっているか確認
- チャンネルにボットを招待しているか確認

## ライセンス

MIT