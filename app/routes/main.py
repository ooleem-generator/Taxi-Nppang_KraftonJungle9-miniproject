# app/routes/main.py

from flask import Blueprint, render_template, request, redirect, session, url_for
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
from app.utils.decorators import login_required
from app.services.slack import send_dm
from app import mongo

main_bp = Blueprint("main", __name__)

# Mongo 연결
client = MongoClient("mongodb://admin9:taxiNppang11@localhost", 27017)
db = client.taxiNppang
ridepost_collection = db["RidePost"]
comment_collection = db["Comment"]
participation_collection = db["Participation"]


@main_bp.route("/login")
def login():
    return render_template("login.html")


# ─────────────────────────────────────
@main_bp.route("/")
def index():
    posts = list(ridepost_collection.find().sort("createdAt", -1))
    for post in posts:
        post["id"] = str(post["_id"])
        post["formatted_created"] = post["createdAt"].strftime("%Y-%m-%d %H:%M")
        post["formatted_departure"] = post["departureTime"].strftime("%H:%M")
        post["currentMembers"] = post.get("currentMembers", post.get("currentCount", 1))
        post["totalMembers"] = post.get("totalMembers", post.get("maxCount", 1))
    return render_template("index.html", ride_posts=posts)


# ─────────────────────────────────────
@main_bp.route("/posts", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("postContent")
    departure = request.form.get("departure")
    destination = request.form.get("destination")
    departure_time_str = request.form.get("departureTime")
    total_members = int(request.form.get("totalMembers", 1))

    now = datetime.now() + timedelta(hours=9)
    departure_time = datetime.strptime(departure_time_str, "%Y-%m-%dT%H:%M")
    user_id = session["user"]["id"]

    post = {
        "postContent": content,
        "departure": departure,
        "departureDetail": "",
        "destination": destination,
        "destinationDetail": "",
        "departureTime": departure_time,
        "totalMembers": total_members,
        "currentCount": 1,
        "status": "OPEN",
        "authorId": user_id,
        "authorName": session["user"]["name"],
        "createdAt": now,
        "statusHistory": [],
    }

    post_result = ridepost_collection.insert_one(post)
    post_id = post_result.inserted_id

    participation = {
        "postId": post_id,
        "userId": user_id,
        "status": "ACTIVE",
        "createdAt": now,
        "updatedAt": now,
    }
    participation_collection.insert_one(participation)

    user = mongo.db.users.find_one({"slack_id": user_id})
    if user and "access_token" in user:
        message = f"🚕 모집글이 등록되었습니다!\n출발지: {departure} → 도착지: {destination}\n출발 시간: {departure_time.strftime('%H:%M')}"
        send_dm(user_id, message)
    return redirect("/")


# ─────────────────────────────────────
@main_bp.route("/posts/<post_id>")
@login_required
def post_detail(post_id):
    try:
        post = ridepost_collection.find_one({"_id": ObjectId(post_id)})
    except Exception:
        return "잘못된 게시글 ID입니다.", 400

    if not post:
        return "해당 모집글을 찾을 수 없습니다.", 404

    # 유저 정보
    user_id = session["user"]["id"]

    # 참여 여부 체크 (userId는 문자열로 저장됨)
    is_participating = (
        participation_collection.find_one(
            {"postId": ObjectId(post_id), "userId": user_id, "status": "ACTIVE"}
        )
        is not None
    )

    # 글 작성자인지 확인
    is_author = post.get("authorId") == user_id

    # 참여자 목록
    participants_cursor = participation_collection.find(
        {"postId": ObjectId(post_id), "status": "ACTIVE"}
    )

    participants = []
    for p in participants_cursor:
        user = mongo.db.users.find_one({"slack_id": p["userId"]})
        if user:
            participants.append(
                {
                    "userName": user["userName"],
                    "userId": user["slack_id"],
                    "is_host": (user["slack_id"] == post["authorId"]),
                    "is_me": (user["slack_id"] == user_id),
                }
            )

    # 모집글 포맷
    post["id"] = str(post["_id"])
    post["created_at"] = post["createdAt"].strftime("%Y-%m-%d %H:%M")
    post["departure_time"] = post["departureTime"].strftime("%H:%M")
    post["description"] = post.get("postContent", "")
    post["departure_detail"] = post.get("departureDetail", "")
    post["destination_detail"] = post.get("destinationDetail", "")
    post["currentMembers"] = post.get("currentMembers", post.get("currentCount", 1))
    post["totalMembers"] = post.get("totalMembers", post.get("maxCount", 1))

    # 댓글 조회
    comments_cursor = comment_collection.find({"postId": ObjectId(post_id)}).sort(
        "createdAt"
    )
    comments = [
        {
            "author": c.get("authorName", "익명"),
            "createdAt": c["createdAt"].strftime("%Y-%m-%d %H:%M"),
            "commentContent": c["commentContent"],
        }
        for c in comments_cursor
    ]

    return render_template(
        "post_detail.html",
        post=post,
        comments=comments,
        participants=participants,
        is_participating=is_participating,
        is_author=is_author,
    )


# ─────────────────────────────────────
@main_bp.route("/comments", methods=["POST"])
@login_required
def submit_comment():
    post_id = request.form.get("post_id")
    comment_text = request.form.get("comment", "").strip()

    if not post_id or not comment_text:
        return "댓글 내용이 비어있거나 게시글 ID가 없습니다.", 400

    user = session.get("user", {})
    user_id = user.get("id")
    user_name = user.get("name", "익명")

    comment = {
        "commentContent": comment_text,
        "postId": ObjectId(post_id),
        "authorId": user_id,  # ← ObjectId로 저장하려면 DB 기준 맞춰야 함
        "authorName": user_name,
        "createdAt": datetime.utcnow() + timedelta(hours=9),
    }

    comment_collection.insert_one(comment)
    return redirect(f"/posts/{post_id}")


# ─────────────────────────────────────
@main_bp.route("/posts/<post_id>/participate", methods=["POST"])
@login_required
def participate(post_id):
    user_id = session.get("user", {}).get("id")

    # 참여자 ID가 ObjectId 형식이 아닌 경우 그냥 문자열로 처리
    # 또는 ObjectId로 변환하는 구조로 DB를 맞추세요
    try:
        post_oid = ObjectId(post_id)
    except Exception:
        return "잘못된 post_id", 400

    # 중복 참여 방지
    existing = participation_collection.find_one(
        {
            "postId": post_oid,
            "userId": user_id,  # ← 문자열로 저장했으면 문자열로 비교
            "status": "ACTIVE",
        }
    )

    if not existing:
        now = datetime.now() + timedelta(hours=9)

        participation = {
            "postId": post_oid,
            "userId": user_id,
            "status": "ACTIVE",
            "createdAt": now,
            "updatedAt": now,
        }

        post = ridepost_collection.find_one({"_id": post_oid})
        if post and post.get("currentMembers", 0) >= post.get("totalMembers", 2):
            return "정원이 초과되었습니다.", 400

        participation_collection.insert_one(participation)

        # 모집글의 currentMembers 필드 증가
        ridepost_collection.update_one(
            {"_id": post_oid}, {"$inc": {"currentMembers": 1}}
        )

    return redirect(f"/posts/{post_id}")


@main_bp.route("/posts/<post_id>/participate", methods=["DELETE"])
@login_required
def cancel_participation(post_id):
    user_id = session.get("user", {}).get("id")
    if not user_id:
        return "", 401

    try:
        post_oid = ObjectId(post_id)
    except Exception:
        return "잘못된 post_id입니다.", 400

    result = participation_collection.update_one(
        {
            "postId": post_oid,
            "userId": user_id,  # userId가 문자열이면 그대로 사용
            "status": "ACTIVE",
        },
        {
            "$set": {
                "status": "CANCELLED",
                "updatedAt": datetime.now() + timedelta(hours=9),
            }
        },
    )

    if result.modified_count > 0:
        ridepost_collection.update_one(
            {"_id": post_oid}, {"$inc": {"currentMembers": -1}}  # 필드명 통일
        )

    return redirect(f"/posts/{post_id}")


# ─────────────────────────────────────
@main_bp.route("/posts/<post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    user_id = session["user"]["id"]

    post = ridepost_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        return "해당 게시글이 없습니다.", 404

    # 작성자 본인만 삭제 가능
    if post.get("authorId") != user_id:
        return "삭제 권한이 없습니다.", 403

    # 게시글 삭제
    ridepost_collection.delete_one({"_id": ObjectId(post_id)})

    # 댓글 삭제
    comment_collection.delete_many({"postId": ObjectId(post_id)})

    # 참여 기록 삭제
    participation_collection.delete_many({"postId": ObjectId(post_id)})

    return redirect(url_for("main.index", msg="글이 삭제되었습니다."))
