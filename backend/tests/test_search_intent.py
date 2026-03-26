"""
Test Search Intent Module - Research Foundation
Tests for POST /api/research/{campaignId}/search-intent/run
Tests for GET /api/research/{campaignId}/search-intent/latest
Tests for GET /api/research/{campaignId}
"""

import pytest
import requests
import os
from datetime import datetime

# Use public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign ID with existing Step 2 data
TEST_CAMPAIGN_ID = "21ec9a20-7747-4353-abe4-2f6881365c5b"


class TestSearchIntentLatest:
    """Tests for GET /api/research/{campaignId}/search-intent/latest"""
    
    def test_get_latest_returns_200(self):
        """GET /search-intent/latest returns 200 for existing campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_get_latest_has_required_fields(self):
        """Response has campaign_id, has_data, snapshot, refresh_due_in_days"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        assert "campaign_id" in data, "Missing campaign_id"
        assert "has_data" in data, "Missing has_data"
        assert data["campaign_id"] == TEST_CAMPAIGN_ID
    
    def test_get_latest_snapshot_structure(self):
        """Snapshot has correct structure when has_data=True"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data.get("snapshot")
            assert snapshot is not None, "Snapshot should exist when has_data=True"
            
            # Required snapshot fields
            assert "version" in snapshot, "Missing version"
            assert "captured_at" in snapshot, "Missing captured_at"
            assert "refresh_due_at" in snapshot, "Missing refresh_due_at"
            assert "inputs_used" in snapshot, "Missing inputs_used"
            assert "seed_phrases" in snapshot, "Missing seed_phrases"
            assert "top_queries" in snapshot, "Missing top_queries"
            assert "buckets" in snapshot, "Missing buckets"
            assert "derived" in snapshot, "Missing derived"
            assert "delta" in snapshot, "Missing delta"
    
    def test_get_latest_buckets_structure(self):
        """Buckets has all 5 intent categories"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            buckets = data["snapshot"].get("buckets", {})
            
            # All 5 buckets must exist
            expected_buckets = ["price", "trust", "urgency", "comparison", "general"]
            for bucket in expected_buckets:
                assert bucket in buckets, f"Missing bucket: {bucket}"
                assert isinstance(buckets[bucket], list), f"Bucket {bucket} should be a list"
    
    def test_get_latest_derived_outputs(self):
        """Derived outputs has ad_keyword_queries and forum_queries"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            derived = data["snapshot"].get("derived", {})
            
            assert "ad_keyword_queries" in derived, "Missing ad_keyword_queries"
            assert "forum_queries" in derived, "Missing forum_queries"
            assert isinstance(derived["ad_keyword_queries"], list)
            assert isinstance(derived["forum_queries"], list)
    
    def test_get_latest_refresh_due_in_days(self):
        """refresh_due_in_days is a non-negative integer"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            refresh_days = data.get("refresh_due_in_days")
            assert refresh_days is not None, "Missing refresh_due_in_days"
            assert isinstance(refresh_days, int), "refresh_due_in_days should be int"
            assert refresh_days >= 0, "refresh_due_in_days should be non-negative"
    
    def test_get_latest_404_for_invalid_campaign(self):
        """Returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/search-intent/latest")
        assert response.status_code == 404


class TestSearchIntentRun:
    """Tests for POST /api/research/{campaignId}/search-intent/run"""
    
    def test_run_returns_200(self):
        """POST /search-intent/run returns 200 for valid campaign"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_run_response_structure(self):
        """Run response has campaign_id, status, snapshot, message"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run")
        data = response.json()
        
        assert "campaign_id" in data, "Missing campaign_id"
        assert "status" in data, "Missing status"
        assert "snapshot" in data, "Missing snapshot"
        assert "message" in data, "Missing message"
        
        assert data["campaign_id"] == TEST_CAMPAIGN_ID
        assert data["status"] in ["success", "partial", "low_data", "failed"]
    
    def test_run_snapshot_has_queries(self):
        """Run generates queries in buckets"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run")
        data = response.json()
        
        if data["status"] != "failed":
            snapshot = data.get("snapshot")
            assert snapshot is not None
            
            # Should have some queries
            total_queries = sum(len(v) for v in snapshot.get("buckets", {}).values())
            assert total_queries > 0, "Should have at least some queries"
    
    def test_run_404_for_invalid_campaign(self):
        """Returns 404 for non-existent campaign"""
        response = requests.post(f"{BASE_URL}/api/research/invalid-campaign-id/search-intent/run")
        assert response.status_code == 404
    
    def test_run_400_without_step2(self):
        """Returns 400 if Step 2 not completed"""
        # Create a new campaign without Step 2
        brief_data = {
            "website_url": "https://test-no-step2.example.com",
            "primary_goal": "sales_orders",
            "success_definition": "Test",
            "country": "United States",
            "city_or_region": "New York",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "not_sure",
            "name": "Test User",
            "email": "test-search-intent@example.com"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=brief_data)
        if create_response.status_code == 200:
            new_campaign_id = create_response.json().get("campaign_brief_id")
            
            # Try to run search intent without Step 2
            run_response = requests.post(f"{BASE_URL}/api/research/{new_campaign_id}/search-intent/run")
            assert run_response.status_code == 400, "Should return 400 without Step 2"


class TestResearchPack:
    """Tests for GET /api/research/{campaignId}"""
    
    def test_get_research_pack_returns_200(self):
        """GET /research/{campaignId} returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}")
        assert response.status_code == 200
    
    def test_get_research_pack_structure(self):
        """Research pack has correct structure"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}")
        data = response.json()
        
        assert "campaign_id" in data
        assert "has_data" in data
        
        if data.get("has_data"):
            assert "research_pack_id" in data
            assert "sources" in data
            assert "search_intent" in data["sources"]
    
    def test_get_research_pack_search_intent_source(self):
        """Search intent source has latest and history"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}")
        data = response.json()
        
        if data.get("has_data"):
            search_intent = data["sources"].get("search_intent", {})
            assert "latest" in search_intent, "Missing latest in search_intent"
            assert "history" in search_intent, "Missing history in search_intent"
    
    def test_get_research_pack_404_for_invalid_campaign(self):
        """Returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id")
        assert response.status_code == 404


class TestSearchIntentHistory:
    """Tests for GET /api/research/{campaignId}/search-intent/history"""
    
    def test_get_history_returns_200(self):
        """GET /search-intent/history returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/history")
        assert response.status_code == 200
    
    def test_get_history_structure(self):
        """History response has correct structure"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/history")
        data = response.json()
        
        assert "campaign_id" in data
        assert "snapshots" in data
        assert "total_count" in data
        
        assert isinstance(data["snapshots"], list)
        assert isinstance(data["total_count"], int)


class TestInputsUsedTracking:
    """Tests for inputs_used field in snapshots"""
    
    def test_inputs_used_has_geo(self):
        """inputs_used has geo with city, country, language"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            inputs_used = data["snapshot"].get("inputs_used", {})
            geo = inputs_used.get("geo", {})
            
            assert "city" in geo, "Missing city in geo"
            assert "country" in geo, "Missing country in geo"
            assert "language" in geo, "Missing language in geo"
    
    def test_inputs_used_has_seeds(self):
        """inputs_used has seeds list"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            inputs_used = data["snapshot"].get("inputs_used", {})
            seeds = inputs_used.get("seeds", [])
            
            assert isinstance(seeds, list), "seeds should be a list"
    
    def test_inputs_used_has_negative_keywords(self):
        """inputs_used has negative_keywords list"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            inputs_used = data["snapshot"].get("inputs_used", {})
            negative_keywords = inputs_used.get("negative_keywords", [])
            
            assert isinstance(negative_keywords, list), "negative_keywords should be a list"
            assert len(negative_keywords) > 0, "Should have negative keywords"


class TestDeltaTracking:
    """Tests for delta field in snapshots"""
    
    def test_delta_structure(self):
        """Delta has required fields"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            delta = data["snapshot"].get("delta", {})
            
            assert "new_queries_count" in delta, "Missing new_queries_count"
            assert "removed_queries_count" in delta, "Missing removed_queries_count"
            assert "notable_new_queries" in delta, "Missing notable_new_queries"
            
            assert isinstance(delta["new_queries_count"], int)
            assert isinstance(delta["removed_queries_count"], int)
            assert isinstance(delta["notable_new_queries"], list)


class TestQueryCounts:
    """Tests for query count fields"""
    
    def test_suggestions_counts(self):
        """Snapshot has raw and final suggestion counts"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            
            assert "suggestions_raw_count" in snapshot
            assert "suggestions_final_count" in snapshot
            
            assert isinstance(snapshot["suggestions_raw_count"], int)
            assert isinstance(snapshot["suggestions_final_count"], int)
            assert snapshot["suggestions_raw_count"] >= 0
            assert snapshot["suggestions_final_count"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
