"""
Novara Research Foundation: Search Intent Schema v2
Pydantic models for SearchIntentSnapshot

Version 2.0 - Feb 2026
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
from enum import Enum


# ============== ENUMS ==============

class IntentBucket(str, Enum):
    """Intent bucket categories (behavioral, not funnel stages)"""
    PRICE = "price"
    TRUST = "trust"
    URGENCY = "urgency"
    COMPARISON = "comparison"
    GENERAL = "general"


# ============== BRP SNAPSHOT ==============

class BRPSnapshot(BaseModel):
    """Stored snapshot of the Business Relevance Profile used for this run"""
    brand_name: str = ""
    domain: str = ""
    geo_city: Optional[str] = None
    geo_country: Optional[str] = None
    business_model: str = "unknown"
    brand_terms: List[str] = Field(default_factory=list)
    service_terms: List[str] = Field(default_factory=list)
    category_terms: List[str] = Field(default_factory=list)
    geo_terms: List[str] = Field(default_factory=list)
    block_terms_count: int = 0
    geo_block_terms_count: int = 0
    has_ecommerce_signals: bool = False


# ============== REJECTION AUDIT ==============

class RelevanceGateAudit(BaseModel):
    """Detailed rejection breakdown from the relevance gate (v2.1)"""
    raw_count: int = 0
    kept_count: int = 0
    rejected_geo_mismatch: int = 0
    rejected_product_intent: int = 0
    rejected_procedure_intent: int = 0
    rejected_unit_noise: int = 0
    rejected_too_generic: int = 0
    rejected_missing_service_token: int = 0
    rejected_missing_modifier_or_geo: int = 0
    rejected_junk: int = 0
    rejected_length: int = 0
    top_rejected_examples: Dict[str, List[str]] = Field(default_factory=dict)


# ============== STATS MODEL ==============

class LLMCleaningAudit(BaseModel):
    """LLM cleaning audit stats — saved per snapshot"""
    input_count: int = 0
    output_count: int = 0
    removed_count: int = 0
    merged_count: int = 0
    moved_count: int = 0
    added_count: int = 0  # Should ALWAYS be 0
    invalid_queries_dropped: List[str] = Field(default_factory=list)
    validation_passed: bool = True


class SearchIntentStats(BaseModel):
    """Pipeline stats for debugging and transparency"""
    seeds_used: int = 0
    seed_list: List[str] = Field(default_factory=list)
    suggestions_raw: int = 0
    filtered_blocklist: int = 0
    relevance_gate: Optional[RelevanceGateAudit] = None
    filtered_irrelevant: int = 0
    kept_final: int = 0
    llm_cleaning: Optional[LLMCleaningAudit] = None


# ============== DELTA MODEL ==============

class SearchIntentDelta(BaseModel):
    """Tracks changes between snapshots"""
    previous_captured_at: Optional[datetime] = None
    new_queries_count: int = 0
    removed_queries_count: int = 0
    notable_new_queries: List[str] = Field(default_factory=list, max_length=5)


# ============== FORUM QUERIES MODEL ==============

class ForumQueries(BaseModel):
    """Forum search queries by platform"""
    reddit: List[str] = Field(default_factory=list, max_length=15)
    quora: List[str] = Field(default_factory=list, max_length=15)


# ============== INPUTS USED MODEL ==============

class SearchIntentInputs(BaseModel):
    """Inputs used for this snapshot (for reproducibility)"""
    geo: Dict[str, str] = Field(default_factory=dict)  # city, country, language
    seeds: List[str] = Field(default_factory=list)
    service_terms: List[str] = Field(default_factory=list)
    category_terms: List[str] = Field(default_factory=list)
    competitor_terms: List[str] = Field(default_factory=list)
    sells_workshops: bool = False


# ============== MAIN SNAPSHOT MODEL ==============

class SearchIntentSnapshot(BaseModel):
    """Complete Search Intent Snapshot v2"""
    version: str = "2.0"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=14))
    
    # BRP used for this run
    brp: Optional[BRPSnapshot] = None
    
    # Pipeline stats
    stats: SearchIntentStats = Field(default_factory=SearchIntentStats)
    
    # Inputs tracking
    inputs_used: SearchIntentInputs = Field(default_factory=SearchIntentInputs)
    
    # Main outputs
    top_10_queries: List[str] = Field(default_factory=list, max_length=10)
    
    intent_buckets: Dict[str, List[str]] = Field(default_factory=lambda: {
        "price": [],
        "trust": [],
        "urgency": [],
        "comparison": [],
        "general": []
    })
    
    # Derived outputs
    ad_keyword_queries: List[str] = Field(default_factory=list, max_length=40)
    forum_queries: ForumQueries = Field(default_factory=ForumQueries)
    
    # Delta from previous
    delta: SearchIntentDelta = Field(default_factory=SearchIntentDelta)


# ============== RESEARCH PACK SOURCE WRAPPER ==============

class SearchIntentSource(BaseModel):
    """Search Intent as a source within research_packs"""
    latest: Optional[SearchIntentSnapshot] = None
    history: List[SearchIntentSnapshot] = Field(default_factory=list, max_length=10)


# ============== API RESPONSE MODELS ==============

class SearchIntentRunResponse(BaseModel):
    """Response from POST /api/research/{campaignId}/search-intent/run"""
    campaign_id: str
    status: str  # "success", "partial", "failed"
    snapshot: SearchIntentSnapshot
    message: str = ""


class SearchIntentLatestResponse(BaseModel):
    """Response from GET /api/research/{campaignId}/search-intent/latest"""
    campaign_id: str
    has_data: bool
    snapshot: Optional[SearchIntentSnapshot] = None
    refresh_due_in_days: Optional[int] = None
