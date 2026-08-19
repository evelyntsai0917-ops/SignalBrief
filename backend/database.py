# ---------------------------------------------------------
# SignalBrief database connection
# ---------------------------------------------------------
# 這個檔案負責：
# 1. 建立 PostgreSQL 連線
# 2. 建立 SQLAlchemy Session
# 3. 提供 Base 給後面的 database models 使用
# ---------------------------------------------------------

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://signalbrief:signalbrief@db:5432/signalbrief",
)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()