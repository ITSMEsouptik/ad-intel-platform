"""
Novara Creative Analysis: Enhanced Prompt Templates
Each prompt provides strategic context, detailed analysis dimensions,
and quality guardrails to produce actionable creative intelligence.
"""

# ============== STRATEGIC CONTEXT (shared across all prompts) ==============

STRATEGIC_CONTEXT = """You are the Head of Creative Strategy at a top-tier performance marketing agency. Your client is entering this brand's competitive space and needs to understand exactly what makes their winning ads work — not surface-level descriptions, but the psychological mechanisms, audience triggers, and creative frameworks that can be adapted for a new brand.

Your analysis feeds directly into a creative brief. Be specific enough that a copywriter and video editor could reconstruct the creative approach without seeing the original ad."""

# ============== QUALITY GUARDRAILS (shared) ==============

QUALITY_RULES = """
## QUALITY RULES (critical — follow precisely):
- WRONG: "The ad uses social proof" → RIGHT: "Opens with '47,000+ 5-star reviews' as animated counter in first frame, building instant credibility before the product is shown"
- WRONG: "Professional production quality" → RIGHT: "Studio-lit with soft key light from upper-left, shallow depth of field isolating product, color graded in warm earth tones"
- WRONG: "Targets young women" → RIGHT: "Targets 25-34 urban professional women experiencing decision fatigue from too many skincare options, seeking a simplified routine validated by dermatologists"
- Every field must reference SPECIFIC elements you observe. Generic labels without evidence are worthless.
- For key_insight: Don't describe what the ad does. State what it TEACHES about persuasion that can be applied elsewhere.
- For replicable_framework: Name the framework (e.g., "The Before/After Authority Bridge") and explain the formula in one sentence.
"""

# ============== ENUM VALUE REFERENCES ==============

ENUM_REFERENCE = """
VALID ENUM VALUES (use EXACTLY these strings):

hook_type: question | bold_claim | pattern_interrupt | social_proof_opener | direct_benefit | transformation_reveal | curiosity_gap | pain_point
messaging_structure: problem_agitate_solve | feature_benefit_proof | testimonial_narrative | educational_steps | comparison | transformation_journey | offer_direct
visual_style: ugc_testimonial | studio_polished | motion_graphics | product_demo | lifestyle | text_overlay_heavy | before_after
production_quality: lo_fi_phone | semi_polished | professional | mixed
talent_archetype: relatable_peer | expert_authority | founder | model_aspirational | no_person_product_only
setting_environment: home_casual | studio | real_location | abstract_graphic | outdoor
urgency_mechanics: none | time_limited | scarcity | seasonal | fomo
cta_psychology: direct_action | low_commitment | urgency_driven | curiosity_driven
voice_person: first_person | second_person | third_person | mixed
tone: casual_conversational | professional_polished | enthusiastic | calm_authoritative | urgent_energetic
implied_awareness_stage: problem_aware | solution_aware | product_aware | most_aware
""".strip()


# ============== VIDEO AD ANALYSIS ==============

VIDEO_AD_FULL_PROMPT = """{strategic_context}

## Your Task
Reverse-engineer this video ad by examining BOTH the visual frames and audio track. Extract the creative DNA — the psychological mechanisms, structural choices, and production techniques that make it perform.

## Ad Metadata
- Brand: {brand_name}
- Platform: {platform}
- Running Days: {running_days}
- Performance Tier: {tier} (Score: {score}/100)
- Ad Copy: {copy_text}
- Headline: {headline}
- CTA Button: {cta}

## Analysis Required
Watch the full video. Pay close attention to:
1. The FIRST 3 SECONDS — what stops the scroll?
2. The AUDIO — voiceover tone, music energy, sound design
3. The NARRATIVE ARC — how tension builds and resolves
4. The PSYCHOLOGICAL TRIGGERS — what makes someone act?

Return a JSON object with this EXACT structure:
{{
  "core": {{
    "hook_type": "<enum>",
    "hook_text": "<EXACT opening line, on-screen text, or spoken words from first 3 seconds>",
    "hook_psychology": "<Why does this hook stop the scroll? What cognitive bias or emotional trigger does it exploit? Be specific.>",
    "scroll_stop_mechanism": "<The exact visual/audio element in the first 1.5 seconds that prevents scrolling — describe the specific frame, motion, or sound>",
    "messaging_structure": "<enum>",
    "body_narrative": "<2-3 sentences: how the argument builds after the hook — what's the persuasion sequence?>",
    "visual_style": "<enum>",
    "production_quality": "<enum>",
    "talent_archetype": "<enum>",
    "setting_environment": "<enum>",
    "proof_elements": ["<SPECIFIC proof elements — e.g., 'Dermatologist-tested badge at 0:08', 'Customer quote overlay: Maria, 34', not just 'social proof'>"],
    "urgency_mechanics": "<enum>",
    "cta_language": "<the EXACT verbal or visual CTA>",
    "cta_psychology": "<enum>",
    "voice_person": "<enum>",
    "tone": "<enum>",
    "implied_target_persona": "<Be precise: demographics + psychographics + situation. e.g., '28-35 urban women experiencing post-pregnancy skin changes, feeling overwhelmed by conflicting advice, seeking expert-backed simplicity'>",
    "implied_awareness_stage": "<enum>",
    "competitive_positioning": "<How does this ad position against alternatives? Direct comparison, category reframe, unique mechanism claim, or aspirational gap?>",
    "replicable_framework": "<Name the framework and state the formula. e.g., 'The Credential-First Demo: Lead with authority signal, then prove with live demonstration, close with risk reversal'>",
    "key_insight": "<One sentence: what does this ad TEACH about persuasion in this category that a strategist should steal?>"
  }},
  "video": {{
    "hook_visual_technique": "<zoom_in|hand_entry|split_screen|text_animation|face_to_camera|product_reveal|transition_effect>",
    "pacing": "<quick_cuts|continuous_shot|mixed_rhythm>",
    "audio_strategy": "<voiceover_narration|text_only_with_music|dialogue_testimonial|asmr_ambient|no_audio_designed>",
    "music_mood": "<upbeat|calm|trending_sound|dramatic|no_music>",
    "on_screen_text": ["<ALL key text overlays in the order they appear>"],
    "narrative_arc_beats": ["<story beats in sequence, e.g., 'curiosity_hook', 'problem_amplification', 'solution_reveal', 'proof_stack', 'urgency_close', 'cta_slide'>"],
    "transition_patterns": "<hard_cuts|smooth_transitions|text_card_breaks|mixed>",
    "emotional_arc": "<Map the viewer's emotional journey: What do they feel at 0s (curiosity/shock/recognition), 5s, 15s, and the end? How does the ad manipulate emotional state to drive action?>"
  }}
}}

{enum_reference}

{quality_rules}

Respond with ONLY the JSON object."""


# ============== IMAGE/STATIC AD ANALYSIS ==============

IMAGE_AD_PROMPT = """{strategic_context}

## Your Task
Reverse-engineer this static image ad. Extract the visual persuasion architecture — how layout, copy, imagery, and color work together to convert a scroll into a click.

## Ad Metadata
- Brand: {brand_name}
- Platform: {platform}
- Running Days: {running_days}
- Performance Tier: {tier} (Score: {score}/100)
- Ad Copy: {copy_text}
- Headline: {headline}
- CTA Button: {cta}

## Analysis Required
Examine every element: text placement, imagery, whitespace, color choices, visual hierarchy, and how the eye travels across the image.

Return a JSON object with this EXACT structure:
{{
  "core": {{
    "hook_type": "<enum>",
    "hook_text": "<the PRIMARY attention-grabbing text element in the image — the first thing the eye hits>",
    "hook_psychology": "<Why does this visual hook work? What cognitive bias does the layout exploit?>",
    "scroll_stop_mechanism": "<The specific visual element that makes a thumb pause — unusual color, face, contrast, pattern break, etc.>",
    "messaging_structure": "<enum>",
    "body_narrative": "<1-2 sentences: the overall persuasion message this image conveys>",
    "visual_style": "<enum>",
    "production_quality": "<enum>",
    "talent_archetype": "<enum>",
    "setting_environment": "<enum>",
    "proof_elements": ["<SPECIFIC proof elements visible in the image>"],
    "urgency_mechanics": "<enum>",
    "cta_language": "<the EXACT CTA text visible in image or ad copy>",
    "cta_psychology": "<enum>",
    "voice_person": "<enum>",
    "tone": "<enum>",
    "implied_target_persona": "<precise demographics + psychographics + situation>",
    "implied_awareness_stage": "<enum>",
    "competitive_positioning": "<How this ad positions vs alternatives>",
    "replicable_framework": "<Name the visual formula. e.g., 'The Split-Screen Contrast: Problem state on left, solution state on right, product bridging the center'>",
    "key_insight": "<One sentence: what this image teaches about visual persuasion in this category>"
  }},
  "image": {{
    "layout_structure": "<product_centered|lifestyle_scene|text_dominant|split_composition|collage|minimal>",
    "text_hierarchy": "<headline_dominant|visual_dominant|balanced|cta_dominant>",
    "information_density": "<minimal_single_message|moderate|dense_multi_element>",
    "color_mood": "<warm|cool|high_contrast|muted|brand_aligned>"
  }}
}}

{enum_reference}

{quality_rules}

Respond with ONLY the JSON object."""


# ============== CAROUSEL AD ANALYSIS ==============

CAROUSEL_AD_PROMPT = """{strategic_context}

## Your Task
Reverse-engineer this carousel ad. Only the first card image is available, but combined with the ad copy, infer the full carousel narrative strategy — how it hooks, builds, and converts across cards.

## Ad Metadata
- Brand: {brand_name}
- Platform: {platform}
- Running Days: {running_days}
- Performance Tier: {tier} (Score: {score}/100)
- Ad Copy: {copy_text}
- Headline: {headline}
- CTA Button: {cta}

## Analysis Required
Analyze the first card visual and full ad copy. Infer the carousel's swipe-driving mechanism and narrative arc.

Return a JSON object with this EXACT structure:
{{
  "core": {{
    "hook_type": "<enum>",
    "hook_text": "<the opening card's primary hook — what makes someone start swiping>",
    "hook_psychology": "<Why does this first card compel a swipe? What curiosity or tension does it create?>",
    "scroll_stop_mechanism": "<The specific element on card 1 that stops the scroll AND triggers a swipe>",
    "messaging_structure": "<enum>",
    "body_narrative": "<1-2 sentences: the inferred carousel story arc from first card + copy>",
    "visual_style": "<enum>",
    "production_quality": "<enum>",
    "talent_archetype": "<enum>",
    "setting_environment": "<enum>",
    "proof_elements": ["<specific proof elements>"],
    "urgency_mechanics": "<enum>",
    "cta_language": "<the actual CTA>",
    "cta_psychology": "<enum>",
    "voice_person": "<enum>",
    "tone": "<enum>",
    "implied_target_persona": "<precise persona description>",
    "implied_awareness_stage": "<enum>",
    "competitive_positioning": "<positioning strategy>",
    "replicable_framework": "<Name the carousel formula. e.g., 'The Progressive Reveal: Each card reveals one more benefit, creating information dependency'>",
    "key_insight": "<One sentence: what this carousel teaches about multi-frame persuasion>"
  }},
  "carousel": {{
    "opening_card_strategy": "<question|bold_statement|striking_visual|problem_image|product_showcase>",
    "card_narrative_type": "<sequential_story|independent_benefits|progressive_reveal|comparison_steps|before_after_journey>",
    "swipe_motivation": "<curiosity_gap|information_dependency|visual_progression>"
  }}
}}

{enum_reference}

{quality_rules}

Respond with ONLY the JSON object."""


# ============== BASIC AD ANALYSIS (thumbnail + copy only) ==============

BASIC_AD_PROMPT = """{strategic_context}

## Your Task
Analyze this ad based on the available thumbnail and copy text. Extract the core creative strategy.

## Ad Metadata
- Brand: {brand_name}
- Platform: {platform}
- Format: {display_format}
- Running Days: {running_days}
- Ad Copy: {copy_text}
- Headline: {headline}
- CTA Button: {cta}

Return a JSON object with this EXACT structure:
{{
  "core": {{
    "hook_type": "<enum>",
    "hook_text": "<primary hook text>",
    "hook_psychology": "<why this hook works>",
    "scroll_stop_mechanism": "<what stops the scroll>",
    "messaging_structure": "<enum>",
    "body_narrative": "<1-2 sentences>",
    "visual_style": "<enum>",
    "production_quality": "<enum>",
    "talent_archetype": "<enum>",
    "setting_environment": "<enum>",
    "proof_elements": ["<proof elements>"],
    "urgency_mechanics": "<enum>",
    "cta_language": "<actual CTA>",
    "cta_psychology": "<enum>",
    "voice_person": "<enum>",
    "tone": "<enum>",
    "implied_target_persona": "<precise persona>",
    "implied_awareness_stage": "<enum>",
    "competitive_positioning": "<positioning>",
    "replicable_framework": "<the creative formula>",
    "key_insight": "<one actionable insight>"
  }}
}}

{enum_reference}

{quality_rules}

Respond with ONLY the JSON object."""


# ============== TIKTOK POST ANALYSIS ==============

TIKTOK_ANALYSIS_PROMPT = """{strategic_context}

## Your Task
Analyze this TikTok post for creative patterns that a brand could adapt. Focus on WHY it earned saves (high-intent engagement) and what makes the format replicable.

## Post Metadata
- Author: @{author_handle}
- Caption: {caption}
- Views: {views}
- Likes: {likes}
- Saves: {saves}
- Save Rate: {save_rate}%
- Duration: {duration}s
- Music: {music_title} by {music_author}

## Analysis Required
Watch the video. Identify the content formula — how it hooks, delivers value, and earns saves. Think about what makes this REPLICABLE for a brand.

Return a JSON object with this EXACT structure:
{{
  "analysis": {{
    "content_format": "<tutorial|transformation|grwm|product_demo|comedy|review|asmr|storytelling|trend_recreation>",
    "hook_technique": "<describe the SPECIFIC technique used in first 1-2 seconds — not just 'visual hook' but exactly what happens>",
    "hook_psychology": "<why this hook works on TikTok specifically — what scroll-stopping mechanism is at play?>",
    "production_style": "<lo_fi_phone|semi_polished|professional>",
    "audio_strategy": "<voiceover|trending_sound|original_audio|text_only|asmr>",
    "save_worthy_reason": "<be specific: what VALUE does a save capture? e.g., 'Step-by-step recipe viewers want to reference later' not just 'educational content'>",
    "trending_elements": ["<specific trending elements a brand could adopt: transition style, audio choice, format template, caption pattern, etc.>"],
    "replicable_framework": "<Name the content formula. e.g., 'The Satisfying Process Reveal: Show raw materials → mesmerizing transformation → finished product, set to trending audio'>"
  }},
  "hook_text": "<the EXACT opening line, text overlay, or spoken hook>",
  "implied_target_persona": "<who this content resonates with — be precise about demographics + interests + situation>",
  "key_insight": "<One sentence: what this content teaches about organic engagement that a brand should learn>"
}}

{quality_rules}

Respond with ONLY the JSON object."""


def build_ad_prompt(ad: dict, depth: str) -> str:
    """Build the appropriate prompt for an ad based on format and depth."""
    fmt = (ad.get("display_format") or "").lower()
    brand = ad.get("brand_name") or "Unknown"
    platform = ad.get("publisher_platform") or "facebook"
    running_days = ad.get("running_days") or "N/A"
    tier = ad.get("tier") or "notable"
    score = ad.get("score") or 0
    copy_text = ad.get("text") or "N/A"
    headline = ad.get("headline") or "N/A"
    cta = ad.get("cta") or "N/A"

    params = dict(
        strategic_context=STRATEGIC_CONTEXT,
        quality_rules=QUALITY_RULES,
        enum_reference=ENUM_REFERENCE,
        brand_name=brand, platform=platform, running_days=running_days,
        tier=tier, score=score, copy_text=copy_text[:500],
        headline=headline, cta=cta, display_format=fmt,
    )

    if depth == "basic":
        return BASIC_AD_PROMPT.format(**params)
    elif fmt == "video":
        return VIDEO_AD_FULL_PROMPT.format(**params)
    elif fmt == "image":
        return IMAGE_AD_PROMPT.format(**params)
    elif fmt == "carousel":
        return CAROUSEL_AD_PROMPT.format(**params)
    else:
        return BASIC_AD_PROMPT.format(**params)


def build_tiktok_prompt(post: dict) -> str:
    """Build the analysis prompt for a TikTok post."""
    metrics = post.get("metrics", post.get("score", {}))
    score_data = post.get("score", {})

    return TIKTOK_ANALYSIS_PROMPT.format(
        strategic_context=STRATEGIC_CONTEXT,
        quality_rules=QUALITY_RULES,
        author_handle=post.get("author_handle", "unknown"),
        caption=post.get("caption", "N/A")[:300],
        views=metrics.get("views", "N/A"),
        likes=metrics.get("likes", 0),
        saves=metrics.get("saves", "N/A"),
        save_rate=round(score_data.get("save_rate", 0) * 100, 2) if isinstance(score_data, dict) else "N/A",
        duration=post.get("duration", "N/A"),
        music_title=post.get("music_title", "N/A"),
        music_author=post.get("music_author", "N/A"),
    )
