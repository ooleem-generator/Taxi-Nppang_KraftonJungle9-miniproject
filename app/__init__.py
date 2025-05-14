# Flask 앱 팩토리 함수 (초기화) / Flask 앱을 모듈화하여 유지보수가 쉬워짐

from flask import Flask
from flask_pymongo import PyMongo
from flask_session import Session
from dotenv import load_dotenv
import os

mongo = PyMongo()  # MongoDB 연결 초기화


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object("app.config.Config")  # config.py 설정을 불러와 Flask에 적용

    mongo.init_app(app)
    Session(app)  # 세션을 파일 기반으로 설정

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp

    # auth, main 블루프린트를 앱에 등록 -> 라우팅 구조 분리

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
