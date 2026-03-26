"""
Novara Research Foundation: Relevance Gate v2
Business-specific relevance scoring and filtering

Version 2.0 - Feb 2026
"""

import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ============== INTENT MODIFIER LISTS ==============

INTENT_MODIFIERS = {
    "price": ["price", "cost", "rates", "packages", "fee", "fees", "charges", "pricing", "how much", "affordable"],
    "trust": ["reviews", "review", "best", "trusted", "recommended", "top rated", "near me", "reliable"],
    "urgency": ["same day", "last minute", "today", "urgent", "emergency", "24/7", "asap", "now"],
    "comparison": ["vs", "versus", "alternative", "alternatives", "better than", "compare", "compared to", "top"]
}

# Flatten all modifiers for quick lookup
ALL_MODIFIERS: Set[str] = set()
for modifiers in INTENT_MODIFIERS.values():
    ALL_MODIFIERS.update(modifiers)

# Common category implied tokens (master list)
# These are generic industry terms that indicate relevance even without exact service match
CATEGORY_IMPLIED_TOKENS = {
    # Beauty & wellness
    "makeup", "hair", "salon", "spa", "beauty", "skincare", "facial", "massage",
    "nail", "nails", "manicure", "pedicure", "waxing", "threading", "lash", "lashes",
    "brow", "brows", "bridal", "wedding", "glam", "stylist", "artist",
    "treatment", "therapy", "wellness",
    # Home services
    "home service", "at home", "mobile", "doorstep", "on-demand",
    # Generic service terms
    "services", "service", "professional", "expert", "specialist"
}


@dataclass
class RelevanceResult:
    """Result of relevance gate check"""
    query: str
    is_relevant: bool
    score: int
    matched_rules: List[str]


def _query_contains_any(query: str, terms: List[str]) -> bool:
    """Check if query contains any of the terms"""
    query_lower = query.lower()
    for term in terms:
        if term.lower() in query_lower:
            return True
    return False


def _query_contains_modifier(query: str) -> Tuple[bool, str]:
    """Check if query contains any intent modifier"""
    query_lower = query.lower()
    for modifier in ALL_MODIFIERS:
        if modifier in query_lower:
            return True, modifier
    return False, ""


def check_relevance(
    query: str,
    service_terms: List[str],
    category_terms: List[str],
    competitor_terms: List[str],
    geo_terms: List[str]
) -> RelevanceResult:
    """
    Check if a query passes the relevance gate.
    
    Pass conditions (must satisfy at least one):
    - R1: contains any service_term
    - R2: contains any category_term
    - R3: contains any competitor_term
    - R4: contains a modifier AND contains either geo term OR category implied token
    
    Scoring:
    +4 contains service_term
    +3 contains category_term
    +2 contains geo_term
    +2 contains modifier
    +1 contains competitor_term
    -2 if > 8 words
    -2 if too generic (only common words)
    
    Threshold: score >= 4 to pass (can be relaxed)
    """
    query_lower = query.lower()
    word_count = len(query.split())
    
    score = 0
    matched_rules = []
    
    # R1: Service term check (+4)
    r1_matched = False
    for term in service_terms:
        if term.lower() in query_lower:
            score += 4
            matched_rules.append(f"R1:service:{term}")
            r1_matched = True
            break
    
    # R2: Category term check (+3)
    r2_matched = False
    for term in category_terms:
        if term.lower() in query_lower:
            score += 3
            matched_rules.append(f"R2:category:{term}")
            r2_matched = True
            break
    
    # R3: Competitor term check (+1)
    r3_matched = False
    for term in competitor_terms:
        if term.lower() in query_lower:
            score += 1
            matched_rules.append(f"R3:competitor:{term}")
            r3_matched = True
            break
    
    # Geo term check (+2)
    geo_matched = False
    for term in geo_terms:
        if term.lower() in query_lower:
            score += 2
            matched_rules.append(f"geo:{term}")
            geo_matched = True
            break
    
    # Modifier check (+2)
    has_modifier, modifier = _query_contains_modifier(query)
    if has_modifier:
        score += 2
        matched_rules.append(f"modifier:{modifier}")
    
    # R4: Modifier + (geo OR category implied)
    r4_matched = False
    if has_modifier:
        # Check category implied tokens
        category_implied_matched = False
        for token in CATEGORY_IMPLIED_TOKENS:
            if token in query_lower:
                category_implied_matched = True
                matched_rules.append(f"R4:implied:{token}")
                break
        
        if geo_matched or category_implied_matched:
            r4_matched = True
    
    # Penalties
    if word_count > 8:
        score -= 2
        matched_rules.append("penalty:long")
    
    # Too generic penalty (only very common words, no specificity)
    generic_only_words = {"the", "a", "an", "in", "for", "and", "or", "to", "of", "best", "top", "near", "me"}
    query_words = set(query_lower.split())
    non_generic = query_words - generic_only_words
    if len(non_generic) <= 1:
        score -= 2
        matched_rules.append("penalty:generic")
    
    # Determine if relevant (passes gate)
    passes_rule = r1_matched or r2_matched or r3_matched or r4_matched
    is_relevant = passes_rule and score >= 4
    
    return RelevanceResult(
        query=query,
        is_relevant=is_relevant,
        score=score,
        matched_rules=matched_rules
    )


def filter_by_relevance(
    queries: List[str],
    service_terms: List[str],
    category_terms: List[str],
    competitor_terms: List[str],
    geo_terms: List[str],
    min_threshold: int = 4,
    relax_threshold: bool = True
) -> Tuple[List[Tuple[str, int]], int]:
    """
    Filter queries through relevance gate with scoring.
    
    Args:
        queries: Cleaned queries to filter
        service_terms: Business service terms
        category_terms: Category/niche terms
        competitor_terms: Competitor names
        geo_terms: Geographic terms
        min_threshold: Minimum score to pass (default 4)
        relax_threshold: If True, progressively relax threshold if too few pass
    
    Returns:
        Tuple of (list of (query, score) tuples, dropped_count)
    """
    results = []
    
    for query in queries:
        result = check_relevance(
            query=query,
            service_terms=service_terms,
            category_terms=category_terms,
            competitor_terms=competitor_terms,
            geo_terms=geo_terms
        )
        results.append(result)
    
    # Filter by threshold
    threshold = min_threshold
    passed = [(r.query, r.score) for r in results if r.score >= threshold]
    
    # Progressive relaxation if too few pass
    if relax_threshold and len(passed) < 10:
        for lower_threshold in [3, 2]:
            passed = [(r.query, r.score) for r in results if r.score >= lower_threshold]
            if len(passed) >= 10:
                threshold = lower_threshold
                logger.info(f"Relaxed relevance threshold to {threshold} (got {len(passed)} queries)")
                break
    
    dropped = len(queries) - len(passed)
    
    logger.info(f"Relevance filter: {len(queries)} -> {len(passed)} (threshold={threshold}, dropped={dropped})")
    
    return passed, dropped


def get_modifier_lists() -> Dict[str, List[str]]:
    """Return intent modifier lists for reference"""
    return {k: v.copy() for k, v in INTENT_MODIFIERS.items()}
