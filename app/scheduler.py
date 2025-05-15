from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from pymongo import MongoClient
from app.services.slack import send_dm


def check_departure_and_notify():

    from app import mongo

    client = MongoClient("mongodb://admin9:taxiNppang11@localhost", 27017)
    db = client.taxiNppang
    ridepost_collection = db["RidePost"]
    participation_collection = db["Participation"]

    now = datetime.utcnow() + timedelta(hours=9)
    soon = now + timedelta(minutes=5)

    print(f"🔍 now: {now}, soon: {soon}")

    posts = ridepost_collection.find(
        {
            "departureTime": {"$gte": now, "$lte": soon},
            "status": "OPEN",
            "impendingNotified": {"$ne": True},
        }
    )

    for post in posts:
        print(f"✅ 알림 대상 모집글: {post['_id']} - {post['departureTime']}")
        participants = participation_collection.find(
            {"postId": post["_id"], "status": "ACTIVE"}
        )

        for participant in participants:
            print(f"🧑 참여자: {participant['userId']}")
            user = mongo.db.users.find_one({"slack_id": participant["userId"]})
            print(f"🔎 사용자 DB 정보: {user}")
            if user and "access_token" in user:
                try:
                    msg = f"🚕 참여하신 모집글의 출발 시간이 임박했습니다!\n출발지: {post['departure']}\n출발 시간: {post['departureTime'].strftime('%H:%M')}\n지금 출발지로 모여주세요!"
                    send_dm(participant["userId"], msg)
                except Exception as e:
                    print(f"❗ DM 전송 실패 ({participant['userId']}): {e}")

        ridepost_collection.update_one(
            {"_id": post["_id"]}, {"$set": {"notified": True}}
        )


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_departure_and_notify, "interval", minutes=1)
    scheduler.start()
