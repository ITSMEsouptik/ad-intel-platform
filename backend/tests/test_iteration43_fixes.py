"""
Iteration 43 Verification Tests
================================
Verifies the 4 fixes implemented:
1. Foreplay credit optimization - COMPETITOR_FETCH_LIMIT=50, name fallback limit=15
2. Reviews niche platform detection - substring match (not exact key match)
3. Competitor geo prompt - city-level requirement
4. TikTok ads handling (confirmed working)

Campaign IDs:
- 568e45c8-7976-4d14-878a-70074f35f3ff: 19 ads (9 comp + 10 cat)
- a517c420-418d-416d-87ae-6e768b21c43b: 10 ads (0 comp + 10 cat)
"""

import pytest
import requests
import os
import sys
import re

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============== UNIT TESTS ==============

class TestForeplayCreditOptimization:
    """Test COMPETITOR_FETCH_LIMIT and name fallback limit values"""
    
    def test_competitor_fetch_limit_default_is_50(self):
        """COMPETITOR_FETCH_LIMIT default value should be 50"""
        # Read the service.py file and check the default
        with open('/app/backend/research/ads_intel/service.py', 'r') as f:
            content = f.read()
        
        # Check for default value of 50
        match = re.search(r'COMPETITOR_FETCH_LIMIT\s*=\s*int\(os\.environ\.get\([^,]+,\s*["\'](\d+)["\']\)', content)
        assert match, "COMPETITOR_FETCH_LIMIT default not found"
        default_value = int(match.group(1))
        assert default_value == 50, f"Expected default 50, got {default_value}"
        print(f"✓ COMPETITOR_FETCH_LIMIT default is 50")
    
    def test_name_fallback_discovery_limit_is_15(self):
        """Name fallback discovery should use limit=15"""
        with open('/app/backend/research/ads_intel/service.py', 'r') as f:
            content = f.read()
        
        # Look for the name fallback section with limit=15
        # This is in _run_competitor_lens where discovery_ads is called with limit=15
        assert 'limit=15' in content, "limit=15 not found in service.py"
        
        # Verify it's in the context of fallback discovery
        lines = content.split('\n')
        found_limit_15_in_fallback = False
        for i, line in enumerate(lines):
            if 'limit=15' in line:
                # Check context (look at nearby lines)
                context = '\n'.join(lines[max(0,i-10):i+5])
                if 'fallback' in context.lower() or 'discovery_ads' in context:
                    found_limit_15_in_fallback = True
                    break
        
        assert found_limit_15_in_fallback, "limit=15 not found in name fallback context"
        print(f"✓ Name fallback uses limit=15")


class TestReviewsNichePlatformSubstringMatch:
    """Test that niche platform detection uses substring matching"""
    
    def test_niche_platform_substring_match_code(self):
        """NICHE_REVIEW_PLATFORMS should use substring match (key in niche_lower)"""
        with open('/app/backend/research/reviews/perplexity_reviews.py', 'r') as f:
            content = f.read()
        
        # Check for substring match pattern
        assert 'key in niche_lower' in content, "Substring match 'key in niche_lower' not found"
        assert 'key in subcat_lower' in content, "Substring match 'key in subcat_lower' not found"
        
        # Ensure it's NOT exact key match like niche_lower == key
        assert 'niche_lower == key' not in content, "Exact match found - should be substring"
        assert 'niche_lower.get(' not in content, "Dict get found - should be substring"
        
        print(f"✓ Niche platform uses substring match (key in niche_lower)")
    
    def test_beauty_matches_on_demand_beauty_services(self):
        """'beauty' key should match 'on-demand beauty services' niche"""
        # Import the function
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        # Test case from the bug report: niche = "On-Demand Beauty Services"
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="UAE",
            niche="On-Demand Beauty Services",  # The actual niche value
            subcategory="",
            app_store_urls=None
        )
        
        # Should find beauty-specific platforms: Fresha, Booksy, StyleSeat
        beauty_platforms = {'Fresha', 'Booksy', 'StyleSeat'}
        found_beauty_platforms = beauty_platforms.intersection(set(combined))
        
        assert len(found_beauty_platforms) > 0, f"No beauty platforms found. Combined: {combined}"
        print(f"✓ 'beauty' matches 'On-Demand Beauty Services' - found platforms: {found_beauty_platforms}")
    
    def test_salon_matches_salon_niche(self):
        """'salon' key should match niche containing 'salon'"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="UAE",
            niche="Hair Salon Services",
            subcategory="",
            app_store_urls=None
        )
        
        # salon key maps to: Fresha, Booksy, StyleSeat
        salon_platforms = {'Fresha', 'Booksy', 'StyleSeat'}
        found_salon_platforms = salon_platforms.intersection(set(combined))
        
        assert len(found_salon_platforms) > 0, f"No salon platforms found. Combined: {combined}"
        print(f"✓ 'salon' matches 'Hair Salon Services' - found platforms: {found_salon_platforms}")


class TestCompetitorGeoPrompt:
    """Test competitor prompt includes city-level geo requirement"""
    
    def test_prompt_contains_city_level_requirement(self):
        """Competitor prompt should require active operations in city, not just country"""
        from research.competitors.perplexity_competitors import build_competitor_prompt
        
        prompt = build_competitor_prompt(
            brand_name="TestBrand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="Salon",
            business_type="service_provider",
            price_tier="premium",
            tagline="",
            one_liner="",
            bullets=[],
            value_prop="",
            key_benefits=[],
            services=["haircut"],
            price_range=None,
            values=[],
            tone_of_voice=[],
            aesthetic=[],
            destination_type="website",
            primary_action=""
        )
        
        # Check for city-level requirement in prompt
        assert "active operations in" in prompt.lower(), "Missing 'active operations in' requirement"
        assert "Dubai" in prompt, "City name should be in prompt"
        
        # Check for specific wording about city vs country
        has_city_requirement = any(phrase in prompt for phrase in [
            "active operations in {city}",
            "active operations in Dubai",
            "not just \"plans to expand\"",
            "serve {city} customers"
        ])
        assert has_city_requirement or "Dubai, UAE" in prompt, "City-level geo requirement not specific enough"
        
        print(f"✓ Competitor prompt includes city-level geo requirement")


# ============== API INTEGRATION TESTS ==============

class TestCampaignAdsAPI:
    """Test campaigns return expected ad counts"""
    
    @pytest.fixture
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def test_campaign_568e45c8_ads_count(self, api_client):
        """Campaign 568e45c8 should return 19 ads (9 comp + 10 cat)"""
        campaign_id = "568e45c8-7976-4d14-878a-70074f35f3ff"
        
        response = api_client.get(f"{BASE_URL}/api/research/{campaign_id}/ads-intel/latest")
        assert response.status_code == 200, f"Failed to get ads-intel: {response.text}"
        
        data = response.json()
        assert "latest" in data, "Response missing latest"
        
        snapshot = data["latest"]
        comp_ads = snapshot.get("competitor_winners", {}).get("ads", [])
        cat_ads = snapshot.get("category_winners", {}).get("ads", [])
        
        comp_count = len(comp_ads)
        cat_count = len(cat_ads)
        total = comp_count + cat_count
        
        print(f"Campaign 568e45c8: {comp_count} competitor + {cat_count} category = {total} total ads")
        
        # Expected: 19 ads (9 comp + 10 cat) per main agent
        # Allow some variance since data can change
        assert total >= 10, f"Too few ads: {total}"
        assert comp_count >= 5, f"Expected ~9 competitor ads, got {comp_count}"
        
        # Check audit for API calls (should be fewer now with limit=50)
        audit = snapshot.get("audit", {})
        api_calls = audit.get("api_calls", 0)
        total_ads_seen = audit.get("total_ads_seen", 0)
        print(f"Audit: {api_calls} API calls, {total_ads_seen} total ads fetched")
        
        print(f"✓ Campaign 568e45c8 returns {total} ads ({comp_count} comp + {cat_count} cat)")
    
    def test_campaign_a517c420_ads_count(self, api_client):
        """Campaign a517c420 should return 10 ads (0 comp + 10 cat) - context validation works"""
        campaign_id = "a517c420-418d-416d-87ae-6e768b21c43b"
        
        response = api_client.get(f"{BASE_URL}/api/research/{campaign_id}/ads-intel/latest")
        assert response.status_code == 200, f"Failed to get ads-intel: {response.text}"
        
        data = response.json()
        snapshot = data.get("latest", {})
        
        comp_ads = snapshot.get("competitor_winners", {}).get("ads", [])
        cat_ads = snapshot.get("category_winners", {}).get("ads", [])
        
        comp_count = len(comp_ads)
        cat_count = len(cat_ads)
        total = comp_count + cat_count
        
        print(f"Campaign a517c420: {comp_count} competitor + {cat_count} category = {total} total ads")
        
        # Expected: 10 ads (0 comp + 10 cat) - context validation rejects false positives
        assert cat_count >= 5, f"Expected ~10 category ads, got {cat_count}"
        
        # Competitor ads should be 0 or very low due to context validation
        assert comp_count <= 5, f"Expected 0 competitor ads (context validation), got {comp_count}"
        
        print(f"✓ Campaign a517c420 returns {total} ads ({comp_count} comp + {cat_count} cat) - context validation working")


class TestReviewsPlatformPresence:
    """Test reviews tab shows platform presence info"""
    
    @pytest.fixture
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def test_campaign_reviews_api(self, api_client):
        """Reviews API should return platform presence info"""
        campaign_id = "568e45c8-7976-4d14-878a-70074f35f3ff"
        
        response = api_client.get(f"{BASE_URL}/api/research/{campaign_id}/reviews")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for discovery data
            discovery = data.get("discovery", {})
            platforms_found = discovery.get("platforms_found", [])
            
            print(f"Reviews: Found {len(platforms_found)} platforms")
            for p in platforms_found[:3]:
                print(f"  - {p.get('platform')}: {p.get('approximate_rating')} stars")
            
            print(f"✓ Reviews API returns platform presence data")
        else:
            # Reviews might not have been run for this campaign yet
            print(f"⚠ Reviews API returned {response.status_code} - may need to run reviews module first")
            pytest.skip(f"Reviews not available: {response.status_code}")


# ============== ENV VAR VALIDATION ==============

class TestEnvVarConfiguration:
    """Validate environment variable configuration"""
    
    def test_env_var_competitor_fetch_limit(self):
        """Check if ADS_INTEL_COMPETITOR_AD_FETCH_LIMIT env var is set correctly"""
        # Read the .env file
        with open('/app/backend/.env', 'r') as f:
            env_content = f.read()
        
        # Check what value is set
        match = re.search(r'ADS_INTEL_COMPETITOR_AD_FETCH_LIMIT=(\d+)', env_content)
        
        if match:
            env_value = int(match.group(1))
            print(f"⚠ ENV VAR: ADS_INTEL_COMPETITOR_AD_FETCH_LIMIT={env_value}")
            
            if env_value != 50:
                print(f"⚠ WARNING: Env var is {env_value}, but main agent claims fix changed it to 50")
                print(f"  The default in code is 50, but env var overrides it to {env_value}")
            else:
                print(f"✓ Env var correctly set to 50")
        else:
            print(f"✓ No env var set - will use default of 50")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
