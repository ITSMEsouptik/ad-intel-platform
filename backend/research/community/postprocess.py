"""
Novara Research Foundation: Community Intelligence — Post-Processor
Version 1.1 - Feb 2026

Deterministic cleanup:
- Dedup threads by URL
- Enforce forum-only domain allowlist on threads AND theme source_urls
- Reject generic/empty themes
- Validate enums (type, frequency)
- Cap lengths and counts
- Dedup language bank entries
- Exclude brand's own domain, press/magazine sites, review sites, employee sites
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Theme type + frequency validation
VALID_THEME_TYPES = {"pain", "objection", "desire", "trigger", "comparison", "how_to"}
VALID_FREQUENCIES = {"high", "medium", "low"}

# Generic theme labels to reject (too vague)
GENERIC_THEME_PATTERNS = [
    r"^(quality|service|value|price)\s*(concerns?|issues?)?$",
    r"^(good|bad|great|poor)\s*(service|quality|experience)?$",
    r"^general\s*(feedback|sentiment|discussion)$",
    r"^(customer|user)\s*(experience|satisfaction)$",
    r"^(positive|negative)\s*(feedback|reviews?)$",
]

# Excluded domains (review platforms, employee sites)
EXCLUDED_DOMAINS = {
    "trustpilot.com", "yelp.com", "g2.com", "capterra.com",
    "tripadvisor.com", "booking.com", "productreview.com.au",
    "glassdoor.com", "indeed.com", "comparably.com", "ambitionbox.com",
    "naukri.com", "kununu.com",
    "google.com", "facebook.com",
    "justdial.com", "sulekha.com", "practo.com",
}

# Press / magazine / news domains — NOT community discussions
PRESS_DOMAINS = {
    "graziamagazine.com", "vogue.com", "elle.com", "cosmopolitan.com",
    "forbes.com", "bloomberg.com", "techcrunch.com", "mashable.com",
    "theverge.com", "wired.com", "bbc.com", "cnn.com", "reuters.com",
    "arabianbusiness.com", "gulfnews.com", "khaleejtimes.com",
    "timeoutdubai.com", "thenationalnews.com", "azyaamode.net",
    "medium.com",  # medium is articles, not forums
    "wikipedia.org",
}

# Allowed forum/community domains — ONLY these are valid sources
FORUM_DOMAIN_ALLOWLIST = {
    "reddit.com", "quora.com", "stackexchange.com", "stackoverflow.com",
    "indiehackers.com", "producthunt.com", "news.ycombinator.com",
    "boards.ie", "mumsnet.com", "studentroom.co.uk",
    "bogleheads.org", "biggerpockets.com", "bodybuilding.com",
    "healthboards.com", "avsforum.com", "head-fi.org",
    "whirlpool.net.au", "redflagdeals.com", "hardwarezone.com.sg",
}


def _matches_any(text: str, patterns: List[str]) -> bool:
    text_lower = text.strip().lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def _is_excluded_domain(url: str, brand_domain: str = "") -> bool:
    """Check if URL belongs to an excluded domain (reviews, employee, press, brand's own site)."""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # Check review/employee exclusions
        if any(excl in domain for excl in EXCLUDED_DOMAINS):
            return True

        # Check press/magazine exclusions
        if any(press in domain for press in PRESS_DOMAINS):
            return True

        # Exclude brand's own website
        if brand_domain:
            brand_clean = brand_domain.lower().replace("www.", "").replace("https://", "").replace("http://", "").rstrip("/")
            if brand_clean and brand_clean in domain:
                return True

        return False
    except Exception:
        return True


def _is_forum_domain(url: str) -> bool:
    """Check if URL is from an allowed forum/community domain."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")
        return any(forum in domain for forum in FORUM_DOMAIN_ALLOWLIST)
    except Exception:
        return False


def _dedup_threads(threads: List[Dict]) -> List[Dict]:
    """Deduplicate threads by canonical URL."""
    seen_urls = set()
    deduped = []
    for t in threads:
        url = t.get("url", "").strip().rstrip("/").lower()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(t)
    return deduped


def _dedup_strings(items: List[str], max_len: int = 200) -> List[str]:
    """Deduplicate strings case-insensitively."""
    seen = set()
    result = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen and len(item) <= max_len:
            seen.add(key)
            result.append(item.strip())
    return result


def postprocess_community(
    discovery: Dict[str, Any],
    synthesis: Dict[str, Any],
    brand_domain: str = "",
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Main post-processing pipeline for community data.
    v1.1: Enforces forum-only domains on threads AND theme source_urls.
    Returns (processed_data, audit_stats).
    """
    stats = {
        "threads_raw": 0,
        "threads_excluded_domain": 0,
        "threads_not_forum": 0,
        "threads_deduped": 0,
        "threads_kept": 0,
        "themes_raw": 0,
        "themes_kept": 0,
        "themes_no_forum_source": 0,
        "generic_themes_removed": 0,
        "themes_no_evidence_removed": 0,
        "phrases_raw": 0,
        "phrases_kept": 0,
        "words_raw": 0,
        "words_kept": 0,
        "domains_found": [],
    }

    # 1. Process threads from discovery — STRICT forum-only enforcement
    raw_threads = discovery.get("threads", [])
    stats["threads_raw"] = len(raw_threads)

    filtered_threads = []
    for t in raw_threads:
        url = t.get("url", "")

        # Filter excluded domains (reviews, employee, press, brand's own site)
        if _is_excluded_domain(url, brand_domain):
            stats["threads_excluded_domain"] += 1
            logger.debug(f"[COMMUNITY-PP] Excluded domain: {url[:80]}")
            continue

        # STRICT: Only allow threads from known forum domains
        if not _is_forum_domain(url):
            stats["threads_not_forum"] += 1
            logger.debug(f"[COMMUNITY-PP] Not a forum domain: {url[:80]}")
            continue

        filtered_threads.append(t)

    # Dedup
    deduped_threads = _dedup_threads(filtered_threads)
    stats["threads_deduped"] = len(filtered_threads) - len(deduped_threads)

    # Validate and cap
    validated_threads = []
    domains_seen = set()
    for t in deduped_threads[:40]:
        url = t.get("url", "")
        domain = ""
        try:
            domain = urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            pass

        if domain:
            domains_seen.add(domain)

        relevance = t.get("relevance_score_0_100", 50)
        if isinstance(relevance, (int, float)):
            relevance = max(0, min(100, int(relevance)))
        else:
            relevance = 50

        validated_threads.append({
            "url": url[:300],
            "domain": domain[:50],
            "title": str(t.get("title", ""))[:150] if t.get("title") else None,
            "published_at": str(t.get("published_at", ""))[:20] if t.get("published_at") else None,
            "query_used": str(t.get("query_used", ""))[:100],
            "excerpt": str(t.get("excerpt", ""))[:280],
            "comment_count_est": t.get("comment_count_est") if isinstance(t.get("comment_count_est"), int) else None,
            "relevance_score_0_100": relevance,
        })

    stats["threads_kept"] = len(validated_threads)
    stats["domains_found"] = sorted(list(domains_seen))

    # 2. Process themes from synthesis — validate source_urls against forum allowlist
    raw_themes = synthesis.get("themes", [])
    stats["themes_raw"] = len(raw_themes)

    validated_themes = []
    for th in raw_themes[:10]:
        label = str(th.get("label", "")).strip()
        if not label or len(label) < 3:
            continue

        # Reject generic
        if _matches_any(label, GENERIC_THEME_PATTERNS):
            stats["generic_themes_removed"] += 1
            continue

        # Validate type
        theme_type = th.get("type", "pain")
        if theme_type not in VALID_THEME_TYPES:
            theme_type = "pain"

        # Validate frequency
        frequency = th.get("frequency", "medium")
        if frequency not in VALID_FREQUENCIES:
            frequency = "medium"

        # Validate evidence
        evidence = [str(e)[:140] for e in th.get("evidence", [])[:4] if len(str(e)) > 10]
        if not evidence:
            stats["themes_no_evidence_removed"] += 1
            continue

        # STRICT: Validate source URLs — only keep forum URLs
        raw_urls = th.get("source_urls", [])
        forum_urls = [str(u)[:300] for u in raw_urls[:4] if str(u).startswith("http") and _is_forum_domain(str(u))]

        if not forum_urls:
            stats["themes_no_forum_source"] += 1
            logger.debug(f"[COMMUNITY-PP] Theme '{label}' rejected: no forum source URLs (had: {[str(u)[:60] for u in raw_urls]})")
            continue

        validated_themes.append({
            "label": label[:60],
            "type": theme_type,
            "frequency": frequency,
            "evidence": evidence,
            "source_urls": forum_urls,
        })

    stats["themes_kept"] = len(validated_themes)

    # 3. Process language bank
    raw_lb = synthesis.get("language_bank", {})

    raw_phrases = raw_lb.get("phrases", [])
    stats["phrases_raw"] = len(raw_phrases)
    validated_phrases = _dedup_strings(
        [str(p)[:80] for p in raw_phrases if len(str(p)) > 3],
        max_len=80
    )[:20]
    stats["phrases_kept"] = len(validated_phrases)

    raw_words = raw_lb.get("words", [])
    stats["words_raw"] = len(raw_words)
    validated_words = _dedup_strings(
        [str(w)[:30] for w in raw_words if len(str(w)) > 1],
        max_len=30
    )[:30]
    stats["words_kept"] = len(validated_words)

    # 4. Process audience notes
    raw_notes = synthesis.get("audience_notes", [])
    validated_notes = [str(n)[:120] for n in raw_notes[:6] if len(str(n)) > 10]

    # 5. Process creative implications
    raw_implications = synthesis.get("creative_implications", [])
    validated_implications = [str(c)[:120] for c in raw_implications[:6] if len(str(c)) > 10]

    # 6. Process gaps
    raw_gaps = synthesis.get("gaps_to_research", [])
    validated_gaps = [str(g)[:120] for g in raw_gaps[:6] if len(str(g)) > 10]

    processed = {
        "threads": validated_threads,
        "themes": validated_themes,
        "language_bank": {
            "phrases": validated_phrases,
            "words": validated_words,
        },
        "audience_notes": validated_notes,
        "creative_implications": validated_implications,
        "gaps_to_research": validated_gaps,
    }

    logger.info(
        f"[COMMUNITY-PP] Result: {stats['threads_kept']} threads "
        f"({stats['threads_excluded_domain']} excluded, {stats['threads_not_forum']} not-forum, "
        f"{stats['threads_deduped']} deduped), "
        f"{stats['themes_kept']} themes ({stats['generic_themes_removed']} generic removed, "
        f"{stats['themes_no_forum_source']} no-forum-source), "
        f"{stats['phrases_kept']} phrases, {stats['words_kept']} words, "
        f"domains: {stats['domains_found']}"
    )

    return processed, stats
