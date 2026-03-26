"""
Novara Research Foundation: Seasonality Post-Processor
Filters out generic/non-actionable buying moments.

Version 2.1 - Feb 2026
- Removes moments with generic "who" values
- Removes moments with non-specific buy_triggers
- Removes moments lacking time-bound "why_now"
- Relaxation fallback if filtering is too aggressive (< 3 moments)
"""

import logging
import re
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# ============== GENERIC PATTERNS ==============

# "who" values that are too vague to be useful
GENERIC_WHO_PATTERNS = [
    r"^(general\s+)?(consumers?|customers?|people|everyone|anyone|individuals?|users?|buyers?)$",
    r"^(broad|general|wide|mass)\s+(audience|public|market|demographic)$",
    r"^those\s+(who|interested|looking)",
    r"^all\s+(ages?|groups?|demographics?)",
]

# buy_triggers that are marketing-speak, not real events
GENERIC_TRIGGER_PATTERNS = [
    r"social\s*media\s*(posts?|content|exposure|campaigns?|marketing|trends?)?",
    r"influencer\s*(content|posts?|recommendations?|marketing)?",
    r"(targeted|digital|online)\s*(ads?|advertising|campaigns?|marketing)",
    r"(marketing|ad|promotional)\s*campaigns?",
    r"brand\s*(awareness|visibility|exposure)",
    r"^(content\s*)?marketing$",
    r"email\s*(marketing|campaigns?|blasts?)",
]

# Moment names that are too generic (year-round / not time-bound)
GENERIC_MOMENT_PATTERNS = [
    r"^(social\s*media\s*(trends?|moments?|marketing)?)$",
    r"^(year[-\s]?round|ongoing|always[-\s]?on|evergreen)\s*(demand|sales?|buying)?$",
    r"^(general|regular|daily|routine)\s*(demand|buying|purchases?|maintenance)$",
]

# best_channels that are too vague
GENERIC_CHANNEL_PATTERNS = [
    r"^social\s*media$",
    r"^online$",
    r"^internet$",
    r"^digital$",
    r"^(the\s+)?web$",
]


def _matches_any(text: str, patterns: List[str]) -> bool:
    """Check if text matches any of the regex patterns (case-insensitive)."""
    text_lower = text.strip().lower()
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def filter_moments(
    moments: List[Dict[str, Any]],
    strict: bool = True
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Filter buying moments, removing generic/non-actionable ones.

    Args:
        moments: List of raw moment dicts from Perplexity
        strict: If True, apply all filters. If False, only remove the worst offenders.

    Returns:
        Tuple of (filtered_moments, rejection_reasons_counts)
    """
    kept = []
    reasons: Dict[str, int] = {}

    for moment in moments:
        rejection = _check_moment(moment, strict)
        if rejection:
            reasons[rejection] = reasons.get(rejection, 0) + 1
            logger.debug(f"[SEASONALITY-FILTER] Rejected '{moment.get('moment', '?')}': {rejection}")
        else:
            kept.append(moment)

    return kept, reasons


def _check_moment(moment: Dict[str, Any], strict: bool) -> str:
    """
    Check a single moment for generic/non-actionable content.
    Returns rejection reason string, or empty string if the moment passes.
    """
    name = moment.get("moment", "")
    who = moment.get("who", "")
    why_now = moment.get("why_now", "")
    buy_triggers = moment.get("buy_triggers", [])
    best_channels = moment.get("best_channels", [])

    # 1. Generic moment name
    if _matches_any(name, GENERIC_MOMENT_PATTERNS):
        return "generic_moment_name"

    # 2. Empty or missing critical fields
    if not name.strip():
        return "missing_moment_name"

    # 3. Generic "who" — always reject, even in relaxed mode
    if _matches_any(who, GENERIC_WHO_PATTERNS):
        return "generic_who"

    if strict:
        # 4. No buy_triggers or all generic
        if not buy_triggers:
            return "missing_buy_triggers"

        generic_trigger_count = sum(
            1 for t in buy_triggers if _matches_any(t, GENERIC_TRIGGER_PATTERNS)
        )
        if generic_trigger_count == len(buy_triggers):
            return "all_generic_triggers"

        # 5. Generic channels (all of them)
        if best_channels:
            generic_channel_count = sum(
                1 for c in best_channels if _matches_any(c, GENERIC_CHANNEL_PATTERNS)
            )
            if generic_channel_count == len(best_channels):
                return "all_generic_channels"

        # 6. Missing why_now or too short
        if len(why_now.strip()) < 10:
            return "weak_why_now"

    return ""


def clean_buy_triggers(triggers: List[str]) -> List[str]:
    """Remove generic triggers from a list, keeping only specific ones."""
    return [
        t for t in triggers
        if not _matches_any(t, GENERIC_TRIGGER_PATTERNS)
    ]


def clean_best_channels(channels: List[str]) -> List[str]:
    """Remove generic channels from a list, keeping only specific ones."""
    return [
        c for c in channels
        if not _matches_any(c, GENERIC_CHANNEL_PATTERNS)
    ]


def postprocess_moments(
    raw_moments: List[Dict[str, Any]],
    min_moments: int = 3
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Main post-processing pipeline for buying moments.

    1. Apply strict filtering
    2. If too few results, relax and retry
    3. Clean individual fields (remove generic triggers/channels from kept moments)

    Returns:
        Tuple of (processed_moments, audit_dict)
    """
    raw_count = len(raw_moments)

    # First pass: strict filtering
    kept, reasons = filter_moments(raw_moments, strict=True)

    relaxation_applied = False

    # Relaxation: if strict filtering is too aggressive, relax
    if len(kept) < min_moments and len(raw_moments) >= min_moments:
        logger.info(f"[SEASONALITY-FILTER] Strict pass kept {len(kept)}/{raw_count}, relaxing...")
        kept, reasons = filter_moments(raw_moments, strict=False)
        relaxation_applied = True

    # Clean individual fields in kept moments
    cleaned = []
    for m in kept:
        cleaned_moment = dict(m)
        # Remove generic triggers but keep at least the originals if all would be removed
        clean_triggers = clean_buy_triggers(m.get("buy_triggers", []))
        if clean_triggers:
            cleaned_moment["buy_triggers"] = clean_triggers

        clean_channels = clean_best_channels(m.get("best_channels", []))
        if clean_channels:
            cleaned_moment["best_channels"] = clean_channels

        cleaned.append(cleaned_moment)

    audit = {
        "raw_moments_count": raw_count,
        "filtered_count": raw_count - len(cleaned),
        "filter_reasons": reasons,
        "relaxation_applied": relaxation_applied
    }

    logger.info(
        f"[SEASONALITY-FILTER] Result: {len(cleaned)}/{raw_count} kept, "
        f"relaxation={'yes' if relaxation_applied else 'no'}"
    )

    return cleaned, audit
