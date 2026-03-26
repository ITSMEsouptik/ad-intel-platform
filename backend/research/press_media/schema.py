"""
Novara Research Foundation: Press & Media Intelligence Schema
Version 1.0 - Feb 2026

Structured press/media coverage intelligence:
- Articles with source, type, sentiment, excerpts
- Media narratives (recurring themes in coverage)
- Key quotes (usable in advertising)
- Source tier classification
- Coverage gaps
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime, timezone, timedelta


# ============== ARTICLE ==============

class PressArticle(BaseModel):
    """A discovered press/media article"""
    url: str = ""
    title: str = ""
    source_name: str = ""  # e.g. "Forbes", "Gulf News", "TechCrunch"
    source_domain: str = ""  # e.g. "forbes.com"
    article_type: str = "news"  # news | feature | interview | press_release | blog | opinion | listicle
    published_date: Optional[str] = None  # "2024-03" or "2025-01-15"
    excerpt: str = Field(default="", max_length=300)
    sentiment: str = "neutral"  # positive | neutral | negative | mixed
    relevance_score_0_100: int = 50


# ============== MEDIA NARRATIVE ==============

class MediaNarrative(BaseModel):
    """A recurring narrative/theme found in press coverage"""
    label: str = Field(default="", max_length=80)
    type: str = "narrative"  # narrative | controversy | milestone | positioning | trend
    sentiment: str = "neutral"  # positive | neutral | negative | mixed
    evidence: List[str] = Field(default_factory=list)  # quotes from articles, max 150 chars each
    source_urls: List[str] = Field(default_factory=list)
    frequency: str = "moderate"  # frequent | moderate | occasional


# ============== KEY QUOTE ==============

class PressQuote(BaseModel):
    """A notable quote from press coverage, usable in advertising"""
    quote: str = Field(default="", max_length=200)
    source_name: str = ""  # "Forbes", "Vogue"
    source_url: str = ""
    context: str = Field(default="", max_length=100)
    is_paraphrased: bool = True


# ============== MEDIA SOURCE ==============

class MediaSource(BaseModel):
    """A media outlet that has covered the brand"""
    name: str = ""
    domain: str = ""
    tier: str = "tier3"  # tier1 (major national/international) | tier2 (industry/regional) | tier3 (niche/local)
    article_count: int = 1
    most_recent_date: Optional[str] = None


# ============== AUDIT ==============

class PressMediaAudit(BaseModel):
    """Pipeline stats (internal)"""
    queries_generated: int = 0
    query_families_used: List[str] = Field(default_factory=list)
    articles_discovered: int = 0
    articles_after_filter: int = 0
    sources_found: List[str] = Field(default_factory=list)
    narratives_raw: int = 0
    narratives_kept: int = 0
    discovery_model: str = ""
    analysis_model: str = ""
    discovery_tokens: int = 0
    analysis_tokens: int = 0
    postprocess_stats: Dict[str, Any] = Field(default_factory=dict)


# ============== DELTA ==============

class PressMediaDelta(BaseModel):
    """Changes since last snapshot"""
    previous_captured_at: Optional[datetime] = None
    new_sources: List[str] = Field(default_factory=list)
    new_articles_count: int = 0
    new_narrative_labels: List[str] = Field(default_factory=list)
    removed_narrative_labels: List[str] = Field(default_factory=list)


# ============== INPUTS USED ==============

class PressMediaInputs(BaseModel):
    """Inputs used for this snapshot"""
    geo: Dict[str, str] = Field(default_factory=dict)
    brand_name: str = ""
    domain: str = ""
    subcategory: str = ""
    niche: str = ""
    services: List[str] = Field(default_factory=list)
    brand_overview: str = ""
    competitors_used: bool = False
    optional_modules_used: List[str] = Field(default_factory=list)


# ============== MAIN SNAPSHOT ==============

class PressMediaSnapshot(BaseModel):
    """Complete Press & Media Intelligence snapshot v1.0"""
    version: str = "1.0"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))

    inputs_used: PressMediaInputs = Field(default_factory=PressMediaInputs)
    query_plan: Dict[str, Any] = Field(default_factory=dict)

    articles: List[PressArticle] = Field(default_factory=list)
    narratives: List[MediaNarrative] = Field(default_factory=list)
    key_quotes: List[PressQuote] = Field(default_factory=list)
    media_sources: List[MediaSource] = Field(default_factory=list)

    coverage_summary: List[str] = Field(default_factory=list)  # 3 bullet summary
    coverage_gaps: List[str] = Field(default_factory=list)  # what's missing
    pr_opportunities: List[str] = Field(default_factory=list)  # angle ideas for future coverage

    audit: PressMediaAudit = Field(default_factory=PressMediaAudit)
    delta: PressMediaDelta = Field(default_factory=PressMediaDelta)


# ============== RESEARCH PACK SOURCE WRAPPER ==============

class PressMediaSource(BaseModel):
    """Press & Media as a source within research_packs"""
    latest: Optional[PressMediaSnapshot] = None
    history: List[PressMediaSnapshot] = Field(default_factory=list, max_length=10)
