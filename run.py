# 앱 실행 스크립트

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        ssl_context=("ssl/cert.pem", "ssl/key.pem"),
        debug=True,
    )
