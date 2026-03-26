"""
Tests for P0 bug fixes:
1. Competitor relevance validation
2. Reviews retry mechanism
3. Ads brand name matching improvements
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# === Issue 1: Competitor Relevance Validation ===

def test_validate_competitor_relevance_filters_irrelevant():
    """Test that irrelevant competitors (like 'Reva' for a beauty brand) are filtered out."""
    from research.competitors.perplexity_competitors import validate_competitor_relevance

    competitors = [
        {
            "name": "Ruuby",
            "what_they_do": "On-demand beauty services at home",
            "positioning": "Premium beauty booking platform",
            "why_competitor": "Competes for at-home beauty clients",
            "strengths": ["beauty at home", "professional stylists"],
        },
        {
            "name": "Reva",
            "what_they_do": "Electric vehicles and sustainable transport",
            "positioning": "Leading EV manufacturer",
            "why_competitor": "Popular brand in the region",
            "strengths": ["electric cars", "sustainable technology"],
        },
    ]

    relevant, rejected = validate_competitor_relevance(
        competitors=competitors,
        brand_subcategory="beauty services",
        brand_niche="on-demand beauty at home",
        brand_services=["makeup", "hair styling", "nails"],
        brand_name="Instaglam",
    )

    assert len(relevant) == 1, f"Expected 1 relevant competitor, got {len(relevant)}"
    assert relevant[0]["name"] == "Ruuby"
    assert len(rejected) == 1
    assert rejected[0]["name"] == "Reva"


def test_validate_competitor_relevance_keeps_all_relevant():
    """Test that all relevant competitors pass the filter."""
    from research.competitors.perplexity_competitors import validate_competitor_relevance

    competitors = [
        {
            "name": "GlamSquad",
            "what_they_do": "At-home beauty services",
            "positioning": "Beauty on demand",
            "why_competitor": "Same market",
            "strengths": ["salon quality at home"],
        },
        {
            "name": "Priv",
            "what_they_do": "Mobile beauty and wellness services",
            "positioning": "Luxury at-home beauty",
            "why_competitor": "Premium beauty competitor",
            "strengths": ["luxury treatments"],
        },
    ]

    relevant, rejected = validate_competitor_relevance(
        competitors=competitors,
        brand_subcategory="beauty services",
        brand_niche="on-demand beauty",
        brand_services=["makeup", "hair", "nails"],
        brand_name="TestBrand",
    )

    assert len(relevant) == 2
    assert len(rejected) == 0


def test_validate_competitor_relevance_no_signals():
    """When no industry signals can be extracted, all competitors should pass."""
    from research.competitors.perplexity_competitors import validate_competitor_relevance

    competitors = [
        {"name": "CompA", "what_they_do": "Something generic", "positioning": "", "strengths": []},
    ]

    relevant, rejected = validate_competitor_relevance(
        competitors=competitors,
        brand_subcategory="",
        brand_niche="",
        brand_services=[],
        brand_name="TestBrand",
    )

    assert len(relevant) == 1
    assert len(rejected) == 0


def test_validate_competitor_rejects_same_brand():
    """Competitor with same name as brand should be rejected."""
    from research.competitors.perplexity_competitors import validate_competitor_relevance

    competitors = [
        {"name": "Instaglam", "what_they_do": "beauty services", "positioning": "beauty", "strengths": ["beauty"]},
    ]

    relevant, rejected = validate_competitor_relevance(
        competitors=competitors,
        brand_subcategory="beauty",
        brand_niche="beauty",
        brand_services=["beauty"],
        brand_name="Instaglam",
    )

    assert len(relevant) == 0
    assert len(rejected) == 1


# === Issue 3a: Ads Brand Name Matching ===

def test_brand_name_match_exact():
    """Exact match should work."""
    from research.ads_intel.service import AdsIntelService
    assert AdsIntelService._brand_name_match("Ruuby", "Ruuby") is True


def test_brand_name_match_case_insensitive():
    """Case insensitive matching."""
    from research.ads_intel.service import AdsIntelService
    assert AdsIntelService._brand_name_match("Ruuby", "ruuby") is True


def test_brand_name_match_with_suffix():
    """Competitor name appears as word within ad brand with suffix."""
    from research.ads_intel.service import AdsIntelService
    assert AdsIntelService._brand_name_match("Ruuby", "Ruuby London") is True
    assert AdsIntelService._brand_name_match("Ruuby", "The Ruuby") is True


def test_brand_name_match_rejects_unrelated():
    """Completely unrelated names should not match."""
    from research.ads_intel.service import AdsIntelService
    assert AdsIntelService._brand_name_match("Ruuby", "RubyRose") is False
    assert AdsIntelService._brand_name_match("Ruuby", "RandomBrand") is False


def test_brand_name_match_partial_overlap():
    """Names with partial overlap but not word-boundary match."""
    from research.ads_intel.service import AdsIntelService
    # "Glam" should NOT match "GlamSquad" (too short for word boundary match)
    # But "GlamSquad" contains "Glam" as prefix
    assert AdsIntelService._brand_name_match("GlamSquad", "GlamSquad") is True
    assert AdsIntelService._brand_name_match("Glam", "Glamorous") is False  # too different


def test_brand_name_match_special_chars():
    """Names with special characters should still match after normalization."""
    from research.ads_intel.service import AdsIntelService
    # After removing non-alphanumeric chars, names should match
    assert AdsIntelService._brand_name_match("Ruuby", "Ruuby.") is True
    assert AdsIntelService._brand_name_match("L'Oreal", "LOreal") is True


# === Issue 3b: Business context validation ===

def test_passes_business_context():
    """Ads with matching industry signals should pass."""
    from research.ads_intel.service import AdsIntelService
    ad = {"headline": "Book your beauty appointment today", "body_text": "Premium salon services"}
    signals = ["beauty", "salon"]
    assert AdsIntelService._passes_business_context(ad, signals) is True


def test_fails_business_context():
    """Ads without matching industry signals should fail."""
    from research.ads_intel.service import AdsIntelService
    ad = {"headline": "Buy electric vehicles", "body_text": "EV charging stations"}
    signals = ["beauty", "salon", "makeup"]
    assert AdsIntelService._passes_business_context(ad, signals) is False


def test_passes_business_context_no_signals():
    """When no signals are provided, all ads should pass."""
    from research.ads_intel.service import AdsIntelService
    ad = {"headline": "Anything"}
    assert AdsIntelService._passes_business_context(ad, []) is True
