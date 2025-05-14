from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
import certifi
import ssl
import urllib3

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# 🔽 인증서 우회용 context 설정
ssl_context = ssl.create_default_context(cafile=certifi.where())

client = WebClient(token=SLACK_BOT_TOKEN, ssl=ssl_context)


def send_dm(user_id, message):
    try:
        response = client.conversations_open(users=user_id)
        channel_id = response["channel"]["id"]
        client.chat_postMessage(channel=channel_id, text=message)
        print(f"✅ 메세지 전송 성공: {user_id}")
    except SlackApiError as e:
        print(f"⚠️ Slack API 에러: {e.response['error']}")
    except Exception as e:
        print(f"❌ 기타 에러 발생: {e}")
