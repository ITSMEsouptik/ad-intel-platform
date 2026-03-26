"""
Novara Research Foundation: Social Trends Intelligence Schema
Version 1.0 - Feb 2026

Structured social trend data:
- TrendItem: A single social post (IG or TikTok) with metrics + scoring
- SocialTrendSet: A list of TrendItems for one platform within one lens
- TrendingAudio: A trending audio track discovered from TikTok data
- SocialTrendsSnapshot: Complete snapshot across both platforms + both lenses
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime, timezone, timedelta


# ============== METRICS ==============

class PostMetrics(BaseModel):
    """Engagement metrics for a social post"""
    views: Optional[int] = None
    likes: int = 0
    comments: int = 0
    shares: Optional[int] = None
    saves: Optional[int] = None


class TrendScore(BaseModel):
    """Computed scores for ranking (v2.0)"""
    trend_score: float = 0.0
    engagement_rate: Optional[float] = None
    recency_score: float = 0.0
    save_rate: Optional[float] = None
    overperformance_ratio: Optional[float] = None


# ============== TREND ITEM ==============

class TrendItem(BaseModel):
    """A single social post in the curated shortlist (v2.0)"""
    platform: Literal["instagram", "tiktok"]
    lens: Literal["brand_competitors", "category_trends"]
    query_type: Optional[str] = None  # viral | breakout | most_saved | most_discussed | handle
    content_label: Optional[str] = None  # official | mention | category (for UI badging)
    source_query: str = ""  # hashtag/keyword/handle/SQL label that found this
    author_handle: str = ""
    author_follower_count: Optional[int] = None
    author_verified: Optional[bool] = None
    post_url: str = ""
    thumb_url: Optional[str] = None  # cover_url for TikTok, media_url for IG
    media_url: Optional[str] = None
    media_type: Optional[str] = None  # image | video | reel | carousel
    caption: Optional[str] = Field(default=None, max_length=180)
    posted_at: Optional[str] = None  # ISO string
    duration: Optional[int] = None  # seconds (video/reel)
    hashtags: List[str] = Field(default_factory=list)
    metrics: PostMetrics = Field(default_factory=PostMetrics)
    score: TrendScore = Field(default_factory=TrendScore)
    # Audio info (TikTok)
    music_title: Optional[str] = None
    music_author: Optional[str] = None


# ============== TRENDING AUDIO ==============

class TrendingAudio(BaseModel):
    """A trending audio track found in category TikTok data"""
    music_title: str = ""
    music_author: str = ""
    usage_count: int = 0
    avg_views: int = 0
    avg_likes: int = 0
    top_video_url: Optional[str] = None  # highest-performing video using this audio
    top_video_views: Optional[int] = None


# ============== SOCIAL TREND SET ==============

class SocialTrendSet(BaseModel):
    """A collection of TrendItems for one platform within one lens"""
    items: List[TrendItem] = Field(default_factory=list)
    total_raw_fetched: int = 0
    queries_used: List[str] = Field(default_factory=list)


# ============== HANDLES ==============

class SocialHandle(BaseModel):
    """A discovered social media handle"""
    platform: Literal["instagram", "tiktok"]
    handle: str = ""
    url: str = ""
    source: str = ""  # "step2_channels" | "website_crawl" | "perplexity_fallback"
    follower_count: Optional[int] = None
    is_verified: Optional[bool] = None
    is_business: Optional[bool] = None


class HandleSet(BaseModel):
    """All discovered handles for brand + competitors"""
    brand: List[SocialHandle] = Field(default_factory=list)
    competitors: List[Dict[str, Any]] = Field(default_factory=list)
    # competitors: [{ name: str, handles: [SocialHandle] }]


# ============== AUDIT ==============

class SocialTrendsAudit(BaseModel):
    """Pipeline stats (internal)"""
    raw_records_fetched: int = 0
    by_source_query_counts: Dict[str, int] = Field(default_factory=dict)
    shofo_cost_estimate: float = 0.0
    request_ids: List[str] = Field(default_factory=list)
    transcript_enabled: bool = False
    comments_enabled: bool = False
    handles_discovered: int = 0
    handle_sources: List[str] = Field(default_factory=list)
    ig_hashtags_queried: int = 0
    tiktok_queries_run: int = 0
    shortlist_ig_count: int = 0
    shortlist_tiktok_count: int = 0
    scoring_config: Dict[str, float] = Field(default_factory=dict)


# ============== DELTA ==============

class SocialTrendsDelta(BaseModel):
    """Changes since last snapshot"""
    previous_captured_at: Optional[datetime] = None
    new_items_count: int = 0
    dropped_items_count: int = 0
    notable_new_items: List[str] = Field(default_factory=list)  # post_urls of high-score new items


# ============== INPUTS USED ==============

class SocialTrendsInputs(BaseModel):
    """Inputs used for this snapshot"""
    geo: Dict[str, str] = Field(default_factory=dict)
    brand_name: str = ""
    domain: str = ""
    subcategory: str = ""
    niche: str = ""
    industry: str = ""
    services: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    competitors_used: List[str] = Field(default_factory=list)


# ============== MAIN SNAPSHOT ==============

class SocialTrendsSnapshot(BaseModel):
    """Complete Social Trends Intelligence snapshot v1.0"""
    version: str = "1.0"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    window_days: int = 30

    inputs_used: SocialTrendsInputs = Field(default_factory=SocialTrendsInputs)
    handles: HandleSet = Field(default_factory=HandleSet)

    lenses: Dict[str, Dict[str, SocialTrendSet]] = Field(default_factory=lambda: {
        "brand_competitors": {"instagram": SocialTrendSet(), "tiktok": SocialTrendSet()},
        "category_trends": {"instagram": SocialTrendSet(), "tiktok": SocialTrendSet()},
    })

    shortlist: Dict[str, List[TrendItem]] = Field(default_factory=lambda: {
        "instagram": [],
        "tiktok": [],
    })

    trending_audio: List[TrendingAudio] = Field(default_factory=list)

    audit: SocialTrendsAudit = Field(default_factory=SocialTrendsAudit)
    delta: SocialTrendsDelta = Field(default_factory=SocialTrendsDelta)


# ============== RESEARCH PACK SOURCE WRAPPER ==============

class SocialTrendsSource(BaseModel):
    """Social Trends as a source within research_packs"""
    latest: Optional[SocialTrendsSnapshot] = None
    history: List[SocialTrendsSnapshot] = Field(default_factory=list, max_length=10)
