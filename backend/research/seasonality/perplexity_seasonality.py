"""
Novara Research Foundation: Seasonality Perplexity Module
Uses Perplexity sonar for real-time seasonality intelligence

Version 2.1 - Feb 2026
- "Buying Moments" prompt: who/why_now/buy_triggers/must_answer/best_channels
- Grounded with Campaign (Step 1) and Business DNA (Step 2) inputs
- Hard rules against strategy, budgets, and generic social media trends
"""

import logging
import json
import os
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar"
TEMPERATURE = 0.2


def build_seasonality_prompt(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    price_range: Optional[Dict[str, Any]] = None
) -> str:
    """Build the v2.1 prompt for buying moments analysis"""

    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else "not specified"

    price_context = ""
    if price_range and price_range.get("avg"):
        currency = price_range.get("currency", "")
        avg = price_range.get("avg", 0)
        min_p = price_range.get("min", 0)
        max_p = price_range.get("max", 0)
        price_context = f"\n- Average ticket size: {currency} {avg} (range: {min_p} - {max_p})"

    return f"""You are a consumer behavior researcher. Your job is to identify **buying moments** — specific windows in the year when real people are most likely to purchase services like those described below.

A "buying moment" is NOT a generic holiday or social media trend. It is a **specific time window where a specific type of person has a specific reason to buy NOW.**

## BUSINESS CONTEXT
- Brand: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}
- Niche: {niche}
- Services: {services_str}{price_context}
- Overview: {brand_overview}

## WHY THIS MATTERS
This seasonality data will be used by:
- **Media buyers** to build a 12-month campaign calendar with budget allocation per moment
- **Ad copywriters** to write time-sensitive hooks that reference the buyer's real-world situation
- **Strategists** to plan creative production and launch timing around peak demand windows

Generic seasonal trends like "summer is busy" are useless. We need moments specific enough that a media buyer could set up a campaign flight around them TODAY.

## YOUR TASK
Identify 4-8 buying moments for this business in {location}. For each moment, answer:
1. WHO is buying? (be specific — not "everyone" or "consumers")
2. WHY NOW? (what makes this window special — not "people want to look good")
3. What TRIGGERS the purchase decision? (real-world events, not marketing campaigns)
4. What MUST be answered before the buyer commits? (their #1 concern)
5. Where can you REACH them during this window? (specific channels, not "social media")

## OUTPUT FORMAT
Return ONLY this JSON (no markdown, no explanation):

{{
  "key_moments": [
    {{
      "moment": "Name of the buying moment (e.g., Wedding Season, Back to School, Ramadan Prep)",
      "window": "When this occurs (e.g., March-May, First 2 weeks of September)",
      "demand": "high | medium | moderate",
      "who": "Who specifically is buying during this moment (under 80 chars)",
      "why_now": "Why this specific window triggers buying behavior (under 120 chars)",
      "buy_triggers": ["specific real-world trigger 1", "specific trigger 2", "specific trigger 3"],
      "must_answer": "The #1 question or concern the buyer needs resolved before purchasing (under 100 chars)",
      "best_channels": ["channel 1", "channel 2"],
      "lead_time": "How far in advance people start searching or booking (e.g., 2-4 weeks before, 1-2 months ahead)"
    }}
  ],
  "evergreen_demand": [
    "Year-round reason people buy this service regardless of season (be specific, not generic)"
  ],
  "weekly_patterns": {{
    "peak_days": ["day1", "day2"],
    "why": "explanation of weekly demand pattern (under 100 chars)"
  }},
  "local_insights": [
    "Specific cultural, religious, or regional factor in {location} that affects demand timing"
  ]
}}

## HARD RULES
1. Return 4-8 key_moments, ordered by demand (highest first)
2. Be specific to {location} — include local holidays, cultural events, weather patterns
3. "who" must name a specific person type — NOT "consumers", "customers", "people", "everyone"
4. "buy_triggers" must be real-world events — NOT "social media posts", "influencer content", "marketing campaigns"
5. "best_channels" must be specific — NOT just "social media" or "online". Use: "Google Search", "Instagram Reels", "WhatsApp groups", "Local radio", "YouTube pre-roll", "Meta retargeting", etc.
6. "must_answer" should reflect a real buyer concern — cost, quality, timing, trust
7. Every "why_now" must reference a TIME-BOUND reason (deadline, event, weather change, cultural moment)
8. Each buy_trigger must be 3-10 words and describe a SPECIFIC event or realization
9. "lead_time" must describe how far BEFORE the moment people start searching/booking (e.g., "2-4 weeks before", "1-2 months ahead", "same week"). If unknown, use ""

## STRICTLY FORBIDDEN (do NOT include any of these)
- Budget recommendations or spending advice
- Marketing strategy, campaign plans, or "how to capitalize" suggestions
- Ad scripts, copy suggestions, or creative writing
- Phrases like "run a campaign", "allocate budget", "create ads", "leverage", "capitalize"
- Generic moments like "Year-round demand" or "Social media trends" as key_moments
- "who" values like "general consumers", "broad audience", "anyone interested"
- "buy_triggers" like "social media exposure", "influencer recommendations", "targeted ads"
- Strategy advice of any kind — only describe WHAT HAPPENS, WHO, and WHEN

## QUALITY CHECK
Before returning, verify each moment passes this test:
- Could a media buyer use this to set up a campaign calendar? (specific dates)
- Could a copywriter use "who" + "why_now" to write a targeted ad? (specific person + motivation)
- Could a sales team use "must_answer" to handle objections? (specific concern)
If any moment fails these tests, remove it and replace with a better one."""


async def call_perplexity_seasonality(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    price_range: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Call Perplexity API for buying moments analysis.

    Returns:
        Dict with key_moments, evergreen_demand, weekly_patterns, local_insights
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not set")

    prompt = build_seasonality_prompt(
        brand_name=brand_name,
        domain=domain,
        city=city,
        country=country,
        subcategory=subcategory,
        niche=niche,
        services=services,
        brand_overview=brand_overview,
        price_range=price_range
    )

    logger.info(f"[SEASONALITY] Calling Perplexity for {brand_name} in {city}, {country}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a consumer behavior researcher. Return only valid JSON. Be specific and data-driven. Never include strategy, budgets, or marketing recommendations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": TEMPERATURE,
        "max_tokens": 4000
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            logger.error(f"[SEASONALITY] Perplexity API error: {response.status_code} - {response.text}")
            raise Exception(f"Perplexity API error: {response.status_code}")

        data = response.json()

    # Extract content
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Clean and parse JSON
    content = content.strip()

    # Remove markdown code blocks if present
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        result = json.loads(content)
        logger.info(f"[SEASONALITY] Got {len(result.get('key_moments', []))} buying moments")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"[SEASONALITY] JSON parse error: {e}")
        logger.error(f"[SEASONALITY] Raw content: {content[:500]}")
        return {
            "key_moments": [],
            "evergreen_demand": [],
            "weekly_patterns": {},
            "local_insights": []
        }
