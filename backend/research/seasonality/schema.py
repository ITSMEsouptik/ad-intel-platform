"""
Novara Research Foundation: Seasonality Schema
Pydantic models for SeasonalitySnapshot

Version 2.1 - Feb 2026
- "Buying Moments" model: who/why_now/buy_triggers/must_answer/best_channels
- Replaced generic KeyMoment with BuyingMoment
- Added audit fields for post-processing stats
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta


# ============== BUYING MOMENT MODEL ==============

class BuyingMoment(BaseModel):
    """A specific buying moment — who buys, why, when, and how to reach them"""
    moment: str  # e.g., "Wedding Season", "Ramadan Prep"
    window: str  # e.g., "March-May", "First 2 weeks of September"
    demand: str = "medium"  # high, medium, moderate
    who: str = ""  # Who is buying? e.g., "Brides-to-be, mothers of the bride"
    why_now: str = ""  # Why this window specifically? Under 120 chars
    buy_triggers: List[str] = Field(default_factory=list, max_length=5)  # Specific real-world triggers
    must_answer: str = ""  # The key question the buyer needs answered before purchasing
    best_channels: List[str] = Field(default_factory=list, max_length=4)  # Where to reach them
    lead_time: str = ""  # How far ahead people start searching/booking, e.g., "2-4 weeks before"


# ============== WEEKLY PATTERNS MODEL ==============

class WeeklyPatterns(BaseModel):
    """Weekly demand patterns"""
    peak_days: List[str] = Field(default_factory=list)
    why: str = ""


# ============== DELTA MODEL ==============

class SeasonalityDelta(BaseModel):
    """Tracks changes between seasonality snapshots"""
    previous_captured_at: Optional[datetime] = None
    new_moments_count: int = 0
    removed_moments_count: int = 0
    notable_changes: List[str] = Field(default_factory=list, max_length=5)


# ============== INPUTS USED MODEL ==============

class SeasonalityInputs(BaseModel):
    """Inputs used for this snapshot"""
    geo: Dict[str, str] = Field(default_factory=dict)
    brand_name: str = ""
    domain: str = ""
    niche: str = ""
    subcategory: str = ""
    services: List[str] = Field(default_factory=list)
    brand_overview: str = ""
    price_range: Optional[Dict[str, Any]] = None


# ============== AUDIT MODEL ==============

class SeasonalityAudit(BaseModel):
    """Tracks post-processing stats"""
    raw_moments_count: int = 0
    filtered_count: int = 0
    filter_reasons: Dict[str, int] = Field(default_factory=dict)
    relaxation_applied: bool = False


# ============== MAIN SNAPSHOT MODEL ==============

class SeasonalitySnapshot(BaseModel):
    """Complete Seasonality Snapshot v2.1 — Buying Moments"""
    version: str = "2.1"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))

    # Inputs tracking
    inputs_used: SeasonalityInputs = Field(default_factory=SeasonalityInputs)

    # Main outputs — buying moments
    key_moments: List[BuyingMoment] = Field(default_factory=list, max_length=10)

    # Additional patterns
    evergreen_demand: List[str] = Field(default_factory=list, max_length=10)
    weekly_patterns: WeeklyPatterns = Field(default_factory=WeeklyPatterns)

    # Context
    local_insights: List[str] = Field(default_factory=list, max_length=5)

    # Delta from previous
    delta: SeasonalityDelta = Field(default_factory=SeasonalityDelta)

    # Audit
    audit: SeasonalityAudit = Field(default_factory=SeasonalityAudit)


# ============== RESEARCH PACK SOURCE WRAPPER ==============

class SeasonalitySource(BaseModel):
    """Seasonality as a source within research_packs"""
    latest: Optional[SeasonalitySnapshot] = None
    history: List[SeasonalitySnapshot] = Field(default_factory=list, max_length=10)


# ============== API RESPONSE MODELS ==============

class SeasonalityRunResponse(BaseModel):
    """Response from POST /api/research/{campaignId}/seasonality/run"""
    campaign_id: str
    status: str
    snapshot: SeasonalitySnapshot
    message: str = ""


class SeasonalityLatestResponse(BaseModel):
    """Response from GET /api/research/{campaignId}/seasonality/latest"""
    campaign_id: str
    has_data: bool
    snapshot: Optional[SeasonalitySnapshot] = None
    refresh_due_in_days: Optional[int] = None
