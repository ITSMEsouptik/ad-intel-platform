"""
Novara Step 2: Website Context Extraction
Web crawler with HTTP-first approach and Playwright fallback
Smart Priority + Hard Limit crawling strategy
"""

import httpx
import asyncio
import re
import glob
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import time

logger = logging.getLogger(__name__)


def _find_browser_executable() -> Optional[str]:
    """Auto-discover Playwright browser executable regardless of version."""
    patterns = [
        '/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell',
        '/pw-browsers/chromium-*/chrome-linux/chrome',
        '/pw-browsers/chrome-linux/chrome',
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return matches[0]
    return None

# Page type priorities (higher = more important)
PAGE_PRIORITIES = {
    'pricing': 100,      # Most valuable - pricing info
    'services': 90,      # What they offer
    'product': 90,       # Product details
    'testimonials': 85,  # Social proof
    'reviews': 85,       # Social proof
    'about': 70,         # Trust, story
    'faq': 70,           # Objections, questions
    'contact': 60,       # Contact info
    'booking': 80,       # Booking flow, CTAs
    'team': 50,          # Team info
    'blog': 20,          # Lower priority
    'other': 10,         # Lowest
}

# Keywords to identify page types
PAGE_TYPE_KEYWORDS = {
    'pricing': ['pricing', 'prices', 'plans', 'packages', 'cost', 'rates', 'fees'],
    'services': ['services', 'service', 'solutions', 'what-we-do', 'offerings', 'our-work'],
    'product': ['products', 'product', 'shop', 'store', 'catalog', 'menu'],
    'testimonials': ['testimonials', 'testimonial', 'reviews', 'success-stories', 'case-studies', 'customers'],
    'reviews': ['reviews', 'review', 'feedback', 'ratings'],
    'about': ['about', 'about-us', 'who-we-are', 'our-story', 'story', 'mission'],
    'faq': ['faq', 'faqs', 'questions', 'help', 'support', 'frequently-asked'],
    'contact': ['contact', 'contact-us', 'get-in-touch', 'reach-us', 'location'],
    'booking': ['book', 'booking', 'schedule', 'appointment', 'reserve', 'bookonline'],
    'team': ['team', 'our-team', 'people', 'staff', 'experts'],
    'blog': ['blog', 'news', 'articles', 'posts', 'insights'],
}

# CTA keywords to identify call-to-action elements
CTA_KEYWORDS = [
    'book', 'buy', 'shop', 'order', 'get started', 'sign up', 'subscribe',
    'contact', 'call', 'whatsapp', 'chat', 'schedule', 'reserve', 'apply',
    'download', 'try', 'demo', 'quote', 'enquire', 'inquire', 'learn more',
    'get quote', 'free trial', 'start now', 'join', 'register'
]

# Social media patterns - IMPROVED: better URL extraction
SOCIAL_PATTERNS = {
    'instagram': r'(?:https?://)?(?:www\.)?(?:instagram\.com|instagr\.am)/([a-zA-Z0-9_\.]+)/?(?:\?|$|")',
    'tiktok': r'(?:https?://)?(?:www\.)?tiktok\.com/@?([a-zA-Z0-9_\.]+)/?(?:\?|$|")',
    'facebook': r'(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.com)/([a-zA-Z0-9_\.]+)/?(?:\?|$|")',
    'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/([a-zA-Z0-9_\-]+)/?(?:\?|$|")',
    'youtube': r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/(?:@|channel/|user/|c/)?([a-zA-Z0-9_\-]+)/?(?:\?|$|")',
    'twitter': r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/?(?:\?|$|")',
}

# Pages to skip (not valuable for ad creation)
SKIP_PATTERNS = [
    'privacy', 'terms', 'policy', 'legal', 'cookie', 'gdpr',
    'login', 'signin', 'signup', 'register', 'account', 'cart',
    'checkout', 'sitemap', 'rss', 'feed', 'tag/', 'category/',
    'author/', 'page/', 'wp-', 'admin'
]


@dataclass
class PageData:
    """Data extracted from a single page"""
    url: str
    page_type: str = 'other'
    title: str = ''
    meta_description: str = ''
    h1: str = ''
    headings: List[str] = field(default_factory=list)
    primary_ctas: List[str] = field(default_factory=list)
    extracted_text_md: str = ''
    raw_html: str = ''  # Full HTML before nav/footer stripping
    asset_urls_found: List[Dict] = field(default_factory=list)  # List of {url, alt, is_logo}
    og_image: str = ''  # OG image URL
    css_texts: List[str] = field(default_factory=list)  # CSS content
    structured_data: List[str] = field(default_factory=list)  # JSON-LD
    html_colors: List[str] = field(default_factory=list)  # Hex colors from full HTML
    fetch_method: str = 'http'
    success: bool = False
    error: str = ''


@dataclass
class CrawlResult:
    """Result of crawling a website"""
    website_url: str
    final_url: str
    domain: str
    crawl_started_at: datetime
    crawl_completed_at: Optional[datetime] = None
    fetch_method: str = 'http'
    pages_attempted: int = 0
    pages_fetched: int = 0
    pages: List[PageData] = field(default_factory=list)
    social_links: Dict[str, str] = field(default_factory=dict)
    all_links_found: List[str] = field(default_factory=list)
    css_texts: List[str] = field(default_factory=list)
    screenshot_base64: str = ""  # Homepage screenshot as base64
    errors: List[str] = field(default_factory=list)


class WebCrawler:
    """HTTP-first web crawler with Playwright fallback and smart prioritization"""
    
    def __init__(
        self,
        max_pages: int = 10,           # Hard limit: max pages to crawl
        max_time_seconds: int = 60,    # Hard limit: max total time
        page_timeout: int = 12,        # Per-page timeout
    ):
        self.max_pages = max_pages
        self.max_time_seconds = max_time_seconds
        self.page_timeout = page_timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        self.start_time = None
    
    def _time_remaining(self) -> float:
        """Check how much time is remaining"""
        if not self.start_time:
            return self.max_time_seconds
        elapsed = time.time() - self.start_time
        return max(0, self.max_time_seconds - elapsed)
    
    def _should_stop(self) -> bool:
        """Check if we should stop crawling"""
        return self._time_remaining() <= 0
    
    async def crawl(self, website_url: str) -> CrawlResult:
        """Main crawl method - orchestrates the entire crawl"""
        self.start_time = time.time()
        
        # Normalize URL
        if not website_url.startswith(('http://', 'https://')):
            website_url = f'https://{website_url}'
        
        parsed = urlparse(website_url)
        domain = parsed.netloc.replace('www.', '')
        
        result = CrawlResult(
            website_url=website_url,
            final_url=website_url,
            domain=domain,
            crawl_started_at=datetime.now(timezone.utc),
        )
        
        try:
            # Step 0: Capture screenshot first (parallel-friendly)
            logger.info("[CRAWLER] Capturing homepage screenshot...")
            screenshot_task = self._capture_screenshot(website_url)
            
            # Step 1: Fetch homepage
            logger.info(f"[CRAWLER] Fetching homepage: {website_url}")
            homepage = await self._fetch_page(website_url, 'home')
            result.pages_attempted += 1
            
            if not homepage.success:
                # Try Playwright fallback for homepage
                logger.info("[CRAWLER] HTTP failed, trying Playwright fallback")
                homepage = await self._fetch_page_playwright(website_url, 'home')
                if homepage.success:
                    result.fetch_method = 'playwright'
            
            # Get screenshot result
            result.screenshot_base64 = await screenshot_task
            logger.info(f"[CRAWLER] Screenshot captured: {len(result.screenshot_base64) > 0}")
            
            if homepage.success:
                result.pages_fetched += 1
                result.pages.append(homepage)
                result.final_url = homepage.url
                
                # Aggregate CSS from homepage
                result.css_texts.extend(homepage.css_texts)
                
                # Extract social links from homepage RAW HTML (not markdown, where nav/footer is stripped)
                result.social_links = self._extract_social_links_from_html(homepage.raw_html)
                
                # Step 2: Discover internal links from homepage HTML
                logger.info("[CRAWLER] Discovering internal links...")
                discovered_links = await self._discover_links_from_html(homepage.url, domain)
                result.all_links_found = [link for link, _, _ in discovered_links]
                logger.info(f"[CRAWLER] Found {len(discovered_links)} internal links")
                
                # Step 3: Prioritize and fetch additional pages
                prioritized = self._prioritize_links(discovered_links)
                logger.info(f"[CRAWLER] Prioritized {len(prioritized)} pages to crawl")
                
                for link, page_type, priority in prioritized:
                    # Check limits
                    if result.pages_fetched >= self.max_pages:
                        logger.info(f"[CRAWLER] Hit max pages limit ({self.max_pages})")
                        break
                    
                    if self._should_stop():
                        logger.info(f"[CRAWLER] Hit time limit ({self.max_time_seconds}s)")
                        break
                    
                    # Skip if already crawled
                    if any(p.url == link for p in result.pages):
                        continue
                    
                    logger.info(f"[CRAWLER] Fetching: {page_type} - {link}")
                    result.pages_attempted += 1
                    page = await self._fetch_page(link, page_type)
                    
                    if not page.success and result.fetch_method != 'http':
                        # Try Playwright if we used it for homepage
                        page = await self._fetch_page_playwright(link, page_type)
                        if page.success:
                            result.fetch_method = 'mixed'
                    
                    if page.success:
                        result.pages_fetched += 1
                        result.pages.append(page)
                        logger.info(f"[CRAWLER] ✓ Fetched: {page_type} ({result.pages_fetched}/{self.max_pages})")
                        
                        # Aggregate CSS (limit total)
                        if len(result.css_texts) < 10:
                            result.css_texts.extend(page.css_texts[:2])
                        
                        # Extract social links from each page's raw HTML
                        page_socials = self._extract_social_links_from_html(page.raw_html)
                        for platform, url in page_socials.items():
                            if platform not in result.social_links:
                                result.social_links[platform] = url
            else:
                result.errors.append(f"Failed to fetch homepage: {homepage.error}")
                logger.error(f"[CRAWLER] Failed to fetch homepage: {homepage.error}")
        
        except asyncio.TimeoutError:
            result.errors.append("Crawl timed out")
            logger.error("[CRAWLER] Crawl timed out")
        except Exception as e:
            result.errors.append(f"Crawl error: {str(e)}")
            logger.exception("[CRAWLER] Crawl failed")
        
        result.crawl_completed_at = datetime.now(timezone.utc)
        elapsed = time.time() - self.start_time
        logger.info(f"[CRAWLER] Complete: {result.pages_fetched} pages in {elapsed:.1f}s")
        
        return result
    
    async def _discover_links_from_html(self, base_url: str, domain: str) -> List[Tuple[str, str, int]]:
        """Discover internal links by fetching and parsing the page HTML"""
        links = []
        seen_urls = set()
        
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.page_timeout,
                headers=self.headers
            ) as client:
                response = await client.get(base_url)
                if response.status_code != 200:
                    return links
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    
                    # Skip empty, anchor, javascript, mailto links
                    if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                        continue
                    
                    # Build full URL
                    full_url = urljoin(base_url, href)
                    parsed = urlparse(full_url)
                    
                    # Must be same domain
                    if domain not in parsed.netloc:
                        continue
                    
                    # Normalize URL (remove fragments, trailing slashes)
                    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
                    
                    if normalized in seen_urls:
                        continue
                    seen_urls.add(normalized)
                    
                    # Skip unwanted pages
                    if self._should_skip_url(normalized):
                        continue
                    
                    # Determine page type and priority
                    page_type = self._detect_page_type(normalized, a.get_text(strip=True))
                    priority = PAGE_PRIORITIES.get(page_type, 10)
                    
                    links.append((normalized, page_type, priority))
        
        except Exception as e:
            logger.warning(f"[CRAWLER] Link discovery error: {e}")
        
        return links
    
    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped"""
        url_lower = url.lower()
        return any(skip in url_lower for skip in SKIP_PATTERNS)
    
    def _detect_page_type(self, url: str, link_text: str) -> str:
        """Detect page type from URL and link text"""
        url_lower = url.lower()
        text_lower = link_text.lower()
        
        for page_type, keywords in PAGE_TYPE_KEYWORDS.items():
            if any(kw in url_lower or kw in text_lower for kw in keywords):
                return page_type
        
        return 'other'
    
    def _prioritize_links(self, links: List[Tuple[str, str, int]]) -> List[Tuple[str, str, int]]:
        """Sort links by priority (highest first)"""
        # Sort by priority descending
        sorted_links = sorted(links, key=lambda x: x[2], reverse=True)
        
        # Limit to max_pages - 1 (since homepage is already fetched)
        return sorted_links[:self.max_pages - 1]
    
    async def _fetch_page(self, url: str, page_type: str = 'other') -> PageData:
        """Fetch a page using HTTP"""
        page_data = PageData(url=url, page_type=page_type, fetch_method='http')
        
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.page_timeout,
                headers=self.headers
            ) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Check if content is meaningful (not just JS loader)
                    if len(html) < 500 or self._is_js_heavy(html):
                        page_data.error = "Page appears to be JS-heavy"
                        return page_data
                    
                    page_data = self._parse_html(html, str(response.url), page_type, 'http')
                    page_data.success = True
                else:
                    page_data.error = f"HTTP {response.status_code}"
        
        except httpx.TimeoutException:
            page_data.error = "Timeout"
        except Exception as e:
            page_data.error = str(e)
        
        return page_data
    
    async def _fetch_page_playwright(self, url: str, page_type: str = 'other') -> PageData:
        """Fetch a page using Playwright (fallback for JS-heavy sites)"""
        page_data = PageData(url=url, page_type=page_type, fetch_method='playwright')
        
        try:
            import os
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
            from playwright.async_api import async_playwright
            
            executable = _find_browser_executable()
            launch_args = {'headless': True, 'args': ['--no-sandbox', '--disable-gpu']}
            if executable:
                launch_args['executable_path'] = executable
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(
                    user_agent=self.headers['User-Agent']
                )
                page = await context.new_page()
                
                try:
                    await page.goto(url, wait_until='networkidle', timeout=self.page_timeout * 1000)
                    html = await page.content()
                    
                    page_data = self._parse_html(html, url, page_type, 'playwright')
                    page_data.success = True
                finally:
                    await browser.close()
        
        except Exception as e:
            page_data.error = f"Playwright error: {str(e)}"
        
        return page_data
    
    async def _capture_screenshot(self, url: str) -> str:
        """Capture a full-page screenshot of a webpage using Playwright, return as base64"""
        try:
            import os
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'
            
            from playwright.async_api import async_playwright
            import base64
            
            executable = _find_browser_executable()
            launch_args = {'headless': True, 'args': ['--no-sandbox', '--disable-gpu']}
            if executable:
                launch_args['executable_path'] = executable
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(
                    viewport={'width': 1440, 'height': 900},
                    user_agent=self.headers['User-Agent']
                )
                page = await context.new_page()
                
                try:
                    await page.goto(url, wait_until='networkidle', timeout=25000)
                    # Scroll down to trigger lazy-loaded content, then back up
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 3)')
                    await page.wait_for_timeout(1500)
                    await page.evaluate('window.scrollTo(0, 0)')
                    await page.wait_for_timeout(3000)
                    
                    # Take full viewport screenshot (no clip — captures entire visible area)
                    screenshot_bytes = await page.screenshot(
                        type='jpeg',
                        quality=75,
                        full_page=False,
                    )
                    
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    return f"data:image/jpeg;base64,{screenshot_base64}"
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.warning(f"Screenshot capture failed: {e}")
            return ""
    
    def _is_js_heavy(self, html: str) -> bool:
        """Check if page is primarily JavaScript with little content"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style tags
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        
        text = soup.get_text(strip=True)
        return len(text) < 200
    
    def _parse_html(self, html: str, url: str, page_type: str, fetch_method: str) -> PageData:
        """Parse HTML and extract structured data"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = ''
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Extract meta description
        meta_desc = ''
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag:
            meta_desc = meta_tag.get('content', '')
        
        # Extract H1
        h1 = ''
        h1_tag = soup.find('h1')
        if h1_tag:
            h1 = h1_tag.get_text(strip=True)
        
        # Extract all headings
        headings = []
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            text = tag.get_text(strip=True)
            if text and len(text) < 200:
                headings.append(text)
        
        # Extract CTAs
        ctas = self._extract_ctas(soup)
        
        # Extract asset URLs
        assets = self._extract_assets(soup, url)
        
        # Extract OG image
        og_image = ''
        og_tag = soup.find('meta', property='og:image')
        if og_tag:
            og_image = og_tag.get('content', '')
            if og_image:
                og_image = urljoin(url, og_image)
        
        # Extract inline CSS - MUST be done BEFORE _html_to_markdown which destroys style tags!
        css_texts = self._extract_css(soup, url)
        
        # Extract hex colors from FULL HTML before truncation (inline styles, SVG fills)
        full_html_str = str(soup)
        html_colors = self._extract_html_colors(full_html_str)
        
        # Save raw HTML BEFORE markdown conversion strips nav/footer
        raw_html = full_html_str[:100000]  # Limit size for storage
        
        # Extract clean text as markdown (NOTE: this destroys script/style/nav/footer tags)
        text_md = self._html_to_markdown(soup)
        
        # NEW: Extract JSON-LD structured data
        structured_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            if script.string:
                structured_data.append(script.string.strip())
        
        return PageData(
            url=url,
            page_type=page_type,
            title=title,
            meta_description=meta_desc,
            h1=h1,
            headings=headings[:20],  # Limit to 20
            primary_ctas=ctas[:15],  # Limit to 15
            extracted_text_md=text_md[:50000],  # Limit size
            raw_html=raw_html,
            asset_urls_found=assets[:50],
            og_image=og_image,
            css_texts=css_texts,
            html_colors=html_colors,
            structured_data=structured_data[:5],
            fetch_method=fetch_method,
            success=True
        )
    
    def _extract_ctas(self, soup: BeautifulSoup) -> List[str]:
        """Extract call-to-action elements"""
        ctas = []
        
        # Find buttons and button-like elements
        for el in soup.find_all(['button', 'a']):
            text = el.get_text(strip=True).lower()
            classes = ' '.join(el.get('class', []))
            
            # Check if it looks like a CTA
            is_cta = (
                any(kw in text for kw in CTA_KEYWORDS) or
                'btn' in classes or
                'button' in classes or
                'cta' in classes or
                el.get('role') == 'button'
            )
            
            if is_cta and text and len(text) < 50:
                cta_text = el.get_text(strip=True)
                if cta_text and cta_text not in ctas:
                    ctas.append(cta_text)
        
        return ctas
    
    def _extract_assets(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract image assets with metadata (url, alt, is_logo)"""
        assets = []
        seen_urls = set()
        
        # Find Open Graph image first (usually best quality)
        og_image = soup.find('meta', property='og:image')
        if og_image:
            content = og_image.get('content')
            if content:
                full_url = urljoin(base_url, content)
                full_url = self._get_high_quality_image_url(full_url, is_logo=False)
                base_url_key = self._get_image_base_url(full_url)
                if base_url_key not in seen_urls:
                    seen_urls.add(base_url_key)
                    assets.append({
                        'url': full_url,
                        'alt': 'og:image',
                        'is_logo': False
                    })
        
        # Find images inside logo containers (header, nav, a.logo, etc.)
        logo_containers = soup.select(
            'header img, nav img, [class*="logo"] img, [id*="logo"] img, '
            'a[class*="logo"] img, a[href="/"] img'
        )
        logo_container_srcs = set()
        for img in logo_containers:
            src = img.get('src') or img.get('data-src')
            if src:
                logo_container_srcs.add(urljoin(base_url, src))
        
        # Find images
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                full_url = urljoin(base_url, src)
                alt = img.get('alt', '') or ''
                classes = ' '.join(img.get('class', []))
                parent_classes = ' '.join(img.parent.get('class', [])) if img.parent else ''
                
                # Check if this is a logo
                is_logo = (
                    'logo' in alt.lower() or 'logo' in src.lower() or
                    'logo' in classes.lower() or 'logo' in parent_classes.lower() or
                    full_url in logo_container_srcs
                )
                
                # Apply high-quality transformation with logo flag
                full_url = self._get_high_quality_image_url(full_url, is_logo=is_logo)
                base_url_key = self._get_image_base_url(full_url)
                
                if base_url_key not in seen_urls:
                    seen_urls.add(base_url_key)
                    assets.append({
                        'url': full_url,
                        'alt': alt[:100] if alt else '',
                        'is_logo': is_logo
                    })
        
        # Fallback: favicon / apple-touch-icon if no logo found yet
        has_logo = any(a.get('is_logo') for a in assets)
        if not has_logo:
            for link_tag in soup.find_all('link', rel=True):
                rel = ' '.join(link_tag.get('rel', []))
                if 'apple-touch-icon' in rel or ('icon' in rel and 'shortcut' not in rel):
                    href = link_tag.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        base_url_key = self._get_image_base_url(full_url)
                        if base_url_key not in seen_urls:
                            seen_urls.add(base_url_key)
                            assets.append({
                                'url': full_url,
                                'alt': 'site-icon',
                                'is_logo': True
                            })
                            break  # Only take the first icon
        
        return assets
    
    def _get_high_quality_image_url(self, url: str, is_logo: bool = False) -> str:
        """Convert image URL to high quality version by removing compression params"""
        # Handle Wix static images
        if 'wixstatic.com' in url:
            import re
            # Remove blur, low quality params
            url = re.sub(r',blur_\d+', '', url)
            url = re.sub(r',q_\d+', ',q_90', url)
            url = re.sub(r'q_\d+,', 'q_90,', url)
            url = re.sub(r',quality_auto', '', url)
            
            if is_logo:
                # For logos: use 'fit' to preserve aspect ratio, don't force square
                url = re.sub(r'/fill/', '/fit/', url)
                # Use larger dimensions but don't force square
                url = re.sub(r'/w_\d+,h_\d+,', '/w_500,h_500,', url)
            else:
                # For regular images: increase dimensions if too small
                url = re.sub(r'/w_\d{1,3},', '/w_800,', url)
                url = re.sub(r',w_\d{1,3},', ',w_800,', url)
                url = re.sub(r'/h_\d{1,3},', '/h_800,', url)
                url = re.sub(r',h_\d{1,3},', ',h_800,', url)
        
        # Handle Squarespace
        elif 'squarespace-cdn.com' in url or 'sqspcdn.com' in url:
            import re
            url = re.sub(r'\?format=\d+w', '?format=1500w', url)
        
        # Handle Shopify
        elif 'cdn.shopify.com' in url:
            import re
            url = re.sub(r'_\d+x\d*\.', '_1200x.', url)
            url = re.sub(r'_x\d+\.', '_x1200.', url)
        
        return url
    
    def _get_image_base_url(self, url: str) -> str:
        """Get base URL for deduplication (removes size/quality params)"""
        import re
        if 'wixstatic.com' in url:
            # Extract the media ID (e.g., 05aa54_cc95527f30d04cbb9af8dc1b19cbef5f~mv2)
            match = re.search(r'media/([a-f0-9_]+(?:~mv\d*)?(?:_d_\d+_\d+_s_\d+_\d+)?)', url)
            if match:
                return match.group(1)
        elif 'squarespace' in url or 'shopify' in url:
            # Just use the path without query params
            return url.split('?')[0].split('/')[-1]
        return url.split('?')[0]
    
    def _html_to_markdown(self, soup: BeautifulSoup) -> str:
        """Convert HTML to clean markdown-like text"""
        # Remove unwanted tags
        for tag in soup(['script', 'style', 'noscript', 'nav', 'footer', 'header', 'iframe']):
            tag.decompose()
        
        lines = []
        for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'span', 'div']):
            text = el.get_text(strip=True)
            if text and len(text) > 10:
                if el.name in ['h1', 'h2', 'h3', 'h4']:
                    lines.append(f"\n## {text}\n")
                else:
                    lines.append(text)
        
        # Deduplicate while preserving order
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    def _extract_social_links_from_html(self, text: str) -> Dict[str, str]:
        """Extract social media links from text/HTML - IMPROVED"""
        socials = {}
        
        # Common false positive usernames to skip
        skip_usernames = [
            'share', 'sharer', 'intent', 'home', 'search', 'login', 'signup',
            'about', 'help', 'support', 'contact', 'terms', 'privacy', 'policy',
            'pages', 'groups', 'events', 'watch', 'hashtag', 'explore', 'settings',
            'p', 'reel', 'reels', 'stories', 'tv', 'live'
        ]
        
        for platform, pattern in SOCIAL_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                username = match.group(1).strip().rstrip('/')
                
                # Skip common false positives
                if username.lower() in skip_usernames:
                    continue
                
                # Skip if it looks like a URL path component
                if len(username) < 2 or len(username) > 50:
                    continue
                
                # Skip if already found for this platform
                if platform in socials:
                    continue
                    
                if platform == 'instagram':
                    socials[platform] = f"https://instagram.com/{username}"
                elif platform == 'tiktok':
                    socials[platform] = f"https://tiktok.com/@{username}"
                elif platform == 'facebook':
                    socials[platform] = f"https://facebook.com/{username}"
                elif platform == 'linkedin':
                    socials[platform] = f"https://linkedin.com/company/{username}"
                elif platform == 'youtube':
                    socials[platform] = f"https://youtube.com/@{username}"
                elif platform == 'twitter':
                    socials[platform] = f"https://twitter.com/{username}"
        
        # Also look for @handles mentioned in text (e.g., "on our Instagram @example-brand.co")
        if 'instagram' not in socials:
            # Pattern: "Instagram @handle" - handle is alphanumeric with dots/underscores
            # Must stop at uppercase letters that start a new word (like "Want")
            ig_handle_patterns = [
                r'(?:instagram|IG)\s*@([a-z0-9_.]+(?:\.[a-z]{2,3})?)',  # Instagram @handle or @handle.co
            ]
            for pattern in ig_handle_patterns:
                ig_match = re.search(pattern, text, re.IGNORECASE)
                if ig_match:
                    handle = ig_match.group(1).strip()
                    # Remove any trailing uppercase words that got captured
                    handle = re.sub(r'[A-Z][a-z]+.*$', '', handle)
                    if len(handle) >= 2 and handle.lower() not in skip_usernames:
                        socials['instagram'] = f"https://instagram.com/{handle}"
                        break
        
        if 'tiktok' not in socials:
            tt_handle_patterns = [
                r'(?:tiktok)\s*@([a-z0-9_.]+)',
            ]
            for pattern in tt_handle_patterns:
                tt_match = re.search(pattern, text, re.IGNORECASE)
                if tt_match:
                    handle = tt_match.group(1).strip()
                    handle = re.sub(r'[A-Z][a-z]+.*$', '', handle)
                    if len(handle) >= 2 and handle.lower() not in skip_usernames:
                        socials['tiktok'] = f"https://tiktok.com/@{handle}"
                        break
        
        return socials
    
    
    def _extract_html_colors(self, full_html: str) -> List[str]:
        """Extract hex colors from inline styles and SVG attributes in full HTML.
        This runs on the FULL HTML before truncation to capture all brand colors."""
        import re
        colors = set()
        
        # Inline styles: style="color:#E21C21" or style="background: #fff"
        for m in re.finditer(r'style="[^"]*?#([0-9a-fA-F]{6})\b', full_html, re.IGNORECASE):
            colors.add(m.group(1).lower())
        
        # SVG fill/stroke: fill="#191919"
        for m in re.finditer(r'(?:fill|stroke)="#([0-9a-fA-F]{6})"', full_html, re.IGNORECASE):
            colors.add(m.group(1).lower())
        
        # data-color attributes
        for m in re.finditer(r'data-color="[^"]*?#([0-9a-fA-F]{6})', full_html, re.IGNORECASE):
            colors.add(m.group(1).lower())
        
        return list(colors)[:100]  # Limit to 100 unique colors

    def _extract_css(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract CSS from inline styles and external stylesheets (max 3)"""
        css_texts = []
        
        # 1. Extract inline <style> tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                css_texts.append(style_tag.string)
        
        # 2. Extract external stylesheets (max 3)
        external_css_urls = []
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                # Skip common CDN/library CSS
                if not any(x in full_url.lower() for x in ['cdn', 'googleapis', 'jsdelivr', 'cloudflare', 'bootstrap', 'fontawesome']):
                    external_css_urls.append(full_url)
        
        # Fetch up to 3 external stylesheets (sync for simplicity)
        import httpx
        for css_url in external_css_urls[:3]:
            try:
                response = httpx.get(css_url, timeout=5, headers=self.headers, follow_redirects=True)
                if response.status_code == 200 and 'text/css' in response.headers.get('content-type', ''):
                    css_texts.append(response.text[:50000])  # Limit size
            except Exception as e:
                logger.debug(f"Failed to fetch CSS {css_url}: {e}")
        
        return css_texts

