# ---------------------------------------------------------
# SignalBrief database models
# ---------------------------------------------------------
# 這個檔案定義 PostgreSQL 裡的資料表結構。
#
# 目前先建立 signals table，
# 用來儲存每天產生的 SignalBrief Top 3。
# ---------------------------------------------------------

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class SignalModel(Base):
    __tablename__ = "signals"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    category = Column(
        String,
        nullable=False,
    )

    subcategory = Column(
        String,
        nullable=False,
    )

    summary = Column(
        Text,
        nullable=False,
    )

    impact_path = Column(
        Text,
        nullable=False,
    )

    importance_score = Column(
        Float,
        nullable=False,
    )

    top_rank = Column(
        Integer,
        nullable=False,
    )

    source_name = Column(
        String,
        nullable=False,
    )

    source_url = Column(
        Text,
        nullable=False,
        unique=True,
    )

    published_at = Column(
        DateTime,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )