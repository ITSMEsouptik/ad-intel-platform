"""
Novara Research Foundation: Query Cleaning v2
Hard blocklist filtering and normalization

Version 2.0 - Feb 2026
"""

import re
import logging
from typing import List, Set, Optional, Tuple

logger = logging.getLogger(__name__)

# ============== HARD BLOCKLIST (LOCKED) ==============

# Always drop if contains any of these tokens
HARD_BLOCKLIST = [
    # Job-related
    "jobs", "job", "hiring", "career", "careers", "salary", "salaries",
    "internship", "intern", "vacancy", "vacancies", "recruitment", "recruiter",
    
    # Education/training (unless brand sells workshops)
    "course", "courses", "training", "class", "classes", "tutorial", "tutorials",
    "certification", "certificate", "degree", "school", "college", "university",
    "learn how", "how to become", "curriculum", "syllabus",
    
    # Downloads/templates
    "template", "templates", "pdf", "download", "downloads", "ebook", "free ebook",
    
    # Wholesale/B2B
    "wholesale", "wholesaler", "supplier", "suppliers", "manufacturer", "manufacturers",
    "distributor", "distributors", "bulk order", "b2b",
    
    # Website/tech noise
    "login", "log in", "sign in", "customer care", "contact number", "address",
    "wix", "shopify", "wordpress", "theme", "plugin",
    
    # Spam patterns
    "meaning", "definition", "wikipedia", "wiki", "what is", "synonym", "essay",
    "assignment", "franchise", "mlm", "pyramid"
]

# Workshop-related terms that should be blocklisted UNLESS sells_workshops=True
WORKSHOP_BLOCKLIST = [
    "workshop", "workshops", "masterclass", "masterclasses", "bootcamp", "bootcamps",
    "academy", "institute", "session", "sessions", "lesson", "lessons"
]

# Optional blocklist (can be toggled)
DISCOUNT_BLOCKLIST = [
    "free", "coupon", "coupons", "promo", "promo code", "discount", "discounts",
    "voucher", "vouchers", "deal", "deals"
]

# Compile patterns for faster matching
def _compile_patterns(words: List[str]) -> List[re.Pattern]:
    return [re.compile(rf'\b{re.escape(w)}\b', re.IGNORECASE) for w in words]

HARD_PATTERNS = _compile_patterns(HARD_BLOCKLIST)
WORKSHOP_PATTERNS = _compile_patterns(WORKSHOP_BLOCKLIST)
DISCOUNT_PATTERNS = _compile_patterns(DISCOUNT_BLOCKLIST)


def normalize_query(query: str) -> str:
    """
    Normalize a query string.
    - Lowercase
    - Collapse whitespace
    - Strip punctuation at ends
    """
    if not query:
        return ""
    
    normalized = query.lower()
    normalized = " ".join(normalized.split())
    normalized = normalized.strip(".,;:!?\"'()-_")
    
    return normalized


def get_word_count(query: str) -> int:
    """Get word count of a query"""
    return len(query.split())


def contains_blocklist_token(
    query: str,
    sells_workshops: bool = False,
    allow_discounts: bool = False
) -> Tuple[bool, str]:
    """
    Check if query contains any blocklist token.
    
    Returns:
        Tuple of (is_blocked, reason)
    """
    query_lower = query.lower()
    
    # Hard blocklist (always apply)
    for pattern in HARD_PATTERNS:
        if pattern.search(query_lower):
            return True, "hard_blocklist"
    
    # Workshop blocklist (apply unless sells_workshops)
    if not sells_workshops:
        for pattern in WORKSHOP_PATTERNS:
            if pattern.search(query_lower):
                return True, "workshop_blocklist"
    
    # Discount blocklist (apply unless allow_discounts)
    if not allow_discounts:
        for pattern in DISCOUNT_PATTERNS:
            if pattern.search(query_lower):
                return True, "discount_blocklist"
    
    return False, ""


def is_nav_intent(query: str, brand_name: str = "") -> bool:
    """
    Check if query is navigational intent (just brand name / login).
    
    Examples:
    - "example-brand login" -> True
    - "example-brand dubai" -> False
    """
    if not brand_name:
        return False
    
    query_lower = query.lower()
    brand_lower = brand_name.lower()
    
    # Check if query is just brand name with nav terms
    nav_terms = ["login", "log in", "sign in", "sign up", "register", "app", "website", "site"]
    
    for term in nav_terms:
        if query_lower == f"{brand_lower} {term}" or query_lower == f"{term} {brand_lower}":
            return True
    
    # Check if query is just the brand name
    if query_lower == brand_lower:
        return True
    
    return False


def clean_suggestions(
    suggestions: List[str],
    sells_workshops: bool = False,
    allow_discounts: bool = False,
    brand_name: str = "",
    min_words: int = 2,
    max_words: int = 10
) -> Tuple[List[str], int, int]:
    """
    Clean and filter suggestions through blocklist.
    
    Args:
        suggestions: Raw suggestions
        sells_workshops: If True, allow workshop-related queries
        allow_discounts: If True, allow discount-related queries
        brand_name: Brand name for nav intent detection
        min_words: Minimum word count (default 2)
        max_words: Maximum word count (default 10)
    
    Returns:
        Tuple of (cleaned_list, blocklist_count, total_dropped)
    """
    if not suggestions:
        return [], 0, 0
    
    cleaned: List[str] = []
    seen: Set[str] = set()
    blocklist_count = 0
    total_dropped = 0
    
    for suggestion in suggestions:
        # Normalize
        normalized = normalize_query(suggestion)
        
        # Skip empty
        if not normalized:
            total_dropped += 1
            continue
        
        # Skip duplicates
        if normalized in seen:
            total_dropped += 1
            continue
        seen.add(normalized)
        
        # Word count check
        word_count = get_word_count(normalized)
        if word_count < min_words or word_count > max_words:
            total_dropped += 1
            continue
        
        # Blocklist check
        is_blocked, reason = contains_blocklist_token(normalized, sells_workshops, allow_discounts)
        if is_blocked:
            blocklist_count += 1
            total_dropped += 1
            continue
        
        # Nav intent check
        if is_nav_intent(normalized, brand_name):
            total_dropped += 1
            continue
        
        cleaned.append(normalized)
    
    logger.info(f"Cleaned: {len(suggestions)} -> {len(cleaned)} "
                f"(blocklist: {blocklist_count}, total dropped: {total_dropped})")
    
    return cleaned, blocklist_count, total_dropped


def get_blocklist_tokens() -> List[str]:
    """Return all blocklist tokens (for debugging)"""
    return HARD_BLOCKLIST + WORKSHOP_BLOCKLIST + DISCOUNT_BLOCKLIST
