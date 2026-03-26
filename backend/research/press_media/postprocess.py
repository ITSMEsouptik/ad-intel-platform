"""
Novara Research Foundation: Press & Media Intelligence — Post-Processor
Version 1.0 - Feb 2026

Deterministic cleanup:
- Dedup articles by URL
- Filter out forum/review/employee sites (wrong module)
- Reject generic narratives
- Validate enums (type, sentiment, frequency, tier)
- Cap lengths and counts
- Exclude brand's own domain
"""

import logging
import re
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ============== VALIDATION SETS ==============

VALID_ARTICLE_TYPES = {"feature", "news", "interview", "press_release", "blog", "opinion", "listicle"}
VALID_SENTIMENTS = {"positive", "neutral", "negative", "mixed"}
VALID_NARRATIVE_TYPES = {"narrative", "controversy", "milestone", "positioning", "trend"}
VALID_FREQUENCIES = {"frequent", "moderate", "occasional"}
VALID_TIERS = {"tier1", "tier2", "tier3"}

# Domains that should NOT appear in press results
EXCLUDED_DOMAINS = {
    # Forums
    "reddit.com", "quora.com", "stackexchange.com", "stackoverflow.com",
    # Review platforms
    "trustpilot.com", "yelp.com", "g2.com", "capterra.com",
    "tripadvisor.com", "booking.com", "productreview.com.au",
    # Employee sites
    "glassdoor.com", "indeed.com", "comparably.com", "ambitionbox.com",
    "naukri.com", "kununu.com",
    # Social media (not press)
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "youtube.com", "linkedin.com",
    # Directories
    "justdial.com", "sulekha.com", "yellowpages.com",
    # Google
    "google.com",
}

# Generic narrative labels to reject
GENERIC_NARRATIVE_PATTERNS = [
    r"^(positive|negative|mixed)\s*(coverage|reception|reviews?)$",
    r"^(good|bad|great)\s*(press|coverage|reputation)$",
    r"^general\s*(coverage|mentions|press)$",
    r"^(brand|company)\s*(overview|profile|description)$",
    r"^online\s*presence$",
]


def _is_excluded_domain(url: str, brand_domain: str = "") -> bool:
    """Check if URL belongs to an excluded domain."""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # Check excluded domains
        if any(excl in domain for excl in EXCLUDED_DOMAINS):
            return True

        # Exclude brand's own website
        if brand_domain:
            brand_clean = brand_domain.lower().replace("www.", "").replace("https://", "").replace("http://", "").rstrip("/")
            if brand_clean and brand_clean in domain:
                return True

        return False
    except Exception:
        return True


def _is_press_source(url: str) -> bool:
    """Check if URL is from a legitimate press/media source (not forum or review)."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        # Reject if it's in excluded set
        if any(excl in domain for excl in EXCLUDED_DOMAINS):
            return False
        # Accept anything that has a domain and isn't excluded
        return bool(domain)
    except Exception:
        return False


def _matches_any(text: str, patterns: List[str]) -> bool:
    text_lower = text.strip().lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def _dedup_articles(articles: List[Dict]) -> List[Dict]:
    """Deduplicate articles by canonical URL."""
    seen_urls = set()
    deduped = []
    for a in articles:
        url = a.get("url", "").strip().rstrip("/").lower()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(a)
    return deduped


def postprocess_press_media(
    discovery: Dict[str, Any],
    analysis: Dict[str, Any],
    brand_domain: str = "",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Main post-processing pipeline for press/media data.
    Returns (processed_data, audit_stats).
    """
    stats = {
        "articles_raw": 0,
        "articles_excluded_domain": 0,
        "articles_deduped": 0,
        "articles_kept": 0,
        "narratives_raw": 0,
        "narratives_kept": 0,
        "generic_narratives_removed": 0,
        "narratives_no_evidence_removed": 0,
        "quotes_raw": 0,
        "quotes_kept": 0,
        "sources_found": [],
    }

    # 1. Process articles from discovery
    raw_articles = discovery.get("articles", [])
    stats["articles_raw"] = len(raw_articles)

    filtered_articles = []
    for a in raw_articles:
        url = a.get("url", "")

        if _is_excluded_domain(url, brand_domain):
            stats["articles_excluded_domain"] += 1
            logger.debug(f"[PRESS-PP] Excluded domain: {url[:80]}")
            continue

        filtered_articles.append(a)

    # Dedup
    deduped_articles = _dedup_articles(filtered_articles)
    stats["articles_deduped"] = len(filtered_articles) - len(deduped_articles)

    # Validate and cap
    validated_articles = []
    sources_seen = {}
    for a in deduped_articles[:30]:
        url = a.get("url", "")
        source_domain = ""
        try:
            source_domain = urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            pass

        source_name = str(a.get("source_name", source_domain))[:60]

        if source_domain:
            if source_domain not in sources_seen:
                sources_seen[source_domain] = {"name": source_name, "count": 0, "latest": None}
            sources_seen[source_domain]["count"] += 1
            pub_date = a.get("published_date")
            if pub_date:
                sources_seen[source_domain]["latest"] = str(pub_date)[:20]

        article_type = a.get("article_type", "news")
        if article_type not in VALID_ARTICLE_TYPES:
            article_type = "news"

        sentiment = a.get("sentiment", "neutral")
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "neutral"

        relevance = a.get("relevance_score_0_100", 50)
        if isinstance(relevance, (int, float)):
            relevance = max(0, min(100, int(relevance)))
        else:
            relevance = 50

        validated_articles.append({
            "url": url[:300],
            "title": str(a.get("title", ""))[:200],
            "source_name": source_name,
            "source_domain": source_domain[:60],
            "article_type": article_type,
            "published_date": str(a.get("published_date", ""))[:20] if a.get("published_date") else None,
            "excerpt": str(a.get("excerpt", ""))[:300],
            "sentiment": sentiment,
            "relevance_score_0_100": relevance,
        })

    stats["articles_kept"] = len(validated_articles)
    stats["sources_found"] = sorted(list(sources_seen.keys()))

    # 2. Process narratives from analysis
    raw_narratives = analysis.get("narratives", [])
    stats["narratives_raw"] = len(raw_narratives)

    validated_narratives = []
    for n in raw_narratives[:8]:
        label = str(n.get("label", "")).strip()
        if not label or len(label) < 3:
            continue

        if _matches_any(label, GENERIC_NARRATIVE_PATTERNS):
            stats["generic_narratives_removed"] += 1
            continue

        n_type = n.get("type", "narrative")
        if n_type not in VALID_NARRATIVE_TYPES:
            n_type = "narrative"

        sentiment = n.get("sentiment", "neutral")
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "neutral"

        frequency = n.get("frequency", "moderate")
        if frequency not in VALID_FREQUENCIES:
            frequency = "moderate"

        evidence = [str(e)[:150] for e in n.get("evidence", [])[:4] if len(str(e)) > 10]
        if not evidence:
            stats["narratives_no_evidence_removed"] += 1
            continue

        source_urls = [str(u)[:300] for u in n.get("source_urls", [])[:4] if str(u).startswith("http") and _is_press_source(str(u))]

        validated_narratives.append({
            "label": label[:80],
            "type": n_type,
            "sentiment": sentiment,
            "frequency": frequency,
            "evidence": evidence,
            "source_urls": source_urls,
        })

    stats["narratives_kept"] = len(validated_narratives)

    # 3. Process key quotes from analysis
    raw_quotes = analysis.get("key_quotes", [])
    stats["quotes_raw"] = len(raw_quotes)

    validated_quotes = []
    seen_quotes = set()
    for q in raw_quotes[:8]:
        quote_text = str(q.get("quote", "")).strip()
        if not quote_text or len(quote_text) < 20:
            continue
        quote_key = quote_text.lower()
        if quote_key in seen_quotes:
            continue
        seen_quotes.add(quote_key)

        validated_quotes.append({
            "quote": quote_text[:200],
            "source_name": str(q.get("source_name", ""))[:60],
            "source_url": str(q.get("source_url", ""))[:300],
            "context": str(q.get("context", ""))[:100],
            "is_paraphrased": True,
        })

    stats["quotes_kept"] = len(validated_quotes)

    # 4. Process media sources from analysis
    raw_sources = analysis.get("media_sources", [])
    validated_sources = []
    for s in raw_sources[:15]:
        tier = s.get("tier", "tier3")
        if tier not in VALID_TIERS:
            tier = "tier3"

        validated_sources.append({
            "name": str(s.get("name", ""))[:60],
            "domain": str(s.get("domain", ""))[:60],
            "tier": tier,
            "article_count": max(1, int(s.get("article_count", 1))) if isinstance(s.get("article_count"), (int, float)) else 1,
            "most_recent_date": str(s.get("most_recent_date", ""))[:20] if s.get("most_recent_date") else None,
        })

    # If analysis didn't provide media_sources, build from discovery data
    if not validated_sources and sources_seen:
        for domain, info in sorted(sources_seen.items(), key=lambda x: x[1]["count"], reverse=True)[:15]:
            validated_sources.append({
                "name": info["name"],
                "domain": domain,
                "tier": "tier3",
                "article_count": info["count"],
                "most_recent_date": info["latest"],
            })

    # 5. Process coverage summary, gaps, PR opportunities
    coverage_summary = [str(s)[:120] for s in analysis.get("coverage_summary", [])[:3] if len(str(s)) > 10]
    coverage_gaps = [str(g)[:120] for g in analysis.get("coverage_gaps", [])[:5] if len(str(g)) > 10]
    pr_opportunities = [str(p)[:120] for p in analysis.get("pr_opportunities", [])[:5] if len(str(p)) > 10]

    processed = {
        "articles": validated_articles,
        "narratives": validated_narratives,
        "key_quotes": validated_quotes,
        "media_sources": validated_sources,
        "coverage_summary": coverage_summary,
        "coverage_gaps": coverage_gaps,
        "pr_opportunities": pr_opportunities,
    }

    logger.info(
        f"[PRESS-PP] Result: {stats['articles_kept']} articles "
        f"({stats['articles_excluded_domain']} excluded, {stats['articles_deduped']} deduped), "
        f"{stats['narratives_kept']} narratives ({stats['generic_narratives_removed']} generic removed), "
        f"{stats['quotes_kept']} quotes, "
        f"sources: {stats['sources_found']}"
    )

    return processed, stats
