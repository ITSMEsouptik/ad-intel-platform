"""
Novara Ads Intelligence: Pydantic Schemas
Defines AdsIntelSnapshot, AdsLensResult, AdCard
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timezone, timedelta


class AdCard(BaseModel):
    ad_id: str
    brand_name: Optional[str] = None
    brand_id: Optional[str] = None

    publisher_platform: str  # facebook/instagram/tiktok
    display_format: Optional[str] = None  # video/image/carousel
    live: Optional[bool] = None

    start_date: Optional[str] = None
    end_date: Optional[str] = None
    last_seen_date: Optional[str] = None
    running_days: Optional[int] = None

    text: Optional[str] = None
    headline: Optional[str] = None
    cta: Optional[str] = None

    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    landing_page_url: Optional[str] = None
    has_preview: bool = True  # False when only a tiny avatar is available (DCO/carousel ads)

    # Composite scoring
    score: int = 0  # 0-100 composite quality score
    tier: str = "notable"  # proven_winner | strong_performer | rising | notable
    score_signals: Dict[str, int] = {}  # per-signal breakdown

    lens: str  # "competitor" | "category"
    why_shortlisted: str  # deterministic explanation


class AdsLensResult(BaseModel):
    ads: List[AdCard] = []
    stats: Dict[str, Any] = {}
    notes: List[str] = []


class AdsIntelSnapshot(BaseModel):
    version: str = "1.0"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=14))

    inputs: Dict[str, Any] = {}  # geo, competitor_domains, category_queries, platforms
    competitor_winners: AdsLensResult = Field(default_factory=AdsLensResult)
    category_winners: AdsLensResult = Field(default_factory=AdsLensResult)

    patterns: List[Dict[str, str]] = []  # detected winning ad patterns

    audit: Dict[str, Any] = {}  # api_calls, total_ads_seen, kept, deduped, rejects
    delta: Dict[str, Any] = {}  # new_ads_count, removed_ads_count (vs previous)
