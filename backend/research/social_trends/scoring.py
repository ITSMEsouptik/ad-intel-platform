"""
Novara Research Foundation: Social Trends — Scoring
Version 2.0 - Feb 2026

Composite trend score optimized for ad creative intelligence:
  - save_rate (30%): saves/views — reference-worthy, purchase intent
  - overperformance (25%): views/followers — content quality signal
  - engagement_rate (25%): total engagement/views — overall resonance
  - recency (20%): exponential decay — freshness
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Weight configuration v2.0
WEIGHTS = {
    "save_rate": 0.30,
    "overperformance": 0.25,
    "engagement": 0.25,
    "recency": 0.20,
}


def compute_save_rate(saves: int = 0, views: Optional[int] = None) -> float:
    """
    Save rate = saves / views.
    Normalized: 2% save rate = 1.0 (very high for TikTok).
    """
    if not views or views <= 0 or saves <= 0:
        return 0.0
    rate = saves / views
    # Normalize: 2% = 1.0, 1% = 0.5, 0.5% = 0.25
    return min(1.0, rate / 0.02)


def compute_overperformance(
    views: Optional[int] = None,
    follower_count: Optional[int] = None,
) -> float:
    """
    Overperformance ratio = views / followers.
    Normalized: 100x = 1.0 (content massively outperformed account size).
    """
    if not views or views <= 0:
        return 0.0
    if not follower_count or follower_count <= 0:
        return 0.5  # unknown followers, assume average
    ratio = views / follower_count
    # Normalize: 100x = 1.0, 10x = 0.5, 1x = 0.15
    # Using log scale: log10(100) = 2, so score = log10(ratio) / 2
    if ratio <= 1:
        return 0.1
    return min(1.0, math.log10(ratio) / 2.0)


def compute_engagement_rate(
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    views: Optional[int] = None,
    follower_count: Optional[int] = None,
) -> Optional[float]:
    """
    Full engagement rate including saves.
    Prefer views-based if available.
    """
    engagement = likes + comments + (shares or 0) + (saves or 0)

    if views and views > 0:
        return engagement / views

    if follower_count and follower_count > 0:
        return engagement / follower_count

    return None


def compute_recency_score(posted_at: Optional[str], half_life_days: int = 15) -> float:
    """
    Exponential decay with 15-day half-life.
    Today = 1.0, 15 days ago ~ 0.5, 30 days ago ~ 0.25.
    """
    if not posted_at:
        return 0.3  # default for unknown date

    try:
        if isinstance(posted_at, (int, float)):
            post_dt = datetime.fromtimestamp(posted_at, tz=timezone.utc)
        elif "T" in str(posted_at):
            post_str = str(posted_at).replace("Z", "+00:00")
            post_dt = datetime.fromisoformat(post_str)
            if post_dt.tzinfo is None:
                post_dt = post_dt.replace(tzinfo=timezone.utc)
        else:
            return 0.3

        now = datetime.now(timezone.utc)
        days_ago = max(0, (now - post_dt).total_seconds() / 86400)

        decay_rate = math.log(2) / half_life_days
        return math.exp(-decay_rate * days_ago)

    except Exception:
        return 0.3


def score_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute all scores for a single trend item (v2.0).
    Returns: { trend_score, engagement_rate, recency_score, save_rate, overperformance_ratio }
    """
    metrics = item.get("metrics", {})
    likes = metrics.get("likes", 0) or 0
    comments = metrics.get("comments", 0) or 0
    shares = metrics.get("shares") or 0
    saves = metrics.get("saves") or 0
    views = metrics.get("views")

    follower_count = item.get("author_follower_count")
    posted_at = item.get("posted_at")
    platform = item.get("platform", "")

    # Individual scores
    save_score = compute_save_rate(saves, views)
    overperf_score = compute_overperformance(views, follower_count)

    eng_rate = compute_engagement_rate(likes, comments, shares, saves, views, follower_count)
    # Normalize engagement: 8% = 1.0 (generous ceiling for TikTok)
    eng_score = min(1.0, (eng_rate or 0) / 0.08) if eng_rate else 0.0

    recency = compute_recency_score(posted_at)

    # Instagram adjustment: when views/saves are unavailable, use likes+comments as proxy
    if platform == "instagram" and not views:
        total_engagement = likes + comments
        if total_engagement > 100:
            eng_score = min(1.0, total_engagement / 5000)
        elif total_engagement > 10:
            eng_score = 0.15
        if total_engagement > 0:
            overperf_score = max(overperf_score, 0.3)

    # Composite trend score
    trend_score = (
        WEIGHTS["save_rate"] * save_score
        + WEIGHTS["overperformance"] * overperf_score
        + WEIGHTS["engagement"] * eng_score
        + WEIGHTS["recency"] * recency
    )

    # Raw ratios for display
    raw_save_rate = (saves / views) if views and views > 0 else None
    raw_overperf = (views / follower_count) if views and follower_count and follower_count > 0 else None

    return {
        "trend_score": round(trend_score, 4),
        "engagement_rate": round(eng_rate, 6) if eng_rate is not None else None,
        "recency_score": round(recency, 4),
        "save_rate": round(raw_save_rate, 6) if raw_save_rate is not None else None,
        "overperformance_ratio": round(raw_overperf, 2) if raw_overperf is not None else None,
    }
