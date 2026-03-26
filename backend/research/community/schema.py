"""
Novara Research Foundation: Community Intelligence Schema
Version 1.0 - Feb 2026

Structured community discussion intelligence:
- Forum threads with excerpts and metadata
- Themes (pain/objection/desire/trigger/comparison/how_to)
- Language bank (verbatim phrases + words from real discussions)
- Audience notes + creative implications
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime, timezone, timedelta


# ============== THREAD ==============

class CommunityThread(BaseModel):
    """A discovered forum/community thread"""
    url: str = ""
    domain: str = ""
    title: Optional[str] = None
    published_at: Optional[str] = None
    query_used: str = ""
    excerpt: str = Field(default="", max_length=280)
    comment_count_est: Optional[int] = None
    relevance_score_0_100: int = 50


# ============== THEMES ==============

class CommunityTheme(BaseModel):
    """A recurring theme extracted from community discussions"""
    label: str = Field(default="", max_length=60)
    type: str = "pain"  # pain | objection | desire | trigger | comparison | how_to
    frequency: str = "medium"  # high | medium | low
    evidence: List[str] = Field(default_factory=list)  # verbatim quotes <= 140 chars
    source_urls: List[str] = Field(default_factory=list)  # 1-4 URLs


# ============== LANGUAGE BANK ==============

class CommunityLanguageBank(BaseModel):
    """Real customer language from forum discussions"""
    phrases: List[str] = Field(default_factory=list)  # <= 20 phrases, <= 80 chars each
    words: List[str] = Field(default_factory=list)  # <= 30 words, 1-3 words each


# ============== AUDIT ==============

class CommunityAudit(BaseModel):
    """Pipeline stats (internal, not shown in UI)"""
    queries_generated: int = 0
    query_families_used: List[str] = Field(default_factory=list)
    threads_discovered: int = 0
    threads_after_dedup: int = 0
    domains_found: List[str] = Field(default_factory=list)
    themes_raw: int = 0
    themes_kept: int = 0
    discovery_model: str = ""
    synthesis_model: str = ""
    discovery_tokens: int = 0
    synthesis_tokens: int = 0
    postprocess_stats: Dict[str, Any] = Field(default_factory=dict)


# ============== DELTA ==============

class CommunityDelta(BaseModel):
    """Changes since last snapshot"""
    previous_captured_at: Optional[datetime] = None
    new_domains: List[str] = Field(default_factory=list)
    new_threads_count: int = 0
    new_theme_labels: List[str] = Field(default_factory=list)
    removed_theme_labels: List[str] = Field(default_factory=list)


# ============== INPUTS USED ==============

class CommunityInputs(BaseModel):
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

class CommunitySnapshot(BaseModel):
    """Complete Community Intelligence snapshot v1.0"""
    version: str = "1.0"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))

    inputs_used: CommunityInputs = Field(default_factory=CommunityInputs)
    query_plan: Dict[str, Any] = Field(default_factory=dict)

    threads: List[CommunityThread] = Field(default_factory=list)
    themes: List[CommunityTheme] = Field(default_factory=list)
    language_bank: CommunityLanguageBank = Field(default_factory=CommunityLanguageBank)
    audience_notes: List[str] = Field(default_factory=list)
    creative_implications: List[str] = Field(default_factory=list)
    gaps_to_research: List[str] = Field(default_factory=list)

    audit: CommunityAudit = Field(default_factory=CommunityAudit)
    delta: CommunityDelta = Field(default_factory=CommunityDelta)


# ============== RESEARCH PACK SOURCE WRAPPER ==============

class CommunitySource(BaseModel):
    """Community as a source within research_packs"""
    latest: Optional[CommunitySnapshot] = None
    history: List[CommunitySnapshot] = Field(default_factory=list, max_length=10)
