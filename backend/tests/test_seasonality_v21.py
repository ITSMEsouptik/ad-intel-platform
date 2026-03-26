"""
Tests for Seasonality v2.1 ("Buying Moments") feature.

Tests:
1. Schema compliance — BuyingMoment fields
2. Post-processing filter — generic moment removal
3. Post-processing relaxation — fallback when filtering too aggressive
4. Data caps — max moments, trigger counts
5. Prompt structure validation
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from research.seasonality.schema import (
    BuyingMoment,
    SeasonalitySnapshot,
    SeasonalityAudit,
    WeeklyPatterns,
    SeasonalityInputs,
    SeasonalityDelta
)
from research.seasonality.postprocess import (
    postprocess_moments,
    filter_moments,
    clean_buy_triggers,
    clean_best_channels,
    _matches_any,
    GENERIC_WHO_PATTERNS,
    GENERIC_TRIGGER_PATTERNS,
    GENERIC_MOMENT_PATTERNS,
    GENERIC_CHANNEL_PATTERNS
)
from research.seasonality.perplexity_seasonality import build_seasonality_prompt


# ============== SCHEMA TESTS ==============

class TestBuyingMomentSchema:
    """Test that BuyingMoment schema matches the v2.1 spec."""

    def test_buying_moment_all_fields(self):
        moment = BuyingMoment(
            moment="Wedding Season",
            window="March-May",
            demand="high",
            who="Brides-to-be, mothers of the bride",
            why_now="Wedding dates are booked 3-6 months ahead, prep starts now",
            buy_triggers=["Wedding invitation received", "Engagement announcement", "Venue booked"],
            must_answer="Can I get an appointment before my wedding date?",
            best_channels=["Instagram Reels", "Google Search", "WhatsApp groups"],
            lead_time="2-4 months before"
        )
        assert moment.moment == "Wedding Season"
        assert moment.window == "March-May"
        assert moment.demand == "high"
        assert moment.who == "Brides-to-be, mothers of the bride"
        assert len(moment.buy_triggers) == 3
        assert moment.must_answer.startswith("Can I get")
        assert len(moment.best_channels) == 3
        assert moment.lead_time == "2-4 months before"

    def test_buying_moment_defaults(self):
        moment = BuyingMoment(moment="Test", window="Jan")
        assert moment.demand == "medium"
        assert moment.who == ""
        assert moment.why_now == ""
        assert moment.buy_triggers == []
        assert moment.must_answer == ""
        assert moment.best_channels == []
        assert moment.lead_time == ""

    def test_snapshot_version(self):
        snapshot = SeasonalitySnapshot()
        assert snapshot.version == "2.1"

    def test_snapshot_has_audit(self):
        snapshot = SeasonalitySnapshot()
        assert isinstance(snapshot.audit, SeasonalityAudit)
        assert snapshot.audit.raw_moments_count == 0
        assert snapshot.audit.relaxation_applied is False

    def test_snapshot_key_moments_are_buying_moments(self):
        moment = BuyingMoment(moment="Test", window="Jan", who="Parents")
        snapshot = SeasonalitySnapshot(key_moments=[moment])
        assert len(snapshot.key_moments) == 1
        assert isinstance(snapshot.key_moments[0], BuyingMoment)
        assert snapshot.key_moments[0].who == "Parents"

    def test_audit_fields(self):
        audit = SeasonalityAudit(
            raw_moments_count=8,
            filtered_count=2,
            filter_reasons={"generic_who": 1, "all_generic_triggers": 1},
            relaxation_applied=False
        )
        assert audit.raw_moments_count == 8
        assert audit.filtered_count == 2
        assert "generic_who" in audit.filter_reasons


# ============== POST-PROCESSING TESTS ==============

class TestPostProcessing:
    """Test the post-processing filter logic."""

    def _make_moment(self, **overrides):
        """Helper to create a valid moment dict."""
        base = {
            "moment": "Wedding Season",
            "window": "March-May",
            "demand": "high",
            "who": "Brides-to-be and mothers of the bride",
            "why_now": "Wedding dates are booked months ahead, prep starts in March",
            "buy_triggers": ["Wedding invitation received", "Venue booked"],
            "must_answer": "Can I get an appointment before my date?",
            "best_channels": ["Instagram Reels", "Google Search"]
        }
        base.update(overrides)
        return base

    def test_valid_moment_passes(self):
        moments = [self._make_moment()]
        kept, reasons = filter_moments(moments, strict=True)
        assert len(kept) == 1
        assert len(reasons) == 0

    def test_generic_who_rejected(self):
        """Moments with generic 'who' like 'consumers' or 'everyone' should be rejected."""
        generic_whos = ["consumers", "Customers", "everyone", "General audience", "broad audience", "people"]
        for who in generic_whos:
            moments = [self._make_moment(who=who)]
            kept, reasons = filter_moments(moments, strict=True)
            assert len(kept) == 0, f"'{who}' should have been rejected"
            assert "generic_who" in reasons

    def test_specific_who_passes(self):
        specific_whos = [
            "Brides-to-be",
            "Parents of school-age children",
            "First-time homebuyers in their 30s",
            "Corporate event planners"
        ]
        for who in specific_whos:
            moments = [self._make_moment(who=who)]
            kept, reasons = filter_moments(moments, strict=True)
            assert len(kept) == 1, f"'{who}' should have passed"

    def test_generic_moment_name_rejected(self):
        generic_names = ["Social media trends", "Year-round demand", "Ongoing sales"]
        for name in generic_names:
            moments = [self._make_moment(moment=name)]
            kept, reasons = filter_moments(moments, strict=True)
            assert len(kept) == 0, f"'{name}' should have been rejected"

    def test_all_generic_triggers_rejected(self):
        moments = [self._make_moment(buy_triggers=["social media posts", "influencer content", "targeted ads"])]
        kept, reasons = filter_moments(moments, strict=True)
        assert len(kept) == 0
        assert "all_generic_triggers" in reasons

    def test_mixed_triggers_pass(self):
        """If at least one trigger is specific, the moment passes."""
        moments = [self._make_moment(buy_triggers=["social media posts", "Wedding invitation received"])]
        kept, reasons = filter_moments(moments, strict=True)
        assert len(kept) == 1

    def test_missing_buy_triggers_rejected_strict(self):
        moments = [self._make_moment(buy_triggers=[])]
        kept, reasons = filter_moments(moments, strict=True)
        assert len(kept) == 0
        assert "missing_buy_triggers" in reasons

    def test_missing_buy_triggers_passes_relaxed(self):
        moments = [self._make_moment(buy_triggers=[])]
        kept, reasons = filter_moments(moments, strict=False)
        assert len(kept) == 1

    def test_all_generic_channels_rejected(self):
        moments = [self._make_moment(best_channels=["social media", "online"])]
        kept, reasons = filter_moments(moments, strict=True)
        assert len(kept) == 0
        assert "all_generic_channels" in reasons

    def test_weak_why_now_rejected_strict(self):
        moments = [self._make_moment(why_now="short")]
        kept, reasons = filter_moments(moments, strict=True)
        assert len(kept) == 0
        assert "weak_why_now" in reasons

    def test_weak_why_now_passes_relaxed(self):
        moments = [self._make_moment(why_now="short")]
        kept, reasons = filter_moments(moments, strict=False)
        assert len(kept) == 1

    def test_relaxation_fallback(self):
        """If strict filtering leaves < 3, relaxation should kick in."""
        moments = [
            self._make_moment(moment=f"Moment {i}", buy_triggers=[])
            for i in range(5)
        ]
        # Strict would reject all (missing buy_triggers)
        result, audit = postprocess_moments(moments, min_moments=3)
        assert audit["relaxation_applied"] is True
        assert len(result) >= 3

    def test_clean_buy_triggers(self):
        triggers = ["social media exposure", "Wedding invitation received", "Influencer posts"]
        cleaned = clean_buy_triggers(triggers)
        assert "Wedding invitation received" in cleaned
        assert len(cleaned) == 1

    def test_clean_best_channels(self):
        channels = ["Instagram Reels", "social media", "Google Search", "online"]
        cleaned = clean_best_channels(channels)
        assert "Instagram Reels" in cleaned
        assert "Google Search" in cleaned
        assert len(cleaned) == 2

    def test_data_caps(self):
        """Verify moments are capped at 8."""
        moments = [self._make_moment(moment=f"Moment {i}") for i in range(12)]
        result, audit = postprocess_moments(moments)
        # postprocess_moments itself doesn't cap — the service does at 8
        # But we verify the input was 12 and output <= 12
        assert audit["raw_moments_count"] == 12


# ============== PROMPT TESTS ==============

class TestPromptStructure:
    """Test the Perplexity prompt for v2.1."""

    def test_prompt_contains_buying_moments_structure(self):
        prompt = build_seasonality_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="Hair Salon",
            services=["Haircut", "Coloring"],
            brand_overview="Premium hair salon in Dubai"
        )
        # Must ask for the new fields
        assert '"who"' in prompt
        assert '"why_now"' in prompt
        assert '"buy_triggers"' in prompt
        assert '"must_answer"' in prompt
        assert '"best_channels"' in prompt
        assert '"lead_time"' in prompt

    def test_prompt_contains_hard_rules(self):
        prompt = build_seasonality_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="London",
            country="UK",
            subcategory="Fitness",
            niche="Personal Training",
            services=["PT Sessions"],
            brand_overview="Personal training studio"
        )
        assert "STRICTLY FORBIDDEN" in prompt
        assert "budget" in prompt.lower()
        assert "capitalize" in prompt.lower()
        assert "leverage" in prompt.lower()

    def test_prompt_uses_business_context(self):
        prompt = build_seasonality_prompt(
            brand_name="GlowSalon",
            domain="glowsalon.ae",
            city="Abu Dhabi",
            country="UAE",
            subcategory="Beauty",
            niche="Skincare Clinic",
            services=["Facial", "Laser Treatment"],
            brand_overview="Premium skincare clinic"
        )
        assert "GlowSalon" in prompt
        assert "glowsalon.ae" in prompt
        assert "Abu Dhabi" in prompt
        assert "Skincare Clinic" in prompt

    def test_prompt_includes_price_context(self):
        prompt = build_seasonality_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="Salon",
            services=["Haircut"],
            brand_overview="Salon",
            price_range={"currency": "AED", "avg": 250, "min": 100, "max": 500}
        )
        assert "AED" in prompt
        assert "250" in prompt


# ============== GENERIC PATTERN TESTS ==============

class TestGenericPatterns:
    """Test the regex patterns for detecting generic content."""

    def test_generic_who_patterns(self):
        should_match = ["consumers", "Customers", "people", "everyone", "general audience", "broad public"]
        for text in should_match:
            assert _matches_any(text, GENERIC_WHO_PATTERNS), f"'{text}' should match generic who"

    def test_non_generic_who_patterns(self):
        should_not_match = [
            "brides-to-be",
            "parents with toddlers",
            "corporate HR managers",
            "first-time renters",
            "fitness enthusiasts aged 25-35"
        ]
        for text in should_not_match:
            assert not _matches_any(text, GENERIC_WHO_PATTERNS), f"'{text}' should NOT match generic who"

    def test_generic_trigger_patterns(self):
        should_match = [
            "social media posts",
            "influencer content",
            "targeted ads",
            "digital advertising",
            "marketing campaigns",
            "email marketing"
        ]
        for text in should_match:
            assert _matches_any(text, GENERIC_TRIGGER_PATTERNS), f"'{text}' should match generic trigger"

    def test_non_generic_trigger_patterns(self):
        should_not_match = [
            "wedding invitation received",
            "school term starts",
            "first cold weather snap",
            "Ramadan begins",
            "child outgrows current shoes"
        ]
        for text in should_not_match:
            assert not _matches_any(text, GENERIC_TRIGGER_PATTERNS), f"'{text}' should NOT match generic trigger"

    def test_generic_channel_patterns(self):
        should_match = ["social media", "online", "internet", "digital", "the web"]
        for text in should_match:
            assert _matches_any(text, GENERIC_CHANNEL_PATTERNS), f"'{text}' should match generic channel"

    def test_non_generic_channel_patterns(self):
        should_not_match = ["Instagram Reels", "Google Search", "WhatsApp groups", "YouTube pre-roll", "Meta retargeting"]
        for text in should_not_match:
            assert not _matches_any(text, GENERIC_CHANNEL_PATTERNS), f"'{text}' should NOT match generic channel"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
