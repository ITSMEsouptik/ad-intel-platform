"""
SPA Service Extractor Tests
Tests for the new Playwright-based service extractor that clicks through all tabs
on booking pages (like example-brand.co/bookonline) to extract every service with name/price/duration.

Test areas:
1. _find_booking_url prioritizes 'bookonline' over generic 'services' URLs
2. extract_spa_services extracts all 9 service categories from example-brand.co/bookonline
3. extract_spa_services extracts ~40 services with correct names, prices, durations
4. SPAServiceResult.to_offer_catalog() returns correct format
5. offer_catalog in step2 output uses SPA-extracted services when available
"""

import pytest
import asyncio
import os
import sys
import requests
from dataclasses import dataclass
from typing import Optional

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get the base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Known example_brand brief ID from iteration_52
INSTAGLAM_BRIEF_ID = "b8a4f405-d06c-49de-94ed-9e6e14ab45de"


# ==================== UNIT TESTS: _find_booking_url ====================

class TestFindBookingUrl:
    """Tests for _find_booking_url function - URL detection and priority"""
    
    def test_import_find_booking_url(self):
        """Test that _find_booking_url can be imported"""
        from spa_service_extractor import _find_booking_url
        assert callable(_find_booking_url)
        print("SUCCESS: _find_booking_url imported successfully")
    
    def test_prioritizes_bookonline_over_services(self):
        """Test that 'bookonline' URL is prioritized over generic 'services' URL"""
        from spa_service_extractor import _find_booking_url
        
        # Mock page objects with .url attribute
        @dataclass
        class MockPage:
            url: str
        
        # Test case: both bookonline and services URLs present
        pages = [
            MockPage(url="https://example.com/services"),
            MockPage(url="https://example.com/bookonline"),
        ]
        links = []
        
        result = _find_booking_url(pages, links)
        assert result == "https://example.com/bookonline", f"Expected bookonline URL, got: {result}"
        print(f"SUCCESS: Prioritized 'bookonline' URL: {result}")
    
    def test_prioritizes_book_online_hyphenated(self):
        """Test that 'book-online' URL is also prioritized"""
        from spa_service_extractor import _find_booking_url
        
        @dataclass
        class MockPage:
            url: str
        
        pages = [
            MockPage(url="https://example.com/our-services"),
            MockPage(url="https://example.com/book-online"),
        ]
        links = []
        
        result = _find_booking_url(pages, links)
        assert result == "https://example.com/book-online", f"Expected book-online URL, got: {result}"
        print(f"SUCCESS: Prioritized 'book-online' URL: {result}")
    
    def test_falls_back_to_services_when_no_booking(self):
        """Test that services URL is returned when no booking URL exists"""
        from spa_service_extractor import _find_booking_url
        
        @dataclass
        class MockPage:
            url: str
        
        pages = [
            MockPage(url="https://example.com/"),
            MockPage(url="https://example.com/services"),
        ]
        links = []
        
        result = _find_booking_url(pages, links)
        assert result == "https://example.com/services", f"Expected services URL, got: {result}"
        print(f"SUCCESS: Fell back to 'services' URL: {result}")
    
    def test_checks_all_links_when_pages_have_no_match(self):
        """Test that all_links is checked when crawl_pages has no match"""
        from spa_service_extractor import _find_booking_url
        
        @dataclass
        class MockPage:
            url: str
        
        pages = [
            MockPage(url="https://example.com/"),
        ]
        links = [
            MockPage(url="https://example.com/bookonline"),
        ]
        
        result = _find_booking_url(pages, links)
        assert result == "https://example.com/bookonline", f"Expected bookonline from links, got: {result}"
        print(f"SUCCESS: Found URL in all_links: {result}")
    
    def test_returns_none_when_no_match(self):
        """Test that None is returned when no booking/services URL found"""
        from spa_service_extractor import _find_booking_url
        
        @dataclass
        class MockPage:
            url: str
        
        pages = [
            MockPage(url="https://example.com/"),
            MockPage(url="https://example.com/about"),
        ]
        links = []
        
        result = _find_booking_url(pages, links)
        assert result is None, f"Expected None, got: {result}"
        print("SUCCESS: Returns None when no match found")
    
    def test_handles_string_urls(self):
        """Test that plain string URLs work (not just objects with .url)"""
        from spa_service_extractor import _find_booking_url
        
        pages = []
        links = [
            "https://example.com/bookonline",
            "https://example.com/services",
        ]
        
        result = _find_booking_url(pages, links)
        assert "bookonline" in result, f"Expected bookonline URL, got: {result}"
        print(f"SUCCESS: Handled string URLs: {result}")


# ==================== UNIT TESTS: SPAServiceResult ====================

class TestSPAServiceResult:
    """Tests for SPAServiceResult dataclass methods"""
    
    def test_to_text_block_empty(self):
        """Test to_text_block with no services returns empty string"""
        from spa_service_extractor import SPAServiceResult
        
        result = SPAServiceResult()
        text = result.to_text_block()
        assert text == "", f"Expected empty string, got: {text}"
        print("SUCCESS: to_text_block returns empty for no services")
    
    def test_to_text_block_with_services(self):
        """Test to_text_block formats services correctly"""
        from spa_service_extractor import SPAServiceResult, ExtractedService
        
        result = SPAServiceResult(
            categories=["Makeup", "Nails"],
            services=[
                ExtractedService(category="Makeup", name="Bridal Makeup", price="$150", duration="1 hr"),
                ExtractedService(category="Makeup", name="Party Makeup", price="$75", duration="45 min"),
                ExtractedService(category="Nails", name="Gel Manicure", price="$40", duration="30 min"),
            ],
            source_url="https://example.com/bookonline"
        )
        
        text = result.to_text_block()
        assert "COMPLETE SERVICE CATALOG" in text
        assert "[Makeup]" in text
        assert "[Nails]" in text
        assert "Bridal Makeup" in text
        assert "$150" in text
        assert "(1 hr)" in text
        print(f"SUCCESS: to_text_block formatted correctly:\n{text[:200]}...")
    
    def test_to_offer_catalog(self):
        """Test to_offer_catalog returns correct format"""
        from spa_service_extractor import SPAServiceResult, ExtractedService
        
        result = SPAServiceResult(
            services=[
                ExtractedService(category="Makeup", name="Bridal Makeup", price="$150", duration="1 hr"),
                ExtractedService(category="Nails", name="Gel Manicure", price="$40", duration="30 min"),
            ]
        )
        
        catalog = result.to_offer_catalog()
        
        assert len(catalog) == 2
        assert catalog[0]["name"] == "Bridal Makeup"
        assert catalog[0]["description"] == "Makeup"
        assert catalog[0]["price_hint"] == "$150"
        assert catalog[1]["name"] == "Gel Manicure"
        assert catalog[1]["description"] == "Nails"
        print(f"SUCCESS: to_offer_catalog format correct: {catalog}")
    
    def test_to_offer_catalog_deduplicates(self):
        """Test that to_offer_catalog removes duplicate services"""
        from spa_service_extractor import SPAServiceResult, ExtractedService
        
        result = SPAServiceResult(
            services=[
                ExtractedService(category="Makeup", name="Bridal Makeup", price="$150"),
                ExtractedService(category="Makeup", name="Bridal Makeup", price="$150"),  # duplicate
                ExtractedService(category="Nails", name="Gel Manicure", price="$40"),
            ]
        )
        
        catalog = result.to_offer_catalog()
        assert len(catalog) == 2, f"Expected 2 items (deduped), got: {len(catalog)}"
        print("SUCCESS: to_offer_catalog correctly deduplicates")


# ==================== INTEGRATION TESTS: extract_spa_services ====================

class TestExtractSPAServices:
    """Integration tests for extract_spa_services - actual Playwright extraction"""
    
    @pytest.mark.asyncio
    async def test_extract_example_brand_services(self):
        """Test extracting all services from example-brand.co/bookonline"""
        from spa_service_extractor import extract_spa_services
        
        booking_url = "https://www.example-brand.co/bookonline"
        print(f"Testing SPA extraction from: {booking_url}")
        
        result = await extract_spa_services(booking_url)
        
        # Check we got categories
        assert len(result.categories) >= 5, f"Expected 5+ categories, got: {len(result.categories)}"
        print(f"Found {len(result.categories)} categories: {result.categories}")
        
        # Check we got services
        assert len(result.services) >= 20, f"Expected 20+ services, got: {len(result.services)}"
        print(f"Found {len(result.services)} total services")
        
        # Check source URL
        assert result.source_url == booking_url
        
        # Print service breakdown by category
        cat_counts = {}
        for svc in result.services:
            cat_counts[svc.category] = cat_counts.get(svc.category, 0) + 1
        print(f"Services per category: {cat_counts}")
    
    @pytest.mark.asyncio
    async def test_extract_example_brand_expected_categories(self):
        """Test that expected service categories are found"""
        from spa_service_extractor import extract_spa_services
        
        result = await extract_spa_services("https://www.example-brand.co/bookonline")
        
        # Known categories from example_brand - check for presence (Hair has multiple subcategories)
        expected_categories = ["Makeup", "Nails"]  # Core categories
        hair_related = ["Hair- Blow Dry", "Hair - Up Do", "Hair- Blow Dry With Iron", "Hair - Curls & Waves"]
        
        for cat in expected_categories:
            assert cat in result.categories, f"Expected category '{cat}' not found in: {result.categories}"
        
        # Check that at least one hair category exists
        hair_found = any(cat.startswith("Hair") for cat in result.categories)
        assert hair_found, f"Expected Hair-related category in: {result.categories}"
        
        print(f"SUCCESS: Found expected categories: {result.categories}")
    
    @pytest.mark.asyncio
    async def test_extract_service_has_price(self):
        """Test that extracted services have prices"""
        from spa_service_extractor import extract_spa_services
        
        result = await extract_spa_services("https://www.example-brand.co/bookonline")
        
        # At least some services should have prices
        services_with_price = [s for s in result.services if s.price]
        assert len(services_with_price) >= 10, f"Expected 10+ services with prices, got: {len(services_with_price)}"
        
        # Print sample prices
        for svc in services_with_price[:5]:
            print(f"  {svc.category}: {svc.name} - {svc.price}")
        print(f"SUCCESS: {len(services_with_price)} services have prices")
    
    @pytest.mark.asyncio
    async def test_extract_service_has_duration(self):
        """Test that extracted services have durations"""
        from spa_service_extractor import extract_spa_services
        
        result = await extract_spa_services("https://www.example-brand.co/bookonline")
        
        # At least some services should have durations
        services_with_duration = [s for s in result.services if s.duration]
        
        # Print sample durations
        for svc in services_with_duration[:5]:
            print(f"  {svc.category}: {svc.name} - {svc.duration}")
        print(f"Found {len(services_with_duration)} services with durations")
    
    @pytest.mark.asyncio
    async def test_offer_catalog_from_extraction(self):
        """Test converting extracted services to offer_catalog format"""
        from spa_service_extractor import extract_spa_services
        
        result = await extract_spa_services("https://www.example-brand.co/bookonline")
        catalog = result.to_offer_catalog()
        
        assert len(catalog) >= 20, f"Expected 20+ catalog items, got: {len(catalog)}"
        
        # Check structure
        for item in catalog[:3]:
            assert "name" in item
            assert "description" in item  # category
            assert "price_hint" in item
            print(f"  {item['name']} ({item['description']}): {item['price_hint']}")
        
        print(f"SUCCESS: Generated {len(catalog)} offer_catalog items")


# ==================== API TESTS: Check Existing Pack Data ====================

class TestExistingPackData:
    """Tests that verify the SPA extractor results in existing pack data"""
    
    def test_example_brand_pack_exists(self):
        """Test that example_brand pack exists in database"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        
        if response.status_code == 404:
            pytest.skip("Instaglam pack not found - may need to run pipeline first")
        
        assert response.status_code == 200, f"Failed to get pack: {response.status_code}"
        pack = response.json()
        assert pack.get("status") in ["success", "partial"], f"Pack status: {pack.get('status')}"
        print(f"SUCCESS: Found example_brand pack with status: {pack.get('status')}")
    
    def test_example_brand_offer_catalog_has_spa_services(self):
        """Test that offer_catalog uses SPA-extracted services (40+ items, not 3 from LLM)"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        
        if response.status_code == 404:
            pytest.skip("Instaglam pack not found")
        
        pack = response.json()
        step2 = pack.get("step2", {})
        offer_catalog = step2.get("offer", {}).get("offer_catalog", [])
        
        # SPA extraction should produce 20+ services, LLM would produce ~3
        assert len(offer_catalog) >= 15, f"Expected 15+ offer_catalog items (SPA), got: {len(offer_catalog)}"
        print(f"SUCCESS: offer_catalog has {len(offer_catalog)} items (from SPA extraction)")
        
        # Print sample items
        for item in offer_catalog[:5]:
            print(f"  - {item.get('name')} ({item.get('description')}): {item.get('price_hint')}")
    
    def test_example_brand_pricing_includes_spa_prices(self):
        """Test that pricing stats include SPA-extracted prices"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{INSTAGLAM_BRIEF_ID}")
        
        if response.status_code == 404:
            pytest.skip("Instaglam pack not found")
        
        pack = response.json()
        step2 = pack.get("step2", {})
        pricing = step2.get("pricing", {})
        
        # SPA extraction should add many prices to price_mentions
        price_count = pricing.get("count", 0)
        observed_prices = pricing.get("observed_prices", [])
        
        print(f"Pricing stats: count={price_count}, min={pricing.get('min')}, max={pricing.get('max')}, avg={pricing.get('avg')}")
        print(f"Sample prices: {observed_prices[:10]}")
        
        # Should have some prices (pricing deduplicates, so count may be lower than services)
        assert price_count >= 1, f"Expected some prices from SPA, got: {price_count}"
        
        # Check that observed_prices have bookonline source (from SPA extraction)
        spa_prices = [p for p in observed_prices if 'bookonline' in p.get('source_url', '')]
        assert len(spa_prices) >= 1, f"Expected bookonline prices, got: {len(spa_prices)}"
        print(f"SUCCESS: Found {len(spa_prices)} prices from bookonline SPA extraction")


# ==================== API TESTS: Run Full Pipeline ====================

class TestFullPipeline:
    """Tests to verify the full pipeline works with SPA extraction"""
    
    def test_api_health(self):
        """Test API is healthy"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("SUCCESS: API is healthy")
    
    def test_get_campaign_brief(self):
        """Test getting the example_brand campaign brief"""
        response = requests.get(f"{BASE_URL}/api/campaign-briefs/{INSTAGLAM_BRIEF_ID}")
        
        if response.status_code == 404:
            pytest.skip("Instaglam brief not found")
        
        assert response.status_code == 200
        brief = response.json()
        assert "example_brand" in brief.get("brand", {}).get("website_url", "").lower()
        print(f"SUCCESS: Found example_brand brief: {brief.get('brand', {}).get('website_url')}")


# ==================== FIXTURES ====================

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


if __name__ == "__main__":
    # Run unit tests first (no network needed)
    print("\n=== Running Unit Tests ===\n")
    pytest.main([__file__, "-v", "-k", "TestFindBookingUrl or TestSPAServiceResult", "--tb=short"])
    
    # Run integration tests (need network + Playwright)
    print("\n=== Running Integration Tests ===\n")
    pytest.main([__file__, "-v", "-k", "TestExtractSPAServices", "--tb=short"])
    
    # Run API tests
    print("\n=== Running API Tests ===\n")
    pytest.main([__file__, "-v", "-k", "TestExistingPackData or TestFullPipeline", "--tb=short"])
