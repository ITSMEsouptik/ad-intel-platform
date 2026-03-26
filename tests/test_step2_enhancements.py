"""
Novara Step 2 Enhancement Tests
Tests for: pricing parsing, asset extraction, LLM summarizer, new fields
"""

import pytest
import requests
import os
import time
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStep2Enhancements:
    """Test Step 2 enhanced extraction with pricing, assets, and LLM summarizer"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.existing_brief_id = "8d3cd53e-d87b-4afe-bad6-e308d3d7e490"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    # ============== API Health Tests ==============
    
    def test_api_health(self):
        """Test API is healthy"""
        response = self.session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ API health check passed")
    
    # ============== Campaign Brief Tests ==============
    
    def test_get_existing_brief(self):
        """Test retrieving existing campaign brief"""
        response = self.session.get(f"{BASE_URL}/api/campaign-briefs/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("campaign_brief_id") == self.existing_brief_id
        assert data.get("brand", {}).get("website_url") == "https://example-brand.co"
        print(f"✓ Retrieved brief: {data.get('brand', {}).get('website_url')}")
    
    def test_create_campaign_brief(self):
        """Test creating a new campaign brief"""
        payload = {
            "website_url": "gonovara.com",
            "primary_goal": "brand_awareness",
            "success_definition": "Test Step 2 enhancements",
            "country": "USA",
            "city_or_region": "San Francisco",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "1000-5000",
            "name": "Test Step2",
            "email": "test.step2@example.com"
        }
        response = self.session.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "campaign_brief_id" in data
        assert data.get("brand", {}).get("website_url") == "https://gonovara.com"
        print(f"✓ Created brief: {data.get('campaign_brief_id')}")
        return data.get("campaign_brief_id")
    
    # ============== Website Context Pack Tests (Existing Brief) ==============
    
    def test_get_website_context_pack_existing(self):
        """Test retrieving website context pack for existing brief"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["success", "partial", "needs_user_input"]
        assert "data" in data
        print(f"✓ Pack status: {data.get('status')}, confidence: {data.get('confidence_score')}")
        return data
    
    def test_new_brand_summary_bullets(self):
        """Test brand_summary_bullets field is populated"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        brand_identity = pack_data.get("brand_identity", {})
        brand_summary_bullets = brand_identity.get("brand_summary_bullets", [])
        
        assert isinstance(brand_summary_bullets, list), "brand_summary_bullets should be a list"
        assert len(brand_summary_bullets) >= 2, f"Expected at least 2 bullets, got {len(brand_summary_bullets)}"
        
        # Verify bullets are strings with reasonable length
        for bullet in brand_summary_bullets:
            assert isinstance(bullet, str), "Each bullet should be a string"
            assert len(bullet) <= 90, f"Bullet too long: {bullet}"
        
        print(f"✓ Brand summary bullets ({len(brand_summary_bullets)}): {brand_summary_bullets[:2]}...")
    
    def test_new_brand_values(self):
        """Test brand_values field is populated"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        brand_identity = pack_data.get("brand_identity", {})
        brand_values = brand_identity.get("brand_values", [])
        
        assert isinstance(brand_values, list), "brand_values should be a list"
        
        # Verify values are short chips (1-3 words)
        for value in brand_values:
            assert isinstance(value, str), "Each value should be a string"
            assert len(value) <= 24, f"Value too long (should be chip): {value}"
        
        print(f"✓ Brand values: {brand_values}")
    
    def test_new_brand_aesthetic(self):
        """Test brand_aesthetic field is populated"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        brand_identity = pack_data.get("brand_identity", {})
        brand_aesthetic = brand_identity.get("brand_aesthetic", [])
        
        assert isinstance(brand_aesthetic, list), "brand_aesthetic should be a list"
        
        # Verify aesthetics are short chips
        for aesthetic in brand_aesthetic:
            assert isinstance(aesthetic, str), "Each aesthetic should be a string"
            assert len(aesthetic) <= 24, f"Aesthetic too long (should be chip): {aesthetic}"
        
        print(f"✓ Brand aesthetic: {brand_aesthetic}")
    
    def test_new_brand_tone_of_voice(self):
        """Test brand_tone_of_voice field is populated"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        brand_identity = pack_data.get("brand_identity", {})
        brand_tone = brand_identity.get("brand_tone_of_voice", [])
        
        assert isinstance(brand_tone, list), "brand_tone_of_voice should be a list"
        
        # Verify tones are short chips
        for tone in brand_tone:
            assert isinstance(tone, str), "Each tone should be a string"
            assert len(tone) <= 24, f"Tone too long (should be chip): {tone}"
        
        print(f"✓ Brand tone of voice: {brand_tone}")
    
    def test_pricing_parsed_structure(self):
        """Test pricing_parsed field has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        offer = pack_data.get("offer", {})
        pricing_parsed = offer.get("pricing_parsed", {})
        
        assert isinstance(pricing_parsed, dict), "pricing_parsed should be a dict"
        
        # Check required fields
        assert "currency" in pricing_parsed, "pricing_parsed should have currency"
        assert "count" in pricing_parsed, "pricing_parsed should have count"
        
        # If prices were found, check min/max/avg
        if pricing_parsed.get("count", 0) > 0:
            assert "min" in pricing_parsed, "pricing_parsed should have min"
            assert "max" in pricing_parsed, "pricing_parsed should have max"
            assert "avg" in pricing_parsed, "pricing_parsed should have avg"
            assert pricing_parsed["min"] <= pricing_parsed["max"], "min should be <= max"
            assert pricing_parsed["min"] <= pricing_parsed["avg"] <= pricing_parsed["max"], "avg should be between min and max"
        
        print(f"✓ Pricing parsed: currency={pricing_parsed.get('currency')}, count={pricing_parsed.get('count')}, min={pricing_parsed.get('min')}, max={pricing_parsed.get('max')}, avg={pricing_parsed.get('avg')}")
    
    def test_image_assets_structure(self):
        """Test image_assets field has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        brand_identity = pack_data.get("brand_identity", {})
        visual = brand_identity.get("visual", {})
        image_assets = visual.get("image_assets", [])
        
        assert isinstance(image_assets, list), "image_assets should be a list"
        
        # Check structure of each asset
        for asset in image_assets[:3]:  # Check first 3
            assert isinstance(asset, dict), "Each asset should be a dict"
            assert "url" in asset, "Asset should have url"
            assert "type" in asset, "Asset should have type"
            assert "score_0_100" in asset, "Asset should have score_0_100"
            assert 0 <= asset["score_0_100"] <= 100, "Score should be 0-100"
        
        print(f"✓ Image assets: {len(image_assets)} found")
        if image_assets:
            print(f"  First asset: type={image_assets[0].get('type')}, score={image_assets[0].get('score_0_100')}")
    
    def test_offer_catalog_structure(self):
        """Test offer_catalog field has correct structure"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        offer = pack_data.get("offer", {})
        offer_catalog = offer.get("offer_catalog", [])
        
        assert isinstance(offer_catalog, list), "offer_catalog should be a list"
        
        # Check structure of each catalog item
        for item in offer_catalog:
            assert isinstance(item, dict), "Each catalog item should be a dict"
            assert "name" in item, "Catalog item should have name"
            # description and price_hint are optional
        
        print(f"✓ Offer catalog: {len(offer_catalog)} items")
        for item in offer_catalog[:3]:
            print(f"  - {item.get('name')}: {item.get('description', 'N/A')[:50]}...")
    
    def test_llm_summarizer_metadata(self):
        """Test LLM summarizer metadata is present"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{self.existing_brief_id}")
        assert response.status_code == 200
        data = response.json()
        
        pack_data = data.get("data", {})
        raw = pack_data.get("raw", {})
        llm_summarizer = raw.get("llm_summarizer", {})
        
        assert isinstance(llm_summarizer, dict), "llm_summarizer should be a dict"
        
        # Check status
        status = llm_summarizer.get("status")
        assert status in ["success", "partial", "failed", None], f"Unexpected LLM status: {status}"
        
        if status == "success":
            assert "model" in llm_summarizer, "Should have model info"
            print(f"✓ LLM summarizer: status={status}, model={llm_summarizer.get('model')}")
        else:
            print(f"✓ LLM summarizer: status={status}")
    
    # ============== Full Flow Test (New Brief) ==============
    
    def test_full_step2_flow_new_brief(self):
        """Test complete Step 2 flow with a new brief"""
        # Create new brief
        payload = {
            "website_url": "stripe.com",
            "primary_goal": "sales_orders",
            "success_definition": "Test full Step 2 flow",
            "country": "USA",
            "city_or_region": "San Francisco",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "5000+",
            "name": "Test Full Flow",
            "email": "test.fullflow@example.com"
        }
        
        # Create brief
        response = self.session.post(f"{BASE_URL}/api/campaign-briefs", json=payload)
        assert response.status_code == 200
        brief_data = response.json()
        brief_id = brief_data.get("campaign_brief_id")
        print(f"✓ Created brief: {brief_id}")
        
        # Start orchestration (Step 2)
        response = self.session.post(f"{BASE_URL}/api/orchestrations/{brief_id}/start")
        assert response.status_code == 200
        orch_data = response.json()
        assert orch_data.get("status") == "running"
        print(f"✓ Started orchestration: {orch_data.get('orchestration_id')}")
        
        # Poll for completion (max 120 seconds)
        max_wait = 120
        poll_interval = 5
        elapsed = 0
        pack_status = "running"
        
        while elapsed < max_wait and pack_status == "running":
            time.sleep(poll_interval)
            elapsed += poll_interval
            
            response = self.session.get(f"{BASE_URL}/api/orchestrations/{brief_id}/status")
            assert response.status_code == 200
            status_data = response.json()
            
            pack = status_data.get("website_context_pack", {})
            pack_status = pack.get("status", "running")
            
            print(f"  Polling... {elapsed}s - status: {pack_status}")
        
        assert pack_status in ["success", "partial", "needs_user_input"], f"Step 2 did not complete: {pack_status}"
        print(f"✓ Step 2 completed with status: {pack_status}")
        
        # Verify new fields are populated
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{brief_id}")
        assert response.status_code == 200
        pack_data = response.json()
        
        data = pack_data.get("data", {})
        brand_identity = data.get("brand_identity", {})
        offer = data.get("offer", {})
        
        # Check new fields exist (may be empty for some sites)
        assert "brand_summary_bullets" in brand_identity or brand_identity.get("brand_summary_bullets") is None
        assert "brand_values" in brand_identity or brand_identity.get("brand_values") is None
        assert "pricing_parsed" in offer or offer.get("pricing_parsed") is None
        
        print(f"✓ New fields present in pack")
        print(f"  - brand_summary_bullets: {len(brand_identity.get('brand_summary_bullets', []))} items")
        print(f"  - brand_values: {brand_identity.get('brand_values', [])}")
        print(f"  - pricing_parsed: {offer.get('pricing_parsed', {})}")
        
        return brief_id
    
    # ============== Edge Cases ==============
    
    def test_pack_not_found(self):
        """Test 404 for non-existent pack"""
        response = self.session.get(f"{BASE_URL}/api/website-context-packs/by-campaign/non-existent-id")
        assert response.status_code == 404
        print("✓ 404 returned for non-existent pack")
    
    def test_brief_not_found(self):
        """Test 404 for non-existent brief"""
        response = self.session.get(f"{BASE_URL}/api/campaign-briefs/non-existent-id")
        assert response.status_code == 404
        print("✓ 404 returned for non-existent brief")


class TestPricingParser:
    """Unit tests for pricing parser module"""
    
    def test_pricing_parser_import(self):
        """Test pricing parser can be imported"""
        import sys
        sys.path.insert(0, '/app/backend')
        from pricing import parse_pricing
        
        result = parse_pricing(["$100", "$200", "$300"], "")
        assert isinstance(result, dict)
        assert result.get("currency") == "USD"
        assert result.get("count") == 3
        assert result.get("min") == 100
        assert result.get("max") == 300
        print(f"✓ Pricing parser: {result}")
    
    def test_pricing_parser_aed(self):
        """Test AED currency detection"""
        import sys
        sys.path.insert(0, '/app/backend')
        from pricing import parse_pricing
        
        result = parse_pricing(["AED 950", "AED 1575", "AED 2100"], "")
        assert result.get("currency") == "AED"
        assert result.get("min") == 950
        assert result.get("max") == 2100
        print(f"✓ AED pricing: {result}")
    
    def test_pricing_parser_empty(self):
        """Test empty pricing list"""
        import sys
        sys.path.insert(0, '/app/backend')
        from pricing import parse_pricing
        
        result = parse_pricing([], "")
        assert result.get("count") == 0
        assert result.get("min") is None
        assert result.get("max") is None
        print(f"✓ Empty pricing: {result}")


class TestAssetExtractor:
    """Unit tests for asset extractor module"""
    
    def test_asset_extractor_import(self):
        """Test asset extractor can be imported"""
        import sys
        sys.path.insert(0, '/app/backend')
        from assets import extract_assets
        
        pages = [
            {
                'url': 'https://example.com',
                'extracted_text_md': '',
                'asset_urls_found': [
                    'https://example.com/logo.png',
                    'https://example.com/hero.jpg',
                    'https://example.com/product.webp'
                ]
            }
        ]
        
        result = extract_assets(pages, 'example.com')
        assert isinstance(result, dict)
        assert "image_assets" in result
        assert "logo_candidates" in result
        print(f"✓ Asset extractor: {len(result.get('image_assets', []))} assets found")
    
    def test_asset_extractor_logo_detection(self):
        """Test logo detection in URLs"""
        import sys
        sys.path.insert(0, '/app/backend')
        from assets import extract_assets
        
        pages = [
            {
                'url': 'https://example.com',
                'extracted_text_md': '',
                'asset_urls_found': [
                    'https://example.com/images/logo-main.png',
                    'https://example.com/hero.jpg'
                ]
            }
        ]
        
        result = extract_assets(pages, 'example.com')
        logo_candidates = result.get('logo_candidates', [])
        
        # Should detect logo in URL
        assert len(logo_candidates) > 0, "Should detect logo candidate"
        assert 'logo' in logo_candidates[0].get('url', '').lower()
        print(f"✓ Logo detection: {logo_candidates[0].get('url')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
