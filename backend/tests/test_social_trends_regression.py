"""
Social Trends Regression Test Suite - Iteration 23
Tests backend API endpoints for Social Trends module and regression tests for other research modules.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign with social trends data
CAMPAIGN_ID = "01f098a0-cd78-46ae-8663-2640cce6b47b"
# Alternative campaign for general testing
ALT_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"
# Non-existent campaign for 404 tests
NON_EXISTENT_CAMPAIGN = "00000000-0000-0000-0000-000000000000"


class TestHealthCheck:
    """Health check endpoint test"""
    
    def test_api_health(self):
        """Test API health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data
        print(f"Health check passed: {data}")


class TestSocialTrendsLatest:
    """Tests for GET /api/research/{campaignId}/social-trends/latest"""
    
    def test_social_trends_latest_with_data(self):
        """Test latest endpoint returns correct structure with data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify top-level structure
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        # Verify data present
        assert data["has_data"] == True
        assert data["status"] in ["fresh", "stale"]
        assert isinstance(data["refresh_due_in_days"], int)
        
        print(f"Social Trends Latest: has_data={data['has_data']}, status={data['status']}")
    
    def test_social_trends_latest_snapshot_structure(self):
        """Test latest snapshot has correct nested structure"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        latest = data.get("latest")
        
        if latest:
            # Check snapshot structure
            assert "version" in latest
            assert "captured_at" in latest
            assert "refresh_due_at" in latest
            assert "window_days" in latest
            assert "inputs_used" in latest
            assert "handles" in latest
            assert "lenses" in latest
            assert "shortlist" in latest
            assert "trending_audio" in latest
            assert "audit" in latest
            
            # Check inputs_used structure
            inputs = latest["inputs_used"]
            assert "geo" in inputs
            assert "brand_name" in inputs
            assert "domain" in inputs
            
            # Check lenses structure
            lenses = latest["lenses"]
            assert "brand_competitors" in lenses
            assert "category_trends" in lenses
            
            # Check shortlist structure
            shortlist = latest["shortlist"]
            assert "instagram" in shortlist
            assert "tiktok" in shortlist
            
            # Check trending_audio is a list
            assert isinstance(latest["trending_audio"], list)
            
            print(f"Snapshot structure valid. TikTok items in category_trends: {len(lenses['category_trends'].get('tiktok', {}).get('items', []))}")
    
    def test_social_trends_latest_trending_audio(self):
        """Test trending audio has correct structure"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        latest = data.get("latest")
        
        if latest and latest.get("trending_audio"):
            audio = latest["trending_audio"]
            assert len(audio) > 0, "Should have trending audio tracks"
            
            # Check first audio item structure
            first_audio = audio[0]
            assert "music_title" in first_audio
            assert "music_author" in first_audio
            assert "usage_count" in first_audio
            assert "avg_views" in first_audio
            assert "avg_likes" in first_audio
            
            print(f"Trending audio count: {len(audio)}")
    
    def test_social_trends_latest_404_nonexistent_campaign(self):
        """Test 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{NON_EXISTENT_CAMPAIGN}/social-trends/latest")
        assert response.status_code == 404
        print("404 correctly returned for non-existent campaign")


class TestSocialTrendsRun:
    """Tests for POST /api/research/{campaignId}/social-trends/run"""
    
    def test_social_trends_run_returns_running_status(self):
        """Test run endpoint returns correct response structure"""
        response = requests.post(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/run")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify response structure
        assert "campaign_id" in data
        assert "status" in data
        assert "message" in data
        
        # Status should be 'running'
        assert data["status"] == "running"
        assert "poll" in data["message"].lower() or "started" in data["message"].lower()
        
        print(f"Run response: status={data['status']}, message={data['message']}")
    
    def test_social_trends_run_404_nonexistent_campaign(self):
        """Test 404 for non-existent campaign on run endpoint"""
        response = requests.post(f"{BASE_URL}/api/research/{NON_EXISTENT_CAMPAIGN}/social-trends/run")
        assert response.status_code == 404
        print("404 correctly returned for non-existent campaign on run endpoint")


class TestSocialTrendsHistory:
    """Tests for GET /api/research/{campaignId}/social-trends/history"""
    
    def test_social_trends_history_returns_snapshots(self):
        """Test history endpoint returns snapshots array"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/history")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify response structure
        assert "campaign_id" in data
        assert "snapshots" in data
        assert "total_count" in data
        
        # Snapshots should be a list
        assert isinstance(data["snapshots"], list)
        assert data["total_count"] >= 0
        
        print(f"History: total_count={data['total_count']}, snapshots_len={len(data['snapshots'])}")
    
    def test_social_trends_history_404_nonexistent_campaign(self):
        """Test 404 for non-existent campaign on history endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{NON_EXISTENT_CAMPAIGN}/social-trends/history")
        assert response.status_code == 404
        print("404 correctly returned for non-existent campaign on history endpoint")


class TestPressMediaRegression:
    """Regression tests for Press & Media endpoints"""
    
    def test_press_media_latest(self):
        """Test press-media latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/press-media/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        assert "status" in data
        print(f"Press Media Latest: has_data={data['has_data']}, status={data['status']}")
    
    def test_press_media_history(self):
        """Test press-media history endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/press-media/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "snapshots" in data or "history" in data or "total_count" in data
        print(f"Press Media History: response received")


class TestOtherResearchModulesRegression:
    """Regression tests for other research module endpoints"""
    
    def test_customer_intel_latest(self):
        """Test customer-intel latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/customer-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        print(f"Customer Intel: has_data={data.get('has_data')}")
    
    def test_search_intent_latest(self):
        """Test search-intent latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        print(f"Search Intent: has_data={data.get('has_data')}")
    
    def test_seasonality_latest(self):
        """Test seasonality latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        print(f"Seasonality: has_data={data.get('has_data')}")
    
    def test_competitors_latest(self):
        """Test competitors latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        print(f"Competitors: has_data={data.get('has_data')}")
    
    def test_reviews_latest(self):
        """Test reviews latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/reviews/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        print(f"Reviews: has_data={data.get('has_data')}")
    
    def test_community_latest(self):
        """Test community latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/community/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        print(f"Community: has_data={data.get('has_data')}")


class TestTrendItemStructure:
    """Tests for TrendItem structure in social trends data"""
    
    def test_tiktok_item_structure(self):
        """Test TikTok items have correct structure"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_ID}/social-trends/latest")
        assert response.status_code == 200
        
        data = response.json()
        latest = data.get("latest")
        
        if latest:
            # Get TikTok items from category_trends lens
            tt_items = latest.get("lenses", {}).get("category_trends", {}).get("tiktok", {}).get("items", [])
            
            if tt_items:
                item = tt_items[0]
                
                # Required fields for TrendItem
                assert item.get("platform") == "tiktok"
                assert "lens" in item
                assert "source_query" in item
                assert "author_handle" in item
                assert "post_url" in item
                assert "caption" in item
                assert "posted_at" in item
                assert "metrics" in item
                assert "score" in item
                
                # Check metrics structure
                metrics = item["metrics"]
                assert "views" in metrics
                assert "likes" in metrics
                assert "comments" in metrics
                
                # Check score structure
                score = item["score"]
                assert "trend_score" in score
                assert "engagement_rate" in score
                assert "recency_score" in score
                
                print(f"TikTok item structure valid. Sample: @{item['author_handle']}, views={metrics['views']}")
            else:
                pytest.skip("No TikTok items in category_trends")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
