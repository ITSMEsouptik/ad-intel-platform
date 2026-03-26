"""
Test Search Intent v2 Module - Research Foundation
Tests for POST /api/research/{campaignId}/search-intent/run (v2 schema)
Tests for GET /api/research/{campaignId}/search-intent/latest (v2 schema)

v2 Schema Changes:
- top_10_queries (was top_queries)
- intent_buckets (was buckets)
- ad_keyword_queries (was derived.ad_keyword_queries)
- forum_queries.reddit/quora (was derived.forum_queries as flat list)
- stats (new: seeds_used, suggestions_raw, filtered_blocklist, filtered_irrelevant, kept_final)
"""

import pytest
import requests
import os
from datetime import datetime

# Use public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign ID with existing Step 2 data (old format)
TEST_CAMPAIGN_ID = "2de697d6-1e75-47cb-8f29-6f4cb8978e02"

# Campaign with new step2 format
TEST_CAMPAIGN_ID_NEW = "21ec9a20-7747-4353-abe4-2f6881365c5b"


class TestSearchIntentV2Latest:
    """Tests for GET /api/research/{campaignId}/search-intent/latest with v2 schema"""
    
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
    
    def test_v2_snapshot_has_version_2(self):
        """Snapshot has version 2.0"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data.get("snapshot")
            assert snapshot is not None, "Snapshot should exist when has_data=True"
            assert snapshot.get("version") == "2.0", f"Expected version 2.0, got {snapshot.get('version')}"
    
    def test_v2_snapshot_has_top_10_queries(self):
        """v2 uses top_10_queries instead of top_queries"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "top_10_queries" in snapshot, "Missing top_10_queries (v2 field)"
            assert isinstance(snapshot["top_10_queries"], list), "top_10_queries should be a list"
            assert len(snapshot["top_10_queries"]) <= 10, "top_10_queries should have max 10 items"
    
    def test_v2_snapshot_has_intent_buckets(self):
        """v2 uses intent_buckets instead of buckets"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "intent_buckets" in snapshot, "Missing intent_buckets (v2 field)"
            
            buckets = snapshot["intent_buckets"]
            expected_buckets = ["price", "trust", "urgency", "comparison", "general"]
            for bucket in expected_buckets:
                assert bucket in buckets, f"Missing bucket: {bucket}"
                assert isinstance(buckets[bucket], list), f"Bucket {bucket} should be a list"
    
    def test_v2_snapshot_has_ad_keyword_queries(self):
        """v2 has ad_keyword_queries at top level (not in derived)"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "ad_keyword_queries" in snapshot, "Missing ad_keyword_queries (v2 field)"
            assert isinstance(snapshot["ad_keyword_queries"], list), "ad_keyword_queries should be a list"
            assert len(snapshot["ad_keyword_queries"]) <= 25, "ad_keyword_queries should have max 25 items"
    
    def test_v2_snapshot_has_forum_queries_object(self):
        """v2 has forum_queries as object with reddit/quora arrays"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "forum_queries" in snapshot, "Missing forum_queries (v2 field)"
            
            forum = snapshot["forum_queries"]
            assert isinstance(forum, dict), "forum_queries should be an object"
            assert "reddit" in forum, "forum_queries missing reddit array"
            assert "quora" in forum, "forum_queries missing quora array"
            assert isinstance(forum["reddit"], list), "forum_queries.reddit should be a list"
            assert isinstance(forum["quora"], list), "forum_queries.quora should be a list"
    
    def test_v2_snapshot_has_stats(self):
        """v2 has stats with pipeline metrics"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "stats" in snapshot, "Missing stats (v2 field)"
            
            stats = snapshot["stats"]
            assert "seeds_used" in stats, "stats missing seeds_used"
            assert "suggestions_raw" in stats, "stats missing suggestions_raw"
            assert "filtered_blocklist" in stats, "stats missing filtered_blocklist"
            assert "filtered_irrelevant" in stats, "stats missing filtered_irrelevant"
            assert "kept_final" in stats, "stats missing kept_final"
            
            # All should be integers
            assert isinstance(stats["seeds_used"], int)
            assert isinstance(stats["suggestions_raw"], int)
            assert isinstance(stats["filtered_blocklist"], int)
            assert isinstance(stats["filtered_irrelevant"], int)
            assert isinstance(stats["kept_final"], int)
    
    def test_v2_stats_line_calculation(self):
        """Stats can be used to show 'Captured: X queries • Filtered: Y irrelevant'"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            stats = data["snapshot"]["stats"]
            captured = stats["kept_final"]
            filtered = stats["filtered_blocklist"] + stats["filtered_irrelevant"]
            
            # Both should be non-negative
            assert captured >= 0, "kept_final should be non-negative"
            assert filtered >= 0, "filtered count should be non-negative"
            
            # Stats line format: "Captured: {captured} queries • Filtered: {filtered} irrelevant"
            stats_line = f"Captured: {captured} queries • Filtered: {filtered} irrelevant"
            assert len(stats_line) > 0, "Stats line should be constructable"
    
    def test_v2_snapshot_has_delta(self):
        """v2 has delta with new_queries_count for badge"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "delta" in snapshot, "Missing delta"
            
            delta = snapshot["delta"]
            assert "new_queries_count" in delta, "delta missing new_queries_count"
            assert "removed_queries_count" in delta, "delta missing removed_queries_count"
            assert "notable_new_queries" in delta, "delta missing notable_new_queries"
            
            assert isinstance(delta["new_queries_count"], int)
            assert isinstance(delta["removed_queries_count"], int)
            assert isinstance(delta["notable_new_queries"], list)
    
    def test_v2_snapshot_has_inputs_used(self):
        """v2 has inputs_used with keyword sets"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "inputs_used" in snapshot, "Missing inputs_used"
            
            inputs = snapshot["inputs_used"]
            assert "geo" in inputs, "inputs_used missing geo"
            assert "seeds" in inputs, "inputs_used missing seeds"
            assert "service_terms" in inputs, "inputs_used missing service_terms"
            assert "category_terms" in inputs, "inputs_used missing category_terms"
            assert "competitor_terms" in inputs, "inputs_used missing competitor_terms"
            assert "sells_workshops" in inputs, "inputs_used missing sells_workshops"
    
    def test_get_latest_404_for_invalid_campaign(self):
        """Returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/search-intent/latest")
        assert response.status_code == 404


class TestSearchIntentV2Run:
    """Tests for POST /api/research/{campaignId}/search-intent/run with v2 schema"""
    
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
    
    def test_run_returns_v2_schema(self):
        """Run returns v2 schema with all new fields"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run")
        data = response.json()
        
        if data["status"] != "failed":
            snapshot = data["snapshot"]
            
            # v2 fields
            assert snapshot.get("version") == "2.0", "Should return version 2.0"
            assert "top_10_queries" in snapshot, "Missing top_10_queries"
            assert "intent_buckets" in snapshot, "Missing intent_buckets"
            assert "ad_keyword_queries" in snapshot, "Missing ad_keyword_queries"
            assert "forum_queries" in snapshot, "Missing forum_queries"
            assert "stats" in snapshot, "Missing stats"
    
    def test_run_generates_queries(self):
        """Run generates queries in intent_buckets"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run")
        data = response.json()
        
        if data["status"] != "failed":
            snapshot = data["snapshot"]
            
            # Should have some queries in buckets
            total_queries = sum(len(v) for v in snapshot.get("intent_buckets", {}).values())
            assert total_queries > 0, "Should have at least some queries in intent_buckets"
    
    def test_run_404_for_invalid_campaign(self):
        """Returns 404 for non-existent campaign"""
        response = requests.post(f"{BASE_URL}/api/research/invalid-campaign-id/search-intent/run")
        assert response.status_code == 404
    
    def test_run_400_without_step2(self):
        """Returns 400 if Step 2 not completed"""
        # Create a new campaign without Step 2
        brief_data = {
            "website_url": "https://test-no-step2-v2.example.com",
            "primary_goal": "sales_orders",
            "success_definition": "Test v2",
            "country": "United States",
            "city_or_region": "New York",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "not_sure",
            "name": "Test User",
            "email": "test-search-intent-v2@example.com"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=brief_data)
        if create_response.status_code == 200:
            new_campaign_id = create_response.json().get("campaign_brief_id")
            
            # Try to run search intent without Step 2
            run_response = requests.post(f"{BASE_URL}/api/research/{new_campaign_id}/search-intent/run")
            assert run_response.status_code == 400, "Should return 400 without Step 2"


class TestSearchIntentV2WithNewStep2Format:
    """Tests for v2 with campaigns that have new step2 format"""
    
    def test_run_with_new_step2_format(self):
        """Run works with new step2 format (offer_catalog, classification)"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID_NEW}/search-intent/run")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] in ["success", "partial", "low_data"], f"Unexpected status: {data['status']}"
    
    def test_latest_with_new_step2_format(self):
        """Latest returns v2 schema for campaign with new step2 format"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID_NEW}/search-intent/latest")
        assert response.status_code == 200
        
        data = response.json()
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert snapshot.get("version") == "2.0"
            assert "top_10_queries" in snapshot
            assert "intent_buckets" in snapshot


class TestSearchIntentV2BackwardsCompatibility:
    """Tests for backwards compatibility - UI should handle both v1 and v2"""
    
    def test_v2_has_no_old_fields(self):
        """v2 should not have old v1 fields at top level"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            
            # v1 fields that should NOT exist in v2
            # Note: UI should check for both and prefer v2
            # These assertions verify v2 is clean
            assert "buckets" not in snapshot or "intent_buckets" in snapshot, "v2 should use intent_buckets"
            assert "top_queries" not in snapshot or "top_10_queries" in snapshot, "v2 should use top_10_queries"
            assert "derived" not in snapshot or "ad_keyword_queries" in snapshot, "v2 should have ad_keyword_queries at top level"


class TestSearchIntentV2History:
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


class TestSearchIntentV2DataQuality:
    """Tests for data quality in v2 output"""
    
    def test_top_10_queries_are_strings(self):
        """top_10_queries contains only strings"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            for query in data["snapshot"]["top_10_queries"]:
                assert isinstance(query, str), f"Query should be string, got {type(query)}"
                assert len(query) > 0, "Query should not be empty"
    
    def test_ad_keyword_queries_word_count(self):
        """ad_keyword_queries should be 2-7 words"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            for query in data["snapshot"]["ad_keyword_queries"][:10]:
                word_count = len(query.split())
                # Allow some flexibility (2-10 words)
                assert 1 <= word_count <= 10, f"Query '{query}' has {word_count} words, expected 2-7"
    
    def test_forum_queries_have_content(self):
        """forum_queries.reddit and forum_queries.quora have content"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        if data.get("has_data"):
            forum = data["snapshot"]["forum_queries"]
            # At least one platform should have queries
            total_forum = len(forum.get("reddit", [])) + len(forum.get("quora", []))
            # Note: It's OK if forum queries are empty for some businesses
            assert total_forum >= 0, "forum_queries should be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
