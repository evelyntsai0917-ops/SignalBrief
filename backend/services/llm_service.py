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
Category: {category}

Evaluate whether this event is important for investors.

Return JSON with exactly these fields:

{{
  "investment_relevance": 0,
  "importance_score": 0,
  "event_summary": "",
  "impact_path": ""
}}

Rules:

- investment_relevance: integer from 0 to 10
- importance_score: integer from 0 to 10
- event_summary: one concise sentence in Traditional Chinese
- impact_path: explain in Traditional Chinese using:
  事件 → 產業影響 → 可能的市場影響

Focus on the EVENT itself, not whether the headline contains financial keywords.

Do not give extra commentary outside JSON.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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