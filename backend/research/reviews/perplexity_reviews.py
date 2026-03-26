"""
Novara Research Foundation: Reviews & Reputation — Perplexity Client
Version 1.5 - Feb 2026

2-call pipeline:
  Call 1 (Discovery): Find all review platforms, URLs, ratings, counts, recency, owner response
  Call 2 (Analysis): Extract themes, quotes, strengths, weaknesses, brand vs reality
Geo-aware + niche-aware platform targeting.
App store detection via Step 2 channels.
1 automatic retry on failure per call.
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

# ============== GEO-AWARE PLATFORM MAPPING ==============

GEO_REVIEW_PLATFORMS = {
    "UAE": ["Google Maps", "Facebook", "Tripadvisor", "Zomato", "Talabat"],
    "United Arab Emirates": ["Google Maps", "Facebook", "Tripadvisor", "Zomato", "Talabat"],
    "Saudi Arabia": ["Google Maps", "Facebook", "Tripadvisor", "HungerStation"],
    "Qatar": ["Google Maps", "Facebook", "Tripadvisor", "Zomato"],
    "Bahrain": ["Google Maps", "Facebook", "Tripadvisor", "Zomato"],
    "Kuwait": ["Google Maps", "Facebook", "Tripadvisor", "Zomato"],
    "Oman": ["Google Maps", "Facebook", "Tripadvisor"],
    "Egypt": ["Google Maps", "Facebook", "Tripadvisor", "Elmenus"],
    "United States": ["Google Maps", "Yelp", "BBB", "Facebook", "Tripadvisor"],
    "United Kingdom": ["Google Maps", "Trustpilot", "Yell", "Facebook", "Tripadvisor"],
    "Canada": ["Google Maps", "Yelp", "Facebook", "Tripadvisor", "BBB"],
    "Australia": ["Google Maps", "Yelp", "Facebook", "Tripadvisor", "ProductReview.com.au"],
    "India": ["Google Maps", "Justdial", "Sulekha", "Facebook", "Zomato", "Practo"],
    "Singapore": ["Google Maps", "Facebook", "Tripadvisor", "Yelp"],
    "Germany": ["Google Maps", "Trustpilot", "Facebook", "Tripadvisor"],
    "France": ["Google Maps", "Trustpilot", "Facebook", "Tripadvisor", "PagesJaunes"],
    "Pakistan": ["Google Maps", "Facebook", "Daraz"],
    "Malaysia": ["Google Maps", "Facebook", "Tripadvisor"],
    "Thailand": ["Google Maps", "Facebook", "Tripadvisor"],
    "Indonesia": ["Google Maps", "Facebook", "Tripadvisor"],
    "Philippines": ["Google Maps", "Facebook", "Tripadvisor"],
    "South Africa": ["Google Maps", "Facebook", "Tripadvisor", "HelloPeter"],
    "Nigeria": ["Google Maps", "Facebook"],
    "Turkey": ["Google Maps", "Facebook", "Tripadvisor"],
    "Japan": ["Google Maps", "Tabelog", "Facebook", "Tripadvisor"],
    "South Korea": ["Google Maps", "Naver", "KakaoMap", "Facebook"],
}

DEFAULT_PLATFORMS = ["Google Maps", "Facebook", "Trustpilot", "Tripadvisor", "Yelp"]

NICHE_REVIEW_PLATFORMS = {
    "restaurant": ["Zomato", "Tripadvisor", "OpenTable", "TheFork"],
    "cafe": ["Zomato", "Tripadvisor", "Foursquare"],
    "food": ["Zomato", "Tripadvisor", "OpenTable"],
    "hotel": ["Tripadvisor", "Booking.com", "Hotels.com", "Expedia"],
    "hospitality": ["Tripadvisor", "Booking.com"],
    "medical": ["Healthgrades", "Practo", "RateMDs", "Zocdoc"],
    "dental": ["Healthgrades", "Zocdoc", "RateMDs"],
    "clinic": ["Healthgrades", "Practo", "Zocdoc"],
    "healthcare": ["Healthgrades", "Practo", "WebMD"],
    "legal": ["Avvo", "Lawyers.com", "Martindale"],
    "software": ["G2", "Capterra", "TrustRadius", "ProductHunt"],
    "saas": ["G2", "Capterra", "TrustRadius"],
    "ecommerce": ["Trustpilot", "Sitejabber", "ResellerRatings"],
    "fitness": ["ClassPass", "MindBody"],
    "gym": ["ClassPass", "MindBody"],
    "beauty": ["Fresha", "Booksy", "StyleSeat"],
    "salon": ["Fresha", "Booksy", "StyleSeat"],
    "spa": ["Tripadvisor", "Fresha", "Yelp"],
    "automotive": ["Cars.com", "DealerRater", "Edmunds"],
    "real estate": ["Zillow", "Realtor.com"],
    "education": ["Course Report", "SwitchUp", "Niche"],
    "financial": ["NerdWallet", "Bankrate"],
    "travel": ["Tripadvisor", "Booking.com"],
}

# App store platform names (for is_app_store detection)
APP_STORE_PLATFORMS = {"Apple App Store", "Google Play Store", "App Store", "Google Play", "Play Store"}


def get_platforms_for_context(
    country: str, niche: str, subcategory: str,
    app_store_urls: Optional[List[str]] = None
) -> tuple:
    """
    Get geo-specific and niche-specific review platforms.
    Adds app store platforms if app store URLs are detected from Step 2.
    Returns (geo_platforms, niche_platforms, combined_unique)
    """
    geo_platforms = GEO_REVIEW_PLATFORMS.get(country, DEFAULT_PLATFORMS)

    niche_platforms = []
    niche_lower = niche.lower()
    subcat_lower = subcategory.lower()
    for key, platforms in NICHE_REVIEW_PLATFORMS.items():
        # Substring match: "beauty" in "on-demand beauty services"
        if key in niche_lower or key in subcat_lower:
            for p in platforms:
                if p not in niche_platforms:
                    niche_platforms.append(p)

    # Always include app stores if URLs are provided
    app_store_additions = []
    if app_store_urls:
        for url in app_store_urls:
            url_lower = url.lower()
            if "apple.com" in url_lower or "apps.apple.com" in url_lower:
                app_store_additions.append("Apple App Store")
            elif "play.google.com" in url_lower:
                app_store_additions.append("Google Play Store")

    # Even without URLs, always add app stores to the check list
    if "Apple App Store" not in app_store_additions:
        app_store_additions.append("Apple App Store")
    if "Google Play Store" not in app_store_additions:
        app_store_additions.append("Google Play Store")

    seen = set()
    combined = []
    for p in list(geo_platforms) + niche_platforms + app_store_additions:
        if p not in seen:
            combined.append(p)
            seen.add(p)

    return list(geo_platforms), niche_platforms, combined


# ============== PROMPT BUILDERS ==============

def build_discovery_prompt(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    platforms_to_check: List[str],
    app_store_urls: Optional[List[str]] = None
) -> str:
    """Build Call 1 prompt: discover review platforms with recency + owner response."""

    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else "not specified"
    platforms_str = ", ".join(platforms_to_check)

    app_store_hint = ""
    if app_store_urls:
        urls_str = "\n".join(f"  - {url}" for url in app_store_urls)
        app_store_hint = f"""

## KNOWN APP STORE LISTINGS
The brand has the following app store presence (from their website):
{urls_str}
Check these URLs for app ratings and review counts."""

    return f"""You are a reputation intelligence analyst working for a performance marketing agency. Your job is to find EVERY platform where this SPECIFIC brand has CUSTOMER reviews or ratings.

## WHY THIS MATTERS
Before writing ad copy, we need to know:
- Where the brand's social proof lives (which platforms have reviews)
- How many reviews exist and what the ratings are
- How RECENT the reviews are (stale reviews reduce credibility)
- Whether the business RESPONDS to reviews (shows engagement)
- Whether the brand has enough social proof to use in advertising

This data will be used by media buyers to assess social proof readiness and by copywriters to source real testimonials.

## THE BRAND (use ALL of these details to identify the correct business)
- Name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}
- Niche: {niche}
- Services: {services_str}
- Overview: {brand_overview}
{app_store_hint}

## IDENTITY VERIFICATION (CRITICAL)
Multiple businesses may share the name "{brand_name}". You MUST only return reviews for the EXACT business described above. For each listing you find, verify ALL of these before including it:
1. **Location match**: The listing must be for a business in or serving {location}. A listing in a different city or country is a DIFFERENT business. Exclude it.
2. **Website/domain match**: If the listing shows a website, it should match or relate to {domain}. If it links to a completely different website, it's the wrong business. Exclude it.
3. **Service match**: The business described in the listing should match the services above ({services_str}). If the listed business offers unrelated services (e.g., a restaurant vs a salon), it's the wrong one. Exclude it.
4. **Cross-reference**: When possible, cross-reference the address, phone number, or photos in the listing against the brand's website ({domain}) to confirm identity.

If you are NOT 100% confident a listing is for this specific business, EXCLUDE IT. It is far better to return zero platforms than to include the wrong business's reviews. A false match will corrupt the entire intelligence report.

## EXCLUDED SOURCES
Do NOT include these types of sites — they are NOT customer review platforms:
- Employee review sites: Indeed, Glassdoor, Ambitionbox, Naukri, Comparably, Kununu
- Job boards or career pages
- Social media posts that aren't formal reviews
- News articles or press mentions (these go in trust_signals, not here)

## YOUR TASK
Find ALL CUSTOMER review platforms where {brand_name} (website: {domain}, located in {location}) has reviews.

**Specifically check these platforms:** {platforms_str}

**Google Maps is CRITICAL for local service businesses.** Search Google Maps for "{brand_name} {location}" and also try variations like the brand name alone in {city}. Most local service businesses in {city} have a Google Maps listing even if other platforms don't cover them.

Also check any OTHER customer review platform where this brand might have reviews (industry directories, app stores, booking platforms, niche platforms like Fresha/Booksy for beauty, etc.).

For each platform where you find verified reviews:
1. The exact URL to their review/listing page
2. Their star rating (or equivalent score)
3. Approximate review count
4. Whether the reviews are real customer reviews (not just a listing)
5. **How recent** the most recent reviews appear to be
6. **Whether the business owner/brand responds** to reviews on this platform

## OUTPUT FORMAT (JSON only — no markdown, no explanation)

{{
  "platforms_found": [
    {{
      "platform": "Platform name (e.g., Google Maps, Yelp, Trustpilot, Apple App Store, Google Play Store)",
      "url": "Direct URL to the brand's review page on this platform",
      "approximate_rating": 4.6,
      "approximate_count": "230+",
      "has_reviews": true,
      "recency": "within_last_month | 1_3_months | 3_6_months | 6_months_plus | unknown",
      "owner_responds": true,
      "response_quality": "active | occasional | rare | none | unknown",
      "verification_note": "Brief note on how you verified this is the correct business"
    }}
  ],
  "platforms_checked_but_not_found": ["Platform names where the brand has NO presence"],
  "additional_platforms_discovered": ["Any platform not in the check list where reviews were found"],
  "excluded_wrong_business": ["Any listings found for a DIFFERENT business with the same name (include platform + city)"]
}}

## FIELD DEFINITIONS
- **recency**: When was the most recent review posted?
  - "within_last_month" = a review in the last 30 days
  - "1_3_months" = most recent review is 1-3 months old
  - "3_6_months" = most recent review is 3-6 months old
  - "6_months_plus" = most recent review is older than 6 months
  - "unknown" = cannot determine
- **owner_responds**: Does the business reply to reviews on this platform? true/false/null if unknown
- **response_quality**: How actively does the business respond?
  - "active" = responds to most reviews (both positive and negative)
  - "occasional" = responds to some reviews (mainly negative)
  - "rare" = only a few responses visible
  - "none" = no owner responses found
  - "unknown" = cannot determine

## RULES
1. Only include platforms where you found ACTUAL evidence of this SPECIFIC brand's presence in {location}
2. URLs must be specific to {brand_name}'s page on that platform (not the platform homepage)
3. If you can't find an exact rating, use null — do NOT guess
4. approximate_count should be a string like "50+", "100-200", "500+" — use null if unknown
5. has_reviews = true only if there are actual customer text reviews (not employee reviews, not just a rating)
6. When in doubt about identity, EXCLUDE the listing and add it to excluded_wrong_business
7. For App Store / Google Play: check if the brand has a mobile app with user reviews"""


def build_analysis_prompt(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    discovery_results: Dict[str, Any],
    competitor_names: List[str],
    brand_claims: Optional[List[str]] = None
) -> str:
    """Build Call 2 prompt: deep analysis of reviews + brand vs reality."""

    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else "not specified"

    platforms_found = discovery_results.get("platforms_found", [])
    platform_context = ""
    for p in platforms_found:
        rating = p.get("approximate_rating", "unknown")
        count = p.get("approximate_count", "unknown")
        url = p.get("url", "")
        platform_context += f"\n- {p.get('platform', '?')}: {rating} stars, ~{count} reviews ({url})"

    if not platform_context:
        platform_context = "\n- No review platforms found in discovery phase — search broadly for any reputation data"

    competitor_context = ""
    if competitor_names:
        comp_str = ", ".join(competitor_names[:3])
        competitor_context = f"""

## COMPETITORS TO COMPARE AGAINST
{comp_str}
For each competitor, find their primary review platform rating so we can compare reputation."""

    # Brand vs Reality section
    brand_claims_context = ""
    if brand_claims and len(brand_claims) > 0:
        claims_list = "\n".join(f"  {i+1}. \"{claim}\"" for i, claim in enumerate(brand_claims[:8]))
        brand_claims_context = f"""

## BRAND VS REALITY CHECK
The brand makes the following marketing claims on their website. For each claim, check if third-party reviews SUPPORT, CONTRADICT, or DON'T MENTION it:
{claims_list}

This comparison helps strategists know which brand promises are backed by real customer experience and which are just marketing."""

    return f"""You are a reputation intelligence analyst working for a performance marketing agency. Your job is to deeply analyze what real CUSTOMERS are saying about this SPECIFIC brand across review platforms.

## WHY THIS MATTERS
This reputation analysis will be used by:
- **Ad copywriters** to pull real customer quotes for testimonial ads and social proof headlines
- **Strategists** to identify strengths to amplify and weaknesses to pre-empt in messaging
- **Media buyers** to understand trust signals that matter to the target audience

We need SPECIFIC, REAL insights — not generic summaries. Every quote and theme must be grounded in actual customer review content.

## THE BRAND (use these details to verify you're analyzing the correct business)
- Name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}
- Niche: {niche}
- Services: {services_str}
- Overview: {brand_overview}

## IDENTITY VERIFICATION
Only analyze reviews that are for THIS specific business ({brand_name} at {domain} in {location}). If any platform below belongs to a different business with the same name (different city, different website, different services), SKIP it entirely.

## EXCLUDED SOURCES
- Do NOT use employee reviews from Indeed, Glassdoor, Ambitionbox, or similar job sites
- Do NOT use social media comments as formal reviews
- Only analyze CUSTOMER reviews from the platforms below

## REVIEW PLATFORMS FOUND (from discovery)
{platform_context}
{competitor_context}
{brand_claims_context}

## YOUR TASK
Analyze the reviews for {brand_name} across the platforms listed above. Extract:
1. **Reputation summary** — 3 bullet overview of the brand's reputation
2. **Strength themes** — What do customers CONSISTENTLY praise? With evidence quotes.
3. **Weakness themes** — What do customers CONSISTENTLY complain about? With evidence quotes and severity.
4. **Social proof snippets** — The best review quotes that could be used directly in advertising
5. **Trust signals** — Certifications, awards, years in business, notable mentions
6. **Competitor comparison** — How {brand_name}'s reputation stacks up against competitors
{"7. **Brand vs Reality** — Compare each brand claim against review evidence" if brand_claims else ""}

## OUTPUT FORMAT (JSON only — no markdown, no explanation)

{{
  "reputation_summary": [
    "3 concise bullets summarizing the brand's reputation (max 120 chars each)"
  ],
  "strength_themes": [
    {{
      "theme": "What customers praise (max 60 chars, be specific — NOT 'great service')",
      "evidence": ["Actual or closely paraphrased quote from a review (max 150 chars)", "Another quote"],
      "frequency": "frequent | moderate | occasional"
    }}
  ],
  "weakness_themes": [
    {{
      "theme": "What customers complain about (max 60 chars, be specific — NOT 'could improve')",
      "evidence": ["Actual or closely paraphrased quote from a review (max 150 chars)", "Another quote"],
      "frequency": "frequent | moderate | occasional",
      "severity": "minor | moderate | deal_breaker"
    }}
  ],
  "social_proof_snippets": [
    {{
      "quote": "A review quote compelling enough to use in an ad (max 180 chars). These are paraphrased from real reviews.",
      "platform": "Which platform this came from",
      "context": "What the reviewer was talking about (max 80 chars)"
    }}
  ],
  "trust_signals": [
    "Specific trust signal: certification, award, years in business, media mention (max 100 chars)"
  ],
  "competitor_reputation": [
    {{
      "name": "Competitor name",
      "approximate_rating": 4.2,
      "primary_platform": "Google Maps",
      "reputation_gap": "How {brand_name} compares — be specific (max 120 chars)"
    }}
  ]{''',
  "brand_vs_reality": [
    {{
      "claim": "The exact brand claim being checked",
      "review_alignment": "supported | partially_supported | contradicted | not_mentioned",
      "evidence": "Specific review evidence supporting this verdict (max 180 chars)"
    }}
  ]''' if brand_claims else ''}
}}

## HARD RULES
1. strength_themes: MAX 5. Each must be specific — NOT "good quality", "great experience", "highly recommend"
2. weakness_themes: MAX 4. If there are genuinely no complaints, return an empty array — do NOT invent weaknesses
3. social_proof_snippets: MAX 6. Each quote must sound like a REAL person wrote it (not polished marketing copy). ALL quotes are paraphrased from reviews — do NOT present them as exact verbatim quotes.
4. trust_signals: MAX 5. Only include signals you found evidence for — do NOT hallucinate awards or certifications
5. competitor_reputation: MAX 3. Only include competitors where you found actual review data
6. Evidence quotes are PARAPHRASED from real reviews — they should capture the spirit of what customers said
7. severity labels: "deal_breaker" = would stop someone from buying, "moderate" = concerning but not fatal, "minor" = nitpick
{"8. brand_vs_reality: Check EVERY claim provided. Use 'not_mentioned' if reviews don't address the claim at all." if brand_claims else ""}

## QUALITY CHECK
Before returning, verify:
- Could a copywriter paste any social_proof_snippet directly into a testimonial ad? (compelling enough?)
- Could a strategist use a weakness_theme to write an objection-handling FAQ? (specific enough?)
- Could a media buyer use trust_signals to decide which proof points to feature on a landing page? (credible?)
If any item fails these tests, replace it with a better one.

## STRICTLY FORBIDDEN
- Making up reviews or quotes that don't exist
- Using employee reviews (Indeed, Glassdoor, etc.) as customer reviews
- Including reviews from a DIFFERENT business that shares the same name
- Generic themes like "good service", "nice place", "would recommend" without specific evidence
- Trust signals you can't verify (don't invent awards)
- Marketing advice, strategy suggestions, or "how to improve" recommendations
- Phrases like "leverage", "capitalize", "run a campaign"
- Any form of action plans — only describe WHAT CUSTOMERS SAY"""


# ============== API CALLS ==============

async def _call_perplexity(prompt: str, system_msg: str, max_tokens: int = 3000) -> Optional[Dict[str, Any]]:
    """Make a single Perplexity API call with 1 retry."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        logger.error("[REVIEWS] PERPLEXITY_API_KEY not set")
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
                    logger.error(f"[REVIEWS] Non-retryable error: {response.status_code}")
                    return None

                response.raise_for_status()

                result = response.json()
                content = result["choices"][0]["message"]["content"]
                tokens = result.get("usage", {}).get("total_tokens", 0)

                parsed = _parse_json(content)
                if parsed:
                    parsed["_tokens"] = tokens
                    return parsed

                logger.warning(f"[REVIEWS] Malformed JSON on attempt {attempt + 1}")
                if attempt == 0:
                    payload["messages"][-1]["content"] += "\n\nIMPORTANT: Your previous response was not valid JSON. Return ONLY a valid JSON object."
                    await asyncio.sleep(RETRY_DELAY)
                    continue

        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"[REVIEWS] API error on attempt {attempt + 1}: {e}")
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY)
                continue
        except Exception as e:
            logger.error(f"[REVIEWS] Unexpected error: {e}")
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

    logger.error(f"[REVIEWS] Failed to parse JSON: {text[:300]}")
    return None


async def fetch_reviews_discovery(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    platforms_to_check: List[str],
    app_store_urls: Optional[List[str]] = None,
    broad_search: bool = False
) -> Optional[Dict[str, Any]]:
    """Call 1: Discover review platforms.
    Retries with simplified query if 0 platforms found.
    broad_search=True: also checks social media pages and booking platform reviews."""

    if broad_search:
        # Broader approach: check Google Maps, social pages, booking platforms
        prompt = _build_broad_discovery_prompt(
            brand_name=brand_name,
            domain=domain,
            city=city,
            country=country,
            subcategory=subcategory,
            niche=niche,
            services=services,
        )
        system_msg = (
            "You are a reputation analyst. Search broadly for ANY customer feedback, "
            "ratings, or testimonials for this brand, including Google Maps, social media pages, "
            "and booking platforms. Return only valid JSON."
        )
        logger.info(f"[REVIEWS] Broad discovery search for '{brand_name}'")
        return await _call_perplexity(prompt, system_msg, max_tokens=2500)

    prompt = build_discovery_prompt(
        brand_name=brand_name,
        domain=domain,
        city=city,
        country=country,
        subcategory=subcategory,
        niche=niche,
        services=services,
        brand_overview=brand_overview,
        platforms_to_check=platforms_to_check,
        app_store_urls=app_store_urls
    )

    system_msg = (
        "You are a reputation intelligence analyst. "
        "Find all review platforms where this brand has customer reviews. "
        "Return only valid JSON. Be thorough — check every platform including app stores."
    )

    logger.info(f"[REVIEWS] Call 1 (Discovery): {brand_name}, checking {len(platforms_to_check)} platforms")
    result = await _call_perplexity(prompt, system_msg, max_tokens=2500)

    # Check if discovery found any platforms with actual reviews
    if result:
        platforms_found = result.get("platforms_found", [])
        has_review_platforms = any(p.get("has_reviews") for p in platforms_found)

        if not has_review_platforms:
            logger.warning(f"[REVIEWS] Discovery returned 0 platforms with reviews for '{brand_name}' — retrying with simplified query")
            retry_result = await _retry_discovery_simplified(
                brand_name=brand_name,
                domain=domain,
                city=city,
                country=country,
                subcategory=subcategory,
            )
            if retry_result:
                retry_platforms = retry_result.get("platforms_found", [])
                if any(p.get("has_reviews") for p in retry_platforms):
                    logger.info(f"[REVIEWS] Simplified retry found {len(retry_platforms)} platforms")
                    # Merge tokens
                    retry_result["_tokens"] = result.get("_tokens", 0) + retry_result.get("_tokens", 0)
                    return retry_result

    return result


def _build_broad_discovery_prompt(
    brand_name: str, domain: str, city: str, country: str,
    subcategory: str, niche: str, services: List[str]
) -> str:
    """Broader search that includes social media pages, booking platforms, and Google Maps."""
    location = f"{city}, {country}" if city else country
    services_str = ", ".join(services[:6]) if services else subcategory

    return f"""Find ANY customer feedback, reviews, or ratings for this business. Search broadly - the brand may be new or small with limited formal review presence.

## THE BRAND
- Name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory} / {niche}
- Services: {services_str}

## SEARCH STRATEGY (try ALL of these)
1. **Google Maps**: Search "{brand_name} {city}" on Google Maps. Also try "{brand_name}" alone.
2. **Facebook page**: Search for "{brand_name}" on Facebook. Check for page ratings, recommendations, and comments on posts.
3. **Instagram**: Check if @{brand_name.lower().replace(' ', '')} or similar handle exists. Look at comment sentiment on recent posts.
4. **Booking platforms**: For beauty/wellness, check Fresha, Booksy, StyleSeat, Treatwell. For food, check Zomato, Talabat.
5. **Google search**: Search "{brand_name} {city} reviews" and see what comes up.
6. **Website testimonials**: Check {domain} for a testimonials or reviews section.

## IMPORTANT
- Include platforms even if they only have a few reviews (1-2 reviews is still data)
- Include Facebook/Instagram if you find customer comments that serve as informal reviews
- For social media, estimate the sentiment from recent post comments
- EXCLUDE employee review sites (Indeed, Glassdoor, Bayt, LinkedIn) — we only want CUSTOMER reviews

## OUTPUT FORMAT (JSON only)
{{
  "platforms_found": [
    {{
      "platform": "Platform name",
      "url": "Direct URL",
      "approximate_rating": 4.5,
      "approximate_count": "5+",
      "has_reviews": true,
      "recency": "within_last_month | 1_3_months | 3_6_months | 6_months_plus | unknown",
      "owner_responds": true,
      "response_quality": "active | occasional | rare | none | unknown",
      "verification_note": "How you verified this is the correct business"
    }}
  ],
  "platforms_checked_but_not_found": []
}}"""


async def _retry_discovery_simplified(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
) -> Optional[Dict[str, Any]]:
    """Simplified retry: focus on Google Maps + Trustpilot + domain-based search."""
    location = f"{city}, {country}" if city else country

    prompt = f"""Find customer reviews for this business:

- Business name: {brand_name}
- Website: {domain}
- Location: {location}
- Category: {subcategory}

Search specifically for:
1. Google Maps listing for "{brand_name}" in {location} — try searching "{brand_name} {city}" on Google Maps
2. Trustpilot page for {domain}
3. Facebook page reviews for {brand_name}
4. Any industry-specific review platform (e.g., Fresha, Booksy, Yelp)

Return JSON only:
{{
  "platforms_found": [
    {{
      "platform": "Platform name",
      "url": "Direct URL to their review page",
      "approximate_rating": 4.5,
      "approximate_count": "50+",
      "has_reviews": true,
      "recency": "within_last_month | 1_3_months | 3_6_months | 6_months_plus | unknown",
      "owner_responds": true,
      "response_quality": "active | occasional | rare | none | unknown",
      "verification_note": "How you verified this is the correct business"
    }}
  ],
  "platforms_checked_but_not_found": []
}}

Only include platforms where you found ACTUAL customer reviews for this specific business at {domain} in {location}. If unsure, exclude it."""

    system_msg = "Find customer review platforms for this business. Return only valid JSON."
    logger.info(f"[REVIEWS] Simplified retry for '{brand_name}' ({domain})")
    return await _call_perplexity(prompt, system_msg, max_tokens=1500)


async def fetch_reviews_analysis(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    discovery_results: Dict[str, Any],
    competitor_names: List[str],
    brand_claims: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """Call 2: Deep analysis of reviews + brand vs reality."""

    prompt = build_analysis_prompt(
        brand_name=brand_name,
        domain=domain,
        city=city,
        country=country,
        subcategory=subcategory,
        niche=niche,
        services=services,
        brand_overview=brand_overview,
        discovery_results=discovery_results,
        competitor_names=competitor_names,
        brand_claims=brand_claims
    )

    system_msg = (
        "You are a reputation intelligence analyst working for a performance marketing agency. "
        "Analyze real customer reviews and extract actionable intelligence. "
        "Return only valid JSON. Be specific — every insight must be grounded in actual review content."
    )

    logger.info(f"[REVIEWS] Call 2 (Analysis): {brand_name}")
    return await _call_perplexity(prompt, system_msg, max_tokens=4500)
