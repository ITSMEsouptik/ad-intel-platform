"""
Media download and caching utilities for Creative Analysis.
Handles parallel downloads and TikTok video caching.
"""

import hashlib
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "cached_media"
TIKTOK_CACHE_DIR = CACHE_DIR / "tiktok"

# Ensure cache dirs exist
TIKTOK_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:16]


def get_tiktok_cache_path(post_url: str) -> Path:
    return TIKTOK_CACHE_DIR / f"{_url_hash(post_url)}.mp4"


def get_cached_tiktok(post_url: str) -> Optional[bytes]:
    """Read cached TikTok video from disk. Returns None if not cached."""
    path = get_tiktok_cache_path(post_url)
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()
    return None


async def download_media(url: str, timeout: float = 45) -> Optional[bytes]:
    """Download media from URL. Returns bytes or None on failure."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
            logger.warning(f"[MEDIA] Download failed: status={resp.status_code} size={len(resp.content)} url={url[:80]}")
            return None
    except Exception as e:
        logger.warning(f"[MEDIA] Download error for {url[:80]}: {e}")
        return None


def _detect_mime_type(url: str, fallback: str = "video/mp4") -> str:
    """Detect MIME type from URL extension."""
    url_lower = url.lower().split("?")[0]
    if url_lower.endswith(".mp4"):
        return "video/mp4"
    elif url_lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    elif url_lower.endswith(".png"):
        return "image/png"
    elif url_lower.endswith(".webp"):
        return "image/webp"
    elif url_lower.endswith(".webm"):
        return "video/webm"
    return fallback


async def download_media_with_mime(url: str, timeout: float = 45) -> tuple[Optional[bytes], str]:
    """Download media and return (bytes, mime_type)."""
    data = await download_media(url, timeout)
    mime = _detect_mime_type(url)
    return data, mime


async def cache_tiktok_videos(posts: List[Dict], max_concurrent: int = 8) -> int:
    """
    Download and cache TikTok videos in parallel.
    Called after Social Trends shortlisting to pre-cache videos.
    Returns count of successfully cached videos.
    """
    sem = asyncio.Semaphore(max_concurrent)
    cached = 0

    async def _cache_one(post: Dict) -> bool:
        post_url = post.get("post_url", "")
        media_url = post.get("media_url")
        if not media_url or not post_url:
            return False

        # Skip if already cached
        cache_path = get_tiktok_cache_path(post_url)
        if cache_path.exists() and cache_path.stat().st_size > 0:
            return True

        async with sem:
            data = await download_media(media_url, timeout=30)
            if data:
                cache_path.write_bytes(data)
                return True
            return False

    tasks = [_cache_one(p) for p in posts]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if r is True:
            cached += 1

    logger.info(f"[MEDIA_CACHE] Cached {cached}/{len(posts)} TikTok videos")
    return cached
