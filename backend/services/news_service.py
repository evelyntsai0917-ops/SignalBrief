# ---------------------------------------------------------
# SignalBrief news service
# ---------------------------------------------------------
# 這個 module 負責所有「新聞取得與前處理」邏輯。

# GDELT（1 次）
#   ↓
# 最近 24 小時 + trusted domains
#   ↓
# trusted source hard filter
#   ↓
# URL deduplication
#   ↓
# candidate articles
# ---------------------------------------------------------

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
import json
import threading
import time
import requests
from services.ranking_service import rank_articles
from services.llm_service import analyze_articles
from services.dedup_service import deduplicate_events


def log(message: str):
    print(message, flush=True)


CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "candidates_cache.json"


def _load_disk_cache() -> list | None:
    if not CACHE_PATH.exists():
        return None

    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        articles = payload.get("articles") if isinstance(payload, dict) else payload
        if isinstance(articles, list) and articles:
            return articles
    except (OSError, json.JSONDecodeError) as exc:
        log(f"disk cache unreadable: {exc}")

    return None


def _save_disk_cache(articles: list) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(
            {"saved_at": datetime.utcnow().isoformat(), "articles": articles},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _previous_articles() -> list:
    memory = _candidate_cache["articles"]
    if memory:
        return memory

    disk = _load_disk_cache()
    if disk:
        _candidate_cache["articles"] = disk
        return disk

    return []


GDELT_HEADERS = {
    "User-Agent": "SignalBrief/1.0 (educational news brief)",
}

# ---------------------------------------------------------
# GDELT DOC 2.0 API endpoint
# ---------------------------------------------------------
# GDELT 是 SignalBrief 第一版的外部新聞搜尋來源。
# 我們使用 DOC API Article List mode，
# 取得新聞的 metadata，例如：
# - title
# - url
# - domain
# - publication time
# ---------------------------------------------------------

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


# ---------------------------------------------------------
# SignalBrief investment search queries
# ---------------------------------------------------------
# 四大類不是最終 Top 3 分類分數，
# 而是「新聞候選池的入口」。
#
# 產品目的：
# 快速掌握可能影響：
# - 股市
# - 投資風口
# - 產業趨勢
# - 重要公司基本面
# ---------------------------------------------------------

# GDELT DOC API 會拒絕過長 query，回傳純文字：
#   "Your query was too short or too long."
# 實測約 250 字元以上就會失敗。
# GDELT：OR 只能出現在 () 裡；空白視為 AND。
#
# 開發 endpoint 只打 1 次 GDELT。
# 四類主題用來在本地標 category，不再各打一次 API。
GDELT_CANDIDATE_QUERY = (
    "(Taiwan OR sanctions OR inflation OR Nvidia OR TSMC OR "
    "earnings OR semiconductor)"
)

CATEGORY_KEYWORDS = {
    "geopolitics": ["taiwan", "sanctions", "tariff", "trade war"],
    "macro": ["inflation", "cpi", "federal reserve", "rate cut"],
    "ai_semiconductor": ["nvidia", "tsmc", "gpu", "hbm", "semiconductor"],
    "company_events": ["earnings", "guidance", "acquisition", "layoffs"],
}

# GDELT 是全球新聞火hose。如果不在 query 裡限制 domain，
# datedesc 的前 N 筆幾乎都是各地小站，trusted source filter 會把結果濾成 0。
# 這組 domain 必須夠短，才能和上面的 keyword query 加總後仍 < 250 字元。
GDELT_DOMAIN_FILTER = (
    "(domain:reuters.com OR domain:cnbc.com OR domain:apnews.com OR "
    "domain:bloomberg.com OR domain:techcrunch.com OR domain:cnyes.com OR "
    "domain:bnext.com.tw)"
)

# GDELT 官方說每 5 秒 1 個 request；實測 5 秒仍常 429，所以拉到 8 秒。
MIN_GDELT_INTERVAL_SECONDS = 8
_last_gdelt_request_at = 0.0

# /api/news/candidates 是開發用 inspection API。
# 短 cache 避免連續重整就再次打爆 GDELT rate limit，看起來又像 0 articles。
CANDIDATE_CACHE_TTL_SECONDS = 10 * 60
_candidate_cache = {
    "fetched_at": 0.0,
    "articles": None,
}
_fetch_lock = threading.Lock()
# ---------------------------------------------------------
# Trusted news source whitelist
# ---------------------------------------------------------
# 來源可信度在 SignalBrief 裡只是一個 Hard Filter。
#
# 也就是：
#
# source 不可信
#     → 直接淘汰
#
# source 可信
#     → 有資格進 candidate pool
#
# 來源本身「不會增加 Top 3 分數」。
#
# Top 3 最後會依照事件本身對：
# - 市場
# - 產業
# - 投資風口
#
# 的影響程度判斷。
#
# 官方一手來源目前刻意不放進新聞池。
# ---------------------------------------------------------

TRUSTED_SOURCES = {
    # International
    "reuters.com",
    "apnews.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "cnbc.com",
    "techcrunch.com",
    "theverge.com",
    "arstechnica.com",
    "wired.com",

    # Taiwan
    "bnext.com.tw",
    "techorange.com",
    "cnyes.com",
    "moneydj.com",
    "businesstoday.com.tw",
}

SOURCE_DISPLAY = {
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    "bloomberg.com": "Bloomberg",
    "ft.com": "Financial Times",
    "wsj.com": "WSJ",
    "cnbc.com": "CNBC",
    "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    "arstechnica.com": "Ars Technica",
    "wired.com": "Wired",
    "bnext.com.tw": "數位時代",
    "techorange.com": "科技報橘",
    "cnyes.com": "鉅亨網",
    "moneydj.com": "MoneyDJ",
    "businesstoday.com.tw": "今周刊",
}


# ---------------------------------------------------------
# Normalize article domain
# ---------------------------------------------------------
# 不直接完全相信 GDELT 回傳 domain 的格式。
# 例如：
# www.reuters.com
# reuters.com
# 對 whitelist 來說其實應該視為同一來源。
#
# 所以這裡統一：
# - 小寫
# - 去掉 www.
# ---------------------------------------------------------

def normalize_domain(domain: str) -> str:
    domain = domain.lower().strip()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def is_trusted_source(domain: str) -> bool:
    domain = normalize_domain(domain)

    if domain in TRUSTED_SOURCES:
        return True

    # uk.reuters.com 仍視為 reuters.com
    return any(domain.endswith("." + source) for source in TRUSTED_SOURCES)


def _respect_gdelt_rate_limit():
    global _last_gdelt_request_at

    elapsed = time.time() - _last_gdelt_request_at

    if _last_gdelt_request_at and elapsed < MIN_GDELT_INTERVAL_SECONDS:
        time.sleep(MIN_GDELT_INTERVAL_SECONDS - elapsed)

    _last_gdelt_request_at = time.time()


def classify_article(article: dict) -> str:
    text = f"{article.get('title') or ''} {article.get('url') or ''}".lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category

    return "uncategorized"


# ---------------------------------------------------------
# Fetch articles from GDELT
# ---------------------------------------------------------
# 這個 function 只負責：
#
# query
#   ↓
# GDELT
#   ↓
# articles
#
# 它不負責：
# - trusted source filter
# - deduplication
# - ranking
#
# 這樣 service function 的責任會比較單純。
# ---------------------------------------------------------

def fetch_gdelt_articles(query: str, max_records: int = 50):
    full_query = f"{query} {GDELT_DOMAIN_FILTER}"

    log(
        f"GDELT query_len={len(full_query)} "
        f"keyword_len={len(query)}"
    )

    params = {
        "query": full_query,
        "mode": "artlist",
        "format": "json",

        # 先抓最近 3 天，避免 24h + trusted domain 剛好沒稿。
        "timespan": "3d",

        # 避免一次抓過多資料。
        "maxrecords": max_records,

        # 最新新聞優先。官方參數是 DateDesc。
        "sort": "DateDesc",
    }

    _respect_gdelt_rate_limit()

    max_attempts = 2

    for attempt in range(max_attempts):
        try:
            response = requests.get(
                GDELT_DOC_API,
                params=params,
                timeout=25,
                headers=GDELT_HEADERS,
            )
        except requests.RequestException as exc:
            log(f"GDELT request failed: {exc}")
            if attempt < max_attempts - 1:
                time.sleep(10)
                continue
            return None

        if response.status_code == 429:
            if attempt < max_attempts - 1:
                log("GDELT rate limited. Retrying in 10s...")
                time.sleep(10)
                continue
            log("GDELT still rate limited after retry.")
            return None

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            log(f"GDELT HTTP error: {exc}")
            return None

        body = response.text.strip()

        if "too short or too long" in body.lower():
            log(
                f"GDELT rejected query as too long "
                f"({len(full_query)} chars): {body[:120]}"
            )
            return []

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            log("GDELT returned invalid JSON:")
            log(body[:500])
            return []

        articles = data.get("articles", []) if isinstance(data, dict) else []
        if not articles:
            log(f"GDELT returned 0 articles. body={body[:200]!r}")
        else:
            log(f"GDELT returned {len(articles)} raw articles")
        return articles

    return None


# ---------------------------------------------------------
# Fetch all candidate articles
# ---------------------------------------------------------
# 這是目前整個「新聞 ingestion 前半段」的入口。
#
# 流程：
#
# 1 次 GDELT
#     ↓
# trusted source filter
#     ↓
# URL deduplication
#     ↓
# 本地 category tagging
#     ↓
# candidate article list
# ---------------------------------------------------------

def fetch_all_candidate_articles():
    if _candidate_cache["articles"] is None:
        disk = _load_disk_cache()
        if disk:
            _candidate_cache["articles"] = disk
            log(f"Loaded {len(disk)} articles from disk cache")

    now = time.time()
    cached_articles = _candidate_cache["articles"]

    if (
        cached_articles is not None
        and now - _candidate_cache["fetched_at"] < CANDIDATE_CACHE_TTL_SECONDS
    ):
        log(
            f"Returning {len(cached_articles)} cached candidate articles"
        )
        return cached_articles

    with _fetch_lock:
        now = time.time()
        cached_articles = _candidate_cache["articles"]

        if (
            cached_articles is not None
            and now - _candidate_cache["fetched_at"]
            < CANDIDATE_CACHE_TTL_SECONDS
        ):
            log(
                f"Returning {len(cached_articles)} cached candidate articles"
            )
            return cached_articles

        articles = fetch_gdelt_articles(GDELT_CANDIDATE_QUERY)

        if articles is None:
            previous = _previous_articles()

            if previous:
                log(
                    f"GDELT failed; returning "
                    f"{len(previous)} previously cached articles"
                )
                return previous

            log("GDELT failed and cache is empty")
            return []

        # -------------------------------------------------
        # Only keep articles from the latest 24 hours
        # -------------------------------------------------

        cutoff_time = (
            datetime.now(timezone.utc)
            - timedelta(hours=24)
        )

        all_articles = []
        seen_urls = set()

        for article in articles:
            url = article.get("url")
            domain = (
                article.get("domain")
                or urlparse(url or "").netloc
            )

            if not url or not domain:
                continue

            # ---------------------------------------------
            # 24-hour publication time filter
            # ---------------------------------------------

            seendate = article.get("seendate")

            if not seendate:
                continue

            try:
                published_time = datetime.strptime(
                    seendate,
                    "%Y%m%dT%H%M%SZ",
                ).replace(tzinfo=timezone.utc)

            except ValueError:
                continue

            if published_time < cutoff_time:
                continue

            # ---------------------------------------------
            # Trusted source hard filter
            # ---------------------------------------------

            if not is_trusted_source(domain):
                continue

            # ---------------------------------------------
            # URL deduplication
            # ---------------------------------------------

            if url in seen_urls:
                continue

            # ---------------------------------------------
            # Local category tagging
            # ---------------------------------------------

            article["category"] = classify_article(article)
            article["domain"] = normalize_domain(domain)

            seen_urls.add(url)
            all_articles.append(article)

        log(
            f"candidates raw={len(articles)} "
            f"kept_24h={len(all_articles)}"
        )

        if all_articles:
            _candidate_cache["articles"] = all_articles
            _candidate_cache["fetched_at"] = time.time()

            _save_disk_cache(all_articles)

        return all_articles

def parse_gdelt_time(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()

    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
    except ValueError:
        return datetime.utcnow()


def get_latest_signals():
    # -----------------------------------------------------
    # 1. 取得最近 24 小時的 candidate articles
    # -----------------------------------------------------
    articles = fetch_all_candidate_articles()

    # -----------------------------------------------------
    # 2. 用規則 ranking 做第一層粗篩
    #    避免所有文章都直接送給 LLM
    # -----------------------------------------------------
    ranked_articles = rank_articles(articles)

    # 目前只取前 10 篇交給 Groq 分析
    llm_candidates = ranked_articles[:10]

    # -----------------------------------------------------
    # 3. Groq AI 分析
    #
    # AI 會判斷：
    # - 是否為真正事件
    # - article type
    # - investment relevance
    # - importance score
    # - subcategory
    # - 中文事件摘要
    # - impact path
    #
    # analyze_articles() 也會把非事件型文章淘汰
    # -----------------------------------------------------
    analyzed_articles = analyze_articles(llm_candidates)

    # -----------------------------------------------------
    # 4. Event deduplication
    #
    # 如果多篇文章其實屬於同一個事件，
    # 只保留 importance_score 最高的一篇
    # -----------------------------------------------------
    deduplicated_articles = deduplicate_events(
        analyzed_articles
    )

    # -----------------------------------------------------
    # 5. 最終 Top 3
    # -----------------------------------------------------
    top_articles = deduplicated_articles[:3]

    signals = []

    # -----------------------------------------------------
    # 6. 整理成 frontend / API 要的 Signal 格式
    # -----------------------------------------------------
    for index, article in enumerate(top_articles, start=1):
        domain = article.get("domain") or ""

        source_name = SOURCE_DISPLAY.get(
            domain,
            domain,
        )

        # 優先使用 AI 判斷的 subcategory。
        # 如果 AI 沒有回傳，才退回原本 keyword 分類。
        category = (
            article.get("subcategory")
            or article.get("category")
            or "other"
        )

        signals.append(
            {
                "id": index,

                "title": (
                    article.get("title")
                    or ""
                ).strip(),

                "summary_points": [
                    article.get(
                        "event_summary",
                        "",
                    )
                ],

                "category": "investment",

                "subcategory": category,

                "impact_path": article.get(
                    "impact_path",
                    "",
                ),

                "importance_score": article.get(
                    "importance_score",
                    0,
                ),

                "top_rank": index,

                "source_name": source_name,

                "source_url": (
                    article.get("url")
                    or ""
                ),

                "published_at": parse_gdelt_time(
                    article.get("seendate")
                ),
            }
        )

    return signals