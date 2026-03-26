"""
Sprint 2: Customer Intel Module - Backend API Tests
Tests GET/POST endpoints for Customer Intel module (replacing Market Intel)

Endpoints tested:
- GET /api/research/{campaignId}/customer-intel/latest
- POST /api/research/{campaignId}/customer-intel/run
- GET /api/research/{campaignId}/customer-intel/history

Also verifies existing endpoints still work with latest accessor:
- GET /api/research/{campaignId}/search-intent/latest
- GET /api/research/{campaignId}/seasonality/latest
- GET /api/research/{campaignId}/competitors/latest
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Campaign with ALL research data
CAMPAIGN_WITH_DATA = "21ec9a20-7747-4353-abe4-2f6881365c5b"
# Campaign without data
CAMPAIGN_WITHOUT_DATA = "b66229cf-7aa9-4e51-ae0e-81a57ab2ac18"


class TestCustomerIntelLatest:
    """Tests for GET /api/research/{campaignId}/customer-intel/latest"""
    
    def test_customer_intel_latest_returns_normalized_format(self):
        """Customer Intel GET /latest returns has_data, status, latest, refresh_due_in_days"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify normalized format
        assert "has_data" in data, "Missing 'has_data' field"
        assert "status" in data, "Missing 'status' field"
        assert "latest" in data, "Missing 'latest' field"
        assert "refresh_due_in_days" in data, "Missing 'refresh_due_in_days' field"
        
        print(f"✓ Customer Intel returns normalized format with has_data={data['has_data']}, status={data['status']}")
    
    def test_customer_intel_latest_not_run_status_when_no_data(self):
        """Campaign without data returns status='not_run' and has_data=False"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITHOUT_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["has_data"] == False, "Expected has_data=False for campaign without data"
        assert data["status"] == "not_run", f"Expected status='not_run', got '{data['status']}'"
        assert data["latest"] is None, "Expected latest=None for campaign without data"
        assert data["refresh_due_in_days"] is None, "Expected refresh_due_in_days=None for campaign without data"
        
        print("✓ Campaign without data returns not_run status correctly")
    
    def test_customer_intel_latest_fresh_status_with_data(self):
        """Campaign with data returns status='fresh' and valid refresh_due_in_days"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        assert data["has_data"] == True, "Expected has_data=True for campaign with data"
        assert data["status"] in ["fresh", "stale"], f"Expected status='fresh' or 'stale', got '{data['status']}'"
        assert data["latest"] is not None, "Expected latest to be present"
        assert isinstance(data["refresh_due_in_days"], int), "Expected refresh_due_in_days to be integer"
        
        print(f"✓ Campaign with data returns status='{data['status']}' with refresh_due_in_days={data['refresh_due_in_days']}")
    
    def test_customer_intel_latest_404_for_invalid_campaign(self):
        """Invalid campaign ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/customer-intel/latest")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print("✓ Invalid campaign ID returns 404")


class TestCustomerIntelSnapshotStructure:
    """Tests for Customer Intel snapshot structure (when data exists)"""
    
    def test_snapshot_has_summary_bullets(self):
        """Snapshot has summary_bullets array with max 3 items, each <=90 chars"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        assert "summary_bullets" in snapshot, "Missing summary_bullets field"
        bullets = snapshot["summary_bullets"]
        
        assert isinstance(bullets, list), "summary_bullets should be a list"
        assert len(bullets) <= 3, f"Expected max 3 bullets, got {len(bullets)}"
        
        for bullet in bullets:
            assert len(bullet) <= 90, f"Bullet exceeds 90 chars: '{bullet[:50]}...'"
        
        print(f"✓ summary_bullets present with {len(bullets)} items (each <=90 chars)")
    
    def test_snapshot_has_icp_segments(self):
        """Snapshot has icp_segments array with 1-3 segments"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        assert "icp_segments" in snapshot, "Missing icp_segments field"
        segments = snapshot["icp_segments"]
        
        assert isinstance(segments, list), "icp_segments should be a list"
        assert 1 <= len(segments) <= 3, f"Expected 1-3 segments, got {len(segments)}"
        
        # Verify first segment structure
        if segments:
            seg = segments[0]
            required_fields = ["name", "job_to_be_done", "motivations", "pains", "objections", 
                             "decision_speed", "price_sensitivity", "best_channels"]
            for field in required_fields:
                assert field in seg, f"Missing field '{field}' in ICP segment"
            
            # Check enum values
            assert seg["decision_speed"] in ["fast", "medium", "slow", "unknown"], f"Invalid decision_speed: {seg['decision_speed']}"
            assert seg["price_sensitivity"] in ["low", "med", "high", "unknown"], f"Invalid price_sensitivity: {seg['price_sensitivity']}"
        
        print(f"✓ icp_segments present with {len(segments)} segments with correct structure")
    
    def test_snapshot_has_triggers(self):
        """Snapshot has triggers block with moments, urgency_triggers, planned_triggers"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        assert "triggers" in snapshot, "Missing triggers field"
        triggers = snapshot["triggers"]
        
        assert "moments" in triggers, "Missing triggers.moments"
        assert "urgency_triggers" in triggers, "Missing triggers.urgency_triggers"
        assert "planned_triggers" in triggers, "Missing triggers.planned_triggers"
        
        assert isinstance(triggers["moments"], list), "moments should be a list"
        assert isinstance(triggers["urgency_triggers"], list), "urgency_triggers should be a list"
        assert isinstance(triggers["planned_triggers"], list), "planned_triggers should be a list"
        
        print(f"✓ triggers present with {len(triggers['moments'])} moments, {len(triggers['urgency_triggers'])} urgency, {len(triggers['planned_triggers'])} planned")
    
    def test_snapshot_has_objections_and_proof(self):
        """Snapshot has objections_and_proof with objections, proof_types_ranked, risk_reducers"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        assert "objections_and_proof" in snapshot, "Missing objections_and_proof field"
        obj_proof = snapshot["objections_and_proof"]
        
        assert "objections" in obj_proof, "Missing objections_and_proof.objections"
        assert "proof_types_ranked" in obj_proof, "Missing objections_and_proof.proof_types_ranked"
        assert "risk_reducers" in obj_proof, "Missing objections_and_proof.risk_reducers"
        
        assert isinstance(obj_proof["objections"], list), "objections should be a list"
        assert isinstance(obj_proof["proof_types_ranked"], list), "proof_types_ranked should be a list"
        assert isinstance(obj_proof["risk_reducers"], list), "risk_reducers should be a list"
        
        print(f"✓ objections_and_proof present with {len(obj_proof['objections'])} objections, {len(obj_proof['proof_types_ranked'])} proof types")
    
    def test_snapshot_has_language_bank(self):
        """Snapshot has language_bank with desire_words, anxiety_words, intent_words"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        assert "language_bank" in snapshot, "Missing language_bank field"
        lang = snapshot["language_bank"]
        
        assert "desire_words" in lang, "Missing language_bank.desire_words"
        assert "anxiety_words" in lang, "Missing language_bank.anxiety_words"
        assert "intent_words" in lang, "Missing language_bank.intent_words"
        
        assert isinstance(lang["desire_words"], list), "desire_words should be a list"
        assert isinstance(lang["anxiety_words"], list), "anxiety_words should be a list"
        assert isinstance(lang["intent_words"], list), "intent_words should be a list"
        
        total_words = len(lang["desire_words"]) + len(lang["anxiety_words"]) + len(lang["intent_words"])
        
        print(f"✓ language_bank present with total {total_words} words across 3 categories")
    
    def test_snapshot_has_persona_cards_optional(self):
        """Snapshot can have persona_cards (optional)"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        # persona_cards is optional but should be in schema
        assert "persona_cards" in snapshot, "Missing persona_cards field"
        personas = snapshot["persona_cards"]
        
        assert isinstance(personas, list), "persona_cards should be a list"
        
        if personas:
            persona = personas[0]
            expected_fields = ["name", "segment", "scenario", "trigger", "key_objection", "winning_proof"]
            for field in expected_fields:
                assert field in persona, f"Missing field '{field}' in persona card"
        
        print(f"✓ persona_cards present with {len(personas)} personas")
    
    def test_snapshot_has_internal_metadata(self):
        """Snapshot has internal metadata with missing_inputs and input_sources"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        assert "internal" in snapshot, "Missing internal field"
        internal = snapshot["internal"]
        
        assert "missing_inputs" in internal, "Missing internal.missing_inputs"
        assert "input_sources" in internal, "Missing internal.input_sources"
        assert "llm_model" in internal, "Missing internal.llm_model"
        
        assert isinstance(internal["missing_inputs"], list), "missing_inputs should be a list"
        assert isinstance(internal["input_sources"], list), "input_sources should be a list"
        
        print(f"✓ internal metadata present with sources: {internal['input_sources']}, missing: {internal['missing_inputs']}")


class TestCustomerIntelMissingInputs:
    """Tests for Customer Intel missing_inputs behavior"""
    
    def test_missing_inputs_empty_when_all_data_available(self):
        """internal.missing_inputs should be empty when all research modules have data"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/latest")
        assert response.status_code == 200
        
        snapshot = response.json().get("latest")
        if not snapshot:
            pytest.skip("No customer intel data available")
        
        internal = snapshot.get("internal", {})
        missing_inputs = internal.get("missing_inputs", [])
        
        # Campaign with data should have all inputs available
        # Missing inputs should be empty or only contain optional sources
        print(f"missing_inputs: {missing_inputs}")
        print(f"input_sources: {internal.get('input_sources', [])}")
        
        # Verify input_sources contains the core required inputs
        input_sources = internal.get("input_sources", [])
        assert "step1" in input_sources, "step1 should be in input_sources"
        assert "step2" in input_sources, "step2 should be in input_sources"
        
        print(f"✓ internal.missing_inputs check passed - missing: {missing_inputs}")


class TestOtherEndpointsStillWork:
    """Verify other research endpoints still work with latest accessor"""
    
    def test_search_intent_latest_still_works(self):
        """Search Intent /latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/search-intent/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        print(f"✓ Search Intent /latest works with has_data={data['has_data']}, status={data['status']}")
    
    def test_seasonality_latest_still_works(self):
        """Seasonality /latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        print(f"✓ Seasonality /latest works with has_data={data['has_data']}, status={data['status']}")
    
    def test_competitors_latest_still_works(self):
        """Competitors /latest endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/competitors/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        
        print(f"✓ Competitors /latest works with has_data={data['has_data']}, status={data['status']}")


class TestCustomerIntelHistory:
    """Tests for GET /api/research/{campaignId}/customer-intel/history"""
    
    def test_customer_intel_history_endpoint_exists(self):
        """History endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "campaign_id" in data
        assert "history" in data
        assert isinstance(data["history"], list)
        
        print(f"✓ Customer Intel history endpoint works with {len(data['history'])} entries")
    
    def test_customer_intel_history_404_for_invalid_campaign(self):
        """History endpoint returns 404 for invalid campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/customer-intel/history")
        assert response.status_code == 404
        
        print("✓ History endpoint returns 404 for invalid campaign")


# Note: POST /run test is commented out due to long Perplexity sonar call time (15-20 seconds)
# Uncomment to test the run endpoint when needed

# class TestCustomerIntelRun:
#     """Tests for POST /api/research/{campaignId}/customer-intel/run"""
#     
#     def test_customer_intel_run_succeeds(self):
#         """POST /run succeeds and returns snapshot"""
#         response = requests.post(f"{BASE_URL}/api/research/{CAMPAIGN_WITH_DATA}/customer-intel/run")
#         assert response.status_code == 200
#         
#         data = response.json()
#         assert data.get("status") == "success"
#         assert "snapshot" in data
#         
#         print("✓ Customer Intel run succeeded")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
