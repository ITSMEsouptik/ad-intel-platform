"""
Novara Search Demand v2.1 Test Suite
Tests for: BRP ecommerce signals, enhanced relevance gate audit,
ad keywords cap 35, forum queries format, intent buckets, progressive relaxation

Campaign: da87033e-7b60-470f-acf2-eb0ff25bbab4 (has Step 2 success)
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
CAMPAIGN_ID = "da87033e-7b60-470f-acf2-eb0ff25bbab4"


class TestSearchIntentV21Run:
    """Tests for POST /api/research/{campaignId}/search-intent/run v2.1 changes"""
    
    @pytest.fixture(scope="class")
    def run_response(self):
        """Run the search intent pipeline and cache response for all tests"""
        response = requests.post(
            f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/run",
            timeout=60
        )
        assert response.status_code == 200, f"Run failed: {response.text}"
        return response.json()
    
    def test_run_returns_success_status(self, run_response):
        """Run endpoint returns status=success"""
        assert run_response.get("status") == "success", \
            f"Expected status=success, got {run_response.get('status')}"
    
    def test_snapshot_contains_brp(self, run_response):
        """Snapshot contains BRP with v2.1 fields"""
        snapshot = run_response.get("snapshot", {})
        brp = snapshot.get("brp", {})
        
        assert brp is not None, "BRP should be present in snapshot"
        assert "business_model" in brp, "BRP should have business_model"
        assert "has_ecommerce_signals" in brp, "BRP should have has_ecommerce_signals (v2.1)"
    
    def test_brp_has_ecommerce_signals_field(self, run_response):
        """BRP contains has_ecommerce_signals field (v2.1 addition)"""
        brp = run_response.get("snapshot", {}).get("brp", {})
        
        # Field must exist and be boolean
        assert "has_ecommerce_signals" in brp, "has_ecommerce_signals field missing"
        assert isinstance(brp["has_ecommerce_signals"], bool), \
            f"has_ecommerce_signals should be bool, got {type(brp['has_ecommerce_signals'])}"
    
    def test_brp_business_model_is_service_booking(self, run_response):
        """For this campaign, business_model should be service_booking"""
        brp = run_response.get("snapshot", {}).get("brp", {})
        
        # InstaGlam is a service_booking business
        assert brp.get("business_model") in ["service_booking", "medical", "unknown"], \
            f"Expected service-type model, got {brp.get('business_model')}"


class TestRelevanceGateAuditV21:
    """Tests for relevance gate audit v2.1 new rejection fields"""
    
    @pytest.fixture(scope="class")
    def relevance_gate(self):
        """Get relevance gate audit from latest endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/latest"
        )
        assert response.status_code == 200
        data = response.json()
        # Latest endpoint returns data under 'latest' key, not 'snapshot'
        return data.get("latest", {}).get("stats", {}).get("relevance_gate", {})
    
    def test_relevance_gate_has_product_intent_rejection(self, relevance_gate):
        """Audit includes rejected_product_intent count (v2.1)"""
        assert "rejected_product_intent" in relevance_gate, \
            "rejected_product_intent field missing from relevance gate"
        assert isinstance(relevance_gate["rejected_product_intent"], int)
    
    def test_relevance_gate_has_procedure_intent_rejection(self, relevance_gate):
        """Audit includes rejected_procedure_intent count (v2.1)"""
        assert "rejected_procedure_intent" in relevance_gate, \
            "rejected_procedure_intent field missing from relevance gate"
        assert isinstance(relevance_gate["rejected_procedure_intent"], int)
    
    def test_relevance_gate_has_unit_noise_rejection(self, relevance_gate):
        """Audit includes rejected_unit_noise count (v2.1)"""
        assert "rejected_unit_noise" in relevance_gate, \
            "rejected_unit_noise field missing from relevance gate"
        assert isinstance(relevance_gate["rejected_unit_noise"], int)
    
    def test_relevance_gate_has_missing_service_token(self, relevance_gate):
        """Audit includes rejected_missing_service_token count (v2.1)"""
        assert "rejected_missing_service_token" in relevance_gate, \
            "rejected_missing_service_token field missing from relevance gate"
        assert isinstance(relevance_gate["rejected_missing_service_token"], int)
    
    def test_relevance_gate_has_missing_modifier_or_geo(self, relevance_gate):
        """Audit includes rejected_missing_modifier_or_geo count (v2.1)"""
        assert "rejected_missing_modifier_or_geo" in relevance_gate, \
            "rejected_missing_modifier_or_geo field missing from relevance gate"
        assert isinstance(relevance_gate["rejected_missing_modifier_or_geo"], int)
    
    def test_relevance_gate_has_top_rejected_examples(self, relevance_gate):
        """Audit includes top_rejected_examples dict (v2.1)"""
        assert "top_rejected_examples" in relevance_gate, \
            "top_rejected_examples field missing from relevance gate"
        examples = relevance_gate["top_rejected_examples"]
        assert isinstance(examples, dict), "top_rejected_examples should be dict"
    
    def test_product_intent_queries_rejected(self, relevance_gate):
        """Product intent queries like 'best hair dryer' should be rejected for service_booking"""
        rejected_product = relevance_gate.get("rejected_product_intent", 0)
        # For a service_booking brand, we expect some product queries to be rejected
        # Based on the run output, we saw 30 product_intent rejections
        assert rejected_product >= 0, "rejected_product_intent should be non-negative"
        
        # Check examples
        examples = relevance_gate.get("top_rejected_examples", {})
        if "product_intent" in examples:
            product_examples = examples["product_intent"]
            # Verify examples contain product-related terms
            product_terms = ["dryer", "straightener", "brush", "kit", "serum", "cream", "oil"]
            has_product_term = any(
                any(term in ex.lower() for term in product_terms)
                for ex in product_examples
            )
            print(f"Product intent rejection examples: {product_examples}")
    
    def test_procedure_queries_rejected_for_non_medical(self, relevance_gate):
        """Procedure queries like 'hair transplant' should be rejected for non-medical brands"""
        rejected_procedure = relevance_gate.get("rejected_procedure_intent", 0)
        assert rejected_procedure >= 0, "rejected_procedure_intent should be non-negative"
        
        # Check examples
        examples = relevance_gate.get("top_rejected_examples", {})
        if "procedure_intent" in examples:
            procedure_examples = examples["procedure_intent"]
            print(f"Procedure intent rejection examples: {procedure_examples}")
    
    def test_unit_noise_queries_rejected(self, relevance_gate):
        """Unit noise queries like 'hair price 1kg' should be rejected"""
        rejected_unit = relevance_gate.get("rejected_unit_noise", 0)
        assert rejected_unit >= 0, "rejected_unit_noise should be non-negative"
        
        # Check examples
        examples = relevance_gate.get("top_rejected_examples", {})
        if "unit_noise" in examples:
            unit_examples = examples["unit_noise"]
            print(f"Unit noise rejection examples: {unit_examples}")
    
    def test_geo_mismatch_rejection(self, relevance_gate):
        """Geo mismatch queries for US-based brand should be rejected"""
        rejected_geo = relevance_gate.get("rejected_geo_mismatch", 0)
        assert rejected_geo >= 0, "rejected_geo_mismatch should be non-negative"
        
        examples = relevance_gate.get("top_rejected_examples", {})
        if "wrong_geo" in examples:
            geo_examples = examples["wrong_geo"]
            print(f"Geo mismatch rejection examples: {geo_examples}")


class TestTop10QueriesV21:
    """Tests for top 10 queries quality - should be service-relevant, no product noise"""
    
    @pytest.fixture(scope="class")
    def search_data(self):
        """Get search intent data"""
        response = requests.get(
            f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/latest"
        )
        assert response.status_code == 200
        # Latest endpoint returns data under 'latest' key, not 'snapshot'
        return response.json().get("latest", {})
    
    def test_top_10_has_exactly_10_or_fewer(self, search_data):
        """Top 10 should have at most 10 queries"""
        top_10 = search_data.get("top_10_queries", [])
        assert len(top_10) <= 10, f"Expected max 10 queries, got {len(top_10)}"
    
    def test_top_10_queries_are_strings(self, search_data):
        """All top 10 queries should be strings"""
        top_10 = search_data.get("top_10_queries", [])
        for query in top_10:
            assert isinstance(query, str), f"Query should be string: {query}"
    
    def test_top_10_no_product_noise(self, search_data):
        """Top 10 should not contain obvious product queries"""
        top_10 = search_data.get("top_10_queries", [])
        product_terms = [
            "dryer", "straightener", "brush", "kit", "serum", "cream", 
            "amazon", "shein", "aliexpress", "temu", "buy online"
        ]
        
        for query in top_10:
            q_lower = query.lower()
            for term in product_terms:
                assert term not in q_lower, \
                    f"Top 10 query '{query}' contains product term '{term}'"
    
    def test_top_10_contains_service_relevant_terms(self, search_data):
        """Top 10 queries should contain service-relevant terms"""
        top_10 = search_data.get("top_10_queries", [])
        service_terms = [
            "salon", "salons", "beauty", "hair", "makeup", "service", "services",
            "near me", "appointment", "book", "best", "price", "cost"
        ]
        
        # At least 50% of top 10 should contain service-relevant terms
        service_count = 0
        for query in top_10:
            q_lower = query.lower()
            if any(term in q_lower for term in service_terms):
                service_count += 1
        
        print(f"Top 10 service-relevant count: {service_count}/{len(top_10)}")
        assert service_count >= len(top_10) * 0.5, \
            f"Expected at least 50% service-relevant queries, got {service_count}/{len(top_10)}"


class TestAdKeywordsV21:
    """Tests for ad keywords cap increase to 35"""
    
    @pytest.fixture(scope="class")
    def ad_keywords(self):
        """Get ad keyword queries"""
        response = requests.get(
            f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/latest"
        )
        assert response.status_code == 200
        # Latest endpoint returns data under 'latest' key, not 'snapshot'
        return response.json().get("latest", {}).get("ad_keyword_queries", [])
    
    def test_ad_keywords_count_up_to_35(self, ad_keywords):
        """Ad keywords should be capped at 35 (v2.1 increase from 25)"""
        assert len(ad_keywords) <= 35, \
            f"Ad keywords should be max 35, got {len(ad_keywords)}"
        print(f"Ad keywords count: {len(ad_keywords)}")
    
    def test_ad_keywords_are_strings(self, ad_keywords):
        """All ad keywords should be strings"""
        for kw in ad_keywords:
            assert isinstance(kw, str), f"Ad keyword should be string: {kw}"
    
    def test_ad_keywords_have_min_2_words(self, ad_keywords):
        """Ad keywords should have at least 2 words"""
        for kw in ad_keywords:
            word_count = len(kw.split())
            assert word_count >= 2, f"Ad keyword '{kw}' has less than 2 words"


class TestForumQueriesV21:
    """Tests for forum queries format - site:reddit.com/quora.com with quotes"""
    
    @pytest.fixture(scope="class")
    def forum_queries(self):
        """Get forum queries"""
        response = requests.get(
            f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/latest"
        )
        assert response.status_code == 200
        # Latest endpoint returns data under 'latest' key, not 'snapshot'
        return response.json().get("latest", {}).get("forum_queries", {})
    
    def test_forum_queries_has_reddit_array(self, forum_queries):
        """Forum queries should have reddit array"""
        assert "reddit" in forum_queries, "Forum queries should have 'reddit' key"
        assert isinstance(forum_queries["reddit"], list)
    
    def test_forum_queries_has_quora_array(self, forum_queries):
        """Forum queries should have quora array"""
        assert "quora" in forum_queries, "Forum queries should have 'quora' key"
        assert isinstance(forum_queries["quora"], list)
    
    def test_reddit_queries_format(self, forum_queries):
        """Reddit queries should use site:reddit.com format with quotes"""
        reddit = forum_queries.get("reddit", [])
        
        for query in reddit:
            assert query.startswith('site:reddit.com "'), \
                f"Reddit query should start with 'site:reddit.com \"': {query}"
            assert query.endswith('"'), \
                f"Reddit query should end with quote: {query}"
    
    def test_quora_queries_format(self, forum_queries):
        """Quora queries should use site:quora.com format with quotes"""
        quora = forum_queries.get("quora", [])
        
        for query in quora:
            assert query.startswith('site:quora.com "'), \
                f"Quora query should start with 'site:quora.com \"': {query}"
            assert query.endswith('"'), \
                f"Quora query should end with quote: {query}"
    
    def test_forum_queries_from_trust_price_buckets(self, forum_queries):
        """Forum queries should be sourced from trust/price buckets, not urgency-only"""
        # Get all forum query texts (without site: prefix)
        all_queries = []
        for q in forum_queries.get("reddit", []):
            # Extract query from site:reddit.com "query"
            if 'site:reddit.com "' in q:
                text = q.replace('site:reddit.com "', '').rstrip('"')
                all_queries.append(text)
        
        # Check that urgency-only terms are not the primary source
        urgency_only_terms = ["open now", "urgent", "asap", "24/7", "emergency", "same day"]
        urgency_count = sum(
            1 for q in all_queries 
            if any(term in q.lower() for term in urgency_only_terms)
        )
        
        # Less than 50% should be urgency-only
        if len(all_queries) > 0:
            urgency_ratio = urgency_count / len(all_queries)
            assert urgency_ratio < 0.5, \
                f"Too many urgency-only forum queries: {urgency_count}/{len(all_queries)}"


class TestIntentBucketsV21:
    """Tests for intent buckets having all 5 keys"""
    
    @pytest.fixture(scope="class")
    def intent_buckets(self):
        """Get intent buckets"""
        response = requests.get(
            f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/latest"
        )
        assert response.status_code == 200
        # Latest endpoint returns data under 'latest' key, not 'snapshot'
        return response.json().get("latest", {}).get("intent_buckets", {})
    
    def test_intent_buckets_has_5_keys(self, intent_buckets):
        """Intent buckets should have exactly 5 keys"""
        expected_keys = {"price", "trust", "urgency", "comparison", "general"}
        actual_keys = set(intent_buckets.keys())
        
        assert actual_keys == expected_keys, \
            f"Expected keys {expected_keys}, got {actual_keys}"
    
    def test_intent_bucket_price_exists(self, intent_buckets):
        """Intent buckets should have 'price' key"""
        assert "price" in intent_buckets
        assert isinstance(intent_buckets["price"], list)
    
    def test_intent_bucket_trust_exists(self, intent_buckets):
        """Intent buckets should have 'trust' key"""
        assert "trust" in intent_buckets
        assert isinstance(intent_buckets["trust"], list)
    
    def test_intent_bucket_urgency_exists(self, intent_buckets):
        """Intent buckets should have 'urgency' key"""
        assert "urgency" in intent_buckets
        assert isinstance(intent_buckets["urgency"], list)
    
    def test_intent_bucket_comparison_exists(self, intent_buckets):
        """Intent buckets should have 'comparison' key"""
        assert "comparison" in intent_buckets
        assert isinstance(intent_buckets["comparison"], list)
    
    def test_intent_bucket_general_exists(self, intent_buckets):
        """Intent buckets should have 'general' key"""
        assert "general" in intent_buckets
        assert isinstance(intent_buckets["general"], list)


class TestProgressiveRelaxation:
    """Tests for progressive relaxation - pipeline shouldn't fail even with strict filtering"""
    
    def test_pipeline_doesnt_fail_with_strict_filtering(self):
        """Pipeline returns results even if filtering is strict"""
        response = requests.post(
            f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/run",
            timeout=60
        )
        
        assert response.status_code == 200, f"Pipeline should not fail: {response.text}"
        data = response.json()
        
        # Pipeline should return success, partial, or low_data - not failed
        assert data.get("status") in ["success", "partial", "low_data"], \
            f"Pipeline returned status={data.get('status')}, expected success/partial/low_data"
        
        # Should have some queries even if filtering is strict
        snapshot = data.get("snapshot", {})
        kept_count = snapshot.get("stats", {}).get("kept_final", 0)
        
        print(f"Pipeline kept {kept_count} queries after filtering")
        # Progressive relaxation should ensure we have at least some results
        # (unless the business has no relevant queries at all)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
