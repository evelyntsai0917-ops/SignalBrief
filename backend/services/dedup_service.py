# ---------------------------------------------------------
# SignalBrief event deduplication service
# ---------------------------------------------------------
# 目的：
#
# 多篇已經通過 LLM 分析的 candidate articles
#       ↓
# LLM 判斷哪些文章屬於同一個事件群
#       ↓
# 同一事件群只保留 importance_score 最高的一篇
#       ↓
# 回傳不同事件的文章
#
# 例如：
#
# Iran war hurts global economy
# Iran war disrupts energy markets
#
# 對每日 Top 3 而言可能屬於同一事件群，
# 不應同時佔掉兩個 Top 3 名額。
# ---------------------------------------------------------

import json
from groq import Groq
import os

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
)

client = Groq()


# ---------------------------------------------------------
# Ask LLM to group related events
# ---------------------------------------------------------

def group_events(articles: list[dict]) -> list[list[int]]:
    if not articles:
        return []

    article_items = []

    for index, article in enumerate(articles):
        article_items.append(
            {
                "index": index,
                "title": article.get("title") or "",
                "event_summary": article.get("event_summary") or "",
                "subcategory": article.get("subcategory") or "",
            }
        )

    prompt = f"""
You are an investment news editor for SignalBrief.

SignalBrief selects only a few important events each day.

Your job is to determine which articles belong to the same underlying
news event or event cluster.

Articles:

{json.dumps(article_items, ensure_ascii=False)}

Group articles that would feel repetitive if they both appeared in a
Top 3 daily investment briefing.

Examples of the SAME event cluster:

- Two articles discussing different consequences of the same ongoing war
  or geopolitical escalation.
- Two articles about the same central bank decision.
- Two articles about the same earnings announcement.
- Two articles about the same acquisition or company announcement.
- Two articles describing different market impacts of the same
  newly announced policy.

Do NOT group articles merely because they:

- involve the same country
- involve the same company
- belong to the same industry
- discuss the same broad topic

They must share the same underlying event or development.

Return JSON with exactly this structure:

{{
  "groups": [
    {{
      "article_indexes": [0, 1]
    }},
    {{
      "article_indexes": [2]
    }}
  ]
}}

Rules:

- Every article index must appear exactly once.
- Use the original integer indexes.
- A unique event should have its own group.
- Do not return commentary outside JSON.
"""

    try:
        completion = client.chat.completions.create(
            model= GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You group investment news articles by "
                        "their underlying real-world event."
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
        result = json.loads(content)

        groups = []

        for group in result.get("groups", []):
            indexes = group.get("article_indexes", [])

            valid_indexes = [
                index
                for index in indexes
                if isinstance(index, int)
                and 0 <= index < len(articles)
            ]

            if valid_indexes:
                groups.append(valid_indexes)

        return groups

    except Exception as exc:
        print(
            f"Event deduplication failed: {exc}",
            flush=True,
        )

        # 如果 LLM dedup 暫時失敗，
        # 不應讓整個 SignalBrief API 掛掉。
        # 每篇文章暫時視為不同事件。
        return [
            [index]
            for index in range(len(articles))
        ]


# ---------------------------------------------------------
# Deduplicate articles
# ---------------------------------------------------------

def deduplicate_events(
    articles: list[dict],
) -> list[dict]:

    if not articles:
        return []

    groups = group_events(articles)

    deduplicated_articles = []
    used_indexes = set()

    for group in groups:
        group_articles = []

        for index in group:
            if index in used_indexes:
                continue

            used_indexes.add(index)
            group_articles.append(articles[index])

        if not group_articles:
            continue

        # 同一事件群中，只保留 AI importance_score 最高的一篇。
        best_article = max(
            group_articles,
            key=lambda article: article.get(
                "importance_score",
                0,
            ),
        )

        deduplicated_articles.append(best_article)

    # 如果 LLM 不小心漏掉某個 index，
    # 也不要讓文章直接消失。
    for index, article in enumerate(articles):
        if index not in used_indexes:
            deduplicated_articles.append(article)

    # 去重後重新依重要性排序。
    deduplicated_articles.sort(
        key=lambda article: article.get(
            "importance_score",
            0,
        ),
        reverse=True,
    )

    return deduplicated_articles