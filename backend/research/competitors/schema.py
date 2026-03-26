"""
Novara Research Foundation: Competitor Discovery Schema
Pydantic models for CompetitorSnapshot

Version 3.0 - Feb 2026
- Structured MarketOverview object
- Removed category_search_terms
- Added business_type and price_tier to inputs
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta


# ============== COMPETITOR MODEL ==============

class Competitor(BaseModel):
    """A discovered competitor"""
    name: str
    website: str
    instagram_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    tiktok_url: Optional[str] = None
    tiktok_handle: Optional[str] = None
    what_they_do: str = Field(default="", max_length=80)
    positioning: str = Field(default="", max_length=100)
    why_competitor: str = Field(default="", max_length=80)
    price_tier: str = Field(default="mid-range")
    estimated_size: str = Field(default="medium")
    overlap_score: str = Field(default="medium")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    ad_strategy_summary: Optional[str] = None
    social_presence: List[Dict[str, Any]] = Field(default_factory=list)


# ============== MARKET OVERVIEW MODEL ==============

class MarketOverview(BaseModel):
    """Structured market intelligence"""
    competitive_density: str = Field(default="moderate")  # low, moderate, high, saturated
    dominant_player_type: str = Field(default="", max_length=100)  # Who dominates
    market_insight: str = Field(default="", max_length=150)  # Non-obvious insight
    ad_landscape_note: str = Field(default="", max_length=150)  # Ad competition note


# ============== DELTA MODEL ==============

class CompetitorDelta(BaseModel):
    """Tracks changes between competitor snapshots"""
    previous_captured_at: Optional[datetime] = None
    new_competitors_count: int = 0
    removed_competitors_count: int = 0
    notable_changes: List[str] = Field(default_factory=list, max_length=5)


# ============== INPUTS USED MODEL ==============

class CompetitorInputs(BaseModel):
    """Inputs used for this snapshot"""
    geo: Dict[str, str] = Field(default_factory=dict)
    brand_name: str = ""
    domain: str = ""
    subcategory: str = ""
    niche: str = ""
    services: List[str] = Field(default_factory=list)
    brand_overview: str = ""
    price_range: Optional[Dict[str, Any]] = None
    # New fields
    business_type: str = "service_provider"  # platform or service_provider
    price_tier: str = "mid-range"  # budget, mid-range, premium, luxury


# ============== MAIN SNAPSHOT MODEL ==============

class CompetitorSnapshot(BaseModel):
    """Complete Competitor Discovery Snapshot"""
    version: str = "3.0"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    
    # Inputs tracking
    inputs_used: CompetitorInputs = Field(default_factory=CompetitorInputs)
    
    # Main outputs
    competitors: List[Competitor] = Field(default_factory=list, max_length=5)
    
    # Market overview (structured)
    market_overview: MarketOverview = Field(default_factory=MarketOverview)
    
    # Delta from previous
    delta: CompetitorDelta = Field(default_factory=CompetitorDelta)


# ============== RESEARCH PACK SOURCE WRAPPER ==============

class CompetitorSource(BaseModel):
    """Competitors as a source within research_packs"""
    latest: Optional[CompetitorSnapshot] = None
    history: List[CompetitorSnapshot] = Field(default_factory=list, max_length=10)


# ============== API RESPONSE MODELS ==============

class CompetitorRunResponse(BaseModel):
    """Response from POST /api/research/{campaignId}/competitors/run"""
    campaign_id: str
    status: str
    snapshot: CompetitorSnapshot
    message: str = ""


class CompetitorLatestResponse(BaseModel):
    """Response from GET /api/research/{campaignId}/competitors/latest"""
    campaign_id: str
    has_data: bool
    snapshot: Optional[CompetitorSnapshot] = None
    refresh_due_in_days: Optional[int] = None
