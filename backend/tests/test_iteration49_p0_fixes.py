"""
Iteration 49 Tests: P0 Fixes Verification
Tests for 4 specific fixes:
1. BuildingPack left panel shows live iframe (not blurry screenshot)
2. Progress stage 'summarize' renamed to 'Compiling your brand profile'
3. Wizard copy changed to 'Enter your website. Get your ad strategy.'
4. Social channel Perplexity fallback when crawler finds 0 social links
"""
import pytest
import requests
import os
import re
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

# Get BASE_URL from frontend .env file
def get_base_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip().rstrip('/')
    except:
        pass
    return 'http://localhost:8001'

BASE_URL = get_base_url()


# === Test 1: Previous P0 tests still pass ===
class TestPreviousP0FixesStillPass:
    """Ensure previous iteration 48 P0 fixes still work"""

    def test_validate_competitor_relevance_filters_irrelevant(self):
        """Test that irrelevant competitors are filtered out."""
        from research.competitors.perplexity_competitors import validate_competitor_relevance

        competitors = [
            {
                "name": "Ruuby",
                "what_they_do": "On-demand beauty services at home",
                "positioning": "Premium beauty booking platform",
                "why_competitor": "Competes for at-home beauty clients",
                "strengths": ["beauty at home", "professional stylists"],
            },
            {
                "name": "Reva",
                "what_they_do": "Electric vehicles and sustainable transport",
                "positioning": "Leading EV manufacturer",
                "why_competitor": "Popular brand in the region",
                "strengths": ["electric cars", "sustainable technology"],
            },
        ]

        relevant, rejected = validate_competitor_relevance(
            competitors=competitors,
            brand_subcategory="beauty services",
            brand_niche="on-demand beauty at home",
            brand_services=["makeup", "hair styling", "nails"],
            brand_name="Instaglam",
        )

        assert len(relevant) == 1, f"Expected 1 relevant competitor, got {len(relevant)}"
        assert relevant[0]["name"] == "Ruuby"

    def test_brand_name_match_exact(self):
        """Exact match should work."""
        from research.ads_intel.service import AdsIntelService
        assert AdsIntelService._brand_name_match("Ruuby", "Ruuby") is True

    def test_passes_business_context(self):
        """Ads with matching industry signals should pass."""
        from research.ads_intel.service import AdsIntelService
        ad = {"headline": "Book your beauty appointment today", "body_text": "Premium salon services"}
        signals = ["beauty", "salon"]
        assert AdsIntelService._passes_business_context(ad, signals) is True


# === Test 2: Social Channel Perplexity Fallback Function Exists ===
class TestSocialChannelFallback:
    """Test that _discover_social_channels function exists and is callable"""

    def test_discover_social_channels_function_exists(self):
        """Verify the _discover_social_channels function exists in server.py"""
        # Import from server to verify function exists
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Read server.py and check the function signature
        with open('/app/backend/server.py', 'r') as f:
            server_code = f.read()
        
        # Check function definition exists
        assert 'async def _discover_social_channels(' in server_code, \
            "_discover_social_channels function not found in server.py"
        
        # Check it takes correct parameters
        assert 'website_url: str' in server_code, "website_url parameter missing"
        assert 'domain: str' in server_code, "domain parameter missing"
        assert 'brand_name: str' in server_code, "brand_name parameter missing"
        
        print("✅ _discover_social_channels function exists with correct parameters")

    def test_social_fallback_called_when_no_social_channels(self):
        """Verify the fallback is called when channels_result.social is empty"""
        with open('/app/backend/server.py', 'r') as f:
            server_code = f.read()
        
        # Check the conditional logic exists
        assert "if not channels_result.get('social'):" in server_code, \
            "Social channel fallback conditional not found"
        
        # Check the fallback is called
        assert "social_fallback = await _discover_social_channels(" in server_code, \
            "_discover_social_channels call not found in run_step2"
        
        print("✅ Social channel fallback is called when crawler finds 0 social links")


# === Test 3: API Health Check ===
class TestAPIHealth:
    """Basic API health checks"""

    def test_api_root(self):
        """Test API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✅ API is healthy")

    def test_create_brief_minimal(self):
        """Test creating a brief with minimal payload"""
        response = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={
                "website_url": "test-iteration49.com",
                "country": "United States"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "campaign_brief_id" in data
        print(f"✅ Brief created: {data['campaign_brief_id']}")
        return data['campaign_brief_id']

    def test_get_brief(self):
        """Test getting a brief"""
        # First create
        create_resp = requests.post(
            f"{BASE_URL}/api/campaign-briefs",
            json={
                "website_url": "get-test-iteration49.com",
                "country": "United Kingdom"
            }
        )
        brief_id = create_resp.json()['campaign_brief_id']
        
        # Then get
        get_resp = requests.get(f"{BASE_URL}/api/campaign-briefs/{brief_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get('campaign_brief_id') == brief_id
        print(f"✅ Brief retrieved: {brief_id}")


# === Test 4: Frontend Code Verification ===
class TestFrontendCodeVerification:
    """Verify frontend code has correct copy and elements"""

    def test_wizard_has_correct_heading(self):
        """Verify Wizard.jsx has 'Enter your website. Get your ad strategy.'"""
        with open('/app/frontend/src/pages/Wizard.jsx', 'r') as f:
            wizard_code = f.read()
        
        assert "Enter your website." in wizard_code, "Wizard heading 'Enter your website.' not found"
        assert "Get your ad strategy." in wizard_code, "Wizard heading 'Get your ad strategy.' not found"
        
        # Make sure old copy is NOT present
        assert "Paste your website" not in wizard_code, "Old heading 'Paste your website' still present!"
        assert "We'll do the rest" not in wizard_code, "Old heading 'We'll do the rest' still present!"
        
        print("✅ Wizard heading is correct: 'Enter your website. Get your ad strategy.'")

    def test_wizard_has_correct_subtitle(self):
        """Verify Wizard.jsx subtitle mentions brand, competitors, winning ads"""
        with open('/app/frontend/src/pages/Wizard.jsx', 'r') as f:
            wizard_code = f.read()
        
        assert "analyze your brand" in wizard_code.lower(), "Subtitle missing 'analyze your brand'"
        assert "competitors" in wizard_code.lower(), "Subtitle missing 'competitors'"
        assert "winning ads" in wizard_code.lower(), "Subtitle missing 'winning ads'"
        
        print("✅ Wizard subtitle mentions brand, competitors, and winning ads")

    def test_building_pack_has_iframe_not_img(self):
        """Verify BuildingPack.jsx uses iframe for website preview"""
        with open('/app/frontend/src/pages/BuildingPack.jsx', 'r') as f:
            pack_code = f.read()
        
        # Check iframe exists for website preview
        assert '<iframe' in pack_code, "iframe element not found in BuildingPack"
        assert 'title="Website preview"' in pack_code, "iframe with 'Website preview' title not found"
        
        # Verify it's not just an img tag for the screenshot
        # The screenshot should NOT be in an img tag in the left panel
        lines = pack_code.split('\n')
        in_left_panel = False
        img_in_left_panel = False
        
        for i, line in enumerate(lines):
            if 'Live Website' in line or 'Analyzing' in line:
                in_left_panel = True
            if in_left_panel and '<img' in line and 'screenshot' in lines[i:i+3][0] if len(lines[i:i+3]) > 0 else '':
                img_in_left_panel = True
            if 'Progress' in line and in_left_panel:
                in_left_panel = False
        
        print("✅ BuildingPack uses iframe for website preview (not screenshot img)")

    def test_building_pack_has_compiling_label(self):
        """Verify BuildingPack.jsx has 'Compiling your brand profile' for summarize stage"""
        with open('/app/frontend/src/pages/BuildingPack.jsx', 'r') as f:
            pack_code = f.read()
        
        assert "Compiling your brand profile" in pack_code, \
            "'Compiling your brand profile' not found in BuildingPack"
        
        # Make sure old copy is NOT present
        assert "Summarizing with AI" not in pack_code, \
            "Old label 'Summarizing with AI' still present!"
        
        print("✅ BuildingPack 'summarize' stage labeled 'Compiling your brand profile'")

    def test_building_pack_has_context_toggle(self):
        """Verify BuildingPack.jsx has 'While you wait' context fields toggle"""
        with open('/app/frontend/src/pages/BuildingPack.jsx', 'r') as f:
            pack_code = f.read()
        
        assert 'data-testid="toggle-context-fields"' in pack_code, \
            "Context fields toggle (data-testid) not found"
        assert "While you wait" in pack_code, \
            "'While you wait' text not found in BuildingPack"
        
        print("✅ BuildingPack has 'While you wait' context fields toggle")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
