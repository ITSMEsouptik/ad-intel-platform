"""
Data Enrichment Quality Validation Tests
Tests for Competitors and Search Demand modules - iteration 40
Validates the bug fixes for:
1. Forum Queries now rendering (object format {reddit:[], quora:[]})
2. Competitors breadcrumb (no undefined industry field, no leading arrow)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"


class TestCompetitorsAPI:
    """Tests for /api/research/{campaign_id}/competitors/latest endpoint"""

    def test_competitors_endpoint_returns_data(self):
        """Test that competitors endpoint returns data"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        data = response.json()
        assert data.get("has_data") is True
        assert "latest" in data
        print("PASS: Competitors endpoint returns data with has_data=true")

    def test_competitors_has_four_competitors(self):
        """Test that we have 4 competitors"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        data = response.json()
        competitors = data.get("latest", {}).get("competitors", [])
        assert len(competitors) == 4, f"Expected 4 competitors, got {len(competitors)}"
        print(f"PASS: Found {len(competitors)} competitors")

    def test_competitors_have_all_required_fields(self):
        """Test that each competitor has all required fields"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        data = response.json()
        competitors = data.get("latest", {}).get("competitors", [])
        
        required_fields = ["name", "website", "what_they_do", "positioning", "why_competitor", 
                          "price_tier", "strengths", "weaknesses", "ad_strategy_summary", "social_presence"]
        
        for comp in competitors:
            for field in required_fields:
                assert field in comp, f"Competitor {comp.get('name')} missing field: {field}"
            # Validate arrays have content
            assert len(comp.get("strengths", [])) > 0, f"{comp.get('name')} has no strengths"
            assert len(comp.get("weaknesses", [])) > 0, f"{comp.get('name')} has no weaknesses"
        print("PASS: All 4 competitors have all required fields with content")

    def test_breadcrumb_no_undefined_industry(self):
        """Test that inputs_used has no undefined industry field (bug fix verification)"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        data = response.json()
        inputs_used = data.get("latest", {}).get("inputs_used", {})
        
        # industry field should NOT be present OR should be None
        industry = inputs_used.get("industry")
        assert industry is None, f"Expected industry to be None/absent, got: {industry}"
        
        # subcategory and niche should be present
        assert inputs_used.get("subcategory") is not None, "subcategory should be present"
        assert inputs_used.get("niche") is not None, "niche should be present"
        print(f"PASS: Breadcrumb data correct - subcategory={inputs_used.get('subcategory')}, niche={inputs_used.get('niche')}, industry=None")

    def test_market_overview_has_all_four_fields(self):
        """Test that market_overview has all 4 fields"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        data = response.json()
        market_overview = data.get("latest", {}).get("market_overview", {})
        
        required_fields = ["competitive_density", "dominant_player_type", "market_insight", "ad_landscape_note"]
        for field in required_fields:
            assert field in market_overview, f"market_overview missing field: {field}"
            assert market_overview.get(field), f"market_overview.{field} is empty"
        print("PASS: market_overview has all 4 required fields with content")


class TestSearchIntentAPI:
    """Tests for /api/research/{campaign_id}/search-intent/latest endpoint"""

    def test_search_intent_endpoint_returns_data(self):
        """Test that search-intent endpoint returns data"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        assert data.get("has_data") is True
        assert "latest" in data
        print("PASS: Search Intent endpoint returns data with has_data=true")

    def test_top_10_queries_present(self):
        """Test that top_10_queries has 10 queries"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        top_queries = data.get("latest", {}).get("top_10_queries", [])
        assert len(top_queries) == 10, f"Expected 10 top queries, got {len(top_queries)}"
        print(f"PASS: Found {len(top_queries)} top queries")

    def test_ad_keyword_queries_present(self):
        """Test that ad_keyword_queries has 35 keywords"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        ad_keywords = data.get("latest", {}).get("ad_keyword_queries", [])
        assert len(ad_keywords) == 35, f"Expected 35 ad keywords, got {len(ad_keywords)}"
        print(f"PASS: Found {len(ad_keywords)} ad keywords")

    def test_intent_buckets_have_all_categories(self):
        """Test that intent_buckets has all 5 categories"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        intent_buckets = data.get("latest", {}).get("intent_buckets", {})
        
        expected_buckets = ["price", "trust", "urgency", "comparison", "general"]
        for bucket in expected_buckets:
            assert bucket in intent_buckets, f"Missing intent bucket: {bucket}"
        print(f"PASS: Found all intent buckets: {list(intent_buckets.keys())}")

    def test_forum_queries_object_format(self):
        """Test that forum_queries is an object with reddit and quora arrays (BUG FIX VERIFICATION)"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        forum_queries = data.get("latest", {}).get("forum_queries", {})
        
        # CRITICAL: forum_queries must be an object, not an array
        assert isinstance(forum_queries, dict), f"forum_queries should be dict, got {type(forum_queries).__name__}"
        
        # Must have reddit and quora keys
        assert "reddit" in forum_queries, "forum_queries missing 'reddit' key"
        assert "quora" in forum_queries, "forum_queries missing 'quora' key"
        
        # Each should be an array
        assert isinstance(forum_queries.get("reddit"), list), "reddit should be a list"
        assert isinstance(forum_queries.get("quora"), list), "quora should be a list"
        
        print(f"PASS: forum_queries is object format with reddit={len(forum_queries.get('reddit', []))} and quora={len(forum_queries.get('quora', []))}")

    def test_forum_queries_have_15_each(self):
        """Test that forum_queries has 15 reddit and 15 quora queries"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        forum_queries = data.get("latest", {}).get("forum_queries", {})
        
        reddit_count = len(forum_queries.get("reddit", []))
        quora_count = len(forum_queries.get("quora", []))
        
        assert reddit_count == 15, f"Expected 15 reddit queries, got {reddit_count}"
        assert quora_count == 15, f"Expected 15 quora queries, got {quora_count}"
        print(f"PASS: Forum queries count correct - Reddit: {reddit_count}, Quora: {quora_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
