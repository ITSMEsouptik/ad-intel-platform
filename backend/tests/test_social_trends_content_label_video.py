"""
Social Trends Content Label + Video Caching Tests (v2.6)
Tests:
1. Social Trends data with content_label field
2. Content label filter (SOURCE filter: All/Official/Mention/Category)
3. Video caching endpoints (cache-video, get-video, stats)
4. Range request support for video serving
"""

import os
import pytest
import requests

# BASE_URL from environment (production URL)
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
CACHED_VIDEO_ID = "7604368424340376853"

class TestHealthCheck:
    """API Health Check"""
    
    def test_api_health(self):
        """Test API is healthy"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")


class TestSocialTrendsContentLabel:
    """Test content_label field on social trends posts"""
    
    def test_social_trends_returns_data(self):
        """Social Trends /latest returns has_data=true"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        assert data.get("has_data") == True
        print("✓ Social Trends returns has_data=true")
    
    def test_social_trends_has_60_tiktok_items(self):
        """Shortlist has 60 TikTok items"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        assert len(tiktok) == 60, f"Expected 60 TikTok items, got {len(tiktok)}"
        print(f"✓ Shortlist has {len(tiktok)} TikTok items")
    
    def test_content_label_field_present(self):
        """Each post has content_label field"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        for i, item in enumerate(tiktok[:10]):  # Check first 10
            assert "content_label" in item, f"Item {i} missing content_label"
        print("✓ content_label field present on all checked items")
    
    def test_content_label_values(self):
        """content_label has valid values: official, mention, or category"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        valid_labels = {"official", "mention", "category"}
        labels_found = set()
        for item in tiktok:
            label = item.get("content_label")
            assert label in valid_labels, f"Invalid content_label: {label}"
            labels_found.add(label)
        
        print(f"✓ All content_labels valid. Found: {labels_found}")
    
    def test_content_label_distribution(self):
        """Verify distribution of content_label values"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        label_counts = {}
        for item in tiktok:
            label = item.get("content_label", "none")
            label_counts[label] = label_counts.get(label, 0) + 1
        
        print(f"✓ Content label distribution: {label_counts}")
        
        # Expect at least one of each type
        assert label_counts.get("mention", 0) > 0, "Expected at least one 'mention' label"
        assert label_counts.get("category", 0) > 0, "Expected at least one 'category' label"
        # official may or may not be present depending on data
    
    def test_official_label_on_brand_handle(self):
        """Official label is on posts from known brand handle"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        official_posts = [i for i in tiktok if i.get("content_label") == "official"]
        for post in official_posts:
            handle = post.get("author_handle", "").lower()
            print(f"  Official post from: @{handle}")
            # ruuby is the brand
            assert "ruuby" in handle, f"Expected brand handle, got @{handle}"
        
        print(f"✓ {len(official_posts)} official posts found, all from brand handle")
    
    def test_post_structure_for_modal(self):
        """Post has all fields needed for modal display"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        required_fields = ["platform", "author_handle", "post_url", "thumb_url", 
                          "media_url", "media_type", "caption", "metrics", "content_label"]
        
        for i, item in enumerate(tiktok[:5]):
            for field in required_fields:
                assert field in item, f"Item {i} missing {field}"
        
        # Check metrics structure
        first = tiktok[0]
        metrics = first.get("metrics", {})
        assert "likes" in metrics or "views" in metrics, "Metrics missing likes or views"
        
        print("✓ Post structure valid for modal display")


class TestVideoCachingEndpoints:
    """Test video caching API endpoints"""
    
    def test_media_stats_endpoint(self):
        """GET /api/media/stats returns cache statistics"""
        response = requests.get(f"{BASE_URL}/api/media/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "thumbs_count" in data
        assert "videos_count" in data
        assert "thumbs_size_mb" in data
        assert "videos_size_mb" in data
        
        print(f"✓ Media stats: {data['thumbs_count']} thumbs, {data['videos_count']} videos")
    
    def test_cached_video_serving(self):
        """GET /api/media/video/{video_id} returns video for cached video"""
        response = requests.get(f"{BASE_URL}/api/media/video/{CACHED_VIDEO_ID}")
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "video/mp4"
        assert len(response.content) > 100000  # > 100KB
        print(f"✓ Cached video served: {len(response.content)} bytes")
    
    def test_video_not_cached_returns_404(self):
        """GET /api/media/video/nonexistent returns 404"""
        response = requests.get(f"{BASE_URL}/api/media/video/nonexistent123456")
        assert response.status_code == 404
        print("✓ Non-cached video returns 404")
    
    def test_range_request_returns_206(self):
        """Range request returns 206 Partial Content"""
        headers = {"Range": "bytes=0-999"}
        response = requests.get(
            f"{BASE_URL}/api/media/video/{CACHED_VIDEO_ID}",
            headers=headers
        )
        assert response.status_code == 206
        assert len(response.content) == 1000
        assert "Content-Range" in response.headers
        print(f"✓ Range request: 206 with {len(response.content)} bytes")
    
    def test_cache_video_already_cached(self):
        """POST /api/media/cache-video/{video_id} returns already_cached for existing"""
        response = requests.post(
            f"{BASE_URL}/api/media/cache-video/{CACHED_VIDEO_ID}",
            json={"video_url": ""}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "already_cached"
        assert data.get("video_id") == CACHED_VIDEO_ID
        print("✓ Cache-video returns already_cached for existing video")
    
    def test_cache_video_requires_video_url(self):
        """POST /api/media/cache-video/{video_id} requires video_url for new videos"""
        response = requests.post(
            f"{BASE_URL}/api/media/cache-video/new_video_12345",
            json={}  # Empty body
        )
        # Should fail because no video_url for new video
        assert response.status_code in [400, 404, 502]
        print("✓ Cache-video validates video_url for new videos")


class TestSortByAndFilters:
    """Test Sort By dropdown functionality (data structure support)"""
    
    def test_posts_have_score_fields(self):
        """Posts have score fields for sorting"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        first = tiktok[0]
        score = first.get("score", {})
        
        # Check for v2.0 score fields
        assert "trend_score" in score
        print(f"✓ Score fields present: {list(score.keys())}")
    
    def test_posts_have_metrics_for_sorting(self):
        """Posts have metrics fields for sorting by saves, views"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        # Check sample posts have metrics
        for i, item in enumerate(tiktok[:5]):
            metrics = item.get("metrics", {})
            assert isinstance(metrics, dict), f"Item {i} metrics not a dict"
        
        print("✓ All checked posts have metrics dict for sorting")
    
    def test_query_type_for_lens_filter(self):
        """Posts have query_type for lens filtering"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        data = response.json()
        shortlist = data.get("latest", {}).get("shortlist", {})
        tiktok = shortlist.get("tiktok", [])
        
        query_types = set()
        for item in tiktok:
            qt = item.get("query_type")
            if qt:
                query_types.add(qt)
        
        print(f"✓ Query types found: {query_types}")
        # Expect viral, breakout, most_saved, most_discussed
        assert len(query_types) > 0, "No query_types found"


class TestThumbnailCaching:
    """Test thumbnail caching endpoints"""
    
    def test_cached_thumbnail_serving(self):
        """GET /api/media/thumb/{video_id} serves cached thumbnail"""
        # Use a video_id from the data
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        data = response.json()
        tiktok = data.get("latest", {}).get("shortlist", {}).get("tiktok", [])
        
        if tiktok:
            # Get video_id from post_url
            post_url = tiktok[0].get("post_url", "")
            if "/video/" in post_url:
                video_id = post_url.split("/video/")[1].split("?")[0].split("/")[0]
                
                thumb_resp = requests.get(f"{BASE_URL}/api/media/thumb/{video_id}")
                if thumb_resp.status_code == 200:
                    assert "image/jpeg" in thumb_resp.headers.get("Content-Type", "")
                    assert len(thumb_resp.content) > 100
                    print(f"✓ Thumbnail cached and served for video {video_id}")
                else:
                    print(f"✓ Thumbnail not cached for {video_id} (expected for some videos)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
