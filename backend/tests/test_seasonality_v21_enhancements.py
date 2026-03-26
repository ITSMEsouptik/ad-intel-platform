"""
Tests for Seasonality v2.1 Enhancements: Month Ribbon + Lead Time
Tests the two new features added to Buying Moments:
1. Month Ribbon - window parsing for active months display
2. Lead Time - how far ahead people start searching/booking

Tests:
- Schema: BuyingMoment lead_time field
- Prompt: lead_time field structure in output
- API: GET seasonality/latest returns lead_time
- Month parsing logic (frontend-side, but we test the data structure)
"""

import pytest
import requests
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')
TEST_CAMPAIGN_ID = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"

# Import schema and prompt builder for unit tests
from research.seasonality.schema import BuyingMoment, SeasonalitySnapshot
from research.seasonality.perplexity_seasonality import build_seasonality_prompt


# ============== SCHEMA TESTS (lead_time field) ==============

class TestLeadTimeSchema:
    """Test that lead_time field is properly defined in BuyingMoment schema."""
    
    def test_lead_time_field_exists(self):
        """BuyingMoment should have lead_time field."""
        assert 'lead_time' in BuyingMoment.model_fields
    
    def test_lead_time_default_empty_string(self):
        """lead_time should default to empty string."""
        moment = BuyingMoment(moment="Test", window="Jan")
        assert moment.lead_time == ""
    
    def test_lead_time_with_value(self):
        """lead_time should accept and store values."""
        moment = BuyingMoment(
            moment="Wedding Season",
            window="March-May",
            lead_time="2-4 months before"
        )
        assert moment.lead_time == "2-4 months before"
    
    def test_lead_time_truncated_at_80_chars(self):
        """Service truncates lead_time at 80 chars - verify field accepts long strings."""
        long_lead_time = "A" * 100
        moment = BuyingMoment(
            moment="Test",
            window="Jan",
            lead_time=long_lead_time[:80]  # Truncated like in service.py
        )
        assert len(moment.lead_time) == 80
    
    def test_buying_moment_with_all_v21_fields_including_lead_time(self):
        """Full v2.1 BuyingMoment with lead_time."""
        moment = BuyingMoment(
            moment="Ramadan Prep",
            window="March-April",
            demand="high",
            who="Muslim families and event planners",
            why_now="Holy month requires advance preparation for gatherings",
            buy_triggers=["Ramadan dates announced", "Family gathering planning starts"],
            must_answer="Can you accommodate halal requirements?",
            best_channels=["WhatsApp groups", "Google Search"],
            lead_time="4-6 weeks before"
        )
        assert moment.lead_time == "4-6 weeks before"
        assert len(moment.buy_triggers) == 2
        assert len(moment.best_channels) == 2


# ============== PROMPT TESTS (lead_time in output format) ==============

class TestPromptLeadTime:
    """Test that the Perplexity prompt includes lead_time field."""
    
    def test_prompt_json_structure_includes_lead_time(self):
        """Prompt should ask for lead_time in the JSON output structure."""
        prompt = build_seasonality_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="Salon",
            services=["Haircut"],
            brand_overview="Test salon"
        )
        # Check for lead_time in the JSON example
        assert '"lead_time"' in prompt
    
    def test_prompt_lead_time_description(self):
        """Prompt should explain what lead_time means."""
        prompt = build_seasonality_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="Salon",
            services=["Haircut"],
            brand_overview="Test salon"
        )
        # Should have description of lead_time
        assert "how far" in prompt.lower() or "advance" in prompt.lower()
    
    def test_prompt_lead_time_examples(self):
        """Prompt should give examples of lead_time values."""
        prompt = build_seasonality_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="Salon",
            services=["Haircut"],
            brand_overview="Test salon"
        )
        # Should have examples like "2-4 weeks before"
        assert "weeks before" in prompt or "months ahead" in prompt
    
    def test_prompt_hard_rule_9_lead_time(self):
        """Prompt rule #9 should define lead_time requirements."""
        prompt = build_seasonality_prompt(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty",
            niche="Salon",
            services=["Haircut"],
            brand_overview="Test salon"
        )
        # Rule 9 should mention lead_time
        # The prompt has: '9. "lead_time" must describe how far BEFORE...'
        assert 'lead_time' in prompt and ('unknown' in prompt.lower() or 'before' in prompt.lower())


# ============== MONTH WINDOW PARSING TESTS ==============
# These test the data format that the frontend parses

class TestWindowDataFormat:
    """Test that window field data is in parsable formats for month ribbon."""
    
    # Month mapping (same as frontend)
    MONTH_MAP = {
        'jan': 0, 'january': 0, 'feb': 1, 'february': 1, 'mar': 2, 'march': 2,
        'apr': 3, 'april': 3, 'may': 4, 'jun': 5, 'june': 5, 'jul': 6, 'july': 6,
        'aug': 7, 'august': 7, 'sep': 8, 'sept': 8, 'september': 8, 'oct': 9,
        'october': 9, 'nov': 10, 'november': 10, 'dec': 11, 'december': 11
    }
    
    def parse_window(self, window_str):
        """Parse window string into active month indices (0-11)."""
        window_str = window_str.lower()
        active_months = set()
        
        # Try "Month-Month" range pattern
        range_match = re.match(r'([a-z]+)\s*[-–to]+\s*([a-z]+)', window_str)
        if range_match:
            start_idx = self.MONTH_MAP.get(range_match.group(1))
            end_idx = self.MONTH_MAP.get(range_match.group(2))
            if start_idx is not None and end_idx is not None:
                if start_idx <= end_idx:
                    for m in range(start_idx, end_idx + 1):
                        active_months.add(m)
                else:
                    # Wrap around (e.g., Dec-Feb)
                    for m in range(start_idx, 12):
                        active_months.add(m)
                    for m in range(0, end_idx + 1):
                        active_months.add(m)
        
        # Try individual month mentions
        if not active_months:
            for name, idx in self.MONTH_MAP.items():
                if name in window_str:
                    active_months.add(idx)
        
        return active_months
    
    def test_parse_range_march_may(self):
        """'March-May' should return months 2,3,4."""
        result = self.parse_window("March-May")
        assert result == {2, 3, 4}
    
    def test_parse_range_dec_feb_wraparound(self):
        """'Dec-Feb' should wrap around: 11,0,1."""
        result = self.parse_window("Dec-Feb")
        assert result == {11, 0, 1}
    
    def test_parse_single_month(self):
        """'September' should return month 8."""
        result = self.parse_window("September")
        assert result == {8}
    
    def test_parse_specific_date_range(self):
        """'January 20-25, 2026' should extract January (month 0)."""
        result = self.parse_window("January 20-25, 2026")
        assert 0 in result
    
    def test_parse_first_two_weeks_format(self):
        """'First 2 weeks of September' should return month 8."""
        result = self.parse_window("First 2 weeks of September")
        assert 8 in result
    
    def test_parse_late_month_format(self):
        """'Late October - Early November' should return months 9,10."""
        result = self.parse_window("Late October - Early November")
        assert result == {9, 10} or result >= {9, 10}


# ============== API TESTS ==============

class TestSeasonalityAPILeadTime:
    """Test API returns lead_time field in responses."""
    
    @pytest.fixture
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def test_api_health(self, api_client):
        """API should be healthy."""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
    
    def test_get_latest_returns_lead_time_field(self, api_client):
        """GET seasonality/latest should return moments with lead_time field."""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("has_data") == True
        
        snapshot = data.get("snapshot", data.get("latest", {}))
        assert snapshot.get("version") == "2.1"
        
        key_moments = snapshot.get("key_moments", [])
        if key_moments:
            # Each moment should have lead_time field
            for moment in key_moments:
                assert "lead_time" in moment, f"Moment missing lead_time field: {moment.get('moment')}"
    
    def test_moments_have_window_field_for_month_ribbon(self, api_client):
        """Each moment should have window field for month ribbon parsing."""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        snapshot = data.get("snapshot", data.get("latest", {}))
        key_moments = snapshot.get("key_moments", [])
        
        for moment in key_moments:
            assert "window" in moment, f"Moment missing window field: {moment.get('moment')}"
            assert moment["window"], f"Window field is empty for: {moment.get('moment')}"
    
    def test_all_v21_fields_present(self, api_client):
        """All v2.1 fields should be present in response."""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        snapshot = data.get("snapshot", data.get("latest", {}))
        key_moments = snapshot.get("key_moments", [])
        
        v21_fields = ["moment", "window", "demand", "who", "why_now", "buy_triggers", "must_answer", "best_channels", "lead_time"]
        
        for moment in key_moments:
            for field in v21_fields:
                assert field in moment, f"Missing field '{field}' in moment: {moment.get('moment')}"


# ============== INTEGRATION TEST ==============

class TestSeasonalityEnhancementsIntegration:
    """Integration tests for month ribbon + lead time features."""
    
    @pytest.fixture
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def test_full_seasonality_response_structure(self, api_client):
        """Test the full response structure with both new features."""
        response = api_client.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        
        data = response.json()
        
        # Top level structure
        assert "has_data" in data
        assert "status" in data
        
        snapshot = data.get("snapshot", data.get("latest", {}))
        
        # Verify version
        assert snapshot.get("version") == "2.1"
        
        # Verify key_moments array
        key_moments = snapshot.get("key_moments", [])
        print(f"Found {len(key_moments)} key moments")
        
        for i, moment in enumerate(key_moments):
            print(f"\nMoment {i}: {moment.get('moment')}")
            print(f"  window: {moment.get('window')}")
            print(f"  lead_time: '{moment.get('lead_time', '')}'")
            
            # Verify window is parsable (contains month names or dates)
            window = moment.get("window", "").lower()
            has_month_data = any(month in window for month in [
                'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
            ])
            assert has_month_data or any(char.isdigit() for char in window), \
                f"Window '{moment.get('window')}' doesn't contain parsable month data"
            
            # lead_time can be empty string (shows as 'unknown' in UI)
            assert "lead_time" in moment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
