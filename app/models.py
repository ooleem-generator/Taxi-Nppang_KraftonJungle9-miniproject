from mongoengine import Document, StringField, DateTimeField, IntField, ListField, ReferenceField
from datetime import datetime

# 사용자
class User(Document):
    email = StringField(required=True, unique=True)
    userName = StringField(required=True)
    createdAt = DateTimeField(default=datetime.now)
    deleted = StringField(default="N")

# 모집글
class RidePost(Document):
    postTitle = StringField(required=True)
    postContent = StringField(required=True)
    departure = StringField(required=True)
    departureDetail = StringField()
    destination = StringField(required=True)
    destinationDetail = StringField()
    departureTime = DateTimeField(required=True)
    totalMembers = IntField(required=True, min_value=2, max_value=4)
    currentMembers = IntField(default=1)
    status = StringField(default="OPEN", choices=["OPEN", "FULL", "SETTLED"])
    authorId = ReferenceField(User, required=True)
    createdAt = DateTimeField(default=datetime.now)
    statusHistory = ListField()

# 댓글
class Comment(Document):
    commentContent = StringField(required=True)
    postId = ReferenceField(RidePost, required=True)
    authorId = ReferenceField(User, required=True)
    createdAt = DateTimeField(default=datetime.now)

# 참여
class Participation(Document):
    postId = ReferenceField(RidePost, required=True)
    userId = ReferenceField(User, required=True)
    status = StringField(default="ACTIVE", choices=["ACTIVE", "CANCELLED"])
    createdAt = DateTimeField(default=datetime.now)
    updatedAt = DateTimeField(default=datetime.now)