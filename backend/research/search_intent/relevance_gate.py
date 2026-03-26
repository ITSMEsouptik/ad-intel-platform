"""
Novara Research Foundation: Relevance Gate v3.1
Deterministic business-relevant filtering using BRP.

Version 3.1 - Feb 2026
Rules:
- R1: Geo mismatch rejection
- R2: Product intent rejection (service_booking/medical unless ecom signals)
- R3: Procedure intent rejection (service_booking unless medical brand)
- R4: Unit/noise rejection
- R5: Junk pattern rejection
- R6: Too generic / non-actionable
- R7: Service token + modifier/geo match (service_booking)
- Relaxation: if <10 kept, relax R7 to service_token-only
"""

import re
import logging
from typing import List, Dict, Tuple
from .brp import BRP

logger = logging.getLogger(__name__)

# ============== TOKEN SETS (generic, not brand-specific) ==============

JUNK_TOKENS = [
    "dummy", "pdf", "wiki", "wikipedia", "jobs", "job", "salary", "salaries",
    "meaning", "definition", "template", "templates", "essay", "assignment",
    "franchise", "mlm", "synonym", "hiring", "career", "vacancy",
    "internship", "login", "sign in", "sign up", "customer care",
    "wholesale", "distributor", "manufacturer", "b2b"
]

PRODUCT_TOKENS = [
    "kit", "kits", "brands", "products", "product", "serum", "serums",
    "dryer", "straightener", "straighteners", "remover",
    "brushes", "brush", "accessories", "accessory",
    "amazon", "noon", "sephora", "aliexpress", "shein", "temu", "ebay",
    "buy online", "coupon code", "review product", "unboxing",
    "haul", "swatch", "swatches", "diy", "homemade",
    "ingredients", "recipe", "supplement", "vitamin",
    "cream", "oil", "shampoo", "conditioner", "toner", "cleanser",
    "machine", "device", "tool", "tools",
    "supply", "supplies", "subscription box", "subscription boxes",
    "advent calendar", "advent calendars", "gift set", "gift sets",
    "bag", "bags", "primer", "concealer", "foundation",
    "palette", "palettes", "mascara", "lipstick", "eyeliner",
    "moisturizer", "sunscreen", "mask"
]

PROCEDURE_TOKENS = [
    "transplant", "botox", "filler", "fillers", "laser", "surgery",
    "clinic", "doctor", "dermatologist", "dermatology",
    "dentist", "dental", "surgeon", "liposuction", "rhinoplasty",
    "implant", "implants", "injection", "injections",
    "prp", "mesotherapy", "microneedling"
]

UNIT_NOISE_TOKENS = [
    "kg", "1kg", "per kg", "rate today", "stock", "price today",
    "gram", "per gram", "ton", "per ton", "litre", "per litre",
    "quintal", "wholesale rate", "market rate", "mandi",
    "commodity", "futures"
]

INTENT_MODIFIERS = [
    "near me", "open now", "book", "booking", "price", "cost",
    "best", "reviews", "top", "at home", "home service", "mobile",
    "same day", "today", "now", "how much", "affordable", "cheap",
    "rates", "fee", "fees", "packages", "trusted", "recommended",
    "rated", "urgent", "asap", "24/7", "appointment", "quote",
    "compare", "vs", "alternative"
]

# Compile patterns for fast matching
JUNK_PATTERNS = [re.compile(rf'\b{re.escape(t)}\b', re.IGNORECASE) for t in JUNK_TOKENS]
PRODUCT_PATTERNS = [re.compile(rf'\b{re.escape(t)}\b', re.IGNORECASE) for t in PRODUCT_TOKENS]
PROCEDURE_PATTERNS = [re.compile(rf'\b{re.escape(t)}\b', re.IGNORECASE) for t in PROCEDURE_TOKENS]
UNIT_NOISE_PATTERNS = [re.compile(rf'\b{re.escape(t)}\b' if ' ' not in t else re.escape(t), re.IGNORECASE) for t in UNIT_NOISE_TOKENS]


class RejectAudit:
    """Tracks rejection reasons with examples for debug transparency"""
    def __init__(self):
        self.raw_count = 0
        self.kept_count = 0
        self.rejected_geo_mismatch = 0
        self.rejected_product_intent = 0
        self.rejected_procedure_intent = 0
        self.rejected_unit_noise = 0
        self.rejected_too_generic = 0
        self.rejected_missing_service_token = 0
        self.rejected_missing_modifier_or_geo = 0
        self.rejected_junk = 0
        self.rejected_length = 0
        # Top 3 examples per reason
        self._examples: Dict[str, List[str]] = {}

    def _add_example(self, reason: str, query: str):
        if reason not in self._examples:
            self._examples[reason] = []
        if len(self._examples[reason]) < 3:
            self._examples[reason].append(query)

    def to_dict(self) -> Dict:
        return {
            "raw_count": self.raw_count,
            "kept_count": self.kept_count,
            "rejected_geo_mismatch": self.rejected_geo_mismatch,
            "rejected_product_intent": self.rejected_product_intent,
            "rejected_procedure_intent": self.rejected_procedure_intent,
            "rejected_unit_noise": self.rejected_unit_noise,
            "rejected_too_generic": self.rejected_too_generic,
            "rejected_missing_service_token": self.rejected_missing_service_token,
            "rejected_missing_modifier_or_geo": self.rejected_missing_modifier_or_geo,
            "rejected_junk": self.rejected_junk,
            "rejected_length": self.rejected_length,
            "top_rejected_examples": self._examples
        }


def _normalize(query: str) -> str:
    """Normalize query for processing"""
    q = query.lower().strip()
    q = re.sub(r'[^\w\s\'-]', '', q)
    q = re.sub(r'\s+', ' ', q)
    return q


def _contains_any(text: str, terms: List[str]) -> bool:
    """Check if text contains any of the terms"""
    text_lower = text.lower()
    for t in terms:
        if t.lower() in text_lower:
            return True
    return False


def _matches_any_pattern(query: str, patterns: list) -> bool:
    """Check if query matches any compiled regex pattern"""
    for pattern in patterns:
        if pattern.search(query):
            return True
    return False


# ============== RULE FUNCTIONS ==============

def _has_geo_mismatch(query: str, brp: BRP) -> bool:
    """R1: Query contains a foreign geo reference"""
    if not brp.geo_block_terms:
        return False
    query_lower = query.lower()
    for geo in brp.geo_block_terms:
        if len(geo) <= 3:
            if re.search(rf'\b{re.escape(geo)}\b', query_lower):
                return True
        else:
            if geo in query_lower:
                return True
    return False


def _has_product_intent(query: str, brp: BRP) -> bool:
    """R2: Product shopping intent for non-ecommerce businesses"""
    if brp.business_model == "ecommerce" or brp.has_ecommerce_signals:
        return False
    if brp.business_model not in ("service_booking", "medical", "saas", "unknown"):
        return False
    if _matches_any_pattern(query, PRODUCT_PATTERNS):
        return True
    return _contains_any(query, brp.block_terms)


def _has_procedure_intent(query: str, brp: BRP) -> bool:
    """R3: Medical procedure intent for non-medical businesses"""
    if brp.business_model == "medical":
        return False
    if brp.business_model not in ("service_booking", "unknown"):
        return False
    return _matches_any_pattern(query, PROCEDURE_PATTERNS)


def _has_unit_noise(query: str) -> bool:
    """R4: Nonsense unit/commodity noise"""
    return _matches_any_pattern(query, UNIT_NOISE_PATTERNS)


def _is_junk(query: str) -> bool:
    """R5: Generic junk patterns"""
    return _matches_any_pattern(query, JUNK_PATTERNS)


def _is_too_generic(query: str, brp: BRP) -> bool:
    """R6: Too generic / non-actionable"""
    words = query.lower().split()
    generic_only = {
        "best", "top", "price", "near", "me", "now", "the", "a",
        "in", "for", "and", "or", "of", "how", "much", "what", "is"
    }
    meaningful = [w for w in words if w not in generic_only and len(w) > 2]
    if len(meaningful) == 0:
        return True
    if len(meaningful) == 1:
        word = meaningful[0]
        if not _contains_any(word, brp.service_terms) and not _contains_any(word, brp.category_terms):
            return True
    return False


def _has_service_token(query: str, brp: BRP) -> bool:
    """Check if query contains at least one service term from BRP"""
    return _contains_any(query, brp.service_terms) or _contains_any(query, brp.category_terms)


def _has_modifier_or_geo(query: str, brp: BRP) -> bool:
    """Check if query contains an intent modifier or geo token"""
    return _contains_any(query, INTENT_MODIFIERS) or _contains_any(query, brp.geo_terms)


# ============== MAIN FILTER ==============

def filter_queries(
    raw_queries: List[str],
    brp: BRP,
    min_results: int = 10
) -> Tuple[List[str], RejectAudit]:
    """
    Deterministic relevance filtering using BRP.

    Rules applied in order:
    1. Normalize + length check
    2. R5: Junk patterns (fast reject)
    3. R4: Unit/noise
    4. R1: Geo mismatch
    5. R2: Product intent (service_booking/medical unless ecom)
    6. R3: Procedure intent (non-medical)
    7. R6: Too generic
    8. R7: Service token + modifier/geo (service_booking)

    Progressive relaxation: if <min_results after strict pass,
    relax R7 to service_token-only (drop modifier requirement).

    Returns:
        Tuple of (kept_queries, audit)
    """
    audit = RejectAudit()
    audit.raw_count = len(raw_queries)

    is_service = brp.business_model in ("service_booking", "unknown")

    # Phase 1: Apply hard filters (R1-R6), collect R7 candidates
    kept_strict = []         # passes all rules including R7 strict
    kept_relaxed_pool = []   # passes R1-R6 + has service_token but no modifier/geo
    seen = set()

    for raw_q in raw_queries:
        q = _normalize(raw_q)
        if not q or q in seen:
            continue
        seen.add(q)

        words = q.split()

        # Length check (2-8 words)
        if len(words) < 2 or len(words) > 8:
            audit.rejected_length += 1
            audit._add_example("length", q)
            continue

        # R5: Junk
        if _is_junk(q):
            audit.rejected_junk += 1
            audit._add_example("junk", q)
            continue

        # R4: Unit/noise
        if _has_unit_noise(q):
            audit.rejected_unit_noise += 1
            audit._add_example("unit_noise", q)
            continue

        # R1: Geo mismatch
        if _has_geo_mismatch(q, brp):
            audit.rejected_geo_mismatch += 1
            audit._add_example("wrong_geo", q)
            continue

        # R2: Product intent
        if _has_product_intent(q, brp):
            audit.rejected_product_intent += 1
            audit._add_example("product_intent", q)
            continue

        # R3: Procedure intent
        if _has_procedure_intent(q, brp):
            audit.rejected_procedure_intent += 1
            audit._add_example("procedure_intent", q)
            continue

        # R6: Too generic
        if _is_too_generic(q, brp):
            audit.rejected_too_generic += 1
            audit._add_example("too_generic", q)
            continue

        # R7: Service token + modifier/geo (for service_booking)
        if is_service:
            has_svc = _has_service_token(q, brp)
            has_mod_geo = _has_modifier_or_geo(q, brp)

            if not has_svc:
                audit.rejected_missing_service_token += 1
                audit._add_example("missing_service_token", q)
                continue

            if has_mod_geo:
                kept_strict.append(q)
            else:
                # Has service token but no modifier/geo — candidate for relaxation
                kept_relaxed_pool.append(q)
        else:
            # Non service_booking: just need some relevance match
            has_brand = _contains_any(q, brp.brand_terms)
            has_svc = _has_service_token(q, brp)
            if has_brand or has_svc:
                kept_strict.append(q)
            else:
                audit.rejected_missing_service_token += 1
                audit._add_example("missing_service_token", q)

    # Phase 2: Relaxation — if strict results < min_results, pull from relaxed pool
    if len(kept_strict) < min_results and kept_relaxed_pool:
        needed = min_results - len(kept_strict)
        promoted = kept_relaxed_pool[:needed]
        kept_strict.extend(promoted)
        # Count the rest as rejected
        remaining = len(kept_relaxed_pool) - len(promoted)
        audit.rejected_missing_modifier_or_geo += remaining
        for q in kept_relaxed_pool[len(promoted):]:
            audit._add_example("missing_modifier_or_geo", q)
        logger.info(f"[RELEVANCE_GATE] Relaxation: promoted {len(promoted)} queries "
                    f"(service_token only, no modifier/geo)")
    else:
        # All relaxed pool queries are rejected
        audit.rejected_missing_modifier_or_geo += len(kept_relaxed_pool)
        for q in kept_relaxed_pool[:3]:
            audit._add_example("missing_modifier_or_geo", q)

    audit.kept_count = len(kept_strict)

    logger.info(
        f"[RELEVANCE_GATE] {audit.raw_count} -> {audit.kept_count} "
        f"(geo={audit.rejected_geo_mismatch}, product={audit.rejected_product_intent}, "
        f"procedure={audit.rejected_procedure_intent}, unit={audit.rejected_unit_noise}, "
        f"generic={audit.rejected_too_generic}, no_svc={audit.rejected_missing_service_token}, "
        f"no_mod={audit.rejected_missing_modifier_or_geo}, "
        f"junk={audit.rejected_junk}, length={audit.rejected_length})"
    )

    return kept_strict, audit
