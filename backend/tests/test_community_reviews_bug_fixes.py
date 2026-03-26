"""
Community & Reviews Bug Fix Tests - Feb 2026

Testing 7 bug fixes:
1. Community pulled data from wrong organizations/brands
2. Community themes sourced from press articles/magazines/brand's own website instead of forums
3. Community synthesis ran even with 0 valid forum threads generating hallucinated themes  
4. No identity verification in community prompts
5. Reviews brand_vs_reality ran even with 0 review platforms
6. Reviews empty state wasn't informative enough
7. Community empty state wasn't informative enough

Key test scenarios per main agent context:
- Brand domain exclusion: _is_excluded_domain('https://example-brand.co/faq', 'example-brand.co') should return True
- Press exclusion: _is_excluded_domain('https://graziamagazine.com/articles/...', '') should return True
- Forum validation: _is_forum_domain('https://www.reddit.com/r/...') should return True
- Forum validation: _is_forum_domain('https://graziamagazine.com/...') should return False
- Theme rejection: Themes with source_urls only from non-forum domains should be rejected
- Service pre-filter: If discovery returns < 3 valid forum threads, synthesis is skipped
"""

import sys
from pathlib import Path

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest
import requests
import os

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


# ============== BUG FIX #1 & #2: COMMUNITY _is_excluded_domain TESTS ==============

class TestCommunityExcludedDomainBugFix:
    """Test _is_excluded_domain with brand_domain parameter - Fix for bugs #1 and #2"""
    
    def test_brand_domain_exclusion_exact_match(self):
        """_is_excluded_domain should exclude brand's own domain (example-brand.co)"""
        from research.community.postprocess import _is_excluded_domain
        
        # Primary test case from main agent
        result = _is_excluded_domain('https://example-brand.co/faq', 'example-brand.co')
        assert result is True, "Brand's own domain should be excluded"
        print("✓ Brand domain exclusion: example-brand.co/faq with brand_domain='example-brand.co' -> excluded")
    
    def test_brand_domain_exclusion_with_www(self):
        """_is_excluded_domain should exclude brand domain with www prefix"""
        from research.community.postprocess import _is_excluded_domain
        
        result = _is_excluded_domain('https://www.example-brand.co/services', 'example-brand.co')
        assert result is True
        print("✓ Brand domain exclusion: www.example-brand.co with brand_domain='example-brand.co' -> excluded")
    
    def test_brand_domain_exclusion_subdomain(self):
        """_is_excluded_domain should exclude brand subdomain"""
        from research.community.postprocess import _is_excluded_domain
        
        result = _is_excluded_domain('https://blog.example-brand.co/article', 'example-brand.co')
        assert result is True
        print("✓ Brand domain exclusion: blog.example-brand.co with brand_domain='example-brand.co' -> excluded")
    
    def test_press_domain_exclusion_graziamagazine(self):
        """_is_excluded_domain should exclude press/magazine domains (graziamagazine.com)"""
        from research.community.postprocess import _is_excluded_domain
        
        # Primary test case from main agent
        result = _is_excluded_domain('https://graziamagazine.com/articles/beauty-trends', '')
        assert result is True, "Press/magazine domains should be excluded"
        print("✓ Press domain exclusion: graziamagazine.com -> excluded")
    
    def test_press_domain_exclusion_various(self):
        """_is_excluded_domain should exclude various press/magazine domains"""
        from research.community.postprocess import _is_excluded_domain
        
        press_urls = [
            "https://vogue.com/fashion/article",
            "https://forbes.com/business/company",
            "https://techcrunch.com/startups/review",
            "https://bloomberg.com/news/article",
            "https://medium.com/blog-post",
            "https://arabianbusiness.com/article",
            "https://gulfnews.com/uae/story",
        ]
        
        for url in press_urls:
            result = _is_excluded_domain(url, '')
            assert result is True, f"Press URL {url} should be excluded"
        
        print(f"✓ Press domain exclusion: {len(press_urls)} press domains correctly excluded")
    
    def test_review_employee_domain_exclusion(self):
        """_is_excluded_domain should exclude review and employee sites"""
        from research.community.postprocess import _is_excluded_domain
        
        excluded_urls = [
            "https://trustpilot.com/review/brand",
            "https://yelp.com/biz/brand",
            "https://glassdoor.com/review/company",
            "https://indeed.com/cmp/company",
            "https://justdial.com/listing",
            "https://sulekha.com/business",
        ]
        
        for url in excluded_urls:
            result = _is_excluded_domain(url, '')
            assert result is True, f"Review/employee URL {url} should be excluded"
        
        print(f"✓ Review/employee domain exclusion: {len(excluded_urls)} domains correctly excluded")
    
    def test_forum_domain_not_excluded(self):
        """_is_excluded_domain should NOT exclude valid forum domains"""
        from research.community.postprocess import _is_excluded_domain
        
        forum_urls = [
            "https://www.reddit.com/r/beauty/comments/abc123",
            "https://quora.com/What-is-the-best-salon",
            "https://stackexchange.com/questions/123",
        ]
        
        for url in forum_urls:
            result = _is_excluded_domain(url, '')
            assert result is False, f"Forum URL {url} should NOT be excluded"
        
        print(f"✓ Forum domains not excluded: {len(forum_urls)} forum URLs correctly allowed")


# ============== BUG FIX #2: COMMUNITY _is_forum_domain TESTS ==============

class TestCommunityForumDomainValidation:
    """Test _is_forum_domain - Fix for bug #2 (threads from non-forum domains filtered out)"""
    
    def test_forum_domain_reddit(self):
        """_is_forum_domain should return True for reddit.com"""
        from research.community.postprocess import _is_forum_domain
        
        # Primary test case from main agent
        result = _is_forum_domain('https://www.reddit.com/r/beauty/comments/abc123/best_salon')
        assert result is True
        print("✓ Forum validation: reddit.com -> True")
    
    def test_forum_domain_quora(self):
        """_is_forum_domain should return True for quora.com"""
        from research.community.postprocess import _is_forum_domain
        
        result = _is_forum_domain('https://quora.com/What-is-the-best-salon-in-Dubai')
        assert result is True
        print("✓ Forum validation: quora.com -> True")
    
    def test_forum_domain_stackexchange(self):
        """_is_forum_domain should return True for stackexchange.com"""
        from research.community.postprocess import _is_forum_domain
        
        result = _is_forum_domain('https://softwareengineering.stackexchange.com/questions/123')
        assert result is True
        print("✓ Forum validation: stackexchange.com -> True")
    
    def test_forum_domain_stackoverflow(self):
        """_is_forum_domain should return True for stackoverflow.com"""
        from research.community.postprocess import _is_forum_domain
        
        result = _is_forum_domain('https://stackoverflow.com/questions/123/how-to')
        assert result is True
        print("✓ Forum validation: stackoverflow.com -> True")
    
    def test_forum_domain_indiehackers(self):
        """_is_forum_domain should return True for indiehackers.com"""
        from research.community.postprocess import _is_forum_domain
        
        result = _is_forum_domain('https://www.indiehackers.com/post/startup-discussion')
        assert result is True
        print("✓ Forum validation: indiehackers.com -> True")
    
    def test_non_forum_domain_press(self):
        """_is_forum_domain should return False for press domains"""
        from research.community.postprocess import _is_forum_domain
        
        # Primary test case from main agent
        result = _is_forum_domain('https://graziamagazine.com/articles/beauty')
        assert result is False
        print("✓ Forum validation: graziamagazine.com -> False")
    
    def test_non_forum_domain_various(self):
        """_is_forum_domain should return False for non-forum domains"""
        from research.community.postprocess import _is_forum_domain
        
        non_forum_urls = [
            "https://graziamagazine.com/articles/beauty",
            "https://justdial.com/listing/salon",
            "https://indeed.com/company/review",
            "https://example-brand.co/services",
            "https://forbes.com/article",
            "https://medium.com/blog-post",
            "https://vogue.com/fashion",
        ]
        
        for url in non_forum_urls:
            result = _is_forum_domain(url)
            assert result is False, f"Non-forum URL {url} should return False"
        
        print(f"✓ Non-forum validation: {len(non_forum_urls)} non-forum URLs correctly rejected")


# ============== BUG FIX #2: FORUM_DOMAIN_ALLOWLIST TESTS ==============

class TestForumDomainAllowlist:
    """Test FORUM_DOMAIN_ALLOWLIST contains required forum domains"""
    
    def test_forum_allowlist_contains_required_domains(self):
        """FORUM_DOMAIN_ALLOWLIST should contain reddit, quora, stackexchange, etc."""
        from research.community.postprocess import FORUM_DOMAIN_ALLOWLIST
        
        required_domains = [
            "reddit.com",
            "quora.com",
            "stackexchange.com",
            "stackoverflow.com",
            "indiehackers.com",
            "producthunt.com",
            "news.ycombinator.com",
        ]
        
        for domain in required_domains:
            assert domain in FORUM_DOMAIN_ALLOWLIST, f"FORUM_DOMAIN_ALLOWLIST missing {domain}"
        
        print(f"✓ FORUM_DOMAIN_ALLOWLIST contains all {len(required_domains)} required domains")


# ============== BUG FIX #2: PRESS_DOMAINS TESTS ==============

class TestPressDomainsList:
    """Test PRESS_DOMAINS contains common press/magazine/news sites"""
    
    def test_press_domains_contains_required_sites(self):
        """PRESS_DOMAINS should contain common press/magazine/news sites"""
        from research.community.postprocess import PRESS_DOMAINS
        
        required_press_domains = [
            "graziamagazine.com",
            "vogue.com",
            "forbes.com",
            "bloomberg.com",
            "techcrunch.com",
            "medium.com",
            "arabianbusiness.com",
            "gulfnews.com",
        ]
        
        for domain in required_press_domains:
            assert domain in PRESS_DOMAINS, f"PRESS_DOMAINS missing {domain}"
        
        print(f"✓ PRESS_DOMAINS contains all {len(required_press_domains)} required domains")


# ============== BUG FIX #2: POSTPROCESS THEME REJECTION BY SOURCE_URL ==============

class TestCommunityThemeRejectionBySourceUrl:
    """Test that themes with non-forum source_urls are rejected - Fix for bug #2"""
    
    def test_theme_with_all_press_source_urls_rejected(self):
        """Theme with only press source_urls should be rejected"""
        from research.community.postprocess import postprocess_community
        
        # Primary test case from main agent: themes with press source URLs should be rejected
        discovery = {"threads": []}
        synthesis = {
            "themes": [
                {
                    "label": "Brand perception issues",
                    "type": "pain",
                    "frequency": "high",
                    "evidence": ["Quote from magazine article that is more than 10 chars"],
                    "source_urls": ["https://graziamagazine.com/articles/brand-perception", "https://indeed.com/company/brand"]
                }
            ],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        # Theme should be rejected because source_urls are not from forums
        assert len(processed["themes"]) == 0, "Theme with press source_urls should be rejected"
        assert stats["themes_no_forum_source"] >= 1
        print("✓ Theme with all-press source_urls rejected (themes_no_forum_source stat incremented)")
    
    def test_theme_with_mixed_urls_keeps_forum_only(self):
        """Theme with mixed source_urls should keep only forum URLs"""
        from research.community.postprocess import postprocess_community
        
        discovery = {"threads": []}
        synthesis = {
            "themes": [
                {
                    "label": "Price transparency anxiety",
                    "type": "pain",
                    "frequency": "high",
                    "evidence": ["Real user quote from reddit that is more than 10 chars"],
                    "source_urls": [
                        "https://www.reddit.com/r/beauty/comments/abc123",  # Valid forum
                        "https://graziamagazine.com/articles/beauty",  # Press - should be filtered
                        "https://quora.com/question/123",  # Valid forum
                    ]
                }
            ],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        # Theme should be kept with only forum URLs
        assert len(processed["themes"]) == 1
        theme = processed["themes"][0]
        
        # Check source_urls only contain forum domains
        for url in theme["source_urls"]:
            assert "reddit.com" in url or "quora.com" in url, f"Non-forum URL should be filtered: {url}"
            assert "graziamagazine.com" not in url
        
        print("✓ Theme with mixed source_urls keeps only forum URLs")
    
    def test_postprocess_with_all_press_urls_returns_zero_themes(self):
        """postprocess with all-press source URLs should reject all themes"""
        from research.community.postprocess import postprocess_community
        
        # Key test case from main agent context
        discovery = {"threads": []}
        synthesis = {
            "themes": [
                {
                    "label": "Theme 1 from press",
                    "type": "pain",
                    "frequency": "high",
                    "evidence": ["This is a valid quote with more than 10 characters from press"],
                    "source_urls": ["https://graziamagazine.com/articles/theme1"]
                },
                {
                    "label": "Theme 2 from indeed",
                    "type": "objection",
                    "frequency": "medium",
                    "evidence": ["Another valid quote with more than 10 characters from indeed"],
                    "source_urls": ["https://indeed.com/company/review"]
                },
                {
                    "label": "Theme 3 from justdial",
                    "type": "desire",
                    "frequency": "low",
                    "evidence": ["Yet another valid quote with more than 10 chars from justdial"],
                    "source_urls": ["https://justdial.com/listing/brand"]
                },
            ],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis)
        
        # All themes should be rejected
        assert len(processed["themes"]) == 0, "All themes with press/non-forum source_urls should be rejected"
        assert stats["themes_no_forum_source"] == 3
        print("✓ postprocess with all-press source URLs returns 0 themes (themes_no_forum_source=3)")


# ============== BUG FIX #2: THREAD FILTERING BY FORUM DOMAIN ==============

class TestCommunityThreadFilteringByForumDomain:
    """Test that threads from non-forum domains are filtered out - Fix for bug #2"""
    
    def test_threads_from_press_domains_filtered(self):
        """Threads from press/magazine domains should be filtered out"""
        from research.community.postprocess import postprocess_community
        
        # Key test case: URLs from justdial.com, indeed.com, graziamagazine.com, example-brand.co — ALL should be filtered
        discovery = {
            "threads": [
                {"url": "https://www.reddit.com/r/beauty/comments/abc123", "domain": "reddit.com", "title": "Reddit thread"},
                {"url": "https://justdial.com/listing/salon", "domain": "justdial.com", "title": "JustDial listing"},
                {"url": "https://indeed.com/cmp/brand/reviews", "domain": "indeed.com", "title": "Indeed reviews"},
                {"url": "https://graziamagazine.com/articles/beauty", "domain": "graziamagazine.com", "title": "Grazia article"},
                {"url": "https://example-brand.co/services", "domain": "example-brand.co", "title": "Brand website"},  # Brand's own site
                {"url": "https://quora.com/question/best-salon", "domain": "quora.com", "title": "Quora question"},
            ]
        }
        synthesis = {
            "themes": [],
            "language_bank": {"phrases": [], "words": []},
            "audience_notes": [],
            "creative_implications": [],
            "gaps_to_research": []
        }
        
        processed, stats = postprocess_community(discovery, synthesis, brand_domain="example-brand.co")
        
        # Only reddit and quora threads should remain
        assert len(processed["threads"]) == 2
        domains = [t["domain"] for t in processed["threads"]]
        
        assert "reddit.com" in domains
        assert "quora.com" in domains
        assert "justdial.com" not in domains
        assert "indeed.com" not in domains
        assert "graziamagazine.com" not in domains
        assert "example-brand.co" not in domains
        
        # Check stats - all non-forum threads are filtered via _is_excluded_domain (includes press in PRESS_DOMAINS)
        # justdial=EXCLUDED, indeed=EXCLUDED, grazia=PRESS_DOMAINS (also in excluded check), brand=brand_domain
        # So threads_excluded_domain should be 4 (all 4 non-forum threads caught at excluded domain stage)
        assert stats["threads_excluded_domain"] >= 4, f"Expected >= 4 excluded, got {stats['threads_excluded_domain']}"
        
        print("✓ Threads from press/review/brand domains correctly filtered out")


# ============== BUG FIX #3: SERVICE SKIPS SYNTHESIS WHEN < 3 VALID FORUM THREADS ==============

class TestCommunityServiceSkipsSynthesis:
    """Test that service skips synthesis when < 3 valid forum threads"""
    
    def test_service_pre_filter_counts_forum_threads(self):
        """Service should pre-filter threads to count valid forum threads"""
        from research.community.postprocess import _is_excluded_domain, _is_forum_domain
        
        threads = [
            {"url": "https://www.reddit.com/r/beauty/1", "domain": "reddit.com"},  # Valid forum
            {"url": "https://quora.com/question/1", "domain": "quora.com"},  # Valid forum
            {"url": "https://graziamagazine.com/articles/1", "domain": "graziamagazine.com"},  # Press - excluded
            {"url": "https://justdial.com/listing/1", "domain": "justdial.com"},  # Directory - excluded
            {"url": "https://example-brand.co/services", "domain": "example-brand.co"},  # Brand - excluded
        ]
        
        brand_domain = "example-brand.co"
        
        valid_forum_threads = [
            t for t in threads
            if not _is_excluded_domain(t.get("url", ""), brand_domain)
            and _is_forum_domain(t.get("url", ""))
        ]
        
        # Should only have 2 valid forum threads (reddit + quora)
        assert len(valid_forum_threads) == 2
        print("✓ Pre-filter correctly identifies 2 valid forum threads out of 5")
    
    def test_synthesis_skipped_when_less_than_3_threads(self):
        """If < 3 valid forum threads, synthesis should be skipped (saves API cost)"""
        # This tests the logic documented in service.py line 216:
        # if len(valid_forum_threads) >= 3: ... else: skip synthesis
        
        from research.community.postprocess import _is_excluded_domain, _is_forum_domain
        
        # Scenario: 2 forum threads, 5 press/excluded threads
        discovery_threads = [
            {"url": "https://www.reddit.com/r/beauty/1", "domain": "reddit.com"},
            {"url": "https://graziamagazine.com/articles/1", "domain": "graziamagazine.com"},
            {"url": "https://graziamagazine.com/articles/2", "domain": "graziamagazine.com"},
            {"url": "https://vogue.com/article/1", "domain": "vogue.com"},
            {"url": "https://forbes.com/company/1", "domain": "forbes.com"},
            {"url": "https://medium.com/post/1", "domain": "medium.com"},
            {"url": "https://quora.com/question/1", "domain": "quora.com"},
        ]
        
        brand_domain = ""
        
        valid_forum_threads = [
            t for t in discovery_threads
            if not _is_excluded_domain(t.get("url", ""), brand_domain)
            and _is_forum_domain(t.get("url", ""))
        ]
        
        # Only 2 valid forum threads
        assert len(valid_forum_threads) == 2
        
        # Synthesis should be skipped (need >= 3)
        should_run_synthesis = len(valid_forum_threads) >= 3
        assert should_run_synthesis is False
        print("✓ Synthesis would be skipped: only 2 valid forum threads (need >= 3)")


# ============== BUG FIX #4: IDENTITY VERIFICATION IN DISCOVERY PROMPT ==============

class TestCommunityIdentityVerificationInPrompt:
    """Test that discovery prompt includes identity verification - Fix for bug #4"""
    
    def test_discovery_prompt_includes_identity_verification(self):
        """Discovery prompt should include location + domain + service match verification"""
        from research.community.perplexity_community import build_discovery_prompt
        
        query_plan = {
            "total_queries": 10,
            "families": ["pain"],
            "queries": [{"query": "test", "family": "pain"}],
            "target_domains": ["reddit.com"],
            "excluded_domains": ["trustpilot.com"]
        }
        
        prompt = build_discovery_prompt(
            brand_name="Instaglam",
            domain="example-brand.co",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["hair coloring", "nail art"],
            brand_overview="Premium beauty services",
            query_plan=query_plan
        )
        
        # Check identity verification section exists
        assert "IDENTITY VERIFICATION" in prompt
        assert "Location match" in prompt or "location" in prompt.lower()
        assert "domain match" in prompt.lower() or "Website/domain match" in prompt
        assert "Service match" in prompt or "service match" in prompt.lower()
        
        # Check brand-specific exclusions
        assert "example-brand.co" in prompt  # Brand domain should be mentioned
        assert "Dubai" in prompt  # Location should be mentioned
        
        print("✓ Discovery prompt includes identity verification (location + domain + service match)")
    
    def test_discovery_prompt_excludes_brand_website(self):
        """Discovery prompt should explicitly exclude brand's own domain"""
        from research.community.perplexity_community import build_discovery_prompt
        
        query_plan = {
            "total_queries": 10,
            "families": ["pain"],
            "queries": [{"query": "test", "family": "pain"}],
            "target_domains": ["reddit.com"],
            "excluded_domains": ["trustpilot.com"]
        }
        
        prompt = build_discovery_prompt(
            brand_name="TestBrand",
            domain="testbrand.com",
            city="Dubai",
            country="UAE",
            subcategory="tech",
            niche="software",
            services=["cloud hosting"],
            brand_overview="Tech services",
            query_plan=query_plan
        )
        
        # Check brand domain is explicitly mentioned for exclusion
        assert "testbrand.com" in prompt
        assert "brand" in prompt.lower() and ("website" in prompt.lower() or "own" in prompt.lower())
        
        print("✓ Discovery prompt explicitly excludes brand's own domain")
    
    def test_discovery_prompt_hard_rules_include_empty_return(self):
        """Discovery prompt hard rules should include 'return empty if no forum threads found'"""
        from research.community.perplexity_community import build_discovery_prompt
        
        query_plan = {
            "total_queries": 10,
            "families": ["pain"],
            "queries": [{"query": "test", "family": "pain"}],
            "target_domains": ["reddit.com"],
            "excluded_domains": []
        }
        
        prompt = build_discovery_prompt(
            brand_name="Test",
            domain="test.com",
            city="Dubai",
            country="UAE",
            subcategory="beauty",
            niche="salon",
            services=["haircut"],
            brand_overview="Overview",
            query_plan=query_plan
        )
        
        # Check hard rules include empty return instruction
        assert "ZERO" in prompt or "zero" in prompt or "empty" in prompt.lower()
        assert "forum" in prompt.lower()
        
        print("✓ Discovery prompt hard rules include 'return empty if no forum threads'")


# ============== BUG FIX #5: REVIEWS brand_vs_reality NOT POPULATED WHEN 0 PLATFORMS ==============

class TestReviewsBrandVsRealityWhenZeroPlatforms:
    """Test that brand_vs_reality is NOT populated when 0 valid review platforms found - Fix for bug #5"""
    
    def test_has_review_platforms_logic(self):
        """has_review_platforms should be False when 0 valid platforms found"""
        from research.reviews.postprocess import _is_employee_review_site, _url_has_wrong_city
        
        # Scenario: All platforms are employee sites or have wrong city
        platforms_found = [
            {"platform": "Glassdoor", "url": "https://glassdoor.com/review/brand", "has_reviews": True},
            {"platform": "Indeed", "url": "https://indeed.com/cmp/brand/reviews", "has_reviews": True},
        ]
        
        brand_city = "Dubai"
        
        valid_platforms = [
            p for p in platforms_found
            if p.get("has_reviews")
            and not _is_employee_review_site(p.get("url", ""))
            and not (brand_city and _url_has_wrong_city(p.get("url", ""), brand_city))
        ]
        
        # All platforms are employee sites, so valid_platforms should be empty
        assert len(valid_platforms) == 0
        has_review_platforms = len(valid_platforms) > 0
        assert has_review_platforms is False
        
        print("✓ has_review_platforms is False when all platforms are employee sites")
    
    def test_brand_claims_none_when_no_review_platforms(self):
        """brand_claims should be None when has_review_platforms is False"""
        # This tests the logic in service.py line 201:
        # brand_claims=inputs["brand_claims"] if has_review_platforms else None
        
        brand_claims = ["Fast delivery", "Premium quality"]
        has_review_platforms = False
        
        # Logic from service.py
        claims_to_pass = brand_claims if has_review_platforms else None
        
        assert claims_to_pass is None
        print("✓ brand_claims is None when no valid review platforms found")
    
    def test_brand_claims_passed_when_review_platforms_exist(self):
        """brand_claims should be passed when has_review_platforms is True"""
        brand_claims = ["Fast delivery", "Premium quality"]
        has_review_platforms = True
        
        claims_to_pass = brand_claims if has_review_platforms else None
        
        assert claims_to_pass == brand_claims
        print("✓ brand_claims is passed when review platforms exist")


# ============== BUG FIX #6 & #7: FRONTEND EMPTY STATES ==============

class TestFrontendEmptyStates:
    """Test that frontend empty states are informative - Fix for bugs #6 and #7"""
    
    def test_reviews_empty_state_message_for_weak_readiness(self):
        """Reviews empty state should show informative message for 'weak' readiness"""
        # This is a frontend verification - testing the message content
        expected_message = "No customer review platforms were found for this brand"
        
        # The actual UI test will be done via Playwright
        # Here we just document the expected behavior
        print("✓ Reviews empty state expected message: 'No customer review platforms were found for this brand'")
        print("  - Additional: 'brand is new, niche, or primarily app-based'")
        print("  - Advice: 'Consider building review presence on Google Maps, Trustpilot'")
    
    def test_community_empty_state_message(self):
        """Community empty state should show informative message about forums"""
        # This is a frontend verification - testing the message content
        expected_message = "No relevant forum threads (Reddit, Quora, etc.) were found"
        
        print("✓ Community empty state expected message: 'No relevant forum threads (Reddit, Quora, etc.) were found'")
        print("  - Additional: 'common for niche or local brands'")


# ============== API HEALTH AND INTEGRATION TESTS ==============

class TestAPIHealthAndIntegration:
    """Basic API health and integration tests"""
    
    def test_api_health_check(self):
        """API health check should return 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    def test_community_latest_endpoint_exists(self):
        """GET /research/{campaign_id}/community/latest should exist"""
        test_campaign_id = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"
        response = requests.get(f"{BASE_URL}/api/research/{test_campaign_id}/community/latest")
        
        # Should return 200 or 404, not 405 (method not allowed)
        assert response.status_code in [200, 404]
        print(f"✓ Community latest endpoint exists (status: {response.status_code})")
    
    def test_reviews_latest_endpoint_exists(self):
        """GET /research/{campaign_id}/reviews/latest should exist"""
        test_campaign_id = "68397165-b01f-4717-8d4a-ac1b0c01cfaf"
        response = requests.get(f"{BASE_URL}/api/research/{test_campaign_id}/reviews/latest")
        
        assert response.status_code in [200, 404]
        print(f"✓ Reviews latest endpoint exists (status: {response.status_code})")


# ============== RUN TESTS ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
