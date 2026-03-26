"""
Test Suite: Reliability & Performance Fixes
Iteration 69 - Jan 2026

Tests 6 key reliability/performance improvements:
1. SPA extraction: Playwright retry loop with increasing timeout (45s -> 60s)
2. Gemini 429: 3s backoff retry before Perplexity fallback
3. Step 2 speed: Parallel channels + LLM via asyncio.gather
4. Reviews fallback: broad_search mode for platforms
5. Community broadening: category-level fallback + lowered threshold to 1
6. Social Trends IG scoring: Instagram null views/saves boost
"""

import pytest
import asyncio
import inspect
import ast
import os


# ========== 1. SPA EXTRACTION: Playwright Retry with Increasing Timeout ==========

class TestSPAExtractorRetry:
    """Verify spa_service_extractor.py _extract_via_playwright has retry loop."""
    
    def test_extract_via_playwright_has_retry_loop(self):
        """_extract_via_playwright must have for loop with 2 iterations."""
        import spa_service_extractor
        source = inspect.getsource(spa_service_extractor._extract_via_playwright)
        
        # Check for range(2) loop
        assert "for attempt in range(2)" in source, \
            "_extract_via_playwright missing 'for attempt in range(2)' retry loop"
        print("PASS: _extract_via_playwright has 'for attempt in range(2)' retry loop")
    
    def test_extract_via_playwright_first_timeout_45s(self):
        """First attempt uses 45000ms timeout."""
        import spa_service_extractor
        source = inspect.getsource(spa_service_extractor._extract_via_playwright)
        
        assert "45000" in source, "First timeout should be 45000ms"
        print("PASS: First attempt uses 45000ms timeout")
    
    def test_extract_via_playwright_second_timeout_60s(self):
        """Second attempt uses 60000ms timeout."""
        import spa_service_extractor
        source = inspect.getsource(spa_service_extractor._extract_via_playwright)
        
        assert "60000" in source, "Second timeout should be 60000ms"
        print("PASS: Second attempt uses 60000ms timeout")
    
    def test_extract_via_playwright_timeout_increases_on_retry(self):
        """timeout_ms = 45000 if attempt == 0 else 60000."""
        import spa_service_extractor
        source = inspect.getsource(spa_service_extractor._extract_via_playwright)
        
        assert "timeout_ms = 45000 if attempt == 0 else 60000" in source, \
            "Missing conditional timeout: 'timeout_ms = 45000 if attempt == 0 else 60000'"
        print("PASS: Timeout increases from 45s to 60s on retry")
    
    def test_extract_via_playwright_logs_retry_message(self):
        """Retry logs 'Retrying with extended timeout'."""
        import spa_service_extractor
        source = inspect.getsource(spa_service_extractor._extract_via_playwright)
        
        assert "Retrying with extended timeout" in source, \
            "Missing log message for retry"
        print("PASS: Retry logs 'Retrying with extended timeout'")


# ========== 2. GEMINI 429: 3s Backoff Retry ==========

class TestGemini429Retry:
    """Verify gemini_site_summarizer.py summarize_with_gemini has 429 retry."""
    
    def test_summarize_with_gemini_has_retry_loop(self):
        """summarize_with_gemini must have for loop with 2 attempts."""
        import gemini_site_summarizer
        source = inspect.getsource(gemini_site_summarizer.summarize_with_gemini)
        
        assert "for attempt in range(2)" in source, \
            "summarize_with_gemini missing 'for attempt in range(2)' retry loop"
        print("PASS: summarize_with_gemini has 'for attempt in range(2)' retry loop")
    
    def test_summarize_with_gemini_detects_429(self):
        """Must detect 429 or RESOURCE_EXHAUSTED in error string."""
        import gemini_site_summarizer
        source = inspect.getsource(gemini_site_summarizer.summarize_with_gemini)
        
        assert "'429' in error_str" in source or '"429" in error_str' in source, \
            "Missing 429 detection in error handling"
        assert "RESOURCE_EXHAUSTED" in source, \
            "Missing RESOURCE_EXHAUSTED detection"
        print("PASS: Detects 429 and RESOURCE_EXHAUSTED errors")
    
    def test_summarize_with_gemini_sleeps_3s_on_429(self):
        """Must sleep 3 seconds before retry on 429."""
        import gemini_site_summarizer
        source = inspect.getsource(gemini_site_summarizer.summarize_with_gemini)
        
        assert "await asyncio.sleep(3)" in source, \
            "Missing 3-second sleep on 429: 'await asyncio.sleep(3)'"
        print("PASS: Sleeps 3s on 429 before retry")
    
    def test_summarize_with_gemini_logs_429_retry(self):
        """Must log when retrying on 429."""
        import gemini_site_summarizer
        source = inspect.getsource(gemini_site_summarizer.summarize_with_gemini)
        
        assert "Gemini 429 rate limit" in source, \
            "Missing log message for 429 retry"
        print("PASS: Logs '429 rate limit' when retrying")
    
    def test_summarize_with_gemini_falls_back_after_persist(self):
        """Must fall back if 429 persists after retry."""
        import gemini_site_summarizer
        source = inspect.getsource(gemini_site_summarizer.summarize_with_gemini)
        
        assert "429 persists" in source, \
            "Missing fallback message when 429 persists"
        print("PASS: Falls back when 429 persists after retry")


# ========== 3. STEP 2 SPEED: Parallel Channels + LLM ==========

class TestStep2Parallelism:
    """Verify server.py runs channels + LLM in parallel via asyncio.gather."""
    
    def test_server_imports_asyncio(self):
        """server.py must import asyncio."""
        import server
        
        assert hasattr(server, 'asyncio'), "server.py missing asyncio import"
        print("PASS: server.py imports asyncio")
    
    def test_run_step2_uses_asyncio_create_task(self):
        """run_step2 uses asyncio.create_task for channels and llm."""
        # Read source directly to check implementation
        with open('/app/backend/server.py', 'r') as f:
            source = f.read()
        
        # Find run_step2 function
        assert "asyncio.create_task" in source, \
            "Missing asyncio.create_task in server.py"
        print("PASS: server.py uses asyncio.create_task")
    
    def test_run_step2_has_channels_task(self):
        """run_step2 creates channels_task."""
        with open('/app/backend/server.py', 'r') as f:
            source = f.read()
        
        assert "channels_task = asyncio.create_task" in source, \
            "Missing 'channels_task = asyncio.create_task'"
        print("PASS: run_step2 creates channels_task")
    
    def test_run_step2_has_llm_task(self):
        """run_step2 creates llm_task."""
        with open('/app/backend/server.py', 'r') as f:
            source = f.read()
        
        assert "llm_task = asyncio.create_task" in source, \
            "Missing 'llm_task = asyncio.create_task'"
        print("PASS: run_step2 creates llm_task")
    
    def test_run_step2_uses_asyncio_gather(self):
        """run_step2 uses asyncio.gather to run tasks in parallel."""
        with open('/app/backend/server.py', 'r') as f:
            source = f.read()
        
        assert "await asyncio.gather" in source, \
            "Missing 'await asyncio.gather' for parallel execution"
        print("PASS: run_step2 uses asyncio.gather")
    
    def test_run_step2_gather_includes_both_tasks(self):
        """asyncio.gather includes both channels_task and llm_task."""
        with open('/app/backend/server.py', 'r') as f:
            source = f.read()
        
        # Check that gather line includes both tasks
        assert "channels_task, llm_task" in source or "llm_task, channels_task" in source, \
            "asyncio.gather must include both channels_task and llm_task"
        print("PASS: asyncio.gather runs channels_task and llm_task in parallel")


# ========== 4. REVIEWS FALLBACK: broad_search Parameter ==========

class TestReviewsBroadSearch:
    """Verify reviews module has broad_search fallback."""
    
    def test_fetch_reviews_discovery_accepts_broad_search(self):
        """fetch_reviews_discovery must accept broad_search parameter."""
        from research.reviews.perplexity_reviews import fetch_reviews_discovery
        sig = inspect.signature(fetch_reviews_discovery)
        
        assert "broad_search" in sig.parameters, \
            "fetch_reviews_discovery missing broad_search parameter"
        print("PASS: fetch_reviews_discovery accepts broad_search parameter")
    
    def test_fetch_reviews_discovery_broad_search_default_false(self):
        """broad_search defaults to False."""
        from research.reviews.perplexity_reviews import fetch_reviews_discovery
        sig = inspect.signature(fetch_reviews_discovery)
        
        param = sig.parameters["broad_search"]
        assert param.default is False, \
            f"broad_search should default to False, got {param.default}"
        print("PASS: broad_search defaults to False")
    
    def test_build_broad_discovery_prompt_exists(self):
        """_build_broad_discovery_prompt function exists."""
        from research.reviews import perplexity_reviews
        
        assert hasattr(perplexity_reviews, '_build_broad_discovery_prompt'), \
            "_build_broad_discovery_prompt function missing"
        print("PASS: _build_broad_discovery_prompt function exists")
    
    def test_build_broad_discovery_prompt_includes_google_maps(self):
        """Broad prompt includes Google Maps search strategy."""
        from research.reviews.perplexity_reviews import _build_broad_discovery_prompt
        
        prompt = _build_broad_discovery_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="At-home beauty",
            services=["Makeup", "Hair"]
        )
        
        assert "Google Maps" in prompt, "Broad prompt must include Google Maps"
        print("PASS: Broad discovery prompt includes Google Maps")
    
    def test_build_broad_discovery_prompt_includes_facebook(self):
        """Broad prompt includes Facebook search strategy."""
        from research.reviews.perplexity_reviews import _build_broad_discovery_prompt
        
        prompt = _build_broad_discovery_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="At-home beauty",
            services=["Makeup"]
        )
        
        assert "Facebook" in prompt, "Broad prompt must include Facebook"
        print("PASS: Broad discovery prompt includes Facebook")
    
    def test_build_broad_discovery_prompt_includes_instagram(self):
        """Broad prompt includes Instagram search strategy."""
        from research.reviews.perplexity_reviews import _build_broad_discovery_prompt
        
        prompt = _build_broad_discovery_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="At-home beauty",
            services=["Makeup"]
        )
        
        assert "Instagram" in prompt, "Broad prompt must include Instagram"
        print("PASS: Broad discovery prompt includes Instagram")
    
    def test_reviews_service_calls_broad_search_fallback(self):
        """ReviewsService.run() calls broad_search=True when 0 platforms found."""
        with open('/app/backend/research/reviews/service.py', 'r') as f:
            source = f.read()
        
        assert "broad_search=True" in source, \
            "ReviewsService must call fetch_reviews_discovery with broad_search=True"
        print("PASS: ReviewsService calls broad_search=True fallback")
    
    def test_reviews_service_checks_valid_platforms_count(self):
        """ReviewsService checks len(valid_platforms) == 0 before broad search."""
        with open('/app/backend/research/reviews/service.py', 'r') as f:
            source = f.read()
        
        assert "len(valid_platforms) == 0" in source, \
            "ReviewsService must check 'len(valid_platforms) == 0' before broad search"
        print("PASS: ReviewsService checks valid_platforms count before broad search")


# ========== 5. COMMUNITY BROADENING: Category Fallback + Threshold ==========

class TestCommunityBroadening:
    """Verify community module has category-level fallback and lowered threshold."""
    
    def test_fetch_community_discovery_accepts_broad_search(self):
        """fetch_community_discovery must accept broad_search parameter."""
        from research.community.perplexity_community import fetch_community_discovery
        sig = inspect.signature(fetch_community_discovery)
        
        assert "broad_search" in sig.parameters, \
            "fetch_community_discovery missing broad_search parameter"
        print("PASS: fetch_community_discovery accepts broad_search parameter")
    
    def test_fetch_community_discovery_broad_search_default_false(self):
        """broad_search defaults to False."""
        from research.community.perplexity_community import fetch_community_discovery
        sig = inspect.signature(fetch_community_discovery)
        
        param = sig.parameters["broad_search"]
        assert param.default is False, \
            f"broad_search should default to False, got {param.default}"
        print("PASS: broad_search defaults to False")
    
    def test_fetch_community_discovery_broad_has_category_search(self):
        """broad_search=True generates category-level prompt."""
        from research.community.perplexity_community import fetch_community_discovery
        source = inspect.getsource(fetch_community_discovery)
        
        # When broad_search=True, prompt should focus on category not brand
        assert "if broad_search:" in source, "Missing broad_search conditional"
        print("PASS: fetch_community_discovery has broad_search conditional")
    
    def test_community_service_calls_broad_search_fallback(self):
        """CommunityService.run() retries with broad_search=True when 0 threads."""
        with open('/app/backend/research/community/service.py', 'r') as f:
            source = f.read()
        
        assert "broad_search=True" in source, \
            "CommunityService must call fetch_community_discovery with broad_search=True"
        print("PASS: CommunityService calls broad_search=True fallback")
    
    def test_community_service_checks_valid_threads_zero(self):
        """CommunityService checks len(valid_forum_threads) == 0 before retry."""
        with open('/app/backend/research/community/service.py', 'r') as f:
            source = f.read()
        
        assert "len(valid_forum_threads) == 0" in source, \
            "CommunityService must check 'len(valid_forum_threads) == 0' before broad search"
        print("PASS: CommunityService checks valid_forum_threads count")
    
    def test_community_service_synthesis_threshold_is_1(self):
        """Synthesis runs if len(valid_forum_threads) >= 1 (lowered from 3)."""
        with open('/app/backend/research/community/service.py', 'r') as f:
            source = f.read()
        
        # Should have >= 1 threshold, not >= 3
        assert "len(valid_forum_threads) >= 1" in source, \
            "Synthesis threshold should be >= 1, not >= 3"
        print("PASS: Synthesis threshold lowered to >= 1 thread")
    
    def test_community_service_logs_broad_retry(self):
        """CommunityService logs when retrying with broader search."""
        with open('/app/backend/research/community/service.py', 'r') as f:
            source = f.read()
        
        assert "broader category search" in source.lower() or "broad search" in source.lower(), \
            "CommunityService should log when retrying with broader search"
        print("PASS: CommunityService logs broad search retry")


# ========== 6. INSTAGRAM SCORING: Null Views/Saves Boost ==========

class TestInstagramScoring:
    """Verify social_trends/scoring.py handles Instagram null views/saves."""
    
    def test_score_item_extracts_platform(self):
        """score_item extracts platform from item."""
        from research.social_trends.scoring import score_item
        source = inspect.getsource(score_item)
        
        assert 'platform = item.get("platform"' in source, \
            "score_item must extract platform from item"
        print("PASS: score_item extracts platform")
    
    def test_score_item_has_instagram_adjustment(self):
        """score_item has special handling for Instagram."""
        from research.social_trends.scoring import score_item
        source = inspect.getsource(score_item)
        
        assert 'platform == "instagram"' in source, \
            "score_item must have Instagram-specific adjustment"
        print("PASS: score_item has Instagram-specific adjustment")
    
    def test_score_item_instagram_checks_null_views(self):
        """Instagram adjustment checks for null/missing views."""
        from research.social_trends.scoring import score_item
        source = inspect.getsource(score_item)
        
        assert "not views" in source, \
            "Instagram adjustment must check 'not views'"
        print("PASS: Instagram adjustment checks for null views")
    
    def test_score_item_instagram_uses_likes_comments_proxy(self):
        """Instagram uses likes+comments as engagement proxy when views missing."""
        from research.social_trends.scoring import score_item
        source = inspect.getsource(score_item)
        
        assert "likes + comments" in source, \
            "Instagram should use 'likes + comments' as proxy"
        print("PASS: Instagram uses likes+comments as proxy")
    
    def test_instagram_item_gets_nonzero_eng_score(self):
        """Instagram item with likes but no views gets non-zero eng_score."""
        from research.social_trends.scoring import score_item
        
        # Test item with Instagram, 500 likes, no views
        item = {
            "platform": "instagram",
            "metrics": {
                "likes": 500,
                "comments": 50,
                "shares": 0,
                "saves": None,
                "views": None
            },
            "author_follower_count": 10000,
            "posted_at": "2026-01-10T12:00:00Z"
        }
        
        result = score_item(item)
        
        assert result["trend_score"] > 0, \
            f"Instagram item with likes should have non-zero trend_score, got {result['trend_score']}"
        print(f"PASS: Instagram item with 500 likes/50 comments gets trend_score={result['trend_score']}")
    
    def test_instagram_item_high_likes_gets_higher_score(self):
        """Instagram item with high engagement gets higher score."""
        from research.social_trends.scoring import score_item
        
        # Low engagement
        low_item = {
            "platform": "instagram",
            "metrics": {"likes": 20, "comments": 2, "views": None},
            "posted_at": "2026-01-10T12:00:00Z"
        }
        
        # High engagement
        high_item = {
            "platform": "instagram",
            "metrics": {"likes": 5000, "comments": 500, "views": None},
            "posted_at": "2026-01-10T12:00:00Z"
        }
        
        low_result = score_item(low_item)
        high_result = score_item(high_item)
        
        assert high_result["trend_score"] > low_result["trend_score"], \
            f"High engagement ({high_result['trend_score']}) should score higher than low ({low_result['trend_score']})"
        print(f"PASS: High engagement ({high_result['trend_score']}) > Low engagement ({low_result['trend_score']})")
    
    def test_instagram_overperf_score_boosted(self):
        """Instagram with null views gets overperf_score boost."""
        from research.social_trends.scoring import score_item
        source = inspect.getsource(score_item)
        
        # Should boost overperf_score when engagement > 0 but views missing
        assert "overperf_score = max(overperf_score, 0.3)" in source, \
            "Instagram should boost overperf_score to at least 0.3"
        print("PASS: Instagram boosts overperf_score to at least 0.3")


# ========== INTEGRATION: API Health Check ==========

class TestAPIHealth:
    """Basic API health verification."""
    
    def test_api_health(self):
        """API health check returns 200."""
        import requests
        BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
        
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"API health check failed: {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"API not healthy: {data}"
        print(f"PASS: API health check returns healthy")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
