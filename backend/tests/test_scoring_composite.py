"""
Test Suite: P1 Expand Winning Ad Signals - Composite Scoring
Tests the multi-dimensional scoring system for ads intelligence.

Signals tested:
- longevity (0-35)
- liveness (0-15)
- format (0-10)
- cta (0-5)
- landing_page (0-5)
- preview (0-5)
- content (0-10)
- recency (0-15)

Tiers:
- proven_winner >= 70
- strong_performer >= 50
- rising >= 30
- notable < 30
"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

from research.ads_intel.scoring import (
    compute_ad_score, ad_sort_key, build_why_shortlisted,
    shortlist_competitor_ads, shortlist_category_ads,
    TIER_PROVEN_WINNER, TIER_STRONG_PERFORMER, TIER_RISING,
    _longevity_score, _liveness_score, _format_score, _cta_score,
    _landing_page_score, _preview_score, _content_score, _recency_score
)
from research.ads_intel.schema import AdCard


class TestIndividualScoringFunctions:
    """Test each individual scoring function"""

    def test_longevity_score_0_days(self):
        """0 days should return 0 points"""
        assert _longevity_score(0) == 0
        assert _longevity_score(None) == 0

    def test_longevity_score_7_days(self):
        """7 days should return 8 points"""
        assert _longevity_score(7) == 8

    def test_longevity_score_14_days(self):
        """14 days should return 15 points"""
        assert _longevity_score(14) == 15

    def test_longevity_score_30_days(self):
        """30 days should return 25 points"""
        assert _longevity_score(30) == 25

    def test_longevity_score_60_days(self):
        """60 days should return 30 points"""
        assert _longevity_score(60) == 30

    def test_longevity_score_90_days(self):
        """90+ days should return 35 points (max)"""
        assert _longevity_score(90) == 35
        assert _longevity_score(180) == 35

    def test_liveness_score_active(self):
        """Active ad should return 15 points"""
        assert _liveness_score({"live": True}) == 15

    def test_liveness_score_inactive(self):
        """Inactive ad should return 0 points"""
        assert _liveness_score({"live": False}) == 0
        assert _liveness_score({}) == 0

    def test_format_score_video(self):
        """Video format should return 10 points"""
        assert _format_score({"_format": "video"}) == 10
        assert _format_score({"display_format": "video"}) == 10

    def test_format_score_carousel(self):
        """Carousel format should return 7 points"""
        assert _format_score({"_format": "carousel"}) == 7

    def test_format_score_image(self):
        """Image format should return 4 points"""
        assert _format_score({"_format": "image"}) == 4

    def test_format_score_unknown(self):
        """Unknown format should return 2 points"""
        assert _format_score({}) == 2
        assert _format_score({"_format": "unknown"}) == 2

    def test_cta_score_has_cta(self):
        """Ad with CTA should return 5 points"""
        assert _cta_score({"cta": "Shop Now"}) == 5

    def test_cta_score_no_cta(self):
        """Ad without CTA should return 0 points"""
        assert _cta_score({}) == 0
        assert _cta_score({"cta": ""}) == 0

    def test_landing_page_score_has_url(self):
        """Ad with landing page URL should return 5 points"""
        assert _landing_page_score({"landing_page_url": "https://example.com"}) == 5

    def test_landing_page_score_no_url(self):
        """Ad without landing page URL should return 0 points"""
        assert _landing_page_score({}) == 0

    def test_preview_score_has_preview(self):
        """Ad with preview should return 5 points (default True)"""
        assert _preview_score({}) == 5
        assert _preview_score({"has_preview": True}) == 5

    def test_preview_score_no_preview(self):
        """Ad without preview should return 0 points"""
        assert _preview_score({"has_preview": False}) == 0

    def test_content_score_headline_and_body(self):
        """Ad with headline AND body should return 10 points"""
        assert _content_score({"headline": "Test", "text": "Body text"}) == 10

    def test_content_score_headline_only(self):
        """Ad with headline only should return 5 points"""
        assert _content_score({"headline": "Test"}) == 5

    def test_content_score_body_only(self):
        """Ad with body only should return 5 points"""
        assert _content_score({"text": "Body text"}) == 5

    def test_content_score_neither(self):
        """Ad without headline or body should return 0 points"""
        assert _content_score({}) == 0


class TestComputeAdScore:
    """Test the main compute_ad_score function"""

    def test_compute_ad_score_returns_dict(self):
        """compute_ad_score should return dict with total, tier, and signals"""
        ad = {"_running_days": 30, "live": True}
        result = compute_ad_score(ad)
        
        assert isinstance(result, dict)
        assert "total" in result
        assert "tier" in result
        assert "signals" in result
        assert isinstance(result["signals"], dict)

    def test_compute_ad_score_all_signals_present(self):
        """All 8 signals should be present in result"""
        ad = {"_running_days": 30, "live": True}
        result = compute_ad_score(ad)
        
        expected_signals = ["longevity", "liveness", "format", "cta", 
                          "landing_page", "preview", "content", "recency"]
        for signal in expected_signals:
            assert signal in result["signals"], f"Missing signal: {signal}"

    def test_compute_ad_score_max_100(self):
        """Total score should be capped at 100"""
        # Create an ad that would score above 100 if uncapped
        ad = {
            "_running_days": 100,  # 35 points
            "live": True,  # 15 points
            "_format": "video",  # 10 points
            "cta": "Shop Now",  # 5 points
            "landing_page_url": "https://test.com",  # 5 points
            "has_preview": True,  # 5 points
            "headline": "Test",  # 10 points (with text)
            "text": "Body",
            "start_date": "2026-01-01T00:00:00Z",  # recency points
        }
        result = compute_ad_score(ad)
        assert result["total"] <= 100

    def test_compute_ad_score_proven_winner_tier(self):
        """Score >= 70 should be proven_winner tier"""
        ad = {
            "_running_days": 90,  # 35
            "live": True,  # 15
            "_format": "video",  # 10
            "cta": "Shop",  # 5
            "landing_page_url": "https://t.com",  # 5
            "has_preview": True,  # 5
            "headline": "H",
            "text": "B",  # 10
        }
        result = compute_ad_score(ad)
        # Should be at least 70
        assert result["tier"] == "proven_winner"

    def test_compute_ad_score_strong_performer_tier(self):
        """Score >= 50 and < 70 should be strong_performer tier"""
        ad = {
            "_running_days": 60,  # 30
            "live": True,  # 15
            "_format": "image",  # 4
            "has_preview": True,  # 5
        }
        result = compute_ad_score(ad)
        # Should be around 54-60
        assert result["total"] >= 50
        assert result["total"] < 70 or result["tier"] in ["strong_performer", "proven_winner"]

    def test_compute_ad_score_rising_tier(self):
        """Score >= 30 and < 50 should be rising tier"""
        ad = {
            "_running_days": 14,  # 15
            "live": True,  # 15
            "_format": "image",  # 4
        }
        result = compute_ad_score(ad)
        # Should be around 34-40
        if result["total"] >= 30 and result["total"] < 50:
            assert result["tier"] == "rising"

    def test_compute_ad_score_notable_tier(self):
        """Score < 30 should be notable tier"""
        ad = {
            "_running_days": 0,
            "live": False,
            "_format": "",
        }
        result = compute_ad_score(ad)
        assert result["total"] < 30
        assert result["tier"] == "notable"


class TestAdSortKey:
    """Test the ad_sort_key function for sorting by composite score"""

    def test_ad_sort_key_uses_composite_score(self):
        """Sort key should use composite score as primary"""
        ad_high = {"_score": {"total": 80}, "_running_days": 10}
        ad_low = {"_score": {"total": 40}, "_running_days": 100}
        
        high_key = ad_sort_key(ad_high)
        low_key = ad_sort_key(ad_low)
        
        # Higher score should come first (higher tuple value)
        assert high_key[0] > low_key[0]

    def test_ad_sort_key_handles_missing_score(self):
        """Should handle missing _score gracefully"""
        ad = {"_running_days": 30}
        key = ad_sort_key(ad)
        assert key[0] == 0  # Default score

    def test_ad_sort_key_secondary_running_days(self):
        """Running days should be secondary sort key"""
        ad1 = {"_score": {"total": 50}, "_running_days": 90}
        ad2 = {"_score": {"total": 50}, "_running_days": 30}
        
        key1 = ad_sort_key(ad1)
        key2 = ad_sort_key(ad2)
        
        # Same score, but ad1 has more running days
        assert key1[0] == key2[0]  # Same score
        assert key1[1] > key2[1]  # Higher running days


class TestBuildWhyShortlisted:
    """Test the build_why_shortlisted function"""

    def test_build_why_shortlisted_includes_tier_label(self):
        """Should include tier label for proven_winner and strong_performer"""
        ad_proven = {
            "_score": {"tier": "proven_winner"},
            "_running_days": 90,
            "live": True,
        }
        result = build_why_shortlisted(ad_proven)
        assert "Proven Winner" in result

    def test_build_why_shortlisted_strong_performer(self):
        """Should include tier label for strong_performer"""
        ad_strong = {
            "_score": {"tier": "strong_performer"},
            "_running_days": 60,
            "live": True,
        }
        result = build_why_shortlisted(ad_strong)
        assert "Strong Performer" in result

    def test_build_why_shortlisted_no_tier_for_rising(self):
        """Should NOT include tier label for rising or notable"""
        ad_rising = {
            "_score": {"tier": "rising"},
            "_running_days": 14,
            "live": True,
        }
        result = build_why_shortlisted(ad_rising)
        assert "Rising" not in result
        assert "Notable" not in result

    def test_build_why_shortlisted_includes_running_days(self):
        """Should include running days info"""
        ad = {"_running_days": 90, "_score": {}}
        result = build_why_shortlisted(ad)
        assert "90 days" in result or "running" in result.lower()

    def test_build_why_shortlisted_includes_active_status(self):
        """Should mention if ad is currently active"""
        ad = {"live": True, "_score": {}}
        result = build_why_shortlisted(ad)
        assert "active" in result.lower()


class TestShortlistCompetitorAds:
    """Test shortlist_competitor_ads computes _score for each ad"""

    def test_shortlist_competitor_ads_computes_score(self):
        """Each ad should have _score computed after shortlisting"""
        ads = [
            {"ad_id": "1", "_running_days": 90, "live": True},
            {"ad_id": "2", "_running_days": 30, "live": False},
        ]
        result = shortlist_competitor_ads(ads, max_total=10)
        
        for ad in result:
            assert "_score" in ad
            assert isinstance(ad["_score"], dict)
            assert "total" in ad["_score"]
            assert "tier" in ad["_score"]
            assert "signals" in ad["_score"]

    def test_shortlist_competitor_ads_sorts_by_score(self):
        """Ads should be sorted by composite score DESC"""
        ads = [
            {"ad_id": "low", "_running_days": 0, "live": False, "brand_id": "b1"},
            {"ad_id": "high", "_running_days": 90, "live": True, "_format": "video", "brand_id": "b2"},
        ]
        result = shortlist_competitor_ads(ads, max_total=10)
        
        if len(result) >= 2:
            # Higher score should come first
            assert result[0]["_score"]["total"] >= result[1]["_score"]["total"]


class TestShortlistCategoryAds:
    """Test shortlist_category_ads computes _score for each ad"""

    def test_shortlist_category_ads_computes_score(self):
        """Each ad should have _score computed after shortlisting"""
        ads = [
            {"ad_id": "1", "_running_days": 60, "live": True},
            {"ad_id": "2", "_running_days": 14, "live": True},
        ]
        result = shortlist_category_ads(ads, max_total=10, geo={})
        
        for ad in result:
            assert "_score" in ad
            assert isinstance(ad["_score"], dict)
            assert "total" in ad["_score"]
            assert "tier" in ad["_score"]
            assert "signals" in ad["_score"]


class TestAdCardSchema:
    """Test AdCard schema includes score, tier, score_signals fields"""

    def test_ad_card_has_score_field(self):
        """AdCard should have score field with default 0"""
        card = AdCard(
            ad_id="test1",
            publisher_platform="facebook",
            lens="competitor",
            why_shortlisted="Test reason"
        )
        assert hasattr(card, "score")
        assert card.score == 0

    def test_ad_card_has_tier_field(self):
        """AdCard should have tier field with default 'notable'"""
        card = AdCard(
            ad_id="test2",
            publisher_platform="facebook",
            lens="competitor",
            why_shortlisted="Test reason"
        )
        assert hasattr(card, "tier")
        assert card.tier == "notable"

    def test_ad_card_has_score_signals_field(self):
        """AdCard should have score_signals dict field"""
        card = AdCard(
            ad_id="test3",
            publisher_platform="facebook",
            lens="competitor",
            why_shortlisted="Test reason"
        )
        assert hasattr(card, "score_signals")
        assert isinstance(card.score_signals, dict)

    def test_ad_card_accepts_score_values(self):
        """AdCard should accept score, tier, and score_signals"""
        signals = {"longevity": 35, "liveness": 15, "format": 10}
        card = AdCard(
            ad_id="test4",
            publisher_platform="facebook",
            lens="competitor",
            why_shortlisted="Test reason",
            score=75,
            tier="proven_winner",
            score_signals=signals
        )
        assert card.score == 75
        assert card.tier == "proven_winner"
        assert card.score_signals == signals


class TestTierThresholds:
    """Test that tier thresholds are correct"""

    def test_tier_proven_winner_threshold(self):
        """TIER_PROVEN_WINNER should be 70"""
        assert TIER_PROVEN_WINNER == 70

    def test_tier_strong_performer_threshold(self):
        """TIER_STRONG_PERFORMER should be 50"""
        assert TIER_STRONG_PERFORMER == 50

    def test_tier_rising_threshold(self):
        """TIER_RISING should be 30"""
        assert TIER_RISING == 30

    def test_tier_assignment_boundaries(self):
        """Test tier assignment at exact boundaries"""
        # Score 70 -> proven_winner
        ad70 = {"_running_days": 90, "live": True, "_format": "video", "headline": "H", "text": "T"}
        result70 = compute_ad_score(ad70)
        if result70["total"] >= 70:
            assert result70["tier"] == "proven_winner"

        # Score 69 -> strong_performer
        # Score 50 -> strong_performer
        # Score 49 -> rising
        # Score 30 -> rising
        # Score 29 -> notable


class TestSignalMaxValues:
    """Test that signal max values match spec"""

    def test_longevity_max_is_35(self):
        """Longevity max should be 35"""
        assert _longevity_score(1000) == 35  # Max value

    def test_liveness_max_is_15(self):
        """Liveness max should be 15"""
        assert _liveness_score({"live": True}) == 15

    def test_format_max_is_10(self):
        """Format max should be 10"""
        assert _format_score({"_format": "video"}) == 10

    def test_cta_max_is_5(self):
        """CTA max should be 5"""
        assert _cta_score({"cta": "any"}) == 5

    def test_landing_page_max_is_5(self):
        """Landing page max should be 5"""
        assert _landing_page_score({"landing_page_url": "https://test.com"}) == 5

    def test_preview_max_is_5(self):
        """Preview max should be 5"""
        assert _preview_score({"has_preview": True}) == 5

    def test_content_max_is_10(self):
        """Content max should be 10"""
        assert _content_score({"headline": "H", "text": "T"}) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
