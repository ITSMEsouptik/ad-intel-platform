"""
Phase 4 Feature Tests - PDF Export, Compare, and Progress endpoints
Tests for Novara Intelligence Hub Phase 4 features.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
TEST_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"


class TestPDFExport:
    """PDF Report Export endpoint tests"""
    
    def test_pdf_export_returns_200(self):
        """Test that PDF export endpoint returns HTTP 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/export/pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ PDF export returned status 200")
    
    def test_pdf_export_returns_pdf_content_type(self):
        """Test that PDF export returns application/pdf content type"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/export/pdf")
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✓ PDF export returns correct content type: {content_type}")
    
    def test_pdf_export_has_content_disposition(self):
        """Test that PDF export has Content-Disposition header for download"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/export/pdf")
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Expected attachment in Content-Disposition, got {content_disp}"
        assert 'novara-report' in content_disp, f"Expected novara-report in filename, got {content_disp}"
        print(f"✓ PDF export has correct Content-Disposition: {content_disp}")
    
    def test_pdf_export_has_valid_pdf_bytes(self):
        """Test that PDF export returns valid PDF bytes (starts with %PDF)"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/export/pdf")
        pdf_bytes = response.content
        assert pdf_bytes[:4] == b'%PDF', f"PDF content does not start with %PDF magic bytes"
        assert len(pdf_bytes) > 1000, f"PDF content seems too small: {len(pdf_bytes)} bytes"
        print(f"✓ PDF export returns valid PDF bytes ({len(pdf_bytes)} bytes)")
    
    def test_pdf_export_404_for_invalid_campaign(self):
        """Test that PDF export returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/export/pdf")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ PDF export returns 404 for invalid campaign")


class TestCompareEndpoints:
    """Module run comparison endpoint tests"""
    
    def test_customer_intel_compare(self):
        """Test customer-intel compare endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/compare")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_comparison' in data, "Response should have has_comparison field"
        assert 'module' in data, "Response should have module field"
        print(f"✓ customer-intel compare: has_comparison={data['has_comparison']}, deltas={len(data.get('deltas', []))}")
    
    def test_search_intent_compare(self):
        """Test search-intent compare endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/compare")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_comparison' in data, "Response should have has_comparison field"
        print(f"✓ search-intent compare: has_comparison={data['has_comparison']}, deltas={len(data.get('deltas', []))}")
    
    def test_seasonality_compare(self):
        """Test seasonality compare endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/compare")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_comparison' in data, "Response should have has_comparison field"
        print(f"✓ seasonality compare: has_comparison={data['has_comparison']}, deltas={len(data.get('deltas', []))}")
    
    def test_competitors_compare(self):
        """Test competitors compare endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/compare")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_comparison' in data, "Response should have has_comparison field"
        print(f"✓ competitors compare: has_comparison={data['has_comparison']}, deltas={len(data.get('deltas', []))}")
    
    def test_compare_delta_structure(self):
        """Test that deltas have correct structure when present"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/compare")
        data = response.json()
        
        if data.get('has_comparison') and data.get('deltas'):
            delta = data['deltas'][0]
            assert 'field' in delta, "Delta should have field"
            assert 'current' in delta, "Delta should have current value"
            assert 'previous' in delta, "Delta should have previous value"
            assert 'direction' in delta, "Delta should have direction (up/down)"
            assert delta['direction'] in ['up', 'down'], f"Direction should be up or down, got {delta['direction']}"
            print(f"✓ Delta structure verified: {delta['field']} ({delta['previous']} → {delta['current']})")
        else:
            print("⚠ No deltas to verify structure (comparison may not have changes)")
    
    def test_compare_404_for_invalid_campaign(self):
        """Test that compare returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/invalid-campaign-id/customer-intel/compare")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ compare returns 404 for invalid campaign")


class TestProgressEndpoints:
    """Module run progress endpoint tests"""
    
    def test_customer_intel_progress(self):
        """Test customer-intel progress endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/progress")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'status' in data, "Response should have status field"
        assert 'events' in data, "Response should have events field"
        assert 'progress_pct' in data, "Response should have progress_pct field"
        print(f"✓ customer-intel progress: status={data['status']}, pct={data['progress_pct']}, events={len(data['events'])}")
    
    def test_search_intent_progress(self):
        """Test search-intent progress endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/progress")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'status' in data, "Response should have status field"
        print(f"✓ search-intent progress: status={data['status']}")
    
    def test_progress_events_structure(self):
        """Test that progress events have correct structure"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/progress")
        data = response.json()
        
        events = data.get('events', [])
        if events:
            event = events[0]
            assert 'event' in event, "Event should have event name"
            assert 'timestamp' in event, "Event should have timestamp"
            print(f"✓ Event structure verified: {event['event']} at {event['timestamp']}")
        else:
            print("⚠ No events to verify structure")
    
    def test_progress_returns_data_for_non_running_module(self):
        """Test that progress endpoint works even for completed modules"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/progress")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should return either COMPLETED status or historical events
        print(f"✓ progress works for non-running module: status={data.get('status')}")


class TestExistingEndpoints:
    """Regression tests for Phase 2+3 endpoints"""
    
    def test_research_pack_endpoint(self):
        """Test research pack endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_data' in data, "Response should have has_data field"
        print(f"✓ Research pack endpoint works: has_data={data['has_data']}")
    
    def test_customer_intel_latest(self):
        """Test customer intel latest endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_data' in data, "Response should have has_data field"
        print(f"✓ customer-intel/latest works: has_data={data['has_data']}")
    
    def test_seasonality_latest(self):
        """Test seasonality latest endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_data' in data, "Response should have has_data field"
        print(f"✓ seasonality/latest works: has_data={data['has_data']}")
    
    def test_search_intent_latest(self):
        """Test search intent latest endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_data' in data, "Response should have has_data field"
        print(f"✓ search-intent/latest works: has_data={data['has_data']}")
    
    def test_competitors_latest(self):
        """Test competitors latest endpoint"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert 'has_data' in data, "Response should have has_data field"
        print(f"✓ competitors/latest works: has_data={data['has_data']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
