"""
Slack AI Chatbot using OpenAI API
Render経由でデプロイ可能なSlackボットアプリケーション
"""
import os
import logging
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from openai import OpenAI
from dotenv import load_dotenv
import json

# 環境変数の読み込み
load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPIアプリの初期化
app = FastAPI()

# 環境変数から設定を取得
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# クライアントの初期化
slack_client = WebClient(token=SLACK_BOT_TOKEN)
# OpenAIクライアントの初期化（proxies引数を明示的に除外）
openai_client = OpenAI(api_key=OPENAI_API_KEY)
signature_verifier = SignatureVerifier(signing_secret=SLACK_SIGNING_SECRET)

# 設定の検証
if not all([SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, OPENAI_API_KEY]):
    logger.warning("必要な環境変数が設定されていません。本番環境ではエラーになります。")


@app.get("/")
async def root():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok", "message": "Slack AI Chatbot is running"}


@app.post("/slack/events")
async def slack_events(request: Request):
    """
    Slackイベントを受け取るエンドポイント
    URL Verificationとメッセージイベントを処理
    """
    try:
        logger.info("Slackイベントを受信しました")
        body = await request.body()
        body_str = body.decode('utf-8')
        logger.info(f"リクエストボディ: {body_str[:200]}...")
        
        # ヘッダーから署名情報を取得
        x_slack_signature = request.headers.get("X-Slack-Signature")
        x_slack_request_timestamp = request.headers.get("X-Slack-Request-Timestamp")
        
        logger.info(f"署名ヘッダー - Signature: {x_slack_signature}, Timestamp: {x_slack_request_timestamp}")
        
        # まずデータをパースしてURL検証かどうかを確認
        try:
            data = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        logger.info(f"イベントタイプ: {data.get('type')}")
        
        # URL Verification（Slackアプリの設定時に必要）
        # URL検証の場合は署名検証をスキップ
        if data.get("type") == "url_verification":
            logger.info("URL Verificationリクエストを受信")
            challenge = data.get("challenge")
            if challenge:
                return JSONResponse(content={"challenge": challenge})
            else:
                logger.error("challengeが見つかりません")
                raise HTTPException(status_code=400, detail="Missing challenge")
        
        # URL検証以外の場合は署名検証を実行
        if x_slack_signature and x_slack_request_timestamp:
            if not signature_verifier.is_valid(body, x_slack_signature, x_slack_request_timestamp):
                logger.warning("無効な署名")
                raise HTTPException(status_code=401, detail="Invalid signature")
            logger.info("署名検証成功")
        else:
            logger.warning(f"署名ヘッダーがありません - Signature: {x_slack_signature}, Timestamp: {x_slack_request_timestamp}")
        
        # イベントの処理
        if data.get("type") == "event_callback":
            event = data.get("event", {})
            logger.info(f"イベントタイプ: {event.get('type')}, チャンネル: {event.get('channel')}")
            
            # ボット自身のメッセージは無視
            if event.get("bot_id"):
                logger.info("ボット自身のメッセージを無視")
                return JSONResponse(content={"status": "ok"})
            
            # メンションのみを処理（メンションされた時だけOpenAI APIを呼び出す）
            if event.get("type") == "app_mention":
                logger.info("メンションイベントを処理します")
                await handle_message(event)
            else:
                logger.info(f"メンション以外のイベント: {event.get('type')}")
        
        return JSONResponse(content={"status": "ok"})
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}", exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


async def handle_message(event: dict):
    """
    メッセージイベントを処理し、OpenAI APIを呼び出してSlackに返信
    スレッドで返信する
    """
    try:
        channel = event.get("channel")
        text = event.get("text", "")
        user = event.get("user")
        ts = event.get("ts")  # 元のメッセージのタイムスタンプ
        
        # メンションの場合はメンション部分を削除
        if event.get("type") == "app_mention":
            # <@U123456> のようなメンションを削除
            import re
            text = re.sub(r'<@[^>]+>', '', text).strip()
        
        if not text:
            return
        
        logger.info(f"メッセージを受信: {text[:100]}...")
        
        # OpenAI APIを呼び出し
        response_text = await call_openai(text, user)
        
        # Slackにスレッドで返信
        slack_client.chat_postMessage(
            channel=channel,
            text=response_text,
            thread_ts=ts  # 元のメッセージのタイムスタンプを指定してスレッド返信
        )
        
        logger.info("スレッドで返信を送信しました")
    
    except SlackApiError as e:
        logger.error(f"Slack API エラー: {e.response['error']}")
    except Exception as e:
        logger.error(f"メッセージ処理エラー: {str(e)}")


async def call_openai(user_message: str, user_id: Optional[str] = None) -> str:
    """
    OpenAI APIを呼び出してレスポンスを取得
    """
    try:
        # システムプロンプト（必要に応じてカスタマイズ）
        system_prompt = "あなたは親切で知識豊富なアシスタントです。日本語で丁寧に回答してください。"
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # または "gpt-4", "gpt-3.5-turbo" など
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"OpenAI API エラー: {str(e)}")
        return "申し訳ございませんが、エラーが発生しました。しばらくしてから再度お試しください。"


@app.post("/slack/commands")
async def slack_commands(request: Request):
    """
    Slack Slash Commandsを受け取るエンドポイント（オプション）
    """
    try:
        form_data = await request.form()
        command = form_data.get("command")
        text = form_data.get("text", "")
        channel_id = form_data.get("channel_id")
        user_id = form_data.get("user_id")
        
        logger.info(f"コマンドを受信: {command} - {text}")
        
        # OpenAI APIを呼び出し
        response_text = await call_openai(text, user_id)
        
        # Slackに返信
        slack_client.chat_postMessage(
            channel=channel_id,
            text=response_text
        )
        
        return JSONResponse(content={"response_type": "in_channel", "text": response_text})
    
    except Exception as e:
        logger.error(f"コマンド処理エラー: {str(e)}")
        return JSONResponse(
            content={"response_type": "ephemeral", "text": "エラーが発生しました。"},
            status_code=500
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

