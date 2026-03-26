"""
Novara Research Foundation: Customer Intel — Perplexity Client
Version 1.1 - Feb 2026

Lean prompt grounded in offer catalog + search demand phrases.
Hard rules against fluff, personas, strategy.
1 automatic retry on failure.
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


def build_input_context(
    step1: Dict[str, Any],
    step2: Dict[str, Any],
    search_demand: Optional[Dict[str, Any]],
    seasonality: Optional[Dict[str, Any]],
    competitors: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Extract structured inputs for prompt construction."""

    geo = step1.get("geo", {})
    city = geo.get("city_or_region", "")
    country = geo.get("country", "")
    goal = step1.get("goal", {})
    primary_goal = goal.get("primary_goal", "")
    destination = step1.get("destination", {})
    destination_type = destination.get("type", "")

    classification = step2.get("classification", {})
    offer = step2.get("offer", {})
    brand_summary = step2.get("brand_summary", {})
    pricing = step2.get("pricing", {})
    channels = step2.get("channels", {})

    # Offer catalog names
    offer_catalog = []
    for item in offer.get("offer_catalog", [])[:10]:
        name = item.get("name", "")
        if name and name.lower() != "unknown":
            offer_catalog.append(name)

    # Pricing summary
    pricing_summary = ""
    if pricing.get("count", 0) > 0:
        currency = pricing.get("currency", "")
        avg = pricing.get("avg", 0)
        min_p = pricing.get("min", 0)
        max_p = pricing.get("max", 0)
        pricing_summary = f"{currency} {min_p}-{max_p} (avg {avg})"

    # Channels
    channels_found = []
    for s in channels.get("social", []):
        if isinstance(s, dict):
            channels_found.append(s.get("platform", ""))
        elif isinstance(s, str):
            channels_found.append(s)
    for m in channels.get("messaging", []):
        if isinstance(m, dict):
            channels_found.append(m.get("platform", ""))
        elif isinstance(m, str):
            channels_found.append(m)

    # Search demand phrases (combine top_10 + bucket queries, cap 30)
    search_phrases = []
    if search_demand:
        top10 = search_demand.get("top_10_queries", [])[:10]
        search_phrases.extend(top10)
        buckets = search_demand.get("intent_buckets", {})
        for bucket_name in ["price", "trust", "urgency", "comparison"]:
            for q in buckets.get(bucket_name, [])[:5]:
                if q not in search_phrases:
                    search_phrases.append(q)
        # Cap at 30
        search_phrases = search_phrases[:30]

    # Seasonality brief
    seasonality_brief = []
    if seasonality:
        for m in seasonality.get("key_moments", [])[:6]:
            moment_name = m.get("moment", m.get("name", ""))
            window = m.get("window", m.get("time_window", ""))
            lead_time = m.get("lead_time", "")
            line = f"{moment_name} ({window})"
            if lead_time:
                line += f" — lead time: {lead_time}"
            seasonality_brief.append(line)

    # Competitors brief
    competitors_brief = []
    if competitors:
        for c in competitors.get("competitors", [])[:3]:
            name = c.get("name", "")
            positioning = c.get("positioning_summary", c.get("what_they_do", ""))
            if name:
                competitors_brief.append(f"{name}: {positioning}")

    return {
        "brand_name": brand_summary.get("name", ""),
        "tagline": brand_summary.get("tagline", ""),
        "one_liner": brand_summary.get("one_liner", ""),
        "city": city,
        "country": country,
        "goal": primary_goal,
        "destination_type": destination_type,
        "niche": classification.get("niche", ""),
        "subcategory": classification.get("subcategory", ""),
        "offer_catalog": offer_catalog,
        "pricing_summary": pricing_summary,
        "channels_found": channels_found,
        "search_phrases": search_phrases,
        "seasonality_brief": seasonality_brief,
        "competitors_brief": competitors_brief,
    }


def build_prompt(ctx: Dict[str, Any]) -> str:
    """Build the v1.1 Customer Intel prompt."""

    offer_list = "\n".join(f"  - {o}" for o in ctx["offer_catalog"]) if ctx["offer_catalog"] else "  (none extracted)"
    search_list = "\n".join(f"  - {s}" for s in ctx["search_phrases"][:20]) if ctx["search_phrases"] else "  (none available — Search Demand not run)"
    seasonality_list = "\n".join(f"  - {s}" for s in ctx["seasonality_brief"]) if ctx["seasonality_brief"] else "  (not available)"
    competitors_list = "\n".join(f"  - {c}" for c in ctx["competitors_brief"]) if ctx["competitors_brief"] else "  (not available)"
    channels_str = ", ".join(ctx["channels_found"][:6]) if ctx["channels_found"] else "unknown"

    return f"""You are a customer intelligence researcher working for a performance marketing agency. Your job is to map out WHO buys this brand's services, WHY they buy, and WHAT language they use when searching.

## WHY THIS MATTERS
This customer intel will be used by:
- **Ad copywriters** to write hooks, headlines, and body copy that match real buyer language
- **Media buyers** to build audience segments and targeting criteria
- **Strategists** to identify which pain points and triggers to lead with in campaigns

Generic insights like "customers want quality" are useless. We need specifics that someone could paste into an ad brief TODAY.

Return ONLY the JSON below. No extra keys. No markdown.

## BUSINESS CONTEXT
- Brand: {ctx["brand_name"]}
- Tagline: {ctx["tagline"]}
- One-liner: {ctx["one_liner"]}
- Location: {ctx["city"]}, {ctx["country"]}
- Goal: {ctx["goal"]}
- Destination: {ctx["destination_type"]}
- Niche: {ctx["niche"]} / {ctx["subcategory"]}
- Pricing: {ctx["pricing_summary"] or "unknown"}
- Active channels: {channels_str}

## OFFER CATALOG (from website)
{offer_list}

## REAL SEARCH PHRASES (from Google Suggest)
{search_list}

## SEASONALITY (buying moments)
{seasonality_list}

## COMPETITORS
{competitors_list}

## OUTPUT FORMAT (strict JSON)
Return ONLY this JSON:

{{
  "summary_bullets": ["3 short insights about who buys and why (max 90 chars each)"],
  "segments": [
    {{
      "segment_name": "2-4 word name (max 48 chars)",
      "jtbd": "What they're trying to accomplish (max 120 chars)",
      "core_motives": ["up to 3 motivations (max 90 chars each)"],
      "top_pains": ["up to 3 pain points (max 90 chars each)"],
      "top_objections": ["up to 3 objections (max 90 chars each)"],
      "best_proof": ["up to 3 proof types that convince this segment (max 90 chars each)"],
      "risk_reducers": ["up to 3 things that reduce perceived risk (max 90 chars each)"],
      "best_offer_items": ["1-3 items from the OFFER CATALOG above that this segment wants most"],
      "best_channel_focus": ["1-2 specific channels to reach this segment"],
      "search_language": ["3-6 phrases from REAL SEARCH PHRASES above that this segment would use"]
    }}
  ],
  "trigger_map": {{
    "moment_triggers": ["up to 5 life moments that trigger buying"],
    "urgency_triggers": ["up to 5 time-sensitive triggers"],
    "planned_triggers": ["up to 5 planned/scheduled triggers"]
  }},
  "language_bank": {{
    "desire_phrases": ["up to 12 phrases expressing desire for this service"],
    "anxiety_phrases": ["up to 12 phrases expressing fear/concern"],
    "intent_phrases": ["up to 12 phrases showing ready-to-buy intent"]
  }}
}}

## HARD RULES
1. Segments: MAX 3. Only as many as the data supports.
2. Each segment MUST reference >= 1 item from OFFER CATALOG in best_offer_items (use exact names from the list above).
3. Each segment MUST reference >= 2 phrases from REAL SEARCH PHRASES in search_language (exact or near-exact from the list above).
4. If REAL SEARCH PHRASES is empty, set search_language to [].
5. All bullets/strings max 90 chars. jtbd max 120 chars.
6. Avoid generic filler: do NOT use "premium", "high-quality", "best-in-class", "top-notch" unless those exact words appear in the search phrases.
7. best_channel_focus must be specific: "Instagram Reels", "Google Search", "WhatsApp" — not just "social media".

## QUALITY CHECK
Before returning, verify each segment passes this test:
- Could a copywriter use "jtbd" + "core_motives" to write a Facebook ad headline? (specific enough?)
- Could a media buyer use "best_channel_focus" + "search_language" to set up targeting? (actionable?)
- Could a strategist use "top_objections" + "risk_reducers" to brief a landing page? (concrete?)
If any segment fails these tests, rewrite it with more specificity.

## STRICTLY FORBIDDEN
- Personas, fictional names, scenarios, or stories
- Decision speed or price sensitivity labels
- Budget recommendations or spending advice
- Marketing strategy, campaign plans, or "how to capitalize" advice
- Ad scripts, copy suggestions, or creative writing
- CTA suggestions per trigger
- Phrases like "run a campaign", "allocate budget", "create ads", "leverage", "capitalize"
- Any form of recommendations or action plans — only describe WHO, WHY, and WHAT CONCERNS THEM"""


async def fetch_customer_intel(
    step1: Dict[str, Any],
    step2: Dict[str, Any],
    search_demand: Optional[Dict[str, Any]] = None,
    seasonality: Optional[Dict[str, Any]] = None,
    competitors: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Call Perplexity sonar for Customer Intel v1.1.
    1 automatic retry on failure (network/5xx/malformed JSON).
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        logger.error("[CUSTOMER_INTEL] PERPLEXITY_API_KEY not set")
        return None

    # Build structured inputs
    ctx = build_input_context(step1, step2, search_demand, seasonality, competitors)
    prompt = build_prompt(ctx)

    # Track missing inputs
    missing_inputs = []
    if not search_demand:
        missing_inputs.append("search_demand")
    if not seasonality:
        missing_inputs.append("seasonality")
    if not competitors:
        missing_inputs.append("competitors")

    logger.info(f"[CUSTOMER_INTEL] Calling Perplexity sonar v1.1 (missing: {missing_inputs})")
    logger.info(f"[CUSTOMER_INTEL] Offer catalog: {len(ctx['offer_catalog'])} items, Search phrases: {len(ctx['search_phrases'])}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a customer intelligence researcher working for a performance marketing agency. Your output feeds directly into ad creative briefs and audience targeting. Return ONLY valid JSON. No markdown, no commentary. Be specific to the business context."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 4000
    }

    retry_count = 0
    last_error = None

    for attempt in range(2):  # max 2 attempts (1 original + 1 retry)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(PERPLEXITY_URL, headers=headers, json=payload)

                # Don't retry auth or rate limit errors
                if response.status_code in (401, 403, 429):
                    logger.error(f"[CUSTOMER_INTEL] Non-retryable error: {response.status_code}")
                    return None

                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                parsed = _parse_json_response(content)
                if parsed:
                    parsed["_missing_inputs"] = missing_inputs
                    parsed["_llm_model"] = PERPLEXITY_MODEL
                    parsed["_llm_tokens"] = result.get("usage", {}).get("total_tokens", 0)
                    parsed["_retry_count"] = retry_count
                    parsed["_offer_catalog"] = ctx["offer_catalog"]
                    parsed["_search_phrases"] = ctx["search_phrases"]
                    logger.info(f"[CUSTOMER_INTEL] Success: {len(parsed.get('segments', []))} segments (attempt {attempt + 1})")
                    return parsed

                # JSON parse failed — retry with hint
                logger.warning(f"[CUSTOMER_INTEL] Malformed JSON on attempt {attempt + 1}")
                if attempt == 0:
                    retry_count += 1
                    payload["messages"][-1]["content"] += "\n\nIMPORTANT: Your previous response was not valid JSON. Return ONLY a valid JSON object."
                    await asyncio.sleep(RETRY_DELAY)
                    continue

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            last_error = e
            logger.warning(f"[CUSTOMER_INTEL] API error on attempt {attempt + 1}: {e}")
            if attempt == 0:
                retry_count += 1
                await asyncio.sleep(RETRY_DELAY)
                continue

        except Exception as e:
            last_error = e
            logger.error(f"[CUSTOMER_INTEL] Unexpected error: {e}")
            break

    logger.error(f"[CUSTOMER_INTEL] All attempts failed. Last error: {last_error}")
    return None


def _parse_json_response(content: str) -> Optional[Dict[str, Any]]:
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

    logger.error(f"[CUSTOMER_INTEL] Failed to parse JSON: {text[:300]}")
    return None
