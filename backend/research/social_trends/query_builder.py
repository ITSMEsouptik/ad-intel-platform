"""
Novara Research Foundation: Social Trends — Query Builder
Version 3.0 - Feb 2026

Generates keyword+hashtag SQL queries for the Shofo TikTok SQL endpoint.
Replaces category_type-based filtering with video_desc LIKE + hashtags UNNEST
for dramatically better coverage (93% of videos have NULL category_type).

Query types:
  - viral: highest view count (pure reach)
  - breakout: small/mid creators with high views (content-driven virality)
  - most_saved: highest save count (reference content, purchase intent)
  - most_discussed: highest comment count (conversation starters)
"""

import time
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

# Stop words to exclude when extracting keywords
STOP_WORDS = {
    "and", "the", "for", "on", "of", "in", "to", "with", "a", "an",
    "or", "not", "is", "are", "be", "at", "by", "from",
    "demand", "services", "service", "based", "online", "digital",
    "premium", "professional", "best", "top", "new", "modern",
    "home", "without", "simple", "special", "custom", "full",
    "quick", "express", "basic", "standard", "deluxe", "complete",
    "mobile", "virtual", "local", "global", "personal",
    "brand", "activation", "strategy", "campaign", "marketing",
    "high", "end", "fine", "luxury", "contemporary", "traditional",
    "group", "private", "club", "membership", "classes", "class",
}


def _extract_keywords(
    niche: str,
    subcategory: str,
    industry: str,
    services: List[str],
    tags: List[str],
    city: str,
    country: str,
) -> Dict[str, Set[str]]:
    """
    Extract search keywords and hashtags from brand classification.

    Returns:
        {
            "desc_keywords": {"makeup", "hair", "hairstyle", ...},  # for LIKE on video_desc
            "hashtags": {"makeup", "grwm", "beautytok", ...},       # for UNNEST(hashtags)
            "geo_hashtags": {"dubaimakeup", "uaebeauty", ...},      # location-specific
        }
    """
    geo_words = set()
    if city:
        geo_words.add(city.lower().strip())
    if country:
        geo_words.add(country.lower().strip())

    # --- Step 1: Extract raw meaningful words ---
    raw_words = set()

    for field in [niche, subcategory, industry]:
        if not field:
            continue
        words = field.lower().replace("&", " ").replace("-", " ").replace("/", " ").split()
        for w in words:
            w = w.strip()
            if len(w) > 2 and w not in STOP_WORDS and w not in geo_words:
                raw_words.add(w)

    # From services — extract the core noun/verb (e.g. "Makeup With Lashes" → "makeup", "lashes")
    for svc in services[:6]:
        words = svc.lower().replace("&", " ").replace("-", " ").split()
        for w in words:
            w = w.strip()
            if len(w) > 2 and w not in STOP_WORDS and w not in geo_words:
                raw_words.add(w)

    # From tags
    for tag in tags[:6]:
        t = tag.lower().strip()
        if len(t) > 2 and t not in STOP_WORDS:
            raw_words.add(t)

    # --- Step 2: Build desc_keywords (for LIKE '%keyword%') ---
    # Use the most meaningful, specific terms (avoid overly broad ones)
    desc_keywords = set()
    for w in raw_words:
        if len(w) >= 3:
            desc_keywords.add(w)

    # Also add multi-word phrases from services (e.g. "hair extension", "nail art")
    for svc in services[:4]:
        words = [w for w in svc.lower().split() if len(w) > 2 and w not in STOP_WORDS]
        if len(words) >= 2:
            desc_keywords.add(" ".join(words[:2]))

    # --- Step 3: Build hashtags (for UNNEST search) ---
    hashtags = set()

    # Direct keywords as hashtags
    for w in raw_words:
        # Single words make good hashtags
        hashtags.add(w)

    # TikTok community-style hashtags: append "tok" to core terms
    tok_candidates = set()
    for w in raw_words:
        if w in ("beauty", "food", "fit", "fitness", "fashion", "book",
                 "clean", "skin", "hair", "nail", "art", "gym", "cook"):
            tok_candidates.add(w)

    for w in tok_candidates:
        hashtags.add(f"{w}tok")

    # Common TikTok format tags based on detected themes
    if any(w in raw_words for w in ("beauty", "makeup", "hair", "skincare", "cosmetics", "salon", "nails")):
        hashtags.update(["grwm", "beautytok", "beautyhacks", "makeupartist", "getreadywithme"])
    if any(w in raw_words for w in ("food", "restaurant", "cooking", "chef", "bakery", "cafe", "recipe")):
        hashtags.update(["foodtok", "foodie", "recipe", "cooking", "homecook"])
    if any(w in raw_words for w in ("fitness", "gym", "workout", "training", "exercise", "yoga")):
        hashtags.update(["fittok", "gymtok", "workout", "fitnessmotivation"])
    if any(w in raw_words for w in ("fashion", "clothing", "style", "outfit", "apparel", "streetwear")):
        hashtags.update(["ootd", "fashiontok", "styleinspo", "outfitoftheday"])
    if any(w in raw_words for w in ("interior", "decor", "furniture", "renovation")):
        hashtags.update(["hometok", "homedecor", "interiordesign", "roomtour"])
    if any(w in raw_words for w in ("travel", "hotel", "tourism", "hospitality")):
        hashtags.update(["traveltok", "wanderlust", "travelinspo"])

    # --- Step 4: Geo-localized hashtags ---
    geo_hashtags = set()
    city_clean = (city or "").lower().replace(" ", "")
    country_clean = (country or "").lower().replace(" ", "")

    # Only combine geo with niche-relevant words (not generic tags like "corporate")
    niche_words = set()
    for field in [niche, subcategory, industry]:
        if not field:
            continue
        words = field.lower().replace("&", " ").replace("-", " ").replace("/", " ").split()
        for w in words:
            w = w.strip()
            if len(w) > 2 and w not in STOP_WORDS and w not in geo_words:
                niche_words.add(w)

    for geo in [city_clean, country_clean]:
        if not geo or len(geo) < 2:
            continue
        for term in sorted(niche_words)[:4]:
            geo_hashtags.add(f"{geo}{term}")
        geo_hashtags.add(geo)

    # Cap sizes to keep queries reasonable
    desc_keywords = set(sorted(desc_keywords, key=len, reverse=True)[:8])
    hashtags = set(sorted(hashtags, key=len)[:15])
    geo_hashtags = set(sorted(geo_hashtags)[:10])

    logger.info(
        f"[SOCIAL-QB] Keywords: desc={sorted(desc_keywords)}, "
        f"hashtags={sorted(hashtags)}, geo={sorted(geo_hashtags)}"
    )

    return {
        "desc_keywords": desc_keywords,
        "hashtags": hashtags,
        "geo_hashtags": geo_hashtags,
    }


def _build_content_filter(keywords: Dict[str, Set[str]]) -> str:
    """
    Build a SQL WHERE clause fragment that matches content by keywords + hashtags.

    Uses:
      - LOWER(video_desc) LIKE '%keyword%' for caption search
      - EXISTS(SELECT 1 FROM UNNEST(hashtags) h WHERE h IN (...)) for hashtag search

    Returns a parenthesized SQL expression like:
      (LOWER(video_desc) LIKE '%makeup%' OR ... OR EXISTS(...))
    """
    parts = []

    # video_desc LIKE conditions (pick top 4 most specific)
    desc_kw = sorted(keywords["desc_keywords"], key=len, reverse=True)[:4]
    for kw in desc_kw:
        escaped = kw.replace("'", "''")
        parts.append(f"LOWER(video_desc) LIKE '%{escaped}%'")

    # Hashtag array search — combine regular + geo hashtags
    all_tags = keywords["hashtags"] | keywords["geo_hashtags"]
    if all_tags:
        tag_list = ", ".join(f"'{t.replace(chr(39), '')}'" for t in sorted(all_tags)[:20])
        parts.append(f"EXISTS(SELECT 1 FROM UNNEST(hashtags) h WHERE h IN ({tag_list}))")

    if not parts:
        return "1=1"

    return "(" + " OR ".join(parts) + ")"


def build_query_plan(
    brand_name: str,
    subcategory: str,
    niche: str,
    industry: str,
    tags: List[str],
    services: List[str],
    city: str,
    country: str,
) -> Dict[str, Any]:
    """
    Build keyword-based SQL queries for category-level trend discovery.

    v3.0: Uses video_desc + hashtags instead of category_type IDs.
    This captures 93%+ more content that has NULL category_type.
    """
    # 1. Extract keywords from brand classification
    keywords = _extract_keywords(
        niche=niche,
        subcategory=subcategory,
        industry=industry,
        services=services,
        tags=tags,
        city=city,
        country=country,
    )

    # 2. Build the content filter SQL clause
    content_filter = _build_content_filter(keywords)

    # 3. Date range: last 90 days
    now_ts = int(time.time())
    lookback_ts = now_ts - (90 * 86400)

    # 4. Base WHERE clause
    base_where = f"{content_filter} AND create_time > {lookback_ts}"

    # 5. Build the 4 query strategies
    cat_label = subcategory or industry or "general"
    sql_queries = []

    # Q1: VIRAL — Top by views (pure reach)
    sql_queries.append({
        "type": "viral",
        "query": f"SELECT * FROM videos WHERE {base_where} AND play_count > 50000 ORDER BY play_count DESC",
        "limit": 100,
        "label": f"Viral {cat_label}",
    })

    # Q2: BREAKOUT — Small/mid creators with disproportionate views
    sql_queries.append({
        "type": "breakout",
        "query": f"SELECT * FROM videos WHERE {base_where} AND play_count > 100000 AND author_follower_count > 0 AND author_follower_count < 500000 ORDER BY play_count DESC",
        "limit": 100,
        "label": f"Breakout {cat_label}",
    })

    # Q3: MOST SAVED — High save count (purchase intent / reference content)
    sql_queries.append({
        "type": "most_saved",
        "query": f"SELECT * FROM videos WHERE {base_where} AND play_count > 50000 AND collect_count > 1000 ORDER BY collect_count DESC",
        "limit": 100,
        "label": f"Most Saved {cat_label}",
    })

    # Q4: MOST DISCUSSED — High comments (conversation starters)
    sql_queries.append({
        "type": "most_discussed",
        "query": f"SELECT * FROM videos WHERE {base_where} AND play_count > 50000 AND comment_count > 500 ORDER BY comment_count DESC",
        "limit": 50,
        "label": f"Most Discussed {cat_label}",
    })

    # 6. Keep IG hashtags + TT keywords for handle-based + hashtag fallback
    all_hashtags = keywords["hashtags"] | keywords["geo_hashtags"]
    ig_hashtags = sorted(all_hashtags)[:10]
    tt_keywords = sorted(keywords["desc_keywords"])[:8]

    plan = {
        "sql_queries": sql_queries,
        "content_filter": content_filter,
        "keywords": {
            "desc_keywords": sorted(keywords["desc_keywords"]),
            "hashtags": sorted(keywords["hashtags"]),
            "geo_hashtags": sorted(keywords["geo_hashtags"]),
        },
        "ig_hashtags": ig_hashtags,
        "tt_keywords": tt_keywords,
        "geo": {"city": city, "country": country},
        "date_range": {"from_ts": lookback_ts, "to_ts": now_ts},
    }

    logger.info(
        f"[SOCIAL-QB] v3.0 query plan: "
        f"{len(sql_queries)} SQL queries, "
        f"{len(keywords['desc_keywords'])} desc keywords, "
        f"{len(keywords['hashtags'])} hashtags, "
        f"{len(keywords['geo_hashtags'])} geo hashtags"
    )

    return plan
