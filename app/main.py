from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import builtins
from dotenv import load_dotenv

# 1. .env 파일을 먼저 로드합니다.
load_dotenv()

# 2. mysql_connection.py가 기대하는 변수들을 내장(builtins) 영역에 주입합니다.
builtins.user = os.getenv("MYSQL_USER")
builtins.passwd = os.getenv("MYSQL_PASSWORD")
builtins.host = os.getenv("MYSQL_HOST")
builtins.port = os.getenv("MYSQL_PORT")
builtins.db = os.getenv("MYSQL_DB")

from app.user.user_router import user
# 새롭게 작성한 review_router를 가져옵니다.
from app.review.review_router import router as review_router
from app.config import PORT

app = FastAPI()
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# 기존 유저 API 등록
app.include_router(user)
# 전처리 자동화 API 등록
app.include_router(review_router)

if __name__=="__main__":
    # "main:app"을 "app.main:app"으로 수정함...
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)