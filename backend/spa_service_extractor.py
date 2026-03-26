"""
SPA Service Extractor
Extracts all services from Single Page Applications with tabbed content.

Strategy:
  1. Playwright (multi-platform): Click through tabs, extract via DOM selectors
  2. Jina fallback (generic): Fetch rendered markdown, parse service patterns
"""

import os
import re
import glob
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '/pw-browsers'

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
            logger.info(f"[BROWSER] Found: {matches[0]}")
            return matches[0]
    return None


@dataclass
class ExtractedService:
    category: str
    name: str
    price: str = ""
    duration: str = ""
    description: str = ""
    booking_url: str = ""

    def to_dict(self) -> Dict:
        d = {
            "category": self.category,
            "name": self.name,
            "price": self.price,
            "duration": self.duration,
        }
        if self.description:
            d["description"] = self.description
        if self.booking_url:
            d["booking_url"] = self.booking_url
        return d


@dataclass
class SPAServiceResult:
    categories: List[str] = field(default_factory=list)
    services: List[ExtractedService] = field(default_factory=list)
    source_url: str = ""
    method: str = ""  # "playwright" or "jina"

    def to_text_block(self) -> str:
        """Convert to a text block suitable for LLM consumption."""
        if not self.services:
            return ""
        lines = ["COMPLETE SERVICE CATALOG (all categories):"]
        current_cat = ""
        for svc in self.services:
            if svc.category != current_cat:
                current_cat = svc.category
                lines.append(f"\n[{current_cat}]")
            price_str = f" - {svc.price}" if svc.price else ""
            dur_str = f" ({svc.duration})" if svc.duration else ""
            desc_str = f"  >> {svc.description}" if svc.description else ""
            lines.append(f"  {svc.name}{price_str}{dur_str}")
            if desc_str:
                lines.append(desc_str)
        return "\n".join(lines)

    def to_offer_catalog(self) -> List[Dict]:
        """Convert to offer_catalog format with proper structure."""
        items = []
        seen = set()
        for svc in self.services:
            key = f"{svc.category}:{svc.name}"
            if key in seen:
                continue
            seen.add(key)
            
            # Parse numeric price from text like "950 UAE dirhams" or "AED 950"
            price_numeric = None
            currency = ""
            if svc.price:
                import re
                num_match = re.search(r'([\d,]+(?:\.\d{2})?)', svc.price)
                if num_match:
                    try:
                        price_numeric = float(num_match.group(1).replace(',', ''))
                    except ValueError:
                        pass
                # Detect currency
                price_lower = svc.price.lower()
                if 'aed' in price_lower or 'dirham' in price_lower or 'uae' in price_lower:
                    currency = 'AED'
                elif '$' in svc.price or 'usd' in price_lower or 'dollar' in price_lower:
                    currency = 'USD'
                elif '€' in svc.price or 'eur' in price_lower:
                    currency = 'EUR'
                elif '£' in svc.price or 'gbp' in price_lower:
                    currency = 'GBP'
            
            items.append({
                "name": svc.name,
                "category": svc.category,
                "price_display": svc.price,
                "price_numeric": price_numeric,
                "currency": currency,
                "duration": svc.duration,
            })
            if svc.description:
                items[-1]["description"] = svc.description
            if svc.booking_url:
                items[-1]["booking_url"] = svc.booking_url
        return items

    def to_grouped_catalog(self) -> List[Dict]:
        """Convert to grouped catalog format with per-category stats."""
        from collections import defaultdict
        groups = defaultdict(list)
        for svc in self.services:
            groups[svc.category].append(svc)
        
        result = []
        for category, svcs in groups.items():
            prices = []
            for s in svcs:
                import re
                num_match = re.search(r'([\d,]+(?:\.\d{2})?)', s.price) if s.price else None
                if num_match:
                    try:
                        prices.append(float(num_match.group(1).replace(',', '')))
                    except ValueError:
                        pass
            
            result.append({
                "category": category,
                "count": len(svcs),
                "price_range": {
                    "min": min(prices) if prices else None,
                    "max": max(prices) if prices else None,
                },
                "services": [
                    {
                        "name": s.name,
                        "price_display": s.price,
                        "duration": s.duration,
                        **({"description": s.description} if s.description else {}),
                        **({"booking_url": s.booking_url} if s.booking_url else {}),
                    }
                    for s in svcs
                ]
            })
        return result


def _find_booking_url(crawl_pages: list, all_links: list) -> Optional[str]:
    """Detect if the site has a booking/services page with tabbed content.
    Returns the most likely booking page URL, prioritizing booking-specific pages."""
    high_priority = ["bookonline", "book-online", "booking", "book-now"]
    low_priority = ["our-services", "services", "menu"]

    def _check_urls(urls, keywords):
        for url in urls:
            url_str = url.url.lower() if hasattr(url, 'url') else str(url).lower()
            if any(kw in url_str for kw in keywords):
                return url.url if hasattr(url, 'url') else str(url)
        return None

    result = _check_urls(crawl_pages, high_priority)
    if result:
        return result
    result = _check_urls(all_links, high_priority)
    if result:
        return result
    result = _check_urls(crawl_pages, low_priority)
    if result:
        return result
    result = _check_urls(all_links, low_priority)
    if result:
        return result
    return None


# ==================== STRATEGY 1: PLAYWRIGHT (Multi-platform) ====================

async def _extract_via_playwright(booking_url: str) -> SPAServiceResult:
    """Extract services via Playwright. Tries Wix-specific selectors first,
    then falls back to generic DOM extraction for other platforms.
    Includes retry on timeout with fresh browser context."""
    from playwright.async_api import async_playwright

    executable = _find_browser_executable()
    launch_args = {'headless': True, 'args': ['--no-sandbox', '--disable-gpu']}
    if executable:
        launch_args['executable_path'] = executable

    for attempt in range(2):
        result = SPAServiceResult(source_url=booking_url, method="playwright")
        timeout_ms = 45000 if attempt == 0 else 60000
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(**launch_args)
                page = await browser.new_page(viewport={'width': 1440, 'height': 900})
                try:
                    # Use domcontentloaded instead of networkidle (Wix never stops requesting)
                    await page.goto(booking_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    # Wait for Wix booking widget OR generic page content
                    try:
                        await page.wait_for_selector(
                            '[data-hook="tags-list-tag"], [data-hook="service-list-widget"], .service-list, .booking-catalog, main',
                            timeout=15000
                        )
                    except Exception:
                        pass
                    await page.wait_for_timeout(3000)

                    tabs = await page.query_selector_all('[data-hook="tags-list-tag"] label')
                    if tabs:
                        result = await _extract_wix_services(page, tabs, booking_url)
                        if result.services:
                            return result

                    result = await _extract_generic_spa_services(page, booking_url)
                    if result.services:
                        return result

                    result = await _extract_page_text_services(page, booking_url)
                    return result
                finally:
                    await browser.close()
        except Exception as e:
            logger.warning(f"[SPA_EXTRACT] Playwright attempt {attempt+1} failed: {e}")
            if attempt == 0:
                logger.info("[SPA_EXTRACT] Retrying with extended timeout...")
                continue
    return SPAServiceResult(source_url=booking_url, method="playwright-failed")


async def _extract_wix_services(page, tabs, booking_url: str) -> SPAServiceResult:
    """Wix-specific: click through booking tabs and extract via data-hook selectors."""
    result = SPAServiceResult(source_url=booking_url, method="playwright-wix")
    tab_names = []
    for tab in tabs:
        name = (await tab.inner_text()).strip()
        tab_names.append(name)

    result.categories = tab_names
    logger.info(f"[SPA_PW_WIX] Found {len(tab_names)} categories: {tab_names}")

    for i, tab in enumerate(tabs):
        cat_name = tab_names[i]
        await tab.click()
        await page.wait_for_timeout(1500)

        items = await page.query_selector_all('[data-hook="Grid-item"]')
        for item in items:
            svc = await _extract_wix_service_card(item, cat_name)
            if svc:
                result.services.append(svc)

        logger.info(f"[SPA_PW_WIX] {cat_name}: {len(items)} services")
    return result


async def _extract_wix_service_card(item, category: str) -> Optional[ExtractedService]:
    """Extract a single service from a Wix service card element."""
    try:
        title_el = await item.query_selector('[data-hook="service-info-title-text"]')
        if not title_el:
            return None
        name = (await title_el.inner_text()).strip()
        if not name:
            return None

        price = ""
        price_el = await item.query_selector('[data-hook="service-info-sr-only-price"]')
        if price_el:
            price = (await price_el.inner_text()).strip().replace("\xa0", " ")

        duration = ""
        detail_els = await item.query_selector_all('[data-hook="details-root"]')
        if detail_els:
            dur_text = (await detail_els[0].inner_text()).strip()
            if re.search(r'\d+\s*(hr|min|h)', dur_text, re.IGNORECASE):
                duration = dur_text

        # Extract description if available
        description = ""
        desc_el = await item.query_selector('[data-hook="service-info-description"]')
        if desc_el:
            description = (await desc_el.inner_text()).strip()[:500]
        if not description:
            tagline_el = await item.query_selector('[data-hook="service-info-tagline"]')
            if tagline_el:
                description = (await tagline_el.inner_text()).strip()[:500]

        # Extract booking URL from the card link
        booking_url = ""
        link_el = await item.query_selector('[data-hook="layout-image-link"]')
        if link_el:
            booking_url = await link_el.get_attribute('href') or ""
        if not booking_url:
            link_el = await item.query_selector('a[href*="booking"]')
            if link_el:
                booking_url = await link_el.get_attribute('href') or ""

        return ExtractedService(
            category=category, name=name, price=price, duration=duration,
            description=description, booking_url=booking_url,
        )
    except Exception as e:
        logger.debug(f"[SPA_PW_WIX] Card parse error: {e}")
        return None


async def _extract_generic_spa_services(page, booking_url: str) -> SPAServiceResult:
    """Generic SPA extraction: detect tabs/sections, click through them, extract services."""
    result = SPAServiceResult(source_url=booking_url, method="playwright-generic")

    # Common tab selectors across different platforms
    TAB_SELECTORS = [
        'nav a', 'nav button',
        '[role="tab"]', '[role="tablist"] button', '[role="tablist"] a',
        '.tabs button', '.tabs a', '.tab-list button', '.tab-list a',
        '.category-nav a', '.category-nav button',
        '.service-categories a', '.service-categories button',
        '.menu-categories a', '.menu-nav a',
        'ul.nav-tabs li a', 'ul.nav-pills li a',
    ]

    tabs = []
    for selector in TAB_SELECTORS:
        found = await page.query_selector_all(selector)
        if found and 2 <= len(found) <= 20:
            # Verify they're visible and look like category tabs
            visible_tabs = []
            for tab in found:
                if await tab.is_visible():
                    text = (await tab.inner_text()).strip()
                    if text and 2 < len(text) < 50:
                        visible_tabs.append(tab)
            if 2 <= len(visible_tabs) <= 20:
                tabs = visible_tabs
                logger.info(f"[SPA_PW_GENERIC] Found tabs via '{selector}': {len(tabs)}")
                break

    if not tabs:
        return result

    # Extract category names and click through
    for tab in tabs:
        cat_name = (await tab.inner_text()).strip()
        if not cat_name or len(cat_name) > 50:
            continue

        # Skip navigation-style links (Home, About, Contact, etc.)
        skip_words = {'home', 'about', 'contact', 'blog', 'faq', 'login', 'sign', 'cart', 'menu'}
        if cat_name.lower() in skip_words:
            continue

        result.categories.append(cat_name)
        try:
            await tab.click()
            await page.wait_for_timeout(1500)
        except Exception:
            continue

        # Extract services visible after clicking this tab
        services = await _scrape_visible_services(page, cat_name)
        result.services.extend(services)

    logger.info(f"[SPA_PW_GENERIC] Extracted {len(result.services)} services across {len(result.categories)} categories")
    return result


async def _scrape_visible_services(page, category: str) -> List[ExtractedService]:
    """Scrape service items from the currently visible page content."""
    services = []

    # Common service card/item selectors
    ITEM_SELECTORS = [
        '.service-item', '.service-card', '.menu-item', '.pricing-item',
        '.product-card', '.offer-card', '.treatment-card',
        '[class*="service"]', '[class*="Service"]',
        '[class*="treatment"]', '[class*="Treatment"]',
    ]

    items = []
    for selector in ITEM_SELECTORS:
        found = await page.query_selector_all(selector)
        if found and len(found) >= 2:
            items = found
            break

    # If no structured items found, try to extract from text content
    if not items:
        return services

    for item in items[:30]:
        try:
            text = (await item.inner_text()).strip()
            if not text or len(text) < 5:
                continue

            lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
            if not lines:
                continue

            name = lines[0][:80]
            price = ""
            duration = ""

            for line in lines[1:]:
                if not price and re.search(r'(?:AED|USD|EUR|GBP|\$|£|€)\s*[\d,]+|[\d,]+\s*(?:AED|USD|EUR|GBP)', line, re.IGNORECASE):
                    price = line.strip()
                if not duration and re.search(r'\d+\s*(hr|min|hour|minute)', line, re.IGNORECASE):
                    duration = line.strip()

            if name and len(name) > 2:
                services.append(ExtractedService(category=category, name=name, price=price, duration=duration))
        except Exception:
            continue

    return services


async def _extract_page_text_services(page, booking_url: str) -> SPAServiceResult:
    """Last resort: extract all visible text and parse for service patterns."""
    result = SPAServiceResult(source_url=booking_url, method="playwright-text")

    try:
        # Scroll through the page to trigger lazy loading
        await page.evaluate("""
            async () => {
                const delay = ms => new Promise(r => setTimeout(r, ms));
                for (let i = 0; i < 5; i++) {
                    window.scrollBy(0, window.innerHeight);
                    await delay(500);
                }
                window.scrollTo(0, 0);
            }
        """)
        await page.wait_for_timeout(1000)

        # Get full page text
        text = await page.evaluate('document.body.innerText')
        if not text or len(text) < 100:
            return result

        # Parse like Jina markdown
        lines = text.split('\n')
        services = _parse_generic_markdown(lines)
        result.services = services
        logger.info(f"[SPA_PW_TEXT] Extracted {len(services)} services from page text")
    except Exception as e:
        logger.warning(f"[SPA_PW_TEXT] Failed: {e}")

    return result


# ==================== STRATEGY 2: JINA READER (generic) ====================

async def _extract_via_jina(booking_url: str) -> SPAServiceResult:
    """Fetch rendered page via Jina Reader, parse markdown for services."""
    import httpx

    result = SPAServiceResult(source_url=booking_url, method="jina")

    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.get(
            f"https://r.jina.ai/{booking_url}",
            headers={"Accept": "application/json", "X-Return-Format": "markdown"}
        )
        if resp.status_code != 200:
            logger.warning(f"[SPA_JINA] HTTP {resp.status_code} for {booking_url}")
            return result

        content = resp.json().get('data', {}).get('content', '')
        if not content:
            return result

    logger.info(f"[SPA_JINA] Fetched {len(content)} chars for {booking_url}")

    # Extract categories from checkbox patterns: - [x] Category Name
    cat_pattern = re.compile(r'-\s*\[x\]\s*(.+)', re.IGNORECASE)
    categories = [m.group(1).strip() for m in cat_pattern.finditer(content)]
    if categories:
        result.categories = categories
        logger.info(f"[SPA_JINA] Found {len(categories)} categories: {categories}")

    # Parse services from markdown using multiple strategies
    services = _parse_services_from_markdown(content, categories)
    result.services = services
    logger.info(f"[SPA_JINA] Parsed {len(services)} services")
    return result


def _parse_services_from_markdown(content: str, categories: List[str]) -> List[ExtractedService]:
    """Parse service items from Jina markdown output.

    Handles common patterns:
    - Wix: Service name in link text, followed by duration + price lines
    - Generic: Heading + list items with prices
    - Table format: | Name | Price | Duration |
    """
    services = []
    lines = content.split('\n')

    # Strategy A: Wix-style markdown (link text + duration + price)
    services = _parse_wix_markdown(lines, categories)
    if services:
        return services

    # Strategy B: Generic heading + price patterns
    services = _parse_generic_markdown(lines)
    return services


def _parse_wix_markdown(lines: List[str], categories: List[str]) -> List[ExtractedService]:
    """Parse Wix booking markdown.
    Handles multiple formats:
    - [Service Name ---](booking-url) duration + price
    - [Service Name](any-url) duration + price
    - **Service Name** duration + price (no link)
    """
    services = []
    default_category = categories[0] if categories else "Services"
    current_category = default_category

    # Multiple link patterns (strict → lenient)
    link_patterns = [
        re.compile(r'\[([^\]]+?)\s*-{2,}\s*\]\(https?://[^)]*booking[^)]*\)'),
        re.compile(r'\[([^\]]+?)\s*-{2,}\s*\]\(https?://[^)]+\)'),
        re.compile(r'\[([^\]]{3,60})\]\(https?://[^)]+\)'),
    ]
    bold_pattern = re.compile(r'\*\*([^\*]{3,60})\*\*')
    price_pattern = re.compile(
        r'(?:AED|USD|EUR|GBP|SAR|INR)\s*[\d,]+(?:\.\d{2})?'
    )
    duration_pattern = re.compile(
        r'(\d+\s*hr?\s*(?:\d+\s*min)?|\d+\s*min)',
        re.IGNORECASE
    )
    # Detect category from checkbox or heading
    cat_heading_re = re.compile(r'^(?:#{1,4}\s+|\-\s*\[x\]\s*)(.+)', re.IGNORECASE)

    skip_words = {
        'book now', 'learn more', 'contact us', 'sign up', 'read more',
        'view all', 'see more', 'home', 'about', 'faq', 'privacy',
        'terms', 'log in', 'close', 'menu', 'search', 'book online',
    }

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check for category heading or checkbox
        cat_match = cat_heading_re.match(line)
        if cat_match:
            cat_text = cat_match.group(1).strip()
            if cat_text and cat_text in categories:
                current_category = cat_text
                i += 1
                continue

        # Try to find a service name via link or bold patterns
        name = None
        for pattern in link_patterns:
            match = pattern.search(line)
            if match:
                name = match.group(1).strip().rstrip('-').strip()
                break
        if not name:
            bold_match = bold_pattern.search(line)
            if bold_match:
                name = bold_match.group(1).strip()

        if name and len(name) > 2 and name.lower() not in skip_words:
            duration = ""
            price = ""

            search_window = line + " " + " ".join(ln.strip() for ln in lines[i+1:i+4])
            dur_match = duration_pattern.search(search_window)
            if dur_match:
                duration = dur_match.group(0).strip()

            price_match = price_pattern.search(search_window)
            if price_match:
                price = price_match.group(0).strip()

            services.append(ExtractedService(
                category=current_category,
                name=name,
                price=price,
                duration=duration,
            ))
        i += 1

    return services


def _parse_generic_markdown(lines: List[str]) -> List[ExtractedService]:
    """Parse generic service/product listings from markdown.

    Detects patterns like:
      ## Category
      - Service Name - $99
      - Service Name (1 hr) ... $150
    Or:
      **Service Name** ... $99/month
    """
    services = []
    current_category = "Services"
    price_re = re.compile(
        r'(?:AED|USD|EUR|GBP|SAR|INR|Rs\.?|₹|\$|£|€)\s*[\d,]+(?:\.\d{2})?'
        r'|[\d,]+(?:\.\d{2})?\s*(?:AED|USD|EUR|GBP|SAR|INR|dirhams?|dollars?|rupees?)',
        re.IGNORECASE
    )
    duration_re = re.compile(r'(\d+\s*(?:hr|min|hour|minute)s?)', re.IGNORECASE)
    heading_re = re.compile(r'^#{1,4}\s+(.+)')
    list_item_re = re.compile(r'^[\*\-]\s+(.+)')

    skip_words = {
        'book now', 'learn more', 'contact us', 'sign up', 'read more',
        'view all', 'see more', 'home', 'about', 'faq', 'privacy',
        'terms', 'log in', 'close', 'menu', 'search',
    }

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect category headings
        h_match = heading_re.match(line)
        if h_match:
            heading_text = h_match.group(1).strip()
            # Only use as category if it's not a page title
            if len(heading_text) < 60 and heading_text.lower() not in skip_words:
                current_category = heading_text
            continue

        # Look for lines with both a name-like text and a price
        price_match = price_re.search(line)
        if not price_match:
            continue

        # Get the name: text before the price, or from list item
        price_text = price_match.group(0)
        name_part = line[:price_match.start()].strip()

        # Clean up name from markdown artifacts
        list_match = list_item_re.match(name_part)
        if list_match:
            name_part = list_match.group(1)

        # Remove markdown formatting
        name_part = re.sub(r'[*_`\[\]]', '', name_part).strip()
        name_part = re.sub(r'\(https?://[^)]+\)', '', name_part).strip()
        name_part = name_part.rstrip('-').rstrip('|').strip()

        if not name_part or len(name_part) < 3 or name_part.lower() in skip_words:
            continue

        duration = ""
        dur_match = duration_re.search(line)
        if dur_match:
            duration = dur_match.group(0).strip()

        services.append(ExtractedService(
            category=current_category,
            name=name_part,
            price=price_text.strip(),
            duration=duration,
        ))

    return services


# ==================== PUBLIC API ====================

async def extract_spa_services(booking_url: str) -> SPAServiceResult:
    """Extract all services from a booking/services page.

    Tries Playwright first (Wix-specific tab clicking), falls back to
    Jina Reader (generic markdown parsing) if Playwright finds nothing.
    """
    # Strategy 1: Playwright (Wix tabs)
    try:
        pw_result = await _extract_via_playwright(booking_url)
        if pw_result.services:
            logger.info(f"[SPA_EXTRACT] Playwright: {len(pw_result.services)} services")
            return pw_result
        logger.info("[SPA_EXTRACT] Playwright found no services, trying Jina fallback")
    except Exception as e:
        logger.warning(f"[SPA_EXTRACT] Playwright failed: {e}, trying Jina fallback")

    # Strategy 2: Jina Reader (generic)
    try:
        jina_result = await _extract_via_jina(booking_url)
        if jina_result.services:
            logger.info(f"[SPA_EXTRACT] Jina: {len(jina_result.services)} services")
            return jina_result
        logger.info("[SPA_EXTRACT] Jina found no services either")
    except Exception as e:
        logger.warning(f"[SPA_EXTRACT] Jina fallback failed: {e}")

    return SPAServiceResult(source_url=booking_url, method="none")
