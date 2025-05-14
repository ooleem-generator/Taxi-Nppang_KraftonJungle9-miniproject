# DM 보내기 유틸 함수

import requests


def send_slack_dm(token, user_id, text):
    res = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": user_id, "text": text},
    )
    return res.json()


# Bearer 토큰과 함께 chat.postMessage 엔드포인트에 메세지 전송, 슬랙 OAuth에서 받은 액세스 토큰이 필요
