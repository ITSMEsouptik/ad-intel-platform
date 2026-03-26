"""
Novara Research Foundation: Community Intelligence — Perplexity Client
Version 1.0 - Feb 2026

2-call pipeline:
  Call 1 (Discovery): Find real forum threads matching query plan
  Call 2 (Synthesis): Extract themes, language bank, audience notes from discovered threads
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
    """Build Call 1: discover forum threads."""

    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else "not specified"

    # Group queries by family for the prompt
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
    domains_str = ", ".join(target_domains)

    excluded = query_plan.get("excluded_domains", [])
    excluded_str = ", ".join(excluded)

    return f"""You are a community intelligence analyst working for a performance marketing agency. Your job is to find REAL public forum and community discussions relevant to this brand and its category.

## WHY THIS MATTERS
Before creating ad copy, we need to understand:
- How real people talk about this category in forums (Reddit, Quora, etc.)
- What questions they ask, what frustrations they express, what they desire
- The exact language and phrasing customers use (not marketing speak)

This data will be used by copywriters to write ads that sound like real people, and by strategists to identify unaddressed objections.

## THE BRAND
- Name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}
- Niche: {niche}
- Services: {services_str}
- Overview: {brand_overview}

## IDENTITY VERIFICATION (CRITICAL)
Multiple businesses may share the name "{brand_name}". You MUST only return threads discussing the EXACT business described above:
1. **Location match**: Discussions must be about {brand_name} in {location}. A thread about a different "{brand_name}" in another city/country is a DIFFERENT business — EXCLUDE it.
2. **Website/domain match**: If a thread links to a website, it should match {domain}. If it links to a different website, it's the wrong business.
3. **Service match**: The business discussed must match the services above ({services_str}). A salon vs. an app vs. a clinic are different businesses even with the same name.

If you are NOT confident a thread is about THIS specific business, EXCLUDE IT.

## YOUR TASK
Search for REAL public discussion threads ONLY on these forums: {domains_str}

CRITICAL: Only return threads from these forum domains. Do NOT return results from news sites, magazines, blogs, the brand's own website ({domain}), or any other non-forum source.

Use these search queries as guidance (grouped by intent):
{query_section}

For each relevant thread you find, return:
- The EXACT URL to the thread (must be on reddit.com, quora.com, or another forum listed above)
- The domain (e.g., reddit.com, quora.com)
- The thread title
- An excerpt of the MOST relevant part (max 280 chars, using the EXACT words people wrote — do NOT paraphrase or clean up)
- Estimated comment count if visible
- Which query led you to find it
- A relevance score (0-100) based on how useful this thread is for understanding customer language

## EXCLUDED SOURCES — DO NOT INCLUDE:
- ANY website that is NOT a forum/community: no news articles, no press, no magazine sites, no blogs, no brand websites
- The brand's own website: {domain}
- Review platforms: {excluded_str}
- Employee/job sites: glassdoor.com, indeed.com, etc.
- News/press: graziamagazine.com, vogue.com, forbes.com, bloomberg.com, gulfnews.com, etc.
- Product listing pages or directories (justdial.com, sulekha.com, etc.)
- Threads about a DIFFERENT business that happens to share the name "{brand_name}"

## OUTPUT FORMAT (JSON only — no markdown, no explanation)

{{
  "threads": [
    {{
      "url": "https://www.reddit.com/r/...",
      "domain": "reddit.com",
      "title": "Thread title as it appears",
      "published_at": "2024-03 or null if unknown",
      "query_used": "the search query that found this",
      "excerpt": "EXACT verbatim excerpt from the thread — do NOT rewrite (max 280 chars)",
      "comment_count_est": 45,
      "relevance_score_0_100": 78
    }}
  ],
  "domains_searched": ["reddit.com", "quora.com"],
  "queries_that_found_results": ["query1", "query2"]
}}

## HARD RULES
1. MAX 40 threads total
2. Every URL must be from a REAL FORUM (reddit.com, quora.com, stackexchange.com, etc.) — NOT news sites, magazines, blogs, directories, or the brand's own website
3. Excerpts must be VERBATIM — copy the exact words people wrote, including typos and slang
4. Only include threads that are genuinely relevant to {brand_name}'s category/services in {location}
5. Prioritize threads with more engagement (comments/upvotes)
6. Recency matters: prefer threads from the last 2 years
7. Do NOT include threads that are just marketing spam or self-promotion
8. VERIFY every thread is about THIS specific {brand_name} in {location} — not a different business with the same name
9. If you find ZERO relevant forum threads, return an empty threads array — do NOT substitute with non-forum sources"""


def build_synthesis_prompt(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    threads: List[Dict[str, Any]],
    optional_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Build Call 2: synthesize themes + language from threads."""

    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else "not specified"

    # Build thread context
    thread_context = ""
    for i, t in enumerate(threads[:30]):
        domain_name = t.get("domain", "")
        title = t.get("title", "untitled")
        excerpt = t.get("excerpt", "")
        url = t.get("url", "")
        thread_context += f"\n[{i+1}] {domain_name} — \"{title}\"\n    Excerpt: \"{excerpt}\"\n    URL: {url}\n"

    # Optional context from other modules
    extra_context = ""
    if optional_context:
        pains = optional_context.get("pains", [])
        weaknesses = optional_context.get("review_weaknesses", [])
        if pains:
            extra_context += "\n\n## KNOWN CUSTOMER PAINS (from Customer Intel module)\n"
            for p in pains[:5]:
                extra_context += f"- {p}\n"
        if weaknesses:
            extra_context += "\n## KNOWN REVIEW COMPLAINTS (from Reviews module)\n"
            for w in weaknesses[:5]:
                extra_context += f"- {w}\n"

    return f"""You are a community intelligence analyst working for a performance marketing agency. You have been given real forum threads discussing topics relevant to this brand's category. Your job is to extract actionable intelligence from these discussions.

## WHY THIS MATTERS
The themes, language, and insights you extract will be used by:
- **Copywriters** to write ad copy that uses the EXACT language real people use
- **Strategists** to identify unaddressed objections and untapped desires
- **Media buyers** to understand what messaging will resonate

## THE BRAND
- Name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}
- Niche: {niche}
- Services: {services_str}
- Overview: {brand_overview}
{extra_context}

## FORUM THREADS TO ANALYZE
{thread_context}

## YOUR TASK
From these threads, extract:

1. **Themes** — recurring patterns across threads, categorized by type
2. **Language Bank** — exact phrases and words real people use when discussing this category
3. **Audience Notes** — observations about who these people are, what they care about
4. **Creative Implications** — what messaging must address based on these discussions (NOT strategy — just observations)
5. **Gaps to Research** — questions that came up but weren't answered well

## OUTPUT FORMAT (JSON only — no markdown, no explanation)

{{
  "themes": [
    {{
      "label": "2-4 word label (e.g., 'Price transparency anxiety')",
      "type": "pain | objection | desire | trigger | comparison | how_to",
      "frequency": "high | medium | low",
      "evidence": [
        "EXACT verbatim quote from a thread (max 140 chars, copy exact words — keep typos/slang)",
        "Another verbatim quote"
      ],
      "source_urls": ["url1", "url2"]
    }}
  ],
  "language_bank": {{
    "phrases": [
      "exact phrase people use (max 80 chars) — copy verbatim from threads"
    ],
    "words": [
      "1-3 word term people use repeatedly"
    ]
  }},
  "audience_notes": [
    "Observation about the audience (max 120 chars) — grounded in what you read"
  ],
  "creative_implications": [
    "What ad messaging must address based on these discussions (max 120 chars, NOT strategy)"
  ],
  "gaps_to_research": [
    "Question that came up but wasn't well-answered (max 120 chars)"
  ]
}}

## HARD RULES
1. themes: MAX 10. Each must have at least 1 evidence quote and 1 source URL
2. language_bank.phrases: MAX 20. Each must be VERBATIM from a real thread — do NOT clean up or make it sound professional
3. language_bank.words: MAX 30. Real terms people use (not marketing jargon)
4. audience_notes: MAX 6 bullets. Each grounded in observed behavior from threads
5. creative_implications: MAX 6. State what messaging needs to address — do NOT write the messaging itself
6. gaps_to_research: MAX 6. Genuine unanswered questions from the threads
7. Evidence quotes MUST be EXACT words from the threads provided — including informal language, typos, abbreviations
8. Every theme must include source_urls pointing to actual threads from the list above

## STRICTLY FORBIDDEN
- Cleaning up, polishing, or professionalizing people's real language
- Inventing quotes that aren't from the provided threads
- Marketing advice, campaign plans, budget recommendations, scripts
- Generic themes like "quality concerns" or "good value" without specific evidence
- Phrases like "leverage", "capitalize", "run a campaign"
- Any form of action plans or strategy recommendations"""


# ============== API CALLS ==============

async def _call_perplexity(prompt: str, system_msg: str, max_tokens: int = 3000) -> Optional[Dict[str, Any]]:
    """Make a single Perplexity API call with 1 retry."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        logger.error("[COMMUNITY] PERPLEXITY_API_KEY not set")
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
                    logger.error(f"[COMMUNITY] Non-retryable error: {response.status_code}")
                    return None

                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]
                tokens = result.get("usage", {}).get("total_tokens", 0)

                parsed = _parse_json(content)
                if parsed:
                    parsed["_tokens"] = tokens
                    return parsed

                logger.warning(f"[COMMUNITY] Malformed JSON on attempt {attempt + 1}")
                if attempt == 0:
                    payload["messages"][-1]["content"] += "\n\nIMPORTANT: Your previous response was not valid JSON. Return ONLY a valid JSON object."
                    await asyncio.sleep(RETRY_DELAY)
                    continue

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"[COMMUNITY] API error on attempt {attempt + 1}: {e}")
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.error(f"[COMMUNITY] Unexpected error: {e}")
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

    logger.error(f"[COMMUNITY] Failed to parse JSON: {text[:300]}")
    return None


async def fetch_community_discovery(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    query_plan: Dict[str, Any],
    broad_search: bool = False,
) -> Optional[Dict[str, Any]]:
    """Call 1: Discover forum threads.
    broad_search=True: searches for category-level discussions instead of brand-specific."""

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

    if broad_search:
        location = f"{city}, {country}" if city else country
        services_str = ", ".join(services[:6]) if services else subcategory
        prompt = f"""Find forum discussions, Reddit threads, and community posts about this CATEGORY (not necessarily this specific brand).

## CATEGORY
- Industry: {subcategory} / {niche}
- Location context: {location}
- Relevant services: {services_str}

## SEARCH STRATEGY
Search for threads where people discuss:
1. Their experience with {niche} services in {location} (e.g., "best {niche} in {city}" or "{subcategory} recommendations {city}")
2. Common problems and complaints about {subcategory} services
3. How people choose between different {niche} providers
4. Price expectations and budget discussions for {subcategory}
5. Tips and advice threads about {niche}

## TARGET FORUMS
Search Reddit, Quora, local community forums, Facebook groups, and any niche forums for {subcategory}.

## OUTPUT FORMAT (JSON only)
{{
  "threads": [
    {{
      "url": "Direct URL to the thread",
      "title": "Thread title",
      "source": "reddit | quora | facebook_group | forum_name",
      "subreddit_or_community": "r/dubai or community name",
      "snippet": "Key excerpt (50-100 words) showing the most relevant discussion content",
      "relevance": "high | medium",
      "sentiment": "positive | negative | mixed | neutral",
      "identity_verified": true,
      "identity_note": "Category-level thread, not brand-specific"
    }}
  ],
  "total_found": 0,
  "search_coverage": "Description of what you searched"
}}"""

    system_msg = (
        "You are a community intelligence analyst. "
        "Find real public forum and community discussions relevant to this brand. "
        "Return only valid JSON. Be thorough — search across all specified forum domains."
    )

    logger.info(f"[COMMUNITY] Call 1 (Discovery{' - BROAD' if broad_search else ''}): {brand_name}, {query_plan.get('total_queries', 0)} queries")
    return await _call_perplexity(prompt, system_msg, max_tokens=3500)


async def fetch_community_synthesis(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    threads: List[Dict[str, Any]],
    optional_context: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Call 2: Synthesize themes + language from threads."""

    prompt = build_synthesis_prompt(
        brand_name=brand_name,
        domain=domain,
        city=city,
        country=country,
        subcategory=subcategory,
        niche=niche,
        services=services,
        brand_overview=brand_overview,
        threads=threads,
        optional_context=optional_context,
    )

    system_msg = (
        "You are a community intelligence analyst working for a performance marketing agency. "
        "Extract themes, verbatim language, and audience insights from real forum discussions. "
        "Return only valid JSON. Every quote must be exact words from the threads provided."
    )

    logger.info(f"[COMMUNITY] Call 2 (Synthesis): {brand_name}, {len(threads)} threads")
    return await _call_perplexity(prompt, system_msg, max_tokens=4000)
