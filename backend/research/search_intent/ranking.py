"""
Novara Research Foundation: Query Ranking v2.1
Score-based ranking with diversity enforcement

Version 2.1 - Feb 2026
- Scoring: +3 service, +2 geo, +2 booking/urgent, +1 trust, +1 price
- Top 10 diversity: max 4 "near me", max 4 "price" variants
- Ad keywords: 35 cap
- Forum queries: from trust/price/pain buckets, exclude urgency-only
"""

import logging
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher
from .brp import BRP

logger = logging.getLogger(__name__)

# Modifier categories for scoring
BOOKING_URGENT_MODIFIERS = [
    "near me", "open now", "book", "booking", "appointment",
    "same day", "today", "now", "urgent", "asap", "24/7",
    "at home", "home service", "mobile", "quote"
]
TRUST_MODIFIERS = ["best", "top", "reviews", "review", "recommended", "trusted", "rated", "reliable"]
PRICE_MODIFIERS = ["price", "cost", "cheap", "affordable", "rates", "fee", "fees", "how much", "packages", "budget"]


def score_queries(queries: List[str], brp: BRP) -> List[Tuple[str, int]]:
    """
    Score filtered queries using BRP terms.

    Weights (per spec v2.1):
    +3 service term match
    +2 geo term match
    +2 booking/urgent modifier
    +1 trust modifier
    +1 price modifier
    +1 category term match
    -1 if > 6 words
    """
    scored = []
    for query in queries:
        q_lower = query.lower()
        score = 0

        # Service term match (+3)
        for term in brp.service_terms:
            if term.lower() in q_lower:
                score += 3
                break

        # Geo term match (+2)
        for term in brp.geo_terms:
            if term.lower() in q_lower:
                score += 2
                break

        # Booking/urgent modifier (+2)
        for mod in BOOKING_URGENT_MODIFIERS:
            if mod in q_lower:
                score += 2
                break

        # Trust modifier (+1)
        for mod in TRUST_MODIFIERS:
            if mod in q_lower:
                score += 1
                break

        # Price modifier (+1)
        for mod in PRICE_MODIFIERS:
            if mod in q_lower:
                score += 1
                break

        # Category term match (+1)
        for term in brp.category_terms:
            if term.lower() in q_lower:
                score += 1
                break

        # Length penalty
        if len(query.split()) > 6:
            score -= 1

        scored.append((query, max(score, 0)))

    logger.info(f"[RANKING] Scored {len(scored)} queries")
    return scored


def normalize_for_dedupe(query: str) -> str:
    """Normalize query for deduplication."""
    words = sorted(query.lower().split())
    fillers = {"in", "the", "a", "an", "for", "at", "of"}
    words = [w for w in words if w not in fillers]
    return " ".join(words)


def dedupe_by_similarity(
    queries_with_scores: List[Tuple[str, int]],
    similarity_threshold: float = 0.85
) -> List[Tuple[str, int]]:
    """Remove near-duplicate queries keeping the higher scored one."""
    deduped: List[Tuple[str, int]] = []
    seen_normalized: Set[str] = set()

    for query, score in queries_with_scores:
        normalized = normalize_for_dedupe(query)
        if normalized in seen_normalized:
            continue
        is_dupe = False
        for existing, _ in deduped:
            existing_normalized = normalize_for_dedupe(existing)
            similarity = SequenceMatcher(None, normalized, existing_normalized).ratio()
            if similarity >= similarity_threshold:
                is_dupe = True
                break
        if not is_dupe:
            deduped.append((query, score))
            seen_normalized.add(normalized)

    return deduped


def rank_and_cap(
    queries_with_scores: List[Tuple[str, int]],
    total_cap: int = 150
) -> List[Tuple[str, int]]:
    """Sort by score descending, then by length ascending, and cap."""
    sorted_queries = sorted(queries_with_scores, key=lambda x: (-x[1], len(x[0])))
    return sorted_queries[:total_cap]


def _classify_variant(query: str) -> str:
    """Classify a query into a variant type for diversity enforcement."""
    q = query.lower()
    if "near me" in q:
        return "near_me"
    for mod in PRICE_MODIFIERS:
        if mod in q:
            return "price"
    for mod in TRUST_MODIFIERS:
        if mod in q:
            return "trust"
    for mod in BOOKING_URGENT_MODIFIERS:
        if mod in q:
            return "booking"
    return "other"


def select_top_10(
    buckets: Dict[str, List[str]],
    queries_with_scores: List[Tuple[str, int]],
    max_per_bucket: int = 3
) -> List[str]:
    """
    Select top 10 queries with diversity enforcement.

    Rules:
    - Max 3 per intent bucket
    - Max 4 "near me" variants
    - Max 4 "price" variants
    - Rest: trust/general/service variants
    """
    score_map = {q: s for q, s in queries_with_scores}
    bucket_counts: Dict[str, int] = {b: 0 for b in buckets}
    variant_counts: Dict[str, int] = {"near_me": 0, "price": 0, "trust": 0, "booking": 0, "other": 0}
    variant_limits = {"near_me": 4, "price": 4, "trust": 4, "booking": 4, "other": 10}

    candidates = []
    for bucket, queries in buckets.items():
        for query in queries:
            score = score_map.get(query, 0)
            candidates.append((query, bucket, score))

    candidates.sort(key=lambda x: -x[2])

    top_10 = []
    for query, bucket, _ in candidates:
        variant = _classify_variant(query)
        if (bucket_counts[bucket] < max_per_bucket
                and variant_counts.get(variant, 0) < variant_limits.get(variant, 10)):
            top_10.append(query)
            bucket_counts[bucket] += 1
            variant_counts[variant] = variant_counts.get(variant, 0) + 1

        if len(top_10) >= 10:
            break

    # If we couldn't fill 10 with diversity constraints, relax and fill
    if len(top_10) < 10:
        for query, bucket, _ in candidates:
            if query not in top_10:
                top_10.append(query)
            if len(top_10) >= 10:
                break

    logger.info(f"[RANKING] Selected top {len(top_10)} from {len(candidates)} candidates")
    return top_10


def generate_ad_keyword_queries(
    queries_with_scores: List[Tuple[str, int]],
    min_words: int = 2,
    max_words: int = 7,
    limit: int = 35
) -> List[str]:
    """
    Generate queries optimized for ad library search.
    Cap: 35 (configurable). Prefer geo+service or service+intent.
    Remove single-word generic queries.
    """
    filtered = []
    for query, score in queries_with_scores:
        word_count = len(query.split())
        if min_words <= word_count <= max_words:
            filtered.append((query, score))

    deduped = dedupe_by_similarity(filtered)
    ad_queries = [q for q, _ in deduped[:limit]]

    logger.info(f"[RANKING] Generated {len(ad_queries)} ad keyword queries (cap={limit})")
    return ad_queries


def generate_forum_queries(
    queries: List[str],
    buckets: Dict[str, List[str]],
    limit_per_platform: int = 15
) -> Dict[str, List[str]]:
    """
    Generate forum search queries for Reddit and Quora.
    Source from trust/price/general buckets (not urgency — "open now" is useless on forums).
    """
    # Priority buckets for forum research
    forum_buckets = ["trust", "price", "comparison", "general"]
    priority_queries = []

    for bucket in forum_buckets:
        priority_queries.extend(buckets.get(bucket, [])[:6])

    # Dedupe
    seen = set()
    unique_queries = []
    for q in priority_queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique_queries.append(q)

    reddit_queries = [f'site:reddit.com "{q}"' for q in unique_queries[:limit_per_platform]]
    quora_queries = [f'site:quora.com "{q}"' for q in unique_queries[:limit_per_platform]]

    logger.info(f"[RANKING] Forum queries: reddit={len(reddit_queries)}, quora={len(quora_queries)}")

    return {
        "reddit": reddit_queries,
        "quora": quora_queries
    }
