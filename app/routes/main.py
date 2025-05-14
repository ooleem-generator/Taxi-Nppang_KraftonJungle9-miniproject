# app/routes/main.py

from flask import Blueprint, render_template, request, redirect, session
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
from app.utils.decorators import login_required
from app.services.slack import send_dm
from app import mongo

main_bp = Blueprint("main", __name__)

# Mongo 연결
client = MongoClient("mongodb://admin9:taxiNppang11@3.95.227.148", 27017)
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
        post["currentMembers"] = post["currentCount"]
        post["totalMembers"] = post["maxCount"]
    return render_template("index.html", ride_posts=posts)


# ─────────────────────────────────────
@main_bp.route("/posts", methods=["POST"])
@login_required
def create_post():
    title = request.form.get("title")
    content = request.form.get("postContent")
    departure = request.form.get("departure")
    destination = request.form.get("destination")
    departure_time_str = request.form.get("departureTime")
    max_count = int(request.form.get("totalMembers", 1))

    print("title:", title)
    print("content:", content)
    print("departure:", departure)
    print("destination:", destination)
    now = datetime.utcnow() + timedelta(hours=9)
    departure_time = datetime.strptime(departure_time_str, "%Y-%m-%dT%H:%M")

    user_id = session.get("user", {}).get("id")

    post = {
        "postTitle": title,
        "postContent": content,
        "departure": departure,
        "departureDetail": "",
        "destination": destination,
        "destinationDetail": "",
        "departureTime": departure_time,
        "maxCount": max_count,
        "currentCount": 1,
        "status": "OPEN",
        "authorId": user_id,
        "createdAt": now,
        "statusHistory": [],
    }

    ridepost_collection.insert_one(post)

    user = mongo.db.users.find_one({"slack_id": user_id})
    if user and "access_token" in user:
        message = f"🚕 모집글이 등록되었습니다!\n출발지: {departure} → 도착지: {destination}\n출발 시간: {departure_time.strftime('%H:%M')}"
        send_dm(user_id, message)
    return redirect("/")


# ─────────────────────────────────────
@main_bp.route("/posts/<post_id>")
@login_required
def post_detail(post_id):
    post = ridepost_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        return "해당 모집글을 찾을 수 없습니다.", 404

    post["id"] = str(post["_id"])
    post["created_at"] = post["createdAt"].strftime("%Y-%m-%d %H:%M")
    post["departure_time"] = post["departureTime"].strftime("%H:%M")
    post["currentMembers"] = post["currentCount"]
    post["totalMembers"] = post["maxCount"]
    post["description"] = post["postContent"]
    post["departure_detail"] = post.get("departureDetail", "")
    post["destination_detail"] = post.get("destinationDetail", "")

    formatted_created = post["createdAt"].strftime("%Y-%m-%d %H:%M")

    comments_cursor = comment_collection.find({"postId": ObjectId(post_id)}).sort(
        "createdAt"
    )
    comments = [
        {
            "author": "익명",
            "createdAt": c["createdAt"],
            "commentContent": c["commentContent"],
        }
        for c in comments_cursor
    ]

    return render_template("post_detail.html", post=post, comments=comments)


# ─────────────────────────────────────
@main_bp.route("/comments", methods=["POST"])
@login_required
def submit_comment():
    post_id = request.form.get("post_id")
    comment_text = request.form.get("comment")

    comment = {
        "commentContent": comment_text,
        "postId": ObjectId(post_id),
        "authorId": session.get("user", {}).get("id"),
        "createdAt": datetime.utcnow() + timedelta(hours=9),
    }

    comment_collection.insert_one(comment)
    return redirect(f"/posts/{post_id}")


# ─────────────────────────────────────
@main_bp.route("/posts/<post_id>/participate", methods=["POST"])
@login_required
def participate(post_id):
    user_id = session.get("user", {}).get("id")

    participation = {
        "postId": ObjectId(post_id),
        "userId": ObjectId(user_id),
        "status": "ACTIVE",
        "createdAt": datetime.utcnow() + timedelta(hours=9),
        "updatedAt": datetime.utcnow() + timedelta(hours=9),
    }

    # 이미 참여한 적이 있는지 확인 후 중복 참여 방지
    exists = participation_collection.find_one(
        {"postId": ObjectId(post_id), "userId": ObjectId(user_id), "status": "ACTIVE"}
    )

    if not exists:
        participation_collection.insert_one(participation)
        # 모집글 참여자 수 증가
        ridepost_collection.update_one(
            {"_id": ObjectId(post_id)}, {"$inc": {"currentCount": 1}}
        )

    return redirect(f"/posts/{post_id}")


# @main_bp.route('/posts/<post_id>/participate', methods=['DELETE'])
# def cancel_participation(post_id):
#     user_id = session.get("user", {}).get("id")
#     if not user_id:
#         return '', 401

#     result = participation_collection.update_one(
#         {
#             "postId": ObjectId(post_id),
#             "userId": ObjectId(user_id),
#             "status": "ACTIVE"
#         },
#         {
#             "$set": {
#                 "status": "CANCELLED",
#                 "updatedAt": datetime.utcnow() + timedelta(hours=9)
#             }
#         }
#     )

#     if result.modified_count > 0:
#         ridepost_collection.update_one(
#             {"_id": ObjectId(post_id)},
#             {"$inc": {"currentCount": -1}}
#         )

#     return redirect(f'/posts/{post_id}')
