"""
Novara Step 2: Website Context Extraction (Refactored)
Extracts raw data from crawled pages for LLM summarization

Changes from previous version:
- Removed testimonials (moved to Market Intel step)
- New schema alignment with Step2Summary
- Returns raw extraction data for LLM processing
"""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse
import logging

from crawler import CrawlResult, PageData

logger = logging.getLogger(__name__)


# Price extraction patterns
PRICE_PATTERNS = [
    r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
    r'€\d+(?:,\d{3})*(?:\.\d{2})?',
    r'£\d+(?:,\d{3})*(?:\.\d{2})?',
    r'₹\d+(?:,\d{3})*(?:\.\d{2})?',
    r'AED\s*\d+(?:,\d{3})*(?:\.\d{2})?',
    r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR|AED)',
]

# CTA patterns
CTA_KEYWORDS = [
    'book', 'buy', 'shop', 'order', 'get started', 'sign up', 'subscribe',
    'contact', 'call', 'whatsapp', 'chat', 'schedule', 'reserve', 'apply',
    'download', 'try', 'demo', 'quote', 'enquire', 'learn more',
]

# Garbage patterns to filter
GARBAGE_PATTERNS = [
    r'bottom of page', r'top of page', r'skip to content',
    r'cookie policy', r'privacy policy', r'terms of service',
    r'all rights reserved', r'copyright \d{4}', r'©\s*\d{4}',
    r'powered by', r'built with', r'website by',
]


def clean_text(text: str) -> str:
    """Clean text by removing garbage and normalizing whitespace"""
    if not text:
        return ''
    for pattern in GARBAGE_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()


def is_question(text: str) -> bool:
    """Check if text is a question"""
    text = text.strip()
    if text.endswith('?'):
        return True
    question_starters = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'do', 'is', 'are']
    return any(text.lower().startswith(q) for q in question_starters)


@dataclass
class RawExtraction:
    """Raw extraction data for LLM processing"""
    # Site info
    input_url: str = ""
    final_url: str = ""
    title: str = ""
    meta_description: str = ""
    language: str = "en"
    
    # Content
    pages_crawled: int = 0
    text_chunks: List[str] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    links: List[Dict] = field(default_factory=list)  # {text, href}
    
    # Images
    images: List[Dict] = field(default_factory=list)  # {src, alt, context}
    og_images: List[str] = field(default_factory=list)
    
    # Brand identity (from CSS)
    css_font_families: List[str] = field(default_factory=list)
    css_colors: List[str] = field(default_factory=list)
    
    # Structured data
    structured_data_jsonld: List[str] = field(default_factory=list)
    
    # CTAs
    ctas: List[str] = field(default_factory=list)
    
    # Prices with source URLs
    price_mentions: List[Dict] = field(default_factory=list)  # {text, source_url}
    
    # Social links
    social_links: Dict[str, str] = field(default_factory=dict)
    
    # Contact
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "pages_crawled": self.pages_crawled,
            "text_chunks": self.text_chunks,
            "headings": self.headings,
            "links": self.links,
            "images": self.images,
            "css_font_families": self.css_font_families,
            "css_colors": self.css_colors,
            "structured_data_jsonld": self.structured_data_jsonld,
        }


class ExtractionEngine:
    """Extracts raw data from crawled pages for Step 2 processing"""
    
    def extract_raw(self, crawl_result: CrawlResult) -> RawExtraction:
        """
        Extract raw data from crawl result.
        This data will be processed by code (pricing, assets, brand identity)
        and then summarized by the LLM.
        """
        raw = RawExtraction()
        
        if not crawl_result.pages:
            return raw
        
        raw.input_url = crawl_result.website_url
        raw.final_url = crawl_result.final_url
        raw.pages_crawled = crawl_result.pages_fetched
        raw.social_links = crawl_result.social_links
        
        homepage = crawl_result.pages[0]
        raw.title = homepage.title
        raw.meta_description = homepage.meta_description
        
        # Detect language
        raw.language = self._detect_language(homepage.extracted_text_md)
        
        # Aggregate from all pages
        all_text_chunks = []
        all_headings = []
        all_ctas = []
        all_images = []
        price_mentions = []
        
        for page in crawl_result.pages:
            # Text chunks
            chunks = self._extract_text_chunks(page.extracted_text_md)
            all_text_chunks.extend(chunks)
            
            # Headings (filter questions)
            for h in page.headings:
                cleaned = clean_text(h)
                if cleaned and not is_question(cleaned):
                    all_headings.append(cleaned)
            
            # CTAs
            all_ctas.extend(page.primary_ctas)
            
            # Images with context
            for asset_url in page.asset_urls_found:
                all_images.append({
                    "src": asset_url,
                    "alt": "",
                    "context": page.page_type
                })
            
            # OG image
            if page.og_image:
                raw.og_images.append(page.og_image)
            
            # Links from page
            # (Already extracted in crawler, but we can add more context here)
            
            # Price mentions with source URL
            prices = self._extract_prices(page.extracted_text_md)
            for price in prices:
                price_mentions.append({
                    "text": price,
                    "source_url": page.url
                })
            
            # Structured data
            raw.structured_data_jsonld.extend(page.structured_data)
        
        # Dedupe and limit
        raw.text_chunks = list(dict.fromkeys(all_text_chunks))[:100]
        raw.headings = list(dict.fromkeys(all_headings))[:50]
        raw.ctas = list(dict.fromkeys(all_ctas))[:30]
        raw.images = all_images[:100]
        raw.price_mentions = price_mentions[:200]
        
        # Extract emails and phones from all text
        all_text = '\n'.join(p.extracted_text_md for p in crawl_result.pages)
        raw.emails = self._extract_emails(all_text)
        raw.phones = self._extract_phones(all_text)
        
        # CSS extraction (fonts and colors are extracted by brand_identity.py)
        # Just store raw CSS text references here
        raw.css_font_families = self._extract_font_mentions(crawl_result.css_texts)
        raw.css_colors = self._extract_color_mentions(crawl_result.css_texts)
        
        return raw
    
    def _extract_text_chunks(self, text: str) -> List[str]:
        """Extract meaningful text chunks"""
        chunks = []
        
        # Split by newlines and paragraphs
        lines = text.split('\n')
        
        for line in lines:
            cleaned = clean_text(line)
            # Keep chunks that are meaningful length
            if 20 < len(cleaned) < 500:
                chunks.append(cleaned)
        
        return chunks
    
    def _extract_prices(self, text: str) -> List[str]:
        """Extract price mentions from text"""
        prices = []
        for pattern in PRICE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prices.extend(matches)
        return prices[:50]  # Limit
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses, filtering malformed ones from HTML concatenation."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, text)
        
        cleaned = []
        for e in emails:
            # Filter common false positives
            if any(x in e.lower() for x in ['example', 'test', 'sample', 'wix', 'squarespace', 'sentry']):
                continue
            # Fix emails with text concatenated to TLD (e.g., "info@brand.coWHAT")
            # Valid TLDs are 2-6 chars, all lowercase alpha
            tld_match = re.match(r'^(.+@.+\.)([a-zA-Z]+)$', e)
            if tld_match:
                tld = tld_match.group(2)
                # If TLD has mixed case or is too long, truncate to valid part
                if len(tld) > 6 or not tld.islower():
                    clean_tld = ''
                    for c in tld:
                        if c.islower():
                            clean_tld += c
                        else:
                            break
                    if len(clean_tld) >= 2:
                        e = tld_match.group(1) + clean_tld
                    else:
                        continue
            cleaned.append(e.lower())
        
        return list(set(cleaned))[:5]
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers, filtering out product codes and false positives."""
        patterns = [
            r'\+\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}',
            r'\(\d{3}\)\s*\d{3}[\s.-]?\d{4}',
        ]
        phones = []
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for m in matches:
                phone = m.group(0).strip()
                digits = re.sub(r'\D', '', phone)
                if len(digits) < 7 or len(digits) > 15:
                    continue
                if digits == digits[0] * len(digits):
                    continue
                # Require +, ( or context that suggests it's actually a phone
                # Lines with just 3-3-4 digit pattern without + or ( are usually SKUs/IDs
                if not phone.startswith('+') and not phone.startswith('('):
                    # Check surrounding text for phone indicators
                    start = max(0, m.start() - 60)
                    end = min(len(text), m.end() + 30)
                    context = text[start:end].lower()
                    phone_hints = ['phone', 'tel', 'call', 'mobile', 'whatsapp', 'contact', 'dial', 'fax']
                    if not any(hint in context for hint in phone_hints):
                        continue
                phones.append(phone)
        return list(set(phones))[:5]
    
    def _extract_font_mentions(self, css_texts: List[str]) -> List[str]:
        """Extract font family mentions from CSS (raw)"""
        fonts = []
        all_css = '\n'.join(css_texts)
        
        pattern = r'font-family:\s*["\']?([^"\';\}]+)'
        matches = re.findall(pattern, all_css, re.IGNORECASE)
        
        for match in matches:
            # Get first font in the stack
            first_font = match.split(',')[0].strip().strip('"\'')
            if first_font and len(first_font) > 2:
                fonts.append(first_font)
        
        return list(set(fonts))[:20]
    
    def _extract_color_mentions(self, css_texts: List[str]) -> List[str]:
        """Extract color mentions from CSS (raw)"""
        colors = []
        all_css = '\n'.join(css_texts)
        
        # Hex colors
        hex_pattern = r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b'
        hex_matches = re.findall(hex_pattern, all_css)
        for h in hex_matches:
            if len(h) == 3:
                h = ''.join([c*2 for c in h])
            colors.append(f'#{h.lower()}')
        
        return list(set(colors))[:30]
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on common words"""
        text_lower = text.lower()
        
        # Check for common Arabic words
        if any(x in text_lower for x in ['و', 'في', 'على', 'من']):
            return 'ar'
        
        # Check for common French words
        if any(x in text_lower for x in ['nous', 'vous', 'est', 'les', 'des']):
            return 'fr'
        
        # Check for common Spanish words
        if any(x in text_lower for x in ['nosotros', 'usted', 'está', 'los', 'las']):
            return 'es'
        
        # Default to English
        return 'en'


def extract_raw_for_step2(crawl_result: CrawlResult) -> Dict:
    """
    Convenience function to extract raw data for Step 2.
    
    Args:
        crawl_result: Result from crawler
        
    Returns:
        Dictionary with raw extraction data
    """
    engine = ExtractionEngine()
    raw = engine.extract_raw(crawl_result)
    
    return {
        "site": {
            "input_url": raw.input_url,
            "final_url": raw.final_url,
            "title": raw.title,
            "meta_description": raw.meta_description,
            "language": raw.language
        },
        "text_chunks": raw.text_chunks,
        "headings": raw.headings,
        "ctas": raw.ctas,
        "images": raw.images,
        "og_images": raw.og_images,
        "price_mentions": raw.price_mentions,
        "social_links": raw.social_links,
        "emails": raw.emails,
        "phones": raw.phones,
        "css_font_families": raw.css_font_families,
        "css_colors": raw.css_colors,
        "structured_data_jsonld": raw.structured_data_jsonld,
        "pages_crawled": raw.pages_crawled
    }
