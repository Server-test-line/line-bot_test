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
    ConfirmTemplate,
    ButtonsTemplate,
    CarouselTemplate,
    CarouselColumn,
    ImageCarouselColumn,
    ImageCarouselTemplate,
    MessageAction,
    URIAction,
    PostbackAction,
    DatetimePickerAction,
    FlexMessage,
    FlexImage,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexIcon,
    FlexButton,
    FlexSeparator,
    FlexContainer,
    PushMessageRequest
)
from linebot.v3.webhooks import (
    MessageEvent,
    FollowEvent,
    PostbackEvent,
    TextMessageContent
)
import json
import os

app = Flask(__name__)

user_states = {}

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))


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

@app.route("/callback_login", methods=['POST'])
def callback_login():
    data = request.get_json()
    print(f"⚠️ 收到的資料：{data}")
    user_id = data.get("userId")
    login_success = data.get("loginSuccess")
    error_message = data.get("errorMessage")  # 假設伺服器回傳的錯誤訊息

    if not user_id:
        print("⚠️ 錯誤：未提供 userId")
        return "Missing userId", 400

    configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))

    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)

            if login_success:
                user_states[user_id] = user_states.get(user_id, {})
                user_states[user_id]["login_success"] = True
                user_states[user_id]["step"] = 1
            else:
                # 登入失敗情況
                user_states[user_id] = user_states.get(user_id, {})
                user_states[user_id]["login_success"] = False
                user_states[user_id]["step"] = 0

                # 根據伺服器回傳的錯誤訊息處理
                if error_message:
                    error_text = f"❌ 登入失敗，原因：{error_message}"
                else:
                    error_text = "❌ 登入失敗，請重新登入會員"

                response = line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=error_text)]
                    )
                )
                print(f"✅ 已推送登入失敗通知給 {user_id}")
                print(f"✅ Line API 回傳：{response}")

    except Exception as e:
        print(f"❌ 通知推送失敗：{str(e)}")
        if hasattr(e, 'status'):
            print(f"HTTP Status: {e.status}")
        if hasattr(e, 'body'):
            print(f"Response body: {e.body}")

    return "OK"


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id  # 取得 user ID
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        # 如果沒有記錄過這個使用者，建立初始狀態
        if user_id not in user_states:
            user_states[user_id] = {"step": 0}
        
        step = user_states[user_id]["step"]

        if '報修' in text:
            user_states[user_id]["step"] = 1
            login_json = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "text",
                        "text": "請點選進入會員登入",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center"
                    }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {
                        "type": "uri",
                        "label": "登入",
                        "uri": f"https://line-login-site.vercel.app/?userId={user_id}" #加入userid
                        },
                        "position": "relative",
                        "color": "#46A3FF",
                        "margin": "none"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [],
                        "margin": "sm"
                    }
                    ],
                    "flex": 0
                }
                }
            login_json_str = json.dumps(login_json)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[FlexMessage(alt_text='會員登入', contents = FlexContainer.from_json(login_json_str))]
                )
            )
            
        elif step == 1:
            if user_states.get(user_id, {}).get('login_success', False):
                # 使用者登入會員 → 回傳 shipTemplate，請他選擇送修方式
                ship_template = ButtonsTemplate(
                    title='送修方式',
                    text='想要如何送修？',
                    actions=[
                        MessageAction(label='百貨專櫃', text='送至百貨專櫃'),
                        MessageAction(label='到府收貨', text='請人員到府收貨'),
                        MessageAction(label='自行送修', text='自行送修'),
                    ]
                )
                template_message = TemplateMessage(
                    alt_text='如何送修',
                    template=ship_template
                )
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[template_message]
                    )
                )
                user_states[user_id]["step"] = 2

            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text='請重新登入會員')]
                    )
                )
                user_states[user_id]["step"] = 0
        
        elif step == 2:
            if '百貨' in text:
                ship_template = ButtonsTemplate(
                title='百貨專櫃',
                text='分店資訊',
                actions=[
                    MessageAction(label='SOGO天母店', text='臺北SOGO天母店'),
                    MessageAction(label='SOGO忠孝店', text='臺北SOGO忠孝店'),
                    MessageAction(label='遠東信義A13', text='臺北遠東信義A13'),
                    MessageAction(label='SOGO高雄店', text='高雄SOGO高雄店')
                    ]
                )
                template_message = TemplateMessage(
                    alt_text='選擇分店',
                    template=ship_template
                )
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[template_message]
                    )
                )
                user_states[user_id]["step"] = 3

            elif '到府' in text:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text='請留下收貨地址')]
                    )
                )
                user_states[user_id]["step"] = 0

            elif '自行' in text:
                company_json = {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": "https://lh3.googleusercontent.com/p/AF1QipO2Hi7c9QwKi3RdWAqgKX_fDT3fEdxIJ5Ei1mnh=w408-h272-k-no",
                        "size": "full",
                        "aspectRatio": "20:13",
                        "aspectMode": "cover",
                        "action": {
                        "type": "uri",
                        "uri": "https://line.me/"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "飛騰家電",
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "margin": "md",
                            "contents": []
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "spacing": "sm",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Place",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "台北市大同區承德路三段285號1F",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Time",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "平日10:30–21:00",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "MAP",
                            "uri": "https://maps.app.goo.gl/AcjfZTvofCGdmFPg6"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "margin": "sm"
                        }
                        ],
                        "flex": 0
                    }
                }
                company_json_str = json.dumps(company_json)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[FlexMessage(alt_text='總公司資訊', contents = FlexContainer.from_json(company_json_str))]
                    )
                )
                user_states[user_id]["step"] = 0

        elif step == 3:
            if '天母' in text:
                shop_json = {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": "https://www.vastar.com.tw/imagess/1021092923_19027BC02p1.jpg",
                        "size": "full",
                        "aspectRatio": "20:13",
                        "aspectMode": "cover",
                        "action": {
                        "type": "uri",
                        "uri": "https://line.me/"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "臺北SOGO天母店",
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "margin": "md",
                            "contents": []
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "spacing": "sm",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Place",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "台北市士林區中山北路六段77號",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Time",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "11:00 - 21:30",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "MAP",
                            "uri": "https://maps.app.goo.gl/GYzP9e3gkVPAoUqs9"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "margin": "sm"
                        }
                        ],
                        "flex": 0
                    }
                }
                shop_json_str = json.dumps(shop_json)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[FlexMessage(alt_text='專櫃資訊', contents = FlexContainer.from_json(shop_json_str))]
                    )
                )
                user_states[user_id]["step"] = 0
            elif '忠孝' in text:
                shop_json = {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": "https://www.vastar.com.tw/imagess/1021092923_19567E8AFp1.jpg",
                        "size": "full",
                        "aspectRatio": "20:13",
                        "aspectMode": "cover",
                        "action": {
                        "type": "uri",
                        "uri": "https://line.me/"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "臺北SOGO忠孝店",
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "margin": "md",
                            "contents": []
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "spacing": "sm",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Place",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "台北市大安區忠孝東路四段45號",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Time",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "11:00 - 21:30",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "MAP",
                            "uri": "https://maps.app.goo.gl/3vfDt1oHGisKaYg57"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "margin": "sm"
                        }
                        ],
                        "flex": 0
                    }
                    }
                shop_json_str = json.dumps(shop_json)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[FlexMessage(alt_text='專櫃資訊', contents = FlexContainer.from_json(shop_json_str))]
                    )
                )
                user_states[user_id]["step"] = 0
            elif '信義' in text:
                shop_json = {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": "https://www.vastar.com.tw/imagess/1023081221_38397C2ACp1.jpg",
                        "size": "full",
                        "aspectRatio": "20:13",
                        "aspectMode": "cover",
                        "action": {
                        "type": "uri",
                        "uri": "https://line.me/"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "臺北遠東信義A13 8F",
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "margin": "md",
                            "contents": []
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "spacing": "sm",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Place",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "台北市信義區松仁路58號",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Time",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "11:00 - 21:30",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "MAP",
                            "uri": "https://maps.app.goo.gl/dBSTW8FwKgjjD3cC6"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "margin": "sm"
                        }
                        ],
                        "flex": 0
                    }
                }
                shop_json_str = json.dumps(shop_json)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[FlexMessage(alt_text='專櫃資訊', contents = FlexContainer.from_json(shop_json_str))]
                    )
                )
                user_states[user_id]["step"] = 0
            elif '高雄' in text:
                shop_json = {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": "https://www.vastar.com.tw/imagess/1021092923_21011259Ap1.jpg",
                        "size": "full",
                        "aspectRatio": "20:13",
                        "aspectMode": "cover",
                        "action": {
                        "type": "uri",
                        "uri": "https://line.me/"
                        }
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                        {
                            "type": "text",
                            "text": "高雄SOGO高雄店",
                            "weight": "bold",
                            "size": "xl"
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "margin": "md",
                            "contents": []
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "spacing": "sm",
                            "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Place",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "高雄市前鎮區三多三路217號",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                {
                                    "type": "text",
                                    "text": "Time",
                                    "color": "#aaaaaa",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": "11:00 - 21:30",
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 5
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                            "type": "uri",
                            "label": "MAP",
                            "uri": "https://maps.app.goo.gl/8G87HxKe3eLiuikRA"
                            }
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [],
                            "margin": "sm"
                        }
                        ],
                        "flex": 0
                    }
                }
                shop_json_str = json.dumps(shop_json)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[FlexMessage(alt_text='專櫃資訊', contents = FlexContainer.from_json(shop_json_str))]
                    )
                )
                user_states[user_id]["step"] = 0

        if '查詢' in text:
            user_states[user_id]["step"] = 4
            confirm_template = ConfirmTemplate(
                text = '是否有會員？',
                actions = [
                    MessageAction(label = 'Yes' , text = '是'),
                    MessageAction(label = 'No' , text = '否'),
                ]
            )
            template_message = TemplateMessage(
                alt_text = '請先登入會員',
                template = confirm_template
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[template_message]
                )
            )
        elif step == 4:
            if '是' in text:
                # 登入後列出維修資料
                
                user_states[user_id]["step"] = 5

            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text='請重新登入會員')]
                    )
                )
                user_states[user_id]["step"] = 0

        if '登入' in text:
            user_states[user_id]["step"] = 5
            confirm_template = ConfirmTemplate(
                text = '是否有會員？',
                actions = [
                    MessageAction(label = 'Yes' , text = '是'),
                    MessageAction(label = 'No' , text = '否'),
                ]
            )
            template_message = TemplateMessage(
                alt_text = '請先登入會員',
                template = confirm_template
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[template_message]
                )
            )
        elif step == 5:
            if '是' in text:
                # 登入功能
                
                user_states[user_id]["step"] = 6

            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text='請重新登入會員')]
                    )
                )
                user_states[user_id]["step"] = 0
        
#followevent 加入好友
@line_handler.add(FollowEvent)
def handle_follow(event):
    print(f'Got {event.type} event')



if __name__ == "__main__":
    app.run()
