"""
Novara Research Foundation: Customer Intel Post-Processor
Version 1.1 - Feb 2026

Validates segments against offer catalog + search phrases.
Removes generic filler. Deduplicates. Enforces list caps.
Relaxes constraints if too few segments survive strict pass.
"""

import logging
import re
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)

# Generic filler words that get stripped unless they appear in search phrases
GENERIC_FILLER = [
    "premium", "high-quality", "high quality", "best-in-class",
    "top-notch", "world-class", "state-of-the-art", "cutting-edge",
    "luxury", "exclusive", "elite", "superior"
]

# List caps per field
CAPS = {
    "summary_bullets": 3,
    "core_motives": 3,
    "top_pains": 3,
    "top_objections": 3,
    "best_proof": 3,
    "risk_reducers": 3,
    "best_offer_items": 3,
    "best_channel_focus": 2,
    "search_language": 6,
    "moment_triggers": 5,
    "urgency_triggers": 5,
    "planned_triggers": 5,
    "desire_phrases": 12,
    "anxiety_phrases": 12,
    "intent_phrases": 12,
}


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r'\s+', ' ', text.strip().lower())


def _substring_match(needle: str, haystack_set: Set[str]) -> bool:
    """Check if needle matches any item in haystack via case-insensitive substring."""
    needle_norm = _normalize(needle)
    for item in haystack_set:
        item_norm = _normalize(item)
        if needle_norm in item_norm or item_norm in needle_norm:
            return True
    return False


def validate_segment_constraints(
    segment: Dict[str, Any],
    offer_items_set: Set[str],
    search_phrases_set: Set[str],
    strict: bool = True
) -> Tuple[bool, str]:
    """
    Validate a segment against offer + search constraints.

    Strict mode:
    - Must reference >= 1 offer item
    - Must reference >= 2 search phrases (if search data available)

    Returns (passes, reason_if_failed)
    """
    # Check offer match
    best_offers = segment.get("best_offer_items", [])
    offer_matches = sum(1 for o in best_offers if _substring_match(o, offer_items_set))

    if strict and offer_items_set and offer_matches == 0:
        return False, "no_offer_match"

    # Check search phrase match (only if search data was available)
    if search_phrases_set:
        search_lang = segment.get("search_language", [])
        search_matches = sum(1 for s in search_lang if _substring_match(s, search_phrases_set))

        if strict and search_matches < 2:
            return False, f"weak_search_match ({search_matches}/2)"

    return True, ""


def remove_generic_filler(text: str, allowed_phrases: Set[str]) -> str:
    """Remove generic filler words unless they appear in search phrases."""
    result = text
    for filler in GENERIC_FILLER:
        if filler in _normalize(text) and not _substring_match(filler, allowed_phrases):
            # Remove the filler word (case-insensitive)
            result = re.sub(re.escape(filler), '', result, flags=re.IGNORECASE).strip()
            result = re.sub(r'\s+', ' ', result).strip()
            # Remove leading/trailing commas or dashes left behind
            result = re.sub(r'^[,\-\s]+|[,\-\s]+$', '', result).strip()
    return result


def clean_string_list(items: List[str], allowed_phrases: Set[str], max_len: int, char_cap: int = 90) -> Tuple[List[str], int]:
    """
    Clean a list of strings:
    1. Remove generic filler
    2. Deduplicate (case-insensitive)
    3. Truncate to char_cap
    4. Cap list length

    Returns (cleaned_list, filler_removed_count)
    """
    seen = set()
    cleaned = []
    filler_count = 0

    for item in items:
        if not item or not item.strip():
            continue

        # Remove filler
        cleaned_item = remove_generic_filler(item, allowed_phrases)
        if cleaned_item != item:
            filler_count += 1
        if not cleaned_item:
            continue

        # Truncate
        cleaned_item = cleaned_item[:char_cap]

        # Dedup
        norm = _normalize(cleaned_item)
        if norm in seen:
            continue
        seen.add(norm)

        cleaned.append(cleaned_item)

    return cleaned[:max_len], filler_count


def postprocess_customer_intel(
    raw: Dict[str, Any],
    offer_catalog: List[str],
    search_phrases: List[str],
    min_segments: int = 2
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Main post-processing pipeline for Customer Intel v1.1.

    1. Validate segment constraints (strict)
    2. Relax if too few segments
    3. Clean all string lists (filler removal, dedup, caps)
    4. Build audit

    Returns (processed_data, audit_dict)
    """
    offer_set = set(offer_catalog)
    search_set = set(search_phrases)

    total_filler = 0
    total_dedup = 0

    # ============== 1. VALIDATE SEGMENTS ==============
    raw_segments = raw.get("segments", [])[:3]
    segments_raw_count = len(raw_segments)
    kept_segments = []
    dropped_segments = []

    # Strict pass
    for seg in raw_segments:
        passes, reason = validate_segment_constraints(seg, offer_set, search_set, strict=True)
        if passes:
            kept_segments.append(seg)
        else:
            dropped_segments.append({"segment": seg.get("segment_name", "?"), "reason": reason})

    relaxation_applied = False

    # Relax if too few
    if len(kept_segments) < min_segments and segments_raw_count >= min_segments:
        logger.info(f"[CUSTOMER_INTEL-FILTER] Strict kept {len(kept_segments)}/{segments_raw_count}, relaxing...")
        kept_segments = []
        dropped_segments = []
        for seg in raw_segments:
            passes, reason = validate_segment_constraints(seg, offer_set, search_set, strict=False)
            if passes:
                kept_segments.append(seg)
            else:
                dropped_segments.append({"segment": seg.get("segment_name", "?"), "reason": reason})
        relaxation_applied = True

    # If still too few after relaxation, keep all
    if len(kept_segments) < min_segments and segments_raw_count > 0:
        kept_segments = raw_segments
        dropped_segments = [{"segment": "all", "reason": "relaxation_kept_all"}]
        relaxation_applied = True

    # ============== 2. CLEAN SEGMENTS ==============
    cleaned_segments = []
    offer_items_used = set()
    search_phrases_used = set()

    for seg in kept_segments:
        cleaned_seg = {}
        cleaned_seg["segment_name"] = seg.get("segment_name", "")[:48]
        cleaned_seg["jtbd"] = seg.get("jtbd", "")[:120]

        for field in ["core_motives", "top_pains", "top_objections", "best_proof", "risk_reducers"]:
            items, filler_ct = clean_string_list(
                seg.get(field, []), search_set, CAPS.get(field, 3)
            )
            cleaned_seg[field] = items
            total_filler += filler_ct

        # Offer items — keep as-is but cap
        cleaned_seg["best_offer_items"] = seg.get("best_offer_items", [])[:CAPS["best_offer_items"]]
        for o in cleaned_seg["best_offer_items"]:
            if _substring_match(o, offer_set):
                offer_items_used.add(o)

        # Channel focus
        cleaned_seg["best_channel_focus"] = seg.get("best_channel_focus", [])[:CAPS["best_channel_focus"]]

        # Search language — keep as-is but cap
        cleaned_seg["search_language"] = seg.get("search_language", [])[:CAPS["search_language"]]
        for s in cleaned_seg["search_language"]:
            if _substring_match(s, search_set):
                search_phrases_used.add(s)

        cleaned_segments.append(cleaned_seg)

    # ============== 3. CLEAN TRIGGER MAP ==============
    trigger_raw = raw.get("trigger_map", {})
    trigger_map = {}
    for field in ["moment_triggers", "urgency_triggers", "planned_triggers"]:
        items, filler_ct = clean_string_list(
            trigger_raw.get(field, []), search_set, CAPS.get(field, 5)
        )
        trigger_map[field] = items
        total_filler += filler_ct

    # ============== 4. CLEAN LANGUAGE BANK ==============
    lang_raw = raw.get("language_bank", {})
    language_bank = {}

    # Collect all phrases for cross-dedup
    all_lang_seen = set()

    for field in ["desire_phrases", "anxiety_phrases", "intent_phrases"]:
        items = lang_raw.get(field, [])
        cleaned = []
        filler_ct = 0
        for item in items:
            if not item or not item.strip():
                continue
            cleaned_item = remove_generic_filler(item, search_set)
            if cleaned_item != item:
                filler_ct += 1
            if not cleaned_item:
                continue
            cleaned_item = cleaned_item[:90]
            norm = _normalize(cleaned_item)
            if norm in all_lang_seen:
                total_dedup += 1
                continue
            all_lang_seen.add(norm)
            cleaned.append(cleaned_item)
        language_bank[field] = cleaned[:CAPS.get(field, 12)]
        total_filler += filler_ct

    # ============== 5. CLEAN SUMMARY ==============
    summary, filler_ct = clean_string_list(
        raw.get("summary_bullets", []), search_set, CAPS["summary_bullets"]
    )
    total_filler += filler_ct

    # ============== 6. BUILD RESULT ==============
    processed = {
        "summary_bullets": summary,
        "segments": cleaned_segments,
        "trigger_map": trigger_map,
        "language_bank": language_bank,
    }

    audit = {
        "offer_items_available": offer_catalog,
        "offer_items_used": list(offer_items_used),
        "search_phrases_available_count": len(search_phrases),
        "search_phrases_used": list(search_phrases_used)[:20],
        "segments_raw_count": segments_raw_count,
        "segments_dropped": dropped_segments,
        "relaxation_applied": relaxation_applied,
        "generic_filler_removed": total_filler,
        "duplicates_removed": total_dedup,
    }

    logger.info(
        f"[CUSTOMER_INTEL-FILTER] Result: {len(cleaned_segments)}/{segments_raw_count} segments, "
        f"filler removed: {total_filler}, dedup: {total_dedup}, "
        f"relaxation: {'yes' if relaxation_applied else 'no'}"
    )

    return processed, audit
