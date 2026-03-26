"""
Creative Analysis Layer - Backend API Tests
Tests: GET /api/research/{campaign_id}/creative-analysis/latest
       POST /api/research/{campaign_id}/creative-analysis/run
       GET /api/research/{campaign_id}/creative-analysis/history
       Data structure validation for ad_analyses, tiktok_analyses, pattern_summary
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_CAMPAIGN_ID = "75ae6fe7-1d1d-40a3-8bb3-a29ea8254bd3"


class TestCreativeAnalysisLatest:
    """Tests for GET /api/research/{campaign_id}/creative-analysis/latest"""

    def test_latest_returns_200(self):
        """GET /latest should return 200 for valid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /latest returned 200")

    def test_latest_has_data_true(self):
        """GET /latest should return has_data:true with existing data"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200
        data = response.json()
        assert data.get("has_data") is True, f"Expected has_data=true, got {data.get('has_data')}"
        print(f"✓ has_data is True")

    def test_latest_has_ad_analyses(self):
        """GET /latest should return ad_analyses array"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200
        data = response.json()
        latest = data.get("latest", {})
        ad_analyses = latest.get("ad_analyses", [])
        assert isinstance(ad_analyses, list), f"ad_analyses should be list, got {type(ad_analyses)}"
        print(f"✓ ad_analyses is list with {len(ad_analyses)} items")

    def test_latest_has_tiktok_analyses(self):
        """GET /latest should return tiktok_analyses array"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200
        data = response.json()
        latest = data.get("latest", {})
        tiktok_analyses = latest.get("tiktok_analyses", [])
        assert isinstance(tiktok_analyses, list), f"tiktok_analyses should be list, got {type(tiktok_analyses)}"
        print(f"✓ tiktok_analyses is list with {len(tiktok_analyses)} items")

    def test_latest_has_pattern_summary(self):
        """GET /latest should return pattern_summary object"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200
        data = response.json()
        latest = data.get("latest", {})
        pattern_summary = latest.get("pattern_summary", {})
        assert isinstance(pattern_summary, dict), f"pattern_summary should be dict, got {type(pattern_summary)}"
        print(f"✓ pattern_summary is dict")


class TestAdCreativeAnalysisStructure:
    """Tests for ad_analyses data structure"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Fetch data once for all tests in this class"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200
        self.data = response.json()
        self.ad_analyses = self.data.get("latest", {}).get("ad_analyses", [])

    def test_ad_has_core_hook_type(self):
        """Ad analysis should have core.hook_type field"""
        if not self.ad_analyses:
            pytest.skip("No ad analyses in data")
        
        # Find first ad with successful analysis (no error)
        for ad in self.ad_analyses:
            if not ad.get("error"):
                core = ad.get("core", {})
                hook_type = core.get("hook_type")
                assert hook_type is not None, f"core.hook_type should exist"
                print(f"✓ Ad has core.hook_type: '{hook_type}'")
                return
        pytest.skip("All ads have errors")

    def test_ad_has_core_hook_psychology(self):
        """Ad analysis should have core.hook_psychology field"""
        if not self.ad_analyses:
            pytest.skip("No ad analyses in data")
        
        for ad in self.ad_analyses:
            if not ad.get("error"):
                core = ad.get("core", {})
                hook_psychology = core.get("hook_psychology")
                assert hook_psychology is not None, f"core.hook_psychology should exist"
                print(f"✓ Ad has core.hook_psychology: '{hook_psychology[:50]}...'" if len(str(hook_psychology)) > 50 else f"✓ Ad has core.hook_psychology: '{hook_psychology}'")
                return
        pytest.skip("All ads have errors")

    def test_ad_has_core_scroll_stop_mechanism(self):
        """Ad analysis should have core.scroll_stop_mechanism field"""
        if not self.ad_analyses:
            pytest.skip("No ad analyses in data")
        
        for ad in self.ad_analyses:
            if not ad.get("error"):
                core = ad.get("core", {})
                scroll_stop = core.get("scroll_stop_mechanism")
                assert scroll_stop is not None, f"core.scroll_stop_mechanism should exist"
                print(f"✓ Ad has core.scroll_stop_mechanism: '{scroll_stop[:50]}...'" if len(str(scroll_stop)) > 50 else f"✓ Ad has core.scroll_stop_mechanism: '{scroll_stop}'")
                return
        pytest.skip("All ads have errors")

    def test_ad_has_core_replicable_framework(self):
        """Ad analysis should have core.replicable_framework field"""
        if not self.ad_analyses:
            pytest.skip("No ad analyses in data")
        
        for ad in self.ad_analyses:
            if not ad.get("error"):
                core = ad.get("core", {})
                framework = core.get("replicable_framework")
                assert framework is not None, f"core.replicable_framework should exist"
                print(f"✓ Ad has core.replicable_framework: '{framework[:50]}...'" if len(str(framework)) > 50 else f"✓ Ad has core.replicable_framework: '{framework}'")
                return
        pytest.skip("All ads have errors")

    def test_ad_has_core_key_insight(self):
        """Ad analysis should have core.key_insight field"""
        if not self.ad_analyses:
            pytest.skip("No ad analyses in data")
        
        for ad in self.ad_analyses:
            if not ad.get("error"):
                core = ad.get("core", {})
                key_insight = core.get("key_insight")
                assert key_insight is not None, f"core.key_insight should exist"
                print(f"✓ Ad has core.key_insight: '{key_insight[:50]}...'" if len(str(key_insight)) > 50 else f"✓ Ad has core.key_insight: '{key_insight}'")
                return
        pytest.skip("All ads have errors")


class TestTikTokAnalysisStructure:
    """Tests for tiktok_analyses data structure"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Fetch data once for all tests in this class"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200
        self.data = response.json()
        self.tiktok_analyses = self.data.get("latest", {}).get("tiktok_analyses", [])

    def test_tiktok_has_analysis_content_format(self):
        """TikTok analysis should have analysis.content_format field"""
        if not self.tiktok_analyses:
            pytest.skip("No TikTok analyses in data")
        
        for tt in self.tiktok_analyses:
            if not tt.get("error"):
                analysis = tt.get("analysis", {})
                content_format = analysis.get("content_format")
                assert content_format is not None, f"analysis.content_format should exist"
                print(f"✓ TikTok has analysis.content_format: '{content_format}'")
                return
        pytest.skip("All TikTok analyses have errors")

    def test_tiktok_has_analysis_hook_psychology(self):
        """TikTok analysis should have analysis.hook_psychology field"""
        if not self.tiktok_analyses:
            pytest.skip("No TikTok analyses in data")
        
        for tt in self.tiktok_analyses:
            if not tt.get("error"):
                analysis = tt.get("analysis", {})
                hook_psychology = analysis.get("hook_psychology")
                assert hook_psychology is not None, f"analysis.hook_psychology should exist"
                print(f"✓ TikTok has analysis.hook_psychology: '{hook_psychology[:50]}...'" if len(str(hook_psychology)) > 50 else f"✓ TikTok has analysis.hook_psychology: '{hook_psychology}'")
                return
        pytest.skip("All TikTok analyses have errors")

    def test_tiktok_has_analysis_replicable_framework(self):
        """TikTok analysis should have analysis.replicable_framework field"""
        if not self.tiktok_analyses:
            pytest.skip("No TikTok analyses in data")
        
        for tt in self.tiktok_analyses:
            if not tt.get("error"):
                analysis = tt.get("analysis", {})
                framework = analysis.get("replicable_framework")
                assert framework is not None, f"analysis.replicable_framework should exist"
                print(f"✓ TikTok has analysis.replicable_framework: '{framework[:50]}...'" if len(str(framework)) > 50 else f"✓ TikTok has analysis.replicable_framework: '{framework}'")
                return
        pytest.skip("All TikTok analyses have errors")


class TestPatternSummaryStructure:
    """Tests for pattern_summary data structure"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Fetch data once for all tests in this class"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/latest")
        assert response.status_code == 200
        self.data = response.json()
        self.pattern_summary = self.data.get("latest", {}).get("pattern_summary", {})

    def test_pattern_summary_has_top_replicable_frameworks(self):
        """Pattern summary should have top_replicable_frameworks field"""
        frameworks = self.pattern_summary.get("top_replicable_frameworks")
        assert frameworks is not None, "top_replicable_frameworks should exist"
        assert isinstance(frameworks, list), f"top_replicable_frameworks should be list, got {type(frameworks)}"
        print(f"✓ pattern_summary has top_replicable_frameworks: {len(frameworks)} items")

    def test_pattern_summary_has_dominant_hook_types(self):
        """Pattern summary should have dominant_hook_types field"""
        hook_types = self.pattern_summary.get("dominant_hook_types")
        assert hook_types is not None, "dominant_hook_types should exist"
        assert isinstance(hook_types, list), f"dominant_hook_types should be list, got {type(hook_types)}"
        print(f"✓ pattern_summary has dominant_hook_types: {len(hook_types)} items")

    def test_pattern_summary_has_dominant_visual_styles(self):
        """Pattern summary should have dominant_visual_styles field"""
        visual_styles = self.pattern_summary.get("dominant_visual_styles")
        assert visual_styles is not None, "dominant_visual_styles should exist"
        assert isinstance(visual_styles, list), f"dominant_visual_styles should be list, got {type(visual_styles)}"
        print(f"✓ pattern_summary has dominant_visual_styles: {len(visual_styles)} items")


class TestCreativeAnalysisRun:
    """Tests for POST /api/research/{campaign_id}/creative-analysis/run"""

    def test_run_returns_running_status(self):
        """POST /run should return status:running"""
        response = requests.post(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/run")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("status") == "running", f"Expected status='running', got {data.get('status')}"
        print(f"✓ POST /run returned status='running'")


class TestCreativeAnalysisHistory:
    """Tests for GET /api/research/{campaign_id}/creative-analysis/history"""

    def test_history_returns_200(self):
        """GET /history should return 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/history")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ GET /history returned 200")

    def test_history_returns_snapshots_list(self):
        """GET /history should return snapshots array"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/creative-analysis/history")
        assert response.status_code == 200
        data = response.json()
        snapshots = data.get("snapshots")
        assert isinstance(snapshots, list), f"snapshots should be list, got {type(snapshots)}"
        print(f"✓ GET /history returned {len(snapshots)} snapshots")


class TestCreativeAnalysisInvalidCampaign:
    """Tests for invalid campaign IDs"""

    def test_latest_returns_404_for_invalid_campaign(self):
        """GET /latest should return 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/creative-analysis/latest")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ GET /latest returns 404 for invalid campaign")

    def test_run_returns_404_for_invalid_campaign(self):
        """POST /run should return 404 for non-existent campaign"""
        response = requests.post(f"{BASE_URL}/api/research/invalid-campaign-id/creative-analysis/run")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ POST /run returns 404 for invalid campaign")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
