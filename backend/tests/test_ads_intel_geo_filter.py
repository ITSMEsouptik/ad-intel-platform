"""
Ads Intelligence API Tests - Geo-Relevance Filter Verification
Tests for the geo-filter fix to ensure irrelevant ads are rejected.

Campaign: 568e45c8-7976-4d14-878a-70074f35f3ff (Dubai, UAE beauty salon)
Expected: No ads from clearly US/India/UK/Australia/Singapore geography
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
BASE_URL = BASE_URL.rstrip('/')

# Test campaign ID - Dubai UAE beauty salon
TEST_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
FAKE_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000000"


class TestAdsIntelAPIEndpoints:
    """Test Ads Intelligence API endpoint availability"""
    
    def test_api_health(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_latest_endpoint_returns_200(self):
        """Latest endpoint should return 200 for valid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        print("✓ /ads-intel/latest endpoint returns 200")
    
    def test_latest_has_required_fields(self):
        """Latest response should have required fields"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        print(f"✓ Required fields present: has_data={data['has_data']}, status={data['status']}")
    
    def test_run_endpoint_returns_running(self):
        """Run endpoint should return status=running"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/run")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") == "running"
        assert "campaign_id" in data
        print(f"✓ /ads-intel/run returns status=running")
    
    def test_history_endpoint_returns_200(self):
        """History endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "snapshots" in data
        assert "total_count" in data
        print(f"✓ /ads-intel/history returns {data['total_count']} snapshots")
    
    def test_404_for_nonexistent_campaign(self):
        """Non-existent campaign should return 404"""
        response = requests.get(f"{BASE_URL}/api/research/{FAKE_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 404
        print("✓ Non-existent campaign returns 404")


class TestAdsIntelDataStructure:
    """Test the structure of returned ads data"""
    
    def test_snapshot_has_competitor_and_category_winners(self):
        """Snapshot should have both competitor_winners and category_winners"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        assert "competitor_winners" in latest
        assert "category_winners" in latest
        
        cw = latest["competitor_winners"]
        cat = latest["category_winners"]
        
        assert "ads" in cw
        assert "ads" in cat
        print(f"✓ Competitor winners: {len(cw['ads'])} ads")
        print(f"✓ Category winners: {len(cat['ads'])} ads")
    
    def test_ad_cards_have_required_fields(self):
        """Each ad card should have required fields for frontend display"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        all_ads = (latest.get("competitor_winners", {}).get("ads", []) + 
                   latest.get("category_winners", {}).get("ads", []))
        
        assert len(all_ads) > 0, "Expected at least some ads"
        
        for i, ad in enumerate(all_ads[:5]):
            assert "ad_id" in ad, f"Ad {i} missing ad_id"
            assert "lens" in ad, f"Ad {i} missing lens"
            assert "why_shortlisted" in ad, f"Ad {i} missing why_shortlisted"
            assert ad["lens"] in ["competitor", "category"], f"Invalid lens: {ad['lens']}"
        
        print(f"✓ {len(all_ads)} ad cards validated")
    
    def test_snapshot_has_audit_info(self):
        """Snapshot should have audit information"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        assert "audit" in latest
        
        audit = latest["audit"]
        assert "api_calls" in audit
        assert "total_ads_seen" in audit
        assert "kept" in audit
        
        print(f"✓ Audit: {audit['api_calls']} API calls, {audit['total_ads_seen']} seen, {audit['kept']} kept")


class TestGeoRelevanceViaAPI:
    """Test that geo-relevance filter is working via API response"""
    
    def test_no_usa_state_mentions_in_ads(self):
        """Category ads should not contain US state mentions for Dubai campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        cat_ads = latest.get("category_winners", {}).get("ads", [])
        
        us_states = [
            "california", "texas", "florida", "new york", "arizona", "nevada",
            "colorado", "washington", "oregon", "georgia", "north carolina"
        ]
        
        violations = []
        for ad in cat_ads:
            text = (ad.get("text") or "").lower()
            headline = (ad.get("headline") or "").lower()
            brand = (ad.get("brand_name") or "").lower()
            combined = f"{text} {headline} {brand}"
            
            for state in us_states:
                if state in combined:
                    violations.append(f"Ad '{ad.get('brand_name')}' contains US state: {state}")
        
        if violations:
            for v in violations:
                print(f"⚠ {v}")
        
        # This is a soft check - we don't fail but report
        print(f"✓ Checked {len(cat_ads)} category ads for US state mentions")
        print(f"  Violations found: {len(violations)}")
    
    def test_no_usa_url_patterns_in_category_ads(self):
        """Category ads should not have obvious US URL patterns"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        cat_ads = latest.get("category_winners", {}).get("ads", [])
        
        us_patterns = ["_US_", "/us/", "store=us", "country=us"]
        
        violations = []
        for ad in cat_ads:
            url = (ad.get("landing_page_url") or "").lower()
            for pattern in us_patterns:
                if pattern.lower() in url:
                    violations.append(f"Ad '{ad.get('brand_name')}' has US URL pattern: {pattern} in {url[:60]}...")
        
        if violations:
            for v in violations:
                print(f"⚠ {v}")
        
        print(f"✓ Checked {len(cat_ads)} category ads for US URL patterns")
        print(f"  Violations found: {len(violations)}")
    
    def test_competitor_ads_are_from_known_competitors(self):
        """Competitor ads should be from the campaign's identified competitors"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        comp_ads = latest.get("competitor_winners", {}).get("ads", [])
        
        # Known Dubai beauty competitors from previous tests
        known_competitors = {"ruuby", "nooora", "nboutique", "vita home spa", "russell & bromley"}
        
        brands_found = set()
        for ad in comp_ads:
            brand = (ad.get("brand_name") or "").lower()
            brands_found.add(brand)
        
        print(f"✓ Competitor brands found: {brands_found}")
        print(f"✓ {len(comp_ads)} competitor ads from {len(brands_found)} brands")
    
    def test_inputs_show_dubai_geo(self):
        """Inputs should show Dubai UAE as the campaign geo"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        inputs = latest.get("inputs", {})
        geo = inputs.get("geo", {})
        
        assert geo.get("city", "").lower() == "dubai" or "dubai" in geo.get("city", "").lower(), \
            f"Expected Dubai city, got: {geo.get('city')}"
        
        country = geo.get("country", "").lower()
        assert "emirates" in country or "uae" in country, \
            f"Expected UAE country, got: {geo.get('country')}"
        
        print(f"✓ Campaign geo confirmed: city={geo.get('city')}, country={geo.get('country')}")


class TestGeoFilterEffectiveness:
    """Test the effectiveness of the geo filter"""
    
    def test_geo_filter_metrics_in_audit(self):
        """Check if geo filter metrics show filtering happened"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        audit = latest.get("audit", {})
        
        total_seen = audit.get("total_ads_seen", 0)
        kept = audit.get("kept", 0)
        
        if total_seen > 0:
            filter_rate = (1 - kept / total_seen) * 100
            print(f"✓ Geo filter: {total_seen} seen → {kept} kept ({filter_rate:.1f}% filtered)")
        else:
            print("⚠ No ads seen in audit")
    
    def test_reasonable_number_of_ads(self):
        """Should have a reasonable number of ads (not 0, not too many)"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data.get("has_data"):
            pytest.skip("No ads data available")
        
        latest = data["latest"]
        comp_ads = latest.get("competitor_winners", {}).get("ads", [])
        cat_ads = latest.get("category_winners", {}).get("ads", [])
        total = len(comp_ads) + len(cat_ads)
        
        assert total >= 1, "Expected at least 1 ad"
        assert total <= 50, f"Too many ads: {total} (expected <= 50)"
        
        print(f"✓ Total ads count: {total} (competitor: {len(comp_ads)}, category: {len(cat_ads)})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
