import json
from groq import Groq


client = Groq()


def analyze_article(article: dict) -> dict:
    title = article.get("title") or ""
    domain = article.get("domain") or ""
    category = article.get("category") or "uncategorized"

    prompt = f"""
You are an investment news analyst for SignalBrief.

Analyze the following news article based only on the information provided.

Title: {title}
Source: {domain}
Current category: {category}

Determine whether this article describes a real, meaningful event that investors should know about.

Return JSON with exactly these fields:

{{
  "is_event": true,
  "article_type": "",
  "investment_relevance": 0,
  "importance_score": 0,
  "subcategory": "",
  "event_summary": "",
  "impact_path": ""
}}

Rules:

- is_event:
  - true only if the article reports a real event, announcement, policy action,
    geopolitical development, macroeconomic development, major company event,
    or meaningful industry development.
  - false for opinion pieces, analyst calls, price targets, trading guides,
    stock picks, commentary, forecasts without a concrete new event,
    or generic market discussion.

- article_type must be one of:
  - event
  - analyst_opinion
  - trading_guide
  - commentary
  - forecast
  - other

- investment_relevance:
  integer from 0 to 10.
  Measure how relevant the event is to investors.

- importance_score:
  integer from 0 to 10.
  Measure how important the EVENT itself is.
  Focus on potential impact scope and magnitude.

- subcategory must be one of:
  - geopolitics
  - macro
  - ai_semiconductor
  - company_events
  - other

- event_summary:
  one concise sentence in Traditional Chinese describing what actually happened.

- impact_path:
  explain in Traditional Chinese using exactly this logic:
  事件 → 受影響產業或公司 → 可能的市場影響

Important:

- Do not assign a high score simply because the headline contains words such as
  Fed, Nvidia, inflation, AI, war, or earnings.
- Judge whether there is a concrete new event.
- Analyst recommendations and price target changes are not major events.
- Trading advice and "how to trade" articles are not major events.
- If is_event is false, importance_score should normally be low.
- Do not give extra commentary outside JSON.
"""

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You analyze investment news objectively "
                    "and return structured JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = completion.choices[0].message.content

    return json.loads(content)

def analyze_articles(articles: list[dict]) -> list[dict]:
    analyzed_articles = []

    for article in articles:
        analysis = analyze_article(article)

        if not analysis.get("is_event", False):
            continue

        analyzed_article = article.copy()
        analyzed_article.update(analysis)

        analyzed_articles.append(analyzed_article)

    analyzed_articles.sort(
        key=lambda article: article.get("importance_score", 0),
        reverse=True,
    )

    return analyzed_articles