"""
Geo-Relevance Filter Tests for Ads Intelligence
Tests the multi-signal geo detection in scoring.py:
1. URL TLD country mapping
2. URL path/query country patterns (UTM params, store=us, etc.)
3. US state name detection
4. Country name detection
5. Region-to-country mapping

Campaign: Dubai, UAE beauty salon
Expected behavior:
- Reject ads from clearly different countries (USA, India, UK, Australia, Singapore)
- Keep ads matching UAE geography
- Keep neutral ads (no geo signal, .com domain) with score 0.5
"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

from research.ads_intel.scoring import (
    compute_geo_relevance,
    _detect_country_from_url,
    _detect_country_from_text,
    _normalize_country,
)

# Dubai UAE campaign geo context
DUBAI_UAE_GEO = {"city": "dubai", "country": "United Arab Emirates"}


class TestCountryNormalization:
    """Test country name normalization"""
    
    def test_normalize_uae_variants(self):
        """UAE variants should normalize to 'uae'"""
        assert _normalize_country("UAE") == "uae"
        assert _normalize_country("United Arab Emirates") == "uae"
        assert _normalize_country("united arab emirates") == "uae"
        assert _normalize_country("Emirates") == "uae"
        print("✓ UAE normalization works correctly")
    
    def test_normalize_usa_variants(self):
        """USA variants should normalize to 'usa'"""
        assert _normalize_country("USA") == "usa"
        assert _normalize_country("United States") == "usa"
        assert _normalize_country("America") == "usa"
        assert _normalize_country("U.S.") == "usa"
        print("✓ USA normalization works correctly")
    
    def test_normalize_uk_variants(self):
        """UK variants should normalize to 'united kingdom'"""
        assert _normalize_country("UK") == "united kingdom"
        assert _normalize_country("United Kingdom") == "united kingdom"
        assert _normalize_country("Britain") == "united kingdom"
        assert _normalize_country("England") == "united kingdom"
        print("✓ UK normalization works correctly")


class TestURLCountryDetection:
    """Test country detection from URL TLD and path patterns"""
    
    def test_detect_ae_tld(self):
        """UAE TLD .ae should be detected"""
        assert _detect_country_from_url("https://example.ae/page") == "uae"
        assert _detect_country_from_url("https://shop.co.ae/beauty") == "uae"
        print("✓ .ae TLD detected as UAE")
    
    def test_detect_us_tld_patterns(self):
        """US country code patterns in URL should be detected"""
        # UTM params with _US_
        assert _detect_country_from_url("https://example.com?utm_campaign=beauty_US_2024") == "usa"
        # /us/ path
        assert _detect_country_from_url("https://example.com/us/shop") == "usa"
        # store=us param
        assert _detect_country_from_url("https://example.com?store=us") == "usa"
        # country=us param
        assert _detect_country_from_url("https://example.com?country=us") == "usa"
        print("✓ US URL patterns detected correctly")
    
    def test_detect_uk_tld(self):
        """UK TLD .co.uk should be detected"""
        assert _detect_country_from_url("https://example.co.uk/shop") == "united kingdom"
        assert _detect_country_from_url("https://shop.uk/beauty") == "united kingdom"
        print("✓ .co.uk/.uk TLD detected as UK")
    
    def test_detect_india_tld(self):
        """India TLDs should be detected"""
        assert _detect_country_from_url("https://example.in/shop") == "india"
        assert _detect_country_from_url("https://shop.co.in/beauty") == "india"
        print("✓ .in/.co.in TLD detected as India")
    
    def test_detect_australia_tld(self):
        """Australia TLDs should be detected"""
        assert _detect_country_from_url("https://example.com.au/shop") == "australia"
        assert _detect_country_from_url("https://shop.au/beauty") == "australia"
        print("✓ .com.au/.au TLD detected as Australia")
    
    def test_neutral_com_domain(self):
        """Generic .com domain should return None (no geo signal)"""
        assert _detect_country_from_url("https://example.com/shop") is None
        assert _detect_country_from_url("https://beautysalon.com/services") is None
        print("✓ .com domains return None (neutral)")
    
    def test_empty_or_invalid_url(self):
        """Empty or invalid URLs should return None"""
        assert _detect_country_from_url("") is None
        assert _detect_country_from_url(None) is None
        print("✓ Empty/invalid URLs return None")


class TestTextCountryDetection:
    """Test country detection from ad text"""
    
    def test_detect_us_state_full_name(self):
        """US state full names should detect USA"""
        assert _detect_country_from_text("Beauty services in California") == "usa"
        assert _detect_country_from_text("Visit our salon in New York") == "usa"
        assert _detect_country_from_text("Located in Moreno Valley, California") == "usa"
        assert _detect_country_from_text("Serving Texas and Florida") == "usa"
        print("✓ US state full names detected correctly")
    
    def test_detect_us_state_abbreviation_with_comma(self):
        """US state abbreviations with comma pattern should detect USA"""
        # Pattern: "City, CA" or "City, NY"
        assert _detect_country_from_text("Located in San Diego, CA") == "usa"
        assert _detect_country_from_text("Visit us at 123 Main St, Los Angeles, CA 90001") == "usa"
        assert _detect_country_from_text("Moreno Valley, CA") == "usa"
        print("✓ US state abbreviation comma patterns detected")
    
    def test_detect_uk_regions(self):
        """UK regions/counties should detect UK"""
        assert _detect_country_from_text("Beauty salon in London") == "united kingdom"
        assert _detect_country_from_text("Serving Surrey and Sussex") == "united kingdom"
        assert _detect_country_from_text("Manchester beauty services") == "united kingdom"
        print("✓ UK regions detected correctly")
    
    def test_detect_indian_states_cities(self):
        """Indian states/cities should detect India"""
        assert _detect_country_from_text("Salon in Mumbai") == "india"
        assert _detect_country_from_text("Beauty services in Bangalore") == "india"
        assert _detect_country_from_text("Located in Maharashtra") == "india"
        assert _detect_country_from_text("Hyderabad beauty parlor") == "india"
        print("✓ Indian states/cities detected correctly")
    
    def test_detect_australian_states_cities(self):
        """Australian states/cities should detect Australia"""
        assert _detect_country_from_text("Beauty salon in Sydney") == "australia"
        assert _detect_country_from_text("Serving Melbourne area") == "australia"
        assert _detect_country_from_text("Queensland beauty services") == "australia"
        print("✓ Australian states/cities detected correctly")
    
    def test_detect_uae_cities(self):
        """UAE cities should detect UAE"""
        assert _detect_country_from_text("Beauty salon in Dubai") == "uae"
        assert _detect_country_from_text("Abu Dhabi beauty services") == "uae"
        assert _detect_country_from_text("Serving Sharjah area") == "uae"
        print("✓ UAE cities detected correctly")
    
    def test_detect_us_major_cities(self):
        """Major US cities should detect USA"""
        assert _detect_country_from_text("Salon in Los Angeles") == "usa"
        assert _detect_country_from_text("New York beauty services") == "usa"
        assert _detect_country_from_text("Chicago spa treatment") == "usa"
        assert _detect_country_from_text("Moreno Valley beauty") == "usa"
        print("✓ US major cities detected correctly")
    
    def test_neutral_text(self):
        """Generic text without geo signals should return None"""
        assert _detect_country_from_text("Best beauty salon services") is None
        assert _detect_country_from_text("Professional spa treatments") is None
        assert _detect_country_from_text("Book your appointment today") is None
        print("✓ Neutral text returns None")


class TestGeoRelevanceScoring:
    """Test full geo-relevance scoring for Dubai UAE campaign"""
    
    def test_reject_usa_url(self):
        """Ads with US TLD/pattern should be rejected (score 0.0)"""
        ad = {
            "brand_name": "US Beauty Brand",
            "landing_page_url": "https://example.com?utm_campaign=beauty_US_2024",
            "text": "Professional beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Expected 0.0, got {score}"
        print("✓ US URL ad rejected (score 0.0)")
    
    def test_reject_usa_state_text(self):
        """Ads mentioning US states should be rejected (score 0.0)"""
        ad = {
            "brand_name": "California Beauty",
            "landing_page_url": "https://example.com",
            "text": "Beauty services in Moreno Valley, California"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Expected 0.0, got {score}"
        print("✓ US state mention ad rejected (score 0.0)")
    
    def test_reject_usa_city_text(self):
        """Ads mentioning US cities should be rejected (score 0.0)"""
        ad = {
            "brand_name": "Moreno Valley Spa",
            "landing_page_url": "https://example.com",
            "text": "Located in Moreno Valley, serving the community"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Expected 0.0, got {score}"
        print("✓ US city mention ad rejected (score 0.0)")
    
    def test_reject_india_url(self):
        """Ads with India TLD should be rejected (score 0.0)"""
        ad = {
            "brand_name": "India Beauty",
            "landing_page_url": "https://beauty.co.in/services",
            "text": "Professional beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Expected 0.0, got {score}"
        print("✓ India TLD ad rejected (score 0.0)")
    
    def test_reject_uk_url(self):
        """Ads with UK TLD should be rejected (score 0.0)"""
        ad = {
            "brand_name": "UK Beauty",
            "landing_page_url": "https://beauty.co.uk/services",
            "text": "Professional beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Expected 0.0, got {score}"
        print("✓ UK TLD ad rejected (score 0.0)")
    
    def test_reject_australia_url(self):
        """Ads with Australia TLD should be rejected (score 0.0)"""
        ad = {
            "brand_name": "Aussie Beauty",
            "landing_page_url": "https://beauty.com.au/services",
            "text": "Professional beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Expected 0.0, got {score}"
        print("✓ Australia TLD ad rejected (score 0.0)")
    
    def test_reject_singapore_url(self):
        """Ads with Singapore TLD should be rejected (score 0.0)"""
        ad = {
            "brand_name": "Singapore Beauty",
            "landing_page_url": "https://beauty.sg/services",
            "text": "Professional beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Expected 0.0, got {score}"
        print("✓ Singapore TLD ad rejected (score 0.0)")
    
    def test_keep_uae_url(self):
        """Ads with UAE TLD should be kept (score 0.9)"""
        ad = {
            "brand_name": "UAE Beauty",
            "landing_page_url": "https://beauty.ae/services",
            "text": "Professional beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.9, f"Expected 0.9, got {score}"
        print("✓ UAE TLD ad kept (score 0.9)")
    
    def test_keep_uae_city_mention(self):
        """Ads mentioning Dubai should get highest score (1.0)"""
        ad = {
            "brand_name": "Dubai Beauty",
            "landing_page_url": "https://example.com",
            "text": "Best beauty salon in Dubai"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 1.0, f"Expected 1.0, got {score}"
        print("✓ Dubai mention ad gets highest score (1.0)")
    
    def test_neutral_generic_com(self):
        """Neutral ads with .com and no geo signal should score 0.5"""
        ad = {
            "brand_name": "Beauty Brand",
            "landing_page_url": "https://beautybrand.com",
            "text": "Professional spa treatments"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.5, f"Expected 0.5, got {score}"
        print("✓ Neutral .com ad scores 0.5 (kept)")
    
    def test_neutral_no_url(self):
        """Ads without URL and no geo text should score 0.5"""
        ad = {
            "brand_name": "Beauty Brand",
            "landing_page_url": "",
            "text": "Professional beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.5, f"Expected 0.5, got {score}"
        print("✓ No URL neutral ad scores 0.5 (kept)")
    
    def test_campaign_country_mention_in_text(self):
        """Ads mentioning 'United Arab Emirates' should score 0.9 (detected via region map)"""
        ad = {
            "brand_name": "Global Beauty",
            "landing_page_url": "https://example.com",
            "text": "Now serving United Arab Emirates"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        # 'united arab emirates' is detected as UAE via _detect_country_from_text
        # which maps to country='uae' matching campaign country -> 0.9
        assert score == 0.9, f"Expected 0.9, got {score}"
        print("✓ 'United Arab Emirates' mention scores 0.9 (same country)")
    
    def test_empty_geo_returns_neutral(self):
        """Empty geo config should return neutral 0.5"""
        ad = {
            "brand_name": "Beauty Brand",
            "landing_page_url": "https://beauty.com.au",
            "text": "Sydney beauty salon"
        }
        score = compute_geo_relevance(ad, {})
        assert score == 0.5, f"Expected 0.5, got {score}"
        score2 = compute_geo_relevance(ad, None)
        assert score2 == 0.5, f"Expected 0.5, got {score2}"
        print("✓ Empty geo returns neutral 0.5")


class TestRealWorldScenarios:
    """Test real-world ad scenarios from the bug report"""
    
    def test_moreno_valley_california_rejected(self):
        """Original bug: Moreno Valley, California ad should be rejected"""
        ad = {
            "brand_name": "Saloncentric",
            "landing_page_url": "https://www.saloncentric.com/shop?utm_medium=cpc&utm_source=meta&utm_campaign=BRAND_AWARENESS_US_FB_20240701",
            "text": "Professional salon services",
            "headline": "Moreno Valley, California"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"Moreno Valley CA ad should be rejected (0.0), got {score}"
        print("✓ Moreno Valley California ad correctly rejected")
    
    def test_us_utm_campaign_rejected(self):
        """US in UTM campaign parameter should be detected and rejected"""
        ad = {
            "brand_name": "US Brand",
            "landing_page_url": "https://example.com?utm_campaign=beauty_US_2024&utm_source=facebook",
            "text": "Beauty salon services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.0, f"US UTM campaign ad should be rejected (0.0), got {score}"
        print("✓ US UTM campaign parameter ad rejected")
    
    def test_uae_competitor_kept(self):
        """UAE-based competitor ads should be kept"""
        ad = {
            "brand_name": "Nooora",
            "landing_page_url": "https://nooora.ae/book",
            "text": "Dubai's on-demand beauty services"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score >= 0.9, f"UAE competitor ad should score >=0.9, got {score}"
        print("✓ UAE competitor ad kept with high score")
    
    def test_global_brand_com_neutral(self):
        """Global brands with .com and no geo signal should be neutral"""
        ad = {
            "brand_name": "Urban Decay",
            "landing_page_url": "https://urbandecay.com/products",
            "text": "Premium makeup products"
        }
        score = compute_geo_relevance(ad, DUBAI_UAE_GEO)
        assert score == 0.5, f"Global .com brand should score 0.5, got {score}"
        print("✓ Global .com brand neutral (0.5)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
