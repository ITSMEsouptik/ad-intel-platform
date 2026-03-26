"""
Novara Research Foundation: Search Intent Module v2

BRP-based pipeline: Seeds -> Suggest -> Filter -> Score -> Bucket -> Rank -> Cleanup
"""

from .schema import (
    SearchIntentSnapshot,
    SearchIntentDelta,
    SearchIntentInputs,
    SearchIntentStats,
    LLMCleaningAudit,
    RelevanceGateAudit,
    BRPSnapshot,
    ForumQueries,
    SearchIntentSource,
    SearchIntentRunResponse,
    SearchIntentLatestResponse
)

from .service import SearchIntentService

from .brp import build_brp, BRP

from .relevance_gate import filter_queries, RejectAudit

from .google_suggest import GoogleSuggestClient

from .seeds import (
    generate_seeds,
    generate_base_seeds,
    expand_seeds_with_patterns,
    extract_seed_inputs,
    build_keyword_sets,
    SeedGenerationInputs,
    KeywordSets
)

from .cleaning import clean_suggestions, get_blocklist_tokens

from .relevance import filter_by_relevance, check_relevance

from .bucketing import bucket_queries_with_scores, classify_query

from .ranking import (
    score_queries,
    rank_and_cap,
    dedupe_by_similarity,
    select_top_10,
    generate_ad_keyword_queries,
    generate_forum_queries
)

from .llm_cleanup import clean_with_llm, apply_llm_cleaning

__all__ = [
    # Schema
    "SearchIntentSnapshot",
    "SearchIntentDelta",
    "SearchIntentInputs",
    "SearchIntentStats",
    "LLMCleaningAudit",
    "RelevanceGateAudit",
    "BRPSnapshot",
    "ForumQueries",
    "SearchIntentSource",
    "SearchIntentRunResponse",
    "SearchIntentLatestResponse",
    
    # Service
    "SearchIntentService",
    
    # BRP
    "build_brp",
    "BRP",
    "filter_queries",
    
    # Client
    "GoogleSuggestClient",
    
    # Seeds
    "generate_seeds",
    "extract_seed_inputs",
    "build_keyword_sets",
    "SeedGenerationInputs",
    "KeywordSets",
    
    # Cleaning
    "clean_suggestions",
    "get_blocklist_tokens",
    
    # Relevance (legacy)
    "filter_by_relevance",
    "check_relevance",
    
    # Bucketing
    "bucket_queries_with_scores",
    "classify_query",
    
    # Ranking
    "score_queries",
    "rank_and_cap",
    "dedupe_by_similarity",
    "select_top_10",
    "generate_ad_keyword_queries",
    "generate_forum_queries",
    
    # LLM Cleanup
    "clean_with_llm",
    "apply_llm_cleaning"
]
