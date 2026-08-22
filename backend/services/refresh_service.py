from database import SessionLocal
from services.news_service import get_latest_signals
from services.signal_service import save_signals


def run_signal_refresh():
    """
    執行完整 SignalBrief refresh pipeline：

    GDELT
    → filtering / ranking
    → Groq AI analysis
    → event filtering
    → deduplication
    → Top 3
    → PostgreSQL
    """

    # 執行完整新聞 pipeline，取得新的 Top 3
    signals = get_latest_signals()

    # 建立 database session
    db = SessionLocal()

    try:
        # 將新的 Top 3 寫入 PostgreSQL
        save_signals(db, signals)

        return signals

    finally:
        # 不論成功或失敗都關閉 DB session
        db.close()