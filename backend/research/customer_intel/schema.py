"""
Novara Research Foundation: Customer Intel Schema
Version 1.1 - Feb 2026

Lean, high-signal structure:
- Max 3 SegmentCards mapped to offer items + search phrases
- TriggerMap (moment/urgency/planned)
- LanguageBank (desire/anxiety/intent, 12 each)
- Killed: personas, decision_speed, price_sensitivity, CTA-per-trigger
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta


class SegmentCard(BaseModel):
    """Customer segment grounded in offers + search phrases"""
    segment_name: str = Field(default="", max_length=48)
    jtbd: str = Field(default="", max_length=120)

    core_motives: List[str] = Field(default_factory=list)
    top_pains: List[str] = Field(default_factory=list)
    top_objections: List[str] = Field(default_factory=list)

    best_proof: List[str] = Field(default_factory=list)
    risk_reducers: List[str] = Field(default_factory=list)

    best_offer_items: List[str] = Field(default_factory=list)
    best_channel_focus: List[str] = Field(default_factory=list)

    search_language: List[str] = Field(default_factory=list)


class TriggerMap(BaseModel):
    """Buying triggers — what makes people start searching"""
    moment_triggers: List[str] = Field(default_factory=list)
    urgency_triggers: List[str] = Field(default_factory=list)
    planned_triggers: List[str] = Field(default_factory=list)


class LanguageBank(BaseModel):
    """Real phrases customers use"""
    desire_phrases: List[str] = Field(default_factory=list)
    anxiety_phrases: List[str] = Field(default_factory=list)
    intent_phrases: List[str] = Field(default_factory=list)


class CustomerIntelAudit(BaseModel):
    """Tracks post-processing and grounding stats"""
    offer_items_available: List[str] = Field(default_factory=list)
    offer_items_used: List[str] = Field(default_factory=list)
    search_phrases_available_count: int = 0
    search_phrases_used: List[str] = Field(default_factory=list)
    segments_raw_count: int = 0
    segments_dropped: List[Dict[str, str]] = Field(default_factory=list)
    relaxation_applied: bool = False
    missing_inputs: List[str] = Field(default_factory=list)
    generic_filler_removed: int = 0
    duplicates_removed: int = 0
    retry_count: int = 0
    llm_model: str = ""
    llm_tokens_used: int = 0


class CustomerIntelDelta(BaseModel):
    """Delta tracking between snapshots"""
    notable_changes: List[str] = Field(default_factory=list, max_length=5)
    new_segments_count: int = 0
    removed_segments_count: int = 0


class CustomerIntelSnapshot(BaseModel):
    """Complete Customer Intel snapshot v1.1"""
    version: str = "1.1"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=14))

    summary_bullets: List[str] = Field(default_factory=list)
    segments: List[SegmentCard] = Field(default_factory=list)
    trigger_map: TriggerMap = Field(default_factory=TriggerMap)
    language_bank: LanguageBank = Field(default_factory=LanguageBank)

    audit: CustomerIntelAudit = Field(default_factory=CustomerIntelAudit)
    delta: CustomerIntelDelta = Field(default_factory=CustomerIntelDelta)


class CustomerIntelSource(BaseModel):
    """Source container in research_packs"""
    latest: Optional[CustomerIntelSnapshot] = None
    history: List[CustomerIntelSnapshot] = Field(default_factory=list)
