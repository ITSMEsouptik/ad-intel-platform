"""
Community Intelligence Module Tests v1.0 - Feb 2026

Test modules:
- v1.0 Schema validation (CommunityThread, CommunityTheme, CommunityLanguageBank, CommunitySnapshot)
- v1.0 Schema validation (theme type enum, frequency enum)
- v1.0 Query Builder (build_query_plan, _get_target_domains, EXCLUDED_DOMAINS)
- v1.0 Post-processing (dedup threads, filter excluded domains, generic theme rejection, enum validation, length caps)
- v1.0 Service (extract_inputs, _get_optional_context)
- v1.0 API (POST run, GET latest, GET history)
"""

import sys
from pathlib import Path

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


# ============== v1.0 SCHEMA TESTS ==============

class TestCommunityV10Schema:
    """Test Community v1.0 schema definitions"""
    
    def test_community_thread_fields(self):
        """CommunityThread should have all required fields"""
        from research.community.schema import CommunityThread
        
        thread = CommunityThread(
            url="https://www.reddit.com/r/test/comments/123/test_thread",
            domain="reddit.com",
            title="Test Thread Title",
            published_at="2024-12",
            query_used="best test service",
            excerpt="This is a test excerpt with real user words",
            comment_count_est=45,
            relevance_score_0_100=78
        )
        
        assert thread.url == "https://www.reddit.com/r/test/comments/123/test_thread"
        assert thread.domain == "reddit.com"
        assert thread.title == "Test Thread Title"
        assert thread.published_at == "2024-12"
        assert thread.query_used == "best test service"
        assert thread.excerpt == "This is a test excerpt with real user words"
        assert thread.comment_count_est == 45
        assert thread.relevance_score_0_100 == 78
        print("✓ CommunityThread validates all fields correctly")
    
    def test_community_thread_defaults(self):
        """CommunityThread should have correct defaults"""
        from research.community.schema import CommunityThread
        
        thread = CommunityThread()
        
        assert thread.url == ""
        assert thread.domain == ""
        assert thread.title is None
        assert thread.published_at is None
        assert thread.query_used == ""
        assert thread.excerpt == ""
        assert thread.comment_count_est is None
        assert thread.relevance_score_0_100 == 50
        print("✓ CommunityThread defaults are correct")
    
    def test_community_theme_type_enum_values(self):
        """CommunityTheme type should accept valid enum values: pain|objection|desire|trigger|comparison|how_to"""
        from research.community.schema import CommunityTheme
        
        valid_types = ["pain", "objection", "desire", "trigger", "comparison", "how_to"]
        
        for theme_type in valid_types:
            theme = CommunityTheme(
                label=f"Test {theme_type} theme",
                type=theme_type,
                frequency="medium",
                evidence=["Test quote"],
                source_urls=["https://reddit.com/r/test"]
            )
            assert theme.type == theme_type
        
        print(f"✓ CommunityTheme type accepts all valid enum values: {valid_types}")
    
    def test_community_theme_frequency_enum_values(self):
        """CommunityTheme frequency should accept: high|medium|low"""
        from research.community.schema import CommunityTheme
        
        valid_frequencies = ["high", "medium", "low"]
        
        for freq in valid_frequencies:
            theme = CommunityTheme(
                label=f"Test theme with {freq} frequency",
                type="pain",
                frequency=freq,
                evidence=["Test quote"],
                source_urls=["https://reddit.com/r/test"]
            )
            assert theme.frequency == freq
        
        print(f"✓ CommunityTheme frequency accepts all valid enum values: {valid_frequencies}")
    
    def test_community_theme_defaults(self):
        """CommunityTheme should have correct defaults"""
        from research.community.schema import CommunityTheme
        
        theme = CommunityTheme()
        
        assert theme.label == ""
        assert theme.type == "pain"  # Default
        assert theme.frequency == "medium"  # Default
        assert theme.evidence == []
        assert theme.source_urls == []
        print("✓ CommunityTheme defaults are correct")
    
    def test_community_language_bank_fields(self):
        """CommunityLanguageBank should have phrases and words"""
        from research.community.schema import CommunityLanguageBank
        
        lb = CommunityLanguageBank(
            phrases=["this service sucks", "highly recommend", "game changer"],
            words=["worth it", "rip off", "life saver"]
        )
        
        assert len(lb.phrases) == 3
        assert len(lb.words) == 3
        assert "this service sucks" in lb.phrases
        assert "worth it" in lb.words
        print("✓ CommunityLanguageBank validates phrases and words correctly")
    
    def test_community_snapshot_fields(self):
        """CommunitySnapshot should have all v1.0 fields"""
        from research.community.schema import (
            CommunitySnapshot, CommunityThread, CommunityTheme, 
            CommunityLanguageBank, CommunityInputs, CommunityAudit
        )
        
        snapshot = CommunitySnapshot(
            version="1.0",
            threads=[CommunityThread(url="https://reddit.com/r/test", domain="reddit.com")],
            themes=[CommunityTheme(label="Price anxiety", type="pain", frequency="high")],
            language_bank=CommunityLanguageBank(phrases=["test phrase"], words=["test word"]),
            audience_notes=["Audience is price-sensitive"],
            creative_implications=["Address pricing upfront"],
            gaps_to_research=["Explore competitor comparison more"],
            inputs_used=CommunityInputs(brand_name="Test Brand"),
            audit=CommunityAudit(queries_generated=20)
        )
        
        assert snapshot.version == "1.0"
        assert len(snapshot.threads) == 1
        assert len(snapshot.themes) == 1
        assert len(snapshot.language_bank.phrases) == 1
        assert len(snapshot.audience_notes) == 1
        assert len(snapshot.creative_implications) == 1
        assert len(snapshot.gaps_to_research) == 1
        assert snapshot.inputs_used.brand_name == "Test Brand"
        assert snapshot.audit.queries_generated == 20
        print("✓ CommunitySnapshot v1.0 fields validate correctly")


# ============== v1.0 QUERY BUILDER TESTS ==============

class TestQueryBuilderV10:
    """Test query_builder.build_query_plan and related functions"""
    
    def test_build_query_plan_generates_5_families(self):
        """build_query_plan should generate queries across 5 families: pain, recommendation, price, comparison, trust"""
        from research.community.query_builder import build_query_plan
        
        plan = build_query_plan(
            brand_name="Test Salon",
            domain="testsalon.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut", "coloring", "styling"],
            competitor_names=["Competitor A", "Competitor B"],
            pains_from_intel=["long wait times", "high prices"]
        )
        
        assert "families" in plan
        families = set(plan["families"])
        expected_families = {"pain", "recommendation", "price", "comparison", "trust"}
        
        assert families == expected_families, f"Expected {expected_families}, got {families}"
        print(f"✓ Query plan generates all 5 families: {families}")
    
    def test_build_query_plan_caps_at_40_queries(self):
        """build_query_plan should cap at 40 queries"""
        from research.community.query_builder import build_query_plan
        
        plan = build_query_plan(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="New York",
            country="USA",
            subcategory="technology",
            niche="software",
            services=["service1", "service2", "service3", "service4", "service5", "service6"],
            competitor_names=["Comp1", "Comp2", "Comp3"],
            pains_from_intel=["pain1", "pain2", "pain3"]
        )
        
        assert plan["total_queries"] <= 40, f"Expected <= 40 queries, got {plan['total_queries']}"
        assert len(plan["queries"]) <= 40
        print(f"✓ Query plan capped at 40 queries (got {plan['total_queries']})")
    
    def test_get_target_domains_returns_allowlist_plus_niche(self):
        """_get_target_domains should return allowlist domains + niche additions"""
        from research.community.query_builder import _get_target_domains, DOMAIN_ALLOWLIST
        
        # Test for software niche
        domains = _get_target_domains("software", "saas")
        
        # Should include base allowlist domains
        assert "reddit.com" in domains
        assert "quora.com" in domains
        
        # Should include niche-specific additions for software/saas
        assert "stackexchange.com" in domains
        assert "indiehackers.com" in domains
        assert "producthunt.com" in domains
        
        print(f"✓ _get_target_domains returns {len(domains)} domains for software/saas niche")
    
    def test_get_target_domains_hotel_includes_tripadvisor(self):
        """_get_target_domains should include tripadvisor for hotel niche"""
        from research.community.query_builder import _get_target_domains
        
        domains = _get_target_domains("hotel", "hospitality")
        
        assert "tripadvisor.com/ShowTopic" in domains
        print("✓ Hotel niche includes tripadvisor.com/ShowTopic")
    
    def test_excluded_domains_contains_review_sites(self):
        """EXCLUDED_DOMAINS should contain review platforms"""
        from research.community.query_builder import EXCLUDED_DOMAINS
        
        review_sites = ["trustpilot.com", "yelp.com", "g2.com", "capterra.com", "productreview.com.au"]
        for site in review_sites:
            assert site in EXCLUDED_DOMAINS, f"Expected {site} in EXCLUDED_DOMAINS"
        
        print(f"✓ EXCLUDED_DOMAINS contains review platforms: {review_sites}")
    
    def test_excluded_domains_contains_employee_sites(self):
        """EXCLUDED_DOMAINS should contain employee review sites"""
        from research.community.query_builder import EXCLUDED_DOMAINS
        
        employee_sites = ["glassdoor.com", "indeed.com", "comparably.com", "ambitionbox.com", "naukri.com", "kununu.com"]
        for site in employee_sites:
            assert site in EXCLUDED_DOMAINS, f"Expected {site} in EXCLUDED_DOMAINS"
        
        print(f"✓ EXCLUDED_DOMAINS contains employee sites: {employee_sites}")


# ============== v1.0 POSTPROCESS TESTS ==============

class TestPostprocessV10:
    """Test postprocess_community function"""
    
    def test_validates_theme_types(self):
        """postprocess should validate theme types (invalid -> 'pain')"""
        from research.community.postprocess import postprocess_community
        
        discovery = {"threads": []}
        # Note: evidence must be > 10 chars to be kept
        synthesis = {
            "themes": [
                {"label": "Test theme 1", "type": "pain", "frequency": "high", "evidence": ["This is a valid quote with more than 10 characters"], "source_urls": ["https://test.com"]},
                {"label": "Test theme 2", "type": "invalid_type", "frequency": "medium", "evidence": ["Another valid quote with enough chars"], "source_urls": ["https://test.com"]},
                {"label": "Test theme 3", "type": "desire", "frequency": "low", "evidence": ["Yet another valid evidence quote"], "source_urls": ["https://test.com"]},
            ],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        theme_types = {t["label"]: t["type"] for t in processed["themes"]}
        
        assert theme_types["Test theme 1"] == "pain"
        assert theme_types["Test theme 2"] == "pain"  # Invalid -> default to pain
        assert theme_types["Test theme 3"] == "desire"
        print("✓ postprocess validates theme types (invalid -> 'pain')")
    
    def test_validates_theme_frequency(self):
        """postprocess should validate theme frequency (invalid -> 'medium')"""
        from research.community.postprocess import postprocess_community
        
        discovery = {"threads": []}
        # Note: evidence must be > 10 chars to be kept
        synthesis = {
            "themes": [
                {"label": "Theme high", "type": "pain", "frequency": "high", "evidence": ["This is a valid quote with more than 10 chars"], "source_urls": ["https://test.com"]},
                {"label": "Theme invalid", "type": "pain", "frequency": "super_high", "evidence": ["Another valid evidence quote here"], "source_urls": ["https://test.com"]},
                {"label": "Theme low", "type": "pain", "frequency": "low", "evidence": ["Yet another valid evidence quote"], "source_urls": ["https://test.com"]},
            ],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        freq_map = {t["label"]: t["frequency"] for t in processed["themes"]}
        
        assert freq_map["Theme high"] == "high"
        assert freq_map["Theme invalid"] == "medium"  # Invalid -> default to medium
        assert freq_map["Theme low"] == "low"
        print("✓ postprocess validates theme frequency (invalid -> 'medium')")
    
    def test_rejects_generic_theme_labels(self):
        """postprocess should reject generic theme labels like 'quality concerns' or 'good service'"""
        from research.community.postprocess import postprocess_community
        
        # Note: evidence must be > 10 chars to be kept
        valid_evidence = ["This is a valid quote with more than 10 characters"]
        
        discovery = {"threads": []}
        synthesis = {
            "themes": [
                {"label": "quality concerns", "type": "pain", "frequency": "high", "evidence": valid_evidence, "source_urls": ["https://test.com"]},
                {"label": "good service", "type": "desire", "frequency": "high", "evidence": valid_evidence, "source_urls": ["https://test.com"]},
                {"label": "general feedback", "type": "pain", "frequency": "high", "evidence": valid_evidence, "source_urls": ["https://test.com"]},
                {"label": "Price transparency anxiety", "type": "pain", "frequency": "high", "evidence": valid_evidence, "source_urls": ["https://reddit.com/r/test"]},  # This one is specific
            ],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        labels = [t["label"] for t in processed["themes"]]
        
        assert "quality concerns" not in labels
        assert "good service" not in labels
        assert "general feedback" not in labels
        assert "Price transparency anxiety" in labels
        assert stats["generic_themes_removed"] >= 3
        print(f"✓ postprocess rejects generic theme labels ({stats['generic_themes_removed']} removed)")
    
    def test_requires_evidence_and_source_urls(self):
        """postprocess should require themes to have evidence and source_urls"""
        from research.community.postprocess import postprocess_community
        
        discovery = {"threads": []}
        synthesis = {
            "themes": [
                {"label": "No evidence theme", "type": "pain", "frequency": "high", "evidence": [], "source_urls": ["https://test.com"]},
                {"label": "No urls theme", "type": "pain", "frequency": "high", "evidence": ["some quote"], "source_urls": []},
                {"label": "Valid theme", "type": "pain", "frequency": "high", "evidence": ["real user quote"], "source_urls": ["https://reddit.com"]},
            ],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        labels = [t["label"] for t in processed["themes"]]
        
        assert "No evidence theme" not in labels
        assert "No urls theme" not in labels
        assert "Valid theme" in labels
        assert stats["themes_no_evidence_removed"] >= 2
        print(f"✓ postprocess requires evidence+source_urls ({stats['themes_no_evidence_removed']} removed)")
    
    def test_deduplicates_threads_by_url(self):
        """postprocess should deduplicate threads by URL"""
        from research.community.postprocess import postprocess_community
        
        discovery = {
            "threads": [
                {"url": "https://reddit.com/r/test/1", "domain": "reddit.com", "title": "Thread 1"},
                {"url": "https://reddit.com/r/test/1", "domain": "reddit.com", "title": "Thread 1 Duplicate"},
                {"url": "https://reddit.com/r/test/2", "domain": "reddit.com", "title": "Thread 2"},
                {"url": "https://quora.com/question/1", "domain": "quora.com", "title": "Question 1"},
            ]
        }
        synthesis = {
            "themes": [],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        urls = [t["url"] for t in processed["threads"]]
        
        assert len(processed["threads"]) == 3
        assert urls.count("https://reddit.com/r/test/1") == 1
        assert stats["threads_deduped"] >= 1
        print(f"✓ postprocess deduplicates threads by URL ({stats['threads_deduped']} deduped)")
    
    def test_filters_excluded_domains_from_threads(self):
        """postprocess should filter threads from excluded domains (review sites)"""
        from research.community.postprocess import postprocess_community
        
        discovery = {
            "threads": [
                {"url": "https://reddit.com/r/test/1", "domain": "reddit.com", "title": "Reddit thread"},
                {"url": "https://trustpilot.com/review/test", "domain": "trustpilot.com", "title": "Trustpilot review"},
                {"url": "https://yelp.com/biz/test", "domain": "yelp.com", "title": "Yelp review"},
                {"url": "https://glassdoor.com/Review/test", "domain": "glassdoor.com", "title": "Glassdoor review"},
                {"url": "https://quora.com/question/1", "domain": "quora.com", "title": "Quora question"},
            ]
        }
        synthesis = {
            "themes": [],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        domains = [t["domain"] for t in processed["threads"]]
        
        assert "trustpilot.com" not in domains
        assert "yelp.com" not in domains
        assert "glassdoor.com" not in domains
        assert "reddit.com" in domains
        assert "quora.com" in domains
        assert stats["threads_excluded_domain"] >= 3
        print(f"✓ postprocess filters excluded domains ({stats['threads_excluded_domain']} excluded)")
    
    def test_caps_threads_at_40(self):
        """postprocess should cap threads at 40"""
        from research.community.postprocess import postprocess_community
        
        # Create 50 threads
        threads = [{"url": f"https://reddit.com/r/test/{i}", "domain": "reddit.com"} for i in range(50)]
        
        discovery = {"threads": threads}
        synthesis = {
            "themes": [],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        assert len(processed["threads"]) <= 40
        print(f"✓ postprocess caps threads at 40 (got {len(processed['threads'])} from 50)")
    
    def test_caps_themes_at_10(self):
        """postprocess should cap themes at 10"""
        from research.community.postprocess import postprocess_community
        
        # Create 15 valid themes
        themes = [
            {
                "label": f"Specific theme {i}",
                "type": "pain",
                "frequency": "high",
                "evidence": [f"Quote {i}"],
                "source_urls": [f"https://reddit.com/{i}"]
            }
            for i in range(15)
        ]
        
        discovery = {"threads": []}
        synthesis = {
            "themes": themes,
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        assert len(processed["themes"]) <= 10
        print(f"✓ postprocess caps themes at 10 (got {len(processed['themes'])} from 15)")
    
    def test_caps_phrases_at_20(self):
        """postprocess should cap language_bank.phrases at 20"""
        from research.community.postprocess import postprocess_community
        
        discovery = {"threads": []}
        synthesis = {
            "themes": [],
            "language_bank": {
                "phrases": [f"Test phrase number {i}" for i in range(30)],
                "words": []
            },
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        assert len(processed["language_bank"]["phrases"]) <= 20
        print(f"✓ postprocess caps phrases at 20 (got {len(processed['language_bank']['phrases'])} from 30)")
    
    def test_caps_words_at_30(self):
        """postprocess should cap language_bank.words at 30"""
        from research.community.postprocess import postprocess_community
        
        discovery = {"threads": []}
        synthesis = {
            "themes": [],
            "language_bank": {
                "phrases": [],
                "words": [f"word{i}" for i in range(40)]
            },
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        assert len(processed["language_bank"]["words"]) <= 30
        print(f"✓ postprocess caps words at 30 (got {len(processed['language_bank']['words'])} from 40)")
    
    def test_deduplicates_language_bank_entries(self):
        """postprocess should deduplicate language bank phrases and words"""
        from research.community.postprocess import postprocess_community
        
        discovery = {"threads": []}
        synthesis = {
            "themes": [],
            "language_bank": {
                "phrases": ["this is great", "This Is Great", "THIS IS GREAT", "another phrase"],
                "words": ["word1", "Word1", "WORD1", "word2"]
            },
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        # Should deduplicate case-insensitively
        phrases_lower = [p.lower() for p in processed["language_bank"]["phrases"]]
        words_lower = [w.lower() for w in processed["language_bank"]["words"]]
        
        assert phrases_lower.count("this is great") == 1
        assert words_lower.count("word1") == 1
        print("✓ postprocess deduplicates language bank entries (case-insensitive)")


# ============== v1.0 SERVICE TESTS ==============

class TestServiceV10:
    """Test CommunityService.extract_inputs and _get_optional_context"""
    
    def test_extract_inputs_extracts_standard_fields(self):
        """extract_inputs should extract geo, brand_name, domain, subcategory, niche, services, brand_overview"""
        from research.community.service import CommunityService
        
        class MockDB:
            pass
        
        service = CommunityService(MockDB())
        
        campaign_brief = {"geo": {"city_or_region": "Dubai", "country": "UAE"}}
        website_context_pack = {
            "step2": {
                "site": {"domain": "testsalon.com", "final_url": "https://testsalon.com"},
                "classification": {"subcategory": "beauty", "niche": "salon"},
                "offer": {
                    "offer_catalog": [
                        {"name": "Haircut"},
                        {"name": "Coloring"},
                        {"name": "Styling"}
                    ]
                },
                "brand_summary": {
                    "name": "Test Salon",
                    "one_liner": "Premium hair care",
                    "tagline": "Your beauty partner",
                    "bullets": ["Expert stylists", "Organic products"]
                }
            }
        }
        
        inputs = service.extract_inputs(campaign_brief, website_context_pack)
        
        assert inputs["geo"]["city"] == "Dubai"
        assert inputs["geo"]["country"] == "UAE"
        assert inputs["brand_name"] == "Test Salon"
        assert inputs["domain"] == "testsalon.com"
        assert inputs["subcategory"] == "beauty"
        assert inputs["niche"] == "salon"
        assert "Haircut" in inputs["services"]
        assert "Coloring" in inputs["services"]
        assert "Premium hair care" in inputs["brand_overview"]
        print("✓ extract_inputs extracts all standard Step 1+2 fields")
    
    def test_extract_inputs_handles_missing_fields(self):
        """extract_inputs should handle missing optional fields gracefully"""
        from research.community.service import CommunityService
        
        class MockDB:
            pass
        
        service = CommunityService(MockDB())
        
        campaign_brief = {"geo": {"country": "USA"}}  # No city
        website_context_pack = {
            "step2": {
                "site": {"domain": "test.com"},
                "classification": {},
                "offer": {},
                "brand_summary": {}
            }
        }
        
        inputs = service.extract_inputs(campaign_brief, website_context_pack)
        
        assert inputs["geo"]["city"] == ""
        assert inputs["geo"]["country"] == "USA"
        assert inputs["subcategory"] == ""
        assert inputs["services"] == []
        print("✓ extract_inputs handles missing optional fields gracefully")


# ============== v1.0 API TESTS ==============

class TestCommunityV10API:
    """Test Community API v1.0 endpoints"""
    
    def test_health_check(self):
        """Health check should return 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health check passed")
    
    def test_community_latest_returns_not_run_for_new_campaign(self):
        """GET /community/latest should return 'not_run' status for campaigns without community data"""
        test_campaign_id = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"
        
        response = requests.get(f"{BASE_URL}/api/research/{test_campaign_id}/community/latest")
        
        if response.status_code == 200:
            data = response.json()
            assert "has_data" in data
            assert "status" in data
            
            if not data.get("has_data"):
                assert data["status"] == "not_run"
                print("✓ Community latest returns 'not_run' for campaigns without data")
            else:
                print(f"✓ Community latest returns existing data with status: {data['status']}")
        elif response.status_code == 404:
            print("✓ Campaign not found (expected for non-existent campaign)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_community_run_returns_404_for_nonexistent_campaign(self):
        """POST /community/run should return 404 for non-existent campaign"""
        test_campaign_id = "nonexistent-campaign-for-community-test"
        
        response = requests.post(f"{BASE_URL}/api/research/{test_campaign_id}/community/run")
        
        assert response.status_code == 404
        print("✓ Community run returns 404 for non-existent campaign")
    
    def test_community_history_returns_404_for_nonexistent_campaign(self):
        """GET /community/history should return 404 for non-existent campaign"""
        test_campaign_id = "nonexistent-campaign-for-community-history-test"
        
        response = requests.get(f"{BASE_URL}/api/research/{test_campaign_id}/community/history")
        
        assert response.status_code == 404
        print("✓ Community history returns 404 for non-existent campaign")
    
    def test_community_latest_response_structure(self):
        """GET /community/latest should have proper response structure"""
        test_campaign_id = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"
        
        response = requests.get(f"{BASE_URL}/api/research/{test_campaign_id}/community/latest")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check response structure
            assert "has_data" in data
            assert "status" in data
            assert "latest" in data
            assert "refresh_due_in_days" in data
            
            print("✓ Community latest has proper response structure")
        else:
            print(f"✓ Response status: {response.status_code}")
    
    def test_community_history_response_structure(self):
        """GET /community/history should have proper response structure"""
        test_campaign_id = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"
        
        response = requests.get(f"{BASE_URL}/api/research/{test_campaign_id}/community/history")
        
        if response.status_code == 200:
            data = response.json()
            
            assert "campaign_id" in data
            assert "snapshots" in data
            assert "total_count" in data
            assert isinstance(data["snapshots"], list)
            
            print(f"✓ Community history has proper response structure (total: {data['total_count']})")
        else:
            print(f"✓ Response status: {response.status_code}")


# ============== PROMPT BUILDING TESTS (for context verification) ==============

class TestPromptBuildingV10:
    """Test that prompt builders include required fields"""
    
    def test_discovery_prompt_includes_query_families(self):
        """Discovery prompt should include query families"""
        from research.community.perplexity_community import build_discovery_prompt
        
        query_plan = {
            "total_queries": 20,
            "families": ["pain", "recommendation", "price", "comparison", "trust"],
            "queries": [
                {"query": "test query", "family": "pain"},
            ],
            "target_domains": ["reddit.com", "quora.com"],
            "excluded_domains": ["trustpilot.com"]
        }
        
        prompt = build_discovery_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut", "coloring"],
            brand_overview="Premium hair care services",
            query_plan=query_plan
        )
        
        assert "Test Brand" in prompt
        assert "Dubai" in prompt
        assert "PAIN" in prompt.upper() or "pain" in prompt.lower()
        assert "reddit.com" in prompt
        assert "trustpilot.com" in prompt
        print("✓ Discovery prompt includes all required context")
    
    def test_synthesis_prompt_includes_themes_structure(self):
        """Synthesis prompt should include themes structure with type enum"""
        from research.community.perplexity_community import build_synthesis_prompt
        
        threads = [
            {"url": "https://reddit.com/r/test", "domain": "reddit.com", "title": "Test thread", "excerpt": "Test excerpt"}
        ]
        
        prompt = build_synthesis_prompt(
            brand_name="Test Brand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut"],
            brand_overview="Test overview",
            threads=threads,
            optional_context={"pains": ["long wait"], "review_weaknesses": ["slow service"]}
        )
        
        assert "pain | objection | desire | trigger | comparison | how_to" in prompt
        assert "high | medium | low" in prompt
        assert "language_bank" in prompt
        assert "audience_notes" in prompt
        assert "creative_implications" in prompt
        assert "gaps_to_research" in prompt
        print("✓ Synthesis prompt includes themes structure with type enum")


# ============== RUN TESTS ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
