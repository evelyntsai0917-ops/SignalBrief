# ---------------------------------------------------------
# SignalBrief signal persistence service
# ---------------------------------------------------------
# 這個 module 負責：
# 1. 把 AI 產生的 Top 3 signals 存進 PostgreSQL
# 2. 從 PostgreSQL 讀取最新 signals
# ---------------------------------------------------------

from sqlalchemy.orm import Session

from models import SignalModel


# ---------------------------------------------------------
# Save signals
# ---------------------------------------------------------

def save_signals(
    db: Session,
    signals: list[dict],
) -> None:

    for signal in signals:
        existing_signal = (
            db.query(SignalModel)
            .filter(
                SignalModel.source_url
                == signal["source_url"]
            )
            .first()
        )

        # 如果同一篇新聞已經存在，就不要重複存
        if existing_signal:
            continue

        db_signal = SignalModel(
            title=signal["title"],
            category=signal["category"],
            subcategory=signal["subcategory"],
            summary=signal["summary_points"][0],
            impact_path=signal["impact_path"],
            importance_score=signal["importance_score"],
            top_rank=signal["top_rank"],
            source_name=signal["source_name"],
            source_url=signal["source_url"],
            published_at=signal["published_at"],
        )

        db.add(db_signal)

    # 把新增的資料真正寫進 PostgreSQL
    db.commit()


# ---------------------------------------------------------
# Get saved signals
# ---------------------------------------------------------

def get_saved_signals(
    db: Session,
) -> list[SignalModel]:

    return (
        db.query(SignalModel)
        .order_by(
            SignalModel.created_at.desc(),
            SignalModel.top_rank.asc(),
        )
        .limit(3)
        .all()
    )