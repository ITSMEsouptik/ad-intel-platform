"""
Novara Research Foundation: LLM Cleaner v3.0
Gemini Flash for cleaning search queries - NOT generating

Version 3.0 - Feb 2026
- Strict validation: output must trace to input
- Comprehensive logging: before/after counts
- LLM is a CLEANER, not a generator
- Allowed ops: remove, merge, shorten, typo-fix, re-bucket
"""

import os
import json
import logging
import httpx
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Toggle for LLM cleanup
ENABLE_LLM_CLEANUP = True

# Gemini API config
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Fuzzy match threshold (0.0 to 1.0)
# 0.7 allows for typo fixes and minor rewrites
FUZZY_MATCH_THRESHOLD = 0.7


@dataclass
class CleaningStats:
    """Statistics for LLM cleaning operation"""
    # Input counts
    input_top10_count: int = 0
    input_ad_keywords_count: int = 0
    input_bucket_counts: Dict[str, int] = None
    input_total_unique: int = 0
    
    # Output counts
    output_top10_count: int = 0
    output_ad_keywords_count: int = 0
    output_bucket_counts: Dict[str, int] = None
    output_total_unique: int = 0
    
    # Operation counts
    removed_count: int = 0
    merged_count: int = 0  # Estimated from count reduction
    moved_count: int = 0   # Bucket changes
    added_count: int = 0   # Should ALWAYS be 0
    
    # Validation
    invalid_queries_dropped: List[str] = None
    validation_passed: bool = True
    
    def __post_init__(self):
        if self.input_bucket_counts is None:
            self.input_bucket_counts = {}
        if self.output_bucket_counts is None:
            self.output_bucket_counts = {}
        if self.invalid_queries_dropped is None:
            self.invalid_queries_dropped = []
    
    def to_dict(self) -> Dict:
        return {
            "input": {
                "top10": self.input_top10_count,
                "ad_keywords": self.input_ad_keywords_count,
                "buckets": self.input_bucket_counts,
                "total_unique": self.input_total_unique
            },
            "output": {
                "top10": self.output_top10_count,
                "ad_keywords": self.output_ad_keywords_count,
                "buckets": self.output_bucket_counts,
                "total_unique": self.output_total_unique
            },
            "operations": {
                "removed": self.removed_count,
                "merged": self.merged_count,
                "moved": self.moved_count,
                "added": self.added_count
            },
            "validation": {
                "passed": self.validation_passed,
                "invalid_dropped": self.invalid_queries_dropped
            }
        }


def normalize_query(query: str) -> str:
    """Normalize query for comparison"""
    return query.lower().strip()


def fuzzy_match(query: str, candidates: Set[str], threshold: float = FUZZY_MATCH_THRESHOLD) -> Optional[str]:
    """
    Find best fuzzy match for query in candidates.
    Returns matched candidate if above threshold, else None.
    """
    query_norm = normalize_query(query)
    best_match = None
    best_ratio = 0.0
    
    for candidate in candidates:
        candidate_norm = normalize_query(candidate)
        
        # Exact match
        if query_norm == candidate_norm:
            return candidate
        
        # Fuzzy match
        ratio = SequenceMatcher(None, query_norm, candidate_norm).ratio()
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = candidate
    
    return best_match


def build_input_fingerprint(
    top_10_queries: List[str],
    ad_keyword_queries: List[str],
    intent_buckets: Dict[str, List[str]]
) -> Set[str]:
    """
    Build a set of all unique queries from input.
    This is our "source of truth" - output must trace back to this.
    """
    all_queries = set()
    
    # Add top 10
    for q in top_10_queries:
        all_queries.add(normalize_query(q))
    
    # Add ad keywords
    for q in ad_keyword_queries:
        all_queries.add(normalize_query(q))
    
    # Add all bucket queries
    for bucket_queries in intent_buckets.values():
        for q in bucket_queries:
            all_queries.add(normalize_query(q))
    
    return all_queries


def validate_output_queries(
    output_queries: List[str],
    input_fingerprint: Set[str],
    context: str = ""
) -> Tuple[List[str], List[str]]:
    """
    Validate that all output queries trace back to input.
    
    Returns:
        Tuple of (valid_queries, invalid_queries)
    """
    valid = []
    invalid = []
    
    for query in output_queries:
        query_norm = normalize_query(query)
        
        # Check exact match
        if query_norm in input_fingerprint:
            valid.append(query)
            continue
        
        # Check fuzzy match (allows for typo fixes, minor rewrites)
        match = fuzzy_match(query, input_fingerprint)
        if match:
            valid.append(query)  # Keep the cleaned version
            continue
        
        # No match found - this is an LLM hallucination
        invalid.append(query)
        logger.warning(f"[LLM_CLEANER] {context} - Dropped invalid query (not in input): '{query}'")
    
    return valid, invalid


def count_bucket_moves(
    input_buckets: Dict[str, List[str]],
    output_buckets: Dict[str, List[str]]
) -> int:
    """
    Estimate how many queries were moved between buckets.
    """
    # Build query -> bucket mapping for input
    input_mapping = {}
    for bucket, queries in input_buckets.items():
        for q in queries:
            input_mapping[normalize_query(q)] = bucket
    
    # Count queries in different buckets in output
    moved = 0
    for bucket, queries in output_buckets.items():
        for q in queries:
            q_norm = normalize_query(q)
            # Check if this query existed in input but in different bucket
            if q_norm in input_mapping and input_mapping[q_norm] != bucket:
                moved += 1
            # Also check fuzzy matches
            elif q_norm not in input_mapping:
                match = fuzzy_match(q, set(input_mapping.keys()))
                if match and input_mapping.get(match) != bucket:
                    moved += 1
    
    return moved


async def clean_with_llm(
    top_10_queries: List[str],
    ad_keyword_queries: List[str],
    intent_buckets: Dict[str, List[str]],
    business_context: Dict[str, str]
) -> Tuple[Optional[Dict[str, Any]], CleaningStats]:
    """
    Use Gemini Flash to CLEAN query outputs.
    
    ALLOWED OPERATIONS:
    - Remove: Drop low-quality or duplicate queries
    - Merge: Combine semantic duplicates (keep better phrasing)
    - Shorten: Make queries more concise
    - Typo-fix: Correct spelling errors
    - Re-bucket: Move queries to correct intent bucket
    
    NOT ALLOWED:
    - Add new queries
    - Significantly rewrite queries
    - Generate or hallucinate queries
    
    Returns:
        Tuple of (cleaned_output, stats)
    """
    stats = CleaningStats()
    
    # ============== BUILD INPUT FINGERPRINT ==============
    input_fingerprint = build_input_fingerprint(top_10_queries, ad_keyword_queries, intent_buckets)
    
    # Record input counts
    stats.input_top10_count = len(top_10_queries)
    stats.input_ad_keywords_count = len(ad_keyword_queries)
    stats.input_bucket_counts = {k: len(v) for k, v in intent_buckets.items()}
    stats.input_total_unique = len(input_fingerprint)
    
    logger.info(f"[LLM_CLEANER] Input: top10={stats.input_top10_count}, "
                f"ad_keywords={stats.input_ad_keywords_count}, "
                f"total_unique={stats.input_total_unique}")
    
    if not ENABLE_LLM_CLEANUP:
        logger.info("[LLM_CLEANER] LLM cleanup disabled, returning original")
        return None, stats
    
    api_key = os.environ.get("GOOGLE_AI_STUDIO_KEY")
    if not api_key:
        logger.warning("[LLM_CLEANER] GOOGLE_AI_STUDIO_KEY not found, skipping")
        return None, stats
    
    # ============== BUILD PROMPT ==============
    brand_name = business_context.get("brand_name", "the brand")
    niche = business_context.get("niche", "their niche")
    city = business_context.get("city", "their location")
    
    input_data = {
        "top_10_candidates": top_10_queries[:15],
        "ad_keywords": ad_keyword_queries[:30],
        "intent_buckets": {k: v[:15] for k, v in intent_buckets.items()}
    }
    
    prompt = f"""You are a search query DATA CLEANER for {brand_name} - a {niche} business in {city}.

Your job is to CLEAN these search queries. You are NOT generating new queries.

## WHY THIS MATTERS
These cleaned queries will be used to:
- **Build Google Ads keyword groups** for the client's paid search campaigns
- **Inform ad copywriting** — real search language gets embedded into headlines and descriptions
- **Map buyer intent** — correctly bucketed queries reveal what stage of the buying journey people are in

Raw Google Suggest data contains duplicates, typos, and mis-bucketed queries that reduce targeting precision and waste ad spend. Your job is to clean without inventing.

INPUT QUERIES:
{json.dumps(input_data, indent=2)}

ALLOWED OPERATIONS:
1. REMOVE - Drop duplicates, irrelevant, or low-quality queries
2. MERGE - Combine semantic duplicates, keep better phrasing
   Example: "makeup artist dubai" and "dubai makeup artist" → keep one
3. SHORTEN - Make queries more concise (same meaning)
4. TYPO-FIX - Correct spelling: "makup" → "makeup", "saloon" → "salon"
5. RE-BUCKET - Move queries to correct intent bucket:
   - price: cost, pricing, rates, fees, "how much"
   - trust: reviews, best, top, recommended, ratings
   - urgency: same day, urgent, today, now, emergency
   - comparison: vs, alternative, compare
   - general: everything else

STRICT RULES:
- You can ONLY output queries that exist in the input (or cleaned versions of them)
- You CANNOT add new queries that weren't in the input
- Output count must be EQUAL or LESS than input count
- Every output query must be traceable to an input query

OUTPUT (JSON only, no explanation):
{{
  "top_10_queries": ["10 best queries from input"],
  "ad_keyword_queries": ["max 25, 2-7 words each"],
  "intent_buckets": {{
    "price": [],
    "trust": [],
    "urgency": [],
    "comparison": [],
    "general": []
  }}
}}"""

    # ============== CALL LLM ==============
    try:
        url = f"{GEMINI_API_URL}?key={api_key}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 2000
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"[LLM_CLEANER] Gemini API error: {response.status_code}")
                return None, stats
            
            result = response.json()
            response_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        
        # Extract JSON
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning("[LLM_CLEANER] No JSON found in response")
            return None, stats
        
        llm_output = json.loads(response_text[json_start:json_end])
        
    except json.JSONDecodeError as e:
        logger.error(f"[LLM_CLEANER] JSON parse error: {e}")
        return None, stats
    except httpx.TimeoutException:
        logger.error("[LLM_CLEANER] Gemini API timeout")
        return None, stats
    except Exception as e:
        logger.error(f"[LLM_CLEANER] LLM call failed: {e}")
        return None, stats
    
    # ============== VALIDATE OUTPUT ==============
    all_invalid = []
    
    # Validate top_10
    raw_top10 = llm_output.get("top_10_queries", [])
    valid_top10, invalid_top10 = validate_output_queries(raw_top10, input_fingerprint, "top_10")
    all_invalid.extend(invalid_top10)
    
    # Validate ad_keywords
    raw_ad_keywords = llm_output.get("ad_keyword_queries", [])
    valid_ad_keywords, invalid_ad_keywords = validate_output_queries(raw_ad_keywords, input_fingerprint, "ad_keywords")
    all_invalid.extend(invalid_ad_keywords)
    
    # Validate buckets
    raw_buckets = llm_output.get("intent_buckets", {})
    valid_buckets = {}
    for bucket in ["price", "trust", "urgency", "comparison", "general"]:
        bucket_queries = raw_buckets.get(bucket, [])
        valid_bucket, invalid_bucket = validate_output_queries(bucket_queries, input_fingerprint, f"bucket_{bucket}")
        valid_buckets[bucket] = valid_bucket[:15]  # Cap
        all_invalid.extend(invalid_bucket)
    
    # ============== BUILD VALIDATED OUTPUT ==============
    cleaned_output = {
        "top_10_queries": valid_top10[:10],
        "ad_keyword_queries": valid_ad_keywords[:25],
        "intent_buckets": valid_buckets
    }
    
    # ============== COMPUTE STATS ==============
    # Output counts
    output_fingerprint = build_input_fingerprint(
        cleaned_output["top_10_queries"],
        cleaned_output["ad_keyword_queries"],
        cleaned_output["intent_buckets"]
    )
    
    stats.output_top10_count = len(cleaned_output["top_10_queries"])
    stats.output_ad_keywords_count = len(cleaned_output["ad_keyword_queries"])
    stats.output_bucket_counts = {k: len(v) for k, v in cleaned_output["intent_buckets"].items()}
    stats.output_total_unique = len(output_fingerprint)
    
    # Operation counts
    stats.removed_count = stats.input_total_unique - stats.output_total_unique
    stats.merged_count = max(0, stats.removed_count)  # Merges appear as removals
    stats.moved_count = count_bucket_moves(intent_buckets, cleaned_output["intent_buckets"])
    stats.added_count = len(all_invalid)  # These were attempted additions
    stats.invalid_queries_dropped = all_invalid
    stats.validation_passed = len(all_invalid) == 0
    
    # ============== LOG RESULTS ==============
    logger.info(f"[LLM_CLEANER] Output: top10={stats.output_top10_count}, "
                f"ad_keywords={stats.output_ad_keywords_count}, "
                f"total_unique={stats.output_total_unique}")
    
    logger.info(f"[LLM_CLEANER] Operations: removed={stats.removed_count}, "
                f"merged≈{stats.merged_count}, moved={stats.moved_count}, "
                f"added(invalid)={stats.added_count}")
    
    if not stats.validation_passed:
        logger.warning(f"[LLM_CLEANER] Validation failed! Dropped {len(all_invalid)} invalid queries: {all_invalid[:5]}")
    else:
        logger.info("[LLM_CLEANER] Validation passed - all outputs trace to inputs")
    
    return cleaned_output, stats


def apply_llm_cleaning(
    original_top_10: List[str],
    original_ad_keywords: List[str],
    original_buckets: Dict[str, List[str]],
    cleaned: Optional[Dict[str, Any]],
    stats: CleaningStats
) -> Tuple[List[str], List[str], Dict[str, List[str]]]:
    """
    Apply LLM cleaning results, falling back to original if cleaning failed.
    
    Returns:
        Tuple of (top_10, ad_keywords, buckets)
    """
    if not cleaned:
        logger.info("[LLM_CLEANER] No cleaning applied, using original")
        return original_top_10, original_ad_keywords, original_buckets
    
    # Use cleaned output
    top_10 = cleaned.get("top_10_queries", original_top_10)[:10]
    ad_keywords = cleaned.get("ad_keyword_queries", original_ad_keywords)[:25]
    buckets = cleaned.get("intent_buckets", original_buckets)
    
    # Ensure buckets has all keys
    for bucket in ["price", "trust", "urgency", "comparison", "general"]:
        if bucket not in buckets:
            buckets[bucket] = original_buckets.get(bucket, [])
    
    return top_10, ad_keywords, buckets


# ============== LEGACY API COMPATIBILITY ==============
# These maintain backward compatibility with existing service.py

async def curate_with_llm(
    top_10_queries: List[str],
    ad_keyword_queries: List[str],
    intent_buckets: Dict[str, List[str]],
    business_context: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    """
    Legacy wrapper for clean_with_llm.
    Returns only the cleaned output (stats logged internally).
    """
    cleaned, stats = await clean_with_llm(
        top_10_queries=top_10_queries,
        ad_keyword_queries=ad_keyword_queries,
        intent_buckets=intent_buckets,
        business_context=business_context
    )
    return cleaned


def apply_llm_curation(
    original_top_10: List[str],
    original_ad_keywords: List[str],
    original_buckets: Dict[str, List[str]],
    curated: Optional[Dict[str, Any]]
) -> Tuple[List[str], List[str], Dict[str, List[str]]]:
    """
    Legacy wrapper for apply_llm_cleaning.
    """
    # Create dummy stats for legacy compatibility
    stats = CleaningStats()
    return apply_llm_cleaning(
        original_top_10=original_top_10,
        original_ad_keywords=original_ad_keywords,
        original_buckets=original_buckets,
        cleaned=curated,
        stats=stats
    )
