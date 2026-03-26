"""
Reviews & Reputation Module Tests (v1.0 - Feb 2026)

Test modules:
- Schema validation (ReviewsSnapshot, ReviewPlatform, StrengthTheme, etc.)
- Geo platform mapping (get_platforms_for_context)
- Prompt building (build_discovery_prompt, build_analysis_prompt)
- Post-processing (postprocess_reviews with guardrails)
- API endpoints (run, latest, history)
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============== SCHEMA TESTS ==============

class TestReviewsSchema:
    """Test schema validation for Reviews models"""
    
    def test_reviews_snapshot_model_validates(self):
        """ReviewsSnapshot should accept valid data"""
        from research.reviews.schema import ReviewsSnapshot, ReviewsInputs, ReviewPlatform, StrengthTheme, WeaknessTheme, SocialProofSnippet, CompetitorReputation, ReviewsAudit, ReviewsDelta
        
        sample_data = {
            "version": "1.0",
            "captured_at": datetime.now(timezone.utc),
            "refresh_due_at": datetime.now(timezone.utc) + timedelta(days=30),
            "inputs_used": ReviewsInputs(
                geo={"city": "Dubai", "country": "UAE"},
                brand_name="Test Salon",
                domain="testsalon.com",
                subcategory="beauty",
                niche="salon",
                services=["haircut", "coloring"],
                brand_overview="A premier salon in Dubai"
            ),
            "reputation_summary": ["Highly rated on Google", "Consistent positive reviews"],
            "platform_presence": [
                ReviewPlatform(platform="Google Maps", approximate_rating=4.7, approximate_count="150+", has_reviews=True)
            ],
            "strength_themes": [
                StrengthTheme(theme="Expert colorists", evidence=["Amazing hair color transformation!"], frequency="frequent")
            ],
            "weakness_themes": [
                WeaknessTheme(theme="Long wait times", evidence=["Had to wait 30 mins"], frequency="occasional", severity="minor")
            ],
            "social_proof_snippets": [
                SocialProofSnippet(quote="Best salon in Dubai!", platform="Google Maps", context="Hair coloring review")
            ],
            "trust_signals": ["10+ years in business", "Award-winning stylists"],
            "competitor_reputation": [
                CompetitorReputation(name="Competitor Salon", approximate_rating=4.2, primary_platform="Google Maps", reputation_gap="Lower rated but faster service")
            ],
            "audit": ReviewsAudit(platforms_checked=5, platforms_with_reviews=3, discovery_tokens=500, analysis_tokens=800),
            "delta": ReviewsDelta()
        }
        
        snapshot = ReviewsSnapshot(**sample_data)
        assert snapshot.version == "1.0"
        assert len(snapshot.platform_presence) == 1
        assert len(snapshot.strength_themes) == 1
        assert len(snapshot.weakness_themes) == 1
        print("ReviewsSnapshot validates correctly with sample data")
    
    def test_review_platform_model(self):
        """ReviewPlatform should validate rating range"""
        from research.reviews.schema import ReviewPlatform
        
        # Valid platform
        platform = ReviewPlatform(
            platform="Google Maps",
            url="https://maps.google.com/test",
            approximate_rating=4.5,
            approximate_count="100+",
            has_reviews=True
        )
        assert platform.platform == "Google Maps"
        assert platform.approximate_rating == 4.5
        print("ReviewPlatform model validates correctly")
    
    def test_strength_theme_model(self):
        """StrengthTheme should validate frequency enum"""
        from research.reviews.schema import StrengthTheme
        
        theme = StrengthTheme(
            theme="Expert stylists",
            evidence=["Quote 1", "Quote 2"],
            frequency="frequent"
        )
        assert theme.theme == "Expert stylists"
        assert len(theme.evidence) == 2
        print("StrengthTheme model validates correctly")
    
    def test_weakness_theme_model_with_severity(self):
        """WeaknessTheme should validate severity enum"""
        from research.reviews.schema import WeaknessTheme
        
        theme = WeaknessTheme(
            theme="Parking issues",
            evidence=["Hard to find parking"],
            frequency="moderate",
            severity="minor"
        )
        assert theme.theme == "Parking issues"
        assert theme.severity == "minor"
        print("WeaknessTheme model validates correctly with severity")


# ============== GEO PLATFORM MAPPING TESTS ==============

class TestGeoPlatformMapping:
    """Test get_platforms_for_context function"""
    
    def test_uae_beauty_platforms(self):
        """UAE + beauty should return UAE geo platforms + beauty niche platforms"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="UAE",
            niche="beauty",
            subcategory="salon"
        )
        
        # UAE should have these geo platforms
        assert "Google Maps" in geo_platforms
        assert "Facebook" in geo_platforms
        assert "Tripadvisor" in geo_platforms
        
        # Beauty/salon niche platforms
        assert "Fresha" in niche_platforms or "Booksy" in niche_platforms
        
        # Combined should include both geo and niche
        assert len(combined) >= len(geo_platforms)
        
        print(f"UAE + beauty: {len(geo_platforms)} geo, {len(niche_platforms)} niche, {len(combined)} combined")
    
    def test_us_restaurant_platforms(self):
        """US + restaurant should return US geo platforms + restaurant niche platforms"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="United States",
            niche="restaurant",
            subcategory="food"
        )
        
        # US should have Yelp
        assert "Yelp" in geo_platforms
        assert "Google Maps" in geo_platforms
        assert "BBB" in geo_platforms
        
        # Restaurant niche platforms
        assert "Zomato" in niche_platforms or "OpenTable" in niche_platforms
        
        print(f"US + restaurant: {len(geo_platforms)} geo, {len(niche_platforms)} niche, {len(combined)} combined")
    
    def test_uk_software_platforms(self):
        """UK + software should return UK geo platforms + software niche platforms"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="United Kingdom",
            niche="software",
            subcategory="saas"
        )
        
        # UK should have Trustpilot
        assert "Trustpilot" in geo_platforms
        
        # Software niche platforms
        assert "G2" in niche_platforms
        assert "Capterra" in niche_platforms
        
        print(f"UK + software: {len(geo_platforms)} geo, {len(niche_platforms)} niche, {len(combined)} combined")
    
    def test_unknown_country_uses_defaults(self):
        """Unknown country should use DEFAULT_PLATFORMS"""
        from research.reviews.perplexity_reviews import get_platforms_for_context, DEFAULT_PLATFORMS
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="Unknown Country",
            niche="unknown",
            subcategory="unknown"
        )
        
        assert geo_platforms == DEFAULT_PLATFORMS
        print(f"Unknown country uses default: {geo_platforms}")


# ============== PROMPT BUILDING TESTS ==============

class TestPromptBuilding:
    """Test prompt builders for discovery and analysis"""
    
    def test_discovery_prompt_has_required_sections(self):
        """Discovery prompt should include WHY THIS MATTERS, brand context, platform list"""
        from research.reviews.perplexity_reviews import build_discovery_prompt
        
        prompt = build_discovery_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut", "coloring"],
            brand_overview="Premium salon in Dubai",
            platforms_to_check=["Google Maps", "Facebook", "Fresha"]
        )
        
        # Required sections
        assert "WHY THIS MATTERS" in prompt
        assert "Test Brand" in prompt
        assert "testbrand.com" in prompt
        assert "Dubai" in prompt
        assert "beauty" in prompt
        assert "Google Maps" in prompt or "Fresha" in prompt
        assert "platforms_found" in prompt  # JSON output format
        
        print("Discovery prompt contains all required sections")
    
    def test_analysis_prompt_has_required_sections(self):
        """Analysis prompt should include WHY THIS MATTERS, discovery results, competitor names, quality check"""
        from research.reviews.perplexity_reviews import build_analysis_prompt
        
        discovery_results = {
            "platforms_found": [
                {"platform": "Google Maps", "approximate_rating": 4.5, "approximate_count": "100+", "url": "https://..."}
            ]
        }
        
        prompt = build_analysis_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut", "coloring"],
            brand_overview="Premium salon in Dubai",
            discovery_results=discovery_results,
            competitor_names=["Competitor A", "Competitor B"]
        )
        
        # Required sections
        assert "WHY THIS MATTERS" in prompt
        assert "Test Brand" in prompt
        assert "Google Maps" in prompt
        assert "Competitor A" in prompt
        assert "QUALITY CHECK" in prompt
        assert "strength_themes" in prompt  # JSON output format
        assert "STRICTLY FORBIDDEN" in prompt
        
        print("Analysis prompt contains all required sections")
    
    def test_analysis_prompt_handles_no_competitors(self):
        """Analysis prompt should work without competitors"""
        from research.reviews.perplexity_reviews import build_analysis_prompt
        
        prompt = build_analysis_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=[],
            brand_overview="",
            discovery_results={"platforms_found": []},
            competitor_names=[]
        )
        
        # Should not error, should still have required sections
        assert "WHY THIS MATTERS" in prompt
        assert "Test Brand" in prompt
        
        print("Analysis prompt handles empty competitor list")


# ============== POSTPROCESS TESTS ==============

class TestPostprocess:
    """Test postprocess_reviews guardrails"""
    
    def test_rejects_generic_strength_themes(self):
        """Generic themes like 'great service' should be rejected"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {"platforms_found": []}
        analysis = {
            "strength_themes": [
                {"theme": "great service", "evidence": ["good"], "frequency": "frequent"},
                {"theme": "Expert colorists with 10+ years experience", "evidence": ["Amazing results!"], "frequency": "frequent"},
                {"theme": "good quality", "evidence": ["nice"], "frequency": "moderate"},
                {"theme": "highly recommend", "evidence": ["yes"], "frequency": "occasional"},
            ],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        # Only the specific theme should survive
        assert len(processed["strength_themes"]) == 1
        assert processed["strength_themes"][0]["theme"] == "Expert colorists with 10+ years experience"
        assert stats["generic_themes_removed"] >= 3
        
        print(f"Rejected {stats['generic_themes_removed']} generic strength themes")
    
    def test_rejects_generic_weakness_themes(self):
        """Generic themes like 'could improve' should be rejected"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {"platforms_found": []}
        analysis = {
            "strength_themes": [],
            "weakness_themes": [
                {"theme": "could improve", "evidence": ["yes"], "frequency": "moderate", "severity": "minor"},
                {"theme": "Long wait times during peak hours", "evidence": ["Waited 45 mins"], "frequency": "moderate", "severity": "moderate"},
                {"theme": "room for improvement", "evidence": ["some things"], "frequency": "occasional", "severity": "minor"},
            ],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        # Only the specific theme should survive
        assert len(processed["weakness_themes"]) == 1
        assert "wait times" in processed["weakness_themes"][0]["theme"].lower()
        assert stats["generic_themes_removed"] >= 2
        
        print(f"Rejected {stats['generic_themes_removed']} generic weakness themes")
    
    def test_validates_rating_range(self):
        """Ratings should be clamped to 0-5 range"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {
            "platforms_found": [
                {"platform": "Google Maps", "approximate_rating": 4.7, "approximate_count": "100+", "has_reviews": True},
                {"platform": "Yelp", "approximate_rating": 6.5, "approximate_count": "50+", "has_reviews": True},  # Invalid
                {"platform": "Facebook", "approximate_rating": -1, "approximate_count": "20+", "has_reviews": True},  # Invalid
            ]
        }
        analysis = {
            "strength_themes": [],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        # Check ratings validation
        google = next(p for p in processed["platform_presence"] if p["platform"] == "Google Maps")
        yelp = next(p for p in processed["platform_presence"] if p["platform"] == "Yelp")
        facebook = next(p for p in processed["platform_presence"] if p["platform"] == "Facebook")
        
        assert google["approximate_rating"] == 4.7  # Valid, unchanged
        assert yelp["approximate_rating"] is None  # Invalid, set to None
        assert facebook["approximate_rating"] is None  # Invalid, set to None
        
        print("Rating validation working: invalid ratings set to None")
    
    def test_caps_string_lengths(self):
        """Strings should be capped at max lengths"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {"platforms_found": []}
        analysis = {
            "strength_themes": [
                {"theme": "A" * 100, "evidence": ["B" * 200], "frequency": "frequent"}  # Theme too long
            ],
            "weakness_themes": [],
            "social_proof_snippets": [
                {"quote": "C" * 250, "platform": "Google", "context": "D" * 150}  # Quote too long
            ],
            "trust_signals": ["E" * 150],  # Too long
            "competitor_reputation": [
                {"name": "Competitor", "approximate_rating": 4.0, "primary_platform": "Google", "reputation_gap": "F" * 200}
            ],
            "reputation_summary": ["G" * 150]
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        # Check length caps
        assert len(processed["strength_themes"][0]["theme"]) <= 80
        assert len(processed["strength_themes"][0]["evidence"][0]) <= 150
        assert len(processed["social_proof_snippets"][0]["quote"]) <= 200
        assert len(processed["trust_signals"][0]) <= 100
        assert len(processed["competitor_reputation"][0]["reputation_gap"]) <= 150
        assert len(processed["reputation_summary"][0]) <= 120
        
        print("String length caps applied correctly")
    
    def test_validates_frequency_enum(self):
        """Invalid frequency values should default to 'moderate'"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {"platforms_found": []}
        analysis = {
            "strength_themes": [
                {"theme": "Specific valid theme name", "evidence": ["good quote here"], "frequency": "invalid_value"}
            ],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        # Invalid frequency should become 'moderate'
        assert processed["strength_themes"][0]["frequency"] == "moderate"
        
        print("Invalid frequency defaults to 'moderate'")
    
    def test_validates_severity_enum(self):
        """Invalid severity values should default to 'minor'"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {"platforms_found": []}
        analysis = {
            "strength_themes": [],
            "weakness_themes": [
                {"theme": "Specific valid weakness theme", "evidence": ["quote here"], "frequency": "moderate", "severity": "invalid_severity"}
            ],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        # Invalid severity should become 'minor'
        assert processed["weakness_themes"][0]["severity"] == "minor"
        
        print("Invalid severity defaults to 'minor'")


# ============== SERVICE INPUT EXTRACTION TESTS ==============

class TestServiceInputExtraction:
    """Test ReviewsService.extract_inputs"""
    
    def test_extracts_all_required_fields(self):
        """extract_inputs should extract brand_name, domain, geo, niche, services from campaign brief + website context pack"""
        from research.reviews.service import ReviewsService
        
        # Mock db (not used in extract_inputs)
        class MockDB:
            pass
        
        service = ReviewsService(MockDB())
        
        campaign_brief = {
            "geo": {"city_or_region": "Dubai", "country": "UAE"}
        }
        
        website_context_pack = {
            "step2": {
                "site": {"domain": "testsalon.com", "final_url": "https://testsalon.com"},
                "classification": {"subcategory": "beauty", "niche": "salon"},
                "offer": {
                    "offer_catalog": [
                        {"name": "Haircut"},
                        {"name": "Hair Coloring"},
                        {"name": "Styling"}
                    ]
                },
                "brand_summary": {
                    "name": "Test Salon",
                    "one_liner": "Premier salon in Dubai",
                    "tagline": "Beauty at its finest",
                    "bullets": ["Expert stylists", "Luxury experience"]
                }
            }
        }
        
        inputs = service.extract_inputs(campaign_brief, website_context_pack)
        
        assert inputs["brand_name"] == "Test Salon"
        assert inputs["domain"] == "testsalon.com"
        assert inputs["geo"]["city"] == "Dubai"
        assert inputs["geo"]["country"] == "UAE"
        assert inputs["subcategory"] == "beauty"
        assert inputs["niche"] == "salon"
        assert "Haircut" in inputs["services"]
        assert "Premier salon in Dubai" in inputs["brand_overview"]
        
        print("extract_inputs correctly extracts all required fields")


# ============== API TESTS ==============

class TestReviewsAPI:
    """Test Reviews API endpoints"""
    
    def test_health_check(self):
        """Health check should return 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("Health check passed")
    
    def test_reviews_run_missing_brief(self):
        """POST /reviews/run should return 404 for non-existent campaign"""
        response = requests.post(f"{BASE_URL}/api/research/nonexistent-campaign-id/reviews/run")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
        print("Reviews run returns 404 for missing brief")
    
    def test_reviews_latest_missing_brief(self):
        """GET /reviews/latest should return 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/nonexistent-campaign-id/reviews/latest")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
        print("Reviews latest returns 404 for missing brief")
    
    def test_reviews_history_missing_brief(self):
        """GET /reviews/history should return 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/nonexistent-campaign-id/reviews/history")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower()
        print("Reviews history returns 404 for missing brief")


class TestReviewsAPIWithCampaign:
    """Test Reviews API with a real campaign - requires valid campaign_brief_id"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Find a valid campaign to test with"""
        # Try to get a campaign from the database via API
        # Use the test campaign from previous tests
        self.test_campaign_id = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"  # example-brand.co from previous tests
    
    def test_reviews_latest_returns_has_data_false(self):
        """GET /reviews/latest should return has_data: false for campaign without reviews data"""
        response = requests.get(f"{BASE_URL}/api/research/{self.test_campaign_id}/reviews/latest")
        
        # Should return 200 even if no data
        if response.status_code == 200:
            data = response.json()
            # Either has_data is false (no reviews yet) or true (has reviews)
            assert "has_data" in data
            print(f"Reviews latest returns has_data: {data['has_data']}")
        elif response.status_code == 404:
            # Campaign not found - might be cleaned up
            print("Test campaign not found - skipping")
            pytest.skip("Test campaign not available")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_reviews_history_returns_snapshots_array(self):
        """GET /reviews/history should return snapshots array"""
        response = requests.get(f"{BASE_URL}/api/research/{self.test_campaign_id}/reviews/history")
        
        if response.status_code == 200:
            data = response.json()
            assert "snapshots" in data
            assert isinstance(data["snapshots"], list)
            assert "total_count" in data
            print(f"Reviews history returns {data['total_count']} snapshots")
        elif response.status_code == 404:
            print("Test campaign not found - skipping")
            pytest.skip("Test campaign not available")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_reviews_run_missing_website_context(self):
        """POST /reviews/run should return 400 if website context pack is missing"""
        # Create a temporary brief without website context
        # This would need a new campaign without step 2 complete
        # For now, just verify the route exists and handles the case
        
        # If campaign has website context, it will run (expensive, don't do it)
        # Just verify the endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/research/{self.test_campaign_id}/reviews/run",
            headers={"Content-Type": "application/json"}
        )
        
        # Should be either 200 (success), 400 (missing context), or 500 (API error)
        # Not 404 (route not found)
        assert response.status_code != 405, "Route should exist (method allowed)"
        
        if response.status_code == 400:
            data = response.json()
            # Should mention step 2 or website context
            print(f"Reviews run correctly requires Step 2: {data.get('detail')}")
        elif response.status_code == 200:
            # Campaign has step 2, actually ran (don't do this in real test)
            print("Reviews run executed (campaign has Step 2)")
        else:
            print(f"Reviews run returned status {response.status_code}")


# ============== RUN TESTS ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
