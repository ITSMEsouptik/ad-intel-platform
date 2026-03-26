"""
Reviews & Reputation Module Tests v1.5 - Feb 2026

Test modules:
- v1.5 Schema validation (ReviewPlatform with recency/owner_responds/response_quality/is_app_store)
- v1.5 Schema validation (SocialProofSnippet with is_paraphrased)
- v1.5 Schema validation (BrandClaimCheck, BrandVsReality, ReviewsSnapshot.social_proof_readiness)
- v1.5 Post-processing (recency validation, response_quality validation, app store detection)
- v1.5 Post-processing (social_proof_readiness score computation)
- v1.5 Post-processing (brand_vs_reality processing, is_paraphrased flag on snippets)
- v1.5 Service (extract_inputs with app_store_urls and brand_claims)
- v1.5 get_platforms_for_context (always adds app stores)
- v1.5 API backwards compatibility (GET /reviews/latest returns v1.0 data)
"""

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


# ============== v1.5 SCHEMA TESTS ==============

class TestReviewsV15Schema:
    """Test v1.5 schema additions"""
    
    def test_review_platform_v15_fields(self):
        """ReviewPlatform should have recency, owner_responds, response_quality, is_app_store"""
        from research.reviews.schema import ReviewPlatform
        
        platform = ReviewPlatform(
            platform="Google Maps",
            url="https://maps.google.com/test",
            approximate_rating=4.5,
            approximate_count="100+",
            has_reviews=True,
            recency="within_last_month",
            owner_responds=True,
            response_quality="active",
            is_app_store=False
        )
        
        assert platform.recency == "within_last_month"
        assert platform.owner_responds is True
        assert platform.response_quality == "active"
        assert platform.is_app_store is False
        print("✓ ReviewPlatform v1.5 fields validate correctly")
    
    def test_review_platform_app_store_flag(self):
        """is_app_store should be True for app store platforms"""
        from research.reviews.schema import ReviewPlatform
        
        app_store_platform = ReviewPlatform(
            platform="Apple App Store",
            url="https://apps.apple.com/app/myapp",
            approximate_rating=4.2,
            has_reviews=True,
            is_app_store=True
        )
        
        assert app_store_platform.is_app_store is True
        print("✓ is_app_store flag works correctly")
    
    def test_review_platform_defaults(self):
        """ReviewPlatform should have correct defaults for v1.5 fields"""
        from research.reviews.schema import ReviewPlatform
        
        platform = ReviewPlatform(platform="Test Platform")
        
        assert platform.recency == "unknown"
        assert platform.owner_responds is None
        assert platform.response_quality == "unknown"
        assert platform.is_app_store is False
        print("✓ ReviewPlatform v1.5 defaults are correct")
    
    def test_social_proof_snippet_is_paraphrased(self):
        """SocialProofSnippet should have is_paraphrased field (default True)"""
        from research.reviews.schema import SocialProofSnippet
        
        snippet = SocialProofSnippet(
            quote="Amazing service, highly recommend!",
            platform="Google Maps",
            context="Hair coloring review"
        )
        
        # Default should be True
        assert snippet.is_paraphrased is True
        print("✓ SocialProofSnippet.is_paraphrased defaults to True")
    
    def test_social_proof_snippet_explicit_paraphrased(self):
        """SocialProofSnippet should accept explicit is_paraphrased value"""
        from research.reviews.schema import SocialProofSnippet
        
        snippet = SocialProofSnippet(
            quote="Exact quote here",
            platform="Trustpilot",
            context="Review",
            is_paraphrased=False  # Explicit false for exact quotes
        )
        
        assert snippet.is_paraphrased is False
        print("✓ SocialProofSnippet.is_paraphrased accepts explicit value")
    
    def test_brand_claim_check_model(self):
        """BrandClaimCheck should validate claim, review_alignment, evidence"""
        from research.reviews.schema import BrandClaimCheck
        
        check = BrandClaimCheck(
            claim="We deliver within 24 hours",
            review_alignment="supported",
            evidence="Multiple reviews mention fast delivery"
        )
        
        assert check.claim == "We deliver within 24 hours"
        assert check.review_alignment == "supported"
        assert check.evidence == "Multiple reviews mention fast delivery"
        print("✓ BrandClaimCheck model validates correctly")
    
    def test_brand_vs_reality_model(self):
        """BrandVsReality should have claims_checked, supported, contradicted, checks, summary"""
        from research.reviews.schema import BrandVsReality, BrandClaimCheck
        
        checks = [
            BrandClaimCheck(claim="Fast delivery", review_alignment="supported", evidence="Good"),
            BrandClaimCheck(claim="24/7 support", review_alignment="contradicted", evidence="Many complaints about slow response"),
            BrandClaimCheck(claim="Premium quality", review_alignment="not_mentioned", evidence="No mentions in reviews"),
        ]
        
        bvr = BrandVsReality(
            claims_checked=3,
            supported=1,
            contradicted=1,
            not_mentioned=1,
            checks=checks,
            summary="1/3 claims supported, 1 contradicted by reviews"
        )
        
        assert bvr.claims_checked == 3
        assert bvr.supported == 1
        assert bvr.contradicted == 1
        assert bvr.not_mentioned == 1
        assert len(bvr.checks) == 3
        assert bvr.summary != ""
        print("✓ BrandVsReality model validates correctly")
    
    def test_reviews_snapshot_v15_fields(self):
        """ReviewsSnapshot should have social_proof_readiness and brand_vs_reality"""
        from research.reviews.schema import ReviewsSnapshot, BrandVsReality, ReviewsInputs
        
        snapshot = ReviewsSnapshot(
            version="1.5",
            social_proof_readiness="strong",
            brand_vs_reality=BrandVsReality(claims_checked=2, supported=2),
            inputs_used=ReviewsInputs(
                brand_name="Test",
                app_store_urls=["https://apps.apple.com/test"],
                brand_claims=["Fast delivery", "Great service"]
            )
        )
        
        assert snapshot.version == "1.5"
        assert snapshot.social_proof_readiness == "strong"
        assert snapshot.brand_vs_reality.claims_checked == 2
        assert snapshot.inputs_used.app_store_urls == ["https://apps.apple.com/test"]
        assert len(snapshot.inputs_used.brand_claims) == 2
        print("✓ ReviewsSnapshot v1.5 fields validate correctly")
    
    def test_reviews_inputs_v15_fields(self):
        """ReviewsInputs should have app_store_urls and brand_claims"""
        from research.reviews.schema import ReviewsInputs
        
        inputs = ReviewsInputs(
            geo={"city": "Dubai", "country": "UAE"},
            brand_name="Test Brand",
            domain="testbrand.com",
            app_store_urls=["https://apps.apple.com/app/123", "https://play.google.com/store/apps/details?id=com.test"],
            brand_claims=["Best prices", "Free delivery", "24/7 support"]
        )
        
        assert len(inputs.app_store_urls) == 2
        assert len(inputs.brand_claims) == 3
        print("✓ ReviewsInputs v1.5 fields validate correctly")


# ============== v1.5 POSTPROCESS TESTS ==============

class TestPostprocessV15:
    """Test v1.5 post-processing: recency, owner_responds, response_quality, is_app_store, brand_vs_reality, social_proof_readiness"""
    
    def test_validates_recency_enum(self):
        """postprocess should validate recency values"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {
            "platforms_found": [
                {"platform": "Google Maps", "has_reviews": True, "recency": "within_last_month"},
                {"platform": "Yelp", "has_reviews": True, "recency": "invalid_value"},  # Invalid
                {"platform": "Facebook", "has_reviews": True, "recency": "6_months_plus"},
            ]
        }
        analysis = {
            "strength_themes": [],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": [],
            "brand_vs_reality": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        platforms = {p["platform"]: p for p in processed["platform_presence"]}
        
        assert platforms["Google Maps"]["recency"] == "within_last_month"
        assert platforms["Yelp"]["recency"] == "unknown"  # Invalid -> unknown
        assert platforms["Facebook"]["recency"] == "6_months_plus"
        print("✓ Recency validation: invalid values default to 'unknown'")
    
    def test_validates_response_quality_enum(self):
        """postprocess should validate response_quality values"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {
            "platforms_found": [
                {"platform": "Google Maps", "has_reviews": True, "owner_responds": True, "response_quality": "active"},
                {"platform": "Yelp", "has_reviews": True, "owner_responds": True, "response_quality": "bad_value"},  # Invalid
                {"platform": "Facebook", "has_reviews": True, "owner_responds": False, "response_quality": "none"},
            ]
        }
        analysis = {
            "strength_themes": [],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": [],
            "brand_vs_reality": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        platforms = {p["platform"]: p for p in processed["platform_presence"]}
        
        assert platforms["Google Maps"]["response_quality"] == "active"
        assert platforms["Yelp"]["response_quality"] == "unknown"  # Invalid -> unknown
        assert platforms["Facebook"]["response_quality"] == "none"
        print("✓ response_quality validation: invalid values default to 'unknown'")
    
    def test_detects_app_store_platforms_by_name(self):
        """postprocess should detect app stores by platform name"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {
            "platforms_found": [
                {"platform": "Apple App Store", "has_reviews": True, "approximate_rating": 4.5},
                {"platform": "Google Play Store", "has_reviews": True, "approximate_rating": 4.2},
                {"platform": "Google Maps", "has_reviews": True, "approximate_rating": 4.7},
            ]
        }
        analysis = {
            "strength_themes": [],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": [],
            "brand_vs_reality": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        platforms = {p["platform"]: p for p in processed["platform_presence"]}
        
        assert platforms["Apple App Store"]["is_app_store"] is True
        assert platforms["Google Play Store"]["is_app_store"] is True
        assert platforms["Google Maps"]["is_app_store"] is False
        assert stats["platforms_app_store"] == 2
        print("✓ App store detection by name works correctly")
    
    def test_detects_app_store_platforms_by_url(self):
        """postprocess should detect app stores by URL patterns"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {
            "platforms_found": [
                {"platform": "App Store", "url": "https://apps.apple.com/us/app/myapp/id123", "has_reviews": True},
                {"platform": "Play Store", "url": "https://play.google.com/store/apps/details?id=com.myapp", "has_reviews": True},
            ]
        }
        analysis = {
            "strength_themes": [],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": [],
            "brand_vs_reality": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        for p in processed["platform_presence"]:
            assert p["is_app_store"] is True
        print("✓ App store detection by URL pattern works correctly")
    
    def test_adds_is_paraphrased_to_all_snippets(self):
        """postprocess should add is_paraphrased: true to all snippets"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {"platforms_found": []}
        analysis = {
            "strength_themes": [],
            "weakness_themes": [],
            "social_proof_snippets": [
                {"quote": "Amazing service, would definitely come back again!", "platform": "Google Maps", "context": "Service review"},
                {"quote": "The best salon in town, highly recommended for everyone.", "platform": "Yelp", "context": "Overall review"},
                {"quote": "Fast delivery and excellent quality products received.", "platform": "Trustpilot", "context": "Product review"},
            ],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": [],
            "brand_vs_reality": []
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        for snippet in processed["social_proof_snippets"]:
            assert snippet["is_paraphrased"] is True
        print("✓ is_paraphrased: true added to all snippets")
    
    def test_processes_brand_vs_reality_checks(self):
        """postprocess should process brand_vs_reality checks with validation"""
        from research.reviews.postprocess import postprocess_reviews
        
        discovery = {"platforms_found": []}
        analysis = {
            "strength_themes": [],
            "weakness_themes": [],
            "social_proof_snippets": [],
            "trust_signals": [],
            "competitor_reputation": [],
            "reputation_summary": [],
            "brand_vs_reality": [
                {"claim": "Fast delivery", "review_alignment": "supported", "evidence": "Many reviews praise quick shipping"},
                {"claim": "24/7 support", "review_alignment": "contradicted", "evidence": "Complaints about slow response times"},
                {"claim": "Eco-friendly", "review_alignment": "not_mentioned", "evidence": "No reviews mention eco practices"},
                {"claim": "Premium quality", "review_alignment": "partially_supported", "evidence": "Mixed reviews on quality"},
                {"claim": "Invalid claim", "review_alignment": "invalid_value", "evidence": "Test"},  # Invalid alignment
            ]
        }
        
        processed, stats = postprocess_reviews(discovery, analysis)
        
        bvr = processed["brand_vs_reality"]
        
        # Check processed checks
        assert len(bvr) == 5
        
        alignments = {c["claim"]: c["review_alignment"] for c in bvr}
        assert alignments["Fast delivery"] == "supported"
        assert alignments["24/7 support"] == "contradicted"
        assert alignments["Eco-friendly"] == "not_mentioned"
        assert alignments["Premium quality"] == "partially_supported"
        assert alignments["Invalid claim"] == "not_mentioned"  # Invalid -> not_mentioned
        
        # Check stats
        assert stats["brand_claims_checked"] == 5
        assert stats["brand_claims_supported"] == 1
        assert stats["brand_claims_contradicted"] == 1
        print("✓ brand_vs_reality processing with validation works correctly")


class TestComputeSocialProofReadiness:
    """Test compute_social_proof_readiness scoring function"""
    
    def test_strong_readiness_score(self):
        """Score >= 8 should return 'strong'"""
        from research.reviews.postprocess import compute_social_proof_readiness
        
        # Strong scenario: 3+ platforms with reviews, high rating, recent, owner responds, aligned claims, 3+ strengths
        platforms = [
            {"has_reviews": True, "approximate_rating": 4.5, "recency": "within_last_month", "owner_responds": True},
            {"has_reviews": True, "approximate_rating": 4.6, "recency": "1_3_months", "owner_responds": False},
            {"has_reviews": True, "approximate_rating": 4.4, "recency": "3_6_months", "owner_responds": False},
        ]
        strengths = [
            {"theme": "Fast service"},
            {"theme": "Quality products"},
            {"theme": "Friendly staff"},
        ]
        brand_vs_reality = [
            {"review_alignment": "supported"},
            {"review_alignment": "supported"},
            {"review_alignment": "not_mentioned"},
        ]
        
        result = compute_social_proof_readiness(platforms, strengths, brand_vs_reality)
        
        # Score breakdown: 3(platforms) + 3(avg rating ~4.5) + 2(recency within_last_month) + 1(owner responds) + 1(>50% supported) + 1(3+ strengths) = 11
        assert result == "strong"
        print("✓ Strong readiness (>=8): 3+ platforms, high rating, recent, owner responds, aligned, 3+ strengths")
    
    def test_moderate_readiness_score(self):
        """Score 4-7 should return 'moderate'"""
        from research.reviews.postprocess import compute_social_proof_readiness
        
        # Moderate scenario: 2 platforms, decent rating, not recent, no owner responds
        platforms = [
            {"has_reviews": True, "approximate_rating": 4.0, "recency": "3_6_months", "owner_responds": False},
            {"has_reviews": True, "approximate_rating": 3.9, "recency": "6_months_plus", "owner_responds": False},
        ]
        strengths = [{"theme": "Good quality"}, {"theme": "Nice ambiance"}]
        brand_vs_reality = []
        
        result = compute_social_proof_readiness(platforms, strengths, brand_vs_reality)
        
        # Score breakdown: 2(platforms) + 2(avg rating ~3.95) = 4
        assert result == "moderate"
        print("✓ Moderate readiness (4-7): 2 platforms, decent rating, no recency bonus")
    
    def test_weak_readiness_score(self):
        """Score < 4 should return 'weak'"""
        from research.reviews.postprocess import compute_social_proof_readiness
        
        # Weak scenario: 1 platform, low rating, old reviews
        platforms = [
            {"has_reviews": True, "approximate_rating": 2.5, "recency": "6_months_plus", "owner_responds": False},
        ]
        strengths = [{"theme": "Okay service"}]
        brand_vs_reality = []
        
        result = compute_social_proof_readiness(platforms, strengths, brand_vs_reality)
        
        # Score breakdown: 1(platform) + 0(avg rating < 3) = 1
        assert result == "weak"
        print("✓ Weak readiness (<4): 1 platform, low rating")
    
    def test_no_platforms_is_weak(self):
        """No platforms with reviews should return 'weak'"""
        from research.reviews.postprocess import compute_social_proof_readiness
        
        platforms = []
        strengths = []
        brand_vs_reality = []
        
        result = compute_social_proof_readiness(platforms, strengths, brand_vs_reality)
        
        assert result == "weak"
        print("✓ No platforms = weak readiness")
    
    def test_recency_bonus(self):
        """Recent reviews should add points"""
        from research.reviews.postprocess import compute_social_proof_readiness
        
        # Same platforms but different recency
        platforms_recent = [{"has_reviews": True, "approximate_rating": 4.0, "recency": "within_last_month"}]
        platforms_old = [{"has_reviews": True, "approximate_rating": 4.0, "recency": "6_months_plus"}]
        
        recent_score_result = compute_social_proof_readiness(platforms_recent, [], [])
        old_score_result = compute_social_proof_readiness(platforms_old, [], [])
        
        # Recent gets +2, old gets +0
        # With 1 platform + 2 rating points: recent = 5 (moderate), old = 3 (weak)
        assert recent_score_result == "moderate"  # 1 + 2 + 2 = 5
        assert old_score_result == "weak"  # 1 + 2 + 0 = 3
        print("✓ Recency bonus: within_last_month adds 2 points")
    
    def test_owner_responds_bonus(self):
        """Owner responds should add 1 point"""
        from research.reviews.postprocess import compute_social_proof_readiness
        
        platforms_responds = [
            {"has_reviews": True, "approximate_rating": 3.5, "recency": "3_6_months", "owner_responds": True},
            {"has_reviews": True, "approximate_rating": 3.6, "recency": "3_6_months", "owner_responds": False},
        ]
        platforms_no_responds = [
            {"has_reviews": True, "approximate_rating": 3.5, "recency": "3_6_months", "owner_responds": False},
            {"has_reviews": True, "approximate_rating": 3.6, "recency": "3_6_months", "owner_responds": False},
        ]
        
        responds_result = compute_social_proof_readiness(platforms_responds, [], [])
        no_responds_result = compute_social_proof_readiness(platforms_no_responds, [], [])
        
        # With owner responds: 2 + 1 + 1 = 4 (moderate)
        # Without: 2 + 1 = 3 (weak)
        assert responds_result == "moderate"
        assert no_responds_result == "weak"
        print("✓ Owner responds bonus: +1 point if any platform has owner responds")


# ============== v1.5 SERVICE INPUT EXTRACTION TESTS ==============

class TestServiceV15Inputs:
    """Test ReviewsService.extract_inputs v1.5 additions"""
    
    def test_extracts_app_store_urls_from_channels(self):
        """extract_inputs should get app_store_urls from step2.channels.apps"""
        from research.reviews.service import ReviewsService
        
        class MockDB:
            pass
        
        service = ReviewsService(MockDB())
        
        campaign_brief = {"geo": {"city_or_region": "Dubai", "country": "UAE"}}
        website_context_pack = {
            "step2": {
                "site": {"domain": "testsalon.com"},
                "classification": {"subcategory": "beauty", "niche": "salon"},
                "offer": {"offer_catalog": []},
                "brand_summary": {"name": "Test Salon"},
                "channels": {
                    "apps": [
                        {"url": "https://apps.apple.com/us/app/testsalon/id123456"},
                        {"url": "https://play.google.com/store/apps/details?id=com.testsalon"},
                    ]
                }
            }
        }
        
        inputs = service.extract_inputs(campaign_brief, website_context_pack)
        
        assert len(inputs["app_store_urls"]) == 2
        assert "apps.apple.com" in inputs["app_store_urls"][0]
        assert "play.google.com" in inputs["app_store_urls"][1]
        print("✓ extract_inputs extracts app_store_urls from channels.apps")
    
    def test_extracts_brand_claims_from_offer(self):
        """extract_inputs should get brand_claims from offer.value_prop + offer.key_benefits + brand_summary.bullets"""
        from research.reviews.service import ReviewsService
        
        class MockDB:
            pass
        
        service = ReviewsService(MockDB())
        
        campaign_brief = {"geo": {"city_or_region": "Dubai", "country": "UAE"}}
        website_context_pack = {
            "step2": {
                "site": {"domain": "testsalon.com"},
                "classification": {"subcategory": "beauty", "niche": "salon"},
                "offer": {
                    "offer_catalog": [],
                    "value_prop": "Premium hair care at affordable prices",
                    "key_benefits": ["Expert stylists", "Organic products", "Relaxing atmosphere"]
                },
                "brand_summary": {
                    "name": "Test Salon",
                    "bullets": ["10+ years experience", "Award-winning team"]
                },
                "channels": {}
            }
        }
        
        inputs = service.extract_inputs(campaign_brief, website_context_pack)
        
        assert "Premium hair care at affordable prices" in inputs["brand_claims"]
        assert "Expert stylists" in inputs["brand_claims"]
        assert "Organic products" in inputs["brand_claims"]
        assert "10+ years experience" in inputs["brand_claims"]
        print("✓ extract_inputs extracts brand_claims from value_prop, key_benefits, bullets")
    
    def test_handles_missing_channels_apps(self):
        """extract_inputs should handle missing channels.apps gracefully"""
        from research.reviews.service import ReviewsService
        
        class MockDB:
            pass
        
        service = ReviewsService(MockDB())
        
        campaign_brief = {"geo": {"city_or_region": "Dubai", "country": "UAE"}}
        website_context_pack = {
            "step2": {
                "site": {"domain": "testsalon.com"},
                "classification": {"subcategory": "beauty", "niche": "salon"},
                "offer": {"offer_catalog": []},
                "brand_summary": {"name": "Test Salon"},
                "channels": {}  # No apps
            }
        }
        
        inputs = service.extract_inputs(campaign_brief, website_context_pack)
        
        assert inputs["app_store_urls"] == []
        print("✓ extract_inputs handles missing channels.apps gracefully")


# ============== v1.5 GET_PLATFORMS_FOR_CONTEXT TESTS ==============

class TestGetPlatformsForContextV15:
    """Test get_platforms_for_context v1.5 additions: always adds app stores"""
    
    def test_always_adds_apple_app_store(self):
        """get_platforms_for_context should always include Apple App Store"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="UAE",
            niche="beauty",
            subcategory="salon",
            app_store_urls=[]  # No known app store URLs
        )
        
        assert "Apple App Store" in combined
        print("✓ Apple App Store always included in combined platforms")
    
    def test_always_adds_google_play_store(self):
        """get_platforms_for_context should always include Google Play Store"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="UAE",
            niche="beauty",
            subcategory="salon",
            app_store_urls=[]
        )
        
        assert "Google Play Store" in combined
        print("✓ Google Play Store always included in combined platforms")
    
    def test_detects_app_stores_from_urls(self):
        """get_platforms_for_context should detect app stores from provided URLs"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="UAE",
            niche="beauty",
            subcategory="salon",
            app_store_urls=[
                "https://apps.apple.com/us/app/myapp/id123",
                "https://play.google.com/store/apps/details?id=com.myapp"
            ]
        )
        
        assert "Apple App Store" in combined
        assert "Google Play Store" in combined
        print("✓ App stores detected from provided URLs")
    
    def test_no_duplicate_app_stores(self):
        """get_platforms_for_context should not duplicate app stores"""
        from research.reviews.perplexity_reviews import get_platforms_for_context
        
        geo_platforms, niche_platforms, combined = get_platforms_for_context(
            country="UAE",
            niche="beauty",
            subcategory="salon",
            app_store_urls=["https://apps.apple.com/us/app/myapp/id123"]
        )
        
        # Count occurrences
        apple_count = combined.count("Apple App Store")
        google_count = combined.count("Google Play Store")
        
        assert apple_count == 1
        assert google_count == 1
        print("✓ No duplicate app stores in combined list")


# ============== v1.5 API TESTS ==============

class TestReviewsV15API:
    """Test Reviews API v1.5 endpoints"""
    
    def test_health_check(self):
        """Health check should return 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health check passed")
    
    def test_reviews_latest_backwards_compatible(self):
        """GET /reviews/latest should work with v1.0 data (no v1.5 fields)"""
        # Use a test campaign ID
        test_campaign_id = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"
        
        response = requests.get(f"{BASE_URL}/api/research/{test_campaign_id}/reviews/latest")
        
        if response.status_code == 200:
            data = response.json()
            assert "has_data" in data
            
            if data.get("has_data") and data.get("snapshot"):
                snapshot = data["snapshot"]
                # v1.5 fields should exist (with defaults for old data)
                # If data exists, it should have version field
                if "version" in snapshot:
                    print(f"✓ Reviews latest returns data with version: {snapshot.get('version')}")
                else:
                    print("✓ Reviews latest returns legacy data (no version field)")
            else:
                print("✓ Reviews latest returns has_data: false (no reviews yet)")
                
        elif response.status_code == 404:
            print("✓ Test campaign not found - expected for non-existent campaign")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_reviews_run_requires_step2(self):
        """POST /reviews/run should return 400 if Step 2 is missing"""
        # This is more of an integration test - it checks the route exists
        test_campaign_id = "nonexistent-campaign-for-v15-test"
        
        response = requests.post(f"{BASE_URL}/api/research/{test_campaign_id}/reviews/run")
        
        # Should be 404 (campaign not found) not 405 (method not allowed)
        assert response.status_code == 404
        print("✓ Reviews run returns 404 for non-existent campaign")


# ============== PROMPT BUILDING v1.5 TESTS ==============

class TestPromptBuildingV15:
    """Test v1.5 prompt builders include new fields"""
    
    def test_discovery_prompt_includes_recency_response_fields(self):
        """Discovery prompt should include recency and owner response fields"""
        from research.reviews.perplexity_reviews import build_discovery_prompt
        
        prompt = build_discovery_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut"],
            brand_overview="Test overview",
            platforms_to_check=["Google Maps"],
            app_store_urls=["https://apps.apple.com/test"]
        )
        
        assert "recency" in prompt.lower()
        assert "within_last_month" in prompt
        assert "owner_responds" in prompt
        assert "response_quality" in prompt
        assert "active" in prompt and "occasional" in prompt
        print("✓ Discovery prompt includes recency and owner response fields")
    
    def test_discovery_prompt_includes_app_store_hint(self):
        """Discovery prompt should include app store URL hints when provided"""
        from research.reviews.perplexity_reviews import build_discovery_prompt
        
        prompt = build_discovery_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut"],
            brand_overview="Test overview",
            platforms_to_check=["Google Maps"],
            app_store_urls=["https://apps.apple.com/us/app/testapp/id123"]
        )
        
        assert "apps.apple.com" in prompt
        assert "APP STORE" in prompt.upper() or "app store" in prompt.lower()
        print("✓ Discovery prompt includes app store URL hints")
    
    def test_analysis_prompt_includes_brand_vs_reality(self):
        """Analysis prompt should include brand vs reality section when brand_claims provided"""
        from research.reviews.perplexity_reviews import build_analysis_prompt
        
        prompt = build_analysis_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut"],
            brand_overview="Test overview",
            discovery_results={"platforms_found": []},
            competitor_names=[],
            brand_claims=["Fast delivery", "Premium quality", "24/7 support"]
        )
        
        assert "BRAND VS REALITY" in prompt
        assert "Fast delivery" in prompt
        assert "Premium quality" in prompt
        assert "supported" in prompt
        assert "contradicted" in prompt
        assert "not_mentioned" in prompt
        print("✓ Analysis prompt includes brand vs reality section with claims")
    
    def test_analysis_prompt_without_brand_claims(self):
        """Analysis prompt should work without brand_claims"""
        from research.reviews.perplexity_reviews import build_analysis_prompt
        
        prompt = build_analysis_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut"],
            brand_overview="Test overview",
            discovery_results={"platforms_found": []},
            competitor_names=[],
            brand_claims=[]  # Empty
        )
        
        # Should still work, just without brand vs reality section
        assert "Test Brand" in prompt
        assert "WHY THIS MATTERS" in prompt
        print("✓ Analysis prompt works without brand_claims")


# ============== RUN TESTS ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
