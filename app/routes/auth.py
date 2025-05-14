# 슬랙 로그인 관련 라우트
from flask import Blueprint, redirect, request, session, url_for
import requests
from app import mongo
import os
from datetime import datetime

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
# SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")


@auth_bp.route("/slack/login")
def login():
    return redirect(
        f"https://taxinppang-jungle.slack.com/oauth/v2/authorize?client_id={SLACK_CLIENT_ID}"
        f"&user_scope=identity.basic,identity.email,identity.avatar,identity.team"
        f"&redirect_uri=https://taxinppang-kraftonjungle9.shop/auth/slack/callback"
    )


# 사용자를 슬랙 로그인 페이지로 리디렉션, 슬랙 로그인 후 권한 요청(scope=identity.*)


@auth_bp.route("/slack/callback")
def callback():
    code = request.args.get("code")
    token_res = requests.post(
        "https://taxinppang-jungle.slack.com/api/oauth.v2.access",
        data={
            "client_id": SLACK_CLIENT_ID,
            "client_secret": SLACK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": "https://taxinppang-kraftonjungle9.shop/auth/slack/callback",
        },
    ).json()

    if not token_res.get("ok"):
        return "Slack login failed", 400

    authed_user = token_res["authed_user"]
    user_id = authed_user["id"]
    access_token = authed_user["access_token"]

    # 🔽 사용자 이름을 Slack users.identity API로 요청
    user_info_res = requests.get(
        "https://slack.com/api/users.email",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    if not user_info_res.get("ok"):
        return "Failed to fetch user info", 400

    user_name = user_info_res["user"]["name"]
    user_email = user_info_res["user"]["email"]

    # MongoDB에 사용자 정보 저장
    mongo.db.users.update_one(
        {"slack_id": user_id},
        {
            "$set": {
                "access_token": access_token,
                "email": user_email,
                "userName": user_name,
                "createdAt": datetime.now(),
                "deleted": "N",
            }
        },
        upsert=True,
    )

    session["user"] = {
        "id": user_id,
        "name": user_name,
    }

    return redirect(url_for("main.index"))


# 로그인 성공 시 슬랙이 code를 넘겨줌, 그 코드를 슬랙 API에 보내 access_token을 받음, 해당 사용자 정보를 MongoDB에 저장하거나 갱신
# flask 세션에 슬랙 사용자 ID를 저장 -> 로그인 유지
