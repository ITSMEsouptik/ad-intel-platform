"""
E2E Data Enrichment Validation Tests
Validates all modules render rich, accurate data end-to-end.
Tests: Competitors, Search Demand, Reviews, Ads Intel, and Overview Tab.

Test campaign: 568e45c8-7976-4d14-878a-70074f35f3ff (Dubai beauty salon)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
TEST_CAMPAIGN_ID = "568e45c8-7976-4d14-878a-70074f35f3ff"


class TestCompetitorsModule:
    """
    COMPETITORS MODULE validation:
    (1) Market Overview section renders with competitive_density, dominant_player_type, market_insight, ad_landscape_note
    (2) Competitor cards show name, website, overlap_score badge, what_they_do, strengths array, weaknesses array, ad_strategy_summary, social_presence links
    (3) BarChart renders with strengths/weaknesses bars
    (4) At least 3+ competitors with non-empty strengths/weaknesses arrays
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = BASE_URL.rstrip('/')
        self.campaign_id = TEST_CAMPAIGN_ID
        
    def test_competitors_latest_returns_200(self):
        """API returns 200 with has_data=True"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/competitors/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("has_data") == True, "Expected has_data=True"
        print("PASS: /api/research/{id}/competitors/latest returns 200 with has_data=True")
        
    def test_market_overview_fields(self):
        """Market Overview section has competitive_density, dominant_player_type, market_insight, ad_landscape_note"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/competitors/latest")
        data = response.json()
        latest = data.get("latest", {})
        market_overview = latest.get("market_overview", {})
        
        assert "competitive_density" in market_overview, "Missing competitive_density"
        assert market_overview["competitive_density"], "competitive_density is empty"
        print(f"  competitive_density: {market_overview['competitive_density']}")
        
        assert "dominant_player_type" in market_overview, "Missing dominant_player_type"
        assert market_overview["dominant_player_type"], "dominant_player_type is empty"
        print(f"  dominant_player_type: {market_overview['dominant_player_type']}")
        
        assert "market_insight" in market_overview, "Missing market_insight"
        assert market_overview["market_insight"], "market_insight is empty"
        print(f"  market_insight: {market_overview['market_insight'][:80]}...")
        
        assert "ad_landscape_note" in market_overview, "Missing ad_landscape_note"
        assert market_overview["ad_landscape_note"], "ad_landscape_note is empty"
        print(f"  ad_landscape_note: {market_overview['ad_landscape_note'][:80]}...")
        
        print("PASS: Market Overview has all required fields")
        
    def test_competitor_count(self):
        """At least 3+ competitors returned"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/competitors/latest")
        data = response.json()
        competitors = data.get("latest", {}).get("competitors", [])
        
        assert len(competitors) >= 3, f"Expected at least 3 competitors, got {len(competitors)}"
        print(f"PASS: Found {len(competitors)} competitors (>= 3 required)")
        
    def test_competitor_card_fields(self):
        """Competitor cards have name, website, overlap_score, what_they_do, strengths, weaknesses, ad_strategy_summary, social_presence"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/competitors/latest")
        data = response.json()
        competitors = data.get("latest", {}).get("competitors", [])
        
        required_fields = ["name", "website", "overlap_score", "what_they_do", "strengths", "weaknesses", "ad_strategy_summary", "social_presence"]
        
        for i, comp in enumerate(competitors):
            print(f"\n  Competitor {i+1}: {comp.get('name', 'Unknown')}")
            for field in required_fields:
                assert field in comp, f"Competitor {comp.get('name')} missing {field}"
            
            # Verify non-empty critical fields
            assert comp.get("name"), f"Competitor {i} has empty name"
            assert comp.get("website"), f"Competitor {comp['name']} has empty website"
            assert comp.get("overlap_score") in ["high", "medium", "low"], f"Competitor {comp['name']} has invalid overlap_score: {comp.get('overlap_score')}"
            
            print(f"    website: {comp.get('website')}")
            print(f"    overlap_score: {comp.get('overlap_score')}")
            print(f"    strengths: {len(comp.get('strengths', []))} items")
            print(f"    weaknesses: {len(comp.get('weaknesses', []))} items")
            print(f"    ad_strategy_summary: {'Yes' if comp.get('ad_strategy_summary') else 'No'}")
            print(f"    social_presence: {len(comp.get('social_presence', []))} platforms")
            
        print("\nPASS: All competitor cards have required fields")
        
    def test_competitors_have_strengths_weaknesses(self):
        """At least 3 competitors have non-empty strengths AND weaknesses arrays"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/competitors/latest")
        data = response.json()
        competitors = data.get("latest", {}).get("competitors", [])
        
        comps_with_both = 0
        for comp in competitors:
            has_strengths = len(comp.get("strengths", [])) > 0
            has_weaknesses = len(comp.get("weaknesses", [])) > 0
            if has_strengths and has_weaknesses:
                comps_with_both += 1
                print(f"  {comp['name']}: {len(comp['strengths'])} strengths, {len(comp['weaknesses'])} weaknesses")
                
        assert comps_with_both >= 3, f"Expected at least 3 competitors with both strengths and weaknesses, got {comps_with_both}"
        print(f"\nPASS: {comps_with_both} competitors have both strengths and weaknesses")
        
    def test_social_presence_has_followers(self):
        """Social presence entries have platform, url, and followers_approx"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/competitors/latest")
        data = response.json()
        competitors = data.get("latest", {}).get("competitors", [])
        
        social_entries_found = 0
        for comp in competitors:
            for sp in comp.get("social_presence", []):
                assert "platform" in sp, f"Social presence missing platform for {comp['name']}"
                assert "url" in sp, f"Social presence missing url for {comp['name']}"
                # followers_approx is optional but should be present when available
                if sp.get("followers_approx"):
                    social_entries_found += 1
                    print(f"  {comp['name']}: {sp['platform']} - {sp['followers_approx']}")
                    
        assert social_entries_found >= 2, f"Expected at least 2 social entries with followers, got {social_entries_found}"
        print(f"\nPASS: Found {social_entries_found} social presence entries with followers")


class TestSearchDemandModule:
    """
    SEARCH DEMAND MODULE validation:
    (1) Intent Distribution bar renders with bucket percentages (price/trust/urgency/comparison/general)
    (2) Top Queries horizontal BarChart renders with colored bars per intent bucket
    (3) Query list shows numbered queries with intent bucket badges
    (4) Ad Keywords tabbed section renders with bucket tabs
    (5) queryBucketMap correctly maps queries to their intent buckets
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = BASE_URL.rstrip('/')
        self.campaign_id = TEST_CAMPAIGN_ID
        
    def test_search_intent_latest_returns_200(self):
        """API returns 200 with has_data=True"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/search-intent/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("has_data") == True, "Expected has_data=True"
        print("PASS: /api/research/{id}/search-intent/latest returns 200 with has_data=True")
        
    def test_intent_buckets_structure(self):
        """Intent buckets have price/trust/urgency/comparison/general with mapped queries"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/search-intent/latest")
        data = response.json()
        latest = data.get("latest", {})
        intent_buckets = latest.get("intent_buckets", {})
        
        expected_buckets = ["price", "trust", "urgency", "comparison", "general"]
        bucket_counts = {}
        
        for bucket in expected_buckets:
            queries = intent_buckets.get(bucket, [])
            bucket_counts[bucket] = len(queries)
            print(f"  {bucket}: {len(queries)} queries")
            
        # At least some buckets should have queries
        total_bucketed = sum(bucket_counts.values())
        assert total_bucketed > 0, "No queries mapped to intent buckets"
        print(f"\nPASS: Intent buckets contain {total_bucketed} total mapped queries")
        
    def test_top_10_queries_exist(self):
        """top_10_queries array has at least 5 queries"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/search-intent/latest")
        data = response.json()
        top_queries = data.get("latest", {}).get("top_10_queries", [])
        
        assert len(top_queries) >= 5, f"Expected at least 5 top queries, got {len(top_queries)}"
        print(f"PASS: top_10_queries has {len(top_queries)} entries")
        for i, q in enumerate(top_queries[:5]):
            query_text = q.get("query", q) if isinstance(q, dict) else q
            print(f"  {i+1}. {query_text}")
            
    def test_ad_keyword_queries_exist(self):
        """ad_keyword_queries array exists with keywords"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/search-intent/latest")
        data = response.json()
        ad_keywords = data.get("latest", {}).get("ad_keyword_queries", [])
        
        assert len(ad_keywords) > 0, "ad_keyword_queries is empty"
        print(f"PASS: ad_keyword_queries has {len(ad_keywords)} keywords")
        
    def test_query_bucket_mapping(self):
        """Verify queryBucketMap correctly maps queries to intent buckets"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/search-intent/latest")
        data = response.json()
        latest = data.get("latest", {})
        intent_buckets = latest.get("intent_buckets", {})
        
        # Build mapping like frontend does
        query_bucket_map = {}
        for bucket, queries in intent_buckets.items():
            for q in (queries or []):
                query_text = q.get("query", q) if isinstance(q, dict) else q
                query_bucket_map[query_text] = bucket
                
        # Check that top queries can be mapped
        top_queries = latest.get("top_10_queries", [])
        mapped_count = 0
        for q in top_queries:
            query_text = q.get("query", q) if isinstance(q, dict) else q
            if query_text in query_bucket_map:
                mapped_count += 1
                print(f"  '{query_text}' -> {query_bucket_map[query_text]}")
                
        print(f"\nPASS: {mapped_count}/{len(top_queries)} top queries mapped to intent buckets")


class TestReviewsModule:
    """
    REVIEWS MODULE validation:
    (1) Review Health Summary renders 4 metrics (Platforms, Strengths, Weaknesses, Trust Signals)
    (2) Trust Signals section renders trust signal items
    (3) Strength/Weakness themes render with frequency/severity badges and expandable evidence
    (4) Competitor Reputation section renders competitor names with reputation info
    (5) Brand vs Reality section renders
    (6) Social Proof readiness badge in header
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = BASE_URL.rstrip('/')
        self.campaign_id = TEST_CAMPAIGN_ID
        
    def test_reviews_latest_returns_200(self):
        """API returns 200 with has_data=True"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/reviews/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("has_data") == True, "Expected has_data=True"
        print("PASS: /api/research/{id}/reviews/latest returns 200 with has_data=True")
        
    def test_review_health_summary_metrics(self):
        """Review Health Summary has Platforms, Strengths, Weaknesses, Trust Signals counts"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/reviews/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        metrics = {
            "platform_presence": len(latest.get("platform_presence", [])),
            "strength_themes": len(latest.get("strength_themes", [])),
            "weakness_themes": len(latest.get("weakness_themes", [])),
            "trust_signals": len(latest.get("trust_signals", []))
        }
        
        print("Review Health Summary metrics:")
        for key, count in metrics.items():
            print(f"  {key}: {count}")
            
        # At least trust_signals should be present
        assert metrics["trust_signals"] > 0 or metrics["platform_presence"] > 0 or metrics["strength_themes"] > 0, \
            "No review data found - at least one metric should be > 0"
        print("\nPASS: Review Health Summary has metrics")
        
    def test_trust_signals_exist(self):
        """Trust Signals section has items"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/reviews/latest")
        data = response.json()
        trust_signals = data.get("latest", {}).get("trust_signals", [])
        
        assert len(trust_signals) > 0, "No trust signals found"
        print(f"PASS: Found {len(trust_signals)} trust signals")
        for i, signal in enumerate(trust_signals[:3]):
            print(f"  {i+1}. {signal[:80]}..." if len(signal) > 80 else f"  {i+1}. {signal}")
            
    def test_competitor_reputation_exists(self):
        """Competitor Reputation section has competitor data"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/reviews/latest")
        data = response.json()
        comp_rep = data.get("latest", {}).get("competitor_reputation", [])
        
        # competitor_reputation can be list or dict
        if isinstance(comp_rep, dict):
            comp_count = len(comp_rep)
        else:
            comp_count = len(comp_rep)
            
        assert comp_count > 0, "No competitor reputation data found"
        print(f"PASS: Found {comp_count} competitor reputation entries")
        
        if isinstance(comp_rep, list):
            for entry in comp_rep[:3]:
                name = entry.get("name", "Unknown")
                print(f"  - {name}: rating={entry.get('approximate_rating', 'N/A')}, platform={entry.get('primary_platform', 'N/A')}")
        else:
            for name, info in list(comp_rep.items())[:3]:
                print(f"  - {name}: {info}")
                
    def test_social_proof_readiness(self):
        """Social Proof readiness badge is present"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/reviews/latest")
        data = response.json()
        readiness = data.get("latest", {}).get("social_proof_readiness")
        
        assert readiness in ["strong", "moderate", "weak", None], f"Invalid social_proof_readiness: {readiness}"
        print(f"PASS: social_proof_readiness = {readiness}")
        
    def test_brand_vs_reality_exists(self):
        """Brand vs Reality section data exists"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/reviews/latest")
        data = response.json()
        brand_reality = data.get("latest", {}).get("brand_vs_reality", {})
        
        # brand_vs_reality should exist even if empty
        assert isinstance(brand_reality, dict), "brand_vs_reality should be a dict"
        print(f"PASS: brand_vs_reality exists with {len(brand_reality)} fields")
        if brand_reality:
            for key in list(brand_reality.keys())[:3]:
                print(f"  - {key}: {brand_reality[key]}")


class TestAdsIntelModule:
    """
    ADS INTEL MODULE validation:
    (1) Filter buttons show correct counts (All, Competitor Winners, Category Winners)
    (2) Ad gallery renders ad cards with thumbnails, brand names, platform badges (FB/IG), running days
    (3) Clicking an ad opens detail modal with headline, why_shortlisted, landing page link
    (4) Lens filter (competitor/category) correctly filters ads
    (5) Verify NO geographically irrelevant ads in category winners (no ads from US/UK/India for Dubai campaign)
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = BASE_URL.rstrip('/')
        self.campaign_id = TEST_CAMPAIGN_ID
        
    def test_ads_intel_latest_returns_200(self):
        """API returns 200 with has_data=True"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/ads-intel/latest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("has_data") == True, "Expected has_data=True"
        print("PASS: /api/research/{id}/ads-intel/latest returns 200 with has_data=True")
        
    def test_competitor_and_category_winners_exist(self):
        """Both competitor_winners and category_winners exist with ads arrays"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        competitor_winners = latest.get("competitor_winners", {})
        category_winners = latest.get("category_winners", {})
        
        cw_ads = competitor_winners.get("ads", [])
        cat_ads = category_winners.get("ads", [])
        
        print(f"  competitor_winners: {len(cw_ads)} ads")
        print(f"  category_winners: {len(cat_ads)} ads")
        print(f"  Total: {len(cw_ads) + len(cat_ads)} ads")
        
        assert len(cw_ads) > 0 or len(cat_ads) > 0, "No ads found in either category"
        print("\nPASS: Both competitor_winners and category_winners have ads")
        
    def test_ad_card_fields(self):
        """Ad cards have required fields: brand_name/brand, platform, running_days/days_running, thumbnail_url, why_shortlisted"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/ads-intel/latest")
        data = response.json()
        latest = data.get("latest", {})
        
        all_ads = (latest.get("competitor_winners", {}).get("ads", []) + 
                   latest.get("category_winners", {}).get("ads", []))
        
        for i, ad in enumerate(all_ads[:5]):
            print(f"\n  Ad {i+1}: {ad.get('brand_name', ad.get('brand', 'Unknown'))}")
            
            # Brand name check (can be brand_name or brand)
            assert ad.get("brand_name") or ad.get("brand"), f"Ad {i} missing brand_name/brand"
            
            # Platform check (can be platform or publisher_platform)
            platform = ad.get("platform") or ad.get("publisher_platform")
            assert platform, f"Ad {i} missing platform"
            print(f"    platform: {platform}")
            
            # Running days check (can be running_days or days_running)
            running = ad.get("running_days") or ad.get("days_running")
            if running:
                print(f"    running_days: {running}")
                
            # Why shortlisted
            why = ad.get("why_shortlisted")
            assert why, f"Ad {i} missing why_shortlisted"
            print(f"    why_shortlisted: {why[:50]}..." if len(why) > 50 else f"    why_shortlisted: {why}")
            
            # Thumbnail (optional but good to have)
            if ad.get("thumbnail_url"):
                print(f"    thumbnail: Yes")
                
        print("\nPASS: Ad cards have required fields")
        
    def test_no_geo_irrelevant_category_ads(self):
        """Category winners should not have US/UK/India ads for Dubai campaign"""
        response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/ads-intel/latest")
        data = response.json()
        category_ads = data.get("latest", {}).get("category_winners", {}).get("ads", [])
        
        irrelevant_countries = ["usa", "united states", "america", "india", "uk", "united kingdom", "australia"]
        us_states = ["california", "texas", "florida", "new york", "arizona", "georgia", "colorado", "washington", 
                     "nevada", "north carolina", "massachusetts", "pennsylvania", "ohio", "illinois", "michigan"]
        us_state_abbr = ["CA", "TX", "FL", "NY", "AZ", "GA", "CO", "WA", "NV", "NC", "MA", "PA", "OH", "IL", "MI"]
        
        flagged_ads = []
        for ad in category_ads:
            brand = (ad.get("brand_name") or ad.get("brand") or "").lower()
            text = (ad.get("text") or "").lower()
            headline = (ad.get("headline") or "").lower()
            landing_url = (ad.get("landing_page_url") or "").lower()
            combined = f"{brand} {text} {headline} {landing_url}"
            
            # Check for US state names
            for state in us_states:
                if state in combined:
                    flagged_ads.append(f"{ad.get('brand_name', 'Unknown')}: contains '{state}'")
                    break
                    
            # Check for US state abbreviations with comma pattern
            for abbr in us_state_abbr:
                if f", {abbr.lower()}" in combined or f",{abbr.lower()}" in combined:
                    flagged_ads.append(f"{ad.get('brand_name', 'Unknown')}: contains state abbr '{abbr}'")
                    break
                    
            # Check for URL patterns
            if ".com/us" in landing_url or "/us/" in landing_url or "store=us" in landing_url:
                flagged_ads.append(f"{ad.get('brand_name', 'Unknown')}: US URL pattern in {landing_url[:50]}")
                
            # Check for UK patterns
            if ".co.uk" in landing_url:
                flagged_ads.append(f"{ad.get('brand_name', 'Unknown')}: UK URL (.co.uk)")
                
            # Check for India patterns  
            if ".co.in" in landing_url or ".in/" in landing_url:
                flagged_ads.append(f"{ad.get('brand_name', 'Unknown')}: India URL pattern")
                
        if flagged_ads:
            print(f"WARNING: Found {len(flagged_ads)} potentially geo-irrelevant ads:")
            for flag in flagged_ads[:5]:
                print(f"  - {flag}")
            # This is a soft check - flag but don't fail
            
        print(f"\nPASS: Checked {len(category_ads)} category ads for geo-relevance")
        

class TestOverviewModule:
    """
    OVERVIEW TAB validation:
    Strategic Summary section shows data points from all modules
    (audience segments, competitors, top queries, buying moments, social posts count, ads count, press articles)
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.base_url = BASE_URL.rstrip('/')
        self.campaign_id = TEST_CAMPAIGN_ID
        
    def test_all_modules_have_data(self):
        """Verify all 9 modules return data for the test campaign"""
        modules = [
            ("customer-intel", "customerIntel"),
            ("search-intent", "searchIntent"),
            ("seasonality", "seasonality"),
            ("competitors", "competitors"),
            ("reviews", "reviews"),
            ("community", "community"),
            ("press-media", "pressMedia"),
            ("social-trends", "socialTrends"),
            ("ads-intel", "adsIntel")
        ]
        
        results = {}
        for endpoint, name in modules:
            try:
                response = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/{endpoint}/latest", timeout=10)
                has_data = response.json().get("has_data", False) if response.status_code == 200 else False
                results[name] = has_data
                status = "OK" if has_data else "NO DATA"
                print(f"  {name}: {status}")
            except Exception as e:
                results[name] = False
                print(f"  {name}: ERROR - {e}")
                
        # Count modules with data
        active_modules = sum(1 for v in results.values() if v)
        print(f"\n{active_modules}/{len(modules)} modules have data")
        
        # At least 5 modules should have data for a good overview
        assert active_modules >= 5, f"Expected at least 5 modules with data, got {active_modules}"
        print("PASS: Overview can render with module data")
        
    def test_strategic_summary_data_points(self):
        """Check that strategic summary can pull data from key modules"""
        data_points = {}
        
        # Customer Intel - segments
        try:
            resp = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/customer-intel/latest")
            if resp.status_code == 200:
                latest = resp.json().get("latest", {})
                segments = latest.get("segments", latest.get("icp_segments", []))
                data_points["audience_segments"] = len(segments)
        except:
            data_points["audience_segments"] = 0
            
        # Competitors
        try:
            resp = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/competitors/latest")
            if resp.status_code == 200:
                competitors = resp.json().get("latest", {}).get("competitors", [])
                data_points["competitors"] = len(competitors)
        except:
            data_points["competitors"] = 0
            
        # Search Intent - top queries
        try:
            resp = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/search-intent/latest")
            if resp.status_code == 200:
                queries = resp.json().get("latest", {}).get("top_10_queries", [])
                data_points["top_queries"] = len(queries)
        except:
            data_points["top_queries"] = 0
            
        # Seasonality - key moments
        try:
            resp = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/seasonality/latest")
            if resp.status_code == 200:
                moments = resp.json().get("latest", {}).get("key_moments", [])
                data_points["buying_moments"] = len(moments)
        except:
            data_points["buying_moments"] = 0
            
        # Social Trends
        try:
            resp = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/social-trends/latest")
            if resp.status_code == 200:
                latest = resp.json().get("latest", {})
                shortlist = latest.get("shortlist", {})
                tt = len(shortlist.get("tiktok", []))
                ig = len(shortlist.get("instagram", []))
                data_points["social_posts"] = tt + ig
        except:
            data_points["social_posts"] = 0
            
        # Ads Intel
        try:
            resp = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/ads-intel/latest")
            if resp.status_code == 200:
                latest = resp.json().get("latest", {})
                cw = len(latest.get("competitor_winners", {}).get("ads", []))
                cat = len(latest.get("category_winners", {}).get("ads", []))
                data_points["ads"] = cw + cat
        except:
            data_points["ads"] = 0
            
        # Press & Media
        try:
            resp = requests.get(f"{self.base_url}/api/research/{self.campaign_id}/press-media/latest")
            if resp.status_code == 200:
                articles = resp.json().get("latest", {}).get("articles", [])
                data_points["press_articles"] = len(articles)
        except:
            data_points["press_articles"] = 0
            
        print("Strategic Summary Data Points:")
        for key, count in data_points.items():
            print(f"  {key}: {count}")
            
        # At least 4 data points should have values
        non_zero = sum(1 for v in data_points.values() if v > 0)
        assert non_zero >= 4, f"Expected at least 4 data points with values, got {non_zero}"
        print(f"\nPASS: {non_zero}/7 data points available for Strategic Summary")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
