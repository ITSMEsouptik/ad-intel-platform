"""
Novara Research Foundation: Reviews Post-Processor
Version 1.5 - Feb 2026

Enhancements over v1.1:
- Validates recency and owner response fields
- Marks all social proof snippets as paraphrased
- Processes brand_vs_reality cross-reference
- Computes social_proof_readiness score deterministically
- App store platform detection
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Employee review sites — NOT customer reviews
EMPLOYEE_REVIEW_DOMAINS = {
    "indeed.com", "glassdoor.com", "glassdoor.co.in", "glassdoor.co.uk",
    "ambitionbox.com", "naukri.com", "comparably.com", "kununu.com",
    "payscale.com", "teamblind.com", "levels.fyi", "ziprecruiter.com",
    "careerbliss.com", "fairygodboss.com", "inhersight.com",
}

# City indicators in URLs that can flag wrong-location matches
CITY_URL_INDICATORS = {
    "delhi": ["delhi", "new-delhi", "noida", "gurgaon", "gurugram", "faridabad", "ghaziabad"],
    "mumbai": ["mumbai", "bombay", "thane", "navi-mumbai"],
    "bangalore": ["bangalore", "bengaluru"],
    "chennai": ["chennai", "madras"],
    "kolkata": ["kolkata", "calcutta"],
    "hyderabad": ["hyderabad", "secunderabad"],
    "pune": ["pune"],
    "london": ["london"],
    "new york": ["new-york", "nyc", "manhattan", "brooklyn"],
    "los angeles": ["los-angeles", "la-"],
    "dubai": ["dubai"],
    "abu dhabi": ["abu-dhabi", "abudhabi"],
    "riyadh": ["riyadh"],
    "jeddah": ["jeddah", "jiddah"],
    "singapore": ["singapore"],
    "sydney": ["sydney"],
    "melbourne": ["melbourne"],
    "toronto": ["toronto"],
}

# Generic themes to reject (too vague for ad strategy)
GENERIC_STRENGTH_PATTERNS = [
    r"^great\s*(service|experience|place|quality|staff)?$",
    r"^good\s*(service|experience|place|quality|staff)?$",
    r"^(nice|excellent|wonderful|amazing)\s*(place|experience)?$",
    r"^(highly\s+)?recommend(ed)?$",
    r"^(overall\s+)?positive\s*(experience|reviews?)?$",
    r"^(high|good|top)\s*quality$",
    r"^best\s*(in|of)\s*(class|town|city)$",
]

GENERIC_WEAKNESS_PATTERNS = [
    r"^(could|room\s+for)\s*improv(e|ement)$",
    r"^(some|minor)\s*(issues?|complaints?|concerns?)$",
    r"^not\s+perfect$",
    r"^(needs?|could\s+use)\s*(work|improvement)$",
]

VALID_FREQUENCIES = {"frequent", "moderate", "occasional"}
VALID_SEVERITIES = {"minor", "moderate", "deal_breaker"}
VALID_RECENCIES = {"within_last_month", "1_3_months", "3_6_months", "6_months_plus", "unknown"}
VALID_RESPONSE_QUALITIES = {"active", "occasional", "rare", "none", "unknown"}
VALID_ALIGNMENTS = {"supported", "partially_supported", "contradicted", "not_mentioned"}

# App store detection
APP_STORE_KEYWORDS = {
    "apple app store", "app store", "ios", "itunes",
    "google play store", "google play", "play store", "android"
}


def _matches_any(text: str, patterns: List[str]) -> bool:
    text_lower = text.strip().lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def _validate_rating(rating: Any) -> float:
    """Validate and clamp rating to 0-5 range."""
    if rating is None:
        return None
    try:
        r = float(rating)
        if r < 0 or r > 5:
            return None
        return round(r, 1)
    except (ValueError, TypeError):
        return None


def _is_employee_review_site(url: str) -> bool:
    """Check if a URL belongs to an employee review site (not customer reviews)."""
    if not url:
        return False
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        return domain in EMPLOYEE_REVIEW_DOMAINS
    except Exception:
        return False


def _url_has_wrong_city(url: str, brand_city: str) -> bool:
    """Check if a URL contains city indicators for a DIFFERENT city than the brand's."""
    if not url or not brand_city:
        return False

    url_lower = url.lower()
    brand_city_lower = brand_city.lower().strip()

    for city_name, indicators in CITY_URL_INDICATORS.items():
        if city_name in brand_city_lower or brand_city_lower in city_name:
            continue
        for indicator in indicators:
            if indicator in url_lower:
                logger.info(f"[REVIEWS-PP] URL geo mismatch: URL contains '{indicator}' (suggests {city_name}), brand is in '{brand_city}'")
                return True

    return False


def _is_app_store_platform(platform_name: str, url: str = "") -> bool:
    """Detect if a platform is an app store."""
    name_lower = platform_name.lower().strip()
    if any(kw in name_lower for kw in APP_STORE_KEYWORDS):
        return True
    if url:
        url_lower = url.lower()
        if "apps.apple.com" in url_lower or "play.google.com" in url_lower:
            return True
    return False


def compute_social_proof_readiness(
    platforms: List[Dict],
    strengths: List[Dict],
    brand_vs_reality_checks: List[Dict]
) -> str:
    """
    Deterministic scoring: strong | moderate | weak

    Factors:
    - Number of platforms with reviews
    - Average rating across platforms
    - Review recency (at least 1 platform with recent reviews)
    - Owner response (at least 1 platform where owner responds)
    - Brand alignment (if checks exist, >50% supported = bonus)
    """
    score = 0

    # Factor 1: Platform count (max 3 pts)
    platforms_with_reviews = [p for p in platforms if p.get("has_reviews")]
    n = len(platforms_with_reviews)
    if n >= 3:
        score += 3
    elif n >= 2:
        score += 2
    elif n >= 1:
        score += 1

    # Factor 2: Average rating (max 3 pts)
    ratings = [p["approximate_rating"] for p in platforms_with_reviews if p.get("approximate_rating")]
    if ratings:
        avg = sum(ratings) / len(ratings)
        if avg >= 4.3:
            score += 3
        elif avg >= 3.8:
            score += 2
        elif avg >= 3.0:
            score += 1

    # Factor 3: Recency (max 2 pts)
    recencies = [p.get("recency", "unknown") for p in platforms_with_reviews]
    if "within_last_month" in recencies:
        score += 2
    elif "1_3_months" in recencies:
        score += 1

    # Factor 4: Owner responds (max 1 pt)
    if any(p.get("owner_responds") for p in platforms_with_reviews):
        score += 1

    # Factor 5: Brand alignment (max 1 pt)
    if brand_vs_reality_checks:
        supported = sum(1 for c in brand_vs_reality_checks if c.get("review_alignment") == "supported")
        total = len(brand_vs_reality_checks)
        if total > 0 and supported / total > 0.5:
            score += 1

    # Factor 6: Strength themes (max 1 pt)
    if len(strengths) >= 3:
        score += 1

    # Total max: 11
    if score >= 8:
        return "strong"
    elif score >= 4:
        return "moderate"
    else:
        return "weak"


def postprocess_reviews(
    discovery: Dict[str, Any],
    analysis: Dict[str, Any],
    brand_city: str = "",
    brand_domain: str = "",
    brand_claims: Optional[List[str]] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Main post-processing pipeline for reviews data.
    v1.5: Handles recency, owner response, app store, brand vs reality, readiness score.

    Returns:
        Tuple of (processed_data, audit_stats)
    """
    stats = {
        "platforms_raw": 0,
        "platforms_validated": 0,
        "platforms_employee_site_removed": 0,
        "platforms_wrong_city_removed": 0,
        "platforms_app_store": 0,
        "strength_themes_raw": 0,
        "strength_themes_kept": 0,
        "weakness_themes_raw": 0,
        "weakness_themes_kept": 0,
        "snippets_raw": 0,
        "snippets_kept": 0,
        "generic_themes_removed": 0,
        "brand_claims_checked": 0,
        "brand_claims_supported": 0,
        "brand_claims_contradicted": 0,
    }

    # 1. Process platforms (with geographic + employee site filtering + new fields)
    raw_platforms = discovery.get("platforms_found", [])
    stats["platforms_raw"] = len(raw_platforms)

    validated_platforms = []
    for p in raw_platforms:
        platform_name = p.get("platform", "")
        if not platform_name:
            continue

        url = str(p.get("url", "")) if p.get("url") else ""

        # Filter: employee review sites
        if _is_employee_review_site(url):
            stats["platforms_employee_site_removed"] += 1
            logger.info(f"[REVIEWS-PP] Removed employee review site: {platform_name} ({url[:80]})")
            continue

        # Filter: wrong city in URL
        if brand_city and _url_has_wrong_city(url, brand_city):
            stats["platforms_wrong_city_removed"] += 1
            logger.info(f"[REVIEWS-PP] Removed wrong-city platform: {platform_name} ({url[:80]}) — brand is in {brand_city}")
            continue

        rating = _validate_rating(p.get("approximate_rating"))

        # Validate recency
        recency = p.get("recency", "unknown")
        if recency not in VALID_RECENCIES:
            recency = "unknown"

        # Validate owner_responds
        owner_responds = p.get("owner_responds")
        if owner_responds is not None:
            owner_responds = bool(owner_responds)

        # Validate response_quality
        response_quality = p.get("response_quality", "unknown")
        if response_quality not in VALID_RESPONSE_QUALITIES:
            response_quality = "unknown"

        # Detect app store
        is_app_store = _is_app_store_platform(platform_name, url)
        if is_app_store:
            stats["platforms_app_store"] += 1

        validated_platforms.append({
            "platform": platform_name[:50],
            "url": url[:200] if url else None,
            "approximate_rating": rating,
            "approximate_count": str(p.get("approximate_count", ""))[:20] if p.get("approximate_count") else None,
            "has_reviews": bool(p.get("has_reviews", False)),
            "recency": recency,
            "owner_responds": owner_responds,
            "response_quality": response_quality,
            "is_app_store": is_app_store,
        })

    stats["platforms_validated"] = len(validated_platforms)

    # 2. Process strength themes
    raw_strengths = analysis.get("strength_themes", [])
    stats["strength_themes_raw"] = len(raw_strengths)

    validated_strengths = []
    for s in raw_strengths[:5]:
        theme = s.get("theme", "")
        if not theme or len(theme) < 5:
            continue
        if _matches_any(theme, GENERIC_STRENGTH_PATTERNS):
            stats["generic_themes_removed"] += 1
            logger.debug(f"[REVIEWS-PP] Rejected generic strength: '{theme}'")
            continue

        evidence = [str(e)[:150] for e in s.get("evidence", [])[:3] if len(str(e)) > 10]
        frequency = s.get("frequency", "moderate")
        if frequency not in VALID_FREQUENCIES:
            frequency = "moderate"

        validated_strengths.append({
            "theme": theme[:80],
            "evidence": evidence,
            "frequency": frequency
        })

    stats["strength_themes_kept"] = len(validated_strengths)

    # 3. Process weakness themes
    raw_weaknesses = analysis.get("weakness_themes", [])
    stats["weakness_themes_raw"] = len(raw_weaknesses)

    validated_weaknesses = []
    for w in raw_weaknesses[:4]:
        theme = w.get("theme", "")
        if not theme or len(theme) < 5:
            continue
        if _matches_any(theme, GENERIC_WEAKNESS_PATTERNS):
            stats["generic_themes_removed"] += 1
            logger.debug(f"[REVIEWS-PP] Rejected generic weakness: '{theme}'")
            continue

        evidence = [str(e)[:150] for e in w.get("evidence", [])[:3] if len(str(e)) > 10]
        frequency = w.get("frequency", "moderate")
        if frequency not in VALID_FREQUENCIES:
            frequency = "moderate"
        severity = w.get("severity", "minor")
        if severity not in VALID_SEVERITIES:
            severity = "minor"

        validated_weaknesses.append({
            "theme": theme[:80],
            "evidence": evidence,
            "frequency": frequency,
            "severity": severity
        })

    stats["weakness_themes_kept"] = len(validated_weaknesses)

    # 4. Process social proof snippets (with is_paraphrased flag)
    raw_snippets = analysis.get("social_proof_snippets", [])
    stats["snippets_raw"] = len(raw_snippets)

    validated_snippets = []
    for sn in raw_snippets[:6]:
        quote = sn.get("quote", "")
        if len(quote) < 15:
            continue
        validated_snippets.append({
            "quote": quote[:200],
            "platform": str(sn.get("platform", ""))[:30],
            "context": str(sn.get("context", ""))[:100],
            "is_paraphrased": True,  # v1.5: always mark as paraphrased
        })

    stats["snippets_kept"] = len(validated_snippets)

    # 5. Process trust signals
    raw_trust = analysis.get("trust_signals", [])
    validated_trust = [str(t)[:100] for t in raw_trust[:5] if len(str(t)) > 5]

    # 6. Process competitor reputation
    raw_comp_rep = analysis.get("competitor_reputation", [])
    validated_comp_rep = []
    for cr in raw_comp_rep[:3]:
        name = cr.get("name", "")
        if not name:
            continue
        validated_comp_rep.append({
            "name": name[:50],
            "approximate_rating": _validate_rating(cr.get("approximate_rating")),
            "primary_platform": str(cr.get("primary_platform", ""))[:30],
            "reputation_gap": str(cr.get("reputation_gap", ""))[:150]
        })

    # 7. Process reputation summary
    raw_summary = analysis.get("reputation_summary", [])
    validated_summary = [str(b)[:120] for b in raw_summary[:3] if len(str(b)) > 10]

    # 8. Process brand vs reality (v1.5)
    raw_bvr = analysis.get("brand_vs_reality", [])
    validated_bvr = []
    if isinstance(raw_bvr, list):
        for check in raw_bvr[:8]:
            claim = str(check.get("claim", ""))[:150]
            alignment = check.get("review_alignment", "not_mentioned")
            if alignment not in VALID_ALIGNMENTS:
                alignment = "not_mentioned"
            evidence = str(check.get("evidence", ""))[:200]

            if claim:
                validated_bvr.append({
                    "claim": claim,
                    "review_alignment": alignment,
                    "evidence": evidence,
                })

                if alignment == "supported":
                    stats["brand_claims_supported"] += 1
                elif alignment == "contradicted":
                    stats["brand_claims_contradicted"] += 1

    stats["brand_claims_checked"] = len(validated_bvr)

    # 9. Compute social proof readiness score (v1.5)
    readiness = compute_social_proof_readiness(
        platforms=validated_platforms,
        strengths=validated_strengths,
        brand_vs_reality_checks=validated_bvr
    )

    processed = {
        "platform_presence": validated_platforms,
        "reputation_summary": validated_summary,
        "strength_themes": validated_strengths,
        "weakness_themes": validated_weaknesses,
        "social_proof_snippets": validated_snippets,
        "trust_signals": validated_trust,
        "competitor_reputation": validated_comp_rep,
        "brand_vs_reality": validated_bvr,
        "social_proof_readiness": readiness,
    }

    logger.info(
        f"[REVIEWS-PP] Result: {stats['platforms_validated']} platforms "
        f"({stats['platforms_employee_site_removed']} employee sites removed, "
        f"{stats['platforms_wrong_city_removed']} wrong-city removed, "
        f"{stats['platforms_app_store']} app stores), "
        f"{stats['strength_themes_kept']} strengths, "
        f"{stats['weakness_themes_kept']} weaknesses, "
        f"{stats['snippets_kept']} snippets, "
        f"{stats['generic_themes_removed']} generic removed, "
        f"readiness={readiness}, "
        f"brand_claims={stats['brand_claims_checked']} ({stats['brand_claims_supported']} supported)"
    )

    return processed, stats
