"""
Ads Intelligence API Tests
Tests the 3 backend endpoints for Ads Intelligence:
- POST /api/research/{campaignId}/ads-intel/run
- GET /api/research/{campaignId}/ads-intel/latest
- GET /api/research/{campaignId}/ads-intel/history

Test campaign ID: 21ec9a20-7747-4353-abe4-2f6881365c5b
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')
if BASE_URL:
    BASE_URL = BASE_URL.rstrip('/')

# Test campaign with competitors (Dubai beauty salon)
TEST_CAMPAIGN_ID = "21ec9a20-7747-4353-abe4-2f6881365c5b"
# Non-existent campaign ID for 404 tests
FAKE_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000000"


class TestHealthCheck:
    """Basic API health check"""
    
    def test_api_health(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ API health check passed: {data}")


class TestAdsIntelLatest:
    """GET /api/research/{campaignId}/ads-intel/latest endpoint tests"""
    
    def test_latest_returns_correct_shape(self):
        """Latest endpoint returns correct response shape"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        # Check required fields exist
        assert "has_data" in data, "Missing 'has_data' field"
        assert "status" in data, "Missing 'status' field"
        assert "latest" in data, "Missing 'latest' field"
        assert "refresh_due_in_days" in data, "Missing 'refresh_due_in_days' field"
        
        print(f"✓ Latest endpoint shape: has_data={data['has_data']}, status={data['status']}")
        
    def test_latest_valid_status_values(self):
        """Status should be one of: not_run, fresh, stale"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        valid_statuses = {"not_run", "fresh", "stale"}
        assert data["status"] in valid_statuses, f"Invalid status: {data['status']}"
        print(f"✓ Status value valid: {data['status']}")
        
    def test_latest_with_data_has_snapshot(self):
        """If has_data=true, latest should contain snapshot structure"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if data["has_data"]:
            latest = data["latest"]
            assert latest is not None, "has_data=true but latest is None"
            
            # Check snapshot fields
            assert "competitor_winners" in latest, "Missing competitor_winners"
            assert "category_winners" in latest, "Missing category_winners"
            
            # Check competitor_winners structure
            comp = latest["competitor_winners"]
            assert "ads" in comp, "Missing ads in competitor_winners"
            assert "stats" in comp, "Missing stats in competitor_winners"
            assert isinstance(comp["ads"], list), "competitor_winners.ads should be list"
            
            # Check category_winners structure
            cat = latest["category_winners"]
            assert "ads" in cat, "Missing ads in category_winners"
            assert "stats" in cat, "Missing stats in category_winners"
            assert isinstance(cat["ads"], list), "category_winners.ads should be list"
            
            print(f"✓ Snapshot structure valid: {len(comp['ads'])} comp ads, {len(cat['ads'])} cat ads")
        else:
            print("✓ has_data=false (no data yet), snapshot test skipped")
            
    def test_latest_404_for_nonexistent_campaign(self):
        """Non-existent campaign should return 404"""
        response = requests.get(f"{BASE_URL}/api/research/{FAKE_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 404
        print(f"✓ Non-existent campaign returns 404")


class TestAdsIntelRun:
    """POST /api/research/{campaignId}/ads-intel/run endpoint tests"""
    
    def test_run_returns_running_status(self):
        """Run endpoint should return running status immediately"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/run")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data, "Missing status field"
        assert data["status"] == "running", f"Expected status='running', got '{data['status']}'"
        assert "campaign_id" in data, "Missing campaign_id"
        assert "message" in data, "Missing message"
        
        print(f"✓ Run endpoint returned: status={data['status']}, message={data['message'][:50]}...")
        
    def test_run_404_for_nonexistent_campaign(self):
        """Non-existent campaign should return 404"""
        response = requests.post(f"{BASE_URL}/api/research/{FAKE_CAMPAIGN_ID}/ads-intel/run")
        assert response.status_code == 404
        print(f"✓ Run on non-existent campaign returns 404")


class TestAdsIntelHistory:
    """GET /api/research/{campaignId}/ads-intel/history endpoint tests"""
    
    def test_history_returns_correct_shape(self):
        """History endpoint returns correct response shape"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "campaign_id" in data, "Missing campaign_id"
        assert "snapshots" in data, "Missing snapshots"
        assert "total_count" in data, "Missing total_count"
        assert isinstance(data["snapshots"], list), "snapshots should be list"
        
        print(f"✓ History shape valid: {data['total_count']} snapshots")
        
    def test_history_404_for_nonexistent_campaign(self):
        """Non-existent campaign should return 404"""
        response = requests.get(f"{BASE_URL}/api/research/{FAKE_CAMPAIGN_ID}/ads-intel/history")
        assert response.status_code == 404
        print(f"✓ History on non-existent campaign returns 404")


class TestAdCardSchema:
    """Test AdCard schema if data exists"""
    
    def test_ad_card_has_required_fields(self):
        """Each ad card should have required fields for frontend display"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data["has_data"]:
            pytest.skip("No ads data available yet")
            
        latest = data["latest"]
        all_ads = (latest.get("competitor_winners", {}).get("ads", []) + 
                   latest.get("category_winners", {}).get("ads", []))
        
        if not all_ads:
            pytest.skip("No ads in snapshot")
            
        # Check first few ads
        for i, ad in enumerate(all_ads[:5]):
            assert "ad_id" in ad, f"Ad {i} missing ad_id"
            assert "publisher_platform" in ad, f"Ad {i} missing publisher_platform"
            assert "lens" in ad, f"Ad {i} missing lens"
            assert "why_shortlisted" in ad, f"Ad {i} missing why_shortlisted"
            
            # Lens should be valid
            assert ad["lens"] in ["competitor", "category"], f"Invalid lens: {ad['lens']}"
            
            # Platform should be valid
            valid_platforms = {"facebook", "instagram", "tiktok", "unknown"}
            assert ad["publisher_platform"] in valid_platforms, f"Invalid platform: {ad['publisher_platform']}"
            
            print(f"  Ad {i}: {ad['publisher_platform']}, lens={ad['lens']}, running_days={ad.get('running_days')}")
            
        print(f"✓ {len(all_ads)} ad cards validated")


class TestAdsIntelSnapshotFields:
    """Test snapshot has all required fields for frontend"""
    
    def test_snapshot_has_audit(self):
        """Snapshot should have audit info"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data["has_data"]:
            pytest.skip("No ads data available yet")
            
        latest = data["latest"]
        
        assert "audit" in latest, "Missing audit field"
        audit = latest["audit"]
        assert "api_calls" in audit, "Missing api_calls in audit"
        assert "total_ads_seen" in audit, "Missing total_ads_seen"
        assert "kept" in audit, "Missing kept count"
        
        print(f"✓ Audit: {audit['api_calls']} API calls, {audit['total_ads_seen']} seen, {audit['kept']} kept")
        
    def test_snapshot_has_inputs(self):
        """Snapshot should have inputs showing what was searched"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/ads-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data["has_data"]:
            pytest.skip("No ads data available yet")
            
        latest = data["latest"]
        
        assert "inputs" in latest, "Missing inputs field"
        inputs = latest["inputs"]
        
        # Check expected input fields
        assert "geo" in inputs, "Missing geo in inputs"
        assert "competitor_domains" in inputs, "Missing competitor_domains"
        assert "category_queries" in inputs, "Missing category_queries"
        assert "platforms" in inputs, "Missing platforms"
        
        print(f"✓ Inputs: {len(inputs.get('competitor_domains', []))} competitor domains, {len(inputs.get('category_queries', []))} category queries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
