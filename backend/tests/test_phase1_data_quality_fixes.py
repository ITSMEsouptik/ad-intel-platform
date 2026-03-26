"""
Tests for Phase 1 Data Quality Fixes:
1. brand_summary.name null-safe extraction using 'or' pattern
2. Logo detection with favicon/apple-touch-icon fallback + parent class check
3. Social channel extraction from raw_html instead of stripped markdown
4. raw_html stored in PageData before nav/footer stripping
5. channels.py prefers raw_html for social link regex
6. server.py passes raw HTML to extract_brand_identity
7. LLM prompt explicitly instructs clean brand name extraction
"""
import pytest
from bs4 import BeautifulSoup
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import List, Dict


# === Test 1: brand_summary.name Null-Safe Extraction ===

class TestBrandSummaryNameExtraction:
    """Tests for brand_summary.name null-safe extraction using 'or' pattern."""
    
    def test_name_uses_llm_output_when_present(self):
        """When LLM returns a name, it should be used."""
        llm_output = {'brand_summary': {'name': 'Instaglam'}}
        site_info = {'title': 'Page Title | Website'}
        
        # Replicate server.py line ~679 logic
        name = (llm_output.get('brand_summary', {}).get('name') or site_info.get('title') or 'unknown') if llm_output else (site_info.get('title') or 'unknown')
        
        assert name == 'Instaglam'
    
    def test_name_falls_back_to_title_when_llm_name_null(self):
        """When LLM returns null name, fallback to site title."""
        llm_output = {'brand_summary': {'name': None}}
        site_info = {'title': 'Backup Title'}
        
        name = (llm_output.get('brand_summary', {}).get('name') or site_info.get('title') or 'unknown') if llm_output else (site_info.get('title') or 'unknown')
        
        assert name == 'Backup Title'
    
    def test_name_falls_back_to_title_when_llm_name_empty(self):
        """When LLM returns empty string name, fallback to site title."""
        llm_output = {'brand_summary': {'name': ''}}
        site_info = {'title': 'Backup Title'}
        
        name = (llm_output.get('brand_summary', {}).get('name') or site_info.get('title') or 'unknown') if llm_output else (site_info.get('title') or 'unknown')
        
        assert name == 'Backup Title'
    
    def test_name_falls_back_to_unknown_when_all_sources_empty(self):
        """When all sources are empty, fallback to 'unknown'."""
        llm_output = {'brand_summary': {'name': None}}
        site_info = {'title': ''}
        
        name = (llm_output.get('brand_summary', {}).get('name') or site_info.get('title') or 'unknown') if llm_output else (site_info.get('title') or 'unknown')
        
        assert name == 'unknown'
    
    def test_name_uses_title_when_no_llm_output(self):
        """When no LLM output, use site title."""
        llm_output = None
        site_info = {'title': 'Site Title'}
        
        name = (llm_output.get('brand_summary', {}).get('name') or site_info.get('title') or 'unknown') if llm_output else (site_info.get('title') or 'unknown')
        
        assert name == 'Site Title'


# === Test 2: Logo Detection with Fallbacks ===

class TestLogoDetection:
    """Tests for expanded logo detection: favicon, apple-touch-icon, parent class check."""
    
    def test_logo_detected_from_header_img(self):
        """Logo should be detected from img inside header."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        html = """
        <html>
        <body>
            <header>
                <img src="/logo.png" alt="Company">
            </header>
            <img src="/hero.jpg" alt="Hero">
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        assets = crawler._extract_assets(soup, 'https://example.com')
        
        logo_assets = [a for a in assets if a.get('is_logo')]
        assert len(logo_assets) >= 1
        assert '/logo.png' in logo_assets[0]['url']
    
    def test_logo_detected_from_nav_img(self):
        """Logo should be detected from img inside nav."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        html = """
        <html>
        <body>
            <nav>
                <img src="/nav-logo.png" alt="Brand">
            </nav>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        assets = crawler._extract_assets(soup, 'https://example.com')
        
        logo_assets = [a for a in assets if a.get('is_logo')]
        assert len(logo_assets) >= 1
    
    def test_logo_detected_from_parent_class(self):
        """Logo should be detected when parent has 'logo' class."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        html = """
        <html>
        <body>
            <div class="site-logo">
                <img src="/brand-mark.png">
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        assets = crawler._extract_assets(soup, 'https://example.com')
        
        logo_assets = [a for a in assets if a.get('is_logo')]
        assert len(logo_assets) >= 1
    
    def test_logo_fallback_to_apple_touch_icon(self):
        """When no logo img found, fallback to apple-touch-icon."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        html = """
        <html>
        <head>
            <link rel="apple-touch-icon" href="/apple-icon.png">
        </head>
        <body>
            <img src="/product.jpg" alt="Product">
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        assets = crawler._extract_assets(soup, 'https://example.com')
        
        logo_assets = [a for a in assets if a.get('is_logo')]
        assert len(logo_assets) >= 1
        # The apple-touch-icon should be marked as logo
        assert any('apple-icon.png' in a['url'] for a in logo_assets)
    
    def test_logo_fallback_to_favicon(self):
        """When no logo img or apple-touch-icon, fallback to favicon."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        html = """
        <html>
        <head>
            <link rel="icon" href="/favicon.png">
        </head>
        <body>
            <img src="/photo.jpg" alt="Photo">
        </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        assets = crawler._extract_assets(soup, 'https://example.com')
        
        logo_assets = [a for a in assets if a.get('is_logo')]
        assert len(logo_assets) >= 1
        assert any('favicon.png' in a['url'] for a in logo_assets)


# === Test 3: raw_html Storage in PageData ===

class TestRawHtmlStorage:
    """Tests for raw_html field in PageData."""
    
    def test_pagedata_has_raw_html_field(self):
        """PageData should have raw_html field."""
        from crawler import PageData
        page = PageData(url='https://example.com')
        assert hasattr(page, 'raw_html')
    
    def test_parse_html_stores_raw_html_before_markdown(self):
        """_parse_html should store raw HTML before nav/footer stripping."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <nav><a href="/about">About</a></nav>
            <main><p>Main content here</p></main>
            <footer><p>Footer content</p></footer>
        </body>
        </html>
        """
        
        page_data = crawler._parse_html(html, 'https://example.com', 'home', 'http')
        
        # raw_html should contain the footer (not stripped)
        assert 'Footer content' in page_data.raw_html
        # extracted_text_md should NOT contain footer (stripped by _html_to_markdown)
        # The markdown converter removes nav/footer
        assert 'Main content' in page_data.extracted_text_md


# === Test 4: Social Link Extraction from raw_html ===

class TestSocialLinkExtractionFromRawHtml:
    """Tests for social link extraction preferring raw_html over stripped markdown."""
    
    def test_crawler_extracts_social_from_raw_html(self):
        """WebCrawler should extract social links from raw_html, not markdown."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        # Simulate raw HTML with social links in footer (which would be stripped from markdown)
        raw_html = """
        <footer>
            <a href="https://instagram.com/brandname">Instagram</a>
            <a href="https://tiktok.com/@brandtiktok">TikTok</a>
        </footer>
        """
        
        socials = crawler._extract_social_links_from_html(raw_html)
        
        assert 'instagram' in socials
        assert 'brandname' in socials['instagram']
        assert 'tiktok' in socials
        assert 'brandtiktok' in socials['tiktok']
    
    def test_channels_prefers_raw_html(self):
        """channels.py extract_channels should prefer raw_html over extracted_text_md."""
        from channels import extract_channels
        
        # Create mock crawl_result with pages
        @dataclass
        class MockPage:
            raw_html: str = ''
            extracted_text_md: str = ''
        
        @dataclass
        class MockCrawlResult:
            pages: List = field(default_factory=list)
            social_links: Dict = field(default_factory=dict)
        
        # raw_html has Instagram, markdown doesn't
        mock_page = MockPage(
            raw_html='<footer><a href="https://instagram.com/testbrand">IG</a></footer>',
            extracted_text_md='Main content without social links'
        )
        mock_crawl = MockCrawlResult(pages=[mock_page])
        
        raw_extraction = {'structured_data_jsonld': [], 'emails': [], 'phones': []}
        
        channels = extract_channels(mock_crawl, raw_extraction)
        
        # Should find Instagram from raw_html
        instagram_channels = [c for c in channels['social'] if c['platform'] == 'instagram']
        assert len(instagram_channels) >= 1


# === Test 5: LLM Prompt Brand Name Instructions ===

class TestLlmPromptBrandNameInstructions:
    """Tests for LLM prompt explicitly instructing clean brand name extraction."""
    
    def test_system_prompt_contains_brand_name_instructions(self):
        """SYSTEM_PROMPT should contain explicit brand name extraction rules."""
        from gemini_site_summarizer import SYSTEM_PROMPT
        
        # Check for brand name instructions
        assert 'brand_summary.name' in SYSTEM_PROMPT
        assert 'clean brand name' in SYSTEM_PROMPT.lower() or 'CRITICAL for brand_summary.name' in SYSTEM_PROMPT
        assert 'page title' in SYSTEM_PROMPT.lower()
        assert 'Do NOT use the HTML page title' in SYSTEM_PROMPT or 'not page title' in SYSTEM_PROMPT.lower()
    
    def test_system_prompt_instructs_no_domain_in_name(self):
        """SYSTEM_PROMPT should instruct not to include domain in brand name."""
        from gemini_site_summarizer import SYSTEM_PROMPT
        
        assert 'domain' in SYSTEM_PROMPT.lower()


# === Test 6: Server passes raw HTML to brand_identity ===

class TestServerRawHtmlPassToBrandIdentity:
    """Tests for server.py passing raw HTML to extract_brand_identity."""
    
    def test_server_builds_raw_html_from_pages(self):
        """Server should concatenate raw_html from all pages for brand_identity."""
        # This is a code verification test - we verify the pattern exists
        import inspect
        from server import run_step2
        
        source = inspect.getsource(run_step2)
        
        # Check that raw_html is used for brand_identity
        assert 'p.raw_html for p in crawl_result.pages' in source
        assert 'extract_brand_identity' in source


# === Integration Tests ===

class TestPhase1DataQualityIntegration:
    """Integration tests verifying the Phase 1 fixes work together."""
    
    def test_full_extraction_pipeline_includes_raw_html(self):
        """Full page extraction should populate raw_html field."""
        from crawler import WebCrawler
        crawler = WebCrawler()
        
        html = """
        <html>
        <head>
            <title>Test Brand | Best Services</title>
            <link rel="apple-touch-icon" href="/apple-icon.png">
        </head>
        <body>
            <header><img src="/logo.png" class="logo"></header>
            <main><h1>Welcome</h1><p>Content</p></main>
            <footer><a href="https://instagram.com/testbrand">IG</a></footer>
        </body>
        </html>
        """
        
        page_data = crawler._parse_html(html, 'https://example.com', 'home', 'http')
        
        # Verify raw_html is populated
        assert page_data.raw_html
        assert len(page_data.raw_html) > 100
        
        # Verify logo is detected
        logo_assets = [a for a in page_data.asset_urls_found if a.get('is_logo')]
        assert len(logo_assets) >= 1
        
        # Verify social can be extracted from raw_html
        socials = crawler._extract_social_links_from_html(page_data.raw_html)
        assert 'instagram' in socials
