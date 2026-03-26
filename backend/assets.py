"""
Novara Step 2: Asset Extraction
Extracts and ranks images/assets from crawled pages with kind classification
(logo, hero, og, product, team, gallery, icon, unknown)
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class ImageAsset:
    """Represents a single image asset with kind classification"""
    url: str
    kind: str  # logo, hero, og, product, team, gallery, icon, unknown
    score_0_100: int = 50
    alt: str = "unknown"
    context_hint: str = "unknown"
    width: int = 0
    height: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "kind": self.kind,
            "score_0_100": self.score_0_100,
            "alt": self.alt,
            "context_hint": self.context_hint
        }


@dataclass
class LogoResult:
    """Logo extraction result"""
    url: str = "unknown"
    type: str = "logo"  # logo, icon, wordmark
    width: int = 0
    height: int = 0


@dataclass
class AssetsResult:
    """Result of asset extraction"""
    logo: LogoResult = field(default_factory=LogoResult)
    image_assets: List[ImageAsset] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "logo": {
                "url": self.logo.url,
                "type": self.logo.type,
                "bg_safe_variant_url": self.logo.url,  # Same as original for now
                "width": self.logo.width,
                "height": self.logo.height
            },
            "image_assets": [ia.to_dict() for ia in self.image_assets]
        }


class AssetExtractor:
    """
    Extracts and ranks image assets from crawled HTML pages.
    Classifies each asset into a kind (logo, hero, og, product, team, gallery, icon).
    """
    
    # Patterns to identify asset kinds
    KIND_PATTERNS = {
        'logo': ['logo', 'brand-logo', 'site-logo', 'company-logo', 'brand-mark'],
        'icon': ['icon', 'favicon', 'apple-touch', 'shortcut'],
        'hero': ['hero', 'banner', 'header-image', 'jumbotron', 'masthead', 'cover'],
        'product': ['product', 'item', 'merchandise', 'catalog', 'shop', 'service'],
        'team': ['team', 'staff', 'employee', 'founder', 'about-us', 'person', 'avatar'],
        'gallery': ['gallery', 'portfolio', 'work', 'project', 'showcase', 'before-after'],
        'og': ['og:image', 'og-image', 'social', 'share', 'twitter:image'],
    }
    
    # Skip patterns for URLs
    SKIP_PATTERNS = [
        r'tracking', r'pixel', r'analytics', r'beacon',
        r'spacer', r'blank', r'transparent', r'placeholder',
        r'data:image/gif', r'data:image/png;base64,iVBOR',
        r'\.svg.*\.svg',
        r'facebook\.com/tr', r'google-analytics',
        r'doubleclick', r'adsense', r'\.gif$',
        r'1x1', r'loader', r'spinner', r'loading',
    ]
    
    # Social media icons to skip (not brand assets)
    SOCIAL_ICON_PATTERNS = [
        r'facebook', r'linkedin', r'twitter', r'instagram', r'tiktok',
        r'youtube', r'pinterest', r'whatsapp', r'telegram', r'snapchat',
        r'vimeo', r'discord', r'reddit', r'slack', r'x\.com',
        r'social[-_]?icon', r'share[-_]?icon', r'social[-_]?media',
        r'/icons?/', r'/social/', r'icon[-_]?facebook', r'icon[-_]?instagram',
        r'fa-facebook', r'fa-instagram', r'fa-twitter', r'fa-linkedin',
        r'sprite', r'icon[-_]?set', r'emoji'
    ]
    
    # File type preferences (higher = better)
    FILE_TYPE_SCORES = {
        'png': 15,
        'jpg': 12,
        'jpeg': 12,
        'webp': 14,
        'svg': 10,
        'gif': 3,
    }
    
    def __init__(self, domain: str = ""):
        self.domain = domain
    
    def extract_from_pages(self, pages: List[Dict], domain: str = "") -> AssetsResult:
        """
        Extract assets from multiple crawled pages.
        
        Args:
            pages: List of page data dicts from crawler
            domain: Website domain for relevance scoring
            
        Returns:
            AssetsResult with logo and ranked image assets
        """
        self.domain = domain or self.domain
        
        result = AssetsResult()
        all_assets = []
        logo_candidates = []
        seen_urls = set()
        
        for i, page in enumerate(pages):
            current_page_type = page.get('page_type', 'other')
            is_homepage = i == 0
            html_text = page.get('extracted_text_md', '')
            asset_urls = page.get('asset_urls_found', [])
            
            # Extract OG image specially
            og_image = page.get('og_image', '')
            if og_image and og_image not in seen_urls:
                seen_urls.add(og_image)
                all_assets.append(ImageAsset(
                    url=og_image,
                    kind='og',
                    score_0_100=85,
                    alt='Open Graph image',
                    context_hint='meta og:image'
                ))
            
            # Process each asset from page
            # Assets can be either List[str] (old format) or List[Dict] (new format with alt, is_logo)
            for idx, asset_item in enumerate(asset_urls):
                # Handle both old (str) and new (dict) formats
                if isinstance(asset_item, dict):
                    url = asset_item.get('url', '')
                    alt_text = asset_item.get('alt', 'unknown')
                    is_logo_hint = asset_item.get('is_logo', False)
                else:
                    url = asset_item
                    alt_text = "unknown"
                    is_logo_hint = False
                
                if not url or url in seen_urls:
                    continue
                
                if self._should_skip_url(url):
                    continue
                
                # Skip social icons based on alt text too
                if self._is_social_icon(url, alt_text):
                    continue
                
                seen_urls.add(url)
                
                # If alt text extraction needed and not provided
                if alt_text == "unknown":
                    alt_text = self._extract_alt_text(url, html_text)
                
                # Classify asset kind - prioritize logo hint
                if is_logo_hint:
                    kind = 'logo'
                    context_hint = 'alt_contains_logo'
                else:
                    kind, context_hint = self._classify_asset(
                        url=url,
                        alt_text=alt_text,
                        position=idx,
                        is_homepage=is_homepage,
                        page_type=current_page_type,
                        html_context=html_text
                    )
                
                # Calculate score
                score = self._calculate_score(
                    url=url,
                    kind=kind,
                    position=idx,
                    is_homepage=is_homepage,
                    page_type=current_page_type
                )
                
                asset = ImageAsset(
                    url=url,
                    kind=kind,
                    score_0_100=score,
                    alt=alt_text,
                    context_hint=context_hint
                )
                
                all_assets.append(asset)
                
                # Track logo candidates
                if kind == 'logo':
                    logo_candidates.append(asset)
        
        # Deduplicate by similar URLs (query param variants)
        all_assets = self._dedupe_similar_urls(all_assets)
        
        # Sort by score
        all_assets.sort(key=lambda a: a.score_0_100, reverse=True)
        
        # Set logo
        if logo_candidates:
            logo_candidates.sort(key=lambda a: a.score_0_100, reverse=True)
            best_logo = logo_candidates[0]
            result.logo = LogoResult(
                url=best_logo.url,
                type=self._detect_logo_type(best_logo.url, best_logo.alt),
                width=0,
                height=0
            )
        elif all_assets:
            # Fall back to highest scored asset
            result.logo = LogoResult(url=all_assets[0].url)
        
        # Filter out the chosen logo from assets list (to avoid duplication)
        result.image_assets = [
            a for a in all_assets 
            if a.url != result.logo.url
        ][:200]  # Max 200 assets
        
        return result
    
    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped"""
        url_lower = url.lower()
        
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        
        # Skip social media icons
        for pattern in self.SOCIAL_ICON_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        
        # Skip data URIs that are too short (placeholders)
        if url.startswith('data:') and len(url) < 200:
            return True
        
        # Skip very long URLs (likely tracking)
        if len(url) > 500:
            return True
        
        return False
    
    def _is_social_icon(self, url: str, alt_text: str) -> bool:
        """Check if asset is a social media icon based on URL or alt text"""
        url_lower = url.lower()
        alt_lower = alt_text.lower() if alt_text else ''
        
        # Social media keywords
        social_keywords = [
            'facebook', 'linkedin', 'twitter', 'instagram', 'tiktok',
            'youtube', 'pinterest', 'whatsapp', 'telegram', 'snapchat',
            'vimeo', 'discord', 'reddit', 'slack', 'x.com',
            'social icon', 'social-icon', 'socialicon'
        ]
        
        # Check URL
        for keyword in social_keywords:
            if keyword in url_lower:
                return True
        
        # Check alt text - more strict (must be exact match or "X icon")
        social_exact = ['facebook', 'linkedin', 'twitter', 'instagram', 'tiktok', 'youtube', 'pinterest', 'whatsapp']
        for keyword in social_exact:
            if alt_lower == keyword or f'{keyword} icon' in alt_lower or f'{keyword}-icon' in alt_lower:
                return True
        
        return False
    
    def _extract_alt_text(self, url: str, html_text: str) -> str:
        """Try to find alt text for an image URL"""
        # Try to find the image tag with this URL
        url_escaped = re.escape(url.split('?')[0])  # Remove query params for matching
        
        patterns = [
            rf'<img[^>]*src=["\']?{url_escaped}[^"\']*["\']?[^>]*alt=["\']([^"\']+)["\']',
            rf'alt=["\']([^"\']+)["\'][^>]*src=["\']?{url_escaped}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_text, re.IGNORECASE)
            if match:
                return match.group(1)[:100]
        
        # Try to extract from URL filename
        path = urlparse(url).path
        filename = path.split('/')[-1].split('.')[0]
        if filename and len(filename) > 2:
            # Clean up filename
            cleaned = re.sub(r'[-_]', ' ', filename)
            cleaned = re.sub(r'[0-9]+', '', cleaned).strip()
            if cleaned and len(cleaned) > 2:
                return cleaned[:60]
        
        return "unknown"
    
    def _classify_asset(
        self,
        url: str,
        alt_text: str,
        position: int,
        is_homepage: bool,
        page_type: str,
        html_context: str
    ) -> Tuple[str, str]:
        """
        Classify asset into a kind (logo, hero, og, product, team, gallery, icon, unknown).
        Returns (kind, context_hint).
        """
        url_lower = url.lower()
        alt_lower = alt_text.lower() if alt_text != "unknown" else ""
        
        # Check URL and alt text against patterns
        for kind, patterns in self.KIND_PATTERNS.items():
            if any(p in url_lower for p in patterns):
                return kind, f'url_contains_{kind}'
            if any(p in alt_lower for p in patterns):
                return kind, f'alt_contains_{kind}'
        
        # Position-based classification for homepage
        if is_homepage:
            if position == 0:
                # First image is often hero or OG
                return 'hero', 'first_image_homepage'
            elif position < 3:
                return 'hero', 'early_position_homepage'
        
        # Page type based classification
        if page_type == 'services' or page_type == 'product':
            return 'product', f'page_type_{page_type}'
        elif page_type == 'about' or page_type == 'team':
            return 'team', f'page_type_{page_type}'
        elif page_type == 'testimonials':
            return 'team', 'testimonials_page'
        
        # Check HTML context for additional hints
        if 'portfolio' in html_context.lower() or 'gallery' in html_context.lower():
            return 'gallery', 'html_context'
        
        return 'unknown', f'position_{position}'
    
    def _calculate_score(
        self,
        url: str,
        kind: str,
        position: int,
        is_homepage: bool,
        page_type: str
    ) -> int:
        """Calculate asset quality score (0-100)"""
        score = 50  # Base score
        
        # Kind bonus
        kind_bonuses = {
            'logo': 25,
            'og': 20,
            'hero': 18,
            'product': 12,
            'team': 10,
            'gallery': 8,
            'icon': 5,
            'unknown': 0
        }
        score += kind_bonuses.get(kind, 0)
        
        # Position bonus (earlier = better, up to +15)
        position_bonus = max(0, 15 - position * 2)
        score += position_bonus
        
        # Homepage bonus
        if is_homepage:
            score += 10
        
        # Page type bonus
        page_bonuses = {
            'services': 5,
            'product': 5,
            'about': 3,
            'pricing': 3,
        }
        score += page_bonuses.get(page_type, 0)
        
        # File type bonus
        ext = self._get_file_extension(url)
        score += self.FILE_TYPE_SCORES.get(ext, 0)
        
        # Domain relevance bonus
        if self.domain and self.domain in url:
            score += 5
        
        # Cap at 100
        return min(100, max(0, score))
    
    def _get_file_extension(self, url: str) -> str:
        """Get file extension from URL"""
        path = urlparse(url).path.lower()
        
        for ext in ['png', 'jpg', 'jpeg', 'webp', 'svg', 'gif']:
            if path.endswith(f'.{ext}'):
                return ext
        
        return ''
    
    def _detect_logo_type(self, url: str, alt_text: str) -> str:
        """Detect logo type (logo, icon, wordmark)"""
        url_lower = url.lower()
        alt_lower = alt_text.lower() if alt_text != "unknown" else ""
        
        if 'wordmark' in url_lower or 'wordmark' in alt_lower:
            return 'wordmark'
        elif 'icon' in url_lower or 'favicon' in url_lower:
            return 'icon'
        
        return 'logo'
    
    def _dedupe_similar_urls(self, assets: List[ImageAsset]) -> List[ImageAsset]:
        """Remove duplicate assets with similar URLs (query param variants)"""
        seen_base_urls = {}
        result = []
        
        for asset in assets:
            # Get base URL without query params
            parsed = urlparse(asset.url)
            base_url = f"{parsed.netloc}{parsed.path}"
            
            if base_url not in seen_base_urls:
                seen_base_urls[base_url] = True
                result.append(asset)
            elif asset.score_0_100 > 70:
                # Keep high-scoring variants
                result.append(asset)
        
        return result


def extract_assets(pages: List[Dict], domain: str = "") -> Dict:
    """
    Convenience function to extract assets from pages.
    
    Args:
        pages: List of page data dicts from crawler
        domain: Website domain
        
    Returns:
        Dictionary with logo and ranked assets
    """
    extractor = AssetExtractor(domain)
    result = extractor.extract_from_pages(pages, domain)
    return result.to_dict()
