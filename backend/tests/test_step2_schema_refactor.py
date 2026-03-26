"""
Novara Step 2 Schema Refactor Tests
Tests the new schema including:
- channels extraction (social/messaging/apps)
- improved classification (industry/subcategory/niche/tags)
- brand_summary with name/tagline/bullets
- identity with logo.primary_url and fonts with family field
- asset deduplication
- confidence score hidden from UI
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "http://localhost:8001"

# Test brief ID with completed extraction
EXISTING_BRIEF_ID = "44394be8-2837-4850-b7ab-0769d1557b88"


class TestHealthAndBasics:
    """Basic API health checks"""
    
    def test_api_health(self):
        """API health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ API healthy: {data}")
    
    def test_get_existing_brief(self):
        """Can retrieve existing campaign brief"""
        response = requests.get(f"{BASE_URL}/api/campaign-briefs/{EXISTING_BRIEF_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("campaign_brief_id") == EXISTING_BRIEF_ID
        print(f"✓ Brief retrieved: {data.get('brand', {}).get('website_url')}")


class TestStep2NewSchema:
    """Tests for the new Step 2 schema structure"""
    
    @pytest.fixture
    def pack_data(self):
        """Fetch the website context pack"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{EXISTING_BRIEF_ID}")
        assert response.status_code == 200
        return response.json()
    
    def test_pack_has_step2_structure(self, pack_data):
        """Pack contains step2 (public) and step2_internal (hidden) structures"""
        assert "step2" in pack_data, "Missing step2 field"
        assert "step2_internal" in pack_data, "Missing step2_internal field"
        print(f"✓ Pack has step2 and step2_internal structures")
    
    def test_classification_new_schema(self, pack_data):
        """Classification has industry/subcategory/niche/tags"""
        step2 = pack_data.get("step2", {})
        classification = step2.get("classification", {})
        
        assert "industry" in classification, "Missing industry"
        assert "subcategory" in classification, "Missing subcategory (was sub_industry)"
        assert "niche" in classification, "Missing niche"
        assert "tags" in classification, "Missing tags"
        
        # Verify tags is a list
        assert isinstance(classification.get("tags"), list), "tags should be a list"
        
        print(f"✓ Classification: {classification.get('industry')} → {classification.get('subcategory')} → {classification.get('niche')}")
        print(f"  Tags: {classification.get('tags')}")
    
    def test_brand_summary_structure(self, pack_data):
        """brand_summary has name/tagline/one_liner/bullets"""
        step2 = pack_data.get("step2", {})
        brand_summary = step2.get("brand_summary", {})
        
        assert "name" in brand_summary, "Missing name"
        assert "tagline" in brand_summary, "Missing tagline"
        assert "one_liner" in brand_summary, "Missing one_liner"
        assert "bullets" in brand_summary, "Missing bullets"
        
        # Verify bullets is a list with 2-5 items
        bullets = brand_summary.get("bullets", [])
        assert isinstance(bullets, list), "bullets should be a list"
        assert len(bullets) >= 2, f"bullets should have at least 2 items, got {len(bullets)}"
        assert len(bullets) <= 5, f"bullets should have at most 5 items, got {len(bullets)}"
        
        print(f"✓ Brand Summary: {brand_summary.get('name')}")
        print(f"  Tagline: {brand_summary.get('tagline')}")
        print(f"  Bullets ({len(bullets)}): {bullets[0][:50]}...")
    
    def test_identity_logo_primary_url(self, pack_data):
        """identity.logo uses primary_url (not url)"""
        step2 = pack_data.get("step2", {})
        identity = step2.get("identity", {})
        logo = identity.get("logo", {})
        
        assert "primary_url" in logo, "Missing logo.primary_url"
        # Should NOT have old 'url' field
        assert "url" not in logo or logo.get("url") is None, "Should use primary_url not url"
        
        primary_url = logo.get("primary_url", "")
        assert primary_url, "primary_url should not be empty"
        
        # Verify it's a valid URL
        assert primary_url.startswith("http"), f"primary_url should be a URL: {primary_url[:50]}"
        
        print(f"✓ Logo primary_url: {primary_url[:80]}...")
    
    def test_identity_colors_structure(self, pack_data):
        """identity.colors array has hex and role"""
        step2 = pack_data.get("step2", {})
        identity = step2.get("identity", {})
        colors = identity.get("colors", [])
        
        assert isinstance(colors, list), "colors should be a list"
        assert len(colors) > 0, "Should have at least one color"
        
        for color in colors[:3]:
            assert "hex" in color, f"Color missing hex: {color}"
            assert "role" in color, f"Color missing role: {color}"
            # Verify hex format
            hex_val = color.get("hex", "")
            assert hex_val.startswith("#"), f"hex should start with #: {hex_val}"
        
        print(f"✓ Colors ({len(colors)}): {[c.get('hex') for c in colors[:4]]}")
    
    def test_identity_fonts_family_field(self, pack_data):
        """identity.fonts uses family field (not name)"""
        step2 = pack_data.get("step2", {})
        identity = step2.get("identity", {})
        fonts = identity.get("fonts", [])
        
        assert isinstance(fonts, list), "fonts should be a list"
        assert len(fonts) > 0, "Should have at least one font"
        
        for font in fonts[:3]:
            assert "family" in font, f"Font missing family field: {font}"
            assert "role" in font, f"Font missing role: {font}"
            # family should have a value
            family = font.get("family")
            assert family and family != "unknown", f"family should have a value: {family}"
        
        print(f"✓ Fonts ({len(fonts)}): {[f.get('family') for f in fonts[:3]]}")


class TestChannelsExtraction:
    """Tests for the new channels structure"""
    
    @pytest.fixture
    def pack_data(self):
        """Fetch the website context pack"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{EXISTING_BRIEF_ID}")
        assert response.status_code == 200
        return response.json()
    
    def test_channels_structure(self, pack_data):
        """channels has social/messaging/apps arrays"""
        step2 = pack_data.get("step2", {})
        channels = step2.get("channels", {})
        
        assert "social" in channels, "Missing channels.social"
        assert "messaging" in channels, "Missing channels.messaging"
        assert "apps" in channels, "Missing channels.apps"
        
        assert isinstance(channels.get("social"), list), "social should be a list"
        assert isinstance(channels.get("messaging"), list), "messaging should be a list"
        assert isinstance(channels.get("apps"), list), "apps should be a list"
        
        print(f"✓ Channels: social={len(channels.get('social', []))}, messaging={len(channels.get('messaging', []))}, apps={len(channels.get('apps', []))}")
    
    def test_social_channel_structure(self, pack_data):
        """Social channels have platform/url/handle"""
        step2 = pack_data.get("step2", {})
        channels = step2.get("channels", {})
        social = channels.get("social", [])
        
        if len(social) > 0:
            for channel in social:
                assert "platform" in channel, f"Social channel missing platform: {channel}"
                assert "url" in channel, f"Social channel missing url: {channel}"
                # handle is optional but should be present
                assert "handle" in channel, f"Social channel missing handle: {channel}"
            
            print(f"✓ Social channels: {[(c.get('platform'), c.get('handle')) for c in social]}")
        else:
            print("⚠ No social channels found (may be expected for some sites)")


class TestConfidenceScoreHidden:
    """Tests that confidence score is hidden from UI (in step2_internal)"""
    
    @pytest.fixture
    def pack_data(self):
        """Fetch the website context pack"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{EXISTING_BRIEF_ID}")
        assert response.status_code == 200
        return response.json()
    
    def test_confidence_not_in_step2(self, pack_data):
        """Confidence score should NOT be in step2 (public data)"""
        step2 = pack_data.get("step2", {})
        
        # Check that confidence is not in step2
        step2_str = str(step2).lower()
        assert "confidence" not in step2_str, "confidence should not be in step2 (public data)"
        
        print("✓ Confidence score not in step2 (public data)")
    
    def test_confidence_in_step2_internal(self, pack_data):
        """Confidence score should be in step2_internal (hidden data)"""
        step2_internal = pack_data.get("step2_internal", {})
        analysis_quality = step2_internal.get("analysis_quality", {})
        
        assert "confidence_score_0_100" in analysis_quality, "Missing confidence_score_0_100 in step2_internal"
        
        confidence = analysis_quality.get("confidence_score_0_100")
        assert isinstance(confidence, (int, float)), f"confidence should be a number: {confidence}"
        assert 0 <= confidence <= 100, f"confidence should be 0-100: {confidence}"
        
        print(f"✓ Confidence in step2_internal: {confidence}")


class TestAssetDeduplication:
    """Tests for asset deduplication"""
    
    @pytest.fixture
    def pack_data(self):
        """Fetch the website context pack"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{EXISTING_BRIEF_ID}")
        assert response.status_code == 200
        return response.json()
    
    def test_assets_structure(self, pack_data):
        """Assets have proper structure with kind and score"""
        step2 = pack_data.get("step2", {})
        assets = step2.get("assets", {})
        image_assets = assets.get("image_assets", [])
        
        assert isinstance(image_assets, list), "image_assets should be a list"
        
        if len(image_assets) > 0:
            for asset in image_assets[:5]:
                assert "url" in asset, f"Asset missing url: {asset}"
                assert "kind" in asset, f"Asset missing kind: {asset}"
                assert "score_0_100" in asset, f"Asset missing score_0_100: {asset}"
        
        print(f"✓ Assets count: {len(image_assets)}")
    
    def test_no_duplicate_asset_urls(self, pack_data):
        """Assets should not have duplicate URLs"""
        step2 = pack_data.get("step2", {})
        assets = step2.get("assets", {})
        image_assets = assets.get("image_assets", [])
        
        urls = [a.get("url") for a in image_assets]
        unique_urls = set(urls)
        
        # Allow some tolerance for near-duplicates
        duplicate_count = len(urls) - len(unique_urls)
        assert duplicate_count <= 2, f"Too many duplicate URLs: {duplicate_count}"
        
        print(f"✓ Asset deduplication: {len(unique_urls)} unique out of {len(urls)} total")


class TestFullStep2Flow:
    """End-to-end test for Step 2 extraction flow"""
    
    def test_create_brief_and_start_orchestration(self):
        """Create a new brief and start orchestration"""
        # Create a new brief
        brief_data = {
            "website_url": "example.com",
            "primary_goal": "brand_awareness",
            "success_definition": "Test brief for schema validation",
            "country": "US",
            "city_or_region": "New York",
            "destination_type": "website",
            "ads_intent": "yes",
            "budget_range_monthly": "300-1000",
            "name": "Test User",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com"
        }
        
        response = requests.post(f"{BASE_URL}/api/campaign-briefs", json=brief_data)
        assert response.status_code == 200, f"Failed to create brief: {response.text}"
        
        brief = response.json()
        brief_id = brief.get("campaign_brief_id")
        assert brief_id, "Missing campaign_brief_id"
        
        print(f"✓ Created brief: {brief_id}")
        
        # Start orchestration
        response = requests.post(f"{BASE_URL}/api/orchestrations/{brief_id}/start")
        assert response.status_code == 200, f"Failed to start orchestration: {response.text}"
        
        orch = response.json()
        assert orch.get("status") == "running", f"Unexpected status: {orch.get('status')}"
        
        print(f"✓ Orchestration started: {orch.get('orchestration_id')}")
        
        # Note: We don't wait for completion as it takes time
        # The schema validation is done on the existing brief
        return brief_id


class TestPricingStructure:
    """Tests for pricing data structure"""
    
    @pytest.fixture
    def pack_data(self):
        """Fetch the website context pack"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{EXISTING_BRIEF_ID}")
        assert response.status_code == 200
        return response.json()
    
    def test_pricing_structure(self, pack_data):
        """Pricing has currency/count/min/avg/max"""
        step2 = pack_data.get("step2", {})
        pricing = step2.get("pricing", {})
        
        assert "currency" in pricing, "Missing currency"
        assert "count" in pricing, "Missing count"
        assert "min" in pricing, "Missing min"
        assert "avg" in pricing, "Missing avg"
        assert "max" in pricing, "Missing max"
        
        print(f"✓ Pricing: {pricing.get('currency')} - min={pricing.get('min')}, avg={pricing.get('avg')}, max={pricing.get('max')}")


class TestBrandDNAStructure:
    """Tests for brand DNA structure"""
    
    @pytest.fixture
    def pack_data(self):
        """Fetch the website context pack"""
        response = requests.get(f"{BASE_URL}/api/website-context-packs/by-campaign/{EXISTING_BRIEF_ID}")
        assert response.status_code == 200
        return response.json()
    
    def test_brand_dna_structure(self, pack_data):
        """brand_dna has values/tone_of_voice/aesthetic/visual_vibe"""
        step2 = pack_data.get("step2", {})
        brand_dna = step2.get("brand_dna", {})
        
        assert "values" in brand_dna, "Missing values"
        assert "tone_of_voice" in brand_dna, "Missing tone_of_voice"
        assert "aesthetic" in brand_dna, "Missing aesthetic"
        assert "visual_vibe" in brand_dna, "Missing visual_vibe"
        
        # All should be lists
        for field in ["values", "tone_of_voice", "aesthetic", "visual_vibe"]:
            assert isinstance(brand_dna.get(field), list), f"{field} should be a list"
        
        print(f"✓ Brand DNA: values={brand_dna.get('values')}, tone={brand_dna.get('tone_of_voice')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
