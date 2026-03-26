"""
Tests for Wizard Redesign:
1. POST /api/campaign-briefs accepts minimal payload {website_url, country}
2. POST /api/campaign-briefs auto-fills contact from authenticated user
3. PATCH /api/campaign-briefs/{id} updates optional fields
4. PATCH /api/campaign-briefs/{id} returns 404 for invalid ID
5. PATCH /api/campaign-briefs/{id} returns 400 when no fields provided
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMinimalBriefCreation:
    """Tests for minimal brief creation (URL + Country only)."""
    
    def test_create_brief_with_minimal_payload(self):
        """POST /api/campaign-briefs accepts minimal payload {website_url, country}."""
        payload = {
            "website_url": "example.com",
            "country": "United States"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "campaign_brief_id" in data
        assert "brand" in data
        assert "geo" in data
        assert "goal" in data
        assert "destination" in data
        
        # Verify input values
        assert data["brand"]["website_url"].endswith("example.com")
        assert data["geo"]["country"] == "United States"
        
        # Verify sensible defaults
        assert data["goal"]["primary_goal"] in ["sales_orders", "bookings_leads", "brand_awareness", "event_launch"]
        assert data["destination"]["type"] in ["website", "whatsapp", "booking_link", "app", "dm", "other"]
        assert data["track"] in ["pilot", "foundation"]
        
        # Store brief_id for cleanup
        self.brief_id = data["campaign_brief_id"]
        return data["campaign_brief_id"]
    
    def test_create_brief_normalizes_url(self):
        """Website URL should be normalized to include https://."""
        payload = {
            "website_url": "testsite.com",
            "country": "United Kingdom"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # URL should be normalized
        assert data["brand"]["website_url"].startswith("https://")
    
    def test_create_brief_with_all_optional_fields(self):
        """POST /api/campaign-briefs accepts all optional fields."""
        payload = {
            "website_url": "fullexample.com",
            "country": "Germany",
            "city_or_region": "Berlin",
            "primary_goal": "sales_orders",
            "success_definition": "Increase conversions by 20%",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "1000-5000",
            "name": "Test User",
            "email": "test@example.com"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify optional fields were saved
        assert data["geo"]["city_or_region"] == "Berlin"
        assert data["goal"]["primary_goal"] == "sales_orders"
        assert data["goal"]["success_definition"] == "Increase conversions by 20%"
        assert data["destination"]["type"] == "website"
        assert data["ads_intent"] == "yes"
        assert data["budget_range_monthly"] == "1000-5000"
        assert data["contact"]["name"] == "Test User"
        assert data["contact"]["email"] == "test@example.com"


class TestBriefUpdate:
    """Tests for PATCH /api/campaign-briefs/{id} endpoint."""
    
    @pytest.fixture(autouse=True)
    def setup_brief(self):
        """Create a brief for testing updates."""
        payload = {
            "website_url": f"testupdate-{uuid.uuid4().hex[:8]}.com",
            "country": "France"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        assert response.status_code == 200
        self.brief_id = response.json()["campaign_brief_id"]
        yield
        # No explicit cleanup needed for this test
    
    def test_patch_updates_city_or_region(self):
        """PATCH updates city_or_region field."""
        update_payload = {"city_or_region": "Paris"}
        response = requests.patch(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}", json=update_payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.json()["status"] == "updated"
        
        # Verify update was persisted
        get_response = requests.get(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}")
        assert get_response.status_code == 200
        assert get_response.json()["geo"]["city_or_region"] == "Paris"
    
    def test_patch_updates_primary_goal(self):
        """PATCH updates primary_goal field."""
        update_payload = {"primary_goal": "brand_awareness"}
        response = requests.patch(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}", json=update_payload)
        
        assert response.status_code == 200
        
        # Verify update was persisted
        get_response = requests.get(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}")
        assert get_response.status_code == 200
        assert get_response.json()["goal"]["primary_goal"] == "brand_awareness"
    
    def test_patch_updates_destination_type(self):
        """PATCH updates destination_type field."""
        update_payload = {"destination_type": "whatsapp"}
        response = requests.patch(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}", json=update_payload)
        
        assert response.status_code == 200
        
        # Verify update was persisted
        get_response = requests.get(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}")
        assert get_response.status_code == 200
        assert get_response.json()["destination"]["type"] == "whatsapp"
    
    def test_patch_updates_success_definition(self):
        """PATCH updates success_definition field."""
        update_payload = {"success_definition": "Generate 100 leads per month"}
        response = requests.patch(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}", json=update_payload)
        
        assert response.status_code == 200
        
        # Verify update was persisted
        get_response = requests.get(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}")
        assert get_response.status_code == 200
        assert get_response.json()["goal"]["success_definition"] == "Generate 100 leads per month"
    
    def test_patch_updates_multiple_fields(self):
        """PATCH updates multiple fields at once."""
        update_payload = {
            "city_or_region": "Lyon",
            "primary_goal": "event_launch",
            "destination_type": "booking_link"
        }
        response = requests.patch(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}", json=update_payload)
        
        assert response.status_code == 200
        
        # Verify all updates persisted
        get_response = requests.get(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["geo"]["city_or_region"] == "Lyon"
        assert data["goal"]["primary_goal"] == "event_launch"
        assert data["destination"]["type"] == "booking_link"
    
    def test_patch_returns_404_for_invalid_id(self):
        """PATCH returns 404 for non-existent brief ID."""
        fake_id = f"fake-{uuid.uuid4()}"
        update_payload = {"city_or_region": "Nowhere"}
        response = requests.patch(f"{BASE_URL}/api/campaign-briefs/{fake_id}", json=update_payload)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
    
    def test_patch_returns_400_when_no_fields_provided(self):
        """PATCH returns 400 when no fields provided in payload."""
        update_payload = {}
        response = requests.patch(f"{BASE_URL}/api/campaign-briefs/{self.brief_id}", json=update_payload)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "No fields to update" in response.text or "detail" in response.json()


class TestContactAutoFill:
    """Tests for contact auto-fill from authenticated user."""
    
    def test_contact_empty_for_anonymous_user(self):
        """Contact should be empty strings when no name/email provided by anonymous user."""
        payload = {
            "website_url": "anonymous-test.com",
            "country": "Canada"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Contact should be empty for anonymous
        assert data["contact"]["name"] == ""
        assert data["contact"]["email"] == ""
    
    def test_contact_uses_provided_values(self):
        """Contact should use explicitly provided name/email."""
        payload = {
            "website_url": "manual-contact.com",
            "country": "Australia",
            "name": "Manual Name",
            "email": "manual@example.com"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["contact"]["name"] == "Manual Name"
        assert data["contact"]["email"] == "manual@example.com"


class TestBriefRetrieval:
    """Tests for GET /api/campaign-briefs/{id} endpoint."""
    
    def test_get_brief_by_id(self):
        """GET returns the correct brief by ID."""
        # Create a brief first
        payload = {
            "website_url": f"retrieve-test-{uuid.uuid4().hex[:8]}.com",
            "country": "Spain",
            "city_or_region": "Madrid"
        }
        create_response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        assert create_response.status_code == 200
        brief_id = create_response.json()["campaign_brief_id"]
        
        # Retrieve the brief
        get_response = requests.get(f"{BASE_URL}/api/campaign-briefs/{brief_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["campaign_brief_id"] == brief_id
        assert data["geo"]["country"] == "Spain"
        assert data["geo"]["city_or_region"] == "Madrid"
    
    def test_get_brief_returns_404_for_invalid_id(self):
        """GET returns 404 for non-existent brief ID."""
        fake_id = f"nonexistent-{uuid.uuid4()}"
        response = requests.get(f"{BASE_URL}/api/campaign-briefs/{fake_id}")
        
        assert response.status_code == 404


class TestDefaultValues:
    """Tests for sensible default values when optional fields not provided."""
    
    def test_default_goal_is_bookings_leads(self):
        """Default primary_goal should be 'bookings_leads'."""
        payload = {
            "website_url": "default-goal-test.com",
            "country": "Italy"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["goal"]["primary_goal"] == "bookings_leads"
    
    def test_default_destination_is_website(self):
        """Default destination_type should be 'website'."""
        payload = {
            "website_url": "default-dest-test.com",
            "country": "Netherlands"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["destination"]["type"] == "website"
    
    def test_default_track_is_pilot(self):
        """Default track should be 'pilot' when ads_intent not provided."""
        payload = {
            "website_url": "default-track-test.com",
            "country": "Sweden"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["track"] == "pilot"
    
    def test_default_budget_is_not_sure(self):
        """Default budget_range_monthly should be 'not_sure'."""
        payload = {
            "website_url": "default-budget-test.com",
            "country": "Norway"
        }
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["budget_range_monthly"] == "not_sure"
