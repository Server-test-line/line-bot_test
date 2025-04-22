from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    TemplateMessage,
    ButtonsTemplate,
    PostbackAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    FollowEvent,
    PostbackEvent,
    TextMessageContent
)

import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 初始化 Firebase
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.environ["FIREBASE_PROJECT_ID"],
    "private_key": os.environ["FIREBASE_PRIVATE_KEY"].replace('\\n', '\n'),
    "client_email": os.environ["FIREBASE_CLIENT_EMAIL"]
})
firebase_admin.initialize_app(cred)

@app.route("/callback", methods=['POST'])##銜接webhook
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_text = event.message.text

    # 判斷是否為登入格式，例如：帳號:xxx 密碼:yyy
    if '帳號:' in user_text and '密碼:' in user_text:
        try:
            account = user_text.split('帳號:')[1].split(' 密碼:')[0].strip()
            password = user_text.split('密碼:')[1].strip()

            # 檢查 Firebase 資料庫中的帳號和密碼
            if check_user(account, password):
                reply_text = f"✅ 登入成功！歡迎 {account}"
            else:
                reply_text = "❌ 帳號或密碼錯誤，請再試一次！"

        except Exception as e:
            reply_text = f"⚠️ 發生錯誤：{str(e)}"
    else:
        reply_text = "請輸入：帳號:你的帳號 密碼:你的密碼"

    # 回覆訊息
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


#followevent 加入好友
@line_handler.add(FollowEvent)
def handle_follow(event):
    print(f'Got {event.type} event')

if __name__ == "__main__":
    app.run()
