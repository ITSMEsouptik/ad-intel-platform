"""
Step 2 Pipeline — Website Context Extraction

Pure data-processing stage functions. No database access, no event firing.
Each stage takes explicit inputs and returns results, making them independently testable.

Orchestration (DB writes, events, error handling) stays in server.py.
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==================== STAGE 1: CRAWL ====================

async def stage_crawl(website_url: str):
    """Crawl the target website. Returns a CrawlResult object."""
    from crawler import WebCrawler

    crawler = WebCrawler()
    crawl_result = await crawler.crawl(website_url)
    logger.info(f"[PIPELINE] Crawl: {crawl_result.pages_fetched}/{crawl_result.pages_attempted} pages")

    if not crawl_result.pages:
        raise Exception("Failed to fetch any pages from website")

    return crawl_result


# ==================== STAGE 2: EXTRACT RAW ====================

def stage_extract_raw(crawl_result) -> dict:
    """Extract raw text, headings, prices, CTAs from crawled pages."""
    from extractor import extract_raw_for_step2

    raw = extract_raw_for_step2(crawl_result)
    logger.info(f"[PIPELINE] Raw extraction: {len(raw.get('text_chunks', []))} chunks, {len(raw.get('headings', []))} headings")
    return raw


async def stage_enrich_with_jina(raw_extraction: dict, crawl_result, website_url: str) -> dict:
    """When crawler gets minimal content (JS-heavy SPA), use Jina Reader to enrich.
    
    Only runs if the crawl returned very little text content (< 500 chars total).
    """
    total_text = sum(len(c) for c in raw_extraction.get('text_chunks', []))
    if total_text > 500 and crawl_result.pages_fetched > 1:
        return raw_extraction

    logger.info(f"[PIPELINE] Sparse crawl ({total_text} chars, {crawl_result.pages_fetched} pages) — enriching via Jina")

    try:
        jina_content = await _fetch_jina_content(website_url)
        if not jina_content or len(jina_content) < 100:
            return raw_extraction

        # Add Jina content as text chunks
        # Split into reasonable chunks (paragraphs)
        paragraphs = [p.strip() for p in jina_content.split('\n\n') if p.strip() and len(p.strip()) > 20]
        raw_extraction['text_chunks'].extend(paragraphs[:30])

        # Extract prices from Jina content
        import re
        price_patterns = [
            r'[\$€£₹]\s*[\d,]+(?:\.\d{2})?',
            r'(?:AED|USD|EUR|GBP)\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:AED|USD|EUR|GBP|dirhams?|dollars?)',
        ]
        for pattern in price_patterns:
            for match in re.finditer(pattern, jina_content, re.IGNORECASE):
                raw_extraction.setdefault('price_mentions', []).append({
                    'text': match.group(0),
                    'source_url': website_url
                })

        # Extract social links from Jina content
        socials = _extract_social_from_content(jina_content)
        if socials:
            raw_extraction['_jina_socials'] = socials

        logger.info(f"[PIPELINE] Jina enrichment: +{len(paragraphs)} chunks, total now {sum(len(c) for c in raw_extraction.get('text_chunks', []))} chars")
    except Exception as e:
        logger.warning(f"[PIPELINE] Jina enrichment failed: {e}")

    return raw_extraction


# ==================== STAGE 2B: SPA SERVICE EXTRACTION ====================

async def stage_extract_spa_services(crawl_result, raw_extraction: dict) -> Optional[dict]:
    """Detect a booking/services page and extract all services.

    Tries Playwright (Wix tabs) first, then Jina Reader as fallback.
    Returns None if no booking page found or no services extracted.
    Mutates raw_extraction in place (adds text chunks and price mentions).
    """
    from spa_service_extractor import extract_spa_services, _find_booking_url

    booking_url = _find_booking_url(crawl_result.pages, crawl_result.all_links_found)
    if not booking_url:
        logger.info("[PIPELINE] No booking/services page detected")
        return None

    logger.info(f"[PIPELINE] SPA extraction from {booking_url}")
    result = await extract_spa_services(booking_url)

    if not result.services:
        logger.info("[PIPELINE] SPA extraction found no services")
        return None

    # Enrich raw_extraction for downstream LLM
    svc_text = result.to_text_block()
    raw_extraction['text_chunks'].insert(0, svc_text)

    # Add SPA prices to price_mentions for pricing stats
    for svc in result.services:
        if svc.price:
            raw_extraction.setdefault('price_mentions', []).append({
                'text': svc.price,
                'source_url': booking_url
            })

    logger.info(f"[PIPELINE] SPA: {len(result.services)} services, {len(result.categories)} categories, method={result.method}")
    return {
        "result": result,
        "booking_url": booking_url,
        "services_count": len(result.services),
        "categories": result.categories,
        "method": result.method,
    }


# ==================== STAGE 3: BRAND IDENTITY ====================

def stage_extract_brand_identity(crawl_result) -> dict:
    """Extract fonts and colors from crawled CSS and HTML."""
    from brand_identity import extract_brand_identity

    all_html = '\n'.join(p.raw_html for p in crawl_result.pages if p.raw_html)
    if not all_html:
        all_html = '\n'.join(p.extracted_text_md for p in crawl_result.pages)

    identity = extract_brand_identity(
        crawl_result.css_texts, all_html,
        html_colors=[c for p in crawl_result.pages for c in getattr(p, 'html_colors', [])]
    )
    logger.info(f"[PIPELINE] Identity: {len(identity.get('fonts', []))} fonts, {len(identity.get('colors', []))} colors")
    return identity


# ==================== STAGE 4: ASSETS ====================

def stage_extract_assets(crawl_result) -> dict:
    """Extract and rank image assets, detect logo."""
    from assets import extract_assets

    pages_data = [
        {
            'url': p.url,
            'page_type': p.page_type,
            'extracted_text_md': p.extracted_text_md,
            'asset_urls_found': p.asset_urls_found,
            'og_image': p.og_image
        }
        for p in crawl_result.pages
    ]
    result = extract_assets(pages_data, crawl_result.domain)
    logger.info(f"[PIPELINE] Assets: {len(result.get('image_assets', []))} images, logo: {result.get('logo', {}).get('url', 'none')[:50]}")
    return result


# ==================== STAGE 5: PRICING ====================

def stage_parse_pricing(raw_extraction: dict) -> dict:
    """Parse and analyze pricing data from raw extraction."""
    from pricing import parse_pricing_with_sources

    result = parse_pricing_with_sources(
        raw_extraction.get('price_mentions', []),
        '\n'.join(raw_extraction.get('text_chunks', []))
    )
    logger.info(f"[PIPELINE] Pricing: {result.get('count', 0)} values, {result.get('currency', 'unknown')}")
    return result


# ==================== STAGE 5B: CHANNELS ====================

async def stage_extract_channels(crawl_result, raw_extraction: dict, website_url: str) -> dict:
    """Extract social media and messaging channels.

    Falls back to Jina Reader and then Perplexity if crawler found nothing.
    """
    from channels import extract_channels

    channels = extract_channels(crawl_result, raw_extraction)
    logger.info(f"[PIPELINE] Channels: {len(channels.get('social', []))} social, {len(channels.get('messaging', []))} messaging")

    domain = crawl_result.domain or ''
    brand_name = raw_extraction.get('site', {}).get('title', '')

    # Fallback chain if no social channels found
    if not channels.get('social'):
        channels['social'] = await _social_channel_fallback(
            website_url, domain, brand_name
        )
    elif len({c['platform'] for c in channels.get('social', [])}) < 3:
        # Augment sparse results
        await _augment_social_channels(channels, website_url, domain, brand_name)

    # Deduplicate social channels by platform (keep first occurrence)
    seen_platforms = set()
    deduped = []
    for ch in channels.get('social', []):
        if ch['platform'] not in seen_platforms:
            seen_platforms.add(ch['platform'])
            deduped.append(ch)
    channels['social'] = deduped

    return channels


async def _social_channel_fallback(website_url: str, domain: str, brand_name: str) -> list:
    """Try Jina AND Perplexity to find social channels, merge results."""
    all_socials = []
    seen_platforms = set()

    # Attempt 1: Jina Reader
    try:
        jina_content = await _fetch_jina_content(website_url)
        if jina_content:
            jina_socials = _extract_social_from_content(jina_content)
            for s in jina_socials:
                if s['platform'] not in seen_platforms:
                    all_socials.append(s)
                    seen_platforms.add(s['platform'])
            if jina_socials:
                logger.info(f"[PIPELINE] Jina social fallback: {len(jina_socials)} channels")
    except Exception as e:
        logger.warning(f"[PIPELINE] Jina social fallback failed: {e}")

    # Attempt 2: Perplexity (always try if fewer than 4 platforms)
    if len(seen_platforms) < 4:
        try:
            pplx_socials = await _discover_social_via_perplexity(website_url, domain, brand_name)
            for s in pplx_socials:
                if s['platform'] not in seen_platforms:
                    all_socials.append(s)
                    seen_platforms.add(s['platform'])
            if pplx_socials:
                logger.info(f"[PIPELINE] Perplexity social fallback: +{len(pplx_socials)} channels (total={len(all_socials)})")
        except Exception as e:
            logger.warning(f"[PIPELINE] Perplexity social fallback failed: {e}")

    return all_socials


async def _augment_social_channels(channels: dict, website_url: str, domain: str = "", brand_name: str = ""):
    """Try to fill gaps if fewer than 3 platforms found. Uses Jina + Perplexity."""
    existing = {c['platform'] for c in channels.get('social', [])}

    # Try Jina first
    try:
        jina_content = await _fetch_jina_content(website_url)
        if jina_content:
            extras = _extract_social_from_content(jina_content)
            for social in extras:
                if social['platform'] not in existing:
                    channels['social'].append(social)
                    existing.add(social['platform'])
                    logger.info(f"[PIPELINE] Jina augmented: +{social['platform']}")
    except Exception as e:
        logger.warning(f"[PIPELINE] Jina augmentation failed: {e}")

    # Also try Perplexity if still sparse
    if len(existing) < 4 and (domain or brand_name):
        try:
            pplx_socials = await _discover_social_via_perplexity(website_url, domain, brand_name)
            for social in pplx_socials:
                if social['platform'] not in existing:
                    channels['social'].append(social)
                    existing.add(social['platform'])
                    logger.info(f"[PIPELINE] Perplexity augmented: +{social['platform']}")
        except Exception as e:
            logger.warning(f"[PIPELINE] Perplexity augmentation failed: {e}")


# ==================== STAGE 6: LLM SUMMARIZATION ====================

async def stage_llm_summarize(raw_extraction: dict, pricing: dict) -> Tuple[Optional[dict], Optional[dict]]:
    """Run LLM summarization on extracted data.

    Returns (llm_output, llm_metadata) — both None if summarization fails.
    """
    from gemini_site_summarizer import summarize_website_context
    from postprocess import postprocess_step2_output

    try:
        llm_result = await summarize_website_context(
            raw_extraction=raw_extraction,
            pricing=pricing
        )
        if llm_result.get('status') == 'success':
            output = postprocess_step2_output(llm_result.get('llm_output', {}))
            metadata = llm_result.get('metadata', {})
            logger.info(f"[PIPELINE] LLM done in {metadata.get('response_duration_seconds', 0)}s")
            return output, metadata
        else:
            logger.warning("[PIPELINE] LLM returned non-success status")
    except Exception as e:
        logger.warning(f"[PIPELINE] LLM failed (non-fatal): {e}")

    return None, None


# ==================== STAGE 7: BUILD OUTPUT ====================

def stage_build_output(
    website_url: str,
    crawl_result,
    raw_extraction: dict,
    brand_identity: dict,
    assets: dict,
    pricing: dict,
    channels: dict,
    llm_output: Optional[dict],
    llm_metadata: Optional[dict],
    spa_services: Optional[dict],
) -> Tuple[dict, dict, int, str]:
    """Assemble the final step2 (public) and step2_internal (debug) dicts.

    Returns (step2_data, step2_internal, confidence_score, status).
    """
    site_info = raw_extraction.get('site', {})
    domain = crawl_result.domain or site_info.get('final_url', '').split('//')[-1].split('/')[0]
    logo_info = assets.get('logo', {})
    logo_url = logo_info.get('url', '') if logo_info.get('url') != 'unknown' else ''

    # Determine offer_catalog source
    spa_result = spa_services.get("result") if spa_services else None
    if spa_result and spa_result.services:
        offer_catalog = spa_result.to_offer_catalog()[:40]
        grouped_catalog = spa_result.to_grouped_catalog()
    else:
        # LLM catalog — normalize to new schema
        raw_catalog = llm_output.get('offer', {}).get('offer_catalog', [])[:20] if llm_output else []
        offer_catalog = _normalize_llm_catalog(raw_catalog)
        grouped_catalog = _group_catalog(offer_catalog)

    # Build contact section from channels
    contact = _extract_contact(channels, raw_extraction)

    # Deduplicate assets
    deduped_assets = _deduplicate_assets(assets.get('image_assets', []))

    step2_data = {
        "site": {
            "input_url": website_url,
            "final_url": site_info.get('final_url', website_url),
            "domain": domain,
            "title": site_info.get('title', 'unknown'),
            "meta_description": site_info.get('meta_description', 'unknown'),
            "language": site_info.get('language', 'en')
        },
        "classification": _safe_llm(llm_output, 'classification', {
            "industry": "unknown", "subcategory": "unknown", "niche": "unknown", "tags": []
        }),
        "brand_summary": {
            "name": _llm_val(llm_output, ['brand_summary', 'name']) or site_info.get('title') or 'unknown',
            "tagline": _llm_val(llm_output, ['brand_summary', 'tagline']) or 'unknown',
            "one_liner": _llm_val(llm_output, ['brand_summary', 'one_liner']) or site_info.get('meta_description') or 'unknown',
            "bullets": (llm_output.get('brand_summary', {}).get('bullets', []) if llm_output else []),
        },
        "brand_dna": llm_output.get('brand_dna', {
            "values": [], "tone_of_voice": [], "aesthetic": [], "visual_vibe": []
        }) if llm_output else {"values": [], "tone_of_voice": [], "aesthetic": [], "visual_vibe": []},
        "identity": {
            "logo": {
                "primary_url": logo_url,
                "type": logo_info.get('type', 'logo'),
                "width": logo_info.get('width', 0),
                "height": logo_info.get('height', 0),
            },
            "colors": brand_identity.get('colors', [])[:6],
            "fonts": _clean_font_list(brand_identity.get('fonts', []))
        },
        "offer": {
            "value_prop": _llm_val(llm_output, ['offer', 'value_prop']) or 'unknown',
            "key_benefits": (llm_output.get('offer', {}).get('key_benefits', [])[:5] if llm_output else []),
            "offer_catalog": offer_catalog,
            "grouped_catalog": grouped_catalog,
        },
        "pricing": {
            "currency": pricing.get('currency', 'unknown'),
            "count": pricing.get('count', 0),
            "min": pricing.get('min', 0),
            "avg": pricing.get('avg', 0),
            "max": pricing.get('max', 0),
            "observed_prices": pricing.get('observed_prices', [])[:50]
        },
        "contact": contact,
        "conversion": {
            "primary_action": _llm_val(llm_output, ['conversion', 'primary_action']) or 'unknown',
            "ctas": raw_extraction.get('ctas', [])[:10],
            "destination_type": _llm_val(llm_output, ['conversion', 'destination_type']) or 'unknown',
        },
        "channels": channels,
        "assets": {
            "image_assets": [
                {
                    "url": a.get('url', ''),
                    "kind": a.get('kind', 'unknown'),
                    "score_0_100": a.get('score_0_100', 50),
                    "alt": a.get('alt', ''),
                    "width": a.get('width', 0),
                    "height": a.get('height', 0)
                }
                for a in deduped_assets[:100]
            ]
        }
    }

    step2_internal = {
        "analysis_quality": {
            "confidence_score_0_100": 75 if llm_output else 50,
            "warnings": crawl_result.errors,
            "missing_fields": []
        },
        "extraction_stats": {
            "pages_crawled": crawl_result.pages_fetched,
            "css_files_fetched": len(crawl_result.css_texts),
            "css_fetch_failures": 0,
            "assets_found": len(raw_extraction.get('images', [])),
            "assets_after_dedup": len(assets.get('image_assets', [])),
            "prices_found": pricing.get('count', 0),
            "channels_found": len(channels.get('social', [])) + len(channels.get('messaging', [])),
            "spa_extraction_method": spa_services.get("method", "none") if spa_services else "none",
            "spa_services_count": spa_services.get("services_count", 0) if spa_services else 0,
        },
        "raw_extraction": {
            "pages_crawled": crawl_result.pages_fetched,
            "text_chunks": raw_extraction.get('text_chunks', [])[:30],
            "headings": raw_extraction.get('headings', [])[:20],
            "raw_css_fonts": raw_extraction.get('css_font_families', []),
            "raw_css_colors": raw_extraction.get('css_colors', []),
            "structured_data_jsonld": raw_extraction.get('structured_data_jsonld', [])[:5]
        },
        "llm_call": {
            "model": llm_metadata.get('model', '') if llm_metadata else '',
            "input_tokens": llm_metadata.get('input_tokens', 0) if llm_metadata else 0,
            "output_tokens": llm_metadata.get('output_tokens', 0) if llm_metadata else 0,
            "total_cost": llm_metadata.get('total_cost', 0) if llm_metadata else 0,
            "attempt": llm_metadata.get('attempt', 1) if llm_metadata else 1,
        }
    }

    # Confidence scoring
    confidence = 50
    if llm_output:
        confidence += 20
    if logo_url:
        confidence += 10
    if brand_identity.get('colors'):
        confidence += 5
    if brand_identity.get('fonts'):
        confidence += 5
    if len(step2_data['brand_summary']['bullets']) >= 2:
        confidence += 10
    if pricing.get('count', 0) > 0:
        confidence += 5
    if channels.get('social'):
        confidence += 5
    confidence = min(100, confidence)

    step2_internal['analysis_quality']['confidence_score_0_100'] = confidence

    # Determine status
    if crawl_result.errors and crawl_result.pages_fetched == 0:
        status = 'failed'
    elif confidence >= 70:
        status = 'success'
    elif confidence >= 50:
        status = 'partial'
    else:
        status = 'needs_review'

    logger.info(f"[PIPELINE] Output: confidence={confidence}, status={status}")
    return step2_data, step2_internal, confidence, status


# ==================== DATA QUALITY HELPERS ====================

def _normalize_llm_catalog(raw_catalog: list) -> list:
    """Normalize LLM-generated offer_catalog to the new schema."""
    import re
    result = []
    for item in raw_catalog:
        price_display = item.get('price_hint', '') or item.get('price_display', '') or ''
        price_numeric = None
        currency = ''
        if price_display:
            num_match = re.search(r'([\d,]+(?:\.\d{2})?)', price_display)
            if num_match:
                try:
                    price_numeric = float(num_match.group(1).replace(',', ''))
                except ValueError:
                    pass
            pl = price_display.lower()
            if 'aed' in pl or 'dirham' in pl:
                currency = 'AED'
            elif '$' in price_display or 'usd' in pl:
                currency = 'USD'
            elif '€' in price_display or 'eur' in pl:
                currency = 'EUR'
            elif '£' in price_display or 'gbp' in pl:
                currency = 'GBP'

        result.append({
            "name": item.get('name', ''),
            "category": item.get('category', '') or item.get('description', '') or 'General',
            "price_display": price_display,
            "price_numeric": price_numeric,
            "currency": currency,
            "duration": item.get('duration', ''),
        })
    return result


def _group_catalog(catalog: list) -> list:
    """Group a flat catalog into per-category arrays with stats."""
    from collections import defaultdict
    groups = defaultdict(list)
    for item in catalog:
        cat = item.get('category', 'General')
        groups[cat].append(item)

    result = []
    for cat, items in groups.items():
        prices = [i['price_numeric'] for i in items if i.get('price_numeric')]
        result.append({
            "category": cat,
            "count": len(items),
            "price_range": {
                "min": min(prices) if prices else None,
                "max": max(prices) if prices else None,
            },
            "services": [
                {"name": i['name'], "price_display": i.get('price_display', ''), "duration": i.get('duration', '')}
                for i in items
            ]
        })
    return result


def _extract_contact(channels: dict, raw_extraction: dict) -> dict:
    """Build a clean contact section from channels and raw extraction."""
    import re

    contact = {"emails": [], "phones": [], "address": ""}
    seen_emails = set()
    seen_phones = set()

    def _clean_email(raw_email: str) -> str:
        """Fix emails with text concatenated to TLD (e.g., 'info@brand.coWHAT' → 'info@brand.co')."""
        m = re.match(r'^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.)([a-zA-Z]+)$', raw_email)
        if not m:
            return ''
        prefix = m.group(1)
        tld_raw = m.group(2)

        # Known valid TLDs (covers 99% of business sites)
        valid_tlds = {'com', 'co', 'net', 'org', 'io', 'ai', 'us', 'uk', 'ae', 'in',
                      'ca', 'au', 'de', 'fr', 'it', 'es', 'nl', 'se', 'no', 'dk',
                      'sg', 'hk', 'jp', 'kr', 'ru', 'br', 'za', 'nz', 'ie', 'ch',
                      'info', 'biz', 'edu', 'gov', 'pro', 'app', 'dev', 'xyz'}

        tld_lower = tld_raw.lower()
        # Exact match
        if tld_lower in valid_tlds:
            return (prefix + tld_lower).lower()

        # Try to find valid TLD at the start (handles "coWHAT" → "co", "comGeneral" → "com")
        for valid in sorted(valid_tlds, key=len, reverse=True):
            if tld_lower.startswith(valid) and len(tld_lower) > len(valid):
                return (prefix + valid).lower()

        # If short and all lowercase, accept as-is
        if tld_lower == tld_raw and 2 <= len(tld_raw) <= 3:
            return raw_email.lower()
        return ''

    # Collect all raw emails from every source
    all_raw_emails = list(raw_extraction.get('emails', []))
    for item in channels.get('other', []):
        item_str = str(item) if not isinstance(item, str) else item
        all_raw_emails.extend(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', item_str))

    for raw_email in all_raw_emails:
        clean = _clean_email(raw_email.strip())
        if clean and clean not in seen_emails and not any(x in clean for x in ['example', 'test', 'sentry', 'wix']):
            seen_emails.add(clean)
            contact['emails'].append(clean)

    # Collect phones
    for phone in raw_extraction.get('phones', []):
        p = phone.strip()
        if p and p not in seen_phones:
            seen_phones.add(p)
            contact['phones'].append(p)

    for item in channels.get('other', []):
        item_str = str(item) if not isinstance(item, str) else item
        phone_match = re.search(r'[\+]?[\d\s\-\(\)]{8,}', item_str)
        if phone_match:
            p = phone_match.group(0).strip()
            digits = re.sub(r'\D', '', p)
            if 7 <= len(digits) <= 15 and p not in seen_phones:
                seen_phones.add(p)
                contact['phones'].append(p)

    contact['emails'] = contact['emails'][:3]
    contact['phones'] = contact['phones'][:3]
    return contact



def _clean_font_list(raw_fonts: list) -> list:
    """Filter system/utility fonts, platform fonts, and format for output."""
    SYSTEM_FONTS = {
        'ui-monospace', 'ui monospace', 'sfmono-regular', 'sfmono regular',
        'sf mono', 'menlo', 'consolas', 'liberation mono', 'courier new',
        'monospace', 'sans-serif', 'serif', 'system-ui', '-apple-system',
        'blinkmacsystemfont', 'segoe ui', 'arial', 'helvetica',
        'helvetica neue', 'courier', 'monaco', 'lucida console',
        'lucida sans', 'lucida sans regular', 'lucida sans unicode',
        'lucida grande', 'georgia', 'times new roman', 'times',
        'trebuchet ms', 'verdana', 'tahoma', 'impact', 'comic sans ms',
        # Google platform fonts (injected by tracking scripts / Chrome)
        'google sans', 'google sans text', 'google sans display',
        'product sans', 'roboto', 'roboto slab', 'roboto mono',
        'noto sans', 'noto serif',
        # Other platform/tracking fonts
        'font awesome', 'fontawesome', 'material icons', 'material symbols',
        'icomoon', 'glyphicons',
    }
    # CSS keywords/artifacts that sometimes leak into font names
    CSS_ARTIFACT_WORDS = {'inherit', 'initial', 'unset', 'revert', 'fallback', 'var(', 'calc(', '!important'}

    result = []
    seen = set()
    for f in raw_fonts:
        name = f.get('name', f.name if hasattr(f, 'name') else '')
        if not name:
            continue
        name_lower = name.lower().strip()
        # Filter system fonts
        if name_lower in SYSTEM_FONTS:
            continue
        # Filter CSS artifacts (names containing CSS keywords or unbalanced parens)
        if any(kw in name_lower for kw in CSS_ARTIFACT_WORDS):
            continue
        if ')' in name and '(' not in name:
            continue
        # Filter names that are just numbers, single chars, or too short
        if len(name_lower.replace('-', '').replace('_', '')) < 3:
            continue
        # Filter "X Fallback" pattern (CSS generated fallback names)
        if name_lower.endswith(' fallback') or name_lower.endswith('-fallback'):
            continue
        if name_lower in seen:
            continue
        seen.add(name_lower)
        result.append({
            "family": name,
            "role": f.get('role', f.role if hasattr(f, 'role') else 'unknown'),
            "source": f.get('source', f.source if hasattr(f, 'source') else 'css'),
        })
    return result[:6]


def _deduplicate_assets(image_assets: list) -> list:
    """Remove duplicate images (same base image at different crop/resize).

    Wix images share the same image ID in URL: /v1/fill/w_XXX,h_YYY,.../IMAGE_ID.ext
    """
    import re

    seen_ids = set()
    deduped = []

    for asset in image_assets:
        url = asset.get('url', '')

        # Extract Wix image ID (hash before extension)
        wix_match = re.search(r'/([a-f0-9]{6,}_[a-f0-9]+)\.\w+', url)
        if wix_match:
            img_id = wix_match.group(1)
            if img_id in seen_ids:
                continue
            seen_ids.add(img_id)

        # Generic dedup: strip size params
        base_url = re.sub(r'[?&](w|h|width|height|size|resize|crop)=[^&]*', '', url)
        base_url = re.sub(r'/w_\d+,h_\d+[^/]*/', '/', base_url)
        if base_url in seen_ids:
            continue
        seen_ids.add(base_url)

        deduped.append(asset)

    return deduped

async def _fetch_jina_content(url: str) -> str:
    """Fetch rendered page content via Jina Reader API."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"https://r.jina.ai/{url}",
                headers={"Accept": "application/json", "X-Return-Format": "markdown"}
            )
            if resp.status_code == 200:
                content = resp.json().get('data', {}).get('content', '')
                logger.info(f"[JINA] Fetched {len(content)} chars for {url}")
                return content
    except Exception as e:
        logger.warning(f"[JINA] Failed to fetch {url}: {e}")
    return ""


def _extract_social_from_content(content: str) -> list:
    """Extract social media profiles from rendered page content."""
    import re

    profiles = []
    seen = set()

    platform_patterns = {
        'instagram': (r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?', 'https://instagram.com/{}'),
        'facebook': (r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9_.]+)/?', 'https://facebook.com/{}'),
        'tiktok': (r'https?://(?:www\.)?tiktok\.com/@?([a-zA-Z0-9_.]+)/?', 'https://tiktok.com/@{}'),
        'linkedin': (r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([a-zA-Z0-9_.-]+)/?', 'https://linkedin.com/company/{}'),
        'youtube': (r'https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)?([a-zA-Z0-9_-]+)/?', 'https://youtube.com/@{}'),
        'twitter': (r'https?://(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)/?', 'https://x.com/{}'),
    }

    skip_handles = {
        'share', 'sharer', 'intent', 'home', 'search', 'login', 'signup',
        'about', 'help', 'support', 'contact', 'terms', 'privacy', 'policy',
        'pages', 'groups', 'events', 'watch', 'hashtag', 'explore', 'settings',
        'p', 'reel', 'reels', 'stories', 'tv', 'live', 'status', 'download',
        'user', 'channel', 'c', 'results', 'feed', 'playlist', 'embed',
        'app', 'apps', 'store', 'web', 'mobile', 'official', 'follow',
        'tr', 'en', 'fr', 'de', 'es', 'it', 'ja', 'ko', 'pt', 'ru', 'zh',
    }

    for platform, (pattern, url_template) in platform_patterns.items():
        if platform in seen:
            continue
        for match in re.finditer(pattern, content, re.IGNORECASE):
            handle = match.group(1).strip().rstrip('/')
            if handle.lower() in skip_handles or len(handle) < 2 or len(handle) > 50:
                continue
            seen.add(platform)
            profiles.append({
                "platform": platform,
                "url": url_template.format(handle.lstrip('@')),
                "handle": handle.lstrip('@')
            })
            break

    return profiles


async def _discover_social_via_perplexity(website_url: str, domain: str, brand_name: str) -> list:
    """Use Perplexity to find social media profiles."""
    import httpx
    import os
    import re

    api_key = os.environ.get('PERPLEXITY_API_KEY')
    if not api_key:
        return []

    clean_name = brand_name.split('|')[0].split('-')[0].strip() if brand_name else domain

    prompt = f"""What are the official social media profiles for {clean_name} ({website_url})?

Please list each platform with its full URL. I need Instagram, Facebook, TikTok, LinkedIn, YouTube, and Twitter/X profiles if they exist. Only include profiles that actually belong to this business."""

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "You are a research assistant. Provide factual social media profile URLs for businesses."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.1
                }
            )
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content']
            logger.info(f"[SOCIAL_FALLBACK] Perplexity response: {content[:300]}")

            profiles = []
            patterns = {
                'instagram': r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)',
                'facebook': r'https?://(?:www\.)?facebook\.com/([a-zA-Z0-9_.]+)',
                'tiktok': r'https?://(?:www\.)?tiktok\.com/@?([a-zA-Z0-9_.]+)',
                'linkedin': r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([a-zA-Z0-9_.-]+)',
                'youtube': r'https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)?([a-zA-Z0-9_-]+)',
                'twitter': r'https?://(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
            }
            skip = {'share', 'sharer', 'intent', 'home', 'search', 'login', 'signup', 'about', 'help', 'explore'}

            for platform, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    handle = match.group(1).strip().rstrip('/')
                    if handle.lower() not in skip and len(handle) >= 2:
                        profiles.append({"platform": platform, "url": match.group(0).rstrip('/'), "handle": handle})

            return profiles
    except Exception as e:
        logger.warning(f"[SOCIAL_FALLBACK] Perplexity failed: {e}")
    return []


def _safe_llm(llm_output: Optional[dict], key: str, defaults: dict) -> dict:
    """Safely extract nested LLM output with defaults."""
    if not llm_output:
        return defaults
    section = llm_output.get(key, {})
    result = {}
    for k, default_val in defaults.items():
        val = section.get(k, default_val)
        # Handle sub_industry -> subcategory alias
        if k == 'subcategory' and val == default_val:
            val = section.get('sub_industry', default_val)
        result[k] = val
    return result


def _llm_val(llm_output: Optional[dict], keys: list) -> str:
    """Extract a nested value from LLM output, returning '' if missing."""
    if not llm_output:
        return ''
    current = llm_output
    for key in keys:
        if not isinstance(current, dict):
            return ''
        current = current.get(key, '')
    return current or ''
