# ---------------------------------------------------------
# SignalBrief news service
# ---------------------------------------------------------
# 這個 module 負責所有「新聞取得與前處理」邏輯。

# GDELT
#   ↓
# 四大投資主題 query
#   ↓
# 最近 24 小時
#   ↓
# trusted source hard filter
#   ↓
# URL deduplication
#   ↓
# candidate articles
# ---------------------------------------------------------

from datetime import datetime, timedelta
from urllib.parse import urlparse
import time
import requests

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

SEARCH_QUERIES = {
    # -----------------------------------------------------
    # 1. 地緣政治與全球風險
    # 例如：
    # - 戰爭
    # - 制裁
    # - 關稅
    # - 台海
    # - 中美關係
    # - 中東
    # - 出口管制
    # 這些事件可能進一步影響：
    # 股票市場、能源、半導體與全球供應鏈。
    # -----------------------------------------------------
    "geopolitics":
        '(war OR conflict OR sanctions OR tariff OR "trade war" OR "export controls" '
        'OR blockade OR military OR tension) '
        'AND (market OR economy OR "supply chain" OR energy OR semiconductor '
        'OR China OR Taiwan OR Russia OR Ukraine OR "Middle East" OR Iran)',

    # -----------------------------------------------------
    # 2. 總體經濟與政策
    #
    # 例如：
    # - CPI / PCE
    # - 利率
    # - Fed
    # - GDP
    # - 就業
    # - recession
    # - bond yields
    # - liquidity
    #
    # 這些資訊會直接影響：
    # 市場估值、資金成本、風險偏好。
    # -----------------------------------------------------
    "macro":
        '(inflation OR CPI OR PCE OR "interest rates" OR "rate cut" OR "rate hike" '
        'OR GDP OR employment OR unemployment OR payrolls OR recession '
        'OR "economic growth" OR "bond yields" OR "Treasury yields" OR dollar OR liquidity) '
        'AND ("Federal Reserve" OR "central bank" OR "monetary policy" '
        'OR market OR stocks OR economy OR US OR China OR "global economy")',

    # -----------------------------------------------------
    # 3. AI 與半導體供應鏈
    #
    # 這是 SignalBrief 用來尋找
    # 「下一個可能形成投資風口的產業變化」
    # 最重要的類別之一。
    # 包含：
    # - AI infrastructure
    # - AI server
    # - GPU
    # - data center
    # - HBM
    # - memory
    # - advanced packaging
    # - foundry
    # - 重要半導體公司
    # -----------------------------------------------------
    "ai_semiconductor":
        '("AI infrastructure" OR "AI server" OR "data center" OR GPU OR accelerator '
        'OR semiconductor OR foundry OR "advanced packaging" OR HBM '
        'OR "high bandwidth memory" OR "memory chip" '
        'OR TSMC OR Nvidia OR AMD OR Broadcom OR ASML OR Micron OR Samsung OR "SK Hynix") '
        'AND (demand OR supply OR shortage OR capacity OR investment OR orders '
        'OR expansion OR guidance OR revenue OR launch OR production)',
    # -----------------------------------------------------
    # 4. 公司重大事件
    # 我們不希望抓所有企業新聞。
    # 這一類只關注可能改變：
    # - 公司成長
    # - 獲利
    # - 市場預期
    # - 供應能力
    # - 重大風險
    # 的事件。
    # -----------------------------------------------------
    "company_events":
        '(earnings OR revenue OR profit OR guidance OR forecast OR acquisition '
        'OR merger OR partnership OR contract OR order OR investment OR layoffs '
        'OR restructuring OR bankruptcy OR investigation OR lawsuit OR recall '
        'OR "new product" OR expansion OR "new factory" OR "production capacity" '
        'OR "major customer") '
        'AND (beat OR miss OR raise OR cut OR growth OR decline OR company '
        'OR technology OR semiconductor OR AI OR shares OR market OR revenue '
        'OR demand OR orders)',
}
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
# ---------------------------------------------------------
# Temporary mock SignalBrief data
# ---------------------------------------------------------
mock_signals = [
    {
        "id": 1,
        "title": "AI 伺服器需求持續成長",
        "summary_points": [
            "大型雲端業者持續增加 AI 基礎設施投資",
            "GPU 與先進封裝需求維持強勁",
            "台灣半導體供應鏈可能持續受惠",
        ],
        "category": "investment",
        "subcategory": "ai_semiconductor",
        "impact_path": "AI 資本支出增加 → GPU 與伺服器需求增加 → 半導體供應鏈受惠",
        "importance_score": 88.5,
        "top_rank": 1,
        "source_name": "Reuters",
        "source_url": "https://example.com/article-1",
        "published_at": "2026-08-10T08:30:00",
    },
    {
        "id": 2,
        "title": "市場持續關注利率政策",
        "summary_points": [
            "投資人關注央行下一步利率決策",
            "通膨數據仍是政策判斷的重要依據",
            "利率預期可能影響科技股與成長股估值",
        ],
        "category": "investment",
        "subcategory": "macro",
        "impact_path": "利率預期改變 → 資金成本與估值調整 → 股票市場波動",
        "importance_score": 82.0,
        "top_rank": 2,
        "source_name": "Reuters",
        "source_url": "https://example.com/article-2",
        "published_at": "2026-08-12T07:45:00",
    },
]


# ---------------------------------------------------------
# Read current SignalBrief signals
# ---------------------------------------------------------
# 這裡很可能會改成直接讀 database，
# 不會在 user request 時重新抓外部新聞。
# ---------------------------------------------------------

def get_latest_signals():
    now = datetime.now()
    cutoff_time = now - timedelta(hours=24)

    return [
        signal
        for signal in mock_signals
        if datetime.fromisoformat(signal["published_at"]) >= cutoff_time
    ]


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
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",

        # GDELT 只搜尋最近 24 小時。
        "timespan": "24h",

        # 避免一次抓過多資料。
        "maxrecords": max_records,

        # 最新新聞優先。
        "sort": "datedesc",
    }

    # -----------------------------------------------------
    # Retry strategy
    # -----------------------------------------------------
    # GDELT 有 rate limiting。
    #
    # 如果收到 HTTP 429：
    # 第一次等待 1 秒
    # 第二次等待 2 秒
    # 第三次等待 4 秒
    #
    # 這稱為 exponential backoff。
    # -----------------------------------------------------

    max_retries = 3

    for attempt in range(max_retries):
        try:
            response = requests.get(
                GDELT_DOC_API,
                params=params,

                # 原本 20 秒可能讓 browser endpoint
                # 卡非常久。
                #
                # 目前 integration/debug 階段
                # 先縮短成 10 秒。
                timeout=10,
            )

        except requests.RequestException as exc:
            print(f"GDELT request failed: {exc}")
            return []

        # -------------------------------------------------
        # Rate limit handling
        # -------------------------------------------------

        if response.status_code == 429:
            wait_seconds = 2 ** attempt

            print(
                f"GDELT rate limited request. "
                f"Retrying in {wait_seconds}s..."
            )

            time.sleep(wait_seconds)
            continue

        # 其他 4xx / 5xx HTTP error。
        try:
            response.raise_for_status()

        except requests.HTTPError as exc:
            print(f"GDELT HTTP error: {exc}")
            return []

        # -------------------------------------------------
        # GDELT normally returns JSON because format=json.
        #
        # 但我們之前實際遇過 response 不是有效 JSON，
        # 所以這裡不能直接假設 response.json() 一定成功。
        # -------------------------------------------------

        try:
            data = response.json()

        except requests.exceptions.JSONDecodeError:
            print("GDELT returned invalid JSON:")
            print(response.text[:500])
            return []

        return data.get("articles", [])

    # 三次都被 rate limit。
    print("GDELT request failed after all retries.")
    return []


# ---------------------------------------------------------
# Fetch all candidate articles
# ---------------------------------------------------------
# 這是目前整個「新聞 ingestion 前半段」的入口。
#
# 流程：
#
# SEARCH_QUERIES
#     ↓
# GDELT
#     ↓
# trusted source filter
#     ↓
# URL deduplication
#     ↓
# category tagging
#     ↓
# candidate article list
# ---------------------------------------------------------

def fetch_all_candidate_articles():
    all_articles = []

    # 用 set 儲存已經看過的 URL。
    # set 的 membership lookup 很快，
    # 適合拿來做 deduplication。
    seen_urls = set()

    # 四大 category → 四次主要 GDELT request。
    for category, query in SEARCH_QUERIES.items():
        articles = fetch_gdelt_articles(query)

        for article in articles:
            url = article.get("url")
            domain = article.get("domain")

            # 沒有 URL 或 domain 的資料無法可靠處理。
            if not url or not domain:
                continue

            normalized_domain = normalize_domain(domain)

            # ---------------------------------------------
            # Trusted source Hard Filter
            # ---------------------------------------------
            # 不可信來源直接淘汰，
            # 不進 event dedup / ranking / LLM。
            # ---------------------------------------------

            if normalized_domain not in TRUSTED_SOURCES:
                continue

            # ---------------------------------------------
            # URL deduplication
            # ---------------------------------------------

            if url in seen_urls:
                continue

            # 標記這則新聞是由哪一組搜尋邏輯找到。
            article["category"] = category

            seen_urls.add(url)
            all_articles.append(article)

    return all_articles