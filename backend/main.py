

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

from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.news_service import (
    get_latest_signals,
    fetch_all_candidate_articles,
)


# ---------------------------------------------------------
# Pydantic response model
# ---------------------------------------------------------
# Signal 定義一則最終 SignalBrief 新聞應該具備哪些欄位。

class Signal(BaseModel):
    id: int
    title: str
    summary_points: list[str]

    # investment 是目前主要的大分類。
    # subcategory 則是：
    # geopolitics / macro / ai_semiconductor / company_events
    category: str
    subcategory: str

    # impact_path 用來說明：
    # 「事件 → 產業影響 → 可能的市場影響」
    impact_path: str

    # 後續會由 SignalBrief 的 ranking logic 計算。
    importance_score: float

    # 如果這則 Signal 最後進入 Top 3，
    # 會是 1 / 2 / 3。
    # 如果沒有進 Top 3，則允許為 None。
    top_rank: int | None = None

    source_name: str
    source_url: str

    # 使用 datetime，而不是單純字串，
    # 因為後面需要做：
    # - 最近 24 小時過濾
    # - 時間排序
    # - 事件去重時比較時間差
    published_at: datetime


# ---------------------------------------------------------
# /api/signals 的最外層 response
# ---------------------------------------------------------
# updated_at：
# 告訴 frontend 這批 SignalBrief 是什麼時間更新的。
#
# signals：
# 最終整理後的新聞清單。
# ---------------------------------------------------------

class SignalResponse(BaseModel):
    updated_at: datetime
    signals: list[Signal]


# ---------------------------------------------------------
# 建立 FastAPI application
# ---------------------------------------------------------

app = FastAPI()


# ---------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Final SignalBrief API
# ---------------------------------------------------------
# 這個 endpoint 是 frontend 真正應該使用的 API。
#
# 現階段：
#   → 呼叫 GDELT，回傳 trusted source 新聞
#
# 之後你可以自己接：
#   → database / AWS / LLM
# ---------------------------------------------------------

@app.get("/api/signals", response_model=SignalResponse)
def get_signals():
    signals = get_latest_signals()

    return {
        "updated_at": datetime.utcnow(),
        "signals": signals,
    }


# ---------------------------------------------------------
# GDELT candidate inspection API
# ---------------------------------------------------------
# 1. 打 1 次 GDELT
# 2. 只保留 trusted sources
# 3. 本地標 category
# 4. 回傳尚未做 event dedup / ranking 的候選新聞
# ---------------------------------------------------------

@app.get("/api/news/candidates")
def get_candidate_articles():
    articles = fetch_all_candidate_articles()

    return {
        "count": len(articles),
        "articles": articles,
    }