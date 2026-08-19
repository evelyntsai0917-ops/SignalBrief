# ---------------------------------------------------------
# SignalBrief signal persistence service
# ---------------------------------------------------------
# 這個 module 負責：
# 1. 儲存目前最新的 Top 3
# 2. 從 PostgreSQL 讀取目前最新的 Top 3
#
# 第一版 SignalBrief 不保留歷史批次。
# 每次 refresh 都會用新的 Top 3 取代舊資料。
# ---------------------------------------------------------

from sqlalchemy.orm import Session

from models import SignalModel


# ---------------------------------------------------------
# Replace current Top 3
# ---------------------------------------------------------

def save_signals(
    db: Session,
    signals: list[dict],
) -> None:

    try:
        # 先刪除上一批 Top 3
        db.query(SignalModel).delete()

        # 儲存新的 Top 3
        for signal in signals:
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

        # 刪除舊資料 + 新增新資料一起正式寫入
        db.commit()

    except Exception:
        # 如果中途失敗，撤銷整次 database transaction，
        # 避免出現「舊資料刪了，但新資料只存一半」。
        db.rollback()
        raise


# ---------------------------------------------------------
# Read current Top 3
# ---------------------------------------------------------

def get_saved_signals(
    db: Session,
) -> list[SignalModel]:

    return (
        db.query(SignalModel)
        .order_by(
            SignalModel.top_rank.asc()
        )
        .limit(3)
        .all()
    )