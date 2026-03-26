"""
Test color extraction improvements (Iteration 52)

Tests the complete rewrite of color extraction:
1. Colors extracted from FULL HTML before 100K truncation via crawler._extract_html_colors
2. Scoring prioritizes inline styles (10pts) and SVG fills (5pts) over CSS variable definitions (1pt)
3. Accent clusters with representative score < 3 are excluded (filters Wix auto-generated colors)
4. Social channels via Jina Reader

Ground truth for example-brand.co:
- #e21c21 (red) - primary
- #ffffff (white) - bg
- #000000 (black) - text
- ~#e8e6e6 (light gray, within dist 15) - bg
"""

import pytest
import requests
import os
import math
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Brief ID for example-brand.co test
TEST_BRIEF_ID = "cdb0dda5-6384-4139-9348-b28f53017a55"

# Expected colors for example-brand.co
EXPECTED_COLORS = {
    'red': '#e21c21',
    'white': '#ffffff',
    'black': '#000000',
    'light_gray': '#e8e6e6'  # Expected to find close match within dist 15
}

# Wix platform colors that should NOT appear
WIX_PLATFORM_COLORS = ['#116dff', '#7fccf7', '#3899ec']


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex to RGB tuple"""
    hex_color = hex_color.lstrip('#').lower()
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def color_distance(c1: str, c2: str) -> float:
    """Calculate Euclidean distance between two hex colors"""
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return math.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2)


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def pack_data(api_client):
    """Get pack data for test brief"""
    response = api_client.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{TEST_BRIEF_ID}")
    assert response.status_code == 200, f"Failed to get pack: {response.status_code}"
    return response.json()


class TestColorExtraction:
    """Tests for color extraction from example-brand.co"""
    
    def test_pack_exists_and_success(self, pack_data):
        """Test pack exists and has success status"""
        assert pack_data.get('status') == 'success', f"Pack status: {pack_data.get('status')}"
        print(f"PASS: Pack status is 'success'")
    
    def test_has_colors(self, pack_data):
        """Test pack has colors extracted"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        assert len(colors) >= 3, f"Expected at least 3 colors, got {len(colors)}"
        print(f"PASS: Found {len(colors)} colors")
    
    def test_contains_red_e21c21(self, pack_data):
        """Test pack contains #e21c21 (red) - the primary brand color"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        hex_values = [c.get('hex', '').lower() for c in colors]
        
        assert EXPECTED_COLORS['red'].lower() in hex_values, \
            f"Expected {EXPECTED_COLORS['red']} not found in {hex_values}"
        print(f"PASS: Found red brand color {EXPECTED_COLORS['red']}")
    
    def test_contains_white(self, pack_data):
        """Test pack contains #ffffff (white) for bg"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        hex_values = [c.get('hex', '').lower() for c in colors]
        
        assert EXPECTED_COLORS['white'].lower() in hex_values, \
            f"Expected {EXPECTED_COLORS['white']} not found in {hex_values}"
        print(f"PASS: Found white {EXPECTED_COLORS['white']}")
    
    def test_contains_black(self, pack_data):
        """Test pack contains #000000 (black) for text"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        hex_values = [c.get('hex', '').lower() for c in colors]
        
        assert EXPECTED_COLORS['black'].lower() in hex_values, \
            f"Expected {EXPECTED_COLORS['black']} not found in {hex_values}"
        print(f"PASS: Found black {EXPECTED_COLORS['black']}")
    
    def test_contains_light_gray_close_match(self, pack_data):
        """Test pack contains color close to #e8e6e6 (light gray) within dist 15"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        expected = EXPECTED_COLORS['light_gray']
        
        close_match = None
        for c in colors:
            hex_val = c.get('hex', '').lower()
            dist = color_distance(hex_val, expected)
            if dist <= 15:
                close_match = (hex_val, dist)
                break
        
        assert close_match is not None, \
            f"No color within dist 15 of {expected}. Colors: {[c.get('hex') for c in colors]}"
        print(f"PASS: Found {close_match[0]} within dist {close_match[1]:.1f} of {expected}")
    
    def test_no_wix_platform_colors(self, pack_data):
        """Test that no Wix platform colors (#116dff, #7fccf7, #3899ec) appear"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        hex_values = [c.get('hex', '').lower() for c in colors]
        
        for wix_color in WIX_PLATFORM_COLORS:
            assert wix_color.lower() not in hex_values, \
                f"Wix platform color {wix_color} should not appear in brand colors"
        print(f"PASS: No Wix platform colors found")
    
    def test_colors_have_valid_structure(self, pack_data):
        """Test colors have hex and role fields"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        
        for c in colors:
            assert 'hex' in c, "Color missing 'hex' field"
            assert 'role' in c, "Color missing 'role' field"
            assert c['hex'].startswith('#'), f"Invalid hex format: {c['hex']}"
        print(f"PASS: All colors have valid structure")


class TestSocialChannels:
    """Tests for social channel extraction via Jina Reader"""
    
    def test_has_social_channels(self, pack_data):
        """Test pack has social channels extracted"""
        channels = pack_data.get('step2', {}).get('channels', {}).get('social', [])
        assert len(channels) >= 1, "Expected at least 1 social channel"
        print(f"PASS: Found {len(channels)} social channels")
    
    def test_has_instagram(self, pack_data):
        """Test pack has Instagram channel"""
        channels = pack_data.get('step2', {}).get('channels', {}).get('social', [])
        platforms = [c.get('platform', '').lower() for c in channels]
        
        assert 'instagram' in platforms, f"Instagram not found in {platforms}"
        print("PASS: Found Instagram channel")
    
    def test_has_facebook(self, pack_data):
        """Test pack has Facebook channel"""
        channels = pack_data.get('step2', {}).get('channels', {}).get('social', [])
        platforms = [c.get('platform', '').lower() for c in channels]
        
        assert 'facebook' in platforms, f"Facebook not found in {platforms}"
        print("PASS: Found Facebook channel")
    
    def test_has_linkedin(self, pack_data):
        """Test pack has LinkedIn channel"""
        channels = pack_data.get('step2', {}).get('channels', {}).get('social', [])
        platforms = [c.get('platform', '').lower() for c in channels]
        
        assert 'linkedin' in platforms, f"LinkedIn not found in {platforms}"
        print("PASS: Found LinkedIn channel")
    
    def test_social_channels_have_valid_urls(self, pack_data):
        """Test social channels have valid URLs and handles"""
        channels = pack_data.get('step2', {}).get('channels', {}).get('social', [])
        
        for ch in channels:
            assert 'platform' in ch, "Channel missing 'platform' field"
            assert 'url' in ch, "Channel missing 'url' field"
            assert ch['url'].startswith('http'), f"Invalid URL: {ch['url']}"
        print("PASS: All social channels have valid URLs")


class TestBrandIdentityExtractor:
    """Tests for the brand_identity.py module functions"""
    
    def test_extract_brand_palette_function_exists(self):
        """Test _extract_brand_palette function exists"""
        import sys
        sys.path.insert(0, '/app/backend')
        from brand_identity import _extract_brand_palette
        assert callable(_extract_brand_palette)
        print("PASS: _extract_brand_palette function exists")
    
    def test_extract_brand_identity_accepts_html_colors(self):
        """Test extract_brand_identity accepts html_colors param"""
        import sys
        sys.path.insert(0, '/app/backend')
        from brand_identity import extract_brand_identity
        import inspect
        sig = inspect.signature(extract_brand_identity)
        params = list(sig.parameters.keys())
        assert 'html_colors' in params, f"html_colors param not found. Params: {params}"
        print("PASS: extract_brand_identity accepts html_colors param")
    
    def test_platform_colors_filtered(self):
        """Test PLATFORM_COLORS list contains expected Wix colors"""
        import sys
        sys.path.insert(0, '/app/backend')
        # Read the file to check PLATFORM_COLORS
        with open('/app/backend/brand_identity.py', 'r') as f:
            content = f.read()
        
        # Check that Wix colors are in the filter list
        for wix_color in ['116dff', '7fccf7', '3899ec']:
            assert wix_color in content, f"Wix color {wix_color} not in filter list"
        print("PASS: Wix platform colors in filter list")


class TestCrawlerHtmlColors:
    """Tests for crawler._extract_html_colors"""
    
    def test_extract_html_colors_function_exists(self):
        """Test _extract_html_colors method exists in WebCrawler"""
        import sys
        sys.path.insert(0, '/app/backend')
        from crawler import WebCrawler
        crawler = WebCrawler()
        assert hasattr(crawler, '_extract_html_colors'), "WebCrawler missing _extract_html_colors"
        print("PASS: WebCrawler._extract_html_colors exists")
    
    def test_page_data_has_html_colors_field(self):
        """Test PageData class has html_colors field"""
        import sys
        sys.path.insert(0, '/app/backend')
        from crawler import PageData
        page = PageData(url='https://example.com')
        assert hasattr(page, 'html_colors'), "PageData missing html_colors field"
        print("PASS: PageData has html_colors field")
    
    def test_extract_html_colors_extracts_inline_styles(self):
        """Test _extract_html_colors extracts colors from inline styles"""
        import sys
        sys.path.insert(0, '/app/backend')
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        test_html = '''
        <div style="color:#E21C21">Red text</div>
        <div style="background:#FFFFFF">White bg</div>
        <svg fill="#000000">Black fill</svg>
        '''
        
        colors = crawler._extract_html_colors(test_html)
        colors_lower = [c.lower() for c in colors]
        
        assert 'e21c21' in colors_lower, f"e21c21 not found in {colors_lower}"
        assert 'ffffff' in colors_lower or any('fff' in c for c in colors_lower), \
            f"ffffff not found in {colors_lower}"
        print(f"PASS: Extracted colors from inline styles: {colors}")


class TestEndToEnd:
    """End-to-end test of the complete flow"""
    
    def test_full_color_palette_for_example_brand(self, pack_data):
        """Test complete color palette matches ground truth"""
        colors = pack_data.get('step2', {}).get('identity', {}).get('colors', [])
        hex_values = [c.get('hex', '').lower() for c in colors]
        
        # Check all expected colors
        checks = {
            'red (#e21c21)': EXPECTED_COLORS['red'].lower() in hex_values,
            'white (#ffffff)': EXPECTED_COLORS['white'].lower() in hex_values,
            'black (#000000)': EXPECTED_COLORS['black'].lower() in hex_values,
            'light_gray (~#e8e6e6)': any(
                color_distance(h, EXPECTED_COLORS['light_gray']) <= 15 
                for h in hex_values
            )
        }
        
        failed = [k for k, v in checks.items() if not v]
        assert not failed, f"Missing colors: {failed}. Found: {hex_values}"
        
        # Check no Wix colors
        wix_found = [c for c in hex_values if c in [w.lower() for w in WIX_PLATFORM_COLORS]]
        assert not wix_found, f"Wix platform colors found: {wix_found}"
        
        print(f"PASS: Full color palette verified. Colors: {hex_values}")
    
    def test_full_social_channels_for_example_brand(self, pack_data):
        """Test all 3 social channels found for example-brand.co"""
        channels = pack_data.get('step2', {}).get('channels', {}).get('social', [])
        platforms = [c.get('platform', '').lower() for c in channels]
        
        expected = ['instagram', 'facebook', 'linkedin']
        missing = [p for p in expected if p not in platforms]
        
        assert not missing, f"Missing social channels: {missing}. Found: {platforms}"
        print(f"PASS: All 3 social channels verified: {platforms}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
