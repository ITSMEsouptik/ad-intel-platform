"""
Full End-to-End Stress Test for Novara Platform
Tests all API endpoints, edge cases, error handling, and data integrity
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign with full data
TEST_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
# Test campaign with partial/no data
EMPTY_CAMPAIGN_ID = "b66229cf-7aa9-4e51-ae0e-81a57ab2ac18"
# Non-existent ID for 404 testing
NONEXISTENT_ID = "00000000-0000-0000-0000-000000000000"

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

# ============== HEALTH CHECK ==============

class TestHealthCheck:
    """API health check tests"""
    
    def test_root_endpoint(self, api_client):
        """Test root API endpoint returns healthy"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data
        print(f"✅ API Health: {data}")

# ============== CAMPAIGN BRIEFS ==============

class TestCampaignBriefs:
    """Campaign brief endpoint tests"""
    
    def test_get_campaign_brief_success(self, api_client):
        """Test getting existing campaign brief"""
        response = api_client.get(f"{BASE_URL}/api/campaign-briefs/{TEST_CAMPAIGN_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "campaign_brief_id" in data
        assert data["campaign_brief_id"] == TEST_CAMPAIGN_ID
        print(f"✅ Campaign brief retrieved: {data.get('brand', {}).get('website_url', 'Unknown')}")
    
    def test_get_campaign_brief_not_found(self, api_client):
        """Test 404 for non-existent campaign"""
        response = api_client.get(f"{BASE_URL}/api/campaign-briefs/{NONEXISTENT_ID}")
        assert response.status_code == 404
        print("✅ 404 returned for non-existent campaign")
    
    def test_list_campaign_briefs_requires_auth(self, api_client):
        """Test that listing briefs requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/campaign-briefs")
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print("✅ Auth required for listing briefs")

# ============== ORCHESTRATION ==============

class TestOrchestration:
    """Orchestration status endpoint tests"""
    
    def test_get_orchestration_status_valid(self, api_client):
        """Test getting orchestration status for valid campaign"""
        response = api_client.get(f"{BASE_URL}/api/orchestrations/{TEST_CAMPAIGN_ID}/status")
        # Could be 200 or 404 depending on if orchestration exists
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Orchestration status: {data.get('orchestration', {}).get('status', 'N/A')}")
        else:
            print("✅ No orchestration found (expected)")
    
    def test_get_orchestration_status_nonexistent(self, api_client):
        """Test 404 for non-existent orchestration"""
        response = api_client.get(f"{BASE_URL}/api/orchestrations/{NONEXISTENT_ID}/status")
        assert response.status_code == 404
        print("✅ 404 returned for non-existent orchestration")

# ============== WEBSITE CONTEXT PACKS ==============

class TestWebsiteContextPacks:
    """Website context pack endpoint tests"""
    
    def test_get_website_context_pack_valid(self, api_client):
        """Test getting website context pack for valid campaign"""
        response = api_client.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_CAMPAIGN_ID}")
        # Could be 200 or 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Website context pack found, status: {data.get('status', 'N/A')}")
        else:
            print("✅ No website context pack found")
    
    def test_get_website_context_pack_nonexistent(self, api_client):
        """Test 404 for non-existent website context pack"""
        response = api_client.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{NONEXISTENT_ID}")
        assert response.status_code == 404
        print("✅ 404 returned for non-existent website context pack")

# ============== RESEARCH PACK ==============

class TestResearchPack:
    """Research pack endpoint tests"""
    
    def test_get_research_pack_valid(self, api_client):
        """Test getting research pack for valid campaign"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "campaign_id" in data
        print(f"✅ Research pack retrieved, has_data: {data.get('has_data', False)}")
        if data.get("has_data"):
            sources = data.get("sources", {})
            print(f"   Sources available: {list(sources.keys())}")
    
    def test_get_research_pack_nonexistent(self, api_client):
        """Test 404 for non-existent campaign"""
        response = api_client.get(f"{BASE_URL}/api/research/{NONEXISTENT_ID}")
        assert response.status_code == 404
        print("✅ 404 returned for non-existent research pack")

# ============== 9 RESEARCH MODULES ==============

class TestCustomerIntelModule:
    """Customer Intel module endpoint tests"""
    
    def test_customer_intel_latest(self, api_client):
        """Test getting latest customer intel"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Customer Intel: has_data={data.get('has_data')}, status={data.get('status')}")
        if data.get("has_data"):
            latest = data.get("latest", {})
            segments = latest.get("segments") or latest.get("icp_segments", [])
            print(f"   Segments count: {len(segments)}")
    
    def test_customer_intel_history(self, api_client):
        """Test getting customer intel history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Customer Intel History: {len(data.get('history', []))} entries")


class TestSearchIntentModule:
    """Search Intent module endpoint tests"""
    
    def test_search_intent_latest(self, api_client):
        """Test getting latest search intent"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Search Intent: has_data={data.get('has_data')}, status={data.get('status')}")
        if data.get("has_data"):
            latest = data.get("latest", {})
            queries = latest.get("top_10_queries", [])
            print(f"   Top queries count: {len(queries)}")
    
    def test_search_intent_history(self, api_client):
        """Test getting search intent history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Search Intent History: {data.get('total_count', 0)} entries")


class TestSeasonalityModule:
    """Seasonality module endpoint tests"""
    
    def test_seasonality_latest(self, api_client):
        """Test getting latest seasonality"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Seasonality: has_data={data.get('has_data')}, status={data.get('status')}")
        if data.get("has_data"):
            latest = data.get("latest", {})
            moments = latest.get("key_moments", [])
            print(f"   Key moments count: {len(moments)}")
    
    def test_seasonality_history(self, api_client):
        """Test getting seasonality history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Seasonality History: {data.get('total_count', 0)} entries")


class TestCompetitorsModule:
    """Competitors module endpoint tests"""
    
    def test_competitors_latest(self, api_client):
        """Test getting latest competitors"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Competitors: has_data={data.get('has_data')}, status={data.get('status')}")
        if data.get("has_data"):
            latest = data.get("latest", {})
            competitors = latest.get("competitors", [])
            print(f"   Competitors count: {len(competitors)}")
    
    def test_competitors_history(self, api_client):
        """Test getting competitors history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Competitors History: {data.get('total_count', 0)} entries")


class TestReviewsModule:
    """Reviews module endpoint tests"""
    
    def test_reviews_latest(self, api_client):
        """Test getting latest reviews"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/reviews/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Reviews: has_data={data.get('has_data')}, status={data.get('status')}")
    
    def test_reviews_history(self, api_client):
        """Test getting reviews history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/reviews/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Reviews History: {data.get('total_count', 0)} entries")


class TestCommunityModule:
    """Community module endpoint tests"""
    
    def test_community_latest(self, api_client):
        """Test getting latest community intel"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/community/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Community: has_data={data.get('has_data')}, status={data.get('status')}")
    
    def test_community_history(self, api_client):
        """Test getting community history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/community/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Community History: {data.get('total_count', 0)} entries")


class TestPressMediaModule:
    """Press & Media module endpoint tests"""
    
    def test_press_media_latest(self, api_client):
        """Test getting latest press & media"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/press-media/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Press & Media: has_data={data.get('has_data')}, status={data.get('status')}")
    
    def test_press_media_history(self, api_client):
        """Test getting press & media history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/press-media/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Press & Media History: {data.get('total_count', 0)} entries")


class TestSocialTrendsModule:
    """Social Trends module endpoint tests"""
    
    def test_social_trends_latest(self, api_client):
        """Test getting latest social trends"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Social Trends: has_data={data.get('has_data')}, status={data.get('status')}")
        if data.get("has_data"):
            latest = data.get("latest", {})
            shortlist = latest.get("shortlist", {})
            tt_count = len(shortlist.get("tiktok", []))
            ig_count = len(shortlist.get("instagram", []))
            print(f"   TikTok posts: {tt_count}, Instagram posts: {ig_count}")
    
    def test_social_trends_history(self, api_client):
        """Test getting social trends history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/social-trends/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Social Trends History: {data.get('total_count', 0)} entries")


class TestAdsIntelModule:
    """Ads Intelligence module endpoint tests"""
    
    def test_ads_intel_latest(self, api_client):
        """Test getting latest ads intel"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Ads Intel: has_data={data.get('has_data')}, status={data.get('status')}")
        if data.get("has_data"):
            latest = data.get("latest", {})
            comp_ads = latest.get("competitor_winners", {}).get("ads", [])
            cat_ads = latest.get("category_winners", {}).get("ads", [])
            print(f"   Competitor ads: {len(comp_ads)}, Category ads: {len(cat_ads)}")
    
    def test_ads_intel_history(self, api_client):
        """Test getting ads intel history"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/history")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Ads Intel History: {data.get('total_count', 0)} entries")

# ============== PDF EXPORT ==============

class TestPDFExport:
    """PDF Export endpoint tests"""
    
    def test_pdf_export_valid_campaign(self, api_client):
        """Test PDF export for campaign with data"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/export/pdf")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert "content-disposition" in response.headers
        content = response.content
        assert len(content) > 0
        # Check PDF magic bytes
        assert content[:4] == b'%PDF'
        print(f"✅ PDF Export: {len(content)} bytes, valid PDF")
    
    def test_pdf_export_empty_campaign(self, api_client):
        """Test PDF export for campaign with partial/no data"""
        response = api_client.get(f"{BASE_URL}/api/research/{EMPTY_CAMPAIGN_ID}/export/pdf")
        # Should still return PDF, just with less content
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            content = response.content
            assert content[:4] == b'%PDF'
            print(f"✅ PDF Export (empty campaign): {len(content)} bytes")
        else:
            print("✅ PDF Export: 404 for campaign with no data (expected)")
    
    def test_pdf_export_nonexistent_campaign(self, api_client):
        """Test PDF export for non-existent campaign"""
        response = api_client.get(f"{BASE_URL}/api/research/{NONEXISTENT_ID}/export/pdf")
        assert response.status_code == 404
        print("✅ PDF Export: 404 for non-existent campaign")

# ============== COMPARE ENDPOINTS ==============

class TestCompareEndpoints:
    """Module comparison endpoint tests"""
    
    def test_compare_customer_intel(self, api_client):
        """Test compare endpoint for customer intel"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/compare")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Customer Intel Compare: has_comparison={data.get('has_comparison')}")
            if data.get("deltas"):
                print(f"   Deltas: {len(data['deltas'])} changes")
        else:
            print("✅ Customer Intel Compare: No research pack (expected)")
    
    def test_compare_search_intent(self, api_client):
        """Test compare endpoint for search intent"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/compare")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search Intent Compare: has_comparison={data.get('has_comparison')}")
    
    def test_compare_seasonality(self, api_client):
        """Test compare endpoint for seasonality"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/compare")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Seasonality Compare: has_comparison={data.get('has_comparison')}")
    
    def test_compare_competitors(self, api_client):
        """Test compare endpoint for competitors"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/compare")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Competitors Compare: has_comparison={data.get('has_comparison')}")
    
    def test_compare_nonexistent_module(self, api_client):
        """Test compare with non-existent campaign"""
        response = api_client.get(f"{BASE_URL}/api/research/{NONEXISTENT_ID}/customer-intel/compare")
        assert response.status_code == 404
        print("✅ Compare: 404 for non-existent campaign")

# ============== PROGRESS ENDPOINTS ==============

class TestProgressEndpoints:
    """Module progress endpoint tests"""
    
    def test_progress_customer_intel(self, api_client):
        """Test progress endpoint for customer intel"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/progress")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "events" in data
        assert "progress_pct" in data
        print(f"✅ Customer Intel Progress: status={data.get('status')}, pct={data.get('progress_pct')}")
    
    def test_progress_nonexistent(self, api_client):
        """Test progress with non-existent campaign"""
        response = api_client.get(f"{BASE_URL}/api/research/{NONEXISTENT_ID}/customer-intel/progress")
        assert response.status_code == 200  # Returns not_found status, not 404
        data = response.json()
        assert data.get("status") == "not_found"
        print("✅ Progress: Returns not_found status for non-existent")

# ============== MEDIA ENDPOINTS ==============

class TestMediaEndpoints:
    """Media cache endpoint tests"""
    
    def test_media_thumb_missing(self, api_client):
        """Test thumbnail endpoint for missing ID"""
        response = api_client.get(f"{BASE_URL}/api/media/thumb/nonexistent-id")
        assert response.status_code == 404
        print("✅ Media Thumb: 404 for non-existent thumbnail")
    
    def test_media_video_missing(self, api_client):
        """Test video endpoint for missing ID"""
        response = api_client.get(f"{BASE_URL}/api/media/video/nonexistent-id")
        assert response.status_code == 404
        print("✅ Media Video: 404 for non-existent video")
    
    def test_media_stats(self, api_client):
        """Test media cache stats endpoint"""
        response = api_client.get(f"{BASE_URL}/api/media/stats")
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Media Stats: {data}")

# ============== AUTH ENDPOINTS ==============

class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_auth_me_without_session(self, api_client):
        """Test /auth/me without session returns 401"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✅ Auth Me: 401 without session")
    
    def test_auth_logout_without_session(self, api_client):
        """Test /auth/logout without session still works"""
        response = api_client.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("✅ Auth Logout: Works without session")

# ============== DEBUG ENDPOINTS ==============

class TestDebugEndpoints:
    """Debug dashboard endpoint tests"""
    
    def test_debug_campaigns(self, api_client):
        """Test debug campaigns listing"""
        response = api_client.get(f"{BASE_URL}/api/debug/campaigns")
        assert response.status_code == 200
        data = response.json()
        assert "campaigns" in data
        print(f"✅ Debug Campaigns: {len(data.get('campaigns', []))} recent campaigns")
    
    def test_debug_campaign_detail(self, api_client):
        """Test debug campaign detail"""
        response = api_client.get(f"{BASE_URL}/api/debug/campaign/{TEST_CAMPAIGN_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "campaign_brief_id" in data
        print(f"✅ Debug Campaign Detail: Retrieved for {TEST_CAMPAIGN_ID[:8]}...")
    
    def test_debug_campaign_nonexistent(self, api_client):
        """Test debug campaign for non-existent ID"""
        response = api_client.get(f"{BASE_URL}/api/debug/campaign/{NONEXISTENT_ID}")
        assert response.status_code == 404
        print("✅ Debug Campaign: 404 for non-existent")

# ============== EDGE CASES ==============

class TestEdgeCases:
    """Edge case and error handling tests"""
    
    def test_invalid_uuid_format(self, api_client):
        """Test handling of invalid UUID format"""
        response = api_client.get(f"{BASE_URL}/api/campaign-briefs/invalid-uuid-format")
        # Should return 404, not 500
        assert response.status_code == 404
        print("✅ Invalid UUID: Returns 404, not 500")
    
    def test_empty_campaign_modules(self, api_client):
        """Test module endpoints for campaign with no research data"""
        modules = ["customer-intel", "search-intent", "seasonality", "competitors", 
                   "reviews", "community", "press-media", "social-trends", "ads-intel"]
        
        for module in modules:
            response = api_client.get(f"{BASE_URL}/api/research/{EMPTY_CAMPAIGN_ID}/{module}/latest")
            # Should return 200 with has_data=False, or 404
            assert response.status_code in [200, 404]
        
        print(f"✅ Empty Campaign: All 9 modules handle gracefully")
    
    def test_all_history_endpoints_for_nonexistent(self, api_client):
        """Test all history endpoints for non-existent campaign"""
        modules = ["customer-intel", "search-intent", "seasonality", "competitors",
                   "reviews", "community", "press-media", "social-trends", "ads-intel"]
        
        for module in modules:
            response = api_client.get(f"{BASE_URL}/api/research/{NONEXISTENT_ID}/{module}/history")
            assert response.status_code == 404
        
        print("✅ Non-existent: All 9 history endpoints return 404")

# ============== DATA INTEGRITY ==============

class TestDataIntegrity:
    """Data integrity tests"""
    
    def test_research_pack_structure(self, api_client):
        """Verify research pack has expected structure"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("has_data"):
            sources = data.get("sources", {})
            expected_modules = ["customer_intel", "search_intent", "seasonality", 
                              "competitors", "reviews", "community", "press_media", 
                              "social_trends", "ads_intel"]
            
            found_modules = list(sources.keys())
            print(f"✅ Data Integrity: Found modules: {found_modules}")
            
            # Verify each module has expected structure
            for module_key in found_modules:
                module_data = sources[module_key]
                # Should have 'latest' key or be empty
                assert isinstance(module_data, dict)
        else:
            print("✅ Data Integrity: No research data for campaign")
    
    def test_customer_intel_segment_structure(self, api_client):
        """Verify customer intel segments have valid structure"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("has_data"):
            latest = data.get("latest", {})
            segments = latest.get("segments") or latest.get("icp_segments", [])
            
            for seg in segments:
                # Segments should have name/label
                assert "segment_name" in seg or "name" in seg or "segment_label" in seg
            
            print(f"✅ Customer Intel Structure: {len(segments)} valid segments")
    
    def test_search_intent_queries_structure(self, api_client):
        """Verify search intent has valid query structure"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("has_data"):
            latest = data.get("latest", {})
            queries = latest.get("top_10_queries", [])
            
            for q in queries:
                # Queries should be strings or have query field
                assert isinstance(q, (str, dict))
                if isinstance(q, dict):
                    assert "query" in q
            
            print(f"✅ Search Intent Structure: {len(queries)} valid queries")
    
    def test_social_trends_content_structure(self, api_client):
        """Verify social trends has valid content structure"""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        if data.get("has_data"):
            latest = data.get("latest", {})
            shortlist = latest.get("shortlist", {})
            
            tiktok_posts = shortlist.get("tiktok", [])
            instagram_posts = shortlist.get("instagram", [])
            
            for post in tiktok_posts[:5]:  # Check first 5
                # Posts should have required fields
                assert "post_url" in post or "video_id" in post or "id" in post
            
            print(f"✅ Social Trends Structure: {len(tiktok_posts)} TikTok, {len(instagram_posts)} Instagram")

# ============== PERFORMANCE ==============

class TestPerformance:
    """Basic performance tests"""
    
    def test_api_response_time_health(self, api_client):
        """Test health endpoint responds quickly"""
        import time
        start = time.time()
        response = api_client.get(f"{BASE_URL}/api/")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0  # Should respond in under 2 seconds
        print(f"✅ Health endpoint: {duration:.2f}s")
    
    def test_api_response_time_research_pack(self, api_client):
        """Test research pack endpoint responds reasonably"""
        import time
        start = time.time()
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 5.0  # Should respond in under 5 seconds
        print(f"✅ Research pack endpoint: {duration:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
