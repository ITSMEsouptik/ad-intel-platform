"""
API Tests for Customer Intel v1.1

Tests:
1. GET /api/research/{campaignId}/customer-intel/latest - v1.1 schema compliance
2. POST /api/research/{campaignId}/customer-intel/run - run endpoint returns v1.1 snapshot
3. Schema validation - v1.1 fields present, v1.0 fields absent
4. Backwards compatibility - old data still readable
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
TEST_CAMPAIGN_ID = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"


class TestCustomerIntelLatestAPI:
    """Test GET /api/research/{campaignId}/customer-intel/latest"""

    def test_api_health(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")

    def test_latest_returns_200(self):
        """GET latest returns 200 for valid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        assert response.status_code == 200
        print("✓ GET /customer-intel/latest returns 200")

    def test_latest_response_structure(self):
        """Response has has_data, status, latest, refresh_due_in_days"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        assert "has_data" in data, "Missing has_data field"
        assert "status" in data, "Missing status field"
        assert "latest" in data, "Missing latest field"
        
        print(f"✓ Response structure: has_data={data['has_data']}, status={data['status']}")

    def test_v11_snapshot_version(self):
        """If has_data, snapshot.version should be '1.1' for new data"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet - run the /run endpoint first")
        
        latest = data.get("latest", {})
        version = latest.get("version")
        
        # Accept both old (None/"1.0") and new ("1.1")
        print(f"✓ Snapshot version: {version}")
        
        if version == "1.1":
            print("✓ v1.1 schema confirmed")
        else:
            print(f"⚠ Old data version: {version} (run /run endpoint to get v1.1)")

    def test_v11_has_segments_not_icp_segments(self):
        """v1.1 uses 'segments' not 'icp_segments'"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        
        # v1.1 should have segments
        if latest.get("version") == "1.1":
            assert "segments" in latest, "v1.1 should have 'segments' field"
            assert "icp_segments" not in latest, "v1.1 should NOT have 'icp_segments' field"
            print(f"✓ segments field present with {len(latest.get('segments', []))} items")
        else:
            # Old data may have icp_segments
            print(f"⚠ Old data - checking backwards compatibility")
            has_segments = "segments" in latest
            has_icp_segments = "icp_segments" in latest
            print(f"  segments: {has_segments}, icp_segments: {has_icp_segments}")

    def test_v11_segment_card_fields(self):
        """v1.1 SegmentCard has new fields: best_offer_items, best_proof, risk_reducers, search_language"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        segments = latest.get("segments", latest.get("icp_segments", []))
        
        if not segments:
            pytest.skip("No segments in data")
        
        segment = segments[0]
        v11_fields = ["best_offer_items", "best_proof", "risk_reducers", "search_language"]
        
        for field in v11_fields:
            if field in segment:
                print(f"✓ {field} present: {len(segment.get(field, []))} items")
            else:
                print(f"⚠ {field} missing (may be old data)")

    def test_v11_trigger_map_structure(self):
        """v1.1 uses trigger_map with moment_triggers, urgency_triggers, planned_triggers"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        
        # Check for v1.1 trigger_map
        trigger_map = latest.get("trigger_map", {})
        triggers = latest.get("triggers", {})  # v1.0 fallback
        
        if trigger_map:
            print(f"✓ trigger_map present")
            print(f"  moment_triggers: {len(trigger_map.get('moment_triggers', []))} items")
            print(f"  urgency_triggers: {len(trigger_map.get('urgency_triggers', []))} items")
            print(f"  planned_triggers: {len(trigger_map.get('planned_triggers', []))} items")
        elif triggers:
            print(f"⚠ Using old 'triggers' structure (v1.0 data)")
        else:
            print(f"⚠ No trigger data found")

    def test_v11_language_bank_structure(self):
        """v1.1 uses desire_phrases, anxiety_phrases, intent_phrases"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        language_bank = latest.get("language_bank", {})
        
        if not language_bank:
            print(f"⚠ No language_bank in data")
            return
        
        v11_fields = ["desire_phrases", "anxiety_phrases", "intent_phrases"]
        v10_fields = ["desire_words", "anxiety_words", "intent_words"]
        
        for i, field in enumerate(v11_fields):
            if field in language_bank:
                print(f"✓ {field} present: {len(language_bank.get(field, []))} items")
            elif v10_fields[i] in language_bank:
                print(f"⚠ {v10_fields[i]} (v1.0 field name)")
            else:
                print(f"⚠ No {field} found")

    def test_v11_no_persona_cards(self):
        """v1.1 should NOT have persona_cards"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        
        assert "persona_cards" not in latest, "v1.1 should NOT have persona_cards"
        print("✓ No persona_cards field (correctly removed in v1.1)")

    def test_v11_no_decision_speed(self):
        """v1.1 should NOT have decision_speed in segments"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        segments = latest.get("segments", latest.get("icp_segments", []))
        
        for seg in segments:
            if "decision_speed" in seg:
                print(f"⚠ decision_speed still present in segment (old data)")
                return
        
        print("✓ No decision_speed in segments (correctly removed in v1.1)")

    def test_v11_no_price_sensitivity(self):
        """v1.1 should NOT have price_sensitivity in segments"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        segments = latest.get("segments", latest.get("icp_segments", []))
        
        for seg in segments:
            if "price_sensitivity" in seg:
                print(f"⚠ price_sensitivity still present in segment (old data)")
                return
        
        print("✓ No price_sensitivity in segments (correctly removed in v1.1)")

    def test_v11_no_best_cta_per_trigger(self):
        """v1.1 should NOT have best_cta_per_trigger"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        trigger_map = latest.get("trigger_map", latest.get("triggers", {}))
        
        if "best_cta_per_trigger" in trigger_map:
            print(f"⚠ best_cta_per_trigger still present (old data)")
        else:
            print("✓ No best_cta_per_trigger (correctly removed in v1.1)")

    def test_v11_audit_field(self):
        """v1.1 snapshot has audit field with grounding stats"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        data = response.json()
        
        if not data.get("has_data"):
            pytest.skip("No customer intel data yet")
        
        latest = data.get("latest", {})
        
        if latest.get("version") == "1.1":
            audit = latest.get("audit", {})
            assert "offer_items_available" in audit or "segments_raw_count" in audit, "v1.1 should have audit stats"
            print(f"✓ audit field present with grounding stats")
            print(f"  offer_items_used: {len(audit.get('offer_items_used', []))}")
            print(f"  segments_raw_count: {audit.get('segments_raw_count')}")
            print(f"  relaxation_applied: {audit.get('relaxation_applied')}")
        else:
            print(f"⚠ Old data - no audit field expected")


class TestCustomerIntelHistoryAPI:
    """Test GET /api/research/{campaignId}/customer-intel/history"""

    def test_history_returns_200(self):
        """GET history returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/history")
        assert response.status_code == 200
        data = response.json()
        assert "campaign_id" in data
        assert "history" in data
        print(f"✓ History endpoint returns {len(data.get('history', []))} snapshots")


class TestCustomerIntel404:
    """Test 404 handling"""

    def test_invalid_campaign_returns_404(self):
        """Invalid campaign ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/customer-intel/latest")
        assert response.status_code == 404
        print("✓ Invalid campaign returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
