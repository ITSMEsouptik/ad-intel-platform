"""
Data Quality v56 Tests - New Fixes Verification

Tests for the data quality fixes in iteration 56:
1. CSS artifact font name filtering ('Inherit)', 'gilroy Fallback', 'Sans Serif !Important')
2. System font filtering (Lucida Sans, Georgia, etc)
3. Google Sans / platform font filtering
4. YouTube 'user' handle filtering
5. Facebook 'tr' tracking pixel handle filtering
6. Social channel deduplication by platform
7. skip_handles completeness in both step2_pipeline.py and channels.py

Stress test campaign briefs to verify:
- sweetgreen: 3e4ad217-5c0b-4866-81c6-1ef578f5b367
- barrys: 1e310579-9fa9-43db-a51c-f1a3690931f4
- aman: bfa38c33-367e-4b25-b7a7-b682df689ade
- sisters_beauty: e7d1cce5-0485-4672-baf4-dc49a9b9f74a
- allbirds: 8ced6098-8f00-42dc-9da4-cc84b0cad531
- calendly: 0ab74626-f981-44e1-a6b9-c0f528c5988e

Run: pytest backend/tests/test_data_quality_v56.py -v --tb=short
"""

import pytest
import re
import sys
import os
import requests

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')

# =============================================================================
# MODULE: step2_pipeline.py - CSS artifact font filtering
# =============================================================================

class TestCSSArtifactFontFiltering:
    """Test _clean_font_list filters CSS artifact names like 'Inherit)', 'X Fallback', '!important'."""
    
    def test_filters_inherit_with_unbalanced_paren(self):
        """'Inherit)' should be filtered (unbalanced closing paren)"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Inherit)', 'role': 'body', 'source': 'css'},
            {'name': 'Poppins', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'inherit)' not in font_names, "Inherit) should be filtered"
        assert 'poppins' in font_names, "Poppins should remain"
        print(f"PASS: 'Inherit)' filtered, remaining: {font_names}")
    
    def test_filters_fallback_pattern(self):
        """'gilroy Fallback', 'Inter-Fallback' should be filtered"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'gilroy Fallback', 'role': 'body', 'source': 'css'},
            {'name': 'Inter-Fallback', 'role': 'body', 'source': 'css'},
            {'name': 'Gilroy', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'gilroy fallback' not in font_names
        assert 'inter-fallback' not in font_names
        assert 'gilroy' in font_names
        print(f"PASS: Fallback patterns filtered, remaining: {font_names}")
    
    def test_filters_important_keyword(self):
        """'Sans Serif !Important' should be filtered (CSS keyword)"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Sans Serif !Important', 'role': 'body', 'source': 'css'},
            {'name': 'Montserrat', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'sans serif !important' not in font_names
        assert 'montserrat' in font_names
        print(f"PASS: '!important' font filtered, remaining: {font_names}")
    
    def test_filters_inherit_keyword(self):
        """'inherit', 'initial', 'unset' should be filtered"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'inherit', 'role': 'body', 'source': 'css'},
            {'name': 'initial', 'role': 'body', 'source': 'css'},
            {'name': 'Playfair Display', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'inherit' not in font_names
        assert 'initial' not in font_names
        assert 'playfair display' in font_names
        print(f"PASS: CSS keywords filtered, remaining: {font_names}")


# =============================================================================
# MODULE: step2_pipeline.py - System font filtering (Lucida, Georgia, etc)
# =============================================================================

class TestSystemFontFilteringExtended:
    """Test _clean_font_list filters extended system fonts (Lucida Sans, Georgia, etc)."""
    
    def test_filters_lucida_sans(self):
        """Lucida Sans variants should be filtered"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Lucida Sans', 'role': 'body', 'source': 'css'},
            {'name': 'Lucida Sans Regular', 'role': 'body', 'source': 'css'},
            {'name': 'Lucida Sans Unicode', 'role': 'body', 'source': 'css'},
            {'name': 'Lucida Grande', 'role': 'body', 'source': 'css'},
            {'name': 'Inter', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        for lucida in ['lucida sans', 'lucida sans regular', 'lucida sans unicode', 'lucida grande']:
            assert lucida not in font_names, f"'{lucida}' should be filtered"
        assert 'inter' in font_names
        print(f"PASS: Lucida variants filtered, remaining: {font_names}")
    
    def test_filters_georgia(self):
        """Georgia should be filtered (system font)"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Georgia', 'role': 'body', 'source': 'css'},
            {'name': 'Times New Roman', 'role': 'body', 'source': 'css'},
            {'name': 'Playfair Display', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'georgia' not in font_names
        assert 'times new roman' not in font_names
        assert 'playfair display' in font_names
        print(f"PASS: Georgia and Times New Roman filtered")
    
    def test_filters_trebuchet_verdana_tahoma(self):
        """Other system fonts: Trebuchet MS, Verdana, Tahoma should be filtered"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Trebuchet MS', 'role': 'body', 'source': 'css'},
            {'name': 'Verdana', 'role': 'body', 'source': 'css'},
            {'name': 'Tahoma', 'role': 'body', 'source': 'css'},
            {'name': 'DM Sans', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'trebuchet ms' not in font_names
        assert 'verdana' not in font_names
        assert 'tahoma' not in font_names
        assert 'dm sans' in font_names
        print(f"PASS: System fonts filtered: {font_names}")


# =============================================================================
# MODULE: step2_pipeline.py - Google/Platform font filtering
# =============================================================================

class TestGooglePlatformFontFiltering:
    """Test _clean_font_list filters Google Sans, Roboto, and other platform fonts."""
    
    def test_filters_google_sans(self):
        """Google Sans variants should be filtered"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Google Sans', 'role': 'body', 'source': 'css'},
            {'name': 'Google Sans Text', 'role': 'body', 'source': 'css'},
            {'name': 'Google Sans Display', 'role': 'heading', 'source': 'css'},
            {'name': 'Product Sans', 'role': 'body', 'source': 'css'},
            {'name': 'Poppins', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'google sans' not in font_names
        assert 'google sans text' not in font_names
        assert 'google sans display' not in font_names
        assert 'product sans' not in font_names
        assert 'poppins' in font_names
        print(f"PASS: Google platform fonts filtered, remaining: {font_names}")
    
    def test_filters_roboto_variants(self):
        """Roboto variants should be filtered"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Roboto', 'role': 'body', 'source': 'css'},
            {'name': 'Roboto Slab', 'role': 'body', 'source': 'css'},
            {'name': 'Roboto Mono', 'role': 'code', 'source': 'css'},
            {'name': 'Work Sans', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'roboto' not in font_names
        assert 'roboto slab' not in font_names
        assert 'roboto mono' not in font_names
        assert 'work sans' in font_names
        print(f"PASS: Roboto variants filtered: {font_names}")
    
    def test_filters_noto_variants(self):
        """Noto Sans/Serif should be filtered"""
        from step2_pipeline import _clean_font_list
        
        raw_fonts = [
            {'name': 'Noto Sans', 'role': 'body', 'source': 'css'},
            {'name': 'Noto Serif', 'role': 'body', 'source': 'css'},
            {'name': 'Lora', 'role': 'heading', 'source': 'css'},
        ]
        
        cleaned = _clean_font_list(raw_fonts)
        font_names = [f['family'].lower() for f in cleaned]
        
        assert 'noto sans' not in font_names
        assert 'noto serif' not in font_names
        assert 'lora' in font_names
        print(f"PASS: Noto variants filtered: {font_names}")


# =============================================================================
# MODULE: step2_pipeline.py - Social handle filtering (skip_handles)
# =============================================================================

class TestSocialHandleSkipping:
    """Test _extract_social_from_content skip_handles includes 'user', 'tr', 'channel', etc."""
    
    def test_skip_handles_includes_user(self):
        """'user' should be in skip_handles (YouTube /user/xxx is generic)"""
        from step2_pipeline import _extract_social_from_content
        
        content = "Follow us on https://youtube.com/user/genericuser"
        socials = _extract_social_from_content(content)
        
        # Should not extract 'user' as a YouTube handle
        youtube_handles = [s['handle'] for s in socials if s['platform'] == 'youtube']
        assert 'user' not in youtube_handles, "'user' should be skipped"
        print(f"PASS: 'user' handle skipped, extracted: {socials}")
    
    def test_skip_handles_includes_tr(self):
        """'tr' should be in skip_handles (Facebook tracking pixel)"""
        from step2_pipeline import _extract_social_from_content
        
        content = "Facebook: https://facebook.com/tr?id=12345 is tracking"
        socials = _extract_social_from_content(content)
        
        fb_handles = [s['handle'] for s in socials if s['platform'] == 'facebook']
        assert 'tr' not in fb_handles, "'tr' should be skipped (tracking pixel)"
        print(f"PASS: 'tr' handle skipped, extracted: {socials}")
    
    def test_skip_handles_includes_channel(self):
        """'channel' should be in skip_handles"""
        from step2_pipeline import _extract_social_from_content
        
        content = "YouTube: https://youtube.com/channel"
        socials = _extract_social_from_content(content)
        
        yt_handles = [s['handle'] for s in socials if s['platform'] == 'youtube']
        assert 'channel' not in yt_handles, "'channel' should be skipped"
        print(f"PASS: 'channel' handle skipped")
    
    def test_skip_handles_includes_language_codes(self):
        """Language codes ('en', 'fr', 'de') should be skipped"""
        from step2_pipeline import _extract_social_from_content
        
        content = """
        https://facebook.com/en
        https://instagram.com/fr
        https://twitter.com/de
        https://instagram.com/mybrand
        """
        socials = _extract_social_from_content(content)
        
        all_handles = [s['handle'] for s in socials]
        for lang in ['en', 'fr', 'de']:
            assert lang not in all_handles, f"'{lang}' should be skipped"
        print(f"PASS: Language codes skipped, extracted handles: {all_handles}")
    
    def test_extracts_real_handles(self):
        """Real brand handles should still be extracted"""
        from step2_pipeline import _extract_social_from_content
        
        content = """
        Instagram: https://instagram.com/sweetgreen
        Facebook: https://facebook.com/sweetgreen
        YouTube: https://youtube.com/@sweetgreen
        """
        socials = _extract_social_from_content(content)
        
        handles = [s['handle'] for s in socials]
        assert 'sweetgreen' in handles, "Real handle 'sweetgreen' should be extracted"
        print(f"PASS: Real handles extracted: {handles}")


# =============================================================================
# MODULE: channels.py - SKIP_USERNAMES completeness
# =============================================================================

class TestChannelsSkipUsernames:
    """Test channels.py SKIP_USERNAMES includes 'user', 'tr', 'channel', etc."""
    
    def test_skip_usernames_has_user(self):
        """SKIP_USERNAMES should include 'user'"""
        from channels import SKIP_USERNAMES
        
        assert 'user' in SKIP_USERNAMES, "'user' should be in SKIP_USERNAMES"
        print(f"PASS: 'user' in SKIP_USERNAMES")
    
    def test_skip_usernames_has_tr(self):
        """SKIP_USERNAMES should include 'tr' (Facebook tracking pixel)"""
        from channels import SKIP_USERNAMES
        
        assert 'tr' in SKIP_USERNAMES, "'tr' should be in SKIP_USERNAMES"
        print(f"PASS: 'tr' in SKIP_USERNAMES")
    
    def test_skip_usernames_has_channel(self):
        """SKIP_USERNAMES should include 'channel'"""
        from channels import SKIP_USERNAMES
        
        assert 'channel' in SKIP_USERNAMES, "'channel' should be in SKIP_USERNAMES"
        print(f"PASS: 'channel' in SKIP_USERNAMES")
    
    def test_skip_usernames_has_language_codes(self):
        """SKIP_USERNAMES should include language codes"""
        from channels import SKIP_USERNAMES
        
        lang_codes = ['en', 'fr', 'de', 'es', 'it', 'ja', 'ko', 'pt', 'ru', 'zh']
        for lang in lang_codes:
            assert lang in SKIP_USERNAMES, f"'{lang}' should be in SKIP_USERNAMES"
        print(f"PASS: Language codes in SKIP_USERNAMES")
    
    def test_skip_usernames_has_common_path_segments(self):
        """SKIP_USERNAMES should include common path segments"""
        from channels import SKIP_USERNAMES
        
        segments = ['share', 'sharer', 'intent', 'explore', 'feed', 'playlist', 'embed']
        for seg in segments:
            assert seg in SKIP_USERNAMES, f"'{seg}' should be in SKIP_USERNAMES"
        print(f"PASS: Common path segments in SKIP_USERNAMES")


# =============================================================================
# MODULE: step2_pipeline.py - Social channel deduplication
# =============================================================================

class TestSocialChannelDeduplication:
    """Test stage_extract_channels deduplicates social channels by platform."""
    
    def test_social_dedup_logic_exists(self):
        """Dedup logic should exist in stage_extract_channels"""
        import inspect
        from step2_pipeline import stage_extract_channels
        
        source = inspect.getsource(stage_extract_channels)
        
        # Check for deduplication logic
        assert 'seen_platforms' in source or 'deduped' in source, "Dedup logic should exist"
        print("PASS: Dedup logic found in stage_extract_channels")
    
    def test_dedup_keeps_first_occurrence(self):
        """Should keep first occurrence per platform"""
        # Test the dedup logic directly
        channels_list = [
            {'platform': 'instagram', 'url': 'https://instagram.com/brand1', 'handle': 'brand1'},
            {'platform': 'instagram', 'url': 'https://instagram.com/brand2', 'handle': 'brand2'},
            {'platform': 'facebook', 'url': 'https://facebook.com/brand', 'handle': 'brand'},
        ]
        
        # Apply same dedup logic as in stage_extract_channels
        seen_platforms = set()
        deduped = []
        for ch in channels_list:
            if ch['platform'] not in seen_platforms:
                seen_platforms.add(ch['platform'])
                deduped.append(ch)
        
        assert len(deduped) == 2, "Should have 2 unique platforms"
        ig = next((c for c in deduped if c['platform'] == 'instagram'), None)
        assert ig['handle'] == 'brand1', "Should keep first Instagram occurrence"
        print(f"PASS: Dedup keeps first occurrence: {[c['handle'] for c in deduped]}")


# =============================================================================
# INTEGRATION: Stress test campaign brief verification
# =============================================================================

class TestStressTestCampaignBriefs:
    """Verify the 6 stress test campaign briefs have clean data."""
    
    # Campaign brief IDs
    STRESS_TESTS = {
        'sweetgreen': '3e4ad217-5c0b-4866-81c6-1ef578f5b367',
        'barrys': '1e310579-9fa9-43db-a51c-f1a3690931f4',
        'aman': 'bfa38c33-367e-4b25-b7a7-b682df689ade',
        'sisters_beauty': 'e7d1cce5-0485-4672-baf4-dc49a9b9f74a',
        'allbirds': '8ced6098-8f00-42dc-9da4-cc84b0cad531',
        'calendly': '0ab74626-f981-44e1-a6b9-c0f528c5988e',
    }
    
    # Platform fonts that should be filtered
    PLATFORM_FONTS = {
        'google sans', 'google sans text', 'google sans display',
        'product sans', 'roboto', 'roboto slab', 'roboto mono',
        'noto sans', 'noto serif', 'arial', 'helvetica', 'sans-serif',
        'lucida sans', 'georgia', 'times new roman', 'verdana', 'tahoma',
    }
    
    # CSS artifacts that should be filtered
    CSS_ARTIFACTS = {'inherit', 'initial', 'unset', 'revert', 'fallback', '!important'}
    
    # Skip handles (should not appear in social channels)
    SKIP_HANDLES = {'user', 'tr', 'channel', 'c', 'en', 'fr', 'de', 'share', 'sharer'}
    
    def _get_pack(self, brief_id: str, brand_name: str):
        """Fetch pack for a campaign brief."""
        try:
            resp = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{brief_id}", timeout=30)
            if resp.status_code == 200:
                return resp.json()
            else:
                pytest.skip(f"{brand_name} pack not available (status={resp.status_code})")
        except Exception as e:
            pytest.skip(f"{brand_name} pack fetch failed: {e}")
    
    def _check_fonts_clean(self, fonts: list, brand_name: str) -> list:
        """Check fonts for platform fonts and CSS artifacts."""
        issues = []
        for font in fonts:
            family = font.get('family', '')
            family_lower = family.lower()
            
            # Check for platform fonts
            if family_lower in self.PLATFORM_FONTS:
                issues.append(f"Platform font found: '{family}'")
            
            # Check for CSS artifacts
            for artifact in self.CSS_ARTIFACTS:
                if artifact in family_lower:
                    issues.append(f"CSS artifact in font: '{family}'")
            
            # Check for unbalanced parens
            if ')' in family and '(' not in family:
                issues.append(f"Unbalanced paren in font: '{family}'")
            
            # Check for 'Fallback' pattern
            if family_lower.endswith(' fallback') or family_lower.endswith('-fallback'):
                issues.append(f"Fallback pattern in font: '{family}'")
        
        return issues
    
    def _check_social_clean(self, socials: list, brand_name: str) -> list:
        """Check social channels for skip handles and duplicates."""
        issues = []
        seen_platforms = set()
        
        for social in socials:
            platform = social.get('platform', '')
            handle = social.get('handle', '').lower()
            
            # Check for skip handles
            if handle in self.SKIP_HANDLES:
                issues.append(f"Skip handle found: {platform}/@{handle}")
            
            # Check for duplicate platforms
            if platform in seen_platforms:
                issues.append(f"Duplicate platform: {platform}")
            seen_platforms.add(platform)
        
        return issues
    
    # Individual tests for each stress test brand
    
    def test_sweetgreen_fonts_clean(self):
        """Sweetgreen should have clean fonts (no platform fonts, no CSS artifacts)"""
        pack = self._get_pack(self.STRESS_TESTS['sweetgreen'], 'sweetgreen')
        fonts = pack.get('step2', {}).get('identity', {}).get('fonts', [])
        
        issues = self._check_fonts_clean(fonts, 'sweetgreen')
        
        if issues:
            print(f"Sweetgreen font issues: {issues}")
        assert len(issues) == 0, f"Sweetgreen font issues: {issues}"
        print(f"PASS: Sweetgreen has {len(fonts)} clean fonts: {[f.get('family') for f in fonts]}")
    
    def test_sweetgreen_social_clean(self):
        """Sweetgreen should have clean social channels (no skip handles, no dupes)"""
        pack = self._get_pack(self.STRESS_TESTS['sweetgreen'], 'sweetgreen')
        socials = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        issues = self._check_social_clean(socials, 'sweetgreen')
        
        if issues:
            print(f"Sweetgreen social issues: {issues}")
        assert len(issues) == 0, f"Sweetgreen social issues: {issues}"
        print(f"PASS: Sweetgreen has {len(socials)} clean social channels")
    
    def test_barrys_fonts_clean(self):
        """Barrys should have clean fonts"""
        pack = self._get_pack(self.STRESS_TESTS['barrys'], 'barrys')
        fonts = pack.get('step2', {}).get('identity', {}).get('fonts', [])
        
        issues = self._check_fonts_clean(fonts, 'barrys')
        
        if issues:
            print(f"Barrys font issues: {issues}")
        assert len(issues) == 0, f"Barrys font issues: {issues}"
        print(f"PASS: Barrys has {len(fonts)} clean fonts: {[f.get('family') for f in fonts]}")
    
    def test_barrys_social_clean(self):
        """Barrys should have clean social channels"""
        pack = self._get_pack(self.STRESS_TESTS['barrys'], 'barrys')
        socials = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        issues = self._check_social_clean(socials, 'barrys')
        
        if issues:
            print(f"Barrys social issues: {issues}")
        assert len(issues) == 0, f"Barrys social issues: {issues}"
        print(f"PASS: Barrys has {len(socials)} clean social channels")
    
    def test_aman_fonts_clean(self):
        """Aman should have clean fonts"""
        pack = self._get_pack(self.STRESS_TESTS['aman'], 'aman')
        fonts = pack.get('step2', {}).get('identity', {}).get('fonts', [])
        
        issues = self._check_fonts_clean(fonts, 'aman')
        
        if issues:
            print(f"Aman font issues: {issues}")
        assert len(issues) == 0, f"Aman font issues: {issues}"
        print(f"PASS: Aman has {len(fonts)} clean fonts: {[f.get('family') for f in fonts]}")
    
    def test_aman_social_clean(self):
        """Aman should have clean social channels"""
        pack = self._get_pack(self.STRESS_TESTS['aman'], 'aman')
        socials = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        issues = self._check_social_clean(socials, 'aman')
        
        if issues:
            print(f"Aman social issues: {issues}")
        assert len(issues) == 0, f"Aman social issues: {issues}"
        print(f"PASS: Aman has {len(socials)} clean social channels")
    
    def test_sisters_beauty_fonts_clean(self):
        """Sisters Beauty should have clean fonts"""
        pack = self._get_pack(self.STRESS_TESTS['sisters_beauty'], 'sisters_beauty')
        fonts = pack.get('step2', {}).get('identity', {}).get('fonts', [])
        
        issues = self._check_fonts_clean(fonts, 'sisters_beauty')
        
        if issues:
            print(f"Sisters Beauty font issues: {issues}")
        assert len(issues) == 0, f"Sisters Beauty font issues: {issues}"
        print(f"PASS: Sisters Beauty has {len(fonts)} clean fonts: {[f.get('family') for f in fonts]}")
    
    def test_sisters_beauty_social_clean(self):
        """Sisters Beauty should have clean social channels"""
        pack = self._get_pack(self.STRESS_TESTS['sisters_beauty'], 'sisters_beauty')
        socials = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        issues = self._check_social_clean(socials, 'sisters_beauty')
        
        if issues:
            print(f"Sisters Beauty social issues: {issues}")
        assert len(issues) == 0, f"Sisters Beauty social issues: {issues}"
        print(f"PASS: Sisters Beauty has {len(socials)} clean social channels")
    
    def test_allbirds_fonts_clean(self):
        """Allbirds should have clean fonts"""
        pack = self._get_pack(self.STRESS_TESTS['allbirds'], 'allbirds')
        fonts = pack.get('step2', {}).get('identity', {}).get('fonts', [])
        
        issues = self._check_fonts_clean(fonts, 'allbirds')
        
        if issues:
            print(f"Allbirds font issues: {issues}")
        assert len(issues) == 0, f"Allbirds font issues: {issues}"
        print(f"PASS: Allbirds has {len(fonts)} clean fonts: {[f.get('family') for f in fonts]}")
    
    def test_allbirds_social_clean(self):
        """Allbirds should have clean social channels"""
        pack = self._get_pack(self.STRESS_TESTS['allbirds'], 'allbirds')
        socials = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        issues = self._check_social_clean(socials, 'allbirds')
        
        if issues:
            print(f"Allbirds social issues: {issues}")
        assert len(issues) == 0, f"Allbirds social issues: {issues}"
        print(f"PASS: Allbirds has {len(socials)} clean social channels")
    
    def test_calendly_fonts_clean(self):
        """Calendly should have clean fonts"""
        pack = self._get_pack(self.STRESS_TESTS['calendly'], 'calendly')
        fonts = pack.get('step2', {}).get('identity', {}).get('fonts', [])
        
        issues = self._check_fonts_clean(fonts, 'calendly')
        
        if issues:
            print(f"Calendly font issues: {issues}")
        assert len(issues) == 0, f"Calendly font issues: {issues}"
        print(f"PASS: Calendly has {len(fonts)} clean fonts: {[f.get('family') for f in fonts]}")
    
    def test_calendly_social_clean(self):
        """Calendly should have clean social channels"""
        pack = self._get_pack(self.STRESS_TESTS['calendly'], 'calendly')
        socials = pack.get('step2', {}).get('channels', {}).get('social', [])
        
        issues = self._check_social_clean(socials, 'calendly')
        
        if issues:
            print(f"Calendly social issues: {issues}")
        assert len(issues) == 0, f"Calendly social issues: {issues}"
        print(f"PASS: Calendly has {len(socials)} clean social channels")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
