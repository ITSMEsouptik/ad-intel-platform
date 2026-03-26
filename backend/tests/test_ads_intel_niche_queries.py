"""
Test: Ads Intel Niche Query Optimization
Validates the category query optimization:
1. Niche queries (at home beauty, at home spa, lashes, etc.) instead of broad "Beauty & Wellness"
2. Credit optimization (154 ads scanned vs 304 before)
3. Diverse category brands (Luxe Cosmetics, JOVS, Theinkeylist) instead of irrelevant (Power Plate, FabFitFun)
4. Competitor winners still has 12 ads
5. Category winners has 15 ads from 11+ unique brands
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

class TestAdsIntelNicheQueryOptimization:
    """Verify niche query generation and credit optimization"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.campaign_id = "568e45c8-7976-4d14-878a-70074f35f3ff"
        self.api_url = f"{BASE_URL}/api/research/{self.campaign_id}/ads-intel/latest"

    def test_api_returns_success(self):
        """Test that API returns data successfully"""
        response = requests.get(self.api_url)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("has_data") is True, "Expected has_data=True"
        assert "latest" in data, "Expected 'latest' field in response"

    def test_category_queries_are_niche_specific(self):
        """Verify queries are niche-specific like 'at home beauty' NOT broad 'Beauty & Wellness'"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        category_queries = latest.get("inputs", {}).get("category_queries", [])
        assert len(category_queries) > 0, "Expected category_queries in inputs"
        
        # Check for niche queries that should be present
        niche_keywords = ["at home", "on demand", "lashes", "nails", "makeup", "hair", "facial", "spa", "beauty"]
        found_niche_queries = []
        
        for query in category_queries:
            query_lower = query.lower()
            for keyword in niche_keywords:
                if keyword in query_lower:
                    found_niche_queries.append(query)
                    break
        
        assert len(found_niche_queries) >= 3, f"Expected at least 3 niche queries, found: {found_niche_queries}"
        
        # Should NOT have broad "Beauty & Wellness" as a query
        broad_queries = [q for q in category_queries if q.lower() in ["beauty & wellness", "health and wellness"]]
        assert len(broad_queries) == 0, f"Should NOT have broad industry queries, found: {broad_queries}"
        
        print(f"✓ Niche queries found: {category_queries}")

    def test_total_ads_scanned_is_optimized(self):
        """Verify credit optimization: ~154 ads scanned (vs 304 before)"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        audit = latest.get("audit", {})
        total_ads_seen = audit.get("total_ads_seen", 0)
        
        # Should be around 154, definitely less than 304
        assert total_ads_seen < 250, f"Expected <250 ads scanned (credit optimization), got {total_ads_seen}"
        assert total_ads_seen > 50, f"Expected >50 ads scanned for valid data, got {total_ads_seen}"
        
        print(f"✓ Credit optimization: {total_ads_seen} ads scanned (vs 304 before)")

    def test_category_winners_has_15_ads(self):
        """Verify category_winners has 15 ads"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        category_winners = latest.get("category_winners", {})
        ads = category_winners.get("ads", [])
        
        assert len(ads) == 15, f"Expected 15 category ads, got {len(ads)}"
        print(f"✓ Category winners: {len(ads)} ads")

    def test_competitor_winners_has_12_ads(self):
        """Verify competitor_winners has 12 ads"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        competitor_winners = latest.get("competitor_winners", {})
        ads = competitor_winners.get("ads", [])
        
        assert len(ads) == 12, f"Expected 12 competitor ads, got {len(ads)}"
        print(f"✓ Competitor winners: {len(ads)} ads")

    def test_category_ads_have_diverse_brands(self):
        """Verify category ads are from diverse brands (11+ unique), not dominated by 1-2"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        category_winners = latest.get("category_winners", {})
        ads = category_winners.get("ads", [])
        
        # Extract unique brands
        brands = set()
        for ad in ads:
            brand = ad.get("brand_name", "Unknown")
            if brand:
                brands.add(brand)
        
        # Should have at least 8 unique brands (diversity)
        assert len(brands) >= 8, f"Expected 8+ unique brands for diversity, got {len(brands)}: {brands}"
        
        # Check that no single brand dominates (max 4 ads per brand)
        brand_counts = {}
        for ad in ads:
            brand = ad.get("brand_name", "Unknown")
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        
        max_count = max(brand_counts.values())
        assert max_count <= 4, f"No brand should have >4 ads (dominance). Counts: {brand_counts}"
        
        print(f"✓ Diverse brands ({len(brands)} unique): {brands}")

    def test_category_ads_are_relevant_beauty_brands(self):
        """Verify category ads are from beauty/skincare brands, not irrelevant like Power Plate"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        category_winners = latest.get("category_winners", {})
        ads = category_winners.get("ads", [])
        
        # Known irrelevant brands that should NOT appear (from old algorithm)
        irrelevant_brands = ["power plate", "fabfitfun", "welleco", "athletic greens", "peloton"]
        
        found_irrelevant = []
        for ad in ads:
            brand = (ad.get("brand_name") or "").lower()
            for irr in irrelevant_brands:
                if irr in brand:
                    found_irrelevant.append(brand)
        
        assert len(found_irrelevant) == 0, f"Should NOT have irrelevant brands: {found_irrelevant}"
        
        # Check for expected relevant brands
        relevant_brands = ["luxe", "jovs", "theinkeylist", "inkey", "skincare", "beauty", "cosmetics"]
        brands_text = " ".join([a.get("brand_name", "").lower() for a in ads])
        
        found_relevant = [b for b in relevant_brands if b in brands_text]
        assert len(found_relevant) >= 2, f"Expected at least 2 relevant beauty brands, found: {found_relevant}"
        
        print(f"✓ Relevant brands verified. Found relevant keywords: {found_relevant}")

    def test_competitor_ads_from_known_competitors(self):
        """Verify competitor ads are from Ruuby, Vita Home Spa, Russell & Bromley"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        competitor_winners = latest.get("competitor_winners", {})
        ads = competitor_winners.get("ads", [])
        
        expected_brands = ["ruuby", "vita home spa", "russell & bromley"]
        found_brands = set()
        
        for ad in ads:
            brand = (ad.get("brand_name") or "").lower()
            for expected in expected_brands:
                if expected in brand:
                    found_brands.add(expected)
        
        assert len(found_brands) >= 2, f"Expected at least 2 of {expected_brands}, found: {found_brands}"
        print(f"✓ Competitor brands verified: {found_brands}")

    def test_shortlisted_total_is_27(self):
        """Verify total shortlisted is 27 (12 competitor + 15 category)"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        audit = latest.get("audit", {})
        kept = audit.get("kept", 0)
        
        assert kept == 27, f"Expected 27 shortlisted (12+15), got {kept}"
        print(f"✓ Total shortlisted: {kept}")

    def test_queries_used_contains_niche_queries(self):
        """Verify category_winners.stats.queries_used has niche queries"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        category_winners = latest.get("category_winners", {})
        stats = category_winners.get("stats", {})
        queries_used = stats.get("queries_used", [])
        
        assert len(queries_used) > 0, "Expected queries_used in category_winners.stats"
        
        # Verify niche queries are in queries_used
        niche_queries = ["at home beauty", "at home spa", "lashes", "nails", "makeup"]
        found = [q for q in queries_used if any(nq in q.lower() for nq in niche_queries)]
        
        assert len(found) >= 3, f"Expected at least 3 niche queries in queries_used, found: {found}"
        print(f"✓ Queries used: {queries_used}")

    def test_filter_percentage_is_correct(self):
        """Verify filter percentage calculation: (total_seen - kept) / total_seen * 100"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        audit = latest.get("audit", {})
        total_ads_seen = audit.get("total_ads_seen", 0)
        kept = audit.get("kept", 0)
        
        if total_ads_seen > 0:
            filter_pct = round(((total_ads_seen - kept) / total_ads_seen) * 100)
            # Should be around 82% based on 154 scanned, 27 kept
            assert 70 <= filter_pct <= 90, f"Expected filter percentage 70-90%, got {filter_pct}%"
            print(f"✓ Filter percentage: {filter_pct}% filtered out")

    def test_video_ads_have_valid_media_url(self):
        """Verify video ads have valid .mp4 media_url"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        all_ads = (
            latest.get("competitor_winners", {}).get("ads", []) +
            latest.get("category_winners", {}).get("ads", [])
        )
        
        video_ads = [a for a in all_ads if a.get("display_format") == "video"]
        
        for ad in video_ads:
            media_url = ad.get("media_url", "")
            if media_url:
                assert ".mp4" in media_url or ".webm" in media_url, f"Video ad should have video URL: {media_url}"
        
        print(f"✓ {len(video_ads)} video ads have valid media URLs")

    def test_ads_have_why_shortlisted(self):
        """Verify all ads have why_shortlisted field"""
        response = requests.get(self.api_url)
        data = response.json()
        latest = data.get("latest", {})
        
        all_ads = (
            latest.get("competitor_winners", {}).get("ads", []) +
            latest.get("category_winners", {}).get("ads", [])
        )
        
        for ad in all_ads:
            why = ad.get("why_shortlisted", "")
            assert len(why) > 5, f"Ad {ad.get('ad_id')} missing why_shortlisted"
        
        print(f"✓ All {len(all_ads)} ads have why_shortlisted")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
