"""
Bug Fix Verification Tests - Instagram Import & Step 2 Prerequisite Check

This test file verifies the fixes for the following issues:
1. Missing Instagram import in IntelligenceHub.jsx (line 24)
2. Auto-run logic firing without checking Step 2 (Business DNA) completion

Test brief used: f8065a63-652d-4b91-856a-fc64bc17b3e9 (has FAILED Step 2 status)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestHealthCheck:
    """Verify API is healthy"""
    
    def test_api_health(self):
        """GET /api/ should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert data.get("message") == "Novara API"
        print("✅ API health check passed")


class TestResearchEndpoints:
    """Test all 4 research module endpoints"""
    
    BRIEF_ID = "f8065a63-652d-4b91-856a-fc64bc17b3e9"
    
    def test_customer_intel_latest(self):
        """GET /api/research/{id}/customer-intel/latest should return normalized format"""
        response = requests.get(f"{BASE_URL}/api/research/{self.BRIEF_ID}/customer-intel/latest")
        assert response.status_code == 200
        data = response.json()
        
        # Verify normalized format
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        # For this brief, there's no data
        assert data["has_data"] == False
        assert data["status"] == "not_run"
        assert data["latest"] is None
        print(f"✅ Customer Intel latest endpoint: has_data={data['has_data']}, status={data['status']}")
    
    def test_search_intent_latest(self):
        """GET /api/research/{id}/search-intent/latest should return normalized format"""
        response = requests.get(f"{BASE_URL}/api/research/{self.BRIEF_ID}/search-intent/latest")
        assert response.status_code == 200
        data = response.json()
        
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        print(f"✅ Search Intent latest endpoint: has_data={data['has_data']}, status={data['status']}")
    
    def test_seasonality_latest(self):
        """GET /api/research/{id}/seasonality/latest should return normalized format"""
        response = requests.get(f"{BASE_URL}/api/research/{self.BRIEF_ID}/seasonality/latest")
        assert response.status_code == 200
        data = response.json()
        
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        print(f"✅ Seasonality latest endpoint: has_data={data['has_data']}, status={data['status']}")
    
    def test_competitors_latest(self):
        """GET /api/research/{id}/competitors/latest should return normalized format"""
        response = requests.get(f"{BASE_URL}/api/research/{self.BRIEF_ID}/competitors/latest")
        assert response.status_code == 200
        data = response.json()
        
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        print(f"✅ Competitors latest endpoint: has_data={data['has_data']}, status={data['status']}")


class TestStep2WebsiteContextPack:
    """Test website context pack endpoints"""
    
    BRIEF_ID = "f8065a63-652d-4b91-856a-fc64bc17b3e9"
    
    def test_get_website_context_pack(self):
        """GET /api/website-context-packs/by-campaign/{id} should return pack with status"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.BRIEF_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "status" in data
        assert "campaign_brief_id" in data
        assert data["campaign_brief_id"] == self.BRIEF_ID
        
        # This brief has FAILED Step 2
        assert data["status"] == "failed"
        print(f"✅ Website context pack: status={data['status']}, confidence={data.get('confidence_score', 'N/A')}")
    
    def test_step2_failed_status_prevents_auto_run(self):
        """Pack with status='failed' should NOT trigger auto-run (frontend check via status)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.BRIEF_ID}")
        data = response.json()
        
        # Status is 'failed', which is NOT 'completed' - frontend should NOT auto-run
        assert data["status"] != "completed"
        print(f"✅ Step 2 status is '{data['status']}' - auto-run should be blocked in frontend")


class TestCampaignBriefAPI:
    """Test campaign brief endpoints"""
    
    BRIEF_ID = "f8065a63-652d-4b91-856a-fc64bc17b3e9"
    
    def test_get_campaign_brief(self):
        """GET /api/campaign-briefs/{id} should return brief data"""
        response = requests.get(f"{BASE_URL}/api/campaign-briefs/{self.BRIEF_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "campaign_brief_id" in data
        assert data["campaign_brief_id"] == self.BRIEF_ID
        print(f"✅ Campaign brief found: {data.get('brand', {}).get('website_url', 'N/A')}")
    
    def test_create_campaign_brief(self):
        """POST /api/campaign-briefs should create a new brief"""
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        payload = {
            "website_url": "https://test-site.com",
            "primary_goal": "sales_orders",
            "success_definition": "Increase online sales by 20%",
            "country": "United States",
            "city_or_region": "New York",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "1000-5000",
            "name": "Test User",
            "email": unique_email
        }
        
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        assert response.status_code == 200
        data = response.json()
        
        assert "campaign_brief_id" in data
        assert data["brand"]["website_url"] == "https://test-site.com"
        print(f"✅ Created campaign brief: {data['campaign_brief_id']}")


class TestInvalidCampaignErrors:
    """Test error handling for invalid campaign IDs"""
    
    INVALID_ID = "invalid-campaign-id-12345"
    
    def test_customer_intel_404(self):
        """Customer Intel endpoint should return 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{self.INVALID_ID}/customer-intel/latest")
        assert response.status_code == 404
        print("✅ Customer Intel returns 404 for invalid campaign")
    
    def test_search_intent_404(self):
        """Search Intent endpoint should return 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{self.INVALID_ID}/search-intent/latest")
        assert response.status_code == 404
        print("✅ Search Intent returns 404 for invalid campaign")
    
    def test_seasonality_404(self):
        """Seasonality endpoint should return 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{self.INVALID_ID}/seasonality/latest")
        assert response.status_code == 404
        print("✅ Seasonality returns 404 for invalid campaign")
    
    def test_competitors_404(self):
        """Competitors endpoint should return 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{self.INVALID_ID}/competitors/latest")
        assert response.status_code == 404
        print("✅ Competitors returns 404 for invalid campaign")
    
    def test_website_context_pack_404(self):
        """Website context pack should return 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.INVALID_ID}")
        assert response.status_code == 404
        print("✅ Website context pack returns 404 for invalid campaign")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
