"""
Novara Research Foundation: Social Trends — Shortlisting
Version 1.0 - Feb 2026

Build final curated shortlist (30-60 per platform) with diversity rules:
- Max 2 items per author
- Max 30% items from a single hashtag/keyword
- Prefer shortform video (reels/tiktok)
- At least 1-2 items per handle in brand_competitors lens
"""

import logging
from typing import List, Dict, Any
from collections import Counter

from .budget import SHORTLIST_MIN_PER_PLATFORM, SHORTLIST_MAX_PER_PLATFORM

logger = logging.getLogger(__name__)

MAX_PER_AUTHOR = 2
MAX_SOURCE_CONCENTRATION = 0.30  # max 30% from single source_query


def build_shortlist(
    items: List[Dict[str, Any]],
    platform: str,
    target_size: int = SHORTLIST_MAX_PER_PLATFORM,
) -> List[Dict[str, Any]]:
    """
    Build a curated shortlist from scored items.
    Items should already have score.trend_score computed.
    """
    if not items:
        return []

    # Sort by trend_score descending
    sorted_items = sorted(items, key=lambda x: x.get("score", {}).get("trend_score", 0), reverse=True)

    shortlist = []
    author_counts: Counter = Counter()
    source_counts: Counter = Counter()

    # Phase 1: Ensure diversity for brand_competitors lens
    # Add at least 1 item per unique handle in brand_competitors
    bc_items = [i for i in sorted_items if i.get("lens") == "brand_competitors"]
    bc_handles = set()
    for item in bc_items:
        handle = item.get("author_handle", "")
        if handle and handle not in bc_handles:
            bc_handles.add(handle)
            shortlist.append(item)
            author_counts[handle] += 1
            source_counts[item.get("source_query", "")] += 1

    # Phase 2: Fill remaining slots with top-scored items
    added_urls = {item.get("post_url") for item in shortlist}

    for item in sorted_items:
        if len(shortlist) >= target_size:
            break

        post_url = item.get("post_url", "")
        if post_url in added_urls:
            continue

        author = item.get("author_handle", "unknown")
        source = item.get("source_query", "")

        # Diversity check: max per author
        if author_counts[author] >= MAX_PER_AUTHOR:
            continue

        # Diversity check: max concentration from single source
        if source and len(shortlist) > 5:
            concentration = source_counts[source] / max(1, len(shortlist))
            if concentration >= MAX_SOURCE_CONCENTRATION and source_counts[source] > 2:
                continue

        shortlist.append(item)
        added_urls.add(post_url)
        author_counts[author] += 1
        source_counts[source] += 1

    # Phase 3: Prefer video/reel content — boost to front if we have mixed types
    video_types = {"video", "reel", "reels"}
    videos = [i for i in shortlist if i.get("media_type", "").lower() in video_types]
    non_videos = [i for i in shortlist if i.get("media_type", "").lower() not in video_types]

    # Interleave: 2 videos then 1 non-video
    if len(videos) > len(non_videos) * 0.5:
        reordered = []
        vi, ni = 0, 0
        while vi < len(videos) or ni < len(non_videos):
            if vi < len(videos):
                reordered.append(videos[vi])
                vi += 1
            if vi < len(videos):
                reordered.append(videos[vi])
                vi += 1
            if ni < len(non_videos):
                reordered.append(non_videos[ni])
                ni += 1
        shortlist = reordered

    logger.info(
        f"[SHORTLIST] {platform}: {len(shortlist)} items "
        f"(from {len(items)} candidates, {len(bc_handles)} brand/competitor handles ensured, "
        f"top authors: {author_counts.most_common(3)})"
    )

    return shortlist[:target_size]


def extract_trending_audio(tiktok_items: List[Dict[str, Any]], top_n: int = 15) -> List[Dict[str, Any]]:
    """
    Extract trending audio tracks from TikTok items.
    Group by music_title, count usage, compute avg metrics.
    """
    audio_map: Dict[str, Dict[str, Any]] = {}

    for item in tiktok_items:
        title = item.get("music_title", "")
        author = item.get("music_author", "")
        if not title or title.lower() in ("original sound", "original audio", ""):
            continue

        key = f"{title}|{author}"
        if key not in audio_map:
            audio_map[key] = {
                "music_title": title,
                "music_author": author,
                "usage_count": 0,
                "total_views": 0,
                "total_likes": 0,
                "top_video_url": None,
                "top_video_views": 0,
            }

        entry = audio_map[key]
        entry["usage_count"] += 1
        metrics = item.get("metrics", {})
        views = metrics.get("views") or 0
        likes = metrics.get("likes", 0)
        entry["total_views"] += views
        entry["total_likes"] += likes

        if views > entry["top_video_views"]:
            entry["top_video_views"] = views
            entry["top_video_url"] = item.get("post_url")

    # Sort by usage count, then by total views
    sorted_audio = sorted(
        audio_map.values(),
        key=lambda x: (x["usage_count"], x["total_views"]),
        reverse=True,
    )[:top_n]

    results = []
    for a in sorted_audio:
        count = a["usage_count"]
        results.append({
            "music_title": a["music_title"],
            "music_author": a["music_author"],
            "usage_count": count,
            "avg_views": round(a["total_views"] / max(1, count)),
            "avg_likes": round(a["total_likes"] / max(1, count)),
            "top_video_url": a["top_video_url"],
            "top_video_views": a["top_video_views"],
        })

    logger.info(f"[SHORTLIST] Trending audio: {len(results)} tracks from {len(tiktok_items)} TikTok items")
    return results
