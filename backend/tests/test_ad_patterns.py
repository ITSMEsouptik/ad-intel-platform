"""
Test Suite: P1 Top Performing Patterns - compute_ad_patterns() Function
Tests pattern detection among highest-scored ads in the Ads Intelligence module.

Pattern types tested:
- format: Detected when >= 50% of top ads share a format
- platform: Detected when >= 60% of top ads share a platform
- longevity: Detected when average running days >= 30
- liveness: Detected when active_count >= 2 AND active_pct >= 40%
- cta: Detected when cta_count >= 2 AND cta_pct >= 60%
- content: Detected when rich_count >= 2 AND rich_pct >= 50%
- source: Detected when top_n >= 4 and one source dominates (>= 3 ads)

Each pattern returns dict with: type, text, detail keys
Max 6 patterns returned
Returns empty list for fewer than 3 ads
"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

from research.ads_intel.scoring import compute_ad_patterns
from research.ads_intel.schema import AdsIntelSnapshot


class TestComputeAdPatternsBasics:
    """Basic tests for compute_ad_patterns function structure"""

    def test_returns_list(self):
        """compute_ad_patterns should return a list"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        assert isinstance(result, list)

    def test_pattern_dict_has_required_keys(self):
        """Each pattern should have type, text, detail keys"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        for pattern in result:
            assert "type" in pattern, f"Pattern missing 'type' key: {pattern}"
            assert "text" in pattern, f"Pattern missing 'text' key: {pattern}"
            assert "detail" in pattern, f"Pattern missing 'detail' key: {pattern}"

    def test_pattern_values_are_strings(self):
        """Pattern type, text, detail should all be strings"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        for pattern in result:
            assert isinstance(pattern["type"], str), f"type is not str: {type(pattern['type'])}"
            assert isinstance(pattern["text"], str), f"text is not str: {type(pattern['text'])}"
            assert isinstance(pattern["detail"], str), f"detail is not str: {type(pattern['detail'])}"


class TestEmptyListConditions:
    """Test that compute_ad_patterns returns empty list for edge cases"""

    def test_empty_list_for_none_ads(self):
        """Should return empty list for None input"""
        result = compute_ad_patterns(None)
        assert result == []

    def test_empty_list_for_empty_ads(self):
        """Should return empty list for empty ads list"""
        result = compute_ad_patterns([])
        assert result == []

    def test_empty_list_for_one_ad(self):
        """Should return empty list for only 1 ad"""
        ads = [{"_score": {"tier": "proven_winner", "total": 80}, "_format": "video"}]
        result = compute_ad_patterns(ads)
        assert result == []

    def test_empty_list_for_two_ads(self):
        """Should return empty list for only 2 ads"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video"},
        ]
        result = compute_ad_patterns(ads)
        assert result == []

    def test_returns_patterns_for_three_ads(self):
        """Should return patterns for 3+ ads"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        # Should return at least the format pattern since all 3 are video (100% >= 50%)
        assert len(result) >= 1


class TestFormatDominancePattern:
    """Test format pattern detection when >= 50% of top ads share a format"""

    def test_detects_video_dominance_at_50_percent(self):
        """Should detect format when >= 50% share video format"""
        # 3 video out of 4 = 75%
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        format_patterns = [p for p in result if p["type"] == "format"]
        assert len(format_patterns) == 1
        assert "video" in format_patterns[0]["text"].lower() or "Video" in format_patterns[0]["text"]

    def test_detects_carousel_dominance(self):
        """Should detect carousel format dominance"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "carousel", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "carousel", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        format_patterns = [p for p in result if p["type"] == "format"]
        # 2/3 = 67% >= 50%
        assert len(format_patterns) == 1
        assert "carousel" in format_patterns[0]["text"].lower() or "Carousel" in format_patterns[0]["text"]

    def test_detects_image_dominance(self):
        """Should detect image format dominance"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "image", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "image", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        format_patterns = [p for p in result if p["type"] == "format"]
        # 3/3 = 100% >= 50%
        assert len(format_patterns) == 1
        assert "image" in format_patterns[0]["text"].lower() or "Image" in format_patterns[0]["text"]

    def test_no_format_pattern_below_50_percent(self):
        """Should NOT detect format when < 50%"""
        # 1/3 = 33% < 50%
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "carousel", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        format_patterns = [p for p in result if p["type"] == "format"]
        assert len(format_patterns) == 0


class TestPlatformDominancePattern:
    """Test platform pattern detection when >= 60% of top ads share a platform"""

    def test_detects_facebook_dominance_at_60_percent(self):
        """Should detect platform when >= 60%"""
        # 4/5 = 80% >= 60%
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "_format": "image", "_platform": "facebook"},
            {"_score": {"tier": "rising", "total": 35}, "_format": "image", "_platform": "instagram"},
        ]
        result = compute_ad_patterns(ads)
        
        platform_patterns = [p for p in result if p["type"] == "platform"]
        assert len(platform_patterns) == 1
        assert "facebook" in platform_patterns[0]["text"].lower() or "Facebook" in platform_patterns[0]["text"]

    def test_detects_instagram_dominance(self):
        """Should detect Instagram platform dominance"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "instagram"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "instagram"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "instagram"},
        ]
        result = compute_ad_patterns(ads)
        
        platform_patterns = [p for p in result if p["type"] == "platform"]
        # 3/3 = 100% >= 60%
        assert len(platform_patterns) == 1
        assert "instagram" in platform_patterns[0]["text"].lower() or "Instagram" in platform_patterns[0]["text"]

    def test_no_platform_pattern_below_60_percent(self):
        """Should NOT detect platform when < 60%"""
        # 2/4 = 50% < 60%
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_format": "video", "_platform": "instagram"},
            {"_score": {"tier": "strong_performer", "total": 55}, "_format": "image", "_platform": "instagram"},
        ]
        result = compute_ad_patterns(ads)
        
        platform_patterns = [p for p in result if p["type"] == "platform"]
        assert len(platform_patterns) == 0


class TestLongevityPattern:
    """Test longevity pattern detection when avg days >= 30"""

    def test_detects_longevity_at_30_days_avg(self):
        """Should detect longevity when avg running days >= 30"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_running_days": 45, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_running_days": 30, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_running_days": 35, "_format": "video", "_platform": "facebook"},
        ]
        # avg = (45+30+35)/3 = 36.67 >= 30
        result = compute_ad_patterns(ads)
        
        longevity_patterns = [p for p in result if p["type"] == "longevity"]
        assert len(longevity_patterns) == 1
        assert "days" in longevity_patterns[0]["text"].lower()

    def test_no_longevity_below_30_days_avg(self):
        """Should NOT detect longevity when avg < 30"""
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "_running_days": 10, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "_running_days": 15, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "_running_days": 20, "_format": "video", "_platform": "facebook"},
        ]
        # avg = (10+15+20)/3 = 15 < 30
        result = compute_ad_patterns(ads)
        
        longevity_patterns = [p for p in result if p["type"] == "longevity"]
        assert len(longevity_patterns) == 0


class TestLivenessPattern:
    """Test liveness pattern detection when active_count >= 2 AND active_pct >= 40%"""

    def test_detects_liveness_pattern(self):
        """Should detect liveness when active_count >= 2 AND active_pct >= 40%"""
        # 3/4 = 75% active
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "live": True, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "live": True, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "live": True, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "rising", "total": 35}, "live": False, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        liveness_patterns = [p for p in result if p["type"] == "liveness"]
        assert len(liveness_patterns) == 1
        assert "active" in liveness_patterns[0]["text"].lower()

    def test_no_liveness_with_only_one_active(self):
        """Should NOT detect liveness when active_count < 2"""
        # 1/4 = 25% active, active_count = 1
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "live": True, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "live": False, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "live": False, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "rising", "total": 35}, "live": False, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        liveness_patterns = [p for p in result if p["type"] == "liveness"]
        assert len(liveness_patterns) == 0

    def test_no_liveness_below_40_percent(self):
        """Should NOT detect liveness when active_pct < 40%"""
        # Top ads are proven_winner + strong_performer = 6 ads
        # 2/6 = 33% < 40%, even though active_count = 2
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "live": True, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "live": True, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "live": False, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 58}, "live": False, "_format": "image", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "live": False, "_format": "image", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 52}, "live": False, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        liveness_patterns = [p for p in result if p["type"] == "liveness"]
        assert len(liveness_patterns) == 0


class TestCTAPattern:
    """Test CTA pattern detection when cta_count >= 2 AND cta_pct >= 60%"""

    def test_detects_cta_pattern(self):
        """Should detect CTA when cta_count >= 2 AND cta_pct >= 60%"""
        # 3/4 = 75% have CTA
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "cta": "Shop Now", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "cta": "Learn More", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "cta": "Sign Up", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "rising", "total": 35}, "cta": "", "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        cta_patterns = [p for p in result if p["type"] == "cta"]
        assert len(cta_patterns) == 1
        assert "cta" in cta_patterns[0]["text"].lower()

    def test_no_cta_with_only_one_cta(self):
        """Should NOT detect CTA when cta_count < 2"""
        # 1/3 = 33%, cta_count = 1
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "cta": "Shop Now", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "cta": "", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "cta": None, "_format": "video", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        cta_patterns = [p for p in result if p["type"] == "cta"]
        assert len(cta_patterns) == 0

    def test_no_cta_below_60_percent(self):
        """Should NOT detect CTA when cta_pct < 60%"""
        # Top ads = 4 (all proven_winner/strong_performer)
        # 2/4 = 50% < 60%, cta_count = 2
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "cta": "Shop Now", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "cta": "Learn More", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "cta": "", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "cta": None, "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        cta_patterns = [p for p in result if p["type"] == "cta"]
        assert len(cta_patterns) == 0


class TestContentRichnessPattern:
    """Test content pattern detection when rich_count >= 2 AND rich_pct >= 50%"""

    def test_detects_content_richness(self):
        """Should detect content when rich_count >= 2 AND rich_pct >= 50%"""
        # 3/4 = 75% have both headline + text
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "headline": "Test H1", "text": "Body 1", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "headline": "Test H2", "text": "Body 2", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "headline": "Test H3", "text": "Body 3", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "rising", "total": 35}, "headline": "", "text": "", "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        content_patterns = [p for p in result if p["type"] == "content"]
        assert len(content_patterns) == 1
        assert "headline" in content_patterns[0]["text"].lower() or "body" in content_patterns[0]["text"].lower() or "copy" in content_patterns[0]["text"].lower()

    def test_no_content_with_only_one_rich(self):
        """Should NOT detect content when rich_count < 2"""
        # 1/3 = 33%, rich_count = 1
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "headline": "Test", "text": "Body", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "headline": "", "text": "Only body", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "headline": "Only headline", "text": "", "_format": "video", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        content_patterns = [p for p in result if p["type"] == "content"]
        assert len(content_patterns) == 0

    def test_no_content_below_50_percent(self):
        """Should NOT detect content when rich_pct < 50%"""
        # Top ads = 5 (all proven_winner/strong_performer)
        # 2/5 = 40% < 50%, rich_count = 2
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "headline": "Test", "text": "Body", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "headline": "Test2", "text": "Body2", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "headline": "", "text": "", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "headline": "", "text": "", "_format": "image", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 52}, "headline": "", "text": "", "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        content_patterns = [p for p in result if p["type"] == "content"]
        assert len(content_patterns) == 0


class TestSourcePattern:
    """Test source pattern detection when top_n >= 4 and one source dominates"""

    def test_detects_competitor_source_dominance(self):
        """Should detect competitor source when top_n >= 4 and competitor >= 3"""
        # Top ads = 4 (all proven_winner/strong_performer), 3 competitor, 1 category
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "lens": "category", "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        source_patterns = [p for p in result if p["type"] == "source"]
        assert len(source_patterns) == 1
        assert "competitor" in source_patterns[0]["text"].lower()

    def test_detects_category_source_dominance(self):
        """Should detect category source when top_n >= 4 and category >= 3"""
        # Top ads = 4 (all proven_winner/strong_performer), 1 competitor, 3 category
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "lens": "category", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "lens": "category", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "lens": "category", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "lens": "competitor", "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        source_patterns = [p for p in result if p["type"] == "source"]
        assert len(source_patterns) == 1
        assert "category" in source_patterns[0]["text"].lower() or "trend" in source_patterns[0]["text"].lower()

    def test_no_source_pattern_with_less_than_4_ads(self):
        """Should NOT detect source when top_n < 4"""
        # 3 ads
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        source_patterns = [p for p in result if p["type"] == "source"]
        assert len(source_patterns) == 0

    def test_no_source_pattern_when_neither_dominates(self):
        """Should NOT detect source when neither source has >= 3"""
        # 4 ads, 2 competitor, 2 category
        ads = [
            {"_score": {"tier": "proven_winner", "total": 80}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "proven_winner", "total": 75}, "lens": "competitor", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 60}, "lens": "category", "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "rising", "total": 35}, "lens": "category", "_format": "image", "_platform": "facebook"},
        ]
        result = compute_ad_patterns(ads)
        
        source_patterns = [p for p in result if p["type"] == "source"]
        assert len(source_patterns) == 0


class TestMaxPatternsLimit:
    """Test that max 6 patterns are returned"""

    def test_max_6_patterns_returned(self):
        """Should return max 6 patterns even if more could be detected"""
        # Create ads that would trigger all 7 pattern types
        ads = [
            {
                "_score": {"tier": "proven_winner", "total": 85},
                "_format": "video",  # format
                "_platform": "facebook",  # platform
                "_running_days": 60,  # longevity
                "live": True,  # liveness
                "cta": "Shop Now",  # cta
                "headline": "Test",  # content
                "text": "Body",
                "lens": "competitor",  # source
            },
            {
                "_score": {"tier": "proven_winner", "total": 80},
                "_format": "video",
                "_platform": "facebook",
                "_running_days": 50,
                "live": True,
                "cta": "Learn More",
                "headline": "Test2",
                "text": "Body2",
                "lens": "competitor",
            },
            {
                "_score": {"tier": "strong_performer", "total": 70},
                "_format": "video",
                "_platform": "facebook",
                "_running_days": 40,
                "live": True,
                "cta": "Sign Up",
                "headline": "Test3",
                "text": "Body3",
                "lens": "competitor",
            },
            {
                "_score": {"tier": "rising", "total": 45},
                "_format": "video",
                "_platform": "facebook",
                "_running_days": 30,
                "live": True,
                "cta": "Get Started",
                "headline": "Test4",
                "text": "Body4",
                "lens": "category",
            },
        ]
        result = compute_ad_patterns(ads)
        
        # Should not exceed 6 patterns
        assert len(result) <= 6


class TestTopAdFiltering:
    """Test that pattern detection uses proven_winner and strong_performer ads"""

    def test_uses_top_tier_ads_for_patterns(self):
        """Should prioritize proven_winner and strong_performer ads"""
        # Mix of tiers - pattern should be based on top 2 ads (proven_winner, strong_performer)
        ads = [
            {"_score": {"tier": "proven_winner", "total": 85}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "strong_performer", "total": 55}, "_format": "video", "_platform": "facebook"},
            {"_score": {"tier": "rising", "total": 40}, "_format": "image", "_platform": "instagram"},
            {"_score": {"tier": "notable", "total": 20}, "_format": "image", "_platform": "instagram"},
        ]
        result = compute_ad_patterns(ads)
        
        # Format pattern should be detected from top ads (both video)
        format_patterns = [p for p in result if p["type"] == "format"]
        assert len(format_patterns) >= 1


class TestSchemaIntegration:
    """Test AdsIntelSnapshot.patterns field"""

    def test_snapshot_has_patterns_field(self):
        """AdsIntelSnapshot should have patterns field"""
        snapshot = AdsIntelSnapshot()
        assert hasattr(snapshot, "patterns")

    def test_snapshot_patterns_is_list(self):
        """patterns field should be a list"""
        snapshot = AdsIntelSnapshot()
        assert isinstance(snapshot.patterns, list)

    def test_snapshot_patterns_default_empty(self):
        """patterns field should default to empty list"""
        snapshot = AdsIntelSnapshot()
        assert snapshot.patterns == []

    def test_snapshot_accepts_patterns(self):
        """AdsIntelSnapshot should accept patterns list"""
        patterns = [
            {"type": "format", "text": "Video ads dominate", "detail": "3/4 use video"},
            {"type": "platform", "text": "Facebook leads", "detail": "80% on Facebook"},
        ]
        snapshot = AdsIntelSnapshot(patterns=patterns)
        assert len(snapshot.patterns) == 2
        assert snapshot.patterns[0]["type"] == "format"

    def test_snapshot_patterns_type_annotation(self):
        """patterns field should be List[Dict[str, str]]"""
        snapshot = AdsIntelSnapshot(patterns=[{"type": "test", "text": "test", "detail": "test"}])
        assert isinstance(snapshot.patterns, list)
        assert isinstance(snapshot.patterns[0], dict)


class TestPatternTypes:
    """Test all 7 pattern types are recognized"""

    def test_all_pattern_types_are_strings(self):
        """Pattern types should be valid strings"""
        valid_types = {"format", "platform", "longevity", "liveness", "cta", "content", "source"}
        
        # Create comprehensive ad set
        ads = [
            {
                "_score": {"tier": "proven_winner", "total": 85},
                "_format": "video",
                "_platform": "facebook",
                "_running_days": 60,
                "live": True,
                "cta": "Shop Now",
                "headline": "Test",
                "text": "Body",
                "lens": "competitor",
            },
            {
                "_score": {"tier": "proven_winner", "total": 80},
                "_format": "video",
                "_platform": "facebook",
                "_running_days": 50,
                "live": True,
                "cta": "Learn",
                "headline": "Test2",
                "text": "Body2",
                "lens": "competitor",
            },
            {
                "_score": {"tier": "strong_performer", "total": 60},
                "_format": "video",
                "_platform": "facebook",
                "_running_days": 40,
                "live": True,
                "cta": "Sign Up",
                "headline": "Test3",
                "text": "Body3",
                "lens": "competitor",
            },
            {
                "_score": {"tier": "rising", "total": 35},
                "_format": "video",
                "_platform": "facebook",
                "_running_days": 30,
                "live": False,
                "cta": "",
                "headline": "",
                "text": "",
                "lens": "category",
            },
        ]
        result = compute_ad_patterns(ads)
        
        for pattern in result:
            assert pattern["type"] in valid_types, f"Unknown pattern type: {pattern['type']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
