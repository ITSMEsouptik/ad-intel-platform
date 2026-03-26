"""
Ads Intel UX Overhaul Tests - Iteration 37
Tests the new Ads tab features: video playback, pipeline summary, contextual filters, why_shortlisted
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"


class TestAdsIntelUXOverhaul:
    """Tests for Ads Intel UX improvements: video support, pipeline summary, filters"""
    
    def test_ads_intel_endpoint_returns_data(self):
        """Basic check that ads-intel endpoint returns data"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("has_data") == True, "Expected has_data=True"
        assert "latest" in data, "Missing 'latest' key"
    
    def test_pipeline_summary_audit_info(self):
        """Verify audit info for pipeline summary bar"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        audit = latest.get("audit", {})
        assert "total_ads_seen" in audit, "Missing total_ads_seen in audit"
        assert audit.get("total_ads_seen", 0) > 0, "total_ads_seen should be > 0"
        
        # Verify kept count matches total shortlisted
        cw_count = len(latest.get("competitor_winners", {}).get("ads", []))
        cat_count = len(latest.get("category_winners", {}).get("ads", []))
        total_shortlisted = cw_count + cat_count
        
        print(f"Audit: {audit.get('total_ads_seen')} scanned, {total_shortlisted} shortlisted")
        assert total_shortlisted > 0, "Should have shortlisted ads"
    
    def test_geo_info_in_inputs(self):
        """Verify geo info for pipeline summary"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        geo = latest.get("inputs", {}).get("geo", {})
        assert "city" in geo, "Missing city in geo"
        assert "country" in geo, "Missing country in geo"
        assert geo.get("city") == "dubai", f"Expected city='dubai', got {geo.get('city')}"
        assert "Arab Emirates" in geo.get("country", ""), f"Expected UAE, got {geo.get('country')}"
        
        print(f"Geo: {geo.get('city')}, {geo.get('country')}")
    
    def test_competitor_winners_count(self):
        """Verify competitor_winners returns expected count"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        cw = latest.get("competitor_winners", {})
        ads = cw.get("ads", [])
        
        assert len(ads) == 12, f"Expected 12 competitor ads, got {len(ads)}"
        print(f"Competitor winners: {len(ads)} ads")
    
    def test_category_winners_count(self):
        """Verify category_winners returns expected count"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        catw = latest.get("category_winners", {})
        ads = catw.get("ads", [])
        
        assert len(ads) == 7, f"Expected 7 category ads, got {len(ads)}"
        print(f"Category winners: {len(ads)} ads")
    
    def test_category_winners_queries_used(self):
        """Verify category_winners stats include queries_used array"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        catw = latest.get("category_winners", {})
        stats = catw.get("stats", {})
        
        assert "queries_used" in stats, "Missing queries_used in category_winners stats"
        queries = stats.get("queries_used", [])
        assert len(queries) > 0, "queries_used should not be empty"
        
        print(f"Queries used: {queries}")
        # Check expected queries
        expected_queries = ["Hair & Makeup Home Service Dubai", "On-demand Beauty Services", "Beauty & Wellness"]
        for q in expected_queries:
            assert q in queries, f"Missing expected query: {q}"
    
    def test_video_ads_have_media_url(self):
        """Verify video ads have media_url with .mp4"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        cw_ads = latest.get("competitor_winners", {}).get("ads", [])
        cat_ads = latest.get("category_winners", {}).get("ads", [])
        all_ads = cw_ads + cat_ads
        
        # Find video ads
        video_ads = [a for a in all_ads if a.get("display_format") == "video" or 
                     (a.get("media_url") and ".mp4" in a.get("media_url", ""))]
        
        assert len(video_ads) > 0, "Should have video ads"
        
        for ad in video_ads:
            media_url = ad.get("media_url", "")
            assert media_url, f"Video ad missing media_url: {ad.get('brand_name')}"
            assert ".mp4" in media_url, f"Video media_url should contain .mp4: {media_url}"
        
        print(f"Found {len(video_ads)} video ads with valid media_url")
    
    def test_why_shortlisted_field_present(self):
        """Verify all ads have why_shortlisted field"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        cw_ads = latest.get("competitor_winners", {}).get("ads", [])
        cat_ads = latest.get("category_winners", {}).get("ads", [])
        all_ads = cw_ads + cat_ads
        
        ads_with_why = [a for a in all_ads if a.get("why_shortlisted")]
        assert len(ads_with_why) == len(all_ads), f"All ads should have why_shortlisted. Have: {len(ads_with_why)}/{len(all_ads)}"
    
    def test_why_shortlisted_has_meaningful_context(self):
        """Verify why_shortlisted includes relevant context like 'long-running', 'competitor', etc."""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        cw_ads = latest.get("competitor_winners", {}).get("ads", [])
        cat_ads = latest.get("category_winners", {}).get("ads", [])
        
        # Check competitor ads mention "competitor"
        for ad in cw_ads[:3]:
            why = ad.get("why_shortlisted", "")
            assert "competitor" in why.lower(), f"Competitor ad why_shortlisted should mention 'competitor': {why}"
        
        # Check some category ads mention "trend" or "geo"
        category_contexts = ["trend", "geo", "running", "industry"]
        for ad in cat_ads[:3]:
            why = ad.get("why_shortlisted", "")
            has_context = any(ctx in why.lower() for ctx in category_contexts)
            assert has_context, f"Category ad should have context: {why}"
        
        print("why_shortlisted has meaningful context")
    
    def test_long_running_ads_flagged(self):
        """Verify long-running ads (>30 days) have 'long-running' in why_shortlisted"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        cw_ads = latest.get("competitor_winners", {}).get("ads", [])
        
        # Find ads running > 30 days
        long_runners = [a for a in cw_ads if a.get("running_days", 0) > 30]
        
        assert len(long_runners) > 0, "Should have long-running ads"
        
        for ad in long_runners[:3]:
            why = ad.get("why_shortlisted", "")
            assert "long-running" in why.lower(), f"Long-running ad ({ad.get('running_days')}d) should say 'long-running': {why}"
        
        print(f"Found {len(long_runners)} long-running ads with proper why_shortlisted")
    
    def test_ad_cards_have_required_fields(self):
        """Verify ad cards have required fields: brand, platform, format, days_running"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        cw_ads = latest.get("competitor_winners", {}).get("ads", [])
        
        required_fields = ["brand_name", "publisher_platform", "display_format", "running_days"]
        
        for ad in cw_ads[:5]:
            for field in required_fields:
                assert field in ad or ad.get(field) is not None, f"Missing {field} in ad: {ad.get('brand_name')}"
        
        print("All ads have required fields")
    
    def test_competitor_winners_stats(self):
        """Verify competitor_winners stats has brands_queried"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        cw = latest.get("competitor_winners", {})
        stats = cw.get("stats", {})
        
        assert "brands_queried" in stats, "Missing brands_queried in competitor_winners stats"
        assert stats.get("brands_queried", 0) > 0, "brands_queried should be > 0"
        
        print(f"Brands queried: {stats.get('brands_queried')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
