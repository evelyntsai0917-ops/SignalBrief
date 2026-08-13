# ---------------------------------------------------------
# SignalBrief ranking service
# ---------------------------------------------------------
# 這個 module 負責判斷一則 candidate article 的投資重要性。
#
# candidate article
#       ↓
# keyword / category signals
#       ↓
# importance_score
#       ↓
# 按分數由高到低排序
#
# 注意：
# source credibility 不在這裡加分。
# trusted source 已經在 news_service.py 做 hard filter。
# ---------------------------------------------------------


# ---------------------------------------------------------
# High-impact keywords
# ---------------------------------------------------------
# 這些事件通常可能影響：
# - 整體市場
# - 多個產業
# - 全球供應鏈
#
# 所以給比較高的權重。
# ---------------------------------------------------------

HIGH_IMPACT_KEYWORDS = {
    "war": 3.0,
    "invasion": 3.0,
    "sanctions": 3.0,
    "tariff": 2.5,
    "trade war": 3.0,

    "federal reserve": 3.0,
    "fed": 2.5,
    "interest rate": 3.0,
    "rate cut": 3.0,
    "rate hike": 3.0,
    "inflation": 2.5,
    "cpi": 2.0,

    "export ban": 3.0,
    "export controls": 3.0,
    "chip ban": 3.0,
}


# ---------------------------------------------------------
# Industry / technology impact keywords
# ---------------------------------------------------------

INDUSTRY_IMPACT_KEYWORDS = {
    "artificial intelligence": 2.0,
    "ai": 1.5,
    "semiconductor": 2.0,
    "chip": 1.5,
    "gpu": 2.0,
    "hbm": 2.0,

    "nvidia": 1.5,
    "tsmc": 1.5,

    "supply chain": 2.0,
}


# ---------------------------------------------------------
# Company event keywords
# ---------------------------------------------------------

COMPANY_EVENT_KEYWORDS = {
    "earnings": 1.5,
    "revenue": 1.0,
    "guidance": 2.0,
    "acquisition": 2.0,
    "merger": 2.0,
    "layoffs": 1.0,
}


# ---------------------------------------------------------
# Category base score
# ---------------------------------------------------------
# category 本身也提供少量基礎分。
#
# 例如：
# geopolitics / macro 通常可能影響整體市場，
# 所以基礎分略高。
# ---------------------------------------------------------

CATEGORY_BASE_SCORE = {
    "geopolitics": 2.0,
    "macro": 2.0,
    "ai_semiconductor": 1.5,
    "company_events": 1.0,
    "uncategorized": 0.0,
}


# ---------------------------------------------------------
# Calculate importance score
# ---------------------------------------------------------

def calculate_importance_score(article: dict) -> float:
    title = (article.get("title") or "").lower()
    category = article.get("category") or "uncategorized"

    score = CATEGORY_BASE_SCORE.get(category, 0.0)

    for keyword, weight in HIGH_IMPACT_KEYWORDS.items():
        if keyword in title:
            score += weight

    for keyword, weight in INDUSTRY_IMPACT_KEYWORDS.items():
        if keyword in title:
            score += weight

    for keyword, weight in COMPANY_EVENT_KEYWORDS.items():
        if keyword in title:
            score += weight

    return round(score, 2)


# ---------------------------------------------------------
# Rank candidate articles
# ---------------------------------------------------------

def rank_articles(articles: list[dict]) -> list[dict]:
    ranked_articles = []

    for article in articles:
        ranked_article = article.copy()

        ranked_article["importance_score"] = (
            calculate_importance_score(article)
        )

        ranked_articles.append(ranked_article)

    ranked_articles.sort(
        key=lambda article: article["importance_score"],
        reverse=True,
    )

    return ranked_articles