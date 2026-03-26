"""
Test Press & Media Intelligence Module
Tests for the new press_media research module - backend endpoints & schema validation

Covers:
- POST /api/research/{campaignId}/press-media/run endpoint
- GET /api/research/{campaignId}/press-media/latest endpoint  
- GET /api/research/{campaignId}/press-media/history endpoint
- 404 for non-existent campaigns
- Module imports
- Postprocessor domain filtering
- Schema validation
- Query builder (5 families)
"""

import pytest
import requests
import os
import sys

# Add backend to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test campaign with Step 2 complete (example-brand.co)
TEST_CAMPAIGN_ID = "01f098a0-cd78-46ae-8663-2640cce6b47b"
NON_EXISTENT_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000000"


class TestPressMediaEndpoints:
    """Test Press & Media API endpoints"""
    
    def test_health_check(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_press_media_latest_endpoint_exists(self):
        """GET /api/research/{campaignId}/press-media/latest returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/press-media/latest")
        assert response.status_code == 200
        data = response.json()
        # Should have the standard response shape
        assert "has_data" in data
        assert "status" in data
        assert "latest" in data
        assert "refresh_due_in_days" in data
        print(f"✓ Press-media latest endpoint exists, has_data={data['has_data']}")
    
    def test_press_media_latest_response_shape(self):
        """GET /api/research/{campaignId}/press-media/latest has correct response shape"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/press-media/latest")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response shape
        assert isinstance(data.get("has_data"), bool)
        assert data.get("status") in ["not_run", "fresh", "stale", "failed"]
        
        if data["has_data"]:
            latest = data["latest"]
            assert "version" in latest
            assert "captured_at" in latest
            assert "refresh_due_at" in latest
            assert "articles" in latest
            assert "narratives" in latest
            assert "key_quotes" in latest
            assert "media_sources" in latest
            assert "coverage_summary" in latest
            assert "coverage_gaps" in latest
            assert "pr_opportunities" in latest
            assert "audit" in latest
            print("✓ Press-media latest has correct response shape with all fields")
        else:
            # If no data yet, latest should be None
            assert data["latest"] is None
            print("✓ Press-media latest has correct empty response shape")
    
    def test_press_media_history_endpoint_exists(self):
        """GET /api/research/{campaignId}/press-media/history returns 200"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/press-media/history")
        assert response.status_code == 200
        data = response.json()
        # Should have campaign_id, snapshots array, total_count
        assert "campaign_id" in data
        assert "snapshots" in data
        assert "total_count" in data
        assert isinstance(data["snapshots"], list)
        print(f"✓ Press-media history endpoint exists, total_count={data['total_count']}")
    
    def test_press_media_404_for_non_existent_campaign(self):
        """GET /api/research/{campaignId}/press-media/latest returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{NON_EXISTENT_CAMPAIGN_ID}/press-media/latest")
        assert response.status_code == 404
        print("✓ Press-media returns 404 for non-existent campaign")
    
    def test_press_media_history_404_for_non_existent_campaign(self):
        """GET /api/research/{campaignId}/press-media/history returns 404 for non-existent campaign"""
        response = requests.get(f"{BASE_URL}/api/research/{NON_EXISTENT_CAMPAIGN_ID}/press-media/history")
        assert response.status_code == 404
        print("✓ Press-media history returns 404 for non-existent campaign")
    
    def test_press_media_run_endpoint_exists(self):
        """POST /api/research/{campaignId}/press-media/run endpoint exists"""
        # We just verify the endpoint exists and returns proper response (not 404/405)
        # Don't actually run pipeline to avoid long test time
        response = requests.post(f"{BASE_URL}/api/research/{NON_EXISTENT_CAMPAIGN_ID}/press-media/run")
        # Should be 404 (campaign not found), not 405 (method not allowed)
        assert response.status_code == 404
        print("✓ Press-media run endpoint exists (verified via 404 for non-existent campaign)")


class TestPressMediaModuleImports:
    """Test Press & Media module imports correctly"""
    
    def test_press_media_service_import(self):
        """from research.press_media import PressMediaService works"""
        try:
            from research.press_media import PressMediaService
            assert PressMediaService is not None
            print("✓ PressMediaService imports correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import PressMediaService: {e}")
    
    def test_press_media_schema_imports(self):
        """All schema classes import correctly"""
        try:
            from research.press_media.schema import (
                PressMediaSnapshot,
                PressArticle,
                MediaNarrative,
                PressQuote,
                MediaSource,
                PressMediaAudit,
                PressMediaDelta,
                PressMediaInputs
            )
            # Verify they're Pydantic models
            from pydantic import BaseModel
            assert issubclass(PressMediaSnapshot, BaseModel)
            assert issubclass(PressArticle, BaseModel)
            assert issubclass(MediaNarrative, BaseModel)
            assert issubclass(PressQuote, BaseModel)
            assert issubclass(MediaSource, BaseModel)
            print("✓ All schema classes import correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import schema classes: {e}")
    
    def test_postprocess_import(self):
        """postprocess_press_media imports correctly"""
        try:
            from research.press_media.postprocess import postprocess_press_media
            assert callable(postprocess_press_media)
            print("✓ postprocess_press_media imports correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import postprocess_press_media: {e}")
    
    def test_query_builder_import(self):
        """build_query_plan imports correctly"""
        try:
            from research.press_media.query_builder import build_query_plan
            assert callable(build_query_plan)
            print("✓ build_query_plan imports correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import build_query_plan: {e}")
    
    def test_perplexity_press_imports(self):
        """Perplexity client functions import correctly"""
        try:
            from research.press_media.perplexity_press import (
                build_discovery_prompt,
                build_analysis_prompt,
                fetch_press_discovery,
                fetch_press_analysis
            )
            assert callable(build_discovery_prompt)
            assert callable(build_analysis_prompt)
            assert callable(fetch_press_discovery)
            assert callable(fetch_press_analysis)
            print("✓ Perplexity press functions import correctly")
        except ImportError as e:
            pytest.fail(f"Failed to import perplexity_press functions: {e}")


class TestPressMediaPostprocessor:
    """Test postprocessor domain filtering"""
    
    def test_excluded_domains_constant(self):
        """EXCLUDED_DOMAINS contains expected values"""
        from research.press_media.postprocess import EXCLUDED_DOMAINS
        # Check key excluded domains
        assert "reddit.com" in EXCLUDED_DOMAINS
        assert "trustpilot.com" in EXCLUDED_DOMAINS
        assert "glassdoor.com" in EXCLUDED_DOMAINS
        assert "yelp.com" in EXCLUDED_DOMAINS
        assert "facebook.com" in EXCLUDED_DOMAINS
        assert "google.com" in EXCLUDED_DOMAINS
        print(f"✓ EXCLUDED_DOMAINS has {len(EXCLUDED_DOMAINS)} domains including expected ones")
    
    def test_is_excluded_domain_filters_forums(self):
        """_is_excluded_domain correctly filters forum domains"""
        from research.press_media.postprocess import _is_excluded_domain
        
        # These should be excluded
        assert _is_excluded_domain("https://reddit.com/r/dubai/comments/123", "") is True
        assert _is_excluded_domain("https://www.reddit.com/r/beauty/", "") is True
        assert _is_excluded_domain("https://quora.com/What-is-best-salon", "") is True
        assert _is_excluded_domain("https://trustpilot.com/review/brand.com", "") is True
        print("✓ _is_excluded_domain correctly excludes forums")
    
    def test_is_excluded_domain_filters_brand_own_domain(self):
        """_is_excluded_domain excludes brand's own domain"""
        from research.press_media.postprocess import _is_excluded_domain
        
        # Brand's own domain should be excluded
        assert _is_excluded_domain("https://example-brand.co/about", "example-brand.co") is True
        assert _is_excluded_domain("https://www.example-brand.co/services", "example-brand.co") is True
        assert _is_excluded_domain("https://blog.example-brand.co/post", "example-brand.co") is True
        print("✓ _is_excluded_domain excludes brand's own domain")
    
    def test_is_excluded_domain_allows_press_sites(self):
        """_is_excluded_domain allows legitimate press sites"""
        from research.press_media.postprocess import _is_excluded_domain
        
        # These should NOT be excluded (legitimate press)
        assert _is_excluded_domain("https://forbes.com/article/brand", "other.com") is False
        assert _is_excluded_domain("https://gulfnews.com/business/brand", "other.com") is False
        assert _is_excluded_domain("https://techcrunch.com/startup", "other.com") is False
        assert _is_excluded_domain("https://allure.com/beauty/brand", "other.com") is False
        print("✓ _is_excluded_domain allows press sites")
    
    def test_postprocess_filters_articles(self):
        """postprocess_press_media filters out excluded domain articles"""
        from research.press_media.postprocess import postprocess_press_media
        
        discovery = {
            "articles": [
                {"url": "https://forbes.com/article", "title": "Forbes article", "source_name": "Forbes"},
                {"url": "https://reddit.com/r/test", "title": "Reddit post", "source_name": "Reddit"},
                {"url": "https://brand.com/news", "title": "Brand news", "source_name": "Brand"},
                {"url": "https://gulfnews.com/article", "title": "Gulf News article", "source_name": "Gulf News"},
            ]
        }
        analysis = {}
        
        processed, stats = postprocess_press_media(discovery, analysis, brand_domain="brand.com")
        
        # Should filter out reddit.com and brand.com
        assert stats["articles_excluded_domain"] >= 2
        # Should keep forbes and gulfnews
        assert stats["articles_kept"] >= 2
        
        # Verify filtered articles don't contain excluded domains
        urls = [a["url"] for a in processed["articles"]]
        assert not any("reddit.com" in url for url in urls)
        assert not any("brand.com" in url for url in urls)
        print(f"✓ Postprocessor filtered {stats['articles_excluded_domain']} excluded domains, kept {stats['articles_kept']}")


class TestPressMediaQueryBuilder:
    """Test query builder generates 5 families"""
    
    def test_query_plan_has_5_families(self):
        """build_query_plan generates queries across 5 families"""
        from research.press_media.query_builder import build_query_plan
        
        plan = build_query_plan(
            brand_name="InstaGlam",
            domain="example-brand.co",
            city="Dubai",
            country="UAE",
            subcategory="Beauty Salon",
            niche="Lash Extensions",
            services=["Lash Extensions", "Eyebrow Threading", "Facials"],
            competitor_names=None
        )
        
        # Check structure
        assert "total_queries" in plan
        assert "families" in plan
        assert "queries" in plan
        assert "target_domains" in plan
        
        # Should have 5 families
        families = set(plan["families"])
        expected_families = {"brand_coverage", "industry_news", "leadership", "awards", "controversy"}
        assert families == expected_families, f"Expected {expected_families}, got {families}"
        
        # Should have queries
        assert plan["total_queries"] > 0
        assert len(plan["queries"]) > 0
        
        print(f"✓ Query plan has {plan['total_queries']} queries across 5 families: {plan['families']}")
    
    def test_query_plan_queries_have_family(self):
        """Each query has a family assigned"""
        from research.press_media.query_builder import build_query_plan
        
        plan = build_query_plan(
            brand_name="TestBrand",
            domain="test.com",
            city="",
            country="UAE",
            subcategory="Restaurant",
            niche="",
            services=["Dining"],
            competitor_names=[]
        )
        
        for q in plan["queries"]:
            assert "query" in q
            assert "family" in q
            assert q["family"] in ["brand_coverage", "industry_news", "leadership", "awards", "controversy"]
        
        print(f"✓ All {len(plan['queries'])} queries have valid family assignment")
    
    def test_query_plan_includes_target_domains(self):
        """Query plan includes target press domains"""
        from research.press_media.query_builder import build_query_plan
        
        plan = build_query_plan(
            brand_name="TestBrand",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="Beauty Salon",
            niche="",
            services=[],
            competitor_names=None
        )
        
        target_domains = plan["target_domains"]
        assert len(target_domains) > 0
        
        # Should include global press domains
        assert any("forbes.com" in d for d in target_domains)
        assert any("bloomberg.com" in d for d in target_domains)
        
        # Should include UAE regional domains for UAE location
        assert any("gulfnews.com" in d for d in target_domains)
        
        print(f"✓ Query plan targets {len(target_domains)} press domains")


class TestPressMediaSchema:
    """Test schema validation"""
    
    def test_press_article_schema(self):
        """PressArticle schema validates correctly"""
        from research.press_media.schema import PressArticle
        
        article = PressArticle(
            url="https://forbes.com/article",
            title="Test Article",
            source_name="Forbes",
            source_domain="forbes.com",
            article_type="feature",
            published_date="2024-06",
            excerpt="This is an excerpt.",
            sentiment="positive",
            relevance_score_0_100=85
        )
        
        assert article.url == "https://forbes.com/article"
        assert article.sentiment == "positive"
        assert article.relevance_score_0_100 == 85
        print("✓ PressArticle schema validates correctly")
    
    def test_media_narrative_schema(self):
        """MediaNarrative schema validates correctly"""
        from research.press_media.schema import MediaNarrative
        
        narrative = MediaNarrative(
            label="Rapid UAE expansion",
            type="milestone",
            sentiment="positive",
            evidence=["The company opened 3 new locations"],
            source_urls=["https://forbes.com/article"],
            frequency="moderate"
        )
        
        assert narrative.label == "Rapid UAE expansion"
        assert narrative.type == "milestone"
        assert len(narrative.evidence) == 1
        print("✓ MediaNarrative schema validates correctly")
    
    def test_press_quote_schema(self):
        """PressQuote schema validates correctly"""
        from research.press_media.schema import PressQuote
        
        quote = PressQuote(
            quote="This is the best salon in Dubai",
            source_name="Gulf News",
            source_url="https://gulfnews.com/article",
            context="Feature on top salons",
            is_paraphrased=True
        )
        
        assert quote.quote == "This is the best salon in Dubai"
        assert quote.is_paraphrased is True
        print("✓ PressQuote schema validates correctly")
    
    def test_media_source_schema(self):
        """MediaSource schema validates correctly"""
        from research.press_media.schema import MediaSource
        
        source = MediaSource(
            name="Forbes",
            domain="forbes.com",
            tier="tier1",
            article_count=3,
            most_recent_date="2024-06"
        )
        
        assert source.name == "Forbes"
        assert source.tier == "tier1"
        assert source.article_count == 3
        print("✓ MediaSource schema validates correctly")
    
    def test_press_media_snapshot_schema(self):
        """PressMediaSnapshot schema validates with all fields"""
        from research.press_media.schema import (
            PressMediaSnapshot, 
            PressArticle, 
            MediaNarrative,
            PressQuote,
            MediaSource
        )
        
        snapshot = PressMediaSnapshot(
            version="1.0",
            articles=[PressArticle(url="https://test.com", title="Test")],
            narratives=[MediaNarrative(label="Test narrative")],
            key_quotes=[PressQuote(quote="Great product")],
            media_sources=[MediaSource(name="Test Source")],
            coverage_summary=["Summary 1"],
            coverage_gaps=["Gap 1"],
            pr_opportunities=["Opportunity 1"]
        )
        
        # Verify structure
        assert snapshot.version == "1.0"
        assert len(snapshot.articles) == 1
        assert len(snapshot.narratives) == 1
        assert len(snapshot.key_quotes) == 1
        assert len(snapshot.media_sources) == 1
        assert len(snapshot.coverage_summary) == 1
        assert len(snapshot.coverage_gaps) == 1
        assert len(snapshot.pr_opportunities) == 1
        
        # Should have defaults for audit and delta
        assert snapshot.audit is not None
        assert snapshot.delta is not None
        
        print("✓ PressMediaSnapshot schema validates with all fields")


class TestExistingTabsStillWork:
    """Verify existing tabs still have working endpoints"""
    
    def test_customer_intel_endpoint(self):
        """Customer Intel endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/customer-intel/latest")
        assert response.status_code == 200
        print("✓ Customer Intel endpoint still works")
    
    def test_search_intent_endpoint(self):
        """Search Demand endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/search-intent/latest")
        assert response.status_code == 200
        print("✓ Search Demand endpoint still works")
    
    def test_seasonality_endpoint(self):
        """Seasonality endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/seasonality/latest")
        assert response.status_code == 200
        print("✓ Seasonality endpoint still works")
    
    def test_competitors_endpoint(self):
        """Competitors endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/competitors/latest")
        assert response.status_code == 200
        print("✓ Competitors endpoint still works")
    
    def test_reviews_endpoint(self):
        """Reviews endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/reviews/latest")
        assert response.status_code == 200
        print("✓ Reviews endpoint still works")
    
    def test_community_endpoint(self):
        """Community endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/research/{TEST_CAMPAIGN_ID}/community/latest")
        assert response.status_code == 200
        print("✓ Community endpoint still works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
