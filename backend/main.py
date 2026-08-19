# ---------------------------------------------------------
# FastAPI application entry point
# ---------------------------------------------------------
# 這個檔案主要負責：
# 1. 建立 FastAPI application
# 2. 設定 CORS，讓 Vue frontend 可以呼叫 backend
# 3. 定義 API response 的資料格式（Pydantic models）
# 4. 定義 frontend 可以呼叫的 API endpoints
#
# 真正的新聞抓取與處理邏輯放在 services/news_service.py，
# main.py 只負責「接收 HTTP request → 呼叫 service → 回傳結果」。
# ---------------------------------------------------------

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from database import Base, engine, SessionLocal
import models

from services.news_service import (
    get_latest_signals,
    fetch_all_candidate_articles,
)

from services.signal_service import (
    save_signals,
    get_saved_signals,
)


# ---------------------------------------------------------
# Pydantic response model
# ---------------------------------------------------------
# Signal 定義一則最終 SignalBrief 新聞應該具備哪些欄位。
# ---------------------------------------------------------

class Signal(BaseModel):
    id: int
    title: str
    summary_points: list[str]

    # investment 是目前主要的大分類。
    # subcategory：
    # geopolitics / macro / ai_semiconductor / company_events
    category: str
    subcategory: str

    # 事件 → 受影響產業/公司 → 可能的市場影響
    impact_path: str

    # 由 AI / ranking logic 計算
    importance_score: float

    # Top 3 排名：
    # 1 / 2 / 3
    top_rank: int | None = None

    source_name: str
    source_url: str

    # 新聞發布時間
    published_at: datetime


# ---------------------------------------------------------
# /api/signals 最外層 response
# ---------------------------------------------------------
# updated_at：
# 這次 API response 的更新時間
#
# signals：
# 最終 SignalBrief Top 3
# ---------------------------------------------------------

class SignalResponse(BaseModel):
    updated_at: datetime
    signals: list[Signal]


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------
# models.py 已經定義 SignalModel。
#
# import models 後，
# SQLAlchemy 會把 table schema 註冊到 Base.metadata。
#
# create_all：
# 如果 PostgreSQL 裡 table 不存在，就建立。
# 已存在則不重複建立。
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# 建立 FastAPI application
# ---------------------------------------------------------

app = FastAPI()


# ---------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------
# 允許目前 local Vue frontend：
#
# http://localhost:5173
#
# 呼叫 FastAPI backend。
#
# 之後 frontend 部署後，
# 還會加入正式 frontend domain。
# ---------------------------------------------------------

FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------------------------------
# GET /api/signals
# ---------------------------------------------------------
# 功能：
# 從 PostgreSQL 讀取目前已儲存的 Top 3。
#
# 不會重新：
# - 呼叫 GDELT
# - 呼叫 Groq
# - 做 AI ranking
#
# 所以前端可以一直 refresh，
# 不會一直消耗 Groq API 額度。
#
# Flow：
#
# Frontend
#   ↓
# GET /api/signals
#   ↓
# PostgreSQL
#   ↓
# Top 3
# ---------------------------------------------------------

@app.get(
    "/api/signals",
    response_model=SignalResponse,
)
def get_signals():
    # 建立 database session
    db = SessionLocal()

    try:
        # 從 PostgreSQL 讀取 signals
        saved_signals = get_saved_signals(db)

        # -------------------------------------------------
        # SignalModel → API Signal format
        # -------------------------------------------------
        # Database 回傳的是 SQLAlchemy objects，
        # 這裡轉成 FastAPI response_model 需要的 dictionary。
        # -------------------------------------------------

        signals = [
            {
                "id": signal.id,
                "title": signal.title,

                # DB 目前存一個 summary 字串，
                # API schema 要 list[str]，
                # 所以包成 list。
                "summary_points": [
                    signal.summary
                ],

                "category": signal.category,
                "subcategory": signal.subcategory,

                "impact_path": signal.impact_path,

                "importance_score": signal.importance_score,
                "top_rank": signal.top_rank,

                "source_name": signal.source_name,
                "source_url": signal.source_url,

                "published_at": signal.published_at,
            }

            for signal in saved_signals
        ]

        return {
            "updated_at": datetime.utcnow(),
            "signals": signals,
        }

    finally:
        # 不管成功或失敗，
        # database session 都一定要關閉。
        db.close()


# ---------------------------------------------------------
# GDELT candidate inspection API
# ---------------------------------------------------------
# 開發 / debugging 用 endpoint。
#
# 功能：
# 1. 呼叫 GDELT
# 2. 最近 24 小時 filter
# 3. trusted source filter
# 4. URL dedup
# 5. category tagging
#
# 這裡回傳的是 candidate articles，
# 還不是最後的 SignalBrief Top 3。
# ---------------------------------------------------------

@app.get("/api/news/candidates")
def get_candidate_articles():
    articles = fetch_all_candidate_articles()

    return {
        "count": len(articles),
        "articles": articles,
    }


# ---------------------------------------------------------
# POST /api/signals/refresh
# ---------------------------------------------------------
# 手動觸發一次完整 SignalBrief 更新。
#
# Flow：
#
# GDELT
#   ↓
# 最近 24 小時
#   ↓
# trusted source filter
#   ↓
# rule ranking 粗篩
#   ↓
# Groq AI analysis
#   ↓
# event filtering
#   ↓
# event deduplication
#   ↓
# Top 3
#   ↓
# PostgreSQL
#
# 未來每天早上固定更新，
# 本質上就是定時執行這個 refresh logic。
# ---------------------------------------------------------

@app.post(
    "/api/signals/refresh",
    response_model=SignalResponse,
)
def refresh_signals():
    # 執行完整新聞 pipeline，
    # 取得新的 Top 3。
    signals = get_latest_signals()

    # 建立 database session
    db = SessionLocal()

    try:
        # 把新的 Top 3 寫進 PostgreSQL
        save_signals(
            db,
            signals,
        )

        # 同時把這次產生的 Top 3 回傳，
        # 方便 Swagger / Postman 測試。
        return {
            "updated_at": datetime.utcnow(),
            "signals": signals,
        }

    finally:
        # 不管成功或失敗都關閉 DB session
        db.close()