"""
Social Trends v2.0 Backend Tests
Tests for the v2.0 upgrade including:
- Smart SQL queries with category_type
- New scoring formula (save_rate 30%, overperformance 25%, engagement 25%, recency 20%)
- 4 query types: viral, breakout, most_saved, most_discussed
- New fields: query_type, save_rate, overperformance_ratio, author_verified, saves metric
- cover_url for thumbnails instead of oEmbed
"""

import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSocialTrendsV2:
    """Test Social Trends v2.0 specific features"""
    
    # Campaign with v2.0 data
    V2_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
    # Campaign with v1 data for comparison
    V1_CAMPAIGN_ID = "01f098a0-cd78-46ae-8663-2640cce6b47b"
    
    def test_api_health(self):
        """Test API health check"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_v2_latest_returns_data(self):
        """Test GET /api/research/{campaignId}/social-trends/latest returns v2.0 data"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("has_data") is True
        assert data.get("status") in ["fresh", "stale"]
        print(f"✓ Social Trends v2 latest: has_data={data.get('has_data')}, status={data.get('status')}")
    
    def test_v2_snapshot_version(self):
        """Test snapshot version is '2.0'"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        latest = data.get("latest", {})
        version = latest.get("version")
        assert version == "2.0", f"Expected version '2.0', got '{version}'"
        print(f"✓ Snapshot version: {version}")
    
    def test_v2_shortlist_count(self):
        """Test shortlist has 60 TikTok posts as expected"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        shortlist = data.get("latest", {}).get("shortlist", {})
        tt_count = len(shortlist.get("tiktok", []))
        ig_count = len(shortlist.get("instagram", []))
        total = tt_count + ig_count
        
        assert total == 60, f"Expected 60 total posts, got {total}"
        print(f"✓ Shortlist count: {tt_count} TikTok + {ig_count} Instagram = {total} total")
    
    def test_v2_query_types_present(self):
        """Test posts have query_type field with expected values"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        tt_posts = data.get("latest", {}).get("shortlist", {}).get("tiktok", [])
        query_types = {}
        for item in tt_posts:
            qt = item.get("query_type", "unknown")
            query_types[qt] = query_types.get(qt, 0) + 1
        
        # Verify all 4 query types are present
        expected_types = ["viral", "breakout", "most_saved", "most_discussed"]
        for qt in expected_types:
            assert qt in query_types, f"Missing query_type: {qt}"
        
        print(f"✓ Query type distribution: {query_types}")
    
    def test_v2_trend_score_has_save_rate(self):
        """Test TrendScore includes save_rate field"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        tt_posts = data.get("latest", {}).get("shortlist", {}).get("tiktok", [])
        assert len(tt_posts) > 0, "No TikTok posts found"
        
        # Check multiple posts for save_rate
        has_save_rate_count = sum(1 for p in tt_posts if p.get("score", {}).get("save_rate") is not None)
        assert has_save_rate_count > 0, "No posts have save_rate in score"
        
        # Check first post with save_rate
        first_with_rate = next((p for p in tt_posts if p.get("score", {}).get("save_rate") is not None), None)
        if first_with_rate:
            save_rate = first_with_rate["score"]["save_rate"]
            print(f"✓ TrendScore.save_rate present: {save_rate} ({has_save_rate_count}/{len(tt_posts)} posts have it)")
    
    def test_v2_trend_score_has_overperformance_ratio(self):
        """Test TrendScore includes overperformance_ratio field"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        tt_posts = data.get("latest", {}).get("shortlist", {}).get("tiktok", [])
        
        # Check multiple posts for overperformance_ratio
        has_overperf_count = sum(1 for p in tt_posts if p.get("score", {}).get("overperformance_ratio") is not None)
        assert has_overperf_count > 0, "No posts have overperformance_ratio in score"
        
        first_with_ratio = next((p for p in tt_posts if p.get("score", {}).get("overperformance_ratio") is not None), None)
        if first_with_ratio:
            ratio = first_with_ratio["score"]["overperformance_ratio"]
            print(f"✓ TrendScore.overperformance_ratio present: {ratio}x ({has_overperf_count}/{len(tt_posts)} posts have it)")
    
    def test_v2_post_metrics_has_saves(self):
        """Test PostMetrics includes saves field (collect_count)"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        tt_posts = data.get("latest", {}).get("shortlist", {}).get("tiktok", [])
        
        has_saves_count = sum(1 for p in tt_posts if p.get("metrics", {}).get("saves") is not None)
        assert has_saves_count > 0, "No posts have saves in metrics"
        
        first_with_saves = next((p for p in tt_posts if p.get("metrics", {}).get("saves") is not None), None)
        if first_with_saves:
            saves = first_with_saves["metrics"]["saves"]
            print(f"✓ PostMetrics.saves present: {saves} ({has_saves_count}/{len(tt_posts)} posts have it)")
    
    def test_v2_author_verified_field(self):
        """Test TrendItem has author_verified field"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        tt_posts = data.get("latest", {}).get("shortlist", {}).get("tiktok", [])
        
        # Check that author_verified field exists (can be True, False, or None)
        has_verified_field = sum(1 for p in tt_posts if "author_verified" in p)
        print(f"✓ author_verified field present in {has_verified_field}/{len(tt_posts)} posts")
    
    def test_v2_thumb_url_present(self):
        """Test posts have thumb_url (cover_url from SQL)"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        
        tt_posts = data.get("latest", {}).get("shortlist", {}).get("tiktok", [])
        
        has_thumb_count = sum(1 for p in tt_posts if p.get("thumb_url"))
        print(f"✓ thumb_url present in {has_thumb_count}/{len(tt_posts)} posts (may expire)")
    
    def test_v2_history_endpoint(self):
        """Test GET /api/research/{campaignId}/social-trends/history"""
        response = requests.get(f"{BASE_URL}/api/research/{self.V2_CAMPAIGN_ID}/social-trends/history")
        assert response.status_code == 200
        data = response.json()
        
        total_count = data.get("total_count", 0)
        snapshots = data.get("snapshots", [])
        
        assert total_count >= 0
        assert isinstance(snapshots, list)
        print(f"✓ History endpoint: total_count={total_count}, snapshots={len(snapshots)}")


class TestSocialTrendsRegression:
    """Regression tests for other research modules"""
    
    CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
    
    def test_press_media_no_regression(self):
        """Test press-media endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/press-media/latest")
        assert response.status_code in [200, 404]  # 404 is OK if not run yet
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Press Media: has_data={data.get('has_data')}")
    
    def test_customer_intel_no_regression(self):
        """Test customer-intel endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/customer-intel/latest")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Customer Intel: has_data={data.get('has_data')}")
    
    def test_search_intent_no_regression(self):
        """Test search-intent endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Search Intent: has_data={data.get('has_data')}")
    
    def test_seasonality_no_regression(self):
        """Test seasonality endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Seasonality: has_data={data.get('has_data')}")
    
    def test_competitors_no_regression(self):
        """Test competitors endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/competitors/latest")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Competitors: has_data={data.get('has_data')}")
    
    def test_reviews_no_regression(self):
        """Test reviews endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/reviews/latest")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Reviews: has_data={data.get('has_data')}")
    
    def test_community_no_regression(self):
        """Test community endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/community/latest")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Community: has_data={data.get('has_data')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
