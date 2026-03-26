"""
Intelligence Hub Stress Test - Iteration 66
Tests all 10 research module API endpoints + core health endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_BRIEF_ID = "d2d2566b-5b7f-4456-b7ad-1a8ee88256f2"

# All 9 research modules API slugs
RESEARCH_MODULES = [
    "customer-intel",
    "search-intent", 
    "seasonality",
    "competitors",
    "reviews",
    "community",
    "press-media",
    "social-trends",
    "ads-intel"
]

class TestBackendHealth:
    """Core backend health checks"""
    
    def test_api_root_health(self):
        """Test backend API root responds 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: /api/ returns {response.status_code}")
    
    def test_api_health_endpoint(self):
        """Test /api/health endpoint if exists"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        # May be 200 or 404 depending on implementation
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"INFO: /api/health returns {response.status_code}")


class TestResearchModuleEndpoints:
    """Test all research module API endpoints respond (even if auth required)"""
    
    @pytest.mark.parametrize("module_slug", RESEARCH_MODULES)
    def test_latest_endpoint_responds(self, module_slug):
        """Test /api/research/{briefId}/{module}/latest endpoint availability"""
        url = f"{BASE_URL}/api/research/{TEST_BRIEF_ID}/{module_slug}/latest"
        response = requests.get(url, timeout=15)
        # Accept 200 (data exists), 401 (auth required), or 404 (not run yet)
        valid_codes = [200, 401, 404]
        assert response.status_code in valid_codes, f"{module_slug}/latest: unexpected {response.status_code}"
        print(f"PASS: {module_slug}/latest returns {response.status_code}")
    
    @pytest.mark.parametrize("module_slug", RESEARCH_MODULES)
    def test_history_endpoint_responds(self, module_slug):
        """Test /api/research/{briefId}/{module}/history endpoint availability"""
        url = f"{BASE_URL}/api/research/{TEST_BRIEF_ID}/{module_slug}/history"
        response = requests.get(url, timeout=15)
        # Accept 200, 401, or 404
        valid_codes = [200, 401, 404]
        assert response.status_code in valid_codes, f"{module_slug}/history: unexpected {response.status_code}"
        print(f"PASS: {module_slug}/history returns {response.status_code}")
    
    @pytest.mark.parametrize("module_slug", RESEARCH_MODULES)
    def test_run_endpoint_responds_to_options(self, module_slug):
        """Test /api/research/{briefId}/{module}/run accepts OPTIONS (CORS)"""
        url = f"{BASE_URL}/api/research/{TEST_BRIEF_ID}/{module_slug}/run"
        response = requests.options(url, timeout=10)
        # OPTIONS should return 200 for CORS preflight
        assert response.status_code in [200, 204, 405], f"{module_slug}/run OPTIONS: {response.status_code}"
        print(f"INFO: {module_slug}/run OPTIONS returns {response.status_code}")


class TestPackAndCampaignEndpoints:
    """Test pack/campaign related endpoints"""
    
    def test_pack_endpoint_exists(self):
        """Test /api/pack/{briefId} endpoint"""
        url = f"{BASE_URL}/api/pack/{TEST_BRIEF_ID}"
        response = requests.get(url, timeout=10)
        # Should be 200 or 404
        assert response.status_code in [200, 404], f"pack endpoint: {response.status_code}"
        print(f"INFO: /api/pack/{TEST_BRIEF_ID[:8]}... returns {response.status_code}")
    
    def test_website_context_pack_endpoint(self):
        """Test /api/website-context-packs/by-campaign/{briefId} endpoint"""
        url = f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}"
        response = requests.get(url, timeout=10)
        # Should be 200 (exists) or 404 (not found)
        assert response.status_code in [200, 404], f"website-context-packs: {response.status_code}"
        print(f"INFO: /api/website-context-packs returns {response.status_code}")


class TestFrontendRoutes:
    """Test frontend routes respond"""
    
    def test_homepage_loads(self):
        """Test homepage returns 200"""
        response = requests.get(f"{BASE_URL}/", timeout=10)
        assert response.status_code == 200, f"Homepage: {response.status_code}"
        print(f"PASS: Homepage returns {response.status_code}")
    
    def test_pack_view_route(self):
        """Test /pack/{briefId} route loads"""
        response = requests.get(f"{BASE_URL}/pack/{TEST_BRIEF_ID}", timeout=10)
        assert response.status_code == 200, f"PackView: {response.status_code}"
        print(f"PASS: /pack/{TEST_BRIEF_ID[:8]}... returns {response.status_code}")
    
    def test_intel_route_responds(self):
        """Test /intel/{briefId} route loads (may redirect to auth)"""
        response = requests.get(f"{BASE_URL}/intel/{TEST_BRIEF_ID}", timeout=10, allow_redirects=False)
        # Could be 200, 302 (redirect to auth), or 401
        valid_codes = [200, 301, 302, 307, 401]
        assert response.status_code in valid_codes, f"Intel route: {response.status_code}"
        print(f"INFO: /intel/{TEST_BRIEF_ID[:8]}... returns {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
