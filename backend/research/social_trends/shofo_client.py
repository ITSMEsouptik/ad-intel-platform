"""
Novara Research Foundation: Social Trends — Shofo API Client
Version 1.0 - Feb 2026

Wraps all Shofo endpoints:
- TikTok: SQL, Profile, Hashtag
- Instagram: Hashtag, User Posts, User Profile
"""

import os
import logging
import asyncio
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

SHOFO_BASE = "https://api.shofo.ai/api"
TIMEOUT = 45.0
RETRY_DELAY = 2


def _headers() -> dict:
    key = os.environ.get("SHOFO_API_KEY", "")
    return {
        "X-API-Key": key,
        "Content-Type": "application/json",
    }


async def _get(endpoint: str, params: dict) -> Optional[Dict[str, Any]]:
    """GET request to Shofo with 1 retry. Skips retry on 400/401/402/403."""
    url = f"{SHOFO_BASE}/{endpoint}"
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=_headers())
                if resp.status_code in (400, 401, 402, 403):
                    error_body = ""
                    try:
                        error_body = str(resp.json().get("detail", ""))[:100]
                    except Exception:
                        pass
                    logger.warning(f"[SHOFO] {resp.status_code} on {endpoint}: {error_body}")
                    return None  # Don't retry on client errors
                if resp.status_code == 429:
                    logger.warning(f"[SHOFO] Rate limited on {endpoint}, retrying...")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"[SHOFO] {endpoint} attempt {attempt+1} failed: {e}")
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"[SHOFO] Unexpected error on {endpoint}: {e}")
            break
    return None


async def _post(endpoint: str, payload: dict) -> Optional[Dict[str, Any]]:
    """POST request to Shofo with 1 retry. Skips retry on 400/401/402/403."""
    url = f"{SHOFO_BASE}/{endpoint}"
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(url, json=payload, headers=_headers())
                if resp.status_code in (400, 401, 402, 403):
                    error_body = ""
                    try:
                        error_body = str(resp.json().get("detail", ""))[:100]
                    except Exception:
                        pass
                    logger.warning(f"[SHOFO] {resp.status_code} on {endpoint}: {error_body}")
                    return None  # Don't retry on client errors
                if resp.status_code == 429:
                    logger.warning(f"[SHOFO] Rate limited on {endpoint}, retrying...")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                if data.get("success") is False:
                    logger.warning(f"[SHOFO] {endpoint} returned success=false: {data.get('error','')}")
                    return None
                return data
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"[SHOFO] {endpoint} attempt {attempt+1} failed: {e}")
            if attempt == 0:
                await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"[SHOFO] Unexpected error on {endpoint}: {e}")
            break
    return None


async def health_check() -> bool:
    """Quick health check — try a minimal TikTok SQL query.
    Returns True if Shofo is responsive, False if down."""
    try:
        result = await _post("tiktok/sql", {"query": "SELECT video_id FROM tiktok LIMIT 1", "limit": 1})
        if result is not None:
            return True
        logger.warning("[SHOFO] Health check failed — service may be down")
        return False
    except Exception:
        logger.warning("[SHOFO] Health check failed — connection error")
        return False



# ============== TIKTOK ENDPOINTS ==============

async def tiktok_sql(query: str, limit: int = 100) -> Optional[Dict[str, Any]]:
    """
    TikTok SQL endpoint.
    Fields: video_id, author_unique_id, author_sec_uid, author_follower_count,
            create_time, video_desc, hashtags, play_count, digg_count,
            comment_count, share_count, video_duration, music_title, music_author_name
    """
    logger.info(f"[SHOFO] TikTok SQL: limit={limit}, query={query[:80]}...")
    return await _post("tiktok/sql", {"query": query, "limit": limit})


async def tiktok_profile(username: str, count: int = 30) -> Optional[Dict[str, Any]]:
    """Get videos from a TikTok user's profile."""
    logger.info(f"[SHOFO] TikTok profile: @{username}, count={count}")
    return await _get("tiktok/profile", {"username": username, "count": count})


async def tiktok_hashtag(hashtag: str, count: int = 40) -> Optional[Dict[str, Any]]:
    """Get videos for a TikTok hashtag."""
    logger.info(f"[SHOFO] TikTok hashtag: #{hashtag}, count={count}")
    return await _get("tiktok/hashtag", {"hashtag": hashtag, "count": count})


# ============== INSTAGRAM ENDPOINTS ==============

async def ig_hashtag(keyword: str, count: int = 40, feed_type: str = "top") -> Optional[Dict[str, Any]]:
    """
    Get posts for an Instagram hashtag.
    feed_type: "top" | "recent" | "reels"
    """
    logger.info(f"[SHOFO] IG hashtag: #{keyword}, count={count}, feed_type={feed_type}")
    return await _get("instagram/hashtag", {
        "keyword": keyword,
        "count": count,
        "feed_type": feed_type,
    })


async def ig_user_posts(username: str, count: int = 30, reels_only: bool = False) -> Optional[Dict[str, Any]]:
    """Get posts/reels from an Instagram user's profile."""
    logger.info(f"[SHOFO] IG user posts: @{username}, count={count}, reels_only={reels_only}")
    return await _get("instagram/user-posts", {
        "username": username,
        "count": count,
        "reels_only": reels_only,
    })


async def ig_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """Get Instagram profile data (no followers/following lists)."""
    logger.info(f"[SHOFO] IG profile: @{username}")
    return await _get("instagram/user-profile", {
        "username": username,
        "max_followers": 0,
        "max_following": 0,
    })


# ============== TIKTOK OEMBED (free, for thumbnails) ==============

async def tiktok_oembed(video_url: str) -> Optional[Dict[str, Any]]:
    """
    Get TikTok video thumbnail via oEmbed (free, no auth).
    Returns: { thumbnail_url, title, author_name, ... }
    """
    oembed_url = "https://www.tiktok.com/oembed"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(oembed_url, params={"url": video_url})
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.debug(f"[SHOFO] oEmbed failed for {video_url[:60]}: {e}")
    return None


async def batch_tiktok_oembed(video_urls: List[str], max_concurrent: int = 5) -> Dict[str, str]:
    """
    Batch-fetch TikTok thumbnails via oEmbed.
    Returns: { video_url: thumbnail_url }
    """
    results = {}
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _fetch(url: str):
        async with semaphore:
            data = await tiktok_oembed(url)
            if data and data.get("thumbnail_url"):
                results[url] = data["thumbnail_url"]

    tasks = [_fetch(url) for url in video_urls[:60]]  # cap at 60
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(f"[SHOFO] oEmbed batch: {len(results)}/{len(video_urls)} thumbnails fetched")
    return results
