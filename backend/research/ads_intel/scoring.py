"""
Novara Ads Intelligence: Scoring
Multi-dimensional composite scoring for ad quality.
Signals: longevity, liveness, format, CTA, landing page, content richness, recency.
Produces score (0-100), tier label, and rich why_shortlisted text.
"""

import os
import re
import logging
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

SHORTLIST_TOTAL = int(os.environ.get("ADS_INTEL_SHORTLIST_TOTAL", "40"))
COMPETITOR_MAX_PER_BRAND = int(os.environ.get("ADS_INTEL_SHORTLIST_COMPETITOR_MAX_PER_BRAND", "6"))
CATEGORY_MAX_PER_QUERY = int(os.environ.get("ADS_INTEL_SHORTLIST_CATEGORY_MAX_PER_QUERY", "15"))

# Score thresholds for tier assignment
TIER_PROVEN_WINNER = 70
TIER_STRONG_PERFORMER = 50
TIER_RISING = 30


def compute_running_days(ad: Dict[str, Any]) -> Optional[int]:
    """Compute running days from start_date/end_date or existing running_days."""
    if ad.get("running_days") and isinstance(ad["running_days"], (int, float)):
        return int(ad["running_days"])

    start = ad.get("start_date") or ad.get("startDate") or ad.get("first_seen_date")
    if not start:
        return None

    try:
        if isinstance(start, str):
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")).date()
        elif isinstance(start, date):
            start_dt = start
        else:
            return None

        end = ad.get("end_date") or ad.get("endDate") or ad.get("last_seen_date")
        if end:
            if isinstance(end, str):
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")).date()
            elif isinstance(end, date):
                end_dt = end
            else:
                end_dt = datetime.now(timezone.utc).date()
        else:
            end_dt = datetime.now(timezone.utc).date()

        days = (end_dt - start_dt).days
        return max(0, days)
    except Exception:
        return None


# ============== COMPOSITE SCORING ==============

def _longevity_score(days: Optional[int]) -> int:
    """0-35 points based on how long the ad has been running."""
    if not days or days <= 0:
        return 0
    if days >= 90:
        return 35
    if days >= 60:
        return 30
    if days >= 30:
        return 25
    if days >= 14:
        return 15
    if days >= 7:
        return 8
    return 3


def _liveness_score(ad: Dict[str, Any]) -> int:
    """0-15 points: active ads get full credit."""
    return 15 if ad.get("live") else 0


def _format_score(ad: Dict[str, Any]) -> int:
    """0-10 points: video > carousel > image."""
    fmt = (ad.get("_format") or ad.get("display_format") or "").lower()
    if fmt == "video":
        return 10
    if fmt == "carousel":
        return 7
    if fmt == "image":
        return 4
    return 2


def _cta_score(ad: Dict[str, Any]) -> int:
    """0-5 points: has a call-to-action."""
    return 5 if ad.get("cta") else 0


def _landing_page_score(ad: Dict[str, Any]) -> int:
    """0-5 points: has a landing page URL."""
    return 5 if ad.get("landing_page_url") else 0


def _preview_score(ad: Dict[str, Any]) -> int:
    """0-5 points: has a real visual preview."""
    return 5 if ad.get("has_preview", True) else 0


def _content_score(ad: Dict[str, Any]) -> int:
    """0-10 points: richness of ad copy."""
    has_headline = bool(ad.get("headline"))
    has_body = bool(ad.get("text"))
    if has_headline and has_body:
        return 10
    if has_headline or has_body:
        return 5
    return 0


def _recency_score(ad: Dict[str, Any]) -> int:
    """0-15 points: how recently the ad was seen/started."""
    start_str = ad.get("start_date") or ""
    now = datetime.now(timezone.utc)
    if not start_str:
        return 5 if ad.get("live") else 0
    try:
        if isinstance(start_str, str):
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        else:
            start_dt = start_str
        days_since_start = (now - start_dt).days
        # Live ad started recently = actively investing
        if ad.get("live"):
            if days_since_start <= 30:
                return 15
            if days_since_start <= 90:
                return 12
            return 8
        # Not live: more recent = more relevant
        if days_since_start <= 30:
            return 10
        if days_since_start <= 90:
            return 5
        return 0
    except Exception:
        return 0


def compute_ad_score(ad: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute composite ad quality score (0-100) and individual signal breakdown.
    Returns dict with 'total', 'tier', and per-signal scores.
    """
    days = ad.get("_running_days")
    signals = {
        "longevity": _longevity_score(days),
        "liveness": _liveness_score(ad),
        "format": _format_score(ad),
        "cta": _cta_score(ad),
        "landing_page": _landing_page_score(ad),
        "preview": _preview_score(ad),
        "content": _content_score(ad),
        "recency": _recency_score(ad),
    }
    total = sum(signals.values())
    total = min(total, 100)

    if total >= TIER_PROVEN_WINNER:
        tier = "proven_winner"
    elif total >= TIER_STRONG_PERFORMER:
        tier = "strong_performer"
    elif total >= TIER_RISING:
        tier = "rising"
    else:
        tier = "notable"

    return {"total": total, "tier": tier, "signals": signals}


def ad_sort_key(ad: Dict[str, Any]) -> tuple:
    """
    Sort key: (composite_score DESC, running_days DESC, recency DESC)
    Uses composite score as primary sort.
    """
    score = ad.get("_score", {}).get("total", 0) if isinstance(ad.get("_score"), dict) else 0
    running = ad.get("_running_days") or 0

    last_seen = ad.get("last_seen_date") or ad.get("end_date") or ""
    recency = 0
    if last_seen:
        try:
            if isinstance(last_seen, str):
                dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            else:
                dt = last_seen
            recency = dt.timestamp()
        except Exception:
            pass

    return (score, running, recency)


TIER_LABELS = {
    "proven_winner": "Proven Winner",
    "strong_performer": "Strong Performer",
    "rising": "Rising",
    "notable": "Notable",
}


def build_why_shortlisted(ad: Dict[str, Any]) -> str:
    """Build rich, multi-signal explanation for why this ad was shortlisted."""
    parts = []
    running = ad.get("_running_days")
    is_live = ad.get("live")
    fmt = ad.get("_format", "")
    lens = ad.get("lens", "")
    geo_score = ad.get("_geo_score")
    score_data = ad.get("_score", {})
    tier = score_data.get("tier", "") if isinstance(score_data, dict) else ""

    # Lead with tier
    tier_label = TIER_LABELS.get(tier, "")
    if tier_label and tier in ("proven_winner", "strong_performer"):
        parts.append(tier_label)

    if is_live:
        parts.append("currently active")
    if running and running > 60:
        parts.append(f"running {running} days, a proven creative")
    elif running and running > 30:
        parts.append(f"long-running ({running} days)")
    elif running and running > 0:
        parts.append(f"running {running} days")

    if fmt == "video":
        parts.append("video format (high engagement)")
    elif fmt == "carousel":
        parts.append("carousel format")

    if lens == "competitor":
        parts.append("from a known competitor")
    elif geo_score and geo_score >= 0.9:
        parts.append("geo-relevant to your market")
    elif geo_score and geo_score >= 0.5:
        parts.append("industry trend")

    if not parts:
        parts.append("Shortlisted for category relevance")

    return "; ".join(parts) + "."


# ============== GEO-RELEVANCE DETECTION ==============

# Country-code TLD → normalized country
_TLD_COUNTRY = {
    ".ae": "uae", ".sa": "saudi arabia", ".qa": "qatar", ".kw": "kuwait",
    ".om": "oman", ".bh": "bahrain", ".in": "india", ".uk": "united kingdom",
    ".au": "australia", ".sg": "singapore", ".my": "malaysia", ".ca": "canada",
    ".de": "germany", ".fr": "france", ".jp": "japan", ".kr": "south korea",
    ".cn": "china", ".br": "brazil", ".mx": "mexico", ".za": "south africa",
    ".ng": "nigeria", ".ke": "kenya", ".eg": "egypt", ".tr": "turkey",
    ".pk": "pakistan", ".bd": "bangladesh", ".ph": "philippines",
    ".id": "indonesia", ".th": "thailand", ".vn": "vietnam",
    ".nz": "new zealand", ".ie": "ireland", ".it": "italy", ".es": "spain",
    ".pt": "portugal", ".nl": "netherlands", ".be": "belgium",
    ".ch": "switzerland", ".se": "sweden", ".no": "norway", ".dk": "denmark",
    ".fi": "finland", ".pl": "poland", ".il": "israel", ".ru": "russia",
    ".hk": "hong kong", ".tw": "taiwan", ".co.uk": "united kingdom",
    ".com.au": "australia", ".com.sg": "singapore", ".co.in": "india",
    ".com.br": "brazil", ".com.mx": "mexico", ".co.za": "south africa",
    ".co.nz": "new zealand", ".com.tr": "turkey", ".com.pk": "pakistan",
    ".co.ke": "kenya", ".com.eg": "egypt", ".com.ng": "nigeria",
}

# Normalize various country name forms to a canonical key
_COUNTRY_NORMALIZE = {
    "uae": "uae", "united arab emirates": "uae", "emirates": "uae",
    "usa": "usa", "united states": "usa", "america": "usa", "u.s.": "usa", "u.s.a.": "usa",
    "uk": "united kingdom", "united kingdom": "united kingdom", "britain": "united kingdom", "great britain": "united kingdom", "england": "united kingdom",
    "india": "india", "saudi arabia": "saudi arabia", "ksa": "saudi arabia",
    "qatar": "qatar", "singapore": "singapore", "australia": "australia",
    "canada": "canada", "germany": "germany", "france": "france",
    "japan": "japan", "south korea": "south korea", "china": "china",
    "brazil": "brazil", "mexico": "mexico", "south africa": "south africa",
    "nigeria": "nigeria", "kenya": "kenya", "egypt": "egypt", "turkey": "turkey",
    "pakistan": "pakistan", "bangladesh": "bangladesh", "philippines": "philippines",
    "indonesia": "indonesia", "thailand": "thailand", "vietnam": "vietnam",
    "new zealand": "new zealand", "ireland": "ireland", "italy": "italy",
    "spain": "spain", "portugal": "portugal", "netherlands": "netherlands",
    "switzerland": "switzerland", "sweden": "sweden", "norway": "norway",
    "denmark": "denmark", "finland": "finland", "poland": "poland",
    "russia": "russia", "israel": "israel", "hong kong": "hong kong",
    "taiwan": "taiwan", "malaysia": "malaysia", "oman": "oman",
    "kuwait": "kuwait", "bahrain": "bahrain",
}

# US states → "usa"
_US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas",
    "utah", "vermont", "virginia", "washington", "west virginia",
    "wisconsin", "wyoming",
}

# US state abbreviations (2-letter) — matched with word boundaries
_US_STATE_ABBR = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
}

# Regions that strongly indicate a country
_REGION_COUNTRY = {
    # UK regions/counties
    "surrey": "united kingdom", "sussex": "united kingdom", "kent": "united kingdom",
    "essex": "united kingdom", "hampshire": "united kingdom", "dorset": "united kingdom",
    "devon": "united kingdom", "cornwall": "united kingdom", "suffolk": "united kingdom",
    "norfolk": "united kingdom", "yorkshire": "united kingdom", "lancashire": "united kingdom",
    "reigate": "united kingdom", "london": "united kingdom", "manchester": "united kingdom",
    "birmingham": "united kingdom", "liverpool": "united kingdom", "leeds": "united kingdom",
    "glasgow": "united kingdom", "edinburgh": "united kingdom", "cardiff": "united kingdom",
    "belfast": "united kingdom", "bristol": "united kingdom", "nottingham": "united kingdom",
    "sheffield": "united kingdom", "leicester": "united kingdom",
    # Indian states/cities
    "maharashtra": "india", "karnataka": "india", "tamil nadu": "india",
    "telangana": "india", "andhra pradesh": "india", "kerala": "india",
    "west bengal": "india", "uttar pradesh": "india", "rajasthan": "india",
    "gujarat": "india", "punjab": "india", "hyderabad": "india",
    "mumbai": "india", "delhi": "india", "bangalore": "india", "bengaluru": "india",
    "chennai": "india", "kolkata": "india", "pune": "india", "ahmedabad": "india",
    "jaipur": "india", "lucknow": "india", "chandigarh": "india", "kochi": "india",
    # Australian states/cities
    "new south wales": "australia", "queensland": "australia", "victoria": "australia",
    "western australia": "australia", "south australia": "australia",
    "tasmania": "australia", "sydney": "australia", "melbourne": "australia",
    "brisbane": "australia", "perth": "australia", "adelaide": "australia",
    # Canadian provinces/cities
    "ontario": "canada", "quebec": "canada", "british columbia": "canada",
    "alberta": "canada", "manitoba": "canada", "saskatchewan": "canada",
    "toronto": "canada", "vancouver": "canada", "montreal": "canada",
    "calgary": "canada", "ottawa": "canada",
    # UAE cities
    "dubai": "uae", "abu dhabi": "uae", "sharjah": "uae", "ajman": "uae",
    "ras al khaimah": "uae", "fujairah": "uae", "umm al quwain": "uae",
    # Saudi cities
    "riyadh": "saudi arabia", "jeddah": "saudi arabia", "mecca": "saudi arabia",
    "medina": "saudi arabia", "dammam": "saudi arabia",
    # Other Gulf
    "doha": "qatar", "muscat": "oman", "manama": "bahrain", "kuwait city": "kuwait",
    # US major cities (to catch "Los Angeles" style mentions)
    "los angeles": "usa", "new york": "usa", "chicago": "usa", "houston": "usa",
    "phoenix": "usa", "san antonio": "usa", "san diego": "usa", "dallas": "usa",
    "san jose": "usa", "austin": "usa", "san francisco": "usa", "seattle": "usa",
    "denver": "usa", "boston": "usa", "las vegas": "usa", "portland": "usa",
    "miami": "usa", "atlanta": "usa", "moreno valley": "usa",
    "scottsdale": "usa", "nashville": "usa", "charlotte": "usa",
    "san bernardino": "usa", "farmingville": "usa", "monrovia": "usa",
    "westlake": "usa", "la quinta": "usa", "downey": "usa",
    "nashua": "usa", "artesia": "usa", "dover": "usa",
    "orlando": "usa", "tampa": "usa", "minneapolis": "usa",
    "pittsburgh": "usa", "st louis": "usa", "detroit": "usa",
    "sacramento": "usa", "cleveland": "usa", "raleigh": "usa",
    # Singapore
    "singapore": "singapore",
    # Other
    "hong kong": "hong kong", "tokyo": "japan", "seoul": "south korea",
    "cairo": "egypt", "istanbul": "turkey", "nairobi": "kenya", "lagos": "nigeria",
}


def _normalize_country(raw: str) -> str:
    """Normalize a country string to canonical form."""
    c = raw.lower().strip()
    return _COUNTRY_NORMALIZE.get(c, c)


def _detect_country_from_url(url: str) -> Optional[str]:
    """Detect country from landing page URL's TLD and path/query patterns."""
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        host = (parsed.netloc or parsed.path).lower().rstrip("/")
        # Check compound TLDs first (e.g., .co.uk, .com.au)
        for tld, country in _TLD_COUNTRY.items():
            if host.endswith(tld):
                return country
        # Check URL path/query for explicit country indicators (common in UTM params)
        url_lower = url.lower()
        for pattern, country in [
            ("_us_", "usa"), ("/us/", "usa"), ("country=us", "usa"), ("store=us", "usa"),
            ("_uk_", "united kingdom"), ("/uk/", "united kingdom"), ("country=uk", "united kingdom"),
            ("_au_", "australia"), ("/au/", "australia"), ("country=au", "australia"),
            ("_in_", "india"), ("country=in", "india"),
            ("_ae_", "uae"), ("/ae/", "uae"), ("country=ae", "uae"),
            ("_ca_", "canada"), ("/ca/", "canada"), ("country=ca", "canada"),
            ("_de_", "germany"), ("country=de", "germany"),
            ("_fr_", "france"), ("country=fr", "france"),
            ("_sg_", "singapore"), ("country=sg", "singapore"),
        ]:
            if pattern in url_lower:
                return country
        return None
    except Exception:
        return None


def _detect_country_from_text(text: str) -> Optional[str]:
    """Detect a country signal from ad text by scanning for regions/states/country names."""
    if not text:
        return None
    text_lower = text.lower()

    # Check for US state full names (strongest US signal)
    for state in _US_STATES:
        if state in text_lower:
            return "usa"

    # Check for US state abbreviations with comma pattern: "City, CA" or "City, NY"
    abbr_pattern = re.findall(r',\s*([A-Z]{2})\b', text)
    for abbr in abbr_pattern:
        if abbr.lower() in _US_STATE_ABBR:
            return "usa"

    # Check for known regions/cities → country mapping (longer strings first)
    for region in sorted(_REGION_COUNTRY, key=len, reverse=True):
        if region in text_lower:
            return _REGION_COUNTRY[region]

    # Check for country names directly in text
    for name, normalized in _COUNTRY_NORMALIZE.items():
        if len(name) > 3 and name in text_lower:
            return normalized

    return None


def compute_geo_relevance(ad: Dict[str, Any], geo: Dict[str, str]) -> float:
    """
    Score 0.0 to 1.0 for how geo-relevant a category ad is.
    Uses multi-signal detection: URL TLD, text region/state/country mentions.

    0.0 = clearly from a different country
    0.5 = no geo signal detected (neutral)
    0.8 = campaign country detected in ad
    1.0 = campaign city detected in ad
    """
    if not geo:
        return 0.5

    campaign_city = (geo.get("city") or "").lower().strip()
    campaign_country_raw = (geo.get("country") or "").lower().strip()
    campaign_country = _normalize_country(campaign_country_raw) if campaign_country_raw else ""

    if not campaign_city and not campaign_country:
        return 0.5

    # Build search text from ad fields
    ad_text = " ".join([
        ad.get("brand_name") or "",
        ad.get("text") or "",
        ad.get("headline") or "",
    ]).strip()
    ad_url = ad.get("landing_page_url") or ""

    # === Signal 1: Positive city match in text ===
    if campaign_city and campaign_city in ad_text.lower():
        return 1.0

    # === Signal 2: Detect ad's country from URL TLD ===
    url_country = _detect_country_from_url(ad_url)

    # === Signal 3: Detect ad's country from text ===
    text_country = _detect_country_from_text(ad_text)

    # Determine the ad's detected country (prefer URL as strongest signal)
    ad_country = url_country or text_country

    if ad_country:
        # We detected a country for this ad — compare with campaign
        if campaign_country and ad_country == campaign_country:
            return 0.9  # Same country, good match
        if campaign_city:
            # Check if campaign city is in the region map and matches
            city_country = _REGION_COUNTRY.get(campaign_city, "")
            if city_country and ad_country == city_country:
                return 0.9
        # Ad is from a DIFFERENT country → filter out
        logger.info(f"[GEO_FILTER] Rejecting: ad_country='{ad_country}' vs campaign='{campaign_country}' | brand='{ad.get('brand_name', '')}' url='{ad_url[:80]}'")
        return 0.0

    # === Signal 4: Check if campaign country name appears in ad text ===
    if campaign_country_raw and campaign_country_raw in ad_text.lower():
        return 0.8

    # No geo signal → neutral, keep the ad
    return 0.5


def shortlist_competitor_ads(
    ads: List[Dict[str, Any]],
    max_total: int = 25,
    max_per_brand: int = None,
) -> List[Dict[str, Any]]:
    """
    Shortlist competitor winner ads.
    - Computes composite score for each ad
    - Sorts by composite score DESC
    - Applies per-brand diversity cap
    """
    if max_per_brand is None:
        max_per_brand = COMPETITOR_MAX_PER_BRAND

    for ad in ads:
        ad["_running_days"] = compute_running_days(ad)
        ad["_score"] = compute_ad_score(ad)

    ads.sort(key=ad_sort_key, reverse=True)

    shortlisted = []
    brand_counts = {}

    for ad in ads:
        if len(shortlisted) >= max_total:
            break

        brand_id = ad.get("brand_id") or ad.get("brand_name") or "unknown"
        count = brand_counts.get(brand_id, 0)
        if count >= max_per_brand:
            continue

        ad["why_shortlisted"] = build_why_shortlisted(ad)
        shortlisted.append(ad)
        brand_counts[brand_id] = count + 1

    logger.info(f"[ADS_INTEL] Competitor shortlist: {len(shortlisted)}/{len(ads)} ads")
    return shortlisted


def shortlist_category_ads(
    ads: List[Dict[str, Any]],
    max_total: int = 15,
    max_per_query: int = None,
    max_per_brand: int = 2,
    geo: Dict[str, str] = None,
) -> List[Dict[str, Any]]:
    """
    Shortlist category winner ads.
    - Applies geo-relevance scoring to filter out irrelevant regions
    - Computes composite score for each ad
    - Sorts by composite score DESC
    - Applies per-query and per-brand diversity caps
    """
    if max_per_query is None:
        max_per_query = CATEGORY_MAX_PER_QUERY

    for ad in ads:
        ad["_running_days"] = compute_running_days(ad)
        ad["_geo_score"] = compute_geo_relevance(ad, geo) if geo else 1.0
        ad["_score"] = compute_ad_score(ad)

    geo_filtered = [a for a in ads if a.get("_geo_score", 1.0) > 0]
    logger.info(f"[ADS_INTEL] Geo filter: {len(ads)} → {len(geo_filtered)} ads (dropped {len(ads) - len(geo_filtered)} irrelevant)")

    geo_filtered.sort(key=lambda a: (a.get("_geo_score", 0), *ad_sort_key(a)), reverse=True)

    shortlisted = []
    query_counts = {}
    brand_counts = {}

    for ad in geo_filtered:
        if len(shortlisted) >= max_total:
            break

        query = ad.get("_source_query", "default")
        qcount = query_counts.get(query, 0)
        if qcount >= max_per_query:
            continue

        brand_key = (ad.get("brand_name") or ad.get("brand_id") or "unknown").lower().strip()
        bcount = brand_counts.get(brand_key, 0)
        if bcount >= max_per_brand:
            continue

        ad["why_shortlisted"] = build_why_shortlisted(ad)
        shortlisted.append(ad)
        query_counts[query] = qcount + 1
        brand_counts[brand_key] = bcount + 1

    logger.info(f"[ADS_INTEL] Category shortlist: {len(shortlisted)}/{len(geo_filtered)} ads, {len(brand_counts)} unique brands")
    return shortlisted


# ============== PATTERN DETECTION ==============

def compute_ad_patterns(ads: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Detect common traits among the highest-scored ads.
    Returns a list of insight dicts: [{type, text, detail}]
    Runs purely on already-scored data — zero additional API calls.
    """
    if not ads or len(ads) < 3:
        return []

    patterns = []

    # Split into tiers
    top_ads = [a for a in ads if a.get("_score", {}).get("tier") in ("proven_winner", "strong_performer")]
    if len(top_ads) < 2:
        top_ads = sorted(ads, key=lambda a: a.get("_score", {}).get("total", 0), reverse=True)[:5]
    top_n = len(top_ads)

    # --- 1. Format distribution ---
    fmt_counts = {}
    for a in top_ads:
        fmt = (a.get("_format") or a.get("display_format") or "image").lower()
        fmt_counts[fmt] = fmt_counts.get(fmt, 0) + 1
    dominant_fmt = max(fmt_counts, key=fmt_counts.get) if fmt_counts else None
    dominant_pct = round((fmt_counts.get(dominant_fmt, 0) / top_n) * 100) if dominant_fmt and top_n else 0
    if dominant_fmt and dominant_pct >= 50:
        fmt_label = {"video": "Video", "carousel": "Carousel", "image": "Image"}.get(dominant_fmt, dominant_fmt.title())
        patterns.append({
            "type": "format",
            "text": f"{fmt_label} ads dominate top performers",
            "detail": f"{fmt_counts[dominant_fmt]} of {top_n} highest-scored ads use {fmt_label.lower()} format ({dominant_pct}%)",
        })

    # --- 2. Platform distribution ---
    plat_counts = {}
    for a in top_ads:
        plat = (a.get("_platform") or a.get("publisher_platform") or "facebook").lower()
        plat_counts[plat] = plat_counts.get(plat, 0) + 1
    dominant_plat = max(plat_counts, key=plat_counts.get) if plat_counts else None
    dominant_plat_pct = round((plat_counts.get(dominant_plat, 0) / top_n) * 100) if dominant_plat and top_n else 0
    if dominant_plat and dominant_plat_pct >= 60:
        plat_label = {"facebook": "Facebook", "instagram": "Instagram", "tiktok": "TikTok"}.get(dominant_plat, dominant_plat.title())
        patterns.append({
            "type": "platform",
            "text": f"{plat_label} leads for high-scoring ads",
            "detail": f"{plat_counts[dominant_plat]} of {top_n} top ads run on {plat_label} ({dominant_plat_pct}%)",
        })

    # --- 3. Longevity insight ---
    running_days_list = [a.get("_running_days") or 0 for a in top_ads if (a.get("_running_days") or 0) > 0]
    if running_days_list:
        avg_days = round(sum(running_days_list) / len(running_days_list))
        if avg_days >= 30:
            patterns.append({
                "type": "longevity",
                "text": f"Top ads average {avg_days} days running",
                "detail": "Long-running campaigns signal proven creatives that convert",
            })

    # --- 4. Active rate ---
    active_count = sum(1 for a in top_ads if a.get("live"))
    active_pct = round((active_count / top_n) * 100) if top_n else 0
    if active_count >= 2 and active_pct >= 40:
        patterns.append({
            "type": "liveness",
            "text": f"{active_pct}% of top ads are currently active",
            "detail": f"{active_count} of {top_n} highest-scored ads are live right now, signaling active investment",
        })

    # --- 5. CTA presence ---
    cta_count = sum(1 for a in top_ads if a.get("cta"))
    cta_pct = round((cta_count / top_n) * 100) if top_n else 0
    if cta_count >= 2 and cta_pct >= 60:
        patterns.append({
            "type": "cta",
            "text": f"{cta_pct}% of top ads include a clear CTA",
            "detail": "Strong call-to-actions are a common trait among winning ads",
        })

    # --- 6. Content richness ---
    rich_count = sum(1 for a in top_ads if a.get("headline") and a.get("text"))
    rich_pct = round((rich_count / top_n) * 100) if top_n else 0
    if rich_count >= 2 and rich_pct >= 50:
        patterns.append({
            "type": "content",
            "text": "Winning ads pair headline + body copy",
            "detail": f"{rich_count} of {top_n} top performers use both headline and body text ({rich_pct}%)",
        })

    # --- 7. Competitor vs Category split ---
    comp_top = sum(1 for a in top_ads if a.get("lens") == "competitor")
    cat_top = top_n - comp_top
    if top_n >= 4:
        if comp_top > cat_top and comp_top >= 3:
            patterns.append({
                "type": "source",
                "text": "Your competitors lead the top-scoring ads",
                "detail": f"{comp_top} of {top_n} top ads come from direct competitors vs {cat_top} from category trends",
            })
        elif cat_top > comp_top and cat_top >= 3:
            patterns.append({
                "type": "source",
                "text": "Category trends outperform competitor ads",
                "detail": f"{cat_top} of {top_n} top ads come from industry trends vs {comp_top} from direct competitors",
            })

    return patterns[:6]
