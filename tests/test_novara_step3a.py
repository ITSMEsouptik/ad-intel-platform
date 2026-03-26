"""
Novara API Tests - Step 3A Perplexity Intel Pack
Tests for the complete flow: Wizard → BuildingPack → PackView → IntelView
"""

import pytest
import requests
import time
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')
API_URL = f"{BASE_URL}/api"


class TestHealthAndBasicEndpoints:
    """Basic API health and endpoint tests"""
    
    def test_api_health(self):
        """Test API root endpoint returns healthy status"""
        response = requests.get(f"{API_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'healthy'
        print(f"✅ API health check passed: {data}")


class TestCampaignBriefCreation:
    """Campaign brief creation tests"""
    
    def test_create_campaign_brief_pilot_track(self):
        """Test creating campaign brief with pilot track (ads_intent='yes')"""
        payload = {
            "website_url": "example-brand.co",
            "primary_goal": "bookings_leads",
            "success_definition": "5 bookings per day",
            "country": "United States",
            "city_or_region": "New York",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "1000-5000",
            "name": "Test User Step3A",
            "email": f"test.step3a.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        }
        
        response = requests.post(f"{API_URL}/campaign-briefs", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert 'campaign_brief_id' in data
        assert data.get('track') == 'pilot'
        
        # Store for later tests
        pytest.brief_id = data['campaign_brief_id']
        print(f"✅ Created campaign brief: {pytest.brief_id}")
        print(f"   Track: {data.get('track')}")
        return data
    
    def test_get_campaign_brief(self):
        """Test retrieving campaign brief by ID"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        response = requests.get(f"{API_URL}/campaign-briefs/{pytest.brief_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get('campaign_brief_id') == pytest.brief_id
        print(f"✅ Retrieved campaign brief: {pytest.brief_id[:8]}...")


class TestStep2WebsiteContextExtraction:
    """Step 2 - Website Context Extraction tests"""
    
    def test_start_orchestration(self):
        """Test starting Step 2 orchestration"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        response = requests.post(f"{API_URL}/orchestrations/{pytest.brief_id}/start")
        assert response.status_code == 200
        
        data = response.json()
        assert 'orchestration_id' in data
        assert 'website_context_pack_id' in data
        
        pytest.orchestration_id = data['orchestration_id']
        pytest.pack_id = data['website_context_pack_id']
        print(f"✅ Started orchestration: {pytest.orchestration_id[:8]}...")
        print(f"   Pack ID: {pytest.pack_id[:8]}...")
        return data
    
    def test_poll_orchestration_status(self):
        """Test polling orchestration status until completion"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        max_polls = 30  # 60 seconds max
        poll_count = 0
        final_status = None
        
        print("   Polling for Step 2 completion...")
        while poll_count < max_polls:
            time.sleep(2)
            poll_count += 1
            
            response = requests.get(f"{API_URL}/orchestrations/{pytest.brief_id}/status")
            assert response.status_code == 200
            
            data = response.json()
            pack = data.get('website_context_pack', {})
            pack_status = pack.get('status', 'unknown')
            
            print(f"   Poll {poll_count}: Status = {pack_status}")
            
            if pack_status in ['success', 'partial', 'failed', 'needs_user_input']:
                final_status = pack_status
                pytest.step2_status = final_status
                break
        
        assert final_status is not None, "Step 2 did not complete within timeout"
        assert final_status in ['success', 'partial', 'needs_user_input'], f"Step 2 failed with status: {final_status}"
        print(f"✅ Step 2 completed with status: {final_status}")
    
    def test_get_website_context_pack(self):
        """Test retrieving website context pack"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        response = requests.get(f"{API_URL}/website-context-packs/by-campaign/{pytest.brief_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert 'website_context_pack_id' in data
        assert 'data' in data
        
        # Validate pack structure
        pack_data = data.get('data', {})
        expected_sections = ['brand_identity', 'offer', 'conversion', 'proof', 'site', 'quality']
        for section in expected_sections:
            assert section in pack_data, f"Missing section: {section}"
        
        confidence_score = data.get('confidence_score', 0)
        print(f"✅ Website context pack retrieved")
        print(f"   Confidence Score: {confidence_score}/100")
        print(f"   Brand Name: {pack_data.get('brand_identity', {}).get('brand_name', 'N/A')}")


class TestStep3APerplexityIntel:
    """Step 3A - Perplexity Intel Pack tests"""
    
    def test_start_step3a(self):
        """Test starting Step 3A - Perplexity Intel generation"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        response = requests.post(f"{API_URL}/orchestrations/{pytest.brief_id}/step-3a/start")
        assert response.status_code == 200
        
        data = response.json()
        assert 'intel_pack_id' in data
        assert data.get('status') in ['running', 'success']
        
        pytest.intel_pack_id = data['intel_pack_id']
        print(f"✅ Started Step 3A: {pytest.intel_pack_id[:8]}...")
        print(f"   Status: {data.get('status')}")
        return data
    
    def test_poll_step3a_completion(self):
        """Test polling Step 3A until completion (can take 30-60 seconds)"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        max_polls = 45  # 90 seconds max for Perplexity API
        poll_count = 0
        final_status = None
        
        print("   Polling for Step 3A completion (Perplexity API)...")
        while poll_count < max_polls:
            time.sleep(2)
            poll_count += 1
            
            response = requests.get(f"{API_URL}/perplexity-intel-packs/by-campaign/{pytest.brief_id}")
            
            if response.status_code == 404:
                print(f"   Poll {poll_count}: Intel pack not found yet")
                continue
            
            assert response.status_code == 200
            
            data = response.json()
            intel_status = data.get('status', 'unknown')
            
            print(f"   Poll {poll_count}: Status = {intel_status}")
            
            if intel_status in ['success', 'failed']:
                final_status = intel_status
                pytest.step3a_status = final_status
                break
        
        assert final_status is not None, "Step 3A did not complete within timeout"
        assert final_status == 'success', f"Step 3A failed with status: {final_status}"
        print(f"✅ Step 3A completed with status: {final_status}")
    
    def test_get_perplexity_intel_pack(self):
        """Test retrieving Perplexity Intel Pack and validating structure"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        response = requests.get(f"{API_URL}/perplexity-intel-packs/by-campaign/{pytest.brief_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert 'intel_pack_id' in data
        assert 'data' in data
        assert data.get('status') == 'success'
        
        # Validate intel pack structure
        intel_data = data.get('data', {})
        
        # Check required sections
        required_sections = [
            'category', 'geo_context', 'customer_psychology', 'trust_builders',
            'competitors', 'foreplay_search_blueprint', 'angle_seeds',
            'positioning_diagnosis', 'offer_scorecard_and_quick_wins',
            'channel_and_format_fit', 'compliance_and_risk_flags',
            'open_questions_for_founder', 'brand_audit_lite', 'ui_summary',
            'sources', 'quality'
        ]
        
        for section in required_sections:
            assert section in intel_data, f"Missing section: {section}"
        
        # Validate competitors (should be 2-3)
        competitors = intel_data.get('competitors', [])
        assert len(competitors) >= 2, f"Expected at least 2 competitors, got {len(competitors)}"
        assert len(competitors) <= 3, f"Expected at most 3 competitors, got {len(competitors)}"
        
        # Validate UI summary cards (should be 5)
        ui_cards = intel_data.get('ui_summary', {}).get('cards', [])
        assert len(ui_cards) == 5, f"Expected 5 UI summary cards, got {len(ui_cards)}"
        
        print(f"✅ Perplexity Intel Pack retrieved and validated")
        print(f"   Industry: {intel_data.get('category', {}).get('industry', 'N/A')}")
        print(f"   Competitors found: {len(competitors)}")
        for comp in competitors:
            print(f"     - {comp.get('name', 'N/A')}: {comp.get('website', 'N/A')}")
        print(f"   UI Summary Cards: {len(ui_cards)}")


class TestStep3AEdgeCases:
    """Edge case tests for Step 3A"""
    
    def test_step3a_without_step2(self):
        """Test that Step 3A fails gracefully without Step 2 completion"""
        # Create a new brief without running Step 2
        payload = {
            "website_url": "test-no-step2.com",
            "primary_goal": "sales_orders",
            "success_definition": "10 sales per week",
            "country": "United States",
            "city_or_region": "Los Angeles",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "300-1000",
            "name": "Test No Step2",
            "email": f"test.nostep2.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        }
        
        response = requests.post(f"{API_URL}/campaign-briefs", json=payload)
        assert response.status_code == 200
        new_brief_id = response.json()['campaign_brief_id']
        
        # Try to start Step 3A without Step 2
        response = requests.post(f"{API_URL}/orchestrations/{new_brief_id}/step-3a/start")
        assert response.status_code == 400, "Expected 400 error when Step 2 not completed"
        
        data = response.json()
        assert 'detail' in data
        print(f"✅ Step 3A correctly rejected without Step 2: {data.get('detail')}")
    
    def test_step3a_nonexistent_brief(self):
        """Test Step 3A with non-existent brief ID"""
        fake_brief_id = "nonexistent-brief-id-12345"
        
        response = requests.post(f"{API_URL}/orchestrations/{fake_brief_id}/step-3a/start")
        assert response.status_code == 404
        print(f"✅ Step 3A correctly returns 404 for non-existent brief")
    
    def test_get_intel_pack_nonexistent(self):
        """Test getting intel pack for non-existent brief"""
        fake_brief_id = "nonexistent-brief-id-12345"
        
        response = requests.get(f"{API_URL}/perplexity-intel-packs/by-campaign/{fake_brief_id}")
        assert response.status_code == 404
        print(f"✅ Intel pack endpoint correctly returns 404 for non-existent brief")


class TestOrchestrationStatusWithIntel:
    """Test orchestration status includes intel pack info"""
    
    def test_orchestration_status_includes_intel(self):
        """Test that orchestration status includes perplexity_intel_pack"""
        if not hasattr(pytest, 'brief_id'):
            pytest.skip("No brief_id from previous test")
        
        response = requests.get(f"{API_URL}/orchestrations/{pytest.brief_id}/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Should include all components
        assert 'orchestration' in data
        assert 'steps' in data
        assert 'website_context_pack' in data
        assert 'perplexity_intel_pack' in data
        
        # Verify intel pack is present
        intel_pack = data.get('perplexity_intel_pack')
        if intel_pack:
            assert intel_pack.get('status') in ['running', 'success', 'failed']
            print(f"✅ Orchestration status includes intel pack: {intel_pack.get('status')}")
        else:
            print(f"⚠️ Intel pack not yet in orchestration status")


# Fixture for session-scoped brief creation
@pytest.fixture(scope="session", autouse=True)
def setup_test_brief():
    """Create a test brief for the entire test session"""
    payload = {
        "website_url": "stripe.com",
        "primary_goal": "bookings_leads",
        "success_definition": "10 leads per day",
        "country": "United States",
        "city_or_region": "San Francisco",
        "destination_type": "website",
        "ads_intent": "yes",
        "budget_range_monthly": "5000+",
        "name": "Test Session User",
        "email": f"test.session.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
    }
    
    response = requests.post(f"{API_URL}/campaign-briefs", json=payload)
    if response.status_code == 200:
        pytest.session_brief_id = response.json()['campaign_brief_id']
        print(f"\n📋 Session brief created: {pytest.session_brief_id[:8]}...")
    
    yield
    
    # Cleanup could go here if needed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
