# app/routes/main.py

from flask import Blueprint, render_template, request, redirect, session
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId

main_bp = Blueprint("main", __name__)

# Mongo 연결
client = MongoClient("localhost", 27017)
db = client.taxi_nppang
ridepost_collection = db["RidePost"]
comment_collection = db["Comment"]
participation_collection = db["Participation"]


@main_bp.route("/login")
def login():
    return render_template("login.html")


# ─────────────────────────────────────
@main_bp.route("/posts")
def get_posts():
    posts = list(ridepost_collection.find().sort("createdAt", -1))
    for post in posts:
        post["id"] = str(post["_id"])
        post["created_at"] = post["createdAt"].strftime("%Y-%m-%d %H:%M")
        post["current_members"] = post["currentCount"]
        post["total_members"] = post["maxCount"]
        post["departure_time"] = post["departureTime"].strftime("%H:%M")
    return render_template("index.html", posts=posts)


# ─────────────────────────────────────
@main_bp.route("/posts", methods=["POST"])
def create_post():
    title = request.form.get("title")
    content = request.form.get("description")
    departure = request.form.get("departure")
    destination = request.form.get("destination")
    departure_time_str = request.form.get("time")
    max_count = int(request.form.get("members", 1))

    now = datetime.utcnow() + timedelta(hours=9)
    departure_time = datetime(
        now.year,
        now.month,
        now.day,
        int(departure_time_str.split(":")[0]),
        int(departure_time_str.split(":")[1]),
    )

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
        "authorId": session.get("user", {}).get("id"),
        "createdAt": now,
        "statusHistory": [],
    }

    ridepost_collection.insert_one(post)
    return redirect("/")


# ─────────────────────────────────────
@main_bp.route("/posts/<post_id>")
def post_detail(post_id):
    post = ridepost_collection.find_one({"_id": ObjectId(post_id)})
    if not post:
        return "해당 모집글을 찾을 수 없습니다.", 404

    post["id"] = str(post["_id"])
    post["created_at"] = post["createdAt"].strftime("%Y-%m-%d %H:%M")
    post["departure_time"] = post["departureTime"].strftime("%H:%M")
    post["current_members"] = post["currentCount"]
    post["total_members"] = post["maxCount"]
    post["description"] = post["postContent"]
    post["departure_detail"] = post.get("departureDetail", "")
    post["destination_detail"] = post.get("destinationDetail", "")

    comments_cursor = comment_collection.find({"postId": ObjectId(post_id)}).sort(
        "createdAt"
    )
    comments = [
        {
            "author": "익명",
            "text": c["commentContent"],
            "created_at": c["createdAt"].strftime("%Y-%m-%d %H:%M"),
        }
        for c in comments_cursor
    ]

    return render_template("post_detail.html", post=post, comments=comments)


# ─────────────────────────────────────
@main_bp.route("/comments", methods=["POST"])
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
    return redirect(f"/post/{post_id}")


# ─────────────────────────────────────
#  참여 취소 가능 기능 -> 테스트 필요

# @main_bp.route('/posts/<post_id>/participate', methods=['DELETE'])
# def join_post():
#     post_id = request.form.get('post_id')
#     user_id = session.get("user", {}).get("id")

#     if not user_id:
#         return redirect('/auth/slack/login')

#     participation = {
#         "postId": ObjectId(post_id),
#         "userId": user_id,
#         "status": "ACTIVE",
#         "createdAt": datetime.utcnow() + timedelta(hours=9),
#         "updatedAt": datetime.utcnow() + timedelta(hours=9)
#     }

#     participation_collection.insert_one(participation)

#     ridepost_collection.update_one(
#         {"_id": ObjectId(post_id)},
#         {"$inc": {"currentCount": 1}}
#     )

#     return redirect(f'/post/{post_id}')
