from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

class Signal(BaseModel):
    id: int
    title: str
    summary_points: list[str]

    category: str
    subcategory: str

    impact_path: str
    importance_score: float
    top_rank: int | None = None

    source_name: str
    source_url: str
    published_at: datetime

class SignalResponse(BaseModel):
    updated_at: datetime
    signals: list[Signal]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/signals", response_model=SignalResponse)
def get_signals():
    return {
        "updated_at": "2026-08-12T08:00:00",
        "signals": [
            {
                "id": 1,
                "title": "AI 伺服器需求持續成長",
                "summary_points": [
                    "大型雲端業者持續增加 AI 基礎設施投資",
                    "GPU 與先進封裝需求維持強勁",
                    "台灣半導體供應鏈可能持續受惠"
                ],
                "category": "investment",
                "subcategory": "ai_semiconductor",
                "impact_path": "AI 資本支出增加 → GPU 與伺服器需求增加 → 半導體供應鏈受惠",
                "importance_score": 88.5,
                "top_rank": 1,
                "source_name": "Reuters",
                "source_url": "https://example.com/article-1",
                "published_at": "2026-08-12T08:30:00"
            },
            {
                "id": 2,
                "title": "市場持續關注利率政策",
                "summary_points": [
                    "投資人關注央行下一步利率決策",
                    "通膨數據仍是政策判斷的重要依據",
                    "利率預期可能影響科技股與成長股估值"
                ],
                "category": "investment",
                "subcategory": "macro",
                "impact_path": "利率預期改變 → 資金成本與估值調整 → 股票市場波動",
                "importance_score": 82.0,
                "top_rank": 2,
                "source_name": "Reuters",
                "source_url": "https://example.com/article-2",
                "published_at": "2026-08-12T07:45:00"
            }
        ]
    }
