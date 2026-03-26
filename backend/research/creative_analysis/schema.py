"""
Novara Creative Analysis Layer: Pydantic Schemas
Defines structured output for multimodal ad/post analysis.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta


# ============== SHARED CORE (all formats) ==============

class CreativeAnalysisCore(BaseModel):
    hook_type: str = ""  # question | bold_claim | pattern_interrupt | social_proof_opener | direct_benefit | transformation_reveal | curiosity_gap | pain_point
    hook_text: str = ""
    hook_psychology: str = ""  # WHY this hook stops the scroll — cognitive bias or emotional trigger
    scroll_stop_mechanism: str = ""  # The exact 1.5-second element that prevents scrolling
    messaging_structure: str = ""  # problem_agitate_solve | feature_benefit_proof | testimonial_narrative | educational_steps | comparison | transformation_journey | offer_direct
    body_narrative: str = ""
    visual_style: str = ""  # ugc_testimonial | studio_polished | motion_graphics | product_demo | lifestyle | text_overlay_heavy | before_after
    production_quality: str = ""  # lo_fi_phone | semi_polished | professional | mixed
    talent_archetype: str = ""  # relatable_peer | expert_authority | founder | model_aspirational | no_person_product_only
    setting_environment: str = ""  # home_casual | studio | real_location | abstract_graphic | outdoor
    proof_elements: List[str] = Field(default_factory=list)
    urgency_mechanics: str = "none"  # none | time_limited | scarcity | seasonal | fomo
    cta_language: str = ""
    cta_psychology: str = ""  # direct_action | low_commitment | urgency_driven | curiosity_driven
    voice_person: str = ""  # first_person | second_person | third_person | mixed
    tone: str = ""  # casual_conversational | professional_polished | enthusiastic | calm_authoritative | urgent_energetic
    implied_target_persona: str = ""
    implied_awareness_stage: str = ""  # problem_aware | solution_aware | product_aware | most_aware
    competitive_positioning: str = ""  # How the ad positions vs alternatives
    replicable_framework: str = ""  # The creative formula that can be applied to another brand
    key_insight: str = ""


# ============== FORMAT-SPECIFIC FIELDS ==============

class VideoAnalysisFields(BaseModel):
    hook_visual_technique: str = ""  # zoom_in | hand_entry | split_screen | text_animation | face_to_camera | product_reveal | transition_effect
    pacing: str = ""  # quick_cuts | continuous_shot | mixed_rhythm
    audio_strategy: str = ""  # voiceover_narration | text_only_with_music | dialogue_testimonial | asmr_ambient | no_audio_designed
    music_mood: str = ""  # upbeat | calm | trending_sound | dramatic | no_music
    on_screen_text: List[str] = Field(default_factory=list)
    narrative_arc_beats: List[str] = Field(default_factory=list)
    transition_patterns: str = ""  # hard_cuts | smooth_transitions | text_card_breaks | mixed
    emotional_arc: str = ""  # Mapped emotional journey: what the viewer feels at 0s, 5s, 15s, end


class ImageAnalysisFields(BaseModel):
    layout_structure: str = ""  # product_centered | lifestyle_scene | text_dominant | split_composition | collage | minimal
    text_hierarchy: str = ""  # headline_dominant | visual_dominant | balanced | cta_dominant
    information_density: str = ""  # minimal_single_message | moderate | dense_multi_element
    color_mood: str = ""  # warm | cool | high_contrast | muted | brand_aligned


class CarouselAnalysisFields(BaseModel):
    opening_card_strategy: str = ""  # question | bold_statement | striking_visual | problem_image | product_showcase
    card_narrative_type: str = ""  # sequential_story | independent_benefits | progressive_reveal | comparison_steps | before_after_journey
    swipe_motivation: str = ""  # curiosity_gap | information_dependency | visual_progression


class TikTokAnalysisFields(BaseModel):
    content_format: str = ""  # tutorial | transformation | grwm | product_demo | comedy | review | asmr | storytelling | trend_recreation
    hook_technique: str = ""
    hook_psychology: str = ""  # WHY this hook works
    production_style: str = ""  # lo_fi_phone | semi_polished | professional
    audio_strategy: str = ""  # voiceover | trending_sound | original_audio | text_only | asmr
    save_worthy_reason: str = ""
    trending_elements: List[str] = Field(default_factory=list)
    replicable_framework: str = ""  # The content formula a brand can adapt


# ============== COMBINED ANALYSIS OBJECTS ==============

class AdCreativeAnalysis(BaseModel):
    """Full analysis for a single ad creative."""
    ad_id: str
    display_format: str  # video | image | carousel | dco
    analysis_depth: str = "full"  # full | standard | basic
    core: CreativeAnalysisCore = Field(default_factory=CreativeAnalysisCore)
    video: Optional[VideoAnalysisFields] = None
    image: Optional[ImageAnalysisFields] = None
    carousel: Optional[CarouselAnalysisFields] = None
    error: Optional[str] = None


class TikTokCreativeAnalysis(BaseModel):
    """Lighter analysis for a TikTok post."""
    post_url: str
    author_handle: str = ""
    analysis: TikTokAnalysisFields = Field(default_factory=TikTokAnalysisFields)
    hook_text: Optional[str] = None
    implied_target_persona: Optional[str] = None
    key_insight: Optional[str] = None
    error: Optional[str] = None


# ============== PATTERN SUMMARY ==============

class PatternSummary(BaseModel):
    """Aggregated patterns from all analyzed creatives."""
    dominant_hook_types: List[Dict[str, Any]] = Field(default_factory=list)
    dominant_messaging_structures: List[Dict[str, Any]] = Field(default_factory=list)
    dominant_visual_styles: List[Dict[str, Any]] = Field(default_factory=list)
    dominant_tones: List[Dict[str, Any]] = Field(default_factory=list)
    common_proof_elements: List[str] = Field(default_factory=list)
    persona_patterns: List[str] = Field(default_factory=list)
    format_insights: List[str] = Field(default_factory=list)
    top_key_insights: List[str] = Field(default_factory=list)
    top_replicable_frameworks: List[str] = Field(default_factory=list)


# ============== SNAPSHOT ==============

class CreativeAnalysisSnapshot(BaseModel):
    version: str = "1.1"
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    refresh_due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=14))

    ad_analyses: List[AdCreativeAnalysis] = Field(default_factory=list)
    tiktok_analyses: List[TikTokCreativeAnalysis] = Field(default_factory=list)

    pattern_summary: PatternSummary = Field(default_factory=PatternSummary)

    audit: Dict[str, Any] = Field(default_factory=dict)
    status: str = "success"  # success | partial | failed
