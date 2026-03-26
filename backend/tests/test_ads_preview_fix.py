"""
Test for ads thumbnail/preview fix - iteration 44
Tests: has_preview flag, media field mapping in postprocess, and API response
"""

import pytest
import requests
import os
import sys

# Add backend to path for unit tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ============== UNIT TESTS: postprocess.py logic ==============

class TestPostprocessMediaDetection:
    """Unit tests for has_preview flag and media field mapping in postprocess_ads"""
    
    def test_video_ad_has_preview_true(self):
        """Video ads should have has_preview=true"""
        from research.ads_intel.postprocess import postprocess_ads
        
        # Ad with video field
        ads = [{
            "id": "ad1",
            "video": "https://example.com/video.mp4",
            "thumbnail": "https://example.com/thumb.jpg",
            "description": "Test video ad",
        }]
        
        result = postprocess_ads(ads, lens="competitor")
        assert len(result) == 1
        assert result[0]["has_preview"] == True
        assert result[0]["media_url"] == "https://example.com/video.mp4"
        assert result[0]["thumbnail_url"] == "https://example.com/thumb.jpg"
        assert result[0]["display_format"] == "video"
    
    def test_image_ad_has_preview_true(self):
        """Image ads should have has_preview=true"""
        from research.ads_intel.postprocess import postprocess_ads
        
        # Ad with image field only
        ads = [{
            "id": "ad2",
            "image": "https://example.com/fullres_image.jpg",
            "description": "Test image ad",
        }]
        
        result = postprocess_ads(ads, lens="competitor")
        assert len(result) == 1
        assert result[0]["has_preview"] == True
        assert result[0]["media_url"] is None  # No video
        assert result[0]["thumbnail_url"] == "https://example.com/fullres_image.jpg"
        assert result[0]["display_format"] == "image"
    
    def test_thumbnail_only_ad_has_preview_true(self):
        """Ads with only thumbnail should have has_preview=true"""
        from research.ads_intel.postprocess import postprocess_ads
        
        # Ad with only thumbnail field
        ads = [{
            "id": "ad3",
            "thumbnail": "https://example.com/thumb.jpg",
            "description": "Test thumbnail ad",
        }]
        
        result = postprocess_ads(ads, lens="competitor")
        assert len(result) == 1
        assert result[0]["has_preview"] == True
        assert result[0]["thumbnail_url"] == "https://example.com/thumb.jpg"
    
    def test_avatar_only_ad_has_preview_false(self):
        """DCO/carousel ads with only avatar should have has_preview=false"""
        from research.ads_intel.postprocess import postprocess_ads
        
        # Ad with only avatar (tiny brand icon) - no usable preview
        ads = [{
            "id": "ad4",
            "avatar": "https://example.com/tiny_avatar.jpg",
            "description": "DCO ad with only avatar",
            "display_format": "dco",
        }]
        
        result = postprocess_ads(ads, lens="competitor")
        assert len(result) == 1
        assert result[0]["has_preview"] == False
        assert result[0]["thumbnail_url"] == "https://example.com/tiny_avatar.jpg"  # Falls back to avatar
        assert result[0]["display_format"] == "dco"
    
    def test_carousel_with_avatar_only_has_preview_false(self):
        """Carousel ads with only avatar should have has_preview=false"""
        from research.ads_intel.postprocess import postprocess_ads
        
        # Carousel ad - Foreplay can't capture dynamic creative
        ads = [{
            "id": "ad5",
            "avatar": "https://example.com/brand_icon.jpg",
            "headline": "Check out our products!",
            "display_format": "carousel",
        }]
        
        result = postprocess_ads(ads, lens="category")
        assert len(result) == 1
        assert result[0]["has_preview"] == False
        assert result[0]["display_format"] == "carousel"
        assert result[0]["headline"] == "Check out our products!"
    
    def test_mixed_media_fields_priority(self):
        """Test that video > image > thumbnail > avatar priority is correct"""
        from research.ads_intel.postprocess import postprocess_ads
        
        # Ad with all fields - video should take priority
        ads = [{
            "id": "ad6",
            "video": "https://example.com/video.mp4",
            "image": "https://example.com/image.jpg",
            "thumbnail": "https://example.com/thumb.jpg",
            "avatar": "https://example.com/avatar.jpg",
            "description": "Mixed media ad",
        }]
        
        result = postprocess_ads(ads, lens="competitor")
        assert len(result) == 1
        assert result[0]["has_preview"] == True  # Has video
        assert result[0]["media_url"] == "https://example.com/video.mp4"
        assert result[0]["thumbnail_url"] == "https://example.com/thumb.jpg"  # video poster
        assert result[0]["display_format"] == "video"
    
    def test_image_with_avatar_uses_image(self):
        """Image ads should use image field, not avatar"""
        from research.ads_intel.postprocess import postprocess_ads
        
        # Ad with image and avatar - image takes priority
        ads = [{
            "id": "ad7",
            "image": "https://example.com/highres.jpg",
            "avatar": "https://example.com/tiny_avatar.jpg",
            "description": "Image with avatar",
        }]
        
        result = postprocess_ads(ads, lens="competitor")
        assert len(result) == 1
        assert result[0]["has_preview"] == True
        assert result[0]["thumbnail_url"] == "https://example.com/highres.jpg"


class TestAdCardSchema:
    """Test AdCard schema includes has_preview field"""
    
    def test_ad_card_has_preview_field_defaults_true(self):
        """AdCard should have has_preview field defaulting to True"""
        from research.ads_intel.schema import AdCard
        
        card = AdCard(
            ad_id="test123",
            publisher_platform="facebook",
            lens="competitor",
            why_shortlisted="Test reason",
        )
        
        assert hasattr(card, 'has_preview')
        assert card.has_preview == True  # Default
    
    def test_ad_card_has_preview_can_be_false(self):
        """AdCard should accept has_preview=False for DCO ads"""
        from research.ads_intel.schema import AdCard
        
        card = AdCard(
            ad_id="dco123",
            publisher_platform="facebook",
            display_format="dco",
            has_preview=False,
            lens="competitor",
            why_shortlisted="DCO ad with no preview",
        )
        
        assert card.has_preview == False
        assert card.display_format == "dco"


# ============== API TESTS: Verify live data ==============

class TestAdsIntelAPIPreviewFlag:
    """API tests to verify has_preview is correctly returned"""
    
    @pytest.fixture(autouse=True)
    def skip_if_no_url(self):
        if not BASE_URL:
            pytest.skip("REACT_APP_BACKEND_URL not set")
    
    def test_api_health(self):
        """Verify API is reachable"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
    
    def test_campaign_ads_have_has_preview_field(self):
        """Verify all ads in API response have has_preview field"""
        campaign_id = "568e45c8-7976-4d14-878a-70074f35f3ff"
        
        response = requests.get(f"{BASE_URL}/api/research/{campaign_id}")
        assert response.status_code == 200
        
        data = response.json()
        sources = data.get("sources", {})
        ai_data = sources.get("ads_intel", {}).get("latest", {})
        
        if not ai_data:
            pytest.skip("No ads_intel data for this campaign")
        
        comp_ads = ai_data.get("competitor_winners", {}).get("ads", [])
        cat_ads = ai_data.get("category_winners", {}).get("ads", [])
        all_ads = comp_ads + cat_ads
        
        assert len(all_ads) > 0, "Campaign should have ads"
        
        for ad in all_ads:
            assert "has_preview" in ad, f"Ad {ad.get('ad_id')} missing has_preview field"
            assert isinstance(ad["has_preview"], bool), "has_preview should be boolean"
    
    def test_dco_ads_have_preview_false(self):
        """Verify DCO/carousel ads have has_preview=false"""
        campaign_id = "568e45c8-7976-4d14-878a-70074f35f3ff"
        
        response = requests.get(f"{BASE_URL}/api/research/{campaign_id}")
        assert response.status_code == 200
        
        data = response.json()
        sources = data.get("sources", {})
        ai_data = sources.get("ads_intel", {}).get("latest", {})
        
        if not ai_data:
            pytest.skip("No ads_intel data")
        
        comp_ads = ai_data.get("competitor_winners", {}).get("ads", [])
        cat_ads = ai_data.get("category_winners", {}).get("ads", [])
        all_ads = comp_ads + cat_ads
        
        dco_ads = [a for a in all_ads if a.get("display_format") in ("dco", "carousel")]
        preview_false_ads = [a for a in all_ads if a.get("has_preview") == False]
        
        # Report findings
        print(f"\nTotal ads: {len(all_ads)}")
        print(f"DCO/carousel ads: {len(dco_ads)}")
        print(f"Ads with has_preview=false: {len(preview_false_ads)}")
        
        # At least some DCO ads should have has_preview=false
        # (Note: some DCO ads might have image/video if Foreplay captured them)
        for ad in preview_false_ads:
            print(f"  - {ad.get('brand_name')}: format={ad.get('display_format')}, has_preview={ad.get('has_preview')}")
        
        assert len(preview_false_ads) > 0, "Expected some ads with has_preview=false"
    
    def test_video_ads_have_preview_true(self):
        """Verify video ads have has_preview=true and media_url set"""
        campaign_id = "568e45c8-7976-4d14-878a-70074f35f3ff"
        
        response = requests.get(f"{BASE_URL}/api/research/{campaign_id}")
        assert response.status_code == 200
        
        data = response.json()
        sources = data.get("sources", {})
        ai_data = sources.get("ads_intel", {}).get("latest", {})
        
        if not ai_data:
            pytest.skip("No ads_intel data")
        
        comp_ads = ai_data.get("competitor_winners", {}).get("ads", [])
        cat_ads = ai_data.get("category_winners", {}).get("ads", [])
        all_ads = comp_ads + cat_ads
        
        video_ads = [a for a in all_ads if a.get("display_format") == "video" or a.get("media_url")]
        
        print(f"\nVideo ads found: {len(video_ads)}")
        
        for ad in video_ads[:5]:
            assert ad.get("has_preview") == True, f"Video ad {ad.get('ad_id')} should have has_preview=true"
            # Video ads should have media_url or thumbnail_url
            has_media = bool(ad.get("media_url") or ad.get("thumbnail_url"))
            assert has_media, f"Video ad {ad.get('ad_id')} should have media or thumbnail URL"
            print(f"  - {ad.get('brand_name')}: format={ad.get('display_format')}, has_preview={ad.get('has_preview')}, has_media_url={bool(ad.get('media_url'))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
