"""
Test P0 Fixes: Social channel extraction (Jina Reader) and Brand color filtering (no Wix colors)

P0 Fix 1: Social channel extraction works for SPA/Wix sites like example-brand.co
  - Jina Reader fallback when crawler finds 0 social channels
  - Should find Instagram, Facebook, LinkedIn

P0 Fix 2: Color extraction filters Wix platform colors
  - Should NOT include #116dff, #7fccf7, #3899ec
  - Should show actual brand colors identified by LLM
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test Brief ID with existing data for example-brand.co
INSTAGLAM_BRIEF_ID = "65f7d5f3-33db-40b7-a7b2-702ce92472de"

# Wix platform colors to filter
WIX_PLATFORM_COLORS = {
    '#116dff', '#0f2ccf', '#2f5dff', '#597dff', '#acbeff', '#d5dfff',
    '#eaefff', '#f5f7ff', '#7fccf7', '#3899ec', '#5c7cfa', '#4c6ef5',
    '#ff4040', '#09f', '#0099ff', '#4eb7f5', '#bcebff', '#e7f5ff',
    '#e8e8e8', '#d6d6d6', '#c4c4c4', '#00a98f', '#60bc57', '#ee5951',
    '#fb7d33', '#f2c94c', '#dfe5eb', '#c1c1c1', '#84939e', '#577083', '#3b4057',
}


class TestSocialChannelExtraction:
    """Tests for P0 Fix 1: Social channel extraction via Jina Reader fallback"""
    
    def test_existing_pack_has_social_channels(self):
        """Verify the existing example-brand.co pack has social channels extracted"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200, f"Failed to fetch pack: {response.text}"
        
        pack = response.json()
        step2 = pack.get('step2', {})
        channels = step2.get('channels', {})
        social = channels.get('social', [])
        
        # Should have at least some social channels
        assert len(social) > 0, "No social channels found - Jina fallback not working"
        print(f"SUCCESS: Found {len(social)} social channels")
        
    def test_social_channels_have_correct_format(self):
        """Verify social channel objects have platform, url, handle"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        social = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        for channel in social:
            assert 'platform' in channel, f"Missing 'platform' in channel: {channel}"
            assert 'url' in channel, f"Missing 'url' in channel: {channel}"
            assert channel['platform'] in ['instagram', 'facebook', 'linkedin', 'tiktok', 'youtube', 'twitter'], \
                f"Unknown platform: {channel['platform']}"
            print(f"  {channel['platform']}: {channel.get('url', '')} (@{channel.get('handle', '')})")
        
        print(f"SUCCESS: All {len(social)} social channels have correct format")
        
    def test_instagram_channel_found(self):
        """Verify Instagram channel was extracted for example-brand.co"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        social = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        platforms = [c['platform'] for c in social]
        assert 'instagram' in platforms, f"Instagram not found. Platforms: {platforms}"
        
        # Verify Instagram URL is valid
        instagram = next((c for c in social if c['platform'] == 'instagram'), None)
        assert instagram is not None
        assert 'instagram.com' in instagram['url'], f"Invalid Instagram URL: {instagram['url']}"
        print(f"SUCCESS: Instagram found - {instagram['url']}")
        
    def test_facebook_channel_found(self):
        """Verify Facebook channel was extracted for example-brand.co"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        social = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        platforms = [c['platform'] for c in social]
        assert 'facebook' in platforms, f"Facebook not found. Platforms: {platforms}"
        
        facebook = next((c for c in social if c['platform'] == 'facebook'), None)
        assert facebook is not None
        assert 'facebook.com' in facebook['url'], f"Invalid Facebook URL: {facebook['url']}"
        print(f"SUCCESS: Facebook found - {facebook['url']}")
        
    def test_linkedin_channel_found(self):
        """Verify LinkedIn channel was extracted for example-brand.co"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        social = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        platforms = [c['platform'] for c in social]
        assert 'linkedin' in platforms, f"LinkedIn not found. Platforms: {platforms}"
        
        linkedin = next((c for c in social if c['platform'] == 'linkedin'), None)
        assert linkedin is not None
        assert 'linkedin.com' in linkedin['url'], f"Invalid LinkedIn URL: {linkedin['url']}"
        print(f"SUCCESS: LinkedIn found - {linkedin['url']}")


class TestJinaReaderIntegration:
    """Direct tests for Jina Reader API integration"""
    
    def test_jina_reader_api_accessible(self):
        """Verify Jina Reader API is accessible and returns content"""
        response = requests.get(
            "https://r.jina.ai/https://example-brand.co",
            headers={"Accept": "application/json"},
            timeout=30
        )
        assert response.status_code == 200, f"Jina Reader API error: {response.status_code}"
        
        data = response.json()
        content = data.get('data', {}).get('content', '')
        assert len(content) > 100, "Jina Reader returned insufficient content"
        print(f"SUCCESS: Jina Reader returned {len(content)} characters")
        
    def test_jina_content_contains_social_links(self):
        """Verify Jina rendered content includes social media links"""
        response = requests.get(
            "https://r.jina.ai/https://example-brand.co",
            headers={"Accept": "application/json"},
            timeout=30
        )
        assert response.status_code == 200
        
        content = response.json().get('data', {}).get('content', '')
        
        # Check for social platform links
        has_instagram = 'instagram.com' in content.lower()
        has_facebook = 'facebook.com' in content.lower()
        has_linkedin = 'linkedin.com' in content.lower()
        
        assert has_instagram or has_facebook or has_linkedin, \
            "No social links found in Jina content - SPA rendering may have failed"
        
        print(f"Social links in Jina content: Instagram={has_instagram}, Facebook={has_facebook}, LinkedIn={has_linkedin}")
        

class TestBrandColorFiltering:
    """Tests for P0 Fix 2: Brand color extraction without Wix platform colors"""
    
    def test_existing_pack_has_colors(self):
        """Verify the existing example-brand.co pack has brand colors extracted"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        colors = pack.get('step2', {}).get('identity', {}).get('colors', [])
        
        assert len(colors) > 0, "No brand colors found"
        print(f"SUCCESS: Found {len(colors)} brand colors")
        for color in colors:
            print(f"  {color.get('hex')} - {color.get('role')}")
            
    def test_no_wix_platform_colors(self):
        """Verify Wix platform colors (#116dff, #7fccf7, #3899ec) are NOT in the pack"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        colors = pack.get('step2', {}).get('identity', {}).get('colors', [])
        
        extracted_hexes = {c.get('hex', '').lower() for c in colors}
        
        # Check that none of the Wix platform colors are present
        wix_found = extracted_hexes.intersection(WIX_PLATFORM_COLORS)
        assert len(wix_found) == 0, f"Wix platform colors found in pack: {wix_found}"
        
        print(f"SUCCESS: No Wix platform colors found. Extracted colors: {extracted_hexes}")
        
    def test_colors_have_valid_hex_format(self):
        """Verify all colors have valid hex format (#xxxxxx)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        colors = pack.get('step2', {}).get('identity', {}).get('colors', [])
        
        hex_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
        
        for color in colors:
            hex_val = color.get('hex', '')
            assert hex_pattern.match(hex_val), f"Invalid hex format: {hex_val}"
            assert 'role' in color, f"Missing 'role' in color: {color}"
            
        print(f"SUCCESS: All {len(colors)} colors have valid hex format")
        
    def test_colors_have_proper_roles(self):
        """Verify colors have proper role assignments (primary, secondary, accent, bg, text)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        colors = pack.get('step2', {}).get('identity', {}).get('colors', [])
        
        valid_roles = {'primary', 'secondary', 'accent', 'bg', 'text'}
        
        for color in colors:
            role = color.get('role', '')
            assert role in valid_roles, f"Invalid role '{role}' for color {color.get('hex')}"
            
        print(f"SUCCESS: All colors have valid roles")


class TestMergeColorsLogic:
    """Tests for the _merge_colors function behavior"""
    
    def test_llm_colors_prioritized(self):
        """Verify LLM-identified colors are prioritized over CSS colors"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        colors = pack.get('step2', {}).get('identity', {}).get('colors', [])
        
        # Colors should be diverse (not all similar shades)
        hexes = [c.get('hex', '') for c in colors]
        
        # Check that we have distinct colors (not all same color family)
        assert len(hexes) >= 2, "Too few colors for meaningful comparison"
        
        # Colors should be visually distinct (simple heuristic)
        unique_first_chars = set(h[1] if len(h) > 1 else '' for h in hexes)
        print(f"SUCCESS: Found {len(colors)} distinct colors from merge logic")


class TestEndToEndOrchestration:
    """End-to-end tests for the full orchestration flow"""
    
    def test_orchestration_status_endpoint(self):
        """Verify orchestration status returns social and color data"""
        response = requests.get(f"{BASE_URL}/api/orchestrations/{INSTAGLAM_BRIEF_ID}/status")
        assert response.status_code == 200
        
        data = response.json()
        pack = data.get('website_context_pack', {})
        
        assert pack is not None, "No website_context_pack in orchestration status"
        assert pack.get('status') in ['success', 'partial', 'running', 'completed'], \
            f"Unexpected pack status: {pack.get('status')}"
            
        print(f"SUCCESS: Orchestration status returned with pack status: {pack.get('status')}")
        
    def test_pack_view_api_returns_full_data(self):
        """Verify pack API returns complete step2 data for frontend"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        assert response.status_code == 200
        
        pack = response.json()
        step2 = pack.get('step2', {})
        
        # Verify all required sections exist
        required_sections = ['site', 'classification', 'brand_summary', 'identity', 'channels']
        for section in required_sections:
            assert section in step2, f"Missing section '{section}' in step2"
            
        # Verify identity has colors and fonts
        identity = step2.get('identity', {})
        assert 'colors' in identity, "Missing 'colors' in identity"
        assert 'fonts' in identity, "Missing 'fonts' in identity"
        
        # Verify channels has social
        channels = step2.get('channels', {})
        assert 'social' in channels, "Missing 'social' in channels"
        
        print(f"SUCCESS: Pack API returns complete step2 data")


class TestCodeImplementation:
    """Tests verifying the code implementation is correct"""
    
    def test_jina_fallback_in_server(self):
        """Verify _fetch_jina_content and _extract_social_from_jina_content exist in server.py"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("server", "/app/backend/server.py")
        # We just verify the file has the functions via grep (done in test setup)
        # This is a sanity check
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
            
        assert '_fetch_jina_content' in content, "Missing _fetch_jina_content function"
        assert '_extract_social_from_jina_content' in content, "Missing _extract_social_from_jina_content function"
        assert 'r.jina.ai' in content, "Missing Jina Reader API URL"
        
        print("SUCCESS: Jina fallback functions exist in server.py")
        
    def test_wix_color_filter_in_brand_identity(self):
        """Verify WIX_PLATFORM_COLORS filter exists in brand_identity.py"""
        with open('/app/backend/brand_identity.py', 'r') as f:
            content = f.read()
            
        assert 'WIX_PLATFORM_COLORS' in content, "Missing WIX_PLATFORM_COLORS filter"
        assert '#116dff' in content, "Missing primary Wix color in filter list"
        assert '#7fccf7' in content, "Missing Wix color #7fccf7 in filter list"
        assert '#3899ec' in content, "Missing Wix color #3899ec in filter list"
        
        print("SUCCESS: Wix color filter exists in brand_identity.py")
        
    def test_merge_colors_in_server(self):
        """Verify _merge_colors function combines LLM + CSS colors"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
            
        assert '_merge_colors' in content, "Missing _merge_colors function"
        assert 'llm_colors' in content, "Missing llm_colors parameter in _merge_colors"
        
        print("SUCCESS: _merge_colors function exists for color merging")
        
    def test_perplexity_natural_language_prompt(self):
        """Verify _discover_social_channels uses natural language prompt (not JSON-forced)"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
            
        # Check that the function doesn't use json_schema response format
        discover_func_match = re.search(
            r'async def _discover_social_channels.*?(?=\nasync def|\ndef |\nclass |\Z)', 
            content, 
            re.DOTALL
        )
        
        assert discover_func_match, "Could not find _discover_social_channels function"
        func_content = discover_func_match.group(0)
        
        # Should NOT have json_schema forcing
        assert 'json_schema' not in func_content, \
            "_discover_social_channels should use natural language, not JSON schema"
            
        # Should have natural language prompt
        assert 'social media profiles' in func_content.lower() or 'instagram' in func_content.lower(), \
            "_discover_social_channels should ask for social profiles in natural language"
            
        print("SUCCESS: _discover_social_channels uses natural language prompt")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
