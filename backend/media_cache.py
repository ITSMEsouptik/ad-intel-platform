"""
Novara Media Cache — Thumbnail & Video Persistence
Feb 2026

Downloads and caches media from temporary CDN URLs (Shofo cover_url, video_url_list).
Serves cached files via FastAPI endpoints.

Storage: /app/backend/cached_media/thumbs/{video_id}.jpg
         /app/backend/cached_media/videos/{video_id}.mp4
"""

import os
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path("/app/backend/cached_media")
THUMB_DIR = CACHE_DIR / "thumbs"
VIDEO_DIR = CACHE_DIR / "videos"

THUMB_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

MAX_THUMB_SIZE = 2 * 1024 * 1024  # 2MB per thumbnail
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB per video
DOWNLOAD_TIMEOUT = 15.0  # seconds per thumbnail
VIDEO_DOWNLOAD_TIMEOUT = 60.0


def _video_id_from_url(post_url: str) -> Optional[str]:
    """Extract video_id from a TikTok post URL."""
    # https://tiktok.com/@user/video/7607914840958471438
    if "/video/" in post_url:
        parts = post_url.split("/video/")
        if len(parts) > 1:
            vid = parts[1].split("?")[0].split("/")[0].strip()
            if vid.isdigit():
                return vid
    # Fallback: hash the URL
    return hashlib.md5(post_url.encode()).hexdigest()[:16]


def get_thumb_path(video_id: str) -> Path:
    return THUMB_DIR / f"{video_id}.jpg"


def get_video_path(video_id: str) -> Path:
    return VIDEO_DIR / f"{video_id}.mp4"


def thumb_exists(video_id: str) -> bool:
    p = get_thumb_path(video_id)
    return p.exists() and p.stat().st_size > 100


def video_exists(video_id: str) -> bool:
    p = get_video_path(video_id)
    return p.exists() and p.stat().st_size > 1000


async def download_thumb(
    cover_url: str, video_id: str, client: Optional[httpx.AsyncClient] = None
) -> bool:
    """Download a thumbnail image and cache it."""
    if not cover_url or thumb_exists(video_id):
        return thumb_exists(video_id)

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True)

    try:
        resp = await client.get(cover_url)
        if resp.status_code == 200:
            content = resp.content
            if len(content) > 100 and len(content) < MAX_THUMB_SIZE:
                get_thumb_path(video_id).write_bytes(content)
                return True
            else:
                logger.debug(f"[CACHE] Thumb too small/large: {video_id} ({len(content)} bytes)")
        else:
            logger.debug(f"[CACHE] Thumb download failed: {video_id} -> {resp.status_code}")
    except Exception as e:
        logger.debug(f"[CACHE] Thumb download error: {video_id} -> {e}")
    finally:
        if own_client:
            await client.aclose()

    return False


async def batch_cache_thumbnails(
    items: List[Dict], max_concurrent: int = 10
) -> Dict[str, bool]:
    """
    Download and cache thumbnails for a list of TrendItems.
    Returns: { video_id: success_bool }
    """
    results = {}
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _download(item: Dict):
        cover_url = item.get("thumb_url") or item.get("cover_url")
        post_url = item.get("post_url", "")
        video_id = _video_id_from_url(post_url)
        if not video_id or not cover_url:
            return

        if thumb_exists(video_id):
            results[video_id] = True
            return

        async with semaphore:
            success = await download_thumb(cover_url, video_id, client=shared_client)
            results[video_id] = success

    async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as shared_client:
        tasks = [_download(item) for item in items]
        await asyncio.gather(*tasks, return_exceptions=True)

    cached = sum(1 for v in results.values() if v)
    logger.info(f"[CACHE] Thumbnails: {cached}/{len(results)} cached ({len(items)} items)")
    return results


async def download_video(
    video_url: str, video_id: str, client: Optional[httpx.AsyncClient] = None
) -> bool:
    """Download a video file and cache it."""
    if not video_url or video_exists(video_id):
        return video_exists(video_id)

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=VIDEO_DOWNLOAD_TIMEOUT, follow_redirects=True)

    try:
        async with client.stream("GET", video_url) as resp:
            if resp.status_code != 200:
                logger.debug(f"[CACHE] Video download failed: {video_id} -> {resp.status_code}")
                return False

            path = get_video_path(video_id)
            total = 0
            with open(path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > MAX_VIDEO_SIZE:
                        logger.warning(f"[CACHE] Video too large, aborting: {video_id}")
                        f.close()
                        path.unlink(missing_ok=True)
                        return False
                    f.write(chunk)

            logger.info(f"[CACHE] Video cached: {video_id} ({total / 1024 / 1024:.1f}MB)")
            return True
    except Exception as e:
        logger.warning(f"[CACHE] Video download error: {video_id} -> {e}")
        get_video_path(video_id).unlink(missing_ok=True)
        return False
    finally:
        if own_client:
            await client.aclose()


async def batch_cache_videos(
    items: List[Dict], max_concurrent: int = 3, max_videos: int = 20
) -> Dict[str, bool]:
    """
    Download and cache videos for a list of TrendItems.
    Only caches the top N items to manage disk space and time.
    Returns: { video_id: success_bool }
    """
    results = {}
    semaphore = asyncio.Semaphore(max_concurrent)
    cached_count = 0

    async def _download(item: Dict):
        nonlocal cached_count
        video_url = item.get("media_url")
        if isinstance(video_url, list):
            video_url = video_url[0] if video_url else None
        post_url = item.get("post_url", "")
        video_id = _video_id_from_url(post_url)
        if not video_id or not video_url:
            return

        if video_exists(video_id):
            results[video_id] = True
            return

        if cached_count >= max_videos:
            return

        async with semaphore:
            success = await download_video(video_url, video_id, client=shared_client)
            results[video_id] = success
            if success:
                cached_count += 1

    async with httpx.AsyncClient(timeout=VIDEO_DOWNLOAD_TIMEOUT, follow_redirects=True) as shared_client:
        tasks = [_download(item) for item in items[:max_videos * 2]]
        await asyncio.gather(*tasks, return_exceptions=True)

    cached = sum(1 for v in results.values() if v)
    logger.info(f"[CACHE] Videos: {cached}/{len(results)} cached ({len(items)} items)")
    return results


def get_cache_stats() -> Dict:
    """Return cache statistics."""
    thumb_files = list(THUMB_DIR.glob("*.jpg"))
    video_files = list(VIDEO_DIR.glob("*.mp4"))
    thumb_size = sum(f.stat().st_size for f in thumb_files)
    video_size = sum(f.stat().st_size for f in video_files)
    return {
        "thumbs_count": len(thumb_files),
        "thumbs_size_mb": round(thumb_size / 1024 / 1024, 2),
        "videos_count": len(video_files),
        "videos_size_mb": round(video_size / 1024 / 1024, 2),
        "total_size_mb": round((thumb_size + video_size) / 1024 / 1024, 2),
    }
