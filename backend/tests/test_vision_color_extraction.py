"""
Test Vision-Based Color Extraction Pipeline
Tests for iteration 51:
- Vision color extraction with screenshot bland detection
- Context-based LLM fallback for SPAs with bland screenshots
- Wix platform color filtering
- Near-white/black color filtering
- _merge_colors function behavior
- Social channels via Jina Reader
"""

import pytest
import requests
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_BRIEF_ID = "e26c5085-01ef-4650-b878-4a1593e9c051"  # Test pack for example-brand.co

# Wix platform colors to verify are filtered
WIX_PLATFORM_COLORS = {
    '#116dff', '#0f2ccf', '#2f5dff', '#597dff', '#acbeff', '#d5dfff',
    '#eaefff', '#f5f7ff', '#7fccf7', '#3899ec', '#5c7cfa', '#4c6ef5',
    '#ff4040', '#09f', '#0099ff', '#4eb7f5', '#bcebff', '#e7f5ff',
    '#e8e8e8', '#d6d6d6', '#c4c4c4', '#00a98f', '#60bc57', '#ee5951', 
    '#fb7d33', '#f2c94c', '#dfe5eb', '#c1c1c1', '#84939e', '#577083', '#3b4057'
}

# Colors to skip (near-white, near-black)
SKIP_COLORS = {'#ffffff', '#000000', '#f5f5f5', '#fafafa', '#f4f4f4', 
               '#eeeeee', '#e5e5e5', '#333333', '#111111'}


class TestVisionColorExtraction:
    """Test vision-based brand color extraction pipeline"""
    
    def test_pack_exists_and_has_success_status(self):
        """Verify the test pack exists and has success status"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        assert response.status_code == 200, f"Failed to fetch pack: {response.status_code}"
        
        data = response.json()
        assert data.get('status') == 'success', f"Pack status is '{data.get('status')}', expected 'success'"
        assert 'step2' in data, "Pack missing step2 data"
        print(f"PASS: Pack exists with status '{data['status']}'")
    
    def test_colors_count_within_range(self):
        """Verify colors are extracted and count is within expected range (3-6)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        assert len(colors) >= 3, f"Too few colors: {len(colors)}, expected at least 3"
        assert len(colors) <= 8, f"Too many colors: {len(colors)}, expected at most 8"
        
        print(f"PASS: {len(colors)} colors extracted")
        for c in colors:
            print(f"  - {c.get('hex')} ({c.get('role')})")
    
    def test_no_wix_platform_colors(self):
        """Verify no Wix platform colors are in the extracted palette"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        extracted_hexes = {c.get('hex', '').lower() for c in colors}
        
        wix_in_palette = extracted_hexes & WIX_PLATFORM_COLORS
        assert len(wix_in_palette) == 0, f"Wix platform colors found in palette: {wix_in_palette}"
        
        print("PASS: No Wix platform colors in extracted palette")
    
    def test_no_pure_white_black(self):
        """Verify no pure white (#ffffff) or black (#000000) in palette"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        extracted_hexes = {c.get('hex', '').lower() for c in colors}
        
        skip_in_palette = extracted_hexes & SKIP_COLORS
        assert len(skip_in_palette) == 0, f"Generic colors found in palette: {skip_in_palette}"
        
        print("PASS: No pure white/black/generic colors in palette")
    
    def test_no_near_white_or_near_black_colors(self):
        """Verify no near-white or near-black colors (brightness > 235 or < 20 with low saturation)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        
        def is_near_white_or_black(hex_val):
            """Check if color is near white/black with low saturation"""
            h = hex_val.lstrip('#').lower()
            if len(h) != 6:
                return False
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            max_c = max(r, g, b)
            saturation = (max_c - min(r, g, b)) / max(max_c, 1) if max_c > 0 else 0
            return (brightness > 235 or brightness < 20) and saturation < 0.15
        
        near_extremes = [c['hex'] for c in colors if is_near_white_or_black(c.get('hex', ''))]
        assert len(near_extremes) == 0, f"Near-white/black colors found: {near_extremes}"
        
        print("PASS: No near-white or near-black colors in palette")
    
    def test_colors_have_valid_structure(self):
        """Verify color objects have hex and role fields"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        
        for i, color in enumerate(colors):
            assert 'hex' in color, f"Color {i} missing 'hex' field"
            assert 'role' in color, f"Color {i} missing 'role' field"
            assert color['hex'].startswith('#'), f"Color {i} hex does not start with #: {color['hex']}"
            assert len(color['hex']) == 7, f"Color {i} hex wrong length: {color['hex']}"
        
        print("PASS: All colors have valid structure")


class TestSocialChannels:
    """Test social channel extraction via Jina Reader"""
    
    def test_social_channels_exist(self):
        """Verify social channels are extracted"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        social = data.get('step2', {}).get('channels', {}).get('social', [])
        assert len(social) >= 3, f"Expected at least 3 social channels, got {len(social)}"
        
        print(f"PASS: {len(social)} social channels found")
        for s in social:
            print(f"  - {s.get('platform')}: {s.get('url')}")
    
    def test_instagram_channel_extracted(self):
        """Verify Instagram channel is extracted"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        social = data.get('step2', {}).get('channels', {}).get('social', [])
        platforms = {s.get('platform') for s in social}
        
        assert 'instagram' in platforms, f"Instagram not found. Platforms: {platforms}"
        print("PASS: Instagram channel extracted")
    
    def test_facebook_channel_extracted(self):
        """Verify Facebook channel is extracted"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        social = data.get('step2', {}).get('channels', {}).get('social', [])
        platforms = {s.get('platform') for s in social}
        
        assert 'facebook' in platforms, f"Facebook not found. Platforms: {platforms}"
        print("PASS: Facebook channel extracted")
    
    def test_linkedin_channel_extracted(self):
        """Verify LinkedIn channel is extracted"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        social = data.get('step2', {}).get('channels', {}).get('social', [])
        platforms = {s.get('platform') for s in social}
        
        assert 'linkedin' in platforms, f"LinkedIn not found. Platforms: {platforms}"
        print("PASS: LinkedIn channel extracted")
    
    def test_social_channels_have_valid_urls(self):
        """Verify social channel URLs are valid"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        social = data.get('step2', {}).get('channels', {}).get('social', [])
        
        for channel in social:
            url = channel.get('url', '')
            assert url.startswith('https://'), f"Invalid URL for {channel.get('platform')}: {url}"
            assert channel.get('handle'), f"Missing handle for {channel.get('platform')}"
        
        print("PASS: All social channels have valid URLs and handles")


class TestMergeColorsFunction:
    """Test the _merge_colors function behavior indirectly via API output"""
    
    def test_colors_are_unique(self):
        """Verify no duplicate colors in merged output"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        hexes = [c.get('hex', '').lower() for c in colors]
        
        assert len(hexes) == len(set(hexes)), f"Duplicate colors found: {hexes}"
        print("PASS: All colors are unique")
    
    def test_colors_have_diverse_hues(self):
        """Verify colors represent diverse hues (not all similar)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        
        def get_hue_bucket(hex_val):
            """Get rough hue bucket (0-5) from hex color"""
            h = hex_val.lstrip('#').lower()
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            if max_c == min_c:
                return 6  # Gray
            if r == max_c:
                return 0 if g >= b else 5  # Red/Magenta
            elif g == max_c:
                return 1 if b <= r else 2  # Yellow/Green
            else:
                return 3 if g <= r else 4  # Blue/Cyan
        
        hue_buckets = set(get_hue_bucket(c.get('hex', '')) for c in colors)
        # Should have at least 2 different hue groups
        assert len(hue_buckets) >= 2, f"Not enough hue diversity. Hue buckets: {hue_buckets}"
        
        print(f"PASS: Colors have {len(hue_buckets)} different hue categories")


class TestBrandIdentityModule:
    """Unit tests for brand_identity.py functions"""
    
    def test_screenshot_has_color_function_exists(self):
        """Verify _screenshot_has_color function exists in brand_identity.py"""
        from brand_identity import _screenshot_has_color
        assert callable(_screenshot_has_color)
        print("PASS: _screenshot_has_color function exists")
    
    def test_colors_from_context_function_exists(self):
        """Verify _colors_from_context function exists"""
        from brand_identity import _colors_from_context
        assert callable(_colors_from_context)
        print("PASS: _colors_from_context function exists")
    
    def test_vision_via_gemini_function_exists(self):
        """Verify _vision_via_gemini function exists"""
        from brand_identity import _vision_via_gemini
        assert callable(_vision_via_gemini)
        print("PASS: _vision_via_gemini function exists")
    
    def test_vision_via_emergent_function_exists(self):
        """Verify _vision_via_emergent function exists"""
        from brand_identity import _vision_via_emergent
        assert callable(_vision_via_emergent)
        print("PASS: _vision_via_emergent function exists")
    
    def test_parse_color_response_function_exists(self):
        """Verify _parse_color_response function exists"""
        from brand_identity import _parse_color_response
        assert callable(_parse_color_response)
        print("PASS: _parse_color_response function exists")
    
    def test_wix_platform_colors_list_exists(self):
        """Verify WIX_PLATFORM_COLORS filter list is defined"""
        from brand_identity import BrandIdentityExtractor
        assert hasattr(BrandIdentityExtractor, 'WIX_PLATFORM_COLORS')
        wix_colors = BrandIdentityExtractor.WIX_PLATFORM_COLORS
        assert '#116dff' in wix_colors, "Expected #116dff in WIX_PLATFORM_COLORS"
        assert '#7fccf7' in wix_colors, "Expected #7fccf7 in WIX_PLATFORM_COLORS"
        assert '#3899ec' in wix_colors, "Expected #3899ec in WIX_PLATFORM_COLORS"
        print(f"PASS: WIX_PLATFORM_COLORS has {len(wix_colors)} colors")
    
    def test_parse_color_response_with_json(self):
        """Test _parse_color_response parses JSON correctly"""
        from brand_identity import _parse_color_response
        
        # Test valid JSON
        response = '[{"hex": "#5a48f5", "role": "primary"}, {"hex": "#d49341", "role": "secondary"}]'
        result = _parse_color_response(response)
        
        assert len(result) == 2
        assert result[0]['hex'] == '#5a48f5'
        assert result[0]['role'] == 'primary'
        print("PASS: _parse_color_response parses JSON correctly")
    
    def test_parse_color_response_with_markdown(self):
        """Test _parse_color_response handles markdown code blocks"""
        from brand_identity import _parse_color_response
        
        # Test JSON in markdown code block
        response = '```json\n[{"hex": "#ff0000", "role": "primary"}]\n```'
        result = _parse_color_response(response)
        
        assert len(result) == 1
        assert result[0]['hex'] == '#ff0000'
        print("PASS: _parse_color_response handles markdown code blocks")


class TestServerMergeColors:
    """Test _merge_colors function in server.py"""
    
    def test_merge_colors_filters_skip_colors(self):
        """Verify _merge_colors filters white/black/generic colors"""
        # We test indirectly via the API output
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        colors = data.get('step2', {}).get('identity', {}).get('colors', [])
        hexes = {c.get('hex', '').lower() for c in colors}
        
        # These should never appear in output
        bad_colors = {'#ffffff', '#000000', '#f5f5f5', '#fafafa', '#333333', '#111111'}
        found_bad = hexes & bad_colors
        
        assert len(found_bad) == 0, f"Bad colors found in output: {found_bad}"
        print("PASS: _merge_colors correctly filters skip colors")


class TestEndToEndPackContent:
    """End-to-end tests for the full pack content"""
    
    def test_pack_has_brand_name(self):
        """Verify pack has brand name"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        brand_name = data.get('step2', {}).get('brand_summary', {}).get('name')
        assert brand_name and brand_name != 'unknown', f"Invalid brand name: {brand_name}"
        print(f"PASS: Brand name is '{brand_name}'")
    
    def test_pack_has_fonts(self):
        """Verify pack has fonts extracted"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        fonts = data.get('step2', {}).get('identity', {}).get('fonts', [])
        assert len(fonts) >= 1, "No fonts extracted"
        print(f"PASS: {len(fonts)} fonts extracted")
    
    def test_pack_has_screenshot(self):
        """Verify pack has screenshot (used for vision extraction)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
        data = response.json()
        
        screenshot = data.get('screenshot', '')
        assert screenshot and len(screenshot) > 100, "No screenshot captured"
        assert screenshot.startswith('data:image/'), "Invalid screenshot format"
        print(f"PASS: Screenshot captured ({len(screenshot)} chars)")


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
