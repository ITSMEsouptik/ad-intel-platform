"""
Test Search Intent BRP Pipeline - v2 Module
Tests for POST /api/research/{campaignId}/search-intent/run
Tests for GET /api/research/{campaignId}/search-intent/latest

Focus Areas:
1. BRP (Business Relevance Profile) population
2. Relevance Gate audit stats
3. Intent buckets with all 5 keys
4. Top 10 queries
5. Ad keyword queries
6. Forum queries

Test Campaign: da87033e-7b60-470f-acf2-eb0ff25bbab4 (has Step 2 data completed)
"""

import pytest
import requests
import os
from datetime import datetime

# Use public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign ID with Step 2 data completed (as per the request)
TEST_CAMPAIGN_ID = "da87033e-7b60-470f-acf2-eb0ff25bbab4"


class TestSearchIntentLatestBRP:
    """Tests for BRP data in GET /api/research/{campaignId}/search-intent/latest"""
    
    def test_latest_returns_200(self):
        """GET /search-intent/latest returns 200 for campaign with Step 2 data"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_latest_has_has_data_and_status(self):
        """Response has has_data=true and status for campaign with data"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        assert "has_data" in data, "Missing has_data field"
        assert data["has_data"] == True, "has_data should be True for campaign with data"
        assert "status" in data, "Missing status field"
        assert data["status"] in ["fresh", "stale"], f"Invalid status: {data['status']}"
    
    def test_brp_is_populated(self):
        """BRP (Business Relevance Profile) exists and is populated"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        assert data.get("has_data"), "No data available"
        snapshot = data.get("latest")
        assert snapshot is not None, "Missing latest snapshot"
        
        brp = snapshot.get("brp")
        assert brp is not None, "Missing BRP in snapshot"
    
    def test_brp_has_business_model(self):
        """BRP has business_model field (service_booking, ecommerce, saas, app, unknown)"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        brp = data["latest"]["brp"]
        assert "business_model" in brp, "Missing business_model in BRP"
        assert brp["business_model"] in ["service_booking", "ecommerce", "saas", "app", "unknown"], \
            f"Invalid business_model: {brp['business_model']}"
    
    def test_brp_has_service_terms(self):
        """BRP has service_terms list populated"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        brp = data["latest"]["brp"]
        assert "service_terms" in brp, "Missing service_terms in BRP"
        assert isinstance(brp["service_terms"], list), "service_terms should be a list"
        assert len(brp["service_terms"]) > 0, "service_terms should not be empty"
        print(f"Service terms: {brp['service_terms'][:5]}")
    
    def test_brp_has_brand_terms(self):
        """BRP has brand_terms list"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        brp = data["latest"]["brp"]
        assert "brand_terms" in brp, "Missing brand_terms in BRP"
        assert isinstance(brp["brand_terms"], list), "brand_terms should be a list"
        print(f"Brand terms: {brp['brand_terms']}")
    
    def test_brp_has_category_terms(self):
        """BRP has category_terms list"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        brp = data["latest"]["brp"]
        assert "category_terms" in brp, "Missing category_terms in BRP"
        assert isinstance(brp["category_terms"], list), "category_terms should be a list"
        print(f"Category terms: {brp['category_terms']}")
    
    def test_brp_has_geo_terms(self):
        """BRP has geo_terms list"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        brp = data["latest"]["brp"]
        assert "geo_terms" in brp, "Missing geo_terms in BRP"
        assert isinstance(brp["geo_terms"], list), "geo_terms should be a list"
        # Should contain "near me" at minimum
        assert "near me" in brp["geo_terms"], "geo_terms should contain 'near me'"
        print(f"Geo terms: {brp['geo_terms']}")


class TestSearchIntentRelevanceGateAudit:
    """Tests for relevance_gate audit stats in stats field"""
    
    def test_stats_has_relevance_gate(self):
        """stats field contains relevance_gate object"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        stats = data["latest"]["stats"]
        assert "relevance_gate" in stats, "Missing relevance_gate in stats"
        assert stats["relevance_gate"] is not None, "relevance_gate should not be null"
    
    def test_relevance_gate_has_raw_count(self):
        """relevance_gate has raw_count field"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        gate = data["latest"]["stats"]["relevance_gate"]
        assert "raw_count" in gate, "Missing raw_count in relevance_gate"
        assert isinstance(gate["raw_count"], int), "raw_count should be an integer"
        assert gate["raw_count"] >= 0, "raw_count should be non-negative"
        print(f"Raw count: {gate['raw_count']}")
    
    def test_relevance_gate_has_kept_count(self):
        """relevance_gate has kept_count field"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        gate = data["latest"]["stats"]["relevance_gate"]
        assert "kept_count" in gate, "Missing kept_count in relevance_gate"
        assert isinstance(gate["kept_count"], int), "kept_count should be an integer"
        assert gate["kept_count"] >= 0, "kept_count should be non-negative"
        print(f"Kept count: {gate['kept_count']}")
    
    def test_relevance_gate_has_rejection_counts(self):
        """relevance_gate has all rejection reason counts"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        gate = data["latest"]["stats"]["relevance_gate"]
        
        # All rejection reason fields
        rejection_fields = [
            "rejected_geo_mismatch",
            "rejected_model_block",
            "rejected_too_generic",
            "rejected_no_relevance",
            "rejected_junk",
            "rejected_length"
        ]
        
        for field in rejection_fields:
            assert field in gate, f"Missing {field} in relevance_gate"
            assert isinstance(gate[field], int), f"{field} should be an integer"
            assert gate[field] >= 0, f"{field} should be non-negative"
        
        print(f"Rejection stats: geo={gate['rejected_geo_mismatch']}, model={gate['rejected_model_block']}, "
              f"generic={gate['rejected_too_generic']}, no_relevance={gate['rejected_no_relevance']}, "
              f"junk={gate['rejected_junk']}, length={gate['rejected_length']}")
    
    def test_relevance_gate_math_consistency(self):
        """raw_count = kept_count + sum of all rejections"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        gate = data["latest"]["stats"]["relevance_gate"]
        
        total_rejected = (
            gate["rejected_geo_mismatch"] +
            gate["rejected_model_block"] +
            gate["rejected_too_generic"] +
            gate["rejected_no_relevance"] +
            gate["rejected_junk"] +
            gate["rejected_length"]
        )
        
        # Note: raw_count includes dedupe, so kept + rejected <= raw_count
        assert gate["kept_count"] + total_rejected <= gate["raw_count"], \
            f"Math inconsistency: kept({gate['kept_count']}) + rejected({total_rejected}) > raw({gate['raw_count']})"
        
        print(f"Gate math: {gate['raw_count']} raw -> {gate['kept_count']} kept, {total_rejected} rejected")


class TestSearchIntentIntentBuckets:
    """Tests for intent_buckets with all 5 keys"""
    
    def test_intent_buckets_exists(self):
        """intent_buckets field exists"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        snapshot = data["latest"]
        assert "intent_buckets" in snapshot, "Missing intent_buckets in snapshot"
        assert isinstance(snapshot["intent_buckets"], dict), "intent_buckets should be a dict"
    
    def test_intent_buckets_has_all_5_keys(self):
        """intent_buckets has all 5 bucket keys: price, trust, urgency, comparison, general"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        buckets = data["latest"]["intent_buckets"]
        expected_keys = ["price", "trust", "urgency", "comparison", "general"]
        
        for key in expected_keys:
            assert key in buckets, f"Missing bucket: {key}"
            assert isinstance(buckets[key], list), f"Bucket {key} should be a list"
        
        print(f"Bucket counts: price={len(buckets['price'])}, trust={len(buckets['trust'])}, "
              f"urgency={len(buckets['urgency'])}, comparison={len(buckets['comparison'])}, general={len(buckets['general'])}")
    
    def test_bucket_queries_are_strings(self):
        """All bucket queries are non-empty strings"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        buckets = data["latest"]["intent_buckets"]
        
        for bucket_name, queries in buckets.items():
            for query in queries:
                assert isinstance(query, str), f"Query in {bucket_name} should be string, got {type(query)}"
                assert len(query) > 0, f"Query in {bucket_name} should not be empty"


class TestSearchIntentTop10Queries:
    """Tests for top_10_queries"""
    
    def test_top_10_queries_exists(self):
        """top_10_queries field exists"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        snapshot = data["latest"]
        assert "top_10_queries" in snapshot, "Missing top_10_queries in snapshot"
        assert isinstance(snapshot["top_10_queries"], list), "top_10_queries should be a list"
    
    def test_top_10_queries_max_10(self):
        """top_10_queries has maximum 10 items"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        queries = data["latest"]["top_10_queries"]
        assert len(queries) <= 10, f"top_10_queries should have max 10 items, got {len(queries)}"
        print(f"Top 10 queries ({len(queries)}): {queries}")
    
    def test_top_10_queries_are_strings(self):
        """All top_10_queries are non-empty strings"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        for query in data["latest"]["top_10_queries"]:
            assert isinstance(query, str), f"Query should be string, got {type(query)}"
            assert len(query) > 0, "Query should not be empty"


class TestSearchIntentAdKeywords:
    """Tests for ad_keyword_queries"""
    
    def test_ad_keyword_queries_exists(self):
        """ad_keyword_queries field exists"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        snapshot = data["latest"]
        assert "ad_keyword_queries" in snapshot, "Missing ad_keyword_queries in snapshot"
        assert isinstance(snapshot["ad_keyword_queries"], list), "ad_keyword_queries should be a list"
    
    def test_ad_keyword_queries_max_25(self):
        """ad_keyword_queries has maximum 25 items"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        queries = data["latest"]["ad_keyword_queries"]
        assert len(queries) <= 25, f"ad_keyword_queries should have max 25 items, got {len(queries)}"
        print(f"Ad keyword queries ({len(queries)}): {queries[:5]}...")


class TestSearchIntentForumQueries:
    """Tests for forum_queries"""
    
    def test_forum_queries_exists(self):
        """forum_queries field exists as object"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        snapshot = data["latest"]
        assert "forum_queries" in snapshot, "Missing forum_queries in snapshot"
        assert isinstance(snapshot["forum_queries"], dict), "forum_queries should be an object"
    
    def test_forum_queries_has_reddit_and_quora(self):
        """forum_queries has reddit and quora arrays"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        forum = data["latest"]["forum_queries"]
        
        assert "reddit" in forum, "Missing reddit in forum_queries"
        assert "quora" in forum, "Missing quora in forum_queries"
        assert isinstance(forum["reddit"], list), "forum_queries.reddit should be a list"
        assert isinstance(forum["quora"], list), "forum_queries.quora should be a list"
        
        print(f"Forum queries: reddit={len(forum['reddit'])}, quora={len(forum['quora'])}")
    
    def test_forum_queries_format(self):
        """Forum queries have site:reddit.com or site:quora.com prefix"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        data = response.json()
        
        forum = data["latest"]["forum_queries"]
        
        for query in forum["reddit"][:3]:
            assert "site:reddit.com" in query, f"Reddit query should contain site:reddit.com: {query}"
        
        for query in forum["quora"][:3]:
            assert "site:quora.com" in query, f"Quora query should contain site:quora.com: {query}"


class TestSearchIntentRunEndpoint:
    """Tests for POST /api/research/{campaignId}/search-intent/run"""
    
    def test_run_returns_200(self):
        """POST /search-intent/run returns 200 for campaign with Step 2"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run", timeout=60)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_run_response_has_status(self):
        """Run response has status field"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run", timeout=60)
        data = response.json()
        
        assert "status" in data, "Missing status in response"
        assert data["status"] in ["success", "partial", "low_data", "failed"], f"Invalid status: {data['status']}"
        print(f"Run status: {data['status']}")
    
    def test_run_response_has_snapshot_with_brp(self):
        """Run response snapshot has brp field"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run", timeout=60)
        data = response.json()
        
        assert "snapshot" in data, "Missing snapshot in response"
        assert data["snapshot"] is not None, "Snapshot should not be null"
        assert "brp" in data["snapshot"], "Missing brp in snapshot"
    
    def test_run_response_has_relevance_gate_stats(self):
        """Run response has stats.relevance_gate"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run", timeout=60)
        data = response.json()
        
        assert "stats" in data["snapshot"], "Missing stats in snapshot"
        assert "relevance_gate" in data["snapshot"]["stats"], "Missing relevance_gate in stats"
        
        gate = data["snapshot"]["stats"]["relevance_gate"]
        print(f"Run kept {gate['kept_count']} of {gate['raw_count']} queries")
    
    def test_run_response_has_all_outputs(self):
        """Run response has top_10_queries, intent_buckets, ad_keyword_queries, forum_queries"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/run", timeout=60)
        data = response.json()
        
        snapshot = data["snapshot"]
        
        assert "top_10_queries" in snapshot, "Missing top_10_queries"
        assert "intent_buckets" in snapshot, "Missing intent_buckets"
        assert "ad_keyword_queries" in snapshot, "Missing ad_keyword_queries"
        assert "forum_queries" in snapshot, "Missing forum_queries"


class TestSearchIntentErrorCases:
    """Tests for error cases"""
    
    def test_latest_404_for_invalid_campaign(self):
        """GET /search-intent/latest returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-uuid-12345/search-intent/latest")
        assert response.status_code == 404
    
    def test_run_404_for_invalid_campaign(self):
        """POST /search-intent/run returns 404 for non-existent campaign"""
        response = requests.post(f"{BASE_URL}/api/research/invalid-uuid-12345/search-intent/run")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
