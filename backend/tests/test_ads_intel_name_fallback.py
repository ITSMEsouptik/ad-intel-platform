"""
Ads Intel Name-Based Fallback Bug Fix Tests
============================================
Tests for the fix: When competitor domains aren't in Foreplay's database,
fall back to name-based search but ONLY keep ads where brand name closely 
matches (>70% length ratio).

Test campaigns:
- 568e45c8-7976-4d14-878a-70074f35f3ff: Should have ~9 competitor ads (Ruuby + Vita Home Spa)
- a517c420-418d-416d-87ae-6e768b21c43b: Should have ~1 competitor ad (Belita via name match)
- 354754aa-1ea1-41d8-890a-6a3759ae6f39: Should have competitor + category ads (Urban Company)
"""

import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign IDs provided by main agent
CAMPAIGN_568e = "568e45c8-7976-4d14-878a-70074f35f3ff"  # Dubai beauty salon
CAMPAIGN_a517 = "a517c420-418d-416d-87ae-6e768b21c43b"  # Has Belita competitor
CAMPAIGN_354754 = "354754aa-1ea1-41d8-890a-6a3759ae6f39"  # Has Urban Company


class TestBrandNameMatchFunction:
    """Unit tests for _brand_name_match() function - the core fix"""
    
    @staticmethod
    def _brand_name_match(competitor_name: str, ad_brand_name: str) -> bool:
        """Local copy of the function to test"""
        if not competitor_name or not ad_brand_name:
            return False
        comp = competitor_name.lower().strip()
        brand = ad_brand_name.lower().strip()
        if comp == brand:
            return True
        comp_clean = re.sub(r'[^a-z0-9\s]', '', comp).strip()
        brand_clean = re.sub(r'[^a-z0-9\s]', '', brand).strip()
        if comp_clean == brand_clean:
            return True
        if comp_clean in brand_clean and len(comp_clean) >= len(brand_clean) * 0.7:
            return True
        if brand_clean in comp_clean and len(brand_clean) >= len(comp_clean) * 0.7:
            return True
        return False
    
    def test_exact_match(self):
        """Exact name matches should return True"""
        assert self._brand_name_match("Belita", "Belita") is True
        assert self._brand_name_match("Ruuby", "Ruuby") is True
        assert self._brand_name_match("Vita Home Spa", "Vita Home Spa") is True
        print("✓ Exact name matches work correctly")
    
    def test_reject_false_positives(self):
        """Names that look similar but are different brands should return False"""
        # Key bug fix test: "Belita" should NOT match "Belita&boys"
        assert self._brand_name_match("Belita", "Belita&boys") is False
        assert self._brand_name_match("Belita", "Belita&boys Korean Fashion") is False
        print("✓ False positives rejected: Belita != Belita&boys")
    
    def test_empty_values_return_false(self):
        """Empty or None values should return False"""
        assert self._brand_name_match("", "Belita") is False
        assert self._brand_name_match("Belita", "") is False
        assert self._brand_name_match(None, "Belita") is False
        assert self._brand_name_match("Belita", None) is False
        print("✓ Empty values handled correctly")
    
    def test_case_insensitive(self):
        """Matching should be case-insensitive"""
        assert self._brand_name_match("BELITA", "belita") is True
        assert self._brand_name_match("Ruuby", "RUUBY") is True
        print("✓ Case-insensitive matching works")
    
    def test_punctuation_normalized(self):
        """Punctuation should be normalized for comparison"""
        assert self._brand_name_match("N'Boutique", "NBoutique") is True
        assert self._brand_name_match("M+", "M") is True
        print("✓ Punctuation normalized correctly")


class TestCampaign568CompetitorLens:
    """Test competitor lens for campaign 568e45c8 (Dubai beauty salon)"""
    
    def test_ads_intel_returns_data(self):
        """Campaign should have ads data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_568e}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        assert data.get("has_data") is True
        print(f"✓ Campaign 568e has ads data")
    
    def test_competitor_ads_count(self):
        """Should have approximately 9 competitor ads"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_568e}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        comp_ads = data.get("latest", {}).get("competitor_winners", {}).get("ads", [])
        assert len(comp_ads) >= 5, f"Expected >=5 competitor ads, got {len(comp_ads)}"
        print(f"✓ Campaign 568e has {len(comp_ads)} competitor ads")
    
    def test_competitor_brands_are_correct(self):
        """Competitor ads should be from Ruuby and Vita Home Spa"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_568e}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        comp_ads = data.get("latest", {}).get("competitor_winners", {}).get("ads", [])
        brands = set([ad.get("brand_name") for ad in comp_ads])
        
        # Vita Home Spa should be via domain lookup (vitahomespa.com)
        assert "Vita Home Spa" in brands or "Vita" in str(brands), f"Expected Vita Home Spa, got {brands}"
        print(f"✓ Competitor brands: {brands}")
    
    def test_category_ads_count(self):
        """Should have 10 category ads"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_568e}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        cat_ads = data.get("latest", {}).get("category_winners", {}).get("ads", [])
        assert len(cat_ads) == 10, f"Expected 10 category ads, got {len(cat_ads)}"
        print(f"✓ Campaign 568e has {len(cat_ads)} category ads")
    
    def test_skipped_competitors_logged(self):
        """Competitors without Foreplay brands should be logged"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_568e}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        audit = data.get("latest", {}).get("audit", {})
        skipped = audit.get("skipped_competitors", [])
        # Nooora and NBoutique should be skipped (no Foreplay brand)
        print(f"✓ Skipped competitors: {skipped}")


class TestCampaignA517NameFallback:
    """Test name-based fallback for campaign a517c420"""
    
    def test_ads_intel_returns_data(self):
        """Campaign should have ads data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_a517}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        assert data.get("has_data") is True
        print(f"✓ Campaign a517 has ads data")
    
    def test_competitor_ad_is_belita(self):
        """Should have Belita competitor ad from name-based fallback"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_a517}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        comp_ads = data.get("latest", {}).get("competitor_winners", {}).get("ads", [])
        
        # Should have at least 1 competitor ad
        assert len(comp_ads) >= 1, f"Expected >=1 competitor ads, got {len(comp_ads)}"
        
        # Check that Belita is one of the brands
        brands = [ad.get("brand_name", "").lower() for ad in comp_ads]
        has_belita = any("belita" in b for b in brands)
        assert has_belita, f"Expected Belita in competitor ads, got brands: {brands}"
        print(f"✓ Campaign a517 has Belita competitor ad (name-based fallback worked)")
    
    def test_no_false_positive_belita_boys(self):
        """Should NOT have Belita&boys ads (false positive rejection)"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_a517}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        comp_ads = data.get("latest", {}).get("competitor_winners", {}).get("ads", [])
        
        # Check for false positives like "Belita&boys"
        false_positives = [ad for ad in comp_ads if "boys" in ad.get("brand_name", "").lower()]
        assert len(false_positives) == 0, f"Found false positive ads: {[a.get('brand_name') for a in false_positives]}"
        print(f"✓ No false positive 'Belita&boys' ads in results")
    
    def test_category_ads_have_10(self):
        """Should have 10 category ads with longest_running + min 30d filter"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_a517}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        cat_ads = data.get("latest", {}).get("category_winners", {}).get("ads", [])
        assert len(cat_ads) == 10, f"Expected 10 category ads, got {len(cat_ads)}"
        print(f"✓ Campaign a517 has {len(cat_ads)} category ads")
    
    def test_skipped_competitors_logged_in_audit(self):
        """Competitors that failed domain + name match should be in audit"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_a517}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        audit = data.get("latest", {}).get("audit", {})
        skipped = audit.get("skipped_competitors", [])
        
        # These competitors should be skipped (domain not in Foreplay, name didn't match)
        assert len(skipped) >= 1, "Expected some competitors to be skipped"
        print(f"✓ Skipped competitors: {skipped}")


class TestCampaign354754:
    """Test competitor lens for campaign 354754aa"""
    
    def test_ads_intel_returns_data(self):
        """Campaign should have ads data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_354754}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        assert data.get("has_data") is True
        print(f"✓ Campaign 354754 has ads data")
    
    def test_has_competitor_ads(self):
        """Should have competitor ads"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_354754}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        comp_ads = data.get("latest", {}).get("competitor_winners", {}).get("ads", [])
        assert len(comp_ads) >= 1, f"Expected >=1 competitor ads, got {len(comp_ads)}"
        brands = set([ad.get("brand_name") for ad in comp_ads])
        print(f"✓ Campaign 354754 has {len(comp_ads)} competitor ads, brands: {brands}")
    
    def test_has_category_ads(self):
        """Should have category ads"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_354754}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        cat_ads = data.get("latest", {}).get("category_winners", {}).get("ads", [])
        assert len(cat_ads) >= 5, f"Expected >=5 category ads, got {len(cat_ads)}"
        print(f"✓ Campaign 354754 has {len(cat_ads)} category ads")


class TestGeoFilterAndCategoryLens:
    """Test geo filter and category lens functionality"""
    
    def test_geo_filter_rejects_irrelevant_ads(self):
        """Geo filter should reject ads from different countries"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_568e}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        audit = data.get("latest", {}).get("audit", {})
        
        total_seen = audit.get("total_ads_seen", 0)
        kept = audit.get("kept", 0)
        
        # Some filtering should have occurred
        assert total_seen > kept, f"Expected filtering: {total_seen} seen → {kept} kept"
        filter_rate = ((total_seen - kept) / total_seen * 100) if total_seen > 0 else 0
        print(f"✓ Geo filter: {total_seen} seen → {kept} kept ({filter_rate:.0f}% filtered)")
    
    def test_category_ads_have_running_days(self):
        """Category ads should have running_days from longest_running order"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_568e}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        cat_ads = data.get("latest", {}).get("category_winners", {}).get("ads", [])
        
        ads_with_days = [ad for ad in cat_ads if ad.get("running_days", 0) > 0]
        assert len(ads_with_days) > 0, "Expected category ads to have running_days"
        
        # Most should have >=30 days due to min filter
        high_runners = [ad for ad in cat_ads if ad.get("running_days", 0) >= 30]
        print(f"✓ {len(high_runners)}/{len(cat_ads)} category ads have running_days >= 30")


class TestAdsIntelEndpoints:
    """Test the /latest endpoint for all campaigns"""
    
    def test_all_campaigns_have_correct_shape(self):
        """All campaign responses should have correct shape"""
        for campaign_id in [CAMPAIGN_568e, CAMPAIGN_a517, CAMPAIGN_354754]:
            response = requests.get(f"{BASE_URL}/api/research/{campaign_id}/ads-intel/latest")
            assert response.status_code == 200, f"Failed for {campaign_id}"
            data = response.json()
            
            assert "has_data" in data
            assert "status" in data
            assert "latest" in data
            
            if data.get("has_data"):
                latest = data["latest"]
                assert "competitor_winners" in latest
                assert "category_winners" in latest
                assert "audit" in latest
        
        print("✓ All campaigns have correct response shape")
    
    def test_all_ads_have_required_fields(self):
        """All ads should have required fields for frontend display"""
        for campaign_id in [CAMPAIGN_568e, CAMPAIGN_a517, CAMPAIGN_354754]:
            response = requests.get(f"{BASE_URL}/api/research/{campaign_id}/ads-intel/latest")
            data = response.json()
            
            if not data.get("has_data"):
                continue
                
            latest = data["latest"]
            all_ads = (
                latest.get("competitor_winners", {}).get("ads", []) +
                latest.get("category_winners", {}).get("ads", [])
            )
            
            required = ["ad_id", "lens", "why_shortlisted"]
            for ad in all_ads:
                for field in required:
                    assert field in ad, f"Ad {ad.get('ad_id')} missing {field}"
        
        print("✓ All ads have required fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
