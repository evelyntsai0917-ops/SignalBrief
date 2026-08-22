# ---------------------------------------------------------
# SignalBrief Daily Refresh Job
# ---------------------------------------------------------
# 這個檔案不是 API endpoint。
#
# 它的用途是讓排程系統（例如 EventBridge Scheduler）
# 可以直接執行 SignalBrief 的完整 refresh logic。
#
# Flow：
#
# EventBridge Scheduler
#   ↓
# ECS RunTask
#   ↓
# python jobs/daily_refresh.py
#   ↓
# run_signal_refresh()
#   ↓
# GDELT → Groq → Top 3 → PostgreSQL
# ---------------------------------------------------------

from services.refresh_service import run_signal_refresh


if __name__ == "__main__":
    run_signal_refresh()