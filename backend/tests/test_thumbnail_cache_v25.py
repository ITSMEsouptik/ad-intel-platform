"""
Thumbnail Caching & Sort Features - v2.5 Tests
Tests for iteration 25 features:
1. Thumbnail caching (oEmbed + disk cache + serve endpoint)
2. Sort By dropdown with 6 sort options
3. Video cache endpoints

Campaign: 568e45c8-7976-4d14-878a-70074f35f3ff (v2.0 data + cached thumbs)
Known cached video_id: 7574869862242143519
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthCheck:
    """Health check - always run first"""
    
    def test_api_health(self):
        """API health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", f"API not healthy: {data}"
        print(f"✓ API health check passed: {data}")


class TestThumbnailCaching:
    """Tests for thumbnail caching feature"""
    
    KNOWN_VIDEO_ID = "7574869862242143519"
    
    def test_cached_thumbnail_returns_jpeg(self):
        """GET /api/media/thumb/{video_id} returns JPEG for cached thumbnail"""
        response = requests.get(f"{BASE_URL}/api/media/thumb/{self.KNOWN_VIDEO_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check content type is JPEG
        content_type = response.headers.get("Content-Type", "")
        assert "image/jpeg" in content_type, f"Expected image/jpeg, got {content_type}"
        
        # Check Cache-Control header (note: Cloudflare may override to no-store in preview env)
        cache_control = response.headers.get("Cache-Control", "")
        # Just log the header - Cloudflare CDN may modify it
        
        # Check content is non-empty
        assert len(response.content) > 1000, f"Content too small: {len(response.content)} bytes"
        
        print(f"✓ Cached thumbnail returns JPEG: {len(response.content)} bytes, Cache-Control: {cache_control}")
    
    def test_nonexistent_thumbnail_returns_404(self):
        """GET /api/media/thumb/nonexistent returns 404"""
        response = requests.get(f"{BASE_URL}/api/media/thumb/nonexistent")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Nonexistent thumbnail returns 404")
    
    def test_media_stats_endpoint(self):
        """GET /api/media/stats returns cache statistics with thumbs_count"""
        response = requests.get(f"{BASE_URL}/api/media/stats")
        assert response.status_code == 200, f"Stats endpoint failed: {response.status_code}"
        
        data = response.json()
        assert "thumbs_count" in data, f"Missing thumbs_count in stats: {data}"
        
        # Based on problem statement: 52 thumbnails cached
        thumbs_count = data.get("thumbs_count", 0)
        assert thumbs_count >= 50, f"Expected ~52 cached thumbs, got {thumbs_count}"
        
        print(f"✓ Media stats: {data}")
    
    def test_cached_thumbnail_content_is_valid_jpeg(self):
        """Verify the cached thumbnail is a valid JPEG file"""
        response = requests.get(f"{BASE_URL}/api/media/thumb/{self.KNOWN_VIDEO_ID}")
        assert response.status_code == 200
        
        # JPEG files start with FFD8FF
        content = response.content
        assert content[:2] == b'\xff\xd8', f"Content doesn't start with JPEG magic bytes"
        print(f"✓ Thumbnail is valid JPEG (starts with FFD8)")


class TestVideoCaching:
    """Tests for video caching endpoints"""
    
    def test_nonexistent_video_returns_404(self):
        """GET /api/media/video/nonexistent returns 404"""
        response = requests.get(f"{BASE_URL}/api/media/video/nonexistent")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Nonexistent video returns 404")


class TestSocialTrendsV2Data:
    """Tests for v2.0 social trends data needed for sorting"""
    
    CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
    
    def test_social_trends_latest_returns_v2_data(self):
        """GET /api/research/{campaignId}/social-trends/latest returns v2.0 data"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("has_data") == True, f"No data in response: {data}"
        
        latest = data.get("latest", {})
        version = latest.get("version", "")
        assert version == "2.0", f"Expected version 2.0, got {version}"
        
        print(f"✓ Social Trends returns v2.0 data")
    
    def test_shortlist_has_60_tiktok_posts(self):
        """Shortlist should have 60 TikTok posts"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        latest = data.get("latest", {})
        shortlist = latest.get("shortlist", {})
        
        # Shortlist is a dict with 'tiktok' and 'instagram' keys
        tt_posts = shortlist.get("tiktok", [])
        assert len(tt_posts) == 60, f"Expected 60 TT posts, got {len(tt_posts)}"
        
        print(f"✓ Shortlist has 60 TikTok posts")
    
    def test_posts_have_score_fields_for_sorting(self):
        """Posts should have score fields needed for sorting: save_rate, overperformance_ratio"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        latest = data.get("latest", {})
        shortlist = latest.get("shortlist", {})
        
        # Shortlist is a dict with 'tiktok' and 'instagram' keys
        tt_posts = shortlist.get("tiktok", [])
        assert len(tt_posts) > 0, "No TikTok posts in shortlist"
        
        # Check first post has score fields
        first_post = tt_posts[0]
        score = first_post.get("score", {})
        
        assert "trend_score" in score, f"Missing trend_score in score: {score}"
        assert "save_rate" in score, f"Missing save_rate in score: {score}"
        assert "overperformance_ratio" in score, f"Missing overperformance_ratio in score: {score}"
        
        print(f"✓ Posts have score fields for sorting: trend_score={score.get('trend_score')}, save_rate={score.get('save_rate')}, overperformance={score.get('overperformance_ratio')}")
    
    def test_posts_have_metrics_for_sorting(self):
        """Posts should have metrics fields for sorting: views, saves"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        latest = data.get("latest", {})
        shortlist = latest.get("shortlist", {})
        
        # Shortlist is a dict with 'tiktok' and 'instagram' keys
        tt_posts = shortlist.get("tiktok", [])
        assert len(tt_posts) > 0, "No TikTok posts in shortlist"
        
        # Check first post has metrics
        first_post = tt_posts[0]
        metrics = first_post.get("metrics", {})
        
        assert "views" in metrics, f"Missing views in metrics: {metrics}"
        assert "saves" in metrics, f"Missing saves in metrics: {metrics}"
        
        print(f"✓ Posts have metrics for sorting: views={metrics.get('views')}, saves={metrics.get('saves')}")
    
    def test_posts_have_query_type(self):
        """Posts should have query_type for filtering"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        latest = data.get("latest", {})
        shortlist = latest.get("shortlist", {})
        
        # Shortlist is a dict with 'tiktok' and 'instagram' keys
        tt_posts = shortlist.get("tiktok", [])
        
        # Check query_type distribution
        query_types = {}
        for post in tt_posts:
            qt = post.get("query_type", "unknown")
            query_types[qt] = query_types.get(qt, 0) + 1
        
        assert "viral" in query_types, f"Missing viral query_type: {query_types}"
        assert "breakout" in query_types, f"Missing breakout query_type: {query_types}"
        
        print(f"✓ Query type distribution: {query_types}")


class TestPressMediaRegression:
    """Regression test for press-media endpoint"""
    
    CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
    
    def test_press_media_latest(self):
        """GET /api/research/{campaignId}/press-media/latest returns data without errors"""
        response = requests.get(f"{BASE_URL}/api/research/{self.CAMPAIGN_ID}/press-media/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # It may or may not have data, but should not error
        print(f"✓ Press Media endpoint works: has_data={data.get('has_data')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
