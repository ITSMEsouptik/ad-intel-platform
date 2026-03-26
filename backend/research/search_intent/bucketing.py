"""
Novara Research Foundation: Query Bucketing v2
Rule-based intent classification

Version 2.0 - Feb 2026
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# ============== BUCKET DEFINITIONS (LOCKED) ==============

BUCKET_KEYWORDS = {
    "price": [
        "price", "pricing", "cost", "costs", "rate", "rates",
        "packages", "package", "fee", "fees", "charge", "charges",
        "how much", "affordable", "cheap", "expensive", "budget"
    ],
    "trust": [
        "review", "reviews", "rated", "rating", "ratings",
        "best", "top", "recommended", "trusted", "reliable",
        "reputation", "testimonial", "testimonials", "feedback"
    ],
    "urgency": [
        "same day", "today", "now", "urgent", "emergency",
        "last minute", "asap", "immediate", "24/7", "24 hour",
        "quick", "fast", "express", "rush"
    ],
    "comparison": [
        " vs ", "versus", "alternative", "alternatives",
        "compared to", "comparison", "difference between",
        " or ", "better than", "similar to"
    ]
}

# Compile patterns
BUCKET_PATTERNS: Dict[str, List[re.Pattern]] = {}
for bucket, keywords in BUCKET_KEYWORDS.items():
    BUCKET_PATTERNS[bucket] = [
        re.compile(rf'\b{re.escape(kw)}\b' if ' ' not in kw else re.escape(kw), re.IGNORECASE)
        for kw in keywords
    ]

# Bucket cap per bucket
BUCKET_CAP = 20


def classify_query(query: str) -> str:
    """
    Classify a query into an intent bucket.
    
    Priority order (first match wins):
    1. Price
    2. Trust
    3. Urgency
    4. Comparison
    5. General (default)
    """
    query_lower = query.lower()
    
    for bucket in ["price", "trust", "urgency", "comparison"]:
        patterns = BUCKET_PATTERNS[bucket]
        for pattern in patterns:
            if pattern.search(query_lower):
                return bucket
    
    return "general"


def bucket_queries_with_scores(
    queries_with_scores: List[Tuple[str, int]],
    bucket_cap: int = BUCKET_CAP
) -> Dict[str, List[str]]:
    """
    Bucket queries that have passed relevance gate.
    Preserves score-based ordering within each bucket.
    
    Args:
        queries_with_scores: List of (query, score) tuples sorted by score desc
        bucket_cap: Maximum queries per bucket
    
    Returns:
        Dict with bucket names as keys and lists of queries as values
    """
    buckets: Dict[str, List[str]] = {
        "price": [],
        "trust": [],
        "urgency": [],
        "comparison": [],
        "general": []
    }
    
    for query, score in queries_with_scores:
        bucket = classify_query(query)
        
        if len(buckets[bucket]) < bucket_cap:
            buckets[bucket].append(query)
    
    distribution = {k: len(v) for k, v in buckets.items()}
    logger.info(f"Bucketed {len(queries_with_scores)} queries: {distribution}")
    
    return buckets


def get_bucket_keywords() -> Dict[str, List[str]]:
    """Return bucket keywords for reference"""
    return {k: v.copy() for k, v in BUCKET_KEYWORDS.items()}
