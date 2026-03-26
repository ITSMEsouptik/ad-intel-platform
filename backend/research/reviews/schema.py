"""
Novara Research Foundation: Reviews & Reputation Schema
Version 1.5 - Feb 2026

Enhancements over v1.0:
- Review recency per platform
- Owner response rate per platform
- App store review detection
- Social proof readiness score
- Brand vs reality cross-reference
- Paraphrased disclaimer on snippets
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime, timezone, timedelta


# ============== PLATFORM PRESENCE ==============

class ReviewPlatform(BaseModel):
    """A review platform where the brand has presence"""
    platform: str = ""
    url: Optional[str] = None
    approximate_rating: Optional[float] = None
    approximate_count: Optional[str] = None
    has_reviews: bool = False
    # v1.5 additions
    recency: str = "unknown"  # within_last_month | 1_3_months | 3_6_months | 6_months_plus | unknown
    owner_responds: Optional[bool] = None  # Does the business respond to reviews?
    response_quality: str = "unknown"  # active | occasional | rare | none | unknown
    is_app_store: bool = False  # True if Apple App Store or Google Play


# ============== THEME MODELS ==============

class StrengthTheme(BaseModel):
    """A recurring positive theme from reviews"""
    theme: str = Field(default="", max_length=80)
    evidence: List[str] = Field(default_factory=list)
    frequency: str = "moderate"  # frequent | moderate | occasional


class WeaknessTheme(BaseModel):
    """A recurring negative theme from reviews"""
    theme: str = Field(default="", max_length=80)
    evidence: List[str] = Field(default_factory=list)
    frequency: str = "moderate"
    severity: str = "minor"  # minor | moderate | deal_breaker


# ============== SOCIAL PROOF ==============

class SocialProofSnippet(BaseModel):
    """A review quote ready to use in ad copy"""
    quote: str = Field(default="", max_length=200)
    platform: str = ""
    context: str = Field(default="", max_length=100)
    is_paraphrased: bool = True  # v1.5: disclaimer — all LLM-sourced quotes are paraphrased


# ============== BRAND VS REALITY ==============

class BrandClaimCheck(BaseModel):
    """A single brand marketing claim compared against review reality"""
    claim: str = Field(default="", max_length=150)
    review_alignment: str = "unknown"  # supported | partially_supported | contradicted | not_mentioned
    evidence: str = Field(default="", max_length=200)


class BrandVsReality(BaseModel):
    """Cross-reference: brand marketing claims vs third-party reviews"""
    claims_checked: int = 0
    supported: int = 0
    contradicted: int = 0
    not_mentioned: int = 0
    checks: List[BrandClaimCheck] = Field(default_factory=list)
    summary: str = Field(default="", max_length=250)


# ============== COMPETITOR REPUTATION ==============

class CompetitorReputation(BaseModel):
    """How a competitor's reputation compares"""
    name: str = ""
    approximate_rating: Optional[float] = None
    primary_platform: str = ""
    reputation_gap: str = Field(default="", max_length=150)


# ============== AUDIT ==============

class ReviewsAudit(BaseModel):
    """Tracks pipeline stats"""
    platforms_checked: int = 0
    platforms_with_reviews: int = 0
    total_approximate_reviews: int = 0
    discovery_model: str = ""
    analysis_model: str = ""
    discovery_tokens: int = 0
    analysis_tokens: int = 0
    geo_platforms_used: List[str] = Field(default_factory=list)
    niche_platforms_used: List[str] = Field(default_factory=list)
    postprocess_stats: Dict[str, Any] = Field(default_factory=dict)


# ============== DELTA ==============

class ReviewsDelta(BaseModel):
    """Tracks changes between snapshots"""
    previous_captured_at: Optional[datetime] = None
    notable_changes: List[str] = Field(default_factory=list, max_length=5)
    rating_change: Optional[float] = None


# ============== INPUTS USED ==============

class ReviewsInputs(BaseModel):
    """Inputs used for this snapshot"""
    geo: Dict[str, str] = Field(default_factory=dict)
    brand_name: str = ""
    domain: str = ""
    subcategory: str = ""
    niche: str = ""
    services: List[str] = Field(default_factory=list)
    brand_overview: str = ""
    # v1.5 additions
    app_store_urls: List[str] = Field(default_factory=list)
    brand_claims: List[str] = Field(default_factory=list)


# ============== MAIN SNAPSHOT ==============

class ReviewsSnapshot(BaseModel):
    """Complete Reviews & Reputation snapshot v1.5"""
    version: str = "1.5"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))

    inputs_used: ReviewsInputs = Field(default_factory=ReviewsInputs)

    # v1.5: Social Proof Readiness Score
    social_proof_readiness: str = "unknown"  # strong | moderate | weak | unknown

    reputation_summary: List[str] = Field(default_factory=list)
    platform_presence: List[ReviewPlatform] = Field(default_factory=list)
    strength_themes: List[StrengthTheme] = Field(default_factory=list)
    weakness_themes: List[WeaknessTheme] = Field(default_factory=list)
    social_proof_snippets: List[SocialProofSnippet] = Field(default_factory=list)
    trust_signals: List[str] = Field(default_factory=list)
    competitor_reputation: List[CompetitorReputation] = Field(default_factory=list)

    # v1.5: Brand vs Reality cross-reference
    brand_vs_reality: BrandVsReality = Field(default_factory=BrandVsReality)

    audit: ReviewsAudit = Field(default_factory=ReviewsAudit)
    delta: ReviewsDelta = Field(default_factory=ReviewsDelta)


# ============== RESEARCH PACK SOURCE WRAPPER ==============

class ReviewsSource(BaseModel):
    """Reviews as a source within research_packs"""
    latest: Optional[ReviewsSnapshot] = None
    history: List[ReviewsSnapshot] = Field(default_factory=list, max_length=10)


# ============== API RESPONSE MODELS ==============

class ReviewsRunResponse(BaseModel):
    """Response from POST /api/research/{campaignId}/reviews/run"""
    campaign_id: str
    status: str
    snapshot: ReviewsSnapshot
    message: str = ""


class ReviewsLatestResponse(BaseModel):
    """Response from GET /api/research/{campaignId}/reviews/latest"""
    campaign_id: str
    has_data: bool
    snapshot: Optional[ReviewsSnapshot] = None
    refresh_due_in_days: Optional[int] = None
