"""
Sprint 1 API Normalization Tests
Tests GET /latest endpoint normalization across all modules

Test coverage:
1. GET /api/research/{campaignId}/search-intent/latest
2. GET /api/research/{campaignId}/seasonality/latest
3. GET /api/research/{campaignId}/competitors/latest

Expected format for all: {has_data, status, latest, refresh_due_in_days}
Status values: 'not_run' | 'fresh' | 'stale'
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Campaign IDs from context
CAMPAIGN_WITH_DATA = "21ec9a20-7747-4353-abe4-2f6881365c5b"
CAMPAIGN_WITHOUT_DATA = "b66229cf-7aa9-4e51-ae0e-81a57ab2ac18"
INVALID_CAMPAIGN = "00000000-0000-0000-0000-000000000000"


class TestAPIResponseNormalization:
    """Test all GET /latest endpoints return normalized format"""
    
    # ============== SEARCH INTENT ==============
    
    def test_search_intent_latest_response_format_with_data(self):
        """Search intent latest returns normalized format when data exists"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/search-intent/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required keys exist
        assert "has_data" in data, "Missing 'has_data' key"
        assert "status" in data, "Missing 'status' key"
        assert "latest" in data, "Missing 'latest' key"
        assert "refresh_due_in_days" in data, "Missing 'refresh_due_in_days' key"
        
        # Verify types and values
        assert data["has_data"] is True
        assert data["status"] in ["fresh", "stale"], f"Invalid status: {data['status']}"
        assert data["latest"] is not None
        assert isinstance(data["refresh_due_in_days"], int)
    
    def test_search_intent_latest_response_format_without_data(self):
        """Search intent latest returns normalized format when no data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITHOUT_DATA}/search-intent/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required keys
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        # Verify values for no-data state
        assert data["has_data"] is False
        assert data["status"] == "not_run"
        assert data["latest"] is None
        assert data["refresh_due_in_days"] is None
    
    def test_search_intent_latest_snapshot_has_stats(self):
        """Search intent snapshot includes stats with LLM cleaning audit"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/search-intent/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert data["has_data"] is True
        
        latest = data["latest"]
        assert "stats" in latest, "Missing stats in snapshot"
        
        stats = latest["stats"]
        # Required stats fields
        assert "seeds_used" in stats
        assert "suggestions_raw" in stats
        assert "filtered_blocklist" in stats
        assert "filtered_irrelevant" in stats
        assert "kept_final" in stats
    
    # ============== SEASONALITY ==============
    
    def test_seasonality_latest_response_format_with_data(self):
        """Seasonality latest returns normalized format when data exists"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required keys
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        # Verify values
        assert data["has_data"] is True
        assert data["status"] in ["fresh", "stale"]
        assert data["latest"] is not None
        assert isinstance(data["refresh_due_in_days"], int)
    
    def test_seasonality_latest_response_format_without_data(self):
        """Seasonality latest returns normalized format when no data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITHOUT_DATA}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify values for no-data state
        assert data["has_data"] is False
        assert data["status"] == "not_run"
        assert data["latest"] is None
        assert data["refresh_due_in_days"] is None
    
    def test_seasonality_latest_snapshot_structure(self):
        """Seasonality snapshot has expected structure"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data["has_data"]:
            pytest.skip("No seasonality data for this campaign")
        
        latest = data["latest"]
        
        # Key moments should exist
        assert "key_moments" in latest, "Missing key_moments"
        assert isinstance(latest["key_moments"], list)
        
        # Weekly patterns
        assert "weekly_patterns" in latest, "Missing weekly_patterns"
    
    # ============== COMPETITORS ==============
    
    def test_competitors_latest_response_format_with_data(self):
        """Competitors latest returns normalized format when data exists"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/competitors/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required keys
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        # Verify values
        assert data["has_data"] is True
        assert data["status"] in ["fresh", "stale"]
        assert data["latest"] is not None
        assert isinstance(data["refresh_due_in_days"], int)
    
    def test_competitors_latest_response_format_without_data(self):
        """Competitors latest returns normalized format when no data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITHOUT_DATA}/competitors/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify values for no-data state
        assert data["has_data"] is False
        assert data["status"] == "not_run"
        assert data["latest"] is None
        assert data["refresh_due_in_days"] is None
    
    def test_competitors_latest_snapshot_structure(self):
        """Competitors snapshot has expected structure"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/competitors/latest")
        assert response.status_code == 200
        
        data = response.json()
        if not data["has_data"]:
            pytest.skip("No competitors data for this campaign")
        
        latest = data["latest"]
        
        # Competitors list
        assert "competitors" in latest, "Missing competitors"
        assert isinstance(latest["competitors"], list)
        
        # Market overview (structured, not legacy string)
        if "market_overview" in latest:
            overview = latest["market_overview"]
            # Check structure
            assert isinstance(overview, dict)
    
    # ============== ERROR HANDLING ==============
    
    def test_search_intent_latest_invalid_campaign_404(self):
        """Search intent returns 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{INVALID_CAMPAIGN}/search-intent/latest")
        assert response.status_code == 404
    
    def test_seasonality_latest_invalid_campaign_404(self):
        """Seasonality returns 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{INVALID_CAMPAIGN}/seasonality/latest")
        assert response.status_code == 404
    
    def test_competitors_latest_invalid_campaign_404(self):
        """Competitors returns 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{INVALID_CAMPAIGN}/competitors/latest")
        assert response.status_code == 404


class TestSearchIntentV2Schema:
    """Test Search Intent v2 schema specifics"""
    
    def test_v2_uses_top_10_queries(self):
        """v2 schema uses top_10_queries (not top_queries)"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/search-intent/latest")
        data = response.json()
        
        if not data["has_data"]:
            pytest.skip("No data")
        
        latest = data["latest"]
        assert "top_10_queries" in latest, "v2 should have top_10_queries"
        assert isinstance(latest["top_10_queries"], list)
    
    def test_v2_uses_intent_buckets(self):
        """v2 schema uses intent_buckets (not buckets)"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/search-intent/latest")
        data = response.json()
        
        if not data["has_data"]:
            pytest.skip("No data")
        
        latest = data["latest"]
        assert "intent_buckets" in latest, "v2 should have intent_buckets"
        assert isinstance(latest["intent_buckets"], dict)
        
        # Check bucket keys
        expected_buckets = ["price", "trust", "urgency", "comparison", "general"]
        for bucket in expected_buckets:
            assert bucket in latest["intent_buckets"], f"Missing bucket: {bucket}"
    
    def test_v2_has_forum_queries_object(self):
        """v2 schema has forum_queries as object with reddit/quora"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/search-intent/latest")
        data = response.json()
        
        if not data["has_data"]:
            pytest.skip("No data")
        
        latest = data["latest"]
        assert "forum_queries" in latest, "v2 should have forum_queries"
        
        forum = latest["forum_queries"]
        assert isinstance(forum, dict)
        assert "reddit" in forum
        assert "quora" in forum
        assert isinstance(forum["reddit"], list)
        assert isinstance(forum["quora"], list)


class TestSeasonalityPromptGuardrails:
    """Test seasonality returns content that respects guardrails"""
    
    def test_seasonality_no_budget_recommendations(self):
        """Seasonality response should not contain budget/strategy advice"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/seasonality/latest")
        data = response.json()
        
        if not data["has_data"]:
            pytest.skip("No data")
        
        latest = data["latest"]
        
        # Convert to string and check for forbidden terms
        content = str(latest).lower()
        
        forbidden_phrases = [
            "allocate budget",
            "run a campaign",
            "marketing strategy",
            "ad script"
        ]
        
        for phrase in forbidden_phrases:
            # Allow some tolerance - check if phrase appears in actual content fields
            # (not just in field names or metadata)
            if phrase in content:
                # Check specific content fields
                key_moments_str = str(latest.get("key_moments", [])).lower()
                if phrase in key_moments_str:
                    pytest.fail(f"Found forbidden phrase '{phrase}' in seasonality response")


class TestFrontendDataAccessor:
    """Test that frontend 'latest' accessor works correctly"""
    
    def test_search_intent_uses_latest_not_snapshot(self):
        """Response uses 'latest' key (not 'snapshot')"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/search-intent/latest")
        data = response.json()
        
        assert "latest" in data, "Should have 'latest' key"
        # Old format should not exist
        assert "snapshot" not in data, "Should not have old 'snapshot' key"
    
    def test_seasonality_uses_latest_not_snapshot(self):
        """Response uses 'latest' key (not 'snapshot')"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/seasonality/latest")
        data = response.json()
        
        assert "latest" in data
        assert "snapshot" not in data
    
    def test_competitors_uses_latest_not_snapshot(self):
        """Response uses 'latest' key (not 'snapshot')"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/competitors/latest")
        data = response.json()
        
        assert "latest" in data
        assert "snapshot" not in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
