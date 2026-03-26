"""
Novara Ads Intelligence: Post-processing
Hard guards: drop invalid ads, dedup, clamp text, platform filter.
Handles actual Foreplay API response format.
"""

import hashlib
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ALLOWED_PLATFORMS = {"facebook", "instagram", "tiktok"}
MAX_TEXT_LENGTH = 500
MAX_HEADLINE_LENGTH = 200


def normalize_platform(raw) -> str:
    """Normalize platform names. Foreplay returns arrays like ['facebook', 'instagram']."""
    if isinstance(raw, list):
        # Pick first platform that's in our allowed set
        for p in raw:
            normalized = normalize_platform(p)
            if normalized in ALLOWED_PLATFORMS:
                return normalized
        # If none match, return first
        return normalize_platform(raw[0]) if raw else ""
    if not raw:
        return ""
    p = str(raw).lower().strip()
    if p in ("fb", "facebook"):
        return "facebook"
    if p in ("ig", "instagram"):
        return "instagram"
    if p in ("tt", "tiktok"):
        return "tiktok"
    if p in ("audience_network", "messenger", "threads"):
        return "facebook"  # Meta family → facebook
    return p


def compute_running_days_from_duration(duration_obj) -> int:
    """Compute total running days from Foreplay's running_duration object."""
    if not duration_obj or not isinstance(duration_obj, dict):
        return 0
    days = duration_obj.get("days", 0) or 0
    hours = duration_obj.get("hours", 0) or 0
    minutes = duration_obj.get("minutes", 0) or 0
    seconds = duration_obj.get("seconds", 0) or 0
    # Convert everything to days (approximate)
    total_days = days + (hours / 24) + (minutes / 1440) + (seconds / 86400)
    return max(0, int(total_days))


def timestamp_to_isodate(ts) -> str:
    """Convert Foreplay millisecond timestamp to ISO date string."""
    if not ts:
        return ""
    try:
        if isinstance(ts, (int, float)):
            # Foreplay uses millisecond timestamps
            if ts > 1e12:
                ts = ts / 1000
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.isoformat()
        return str(ts)
    except Exception:
        return ""


def text_hash(text: str) -> str:
    if not text:
        return ""
    return hashlib.md5(text.strip().lower().encode()).hexdigest()[:12]


def postprocess_ads(ads: List[Dict[str, Any]], lens: str) -> List[Dict[str, Any]]:
    """
    Apply hard guards and dedup to a list of raw Foreplay ad dicts.
    Handles actual Foreplay API response format.
    """
    cleaned = []
    seen_ad_ids = set()
    seen_fingerprints = set()
    dropped = {"no_id": 0, "no_content": 0, "bad_platform": 0, "duplicate": 0}

    for ad in ads:
        # Foreplay uses 'id' as the internal ID, 'ad_id' as the ad library ID
        ad_id = str(ad.get("id", ad.get("ad_id", ""))).strip()
        if not ad_id:
            dropped["no_id"] += 1
            continue

        # Must have at least media OR text
        media = ad.get("image") or ad.get("video") or ad.get("thumbnail") or ad.get("media_url")
        body = ad.get("description") or ad.get("text") or ad.get("body") or ""
        headline = ad.get("headline") or ad.get("name") or ""
        if not media and not body and not headline:
            dropped["no_content"] += 1
            continue

        # Platform filter - Foreplay returns publisher_platform as array
        raw_platform = ad.get("publisher_platform") or ad.get("platform") or []
        platform = normalize_platform(raw_platform)
        if platform and platform not in ALLOWED_PLATFORMS:
            dropped["bad_platform"] += 1
            continue

        # Dedup by ad_id
        if ad_id in seen_ad_ids:
            dropped["duplicate"] += 1
            continue
        seen_ad_ids.add(ad_id)

        # Dedup by (brand_id, media, text_hash)
        brand_id = str(ad.get("brand_id") or "")
        fingerprint = f"{brand_id}|{media or ''}|{text_hash(body)}"
        if fingerprint in seen_fingerprints:
            dropped["duplicate"] += 1
            continue
        seen_fingerprints.add(fingerprint)

        # Clamp text
        if body and len(body) > MAX_TEXT_LENGTH:
            body = body[:MAX_TEXT_LENGTH] + "..."
        if headline and len(headline) > MAX_HEADLINE_LENGTH:
            headline = headline[:MAX_HEADLINE_LENGTH] + "..."

        # Compute running days from Foreplay's running_duration object
        running_duration = ad.get("running_duration")
        running_days = compute_running_days_from_duration(running_duration)

        # Parse started_running timestamp
        start_date = timestamp_to_isodate(ad.get("started_running"))

        # Determine display format
        display_format = (ad.get("display_format") or ad.get("type") or "").lower()

        # Media: prioritize high-quality fields
        # - Image ads: 'image' is full-res
        # - Video ads: 'video' is the video, 'thumbnail' is preview frame
        # - Carousel ads: only 'avatar' (tiny brand icon) — no usable preview
        video_url = ad.get("video")
        image_url = ad.get("image")
        thumb = ad.get("thumbnail")
        avatar = ad.get("avatar")

        # For display: use highest quality available
        if video_url:
            media_url = video_url
            thumbnail_url = thumb or image_url or avatar
            if not display_format:
                display_format = "video"
        elif image_url:
            media_url = None  # no video
            thumbnail_url = image_url
            if not display_format:
                display_format = "image"
        elif thumb:
            media_url = None
            thumbnail_url = thumb
        else:
            media_url = None
            thumbnail_url = avatar  # last resort: tiny brand icon

        # Flag: does this ad have a real preview image (not just a tiny avatar)?
        has_preview = bool(image_url or thumb or video_url)

        cleaned.append({
            "ad_id": ad_id,
            "brand_name": ad.get("brand_name") or ad.get("name"),
            "brand_id": brand_id if brand_id else None,
            "publisher_platform": platform or "unknown",
            "display_format": display_format or None,
            "has_preview": has_preview,
            "live": ad.get("live"),
            "start_date": start_date or None,
            "end_date": None,
            "last_seen_date": None,
            "running_days": running_days,
            "text": body,
            "headline": headline,
            "cta": ad.get("cta_title") or ad.get("cta_type") or ad.get("cta"),
            "media_url": media_url,
            "thumbnail_url": thumbnail_url,
            "landing_page_url": ad.get("link_url") or ad.get("landing_page_url"),
            "lens": lens,
            "_platform": platform,
            "_format": display_format,
        })

    logger.info(f"[ADS_INTEL] Postprocess [{lens}]: {len(cleaned)} kept, dropped={dropped}")
    return cleaned
