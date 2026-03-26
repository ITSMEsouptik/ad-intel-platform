"""
Novara Step 2: Channel Extraction
Extracts social media, messaging, and app store links from crawled pages

Channels include:
- Social: Instagram, TikTok, YouTube, Facebook, LinkedIn, Pinterest, X/Twitter
- Messaging: WhatsApp, Telegram
- Apps: Apple App Store, Google Play Store
- Other: Contact links, custom URLs
"""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)


# Platform detection patterns
SOCIAL_PLATFORMS = {
    'instagram': [
        r'instagram\.com/([a-zA-Z0-9_.]+)',
        r'instagr\.am/([a-zA-Z0-9_.]+)',
    ],
    'tiktok': [
        r'tiktok\.com/@?([a-zA-Z0-9_.]+)',
    ],
    'youtube': [
        r'youtube\.com/(?:user/|channel/|c/|@)([a-zA-Z0-9_-]+)',
        r'youtube\.com/([a-zA-Z0-9_-]+)(?:\?|$|/)',
    ],
    'facebook': [
        r'facebook\.com/([a-zA-Z0-9_.]+)',
        r'fb\.com/([a-zA-Z0-9_.]+)',
    ],
    'linkedin': [
        r'linkedin\.com/(?:company|in)/([a-zA-Z0-9_-]+)',
    ],
    'twitter': [
        r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)',
    ],
    'pinterest': [
        r'pinterest\.com/([a-zA-Z0-9_]+)',
    ],
    'snapchat': [
        r'snapchat\.com/add/([a-zA-Z0-9_.]+)',
    ],
}

MESSAGING_PLATFORMS = {
    'whatsapp': [
        r'wa\.me/(\d+)',
        r'api\.whatsapp\.com/send\?phone=(\d+)',
        r'whatsapp\.com/send\?phone=(\d+)',
        r'whatsapp://send\?phone=(\d+)',
    ],
    'telegram': [
        r't\.me/([a-zA-Z0-9_]+)',
        r'telegram\.me/([a-zA-Z0-9_]+)',
    ],
}

APP_STORE_PATTERNS = {
    'apple': [
        r'apps\.apple\.com/[a-z]{2}/app/[^/]+/id(\d+)',
        r'itunes\.apple\.com/[a-z]{2}/app/[^/]+/id(\d+)',
    ],
    'google': [
        r'play\.google\.com/store/apps/details\?id=([a-zA-Z0-9_.]+)',
    ],
}

# Skip these false positive usernames
SKIP_USERNAMES = {
    'share', 'sharer', 'intent', 'home', 'search', 'login', 'signup',
    'about', 'help', 'support', 'contact', 'terms', 'privacy', 'policy',
    'pages', 'groups', 'events', 'watch', 'hashtag', 'explore', 'settings',
    'p', 'reel', 'reels', 'stories', 'tv', 'live', 'status', 'download',
    'app', 'apps', 'store', 'web', 'mobile', 'official', 'follow',
    'user', 'channel', 'c', 'results', 'feed', 'playlist', 'embed',
    'tr', 'en', 'fr', 'de', 'es', 'it', 'ja', 'ko', 'pt', 'ru', 'zh',
}


def extract_channels(
    crawl_result: Any,  # CrawlResult from crawler
    raw_extraction: Dict
) -> Dict[str, List[Dict]]:
    """
    Extract all channels from crawled data.
    
    Returns:
        {
            "social": [{"platform": "instagram", "url": "...", "handle": "..."}],
            "messaging": [{"platform": "whatsapp", "url": "...", "handle": "..."}],
            "apps": [{"platform": "apple", "url": "..."}],
            "other": [{"label": "email", "url": "mailto:..."}]
        }
    """
    channels = {
        "social": [],
        "messaging": [],
        "apps": [],
        "other": []
    }
    
    seen_urls = set()
    
    # Collect all text and HTML to search
    all_text_sources = []
    
    # From crawler pages — prefer raw HTML (has nav/footer with social links)
    if hasattr(crawl_result, 'pages'):
        for page in crawl_result.pages:
            if hasattr(page, 'raw_html') and page.raw_html:
                all_text_sources.append(page.raw_html)
            elif hasattr(page, 'extracted_text_md'):
                all_text_sources.append(page.extracted_text_md)
    
    # From JSON-LD
    for jsonld in raw_extraction.get('structured_data_jsonld', []):
        all_text_sources.append(jsonld)
    
    all_text = '\n'.join(all_text_sources)
    
    # Extract social platforms
    for platform, patterns in SOCIAL_PLATFORMS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                handle = match.group(1).strip().rstrip('/')
                
                # Skip false positives
                if handle.lower() in SKIP_USERNAMES:
                    continue
                if len(handle) < 2 or len(handle) > 50:
                    continue
                
                # Build URL
                url = _build_social_url(platform, handle)
                
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    channels["social"].append({
                        "platform": platform,
                        "url": url,
                        "handle": handle
                    })
                    break  # Only first match per platform
    
    # Also check crawler's pre-extracted social links
    if hasattr(crawl_result, 'social_links'):
        for platform, url in crawl_result.social_links.items():
            if url and url not in seen_urls:
                handle = _extract_handle_from_url(url, platform)
                # Skip false positive handles
                if handle.lower() in SKIP_USERNAMES or len(handle) < 2:
                    continue
                seen_urls.add(url)
                channels["social"].append({
                    "platform": platform,
                    "url": url,
                    "handle": handle
                })
    
    # Extract messaging platforms
    for platform, patterns in MESSAGING_PLATFORMS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                identifier = match.group(1).strip()
                
                # Build URL
                if platform == 'whatsapp':
                    url = f"https://wa.me/{identifier}"
                elif platform == 'telegram':
                    url = f"https://t.me/{identifier}"
                else:
                    url = match.group(0)
                
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    channels["messaging"].append({
                        "platform": platform,
                        "url": url,
                        "handle": identifier
                    })
                    break
    
    # Also check for WhatsApp links in href attributes
    whatsapp_href_patterns = [
        r'href=["\']?(https?://wa\.me/\d+)["\']?',
        r'href=["\']?(https?://api\.whatsapp\.com/send[^"\'>\s]+)["\']?',
    ]
    for pattern in whatsapp_href_patterns:
        matches = re.finditer(pattern, all_text, re.IGNORECASE)
        for match in matches:
            url = match.group(1)
            if url not in seen_urls:
                seen_urls.add(url)
                # Extract phone number
                phone_match = re.search(r'(\d+)', url)
                handle = phone_match.group(1) if phone_match else ""
                channels["messaging"].append({
                    "platform": "whatsapp",
                    "url": url,
                    "handle": handle
                })
                break
    
    # Extract app store links
    for platform, patterns in APP_STORE_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                app_id = match.group(1).strip()
                
                # Build URL
                if platform == 'apple':
                    url = f"https://apps.apple.com/app/id{app_id}"
                elif platform == 'google':
                    url = f"https://play.google.com/store/apps/details?id={app_id}"
                else:
                    url = match.group(0)
                
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    channels["apps"].append({
                        "platform": platform,
                        "url": url
                    })
                    break
    
    # Extract JSON-LD sameAs links
    for jsonld_str in raw_extraction.get('structured_data_jsonld', []):
        try:
            import json
            jsonld = json.loads(jsonld_str) if isinstance(jsonld_str, str) else jsonld_str
            
            same_as = jsonld.get('sameAs', [])
            if isinstance(same_as, str):
                same_as = [same_as]
            
            for url in same_as:
                if url in seen_urls:
                    continue
                
                # Try to classify
                platform = _classify_url_platform(url)
                if platform:
                    seen_urls.add(url)
                    handle = _extract_handle_from_url(url, platform)
                    
                    if platform in SOCIAL_PLATFORMS:
                        # Check if we already have this platform
                        existing = [c for c in channels["social"] if c["platform"] == platform]
                        if not existing:
                            channels["social"].append({
                                "platform": platform,
                                "url": url,
                                "handle": handle
                            })
                    elif platform in MESSAGING_PLATFORMS:
                        existing = [c for c in channels["messaging"] if c["platform"] == platform]
                        if not existing:
                            channels["messaging"].append({
                                "platform": platform,
                                "url": url,
                                "handle": handle
                            })
        except Exception:
            pass
    
    # Add emails as "other" channels
    for email in raw_extraction.get('emails', [])[:3]:
        url = f"mailto:{email}"
        if url not in seen_urls:
            seen_urls.add(url)
            channels["other"].append({
                "label": "email",
                "url": url
            })
    
    # Add phones as "other" channels
    for phone in raw_extraction.get('phones', [])[:2]:
        # Clean phone number
        clean_phone = re.sub(r'[^\d+]', '', phone)
        url = f"tel:{clean_phone}"
        if url not in seen_urls:
            seen_urls.add(url)
            channels["other"].append({
                "label": "phone",
                "url": url
            })
    
    logger.info(f"[CHANNELS] Found {len(channels['social'])} social, {len(channels['messaging'])} messaging, {len(channels['apps'])} apps")
    
    return channels


def _build_social_url(platform: str, handle: str) -> str:
    """Build canonical URL for a social platform"""
    if platform == 'instagram':
        return f"https://instagram.com/{handle}"
    elif platform == 'tiktok':
        handle = handle.lstrip('@')
        return f"https://tiktok.com/@{handle}"
    elif platform == 'youtube':
        if handle.startswith('UC') or handle.startswith('HC'):  # Channel ID
            return f"https://youtube.com/channel/{handle}"
        return f"https://youtube.com/@{handle}"
    elif platform == 'facebook':
        return f"https://facebook.com/{handle}"
    elif platform == 'linkedin':
        return f"https://linkedin.com/company/{handle}"
    elif platform == 'twitter':
        return f"https://x.com/{handle}"
    elif platform == 'pinterest':
        return f"https://pinterest.com/{handle}"
    elif platform == 'snapchat':
        return f"https://snapchat.com/add/{handle}"
    return ""


def _extract_handle_from_url(url: str, platform: str) -> str:
    """Extract handle/username from a social URL"""
    try:
        # Try each pattern for the platform
        patterns = SOCIAL_PLATFORMS.get(platform, []) + MESSAGING_PLATFORMS.get(platform, [])
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip('/')
    except Exception:
        pass
    
    # Fallback: get last path segment
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if '/' in path:
            return path.split('/')[-1]
        return path
    except Exception:
        return ""


def _classify_url_platform(url: str) -> str:
    """Classify a URL to a platform type"""
    url_lower = url.lower()
    
    # Social platforms
    if 'instagram.com' in url_lower or 'instagr.am' in url_lower:
        return 'instagram'
    if 'tiktok.com' in url_lower:
        return 'tiktok'
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    if 'facebook.com' in url_lower or 'fb.com' in url_lower:
        return 'facebook'
    if 'linkedin.com' in url_lower:
        return 'linkedin'
    if 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    if 'pinterest.com' in url_lower:
        return 'pinterest'
    
    # Messaging
    if 'wa.me' in url_lower or 'whatsapp.com' in url_lower:
        return 'whatsapp'
    if 't.me' in url_lower or 'telegram.me' in url_lower:
        return 'telegram'
    
    # Apps
    if 'apps.apple.com' in url_lower or 'itunes.apple.com' in url_lower:
        return 'apple'
    if 'play.google.com' in url_lower:
        return 'google'
    
    return ""
