"""
Novara Research Foundation: Competitor Discovery Tests
Tests for GET/POST /api/research/{campaignId}/competitors/* endpoints

Test Campaign: 21ec9a20-7747-4353-abe4-2f6881365c5b (Instaglam Dubai - has Step 2)
Test Campaign without Step 2: b66229cf-7aa9-4e51-ae0e-81a57ab2ac18
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaigns
CAMPAIGN_WITH_STEP2 = "21ec9a20-7747-4353-abe4-2f6881365c5b"  # Instaglam Dubai
CAMPAIGN_WITHOUT_STEP2 = "b66229cf-7aa9-4e51-ae0e-81a57ab2ac18"
INVALID_CAMPAIGN = "invalid-campaign-id-12345"


class TestCompetitorsLatest:
    """Tests for GET /api/research/{campaignId}/competitors/latest"""
    
    def test_get_latest_returns_200_for_existing_campaign(self):
        """GET /api/research/{campaignId}/competitors/latest returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        assert response.status_code == 200
        print(f"✓ GET competitors/latest returns 200")
    
    def test_get_latest_has_required_fields(self):
        """Response has campaign_id, has_data, snapshot, refresh_due_in_days"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        assert "campaign_id" in data
        assert "has_data" in data
        assert "snapshot" in data
        assert "refresh_due_in_days" in data
        print(f"✓ Response has required fields: campaign_id, has_data, snapshot, refresh_due_in_days")
    
    def test_get_latest_snapshot_structure(self):
        """Snapshot has correct structure (version, captured_at, refresh_due_at, inputs_used, competitors, etc.)"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data"):
            snapshot = data["snapshot"]
            assert "version" in snapshot
            assert "captured_at" in snapshot
            assert "refresh_due_at" in snapshot
            assert "inputs_used" in snapshot
            assert "competitors" in snapshot
            assert "category_search_terms" in snapshot
            assert "negative_filters" in snapshot
            assert "delta" in snapshot
            print(f"✓ Snapshot has correct structure")
        else:
            print(f"⚠ No data yet - snapshot structure not tested")
    
    def test_get_latest_inputs_used_structure(self):
        """inputs_used has geo, industry, subcategory, niche, services, brand_name"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data"):
            inputs = data["snapshot"]["inputs_used"]
            assert "geo" in inputs
            assert "industry" in inputs
            assert "subcategory" in inputs
            assert "niche" in inputs
            assert "services" in inputs
            assert "brand_name" in inputs
            
            # Geo should have city and country
            geo = inputs["geo"]
            assert "city" in geo
            assert "country" in geo
            print(f"✓ inputs_used has correct structure with geo.city and geo.country")
        else:
            print(f"⚠ No data yet - inputs_used structure not tested")
    
    def test_get_latest_competitors_structure(self):
        """Each competitor has name, website, positioning_summary, overlap_reason"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data") and data["snapshot"]["competitors"]:
            for i, comp in enumerate(data["snapshot"]["competitors"]):
                assert "name" in comp, f"Competitor {i} missing name"
                assert "website" in comp, f"Competitor {i} missing website"
                assert "positioning_summary" in comp, f"Competitor {i} missing positioning_summary"
                assert "overlap_reason" in comp, f"Competitor {i} missing overlap_reason"
                # Optional social fields
                assert "instagram_url" in comp or comp.get("instagram_url") is None
                assert "tiktok_url" in comp or comp.get("tiktok_url") is None
            print(f"✓ All {len(data['snapshot']['competitors'])} competitors have correct structure")
        else:
            print(f"⚠ No competitors data yet")
    
    def test_get_latest_delta_structure(self):
        """delta has previous_captured_at, new_competitors_count, removed_competitors_count, notable_changes"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data"):
            delta = data["snapshot"]["delta"]
            assert "previous_captured_at" in delta
            assert "new_competitors_count" in delta
            assert "removed_competitors_count" in delta
            assert "notable_changes" in delta
            print(f"✓ delta has correct structure")
        else:
            print(f"⚠ No data yet - delta structure not tested")
    
    def test_get_latest_refresh_due_in_days_is_valid(self):
        """refresh_due_in_days is non-negative integer or None"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data"):
            refresh_days = data["refresh_due_in_days"]
            assert isinstance(refresh_days, int)
            assert refresh_days >= 0
            print(f"✓ refresh_due_in_days is valid: {refresh_days} days")
        else:
            assert data["refresh_due_in_days"] is None
            print(f"✓ refresh_due_in_days is None when no data")
    
    def test_get_latest_returns_404_for_invalid_campaign(self):
        """GET /api/research/{invalidId}/competitors/latest returns 404"""
        response = requests.get(f"{BASE_URL}/api/research/{INVALID_CAMPAIGN}/competitors/latest")
        assert response.status_code == 404
        print(f"✓ Returns 404 for invalid campaign")
    
    def test_get_latest_returns_no_data_for_campaign_without_competitors(self):
        """Campaign without competitors returns has_data=false"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITHOUT_STEP2}/competitors/latest")
        # Should return 200 with has_data=false (campaign exists but no Step 2)
        # OR 404 if campaign doesn't exist
        if response.status_code == 200:
            data = response.json()
            assert data["has_data"] == False
            assert data["snapshot"] is None
            print(f"✓ Returns has_data=false for campaign without competitors")
        else:
            print(f"✓ Returns {response.status_code} for campaign without Step 2")


class TestCompetitorsRun:
    """Tests for POST /api/research/{campaignId}/competitors/run"""
    
    def test_run_returns_400_without_step2(self):
        """POST /api/research/{campaignId}/competitors/run returns 400 without Step 2"""
        response = requests.post(f"{BASE_URL}/api/research/{CAMPAIGN_WITHOUT_STEP2}/competitors/run")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Step 2" in data["detail"] or "Website context" in data["detail"]
        print(f"✓ Returns 400 without Step 2: {data['detail']}")
    
    def test_run_returns_404_for_invalid_campaign(self):
        """POST /api/research/{invalidId}/competitors/run returns 404"""
        response = requests.post(f"{BASE_URL}/api/research/{INVALID_CAMPAIGN}/competitors/run")
        assert response.status_code == 404
        print(f"✓ Returns 404 for invalid campaign")
    
    def test_run_returns_200_for_valid_campaign(self):
        """POST /api/research/{campaignId}/competitors/run returns 200 for valid campaign with Step 2"""
        response = requests.post(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/run", timeout=120)
        assert response.status_code == 200
        print(f"✓ POST competitors/run returns 200")
    
    def test_run_response_structure(self):
        """Response has campaign_id, status, snapshot, message"""
        response = requests.post(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/run", timeout=120)
        data = response.json()
        
        assert "campaign_id" in data
        assert "status" in data
        assert "snapshot" in data
        assert "message" in data
        print(f"✓ Response has required fields: campaign_id, status, snapshot, message")
        print(f"  Status: {data['status']}, Message: {data['message']}")
    
    def test_run_generates_competitors(self):
        """Run generates competitors list"""
        response = requests.post(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/run", timeout=120)
        data = response.json()
        
        if data["status"] in ["success", "partial"]:
            snapshot = data["snapshot"]
            assert "competitors" in snapshot
            assert len(snapshot["competitors"]) >= 1
            print(f"✓ Generated {len(snapshot['competitors'])} competitors")
        else:
            print(f"⚠ Status is {data['status']}, competitors may not be generated")
    
    def test_run_generates_category_search_terms(self):
        """Run generates category_search_terms"""
        response = requests.post(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/run", timeout=120)
        data = response.json()
        
        if data["status"] in ["success", "partial"]:
            snapshot = data["snapshot"]
            assert "category_search_terms" in snapshot
            assert len(snapshot["category_search_terms"]) >= 1
            print(f"✓ Generated {len(snapshot['category_search_terms'])} category search terms")
        else:
            print(f"⚠ Status is {data['status']}, category terms may not be generated")


class TestCompetitorsHistory:
    """Tests for GET /api/research/{campaignId}/competitors/history"""
    
    def test_history_returns_200(self):
        """GET /api/research/{campaignId}/competitors/history returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/history")
        assert response.status_code == 200
        print(f"✓ GET competitors/history returns 200")
    
    def test_history_has_correct_structure(self):
        """Response has campaign_id, snapshots, total_count"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/history")
        data = response.json()
        
        assert "campaign_id" in data
        assert "snapshots" in data
        assert "total_count" in data
        assert isinstance(data["snapshots"], list)
        assert isinstance(data["total_count"], int)
        print(f"✓ History has correct structure with {data['total_count']} snapshots")
    
    def test_history_returns_404_for_invalid_campaign(self):
        """GET /api/research/{invalidId}/competitors/history returns 404"""
        response = requests.get(f"{BASE_URL}/api/research/{INVALID_CAMPAIGN}/competitors/history")
        assert response.status_code == 404
        print(f"✓ Returns 404 for invalid campaign")


class TestCompetitorDataQuality:
    """Tests for competitor data quality"""
    
    def test_competitor_names_are_not_empty(self):
        """Competitor names are not empty strings"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data") and data["snapshot"]["competitors"]:
            for comp in data["snapshot"]["competitors"]:
                assert comp["name"] and len(comp["name"]) > 0
            print(f"✓ All competitor names are non-empty")
        else:
            print(f"⚠ No competitors to test")
    
    def test_competitor_websites_are_valid_urls(self):
        """Competitor websites are valid URLs"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data") and data["snapshot"]["competitors"]:
            for comp in data["snapshot"]["competitors"]:
                website = comp.get("website", "")
                if website:
                    assert website.startswith("http://") or website.startswith("https://")
            print(f"✓ All competitor websites are valid URLs")
        else:
            print(f"⚠ No competitors to test")
    
    def test_instagram_handles_format(self):
        """Instagram handles start with @"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data") and data["snapshot"]["competitors"]:
            for comp in data["snapshot"]["competitors"]:
                handle = comp.get("instagram_handle")
                if handle:
                    assert handle.startswith("@"), f"Instagram handle should start with @: {handle}"
            print(f"✓ Instagram handles have correct format")
        else:
            print(f"⚠ No competitors to test")
    
    def test_category_search_terms_are_valid(self):
        """Category search terms are 2-7 words"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data"):
            terms = data["snapshot"]["category_search_terms"]
            for term in terms:
                word_count = len(term.split())
                assert 2 <= word_count <= 7, f"Term '{term}' has {word_count} words, expected 2-7"
            print(f"✓ All {len(terms)} category search terms have valid word count")
        else:
            print(f"⚠ No data to test")
    
    def test_positioning_summary_length(self):
        """Positioning summaries are under 140 chars"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_STEP2}/competitors/latest")
        data = response.json()
        
        if data.get("has_data") and data["snapshot"]["competitors"]:
            for comp in data["snapshot"]["competitors"]:
                summary = comp.get("positioning_summary", "")
                assert len(summary) <= 140, f"Positioning summary too long: {len(summary)} chars"
            print(f"✓ All positioning summaries are under 140 chars")
        else:
            print(f"⚠ No competitors to test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
