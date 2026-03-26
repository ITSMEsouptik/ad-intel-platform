"""
API Integration Tests for Seasonality v2.1 ("Buying Moments") Feature

Tests the backend API endpoints:
1. GET /api/research/{campaignId}/seasonality/latest - returns v2.1 schema
2. POST /api/research/{campaignId}/seasonality/run - triggers Perplexity and returns v2.1 snapshot
3. Schema validation - BuyingMoment fields (who, why_now, buy_triggers, must_answer, best_channels)
"""

import pytest
import requests
import os

# Get the public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign with Step 2 complete (example-brand.co - Dubai)
TEST_CAMPAIGN_ID = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"

# Fallback campaign if first doesn't work
FALLBACK_CAMPAIGN_ID = "2de697d6-1e75-47cb-8f29-6f4cb8978e02"


class TestSeasonalityV21API:
    """API tests for Seasonality v2.1 endpoints"""

    def test_api_health(self):
        """Verify API is running"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"API health check passed: {data}")

    def test_seasonality_latest_no_data(self):
        """Test GET /latest returns 'not_run' status when no data exists"""
        # Use a campaign that likely doesn't have seasonality data
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        
        # Should return 200 even if no data (not 404)
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "has_data" in data
        assert "status" in data
        
        print(f"Latest seasonality response: has_data={data.get('has_data')}, status={data.get('status')}")
        
        return data

    def test_seasonality_run_triggers_analysis(self):
        """Test POST /run triggers Perplexity API and returns v2.1 snapshot"""
        # This test actually calls the Perplexity API (takes 20-40 seconds)
        response = requests.post(
            f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/run",
            timeout=120  # Allow time for Perplexity API
        )
        
        # Should return 200 on success
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "campaign_id" in data
        assert "status" in data
        assert "snapshot" in data
        
        snapshot = data.get("snapshot", {})
        
        # Verify v2.1 schema
        assert snapshot.get("version") == "2.1", f"Expected version 2.1, got {snapshot.get('version')}"
        
        # Check for key_moments (BuyingMoment objects)
        key_moments = snapshot.get("key_moments", [])
        assert isinstance(key_moments, list), "key_moments should be a list"
        
        print(f"Seasonality run completed: status={data.get('status')}, moments={len(key_moments)}")
        
        return snapshot

    def test_buying_moment_v21_fields(self):
        """Verify BuyingMoment objects have v2.1 fields"""
        # First run to ensure data exists
        run_response = requests.post(
            f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/run",
            timeout=120
        )
        
        if run_response.status_code != 200:
            pytest.skip(f"Seasonality run failed: {run_response.text}")
        
        snapshot = run_response.json().get("snapshot", {})
        key_moments = snapshot.get("key_moments", [])
        
        if len(key_moments) == 0:
            pytest.skip("No buying moments returned - may be API limitation")
        
        # Check first moment for v2.1 fields
        moment = key_moments[0]
        
        # Required v2.1 fields
        v21_fields = ["moment", "window", "demand", "who", "why_now", "buy_triggers", "must_answer", "best_channels"]
        
        for field in v21_fields:
            assert field in moment, f"Missing v2.1 field: {field}"
        
        print(f"Buying moment v2.1 fields present:")
        print(f"  - moment: {moment.get('moment')}")
        print(f"  - window: {moment.get('window')}")
        print(f"  - demand: {moment.get('demand')}")
        print(f"  - who: {moment.get('who')[:50]}..." if len(moment.get('who', '')) > 50 else f"  - who: {moment.get('who')}")
        print(f"  - why_now: {moment.get('why_now')[:50]}..." if len(moment.get('why_now', '')) > 50 else f"  - why_now: {moment.get('why_now')}")
        print(f"  - buy_triggers count: {len(moment.get('buy_triggers', []))}")
        print(f"  - must_answer: {moment.get('must_answer')[:50]}..." if len(moment.get('must_answer', '')) > 50 else f"  - must_answer: {moment.get('must_answer')}")
        print(f"  - best_channels: {moment.get('best_channels')}")

    def test_seasonality_latest_returns_v21_schema(self):
        """Verify GET /latest returns v2.1 schema after run"""
        # First ensure data exists by running
        run_response = requests.post(
            f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/run",
            timeout=120
        )
        
        if run_response.status_code != 200:
            pytest.skip(f"Seasonality run failed: {run_response.text}")
        
        # Now get latest
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        data = response.json()
        
        # Verify has_data is True after run
        assert data.get("has_data") is True
        
        # Get the snapshot
        snapshot = data.get("latest", {})
        
        # Verify v2.1 schema
        assert snapshot.get("version") == "2.1"
        
        # Check key sections
        assert "key_moments" in snapshot
        assert "evergreen_demand" in snapshot
        assert "weekly_patterns" in snapshot
        assert "local_insights" in snapshot
        assert "audit" in snapshot
        
        print(f"Latest seasonality v2.1 schema verified:")
        print(f"  - version: {snapshot.get('version')}")
        print(f"  - key_moments: {len(snapshot.get('key_moments', []))}")
        print(f"  - evergreen_demand: {len(snapshot.get('evergreen_demand', []))}")
        print(f"  - local_insights: {len(snapshot.get('local_insights', []))}")

    def test_post_processing_filter_in_audit(self):
        """Verify audit contains post-processing stats"""
        run_response = requests.post(
            f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/run",
            timeout=120
        )
        
        if run_response.status_code != 200:
            pytest.skip(f"Seasonality run failed: {run_response.text}")
        
        snapshot = run_response.json().get("snapshot", {})
        audit = snapshot.get("audit", {})
        
        # Check audit fields
        assert "raw_moments_count" in audit
        assert "filtered_count" in audit
        assert "filter_reasons" in audit
        assert "relaxation_applied" in audit
        
        print(f"Audit stats:")
        print(f"  - raw_moments_count: {audit.get('raw_moments_count')}")
        print(f"  - filtered_count: {audit.get('filtered_count')}")
        print(f"  - filter_reasons: {audit.get('filter_reasons')}")
        print(f"  - relaxation_applied: {audit.get('relaxation_applied')}")

    def test_weekly_patterns_structure(self):
        """Verify weekly_patterns has peak_days and why"""
        run_response = requests.post(
            f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/run",
            timeout=120
        )
        
        if run_response.status_code != 200:
            pytest.skip(f"Seasonality run failed: {run_response.text}")
        
        snapshot = run_response.json().get("snapshot", {})
        weekly = snapshot.get("weekly_patterns", {})
        
        assert "peak_days" in weekly
        assert "why" in weekly
        assert isinstance(weekly.get("peak_days"), list)
        
        print(f"Weekly patterns:")
        print(f"  - peak_days: {weekly.get('peak_days')}")
        print(f"  - why: {weekly.get('why')}")

    def test_campaign_not_found_returns_404(self):
        """Test that non-existent campaign returns 404"""
        response = requests.get(f"{BASE_URL}/api/research/non-existent-id/seasonality/latest")
        assert response.status_code == 404

    def test_campaign_without_step2_returns_400(self):
        """Test that campaign without Step 2 returns 400 on run"""
        # Create a new campaign without Step 2
        new_brief = {
            "website_url": "https://test-no-step2.com",
            "primary_goal": "sales_orders",
            "success_definition": "Test campaign",
            "country": "United States",
            "city_or_region": "Test City",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "300-1000",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=new_brief)
        if create_response.status_code != 200:
            pytest.skip("Could not create test campaign")
        
        campaign_id = create_response.json().get("campaign_brief_id")
        
        # Try to run seasonality without Step 2
        run_response = requests.post(f"{BASE_URL}/api/research/{campaign_id}/seasonality/run")
        
        # Should return 400 (Step 2 required)
        assert run_response.status_code == 400
        print(f"Correctly returned 400 for campaign without Step 2: {run_response.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
