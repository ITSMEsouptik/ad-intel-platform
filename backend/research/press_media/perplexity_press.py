"""
Novara Research Foundation: Press & Media Intelligence — Perplexity Client
Version 1.0 - Feb 2026

2-call pipeline:
  Call 1 (Discovery): Find press articles, blog posts, news mentions
  Call 2 (Analysis): Extract narratives, key quotes, source tiers, coverage gaps
"""

import os
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

PERPLEXITY_MODEL = "sonar"
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
RETRY_DELAY = 3


def build_discovery_prompt(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    query_plan: Dict[str, Any],
) -> str:
    """Build Call 1: discover press articles and media coverage."""

    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else "not specified"

    # Group queries by family
    families = {}
    for q in query_plan.get("queries", []):
        fam = q.get("family", "general")
        families.setdefault(fam, []).append(q["query"])

    query_section = ""
    for fam, qs in families.items():
        query_section += f"\n**{fam.upper()}:**\n"
        for q in qs[:6]:
            query_section += f"  - {q}\n"

    target_domains = query_plan.get("target_domains", [])
    domains_str = ", ".join(target_domains[:20])

    return f"""You are a media intelligence analyst working for a performance marketing agency. Your job is to find ALL press articles, news features, blog posts, and media coverage about this brand.

## WHY THIS MATTERS
Before creating ad campaigns, we need to understand:
- How the media portrays this brand (positive, negative, neutral)
- What narratives journalists have built around the brand
- Notable quotes and press mentions usable as social proof in ads
- Which media outlets cover the brand (helps with PR strategy)

This data will be used by strategists to identify press-worthy angles and by copywriters to incorporate media credibility into ads.

## THE BRAND
- Name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}
- Niche: {niche}
- Services: {services_str}
- Overview: {brand_overview}

## IDENTITY VERIFICATION (CRITICAL)
Multiple businesses may share the name "{brand_name}". You MUST only return articles about the EXACT business described above:
1. **Location match**: Articles must be about {brand_name} in or serving {location}.
2. **Website/domain match**: If the article links to a website, it should match or relate to {domain}.
3. **Service match**: The business described must match the services above ({services_str}).

If you are NOT confident an article is about THIS specific business, EXCLUDE IT.

## YOUR TASK
Find ALL press articles, news stories, blog posts, features, and media mentions about {brand_name} ({domain}) in {location}.

Search across these types of sources: news outlets, industry blogs, lifestyle magazines, business publications, local media, trade publications.

Priority sources: {domains_str}

Use these search queries as guidance (grouped by intent):
{query_section}

For each article you find, return:
- The EXACT URL to the article
- The source name (e.g., "Forbes", "Gulf News")
- The source domain
- The article title
- The publication date (if visible)
- The type of article
- A brief excerpt capturing the key point about the brand (max 300 chars)
- The article's sentiment toward the brand
- A relevance score (0-100)

## OUTPUT FORMAT (JSON only — no markdown, no explanation)

{{
  "articles": [
    {{
      "url": "https://www.forbes.com/...",
      "title": "Article title as it appears",
      "source_name": "Forbes",
      "source_domain": "forbes.com",
      "article_type": "feature | news | interview | press_release | blog | opinion | listicle",
      "published_date": "2024-03 or 2024-03-15 or null",
      "excerpt": "Key excerpt about the brand (max 300 chars, keep original phrasing)",
      "sentiment": "positive | neutral | negative | mixed",
      "relevance_score_0_100": 85
    }}
  ],
  "sources_searched": ["forbes.com", "gulfnews.com"],
  "queries_that_found_results": ["query1", "query2"]
}}

## HARD RULES
1. MAX 30 articles total
2. Only include articles from NEWS, PRESS, BLOG, or MEDIA sources — NOT forums (reddit, quora), NOT review platforms (trustpilot, yelp, g2), NOT the brand's own website ({domain})
3. Excerpts should capture the key point — keep original journalistic phrasing where possible
4. Only include articles genuinely about THIS {brand_name} in {location}
5. Prefer recent articles (last 2 years) but include older landmark articles
6. Include BOTH positive and negative coverage — do not filter by sentiment
7. If you find ZERO press articles, return an empty articles array — do NOT substitute with non-press sources
8. article_type must be one of: feature, news, interview, press_release, blog, opinion, listicle"""


def build_analysis_prompt(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    articles: List[Dict[str, Any]],
    optional_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Build Call 2: analyze press coverage for narratives, quotes, gaps."""

    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else "not specified"

    # Build article context
    article_context = ""
    for i, a in enumerate(articles[:25]):
        source = a.get("source_name", "")
        title = a.get("title", "untitled")
        excerpt = a.get("excerpt", "")
        url = a.get("url", "")
        sentiment = a.get("sentiment", "neutral")
        article_context += f"\n[{i+1}] {source} — \"{title}\" ({sentiment})\n    Excerpt: \"{excerpt}\"\n    URL: {url}\n"

    # Optional context from other modules
    extra_context = ""
    if optional_context:
        strengths = optional_context.get("review_strengths", [])
        weaknesses = optional_context.get("review_weaknesses", [])
        if strengths:
            extra_context += "\n\n## KNOWN BRAND STRENGTHS (from Reviews module)\n"
            for s in strengths[:3]:
                extra_context += f"- {s}\n"
        if weaknesses:
            extra_context += "\n## KNOWN BRAND WEAKNESSES (from Reviews module)\n"
            for w in weaknesses[:3]:
                extra_context += f"- {w}\n"

    return f"""You are a media intelligence analyst working for a performance marketing agency. You have been given press articles about this brand. Your job is to extract actionable intelligence from the media coverage.

## WHY THIS MATTERS
The narratives, quotes, and insights you extract will be used by:
- **Ad copywriters** to incorporate media credibility and press quotes into advertising
- **Strategists** to understand how the brand is perceived by the media
- **PR teams** to identify coverage gaps and media opportunities

## THE BRAND
- Name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}
- Niche: {niche}
- Services: {services_str}
- Overview: {brand_overview}
{extra_context}

## PRESS ARTICLES TO ANALYZE
{article_context}

## YOUR TASK
From these articles, extract:

1. **Coverage Summary** — 3 bullet overview of how the media portrays this brand
2. **Media Narratives** — recurring themes/stories in the coverage
3. **Key Quotes** — the most compelling press quotes usable in advertising
4. **Media Sources** — classify each source by tier
5. **Coverage Gaps** — what stories are MISSING from the press
6. **PR Opportunities** — angles that could generate future coverage

## OUTPUT FORMAT (JSON only — no markdown, no explanation)

{{
  "coverage_summary": [
    "3 concise bullets summarizing how the media portrays the brand (max 120 chars each)"
  ],
  "narratives": [
    {{
      "label": "2-5 word label (e.g., 'Rapid UAE expansion')",
      "type": "narrative | controversy | milestone | positioning | trend",
      "sentiment": "positive | neutral | negative | mixed",
      "frequency": "frequent | moderate | occasional",
      "evidence": [
        "Key quote or paraphrase from an article supporting this narrative (max 150 chars)"
      ],
      "source_urls": ["url1", "url2"]
    }}
  ],
  "key_quotes": [
    {{
      "quote": "A compelling press quote about the brand, usable in advertising (max 200 chars). These are paraphrased from the articles.",
      "source_name": "Forbes",
      "source_url": "https://...",
      "context": "What the article was about (max 100 chars)"
    }}
  ],
  "media_sources": [
    {{
      "name": "Forbes",
      "domain": "forbes.com",
      "tier": "tier1 | tier2 | tier3",
      "article_count": 2,
      "most_recent_date": "2024-06 or null"
    }}
  ],
  "coverage_gaps": [
    "Area where press coverage is missing or weak (max 120 chars)"
  ],
  "pr_opportunities": [
    "Angle that could generate future press coverage (max 120 chars, observation NOT strategy)"
  ]
}}

## TIER DEFINITIONS
- **tier1**: Major international/national outlets (Forbes, Bloomberg, BBC, NYT, Vogue, etc.)
- **tier2**: Industry-specific or strong regional outlets (TechCrunch, Gulf News, Arabian Business, Eater, etc.)
- **tier3**: Niche blogs, local media, trade publications

## HARD RULES
1. narratives: MAX 8. Each must have at least 1 evidence quote and 1 source URL
2. key_quotes: MAX 8. Each must sound compelling enough to use in a testimonial ad or press page. ALL quotes are paraphrased from the articles.
3. media_sources: List EVERY unique source from the articles provided
4. coverage_gaps: MAX 5. Genuine gaps — NOT marketing suggestions
5. pr_opportunities: MAX 5. Observations about what angles could work — NOT strategy advice
6. Evidence quotes should closely paraphrase the original article — keep the journalistic tone
7. Coverage summary must be factual — do NOT editorialize

## STRICTLY FORBIDDEN
- Making up articles or quotes that don't exist
- Including forum/community content (Reddit, Quora) — that belongs in a different module
- Including review site content (Trustpilot, Yelp, Google Reviews) — that's a different module
- Marketing advice, campaign plans, budget recommendations
- Phrases like "leverage", "capitalize", "run a campaign"
- Any form of action plans or strategy recommendations
- Generic narratives without specific evidence"""


# ============== API CALLS ==============

async def _call_perplexity(prompt: str, system_msg: str, max_tokens: int = 3000) -> Optional[Dict[str, Any]]:
    """Make a single Perplexity API call with 1 retry."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        logger.error("[PRESS] PERPLEXITY_API_KEY not set")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(PERPLEXITY_URL, headers=headers, json=payload)

                if response.status_code in (401, 403, 429):
                    logger.error(f"[PRESS] Non-retryable error: {response.status_code}")
                    return None

                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]
                tokens = result.get("usage", {}).get("total_tokens", 0)

                parsed = _parse_json(content)
                if parsed:
                    parsed["_tokens"] = tokens
                    return parsed

                logger.warning(f"[PRESS] Malformed JSON on attempt {attempt + 1}")
                if attempt == 0:
                    payload["messages"][-1]["content"] += "\n\nIMPORTANT: Your previous response was not valid JSON. Return ONLY a valid JSON object."
                    await asyncio.sleep(RETRY_DELAY)
                    continue

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"[PRESS] API error on attempt {attempt + 1}: {e}")
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.error(f"[PRESS] Unexpected error: {e}")
            break

    return None


def _parse_json(content: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response, handling markdown wrappers."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    logger.error(f"[PRESS] Failed to parse JSON: {text[:300]}")
    return None


async def fetch_press_discovery(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    query_plan: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Call 1: Discover press articles."""

    prompt = build_discovery_prompt(
        brand_name=brand_name,
        domain=domain,
        city=city,
        country=country,
        subcategory=subcategory,
        niche=niche,
        services=services,
        brand_overview=brand_overview,
        query_plan=query_plan,
    )

    system_msg = (
        "You are a media intelligence analyst. "
        "Find all press articles, news stories, and media coverage about this brand. "
        "Return only valid JSON. Be thorough — search across news, industry publications, and lifestyle media."
    )

    logger.info(f"[PRESS] Call 1 (Discovery): {brand_name}, {query_plan.get('total_queries', 0)} queries")
    return await _call_perplexity(prompt, system_msg, max_tokens=3500)


async def fetch_press_analysis(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    articles: List[Dict[str, Any]],
    optional_context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Call 2: Analyze press coverage for narratives + quotes."""

    prompt = build_analysis_prompt(
        brand_name=brand_name,
        domain=domain,
        city=city,
        country=country,
        subcategory=subcategory,
        niche=niche,
        services=services,
        brand_overview=brand_overview,
        articles=articles,
        optional_context=optional_context,
    )

    system_msg = (
        "You are a media intelligence analyst working for a performance marketing agency. "
        "Analyze press coverage and extract narratives, key quotes, and coverage gaps. "
        "Return only valid JSON. Every insight must be grounded in actual article content."
    )

    logger.info(f"[PRESS] Call 2 (Analysis): {brand_name}, {len(articles)} articles")
    return await _call_perplexity(prompt, system_msg, max_tokens=4000)
