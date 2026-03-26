"""
Novara Research Foundation: Competitor Discovery Perplexity Module
Uses Perplexity sonar for real-time competitor intelligence

Version 3.0 - Feb 2026
- Enriched business context in prompt
- Structured market_overview object
- Conditional logic for platform vs service provider
- Removed category_search_terms
- Improved tier detection (price + brand signals)
"""

import logging
import json
import os
import re
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar"
TEMPERATURE = 0.2
URL_VALIDATION_TIMEOUT = 8  # seconds
MIN_VALID_COMPETITORS = 4  # minimum required
MAX_RETRIES = 2  # maximum retry attempts

# Platform indicators
PLATFORM_KEYWORDS = [
    "book professionals", "find experts", "connect with", "marketplace",
    "platform", "directory", "discover", "browse professionals",
    "hire", "find and book", "book online", "list your business",
    "join as provider", "become a partner", "for professionals"
]


def extract_handle_from_url(url: Optional[str], platform: str) -> Optional[str]:
    """Extract social handle from URL"""
    if not url:
        return None
    
    url = url.strip().rstrip('/')
    
    if platform == "instagram":
        match = re.search(r'instagram\.com/([^/?]+)', url, re.IGNORECASE)
        if match:
            handle = match.group(1)
            if handle.lower() not in ['p', 'reel', 'stories', 'explore']:
                return f"@{handle}" if not handle.startswith('@') else handle
    
    elif platform == "tiktok":
        match = re.search(r'tiktok\.com/@?([^/?]+)', url, re.IGNORECASE)
        if match:
            handle = match.group(1)
            return f"@{handle}" if not handle.startswith('@') else handle
    
    return None


def clean_website_url(url: Optional[str]) -> Optional[str]:
    """Clean website URL to root domain only"""
    if not url:
        return None
    
    url = url.strip()
    
    if not url.startswith('http'):
        url = f"https://{url}"
    
    try:
        parsed = urlparse(url)
        clean_url = f"https://{parsed.netloc}"
        return clean_url if parsed.netloc else None
    except Exception:
        return url


def extract_domain(url: Optional[str]) -> Optional[str]:
    """Extract just the domain from a URL"""
    if not url:
        return None
    
    try:
        if not url.startswith('http'):
            url = f"https://{url}"
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def detect_business_type(
    destination_type: str,
    one_liner: str,
    value_prop: str,
    brand_overview: str
) -> str:
    """
    Detect if business is a platform/marketplace or direct service provider.
    
    Returns: 'platform' or 'service_provider'
    """
    # Check destination type
    if destination_type in ['app', 'platform']:
        return 'platform'
    
    # Check text for platform indicators
    text_to_check = f"{one_liner} {value_prop} {brand_overview}".lower()
    
    platform_score = 0
    for keyword in PLATFORM_KEYWORDS:
        if keyword.lower() in text_to_check:
            platform_score += 1
    
    if platform_score >= 2:
        return 'platform'
    
    return 'service_provider'


def detect_price_tier(
    price_range: Optional[Dict[str, Any]],
    aesthetic: List[str],
    tone_of_voice: List[str],
    values: List[str]
) -> str:
    """
    Detect price tier using price data + brand signals.
    
    Returns: 'budget' | 'mid-range' | 'premium' | 'luxury'
    """
    # Brand signal keywords
    luxury_signals = ['luxury', 'luxurious', 'exclusive', 'elite', 'bespoke', 
                      'high-end', 'sophisticated', 'refined', 'opulent', 'premium']
    premium_signals = ['professional', 'quality', 'expert', 'premium', 'curated',
                       'elevated', 'polished', 'sleek', 'modern', 'minimal']
    budget_signals = ['affordable', 'budget', 'cheap', 'value', 'discount',
                      'economical', 'low-cost', 'bargain', 'accessible']
    
    # Combine brand signals to check
    brand_text = " ".join(aesthetic + tone_of_voice + values).lower()
    
    # Score brand signals
    luxury_score = sum(1 for s in luxury_signals if s in brand_text)
    premium_score = sum(1 for s in premium_signals if s in brand_text)
    budget_score = sum(1 for s in budget_signals if s in brand_text)
    
    # Get price-based tier
    price_tier = 'mid-range'
    if price_range and price_range.get("avg"):
        avg = price_range.get("avg", 0)
        currency = price_range.get("currency", "").upper()
        
        # Adjust thresholds by currency
        if currency in ["AED", "USD", "EUR", "GBP", "SGD", "AUD"]:
            if avg > 500:
                price_tier = 'luxury'
            elif avg > 200:
                price_tier = 'premium'
            elif avg > 50:
                price_tier = 'mid-range'
            else:
                price_tier = 'budget'
        elif currency in ["INR", "PHP", "MYR", "THB"]:
            # Lower thresholds for these currencies
            if avg > 10000:
                price_tier = 'luxury'
            elif avg > 3000:
                price_tier = 'premium'
            elif avg > 500:
                price_tier = 'mid-range'
            else:
                price_tier = 'budget'
    
    # Adjust based on brand signals (can bump up or down one tier)
    if luxury_score >= 2 and price_tier in ['premium', 'mid-range']:
        price_tier = 'luxury' if price_tier == 'premium' else 'premium'
    elif premium_score >= 2 and price_tier == 'mid-range':
        price_tier = 'premium'
    elif budget_score >= 2 and price_tier in ['mid-range', 'premium']:
        price_tier = 'mid-range' if price_tier == 'premium' else 'budget'
    
    return price_tier


async def validate_url(url: str, client: httpx.AsyncClient) -> Tuple[str, bool, str]:
    """Validate a single URL by making a HEAD request."""
    if not url:
        return (url, False, "empty_url")
    
    try:
        response = await client.head(url, follow_redirects=True, timeout=URL_VALIDATION_TIMEOUT)
        
        if response.status_code < 400:
            return (url, True, "ok")
        
        if response.status_code in [403, 405]:
            response = await client.get(url, follow_redirects=True, timeout=URL_VALIDATION_TIMEOUT)
            if response.status_code < 400:
                return (url, True, "ok")
        
        return (url, False, f"status_{response.status_code}")
        
    except httpx.TimeoutException:
        return (url, False, "timeout")
    except httpx.ConnectError:
        return (url, False, "connection_error")
    except Exception as e:
        return (url, False, f"error_{type(e).__name__}")


def validate_competitor_relevance(
    competitors: List[Dict],
    brand_subcategory: str,
    brand_niche: str,
    brand_services: List[str],
    brand_name: str,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Post-LLM relevance validation: check each competitor's description
    actually matches the brand's service category.
    Uses word-boundary matching to avoid false positives (e.g., "ai" in "sustainable").
    Returns (relevant_competitors, rejected_competitors).
    """
    if not competitors:
        return ([], [])

    # Build signal words from brand context
    context_text = f"{brand_subcategory} {brand_niche} {' '.join(brand_services)}".lower()
    signal_words = set()
    for sector, words in INDUSTRY_SIGNALS.items():
        for w in words:
            if len(w) < 3:
                continue  # Skip very short signals that cause false positives
            if w in context_text:
                signal_words.add(w)
    # Also add raw service names as signals (only tokens >= 4 chars)
    for svc in brand_services:
        for token in svc.lower().split():
            if len(token) >= 4:
                signal_words.add(token)

    if not signal_words:
        # No signals to validate against — let all pass
        logger.info("[COMPETITORS] No industry signals extracted for relevance check — skipping")
        return (competitors, [])

    relevant = []
    rejected = []
    brand_lower = brand_name.lower().strip()

    for comp in competitors:
        name = comp.get("name", "")
        # Skip if competitor name is too similar to the brand itself
        if name.lower().strip() == brand_lower:
            logger.info(f"[COMPETITORS] Relevance: Rejected '{name}' — same as brand name")
            rejected.append(comp)
            continue

        # Build text from all available competitor fields
        comp_text = " ".join([
            comp.get("what_they_do", ""),
            comp.get("positioning", ""),
            comp.get("why_competitor", ""),
            " ".join(comp.get("strengths", [])),
        ]).lower()

        # Use word-boundary matching to avoid substring false positives
        matches = []
        for w in signal_words:
            pattern = r'\b' + re.escape(w) + r'\b'
            if re.search(pattern, comp_text):
                matches.append(w)

        if len(matches) >= 1:
            relevant.append(comp)
            logger.info(f"[COMPETITORS] Relevance: ✓ '{name}' — {len(matches)} signal matches: {matches[:5]}")
        else:
            rejected.append(comp)
            logger.warning(
                f"[COMPETITORS] Relevance: ✗ '{name}' — 0 signal matches in description. "
                f"Signals checked: {list(signal_words)[:8]}, "
                f"Description: '{comp_text[:100]}'"
            )

    return (relevant, rejected)


# Industry signals for relevance validation (same structure as ads_intel/seeds.py)
INDUSTRY_SIGNALS = {
    "beauty": ["beauty", "salon", "spa", "skincare", "lash", "lashes", "nails", "makeup",
               "facial", "grooming", "waxing", "threading", "manicure", "pedicure",
               "hair", "bridal", "aesthetics", "blowout", "brow", "tanning", "wellness"],
    "fitness": ["fitness", "gym", "yoga", "pilates", "workout", "training", "crossfit",
                "personal trainer", "exercise"],
    "food": ["restaurant", "cafe", "catering", "food", "delivery", "kitchen", "bakery",
             "coffee", "dining", "meal"],
    "health": ["clinic", "dental", "therapy", "chiropractic", "medical", "doctor",
               "physiotherapy", "derma", "health", "care"],
    "home": ["cleaning", "plumbing", "landscaping", "home service", "repair", "maintenance",
             "handyman", "pest control", "moving"],
    "education": ["tutoring", "coaching", "courses", "learning", "school", "academy",
                  "training", "classes"],
    "tech": ["software", "app", "saas", "platform", "digital", "tech", "cloud", "ai",
             "automation"],
    "fashion": ["fashion", "clothing", "apparel", "boutique", "jewelry", "accessories",
                "shoes", "designer", "luxury"],
    "real_estate": ["real estate", "property", "rental", "apartment", "housing", "mortgage"],
    "automotive": ["automotive", "car", "vehicle", "motor", "garage", "mechanic", "auto"],
    "travel": ["travel", "hotel", "resort", "tourism", "booking", "flight", "tour"],
}


async def validate_competitor_urls(competitors: List[Dict]) -> Tuple[List[Dict], List[str]]:
    """Validate all competitor URLs in parallel."""
    if not competitors:
        return ([], [])
    
    valid_competitors = []
    invalid_domains = []
    
    async with httpx.AsyncClient(
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        verify=False
    ) as client:
        tasks = [validate_url(comp.get("website"), client) for comp in competitors if comp.get("website")]
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
        
        for i, result in enumerate(results):
            comp = competitors[i]
            
            if isinstance(result, Exception):
                logger.warning(f"[COMPETITORS] URL validation exception for {comp.get('name')}: {result}")
                domain = extract_domain(comp.get("website"))
                if domain:
                    invalid_domains.append(domain)
                continue
            
            url, is_valid, reason = result
            
            if is_valid:
                valid_competitors.append(comp)
                logger.info(f"[COMPETITORS] ✓ {comp.get('name')} - {url} is valid")
            else:
                domain = extract_domain(url)
                if domain:
                    invalid_domains.append(domain)
                logger.warning(f"[COMPETITORS] ✗ {comp.get('name')} - {url} is invalid ({reason})")
    
    return (valid_competitors, invalid_domains)


def build_competitor_prompt(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    business_type: str,
    price_tier: str,
    tagline: str,
    one_liner: str,
    bullets: List[str],
    value_prop: str,
    key_benefits: List[str],
    services: List[str],
    price_range: Optional[Dict[str, Any]],
    values: List[str],
    tone_of_voice: List[str],
    aesthetic: List[str],
    destination_type: str,
    primary_action: str,
    exclude_domains: Optional[List[str]] = None
) -> str:
    """Build the enriched prompt for competitor discovery"""
    
    full_location = f"{city}, {country}" if city else country
    
    # Format lists
    bullets_formatted = "\n".join(f"  - {b}" for b in bullets[:5]) if bullets else "  - Not specified"
    benefits_formatted = ", ".join(key_benefits[:5]) if key_benefits else "Not specified"
    services_formatted = ", ".join(services[:6]) if services else "Not specified"
    values_formatted = ", ".join(values[:5]) if values else "Not specified"
    tone_formatted = ", ".join(tone_of_voice[:5]) if tone_of_voice else "Not specified"
    aesthetic_formatted = ", ".join(aesthetic[:5]) if aesthetic else "Not specified"
    
    # Price formatting
    price_display = "Not specified"
    if price_range and price_range.get("avg"):
        currency = price_range.get("currency", "")
        price_display = f"{currency} {price_range.get('min', 0)} - {price_range.get('max', 0)} (avg: {price_range.get('avg', 0)})"
    
    # Build exclusion clause
    exclusion_clause = ""
    if exclude_domains:
        domains_str = ", ".join(exclude_domains)
        exclusion_clause = f"""

## EXCLUDED DOMAINS (websites not working - find different competitors)
{domains_str}"""
    
    # Build business type specific instructions
    if business_type == 'platform':
        competitor_type_instruction = f"""
## COMPETITOR TYPE: PLATFORMS/MARKETPLACES

Since {brand_name} is a PLATFORM/MARKETPLACE where service providers list themselves, find OTHER platforms/marketplaces that:
- Serve the same industry ({subcategory})
- Operate in {country}
- Compete for the same service providers AND customers

Examples of what to find: Other booking platforms, service marketplaces, aggregators in this space.
Do NOT include individual service providers - we want competing platforms."""
    else:
        competitor_type_instruction = f"""
## COMPETITOR TYPE: DIRECT SERVICE PROVIDERS

Since {brand_name} is a SERVICE PROVIDER (delivers services directly to customers), find OTHER service providers that:
- Offer the same type of services ({subcategory})
- Operate in {country}
- Compete for the same customers

Do NOT include:
- Platforms/marketplaces (Fresha, Booksy, StyleSeat, Groupon, ClassPass, Fiverr, Yelp, etc.)
- Directories or listing sites
- Aggregators where businesses list themselves

We want actual businesses that deliver services, not platforms."""

    return f"""You are a competitive intelligence analyst for a performance marketing agency. Your job is to find direct competitors that our client will be bidding against in paid ad auctions.

## WHY THIS MATTERS
Before launching ads, we need to know:
- Who else is advertising to the same audience
- How competitors position themselves
- What messaging angles are already in use

## THE CLIENT WE'RE RESEARCHING

### Brand Identity
- Name: {brand_name}
- Website: {domain}
- Tagline: {tagline or 'Not specified'}
- One-liner: {one_liner or 'Not specified'}

### What They Do
{bullets_formatted}

### Business Classification
- Category: {subcategory}
- Niche: {niche}
- Business type: {business_type.replace('_', ' ').title()}
- Location: {full_location}

### Service Delivery
- How customers engage: {destination_type} 
- Primary CTA: {primary_action or 'Not specified'}

### Their Offer
- Value proposition: {value_prop or 'Not specified'}
- Key benefits: {benefits_formatted}
- Services/Products: {services_formatted}

### Pricing
- Range: {price_display}
- Tier: {price_tier.upper()}

### Brand Personality
- Values: {values_formatted}
- Tone: {tone_formatted}
- Aesthetic: {aesthetic_formatted}
{competitor_type_instruction}
{exclusion_clause}

## VALIDATION REQUIREMENTS
For each competitor, verify:
1. Website is live and accessible
2. They MUST serve customers in {country} (ideally in {city} or nearby). National brands operating in {country} are valid even if not headquartered in {city}.
3. They match the business type ({business_type.replace('_', ' ')})
4. They genuinely compete for the same customer segment
5. Real active business with verifiable online presence

## OUTPUT FORMAT (JSON only - no markdown, no explanation)

{{
  "competitors": [
    {{
      "name": "Business name",
      "website": "https://root-domain.com (root domain only)",
      "instagram_url": "https://instagram.com/handle or null",
      "tiktok_url": "https://tiktok.com/@handle or null",
      "what_they_do": "What they sell and to whom (max 80 chars)",
      "positioning": "Their main angle or value prop (max 100 chars)",
      "why_competitor": "Why they compete for same customers (max 80 chars)",
      "price_tier": "budget | mid-range | premium | luxury",
      "estimated_size": "small | medium | large",
      "overlap_score": "high | medium | low",
      "strengths": ["Competitive advantage 1", "Competitive advantage 2", "Competitive advantage 3"],
      "weaknesses": ["Known weakness or gap 1", "Known weakness or gap 2"],
      "ad_strategy_summary": "Brief description of their advertising approach, common ad angles, and platforms they advertise on (max 150 chars)",
      "social_presence": [
        {{"platform": "Instagram", "url": "https://instagram.com/handle", "followers_approx": "10K"}},
        {{"platform": "TikTok", "url": "https://tiktok.com/@handle", "followers_approx": "5K"}}
      ]
    }}
  ],
  "market_overview": {{
    "competitive_density": "low | moderate | high | saturated",
    "dominant_player_type": "Who dominates this market - independents, chains, platforms, or mixed",
    "market_insight": "One specific, non-obvious insight about competition in this market (max 150 chars)",
    "ad_landscape_note": "What to expect in paid ads - who advertises, common angles used (max 150 chars)"
  }}
}}

## RULES
1. Return 6-8 competitors (aim for variety: mix of direct rivals, aspirational players, and emerging challengers)
2. All must have WORKING websites
3. All must match the business type ({business_type.replace('_', ' ')})
4. All must serve customers in {country}. {city}-based businesses are preferred but national/regional brands that serve {city} customers count too.
5. Website = root domain only (no subpages)
6. Social URLs only if account is active, otherwise null
7. market_overview must be specific to {full_location} and {subcategory}
8. strengths: 2-4 real competitive advantages per competitor (specific, not generic)
9. weaknesses: 2-3 known gaps or limitations per competitor
10. ad_strategy_summary: What ads they run, where, and what angles they use
11. social_presence: Include only platforms where they have active accounts with approximate follower counts
12. Include a MIX of price tiers and sizes for a complete competitive picture
13. JSON only - no markdown"""


async def fetch_competitors_from_perplexity(
    prompt: str,
    is_retry: bool = False,
    exclude_domains: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Make a single call to Perplexity API for competitors."""
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not set")
    
    retry_note = f" (RETRY - excluding: {', '.join(exclude_domains)})" if is_retry and exclude_domains else ""
    logger.info(f"[COMPETITORS] Calling Perplexity{retry_note}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a competitive intelligence analyst. Return only valid JSON. Verify all websites are real and working before including them."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": 5000
    }
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(PERPLEXITY_API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            logger.error(f"[COMPETITORS] Perplexity API error: {response.status_code} - {response.text}")
            raise Exception(f"Perplexity API error: {response.status_code}")
        
        data = response.json()
    
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    content = content.strip()
    
    # Remove markdown code blocks
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    try:
        parsed = json.loads(content)
        comps = parsed.get('competitors', [])
        if comps:
            sample = comps[0]
            logger.info(f"[COMPETITORS] Parsed {len(comps)} competitors. Sample keys: {list(sample.keys())}")
            logger.info(f"[COMPETITORS] Sample strengths: {sample.get('strengths')}, weaknesses: {sample.get('weaknesses')}, ad_strategy: {sample.get('ad_strategy_summary')}, social: {sample.get('social_presence')}")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"[COMPETITORS] JSON parse error: {e}")
        return {"competitors": [], "market_overview": {}}


async def call_perplexity_competitors(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    brand_overview: str,
    price_range: Optional[Dict[str, Any]] = None,
    # New enriched context
    tagline: str = "",
    one_liner: str = "",
    bullets: List[str] = None,
    value_prop: str = "",
    key_benefits: List[str] = None,
    values: List[str] = None,
    tone_of_voice: List[str] = None,
    aesthetic: List[str] = None,
    destination_type: str = "website",
    primary_action: str = ""
) -> Dict[str, Any]:
    """
    Call Perplexity API for competitor discovery with URL validation and retry.
    
    Flow:
    1. Detect business type (platform vs service provider)
    2. Detect price tier (price + brand signals)
    3. Get competitors from Perplexity with enriched context
    4. Validate URLs
    5. Retry if needed (max 2 retries)
    6. Return validated results
    """
    
    # Defaults
    bullets = bullets or []
    key_benefits = key_benefits or []
    values = values or []
    tone_of_voice = tone_of_voice or []
    aesthetic = aesthetic or []
    
    # ============== Detect business type ==============
    business_type = detect_business_type(
        destination_type=destination_type,
        one_liner=one_liner,
        value_prop=value_prop,
        brand_overview=brand_overview
    )
    logger.info(f"[COMPETITORS] Detected business type: {business_type}")
    
    # ============== Detect price tier ==============
    price_tier = detect_price_tier(
        price_range=price_range,
        aesthetic=aesthetic,
        tone_of_voice=tone_of_voice,
        values=values
    )
    logger.info(f"[COMPETITORS] Detected price tier: {price_tier}")
    
    # ============== Main loop with retries ==============
    all_invalid_domains = []
    all_valid_competitors = []
    market_overview = {}
    seen_domains = set()
    
    for attempt in range(MAX_RETRIES + 1):
        # Build prompt with current exclusions
        prompt = build_competitor_prompt(
            brand_name=brand_name,
            domain=domain,
            city=city,
            country=country,
            subcategory=subcategory,
            niche=niche,
            business_type=business_type,
            price_tier=price_tier,
            tagline=tagline,
            one_liner=one_liner,
            bullets=bullets,
            value_prop=value_prop,
            key_benefits=key_benefits,
            services=services,
            price_range=price_range,
            values=values,
            tone_of_voice=tone_of_voice,
            aesthetic=aesthetic,
            destination_type=destination_type,
            primary_action=primary_action,
            exclude_domains=all_invalid_domains if attempt > 0 else None
        )
        
        # Fetch from Perplexity
        result = await fetch_competitors_from_perplexity(
            prompt=prompt,
            is_retry=attempt > 0,
            exclude_domains=all_invalid_domains if attempt > 0 else None
        )
        
        # Clean website URLs
        for comp in result.get("competitors", []):
            if comp.get("website"):
                comp["website"] = clean_website_url(comp["website"])
        
        # Validate URLs
        valid_competitors, invalid_domains = await validate_competitor_urls(result.get("competitors", []))
        
        # Track invalid domains
        all_invalid_domains.extend(invalid_domains)
        all_invalid_domains = list(set(all_invalid_domains))
        
        # Add new valid competitors
        for comp in valid_competitors:
            comp_domain = extract_domain(comp.get("website"))
            if comp_domain and comp_domain not in seen_domains:
                all_valid_competitors.append(comp)
                seen_domains.add(comp_domain)
        
        # Keep market_overview from first successful response with data
        if not market_overview and result.get("market_overview"):
            market_overview = result.get("market_overview", {})
        
        logger.info(f"[COMPETITORS] Attempt {attempt + 1}: {len(valid_competitors)} new valid, {len(all_valid_competitors)} total valid")
        
        # Check if we have enough
        if len(all_valid_competitors) >= MIN_VALID_COMPETITORS:
            logger.info(f"[COMPETITORS] Got {len(all_valid_competitors)} valid competitors, done!")
            break
        
        if attempt < MAX_RETRIES:
            logger.info(f"[COMPETITORS] Only {len(all_valid_competitors)} valid, retrying...")
        else:
            logger.warning(f"[COMPETITORS] Max retries reached, returning {len(all_valid_competitors)} competitors")
    
    # ============== Relevance validation ==============
    relevant_competitors, rejected_competitors = validate_competitor_relevance(
        competitors=all_valid_competitors,
        brand_subcategory=subcategory,
        brand_niche=niche,
        brand_services=services,
        brand_name=brand_name,
    )
    if rejected_competitors:
        logger.warning(
            f"[COMPETITORS] Relevance filter removed {len(rejected_competitors)} irrelevant competitors: "
            f"{[c.get('name') for c in rejected_competitors]}"
        )

    # ============== Post-process ==============
    for comp in relevant_competitors:
        if comp.get("instagram_url"):
            comp["instagram_handle"] = extract_handle_from_url(comp["instagram_url"], "instagram")
        if comp.get("tiktok_url"):
            comp["tiktok_handle"] = extract_handle_from_url(comp["tiktok_url"], "tiktok")
    
    final_result = {
        "competitors": relevant_competitors[:5],
        "market_overview": market_overview
    }
    
    logger.info(f"[COMPETITORS] Final: {len(final_result['competitors'])} competitors (after relevance check)")
    
    return final_result
