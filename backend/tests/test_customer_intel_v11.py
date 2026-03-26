"""
Tests for Customer Intel v1.1 — Lean, High-Signal

Tests:
1. Schema compliance — SegmentCard, TriggerMap, LanguageBank
2. Post-processing — offer/search constraint validation
3. Post-processing — generic filler removal
4. Post-processing — dedup + caps
5. Post-processing — relaxation fallback
6. Prompt structure — offers + search phrases in prompt
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from research.customer_intel.schema import (
    SegmentCard,
    TriggerMap,
    LanguageBank,
    CustomerIntelSnapshot,
    CustomerIntelAudit,
    CustomerIntelDelta,
)
from research.customer_intel.postprocess import (
    postprocess_customer_intel,
    validate_segment_constraints,
    remove_generic_filler,
    clean_string_list,
    _normalize,
    _substring_match,
)
from research.customer_intel.perplexity_customer_intel import (
    build_prompt,
    build_input_context,
)


# ============== SCHEMA TESTS ==============

class TestSchemaV11:

    def test_segment_card_all_fields(self):
        seg = SegmentCard(
            segment_name="Busy Brides",
            jtbd="Look amazing on wedding day without stress",
            core_motives=["Confidence", "Time saving"],
            top_pains=["Can't find reliable artist", "Worried about allergies"],
            top_objections=["Too expensive", "Can't see results first"],
            best_proof=["Before/after photos", "Google reviews"],
            risk_reducers=["Free consultation", "Patch test"],
            best_offer_items=["Bridal Makeup", "Hair Styling"],
            best_channel_focus=["Instagram Reels"],
            search_language=["bridal makeup near me", "wedding makeup artist"]
        )
        assert seg.segment_name == "Busy Brides"
        assert len(seg.core_motives) == 2
        assert len(seg.best_offer_items) == 2
        assert len(seg.search_language) == 2

    def test_segment_card_defaults(self):
        seg = SegmentCard()
        assert seg.segment_name == ""
        assert seg.jtbd == ""
        assert seg.core_motives == []
        assert seg.best_offer_items == []
        assert seg.search_language == []

    def test_snapshot_version(self):
        snapshot = CustomerIntelSnapshot()
        assert snapshot.version == "1.1"

    def test_snapshot_no_personas(self):
        """v1.1 should not have persona_cards field"""
        snapshot = CustomerIntelSnapshot()
        assert not hasattr(snapshot, 'persona_cards')

    def test_snapshot_no_icp_segments(self):
        """v1.1 uses 'segments' not 'icp_segments'"""
        snapshot = CustomerIntelSnapshot()
        assert hasattr(snapshot, 'segments')
        assert not hasattr(snapshot, 'icp_segments')

    def test_snapshot_has_trigger_map(self):
        snapshot = CustomerIntelSnapshot()
        assert isinstance(snapshot.trigger_map, TriggerMap)
        assert hasattr(snapshot.trigger_map, 'moment_triggers')
        assert hasattr(snapshot.trigger_map, 'urgency_triggers')
        assert hasattr(snapshot.trigger_map, 'planned_triggers')

    def test_snapshot_has_language_bank(self):
        snapshot = CustomerIntelSnapshot()
        assert isinstance(snapshot.language_bank, LanguageBank)
        assert hasattr(snapshot.language_bank, 'desire_phrases')
        assert hasattr(snapshot.language_bank, 'anxiety_phrases')
        assert hasattr(snapshot.language_bank, 'intent_phrases')

    def test_audit_fields(self):
        audit = CustomerIntelAudit(
            offer_items_available=["Bridal Makeup", "Haircut"],
            offer_items_used=["Bridal Makeup"],
            search_phrases_available_count=20,
            search_phrases_used=["bridal makeup near me"],
            segments_raw_count=3,
            segments_dropped=[{"segment": "Generic", "reason": "no_offer_match"}],
            relaxation_applied=False,
            generic_filler_removed=2,
            duplicates_removed=1,
            retry_count=0
        )
        assert len(audit.offer_items_used) == 1
        assert audit.generic_filler_removed == 2


# ============== POST-PROCESSING TESTS ==============

class TestPostProcessing:

    def _make_segment(self, **overrides):
        base = {
            "segment_name": "Busy Brides",
            "jtbd": "Look amazing on wedding day",
            "core_motives": ["Confidence", "Time saving"],
            "top_pains": ["Can't find reliable artist"],
            "top_objections": ["Too expensive"],
            "best_proof": ["Before/after photos"],
            "risk_reducers": ["Free consultation"],
            "best_offer_items": ["Bridal Makeup"],
            "best_channel_focus": ["Instagram Reels"],
            "search_language": ["bridal makeup near me", "wedding makeup artist", "best makeup for wedding"]
        }
        base.update(overrides)
        return base

    def test_valid_segment_passes_strict(self):
        offer_items = {"Bridal Makeup", "Haircut", "Coloring"}
        search_phrases = {"bridal makeup near me", "wedding makeup artist", "hair salon dubai"}
        passes, reason = validate_segment_constraints(
            self._make_segment(), offer_items, search_phrases, strict=True
        )
        assert passes
        assert reason == ""

    def test_no_offer_match_fails_strict(self):
        offer_items = {"Laser Treatment", "Facial"}
        search_phrases = {"bridal makeup near me", "wedding makeup artist"}
        seg = self._make_segment(best_offer_items=["Something Else"])
        passes, reason = validate_segment_constraints(seg, offer_items, search_phrases, strict=True)
        assert not passes
        assert "offer" in reason

    def test_weak_search_match_fails_strict(self):
        offer_items = {"Bridal Makeup"}
        search_phrases = {"hair salon dubai", "laser treatment cost"}
        seg = self._make_segment(search_language=["unrelated phrase 1", "unrelated phrase 2"])
        passes, reason = validate_segment_constraints(seg, offer_items, search_phrases, strict=True)
        assert not passes
        assert "search" in reason

    def test_no_search_data_skips_search_check(self):
        """If search_phrases_set is empty, search constraint is skipped"""
        offer_items = {"Bridal Makeup"}
        seg = self._make_segment(search_language=[])
        passes, reason = validate_segment_constraints(seg, offer_items, set(), strict=True)
        assert passes

    def test_substring_match_works(self):
        assert _substring_match("Bridal Makeup", {"bridal makeup and styling"})
        assert _substring_match("makeup", {"Bridal Makeup"})
        assert not _substring_match("laser", {"Bridal Makeup"})

    def test_relaxation_keeps_segments(self):
        """If strict filtering drops too many, relaxation should keep them"""
        segments = [
            self._make_segment(segment_name=f"Seg {i}", best_offer_items=["Unknown"])
            for i in range(3)
        ]
        raw = {
            "segments": segments,
            "trigger_map": {"moment_triggers": [], "urgency_triggers": [], "planned_triggers": []},
            "language_bank": {"desire_phrases": [], "anxiety_phrases": [], "intent_phrases": []},
            "summary_bullets": []
        }
        result, audit = postprocess_customer_intel(
            raw=raw,
            offer_catalog=["Bridal Makeup"],
            search_phrases=["bridal makeup near me"]
        )
        assert audit["relaxation_applied"] is True
        assert len(result["segments"]) >= 2

    def test_generic_filler_removed(self):
        text = "Premium high-quality bridal service"
        cleaned = remove_generic_filler(text, set())
        assert "premium" not in cleaned.lower()
        assert "high-quality" not in cleaned.lower()

    def test_filler_kept_if_in_search_phrases(self):
        """If 'premium' is in search phrases, keep it"""
        text = "Premium bridal service"
        cleaned = remove_generic_filler(text, {"premium bridal makeup"})
        assert "premium" in cleaned.lower() or "Premium" in cleaned

    def test_dedup_case_insensitive(self):
        items = ["Bridal Makeup", "bridal makeup", "BRIDAL MAKEUP", "Hair Styling"]
        cleaned, _ = clean_string_list(items, set(), max_len=10)
        assert len(cleaned) == 2

    def test_list_caps_enforced(self):
        items = [f"Item {i}" for i in range(20)]
        cleaned, _ = clean_string_list(items, set(), max_len=3)
        assert len(cleaned) == 3

    def test_full_pipeline(self):
        raw = {
            "summary_bullets": ["Insight 1", "Insight 2"],
            "segments": [self._make_segment()],
            "trigger_map": {
                "moment_triggers": ["Wedding booked"],
                "urgency_triggers": ["Event in 48 hours"],
                "planned_triggers": ["Wedding 3 months away"]
            },
            "language_bank": {
                "desire_phrases": ["bridal glow", "perfect look"],
                "anxiety_phrases": ["will it last?"],
                "intent_phrases": ["book bridal makeup"]
            }
        }
        result, audit = postprocess_customer_intel(
            raw=raw,
            offer_catalog=["Bridal Makeup", "Haircut"],
            search_phrases=["bridal makeup near me", "wedding makeup artist", "best makeup for wedding"]
        )
        assert len(result["segments"]) == 1
        assert len(result["trigger_map"]["moment_triggers"]) == 1
        assert len(result["language_bank"]["desire_phrases"]) == 2
        assert audit["segments_raw_count"] == 1

    def test_cross_dedup_language_bank(self):
        """Same phrase in desire and anxiety should be deduped across categories"""
        raw = {
            "summary_bullets": [],
            "segments": [],
            "trigger_map": {"moment_triggers": [], "urgency_triggers": [], "planned_triggers": []},
            "language_bank": {
                "desire_phrases": ["bridal glow", "perfect look"],
                "anxiety_phrases": ["bridal glow", "will it last?"],  # "bridal glow" is a dupe
                "intent_phrases": ["book now"]
            }
        }
        result, audit = postprocess_customer_intel(raw, [], [])
        all_phrases = (
            result["language_bank"]["desire_phrases"] +
            result["language_bank"]["anxiety_phrases"] +
            result["language_bank"]["intent_phrases"]
        )
        norms = [_normalize(p) for p in all_phrases]
        assert len(norms) == len(set(norms)), "Cross-category duplicates should be removed"


# ============== PROMPT TESTS ==============

class TestPromptV11:

    def _mock_step1(self):
        return {
            "geo": {"city_or_region": "Dubai", "country": "UAE"},
            "goal": {"primary_goal": "leads"},
            "destination": {"type": "website"}
        }

    def _mock_step2(self):
        return {
            "classification": {"niche": "Bridal Makeup", "subcategory": "Beauty"},
            "offer": {
                "offer_catalog": [
                    {"name": "Bridal Makeup"},
                    {"name": "Hair Styling"},
                    {"name": "Facial"}
                ]
            },
            "brand_summary": {"name": "GlowStudio", "tagline": "Your glow, our art", "one_liner": "Premium bridal makeup"},
            "pricing": {"currency": "AED", "min": 200, "max": 1500, "avg": 600, "count": 10},
            "channels": {"social": [{"platform": "Instagram"}, {"platform": "TikTok"}], "messaging": []}
        }

    def test_prompt_includes_offer_catalog(self):
        ctx = build_input_context(self._mock_step1(), self._mock_step2(), None, None, None)
        prompt = build_prompt(ctx)
        assert "Bridal Makeup" in prompt
        assert "Hair Styling" in prompt
        assert "Facial" in prompt

    def test_prompt_includes_search_phrases(self):
        search_demand = {
            "top_10_queries": ["bridal makeup dubai", "wedding makeup near me"],
            "intent_buckets": {"price": ["makeup price dubai"]}
        }
        ctx = build_input_context(self._mock_step1(), self._mock_step2(), search_demand, None, None)
        prompt = build_prompt(ctx)
        assert "bridal makeup dubai" in prompt
        assert "wedding makeup near me" in prompt

    def test_prompt_no_search_shows_not_available(self):
        ctx = build_input_context(self._mock_step1(), self._mock_step2(), None, None, None)
        prompt = build_prompt(ctx)
        assert "Search Demand not run" in prompt

    def test_prompt_hard_rules(self):
        ctx = build_input_context(self._mock_step1(), self._mock_step2(), None, None, None)
        prompt = build_prompt(ctx)
        assert "STRICTLY FORBIDDEN" in prompt
        assert "Personas" in prompt
        assert "Decision speed" in prompt
        assert ">= 1 item from OFFER CATALOG" in prompt
        assert ">= 2 phrases from REAL SEARCH PHRASES" in prompt

    def test_prompt_no_personas_no_strategy(self):
        ctx = build_input_context(self._mock_step1(), self._mock_step2(), None, None, None)
        prompt = build_prompt(ctx)
        assert "persona" in prompt.lower()  # should be in forbidden section
        assert "capitalize" in prompt.lower()  # should be in forbidden section
        assert "leverage" in prompt.lower()  # should be in forbidden section

    def test_context_extraction(self):
        ctx = build_input_context(self._mock_step1(), self._mock_step2(), None, None, None)
        assert ctx["brand_name"] == "GlowStudio"
        assert ctx["city"] == "Dubai"
        assert "Bridal Makeup" in ctx["offer_catalog"]
        assert len(ctx["search_phrases"]) == 0  # no search demand


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
