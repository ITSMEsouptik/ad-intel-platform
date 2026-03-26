"""
Novara Creative Analysis: Multimodal LLM Analyzer
Sends media + context to Gemini 2.5 Flash for structured creative breakdowns.
"""

import os
import json
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List

from .schema import (
    AdCreativeAnalysis, CreativeAnalysisCore,
    VideoAnalysisFields, ImageAnalysisFields, CarouselAnalysisFields,
    TikTokCreativeAnalysis, TikTokAnalysisFields,
)
from .prompts import build_ad_prompt, build_tiktok_prompt
from .media_cache import download_media_with_mime, get_cached_tiktok, download_media, _detect_mime_type

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"
MAX_RETRIES = 2
RATE_LIMIT_BACKOFF = 3


def _get_client():
    """Create a Gemini client with the user's API key."""
    from google import genai
    api_key = os.environ.get("GOOGLE_AI_STUDIO_KEY")
    if not api_key:
        raise ValueError("GOOGLE_AI_STUDIO_KEY not set")
    return genai.Client(api_key=api_key)


def _determine_depth(ad: dict) -> str:
    """Determine analysis depth based on ad score tier."""
    score = ad.get("score")
    if score is None:
        # No scoring data — default to standard depth
        return "standard"
    if score >= 70:
        return "full"
    elif score >= 50:
        return "standard"
    return "basic"


def _get_media_url(ad: dict) -> tuple[Optional[str], str]:
    """Get the best media URL for an ad and its expected type."""
    fmt = (ad.get("display_format") or "").lower()
    if fmt == "video" and ad.get("media_url"):
        return ad["media_url"], "video"
    elif fmt == "image" and ad.get("thumbnail_url"):
        return ad["thumbnail_url"], "image"
    elif fmt == "carousel" and ad.get("thumbnail_url"):
        return ad["thumbnail_url"], "image"
    elif ad.get("thumbnail_url"):
        return ad["thumbnail_url"], "image"
    return None, "unknown"


async def _call_gemini(prompt: str, media_bytes: Optional[bytes] = None,
                       mime_type: str = "image/jpeg") -> Optional[dict]:
    """Call Gemini with optional media input. Returns parsed JSON or None."""
    from google.genai import types

    client = _get_client()

    for attempt in range(MAX_RETRIES):
        try:
            parts = []
            if media_bytes:
                parts.append(types.Part(
                    inline_data=types.Blob(data=media_bytes, mime_type=mime_type)
                ))
            parts.append(types.Part(text=prompt))

            start = time.time()
            # Use async client to avoid blocking the event loop
            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=types.Content(parts=parts),
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=8000,
                    response_mime_type="application/json",
                )
            )
            elapsed = round(time.time() - start, 2)

            text = response.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [line for line in lines if not line.startswith("```")]
                text = "\n".join(lines)

            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Try to fix truncated JSON by closing open brackets
                fixed = text
                open_braces = fixed.count("{") - fixed.count("}")
                open_brackets = fixed.count("[") - fixed.count("]")
                # Trim trailing incomplete string
                if fixed and fixed[-1] not in "]}\"":
                    last_quote = fixed.rfind('"')
                    if last_quote > 0:
                        fixed = fixed[:last_quote + 1]
                fixed += "]" * max(0, open_brackets)
                fixed += "}" * max(0, open_braces)
                try:
                    result = json.loads(fixed)
                    logger.info(f"[ANALYZER] Fixed truncated JSON (added {open_braces} braces, {open_brackets} brackets)")
                except json.JSONDecodeError as e2:
                    logger.warning(f"[ANALYZER] JSON parse failed on attempt {attempt+1}: {e2}")
                    if attempt < MAX_RETRIES - 1:
                        continue
                    return None

            logger.info(f"[ANALYZER] Gemini response in {elapsed}s, keys={list(result.keys())}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"[ANALYZER] JSON parse error on attempt {attempt+1}: {e}")
            if attempt < MAX_RETRIES - 1:
                continue
            return None
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"[ANALYZER] Rate limit, backing off {RATE_LIMIT_BACKOFF}s...")
                    await asyncio.sleep(RATE_LIMIT_BACKOFF)
                    continue
            logger.error(f"[ANALYZER] Gemini error on attempt {attempt+1}: {e}")
            return None
    return None


def _parse_ad_analysis(raw: dict, ad: dict, depth: str) -> AdCreativeAnalysis:
    """Parse raw LLM output into structured AdCreativeAnalysis."""
    ad_id = ad.get("ad_id", "unknown")
    fmt = (ad.get("display_format") or "").lower()

    try:
        core_data = raw.get("core", raw)
        core = CreativeAnalysisCore(**{
            k: core_data.get(k, v.default if hasattr(v, 'default') else "")
            for k, v in CreativeAnalysisCore.model_fields.items()
        })
    except Exception as e:
        logger.warning(f"[ANALYZER] Core parse fallback for ad {ad_id}: {e}")
        core = CreativeAnalysisCore()

    video = None
    image = None
    carousel = None

    try:
        if fmt == "video" and depth != "basic":
            vid_data = raw.get("video", {})
            if vid_data:
                video = VideoAnalysisFields(**{
                    k: vid_data.get(k, "") for k in VideoAnalysisFields.model_fields
                })

        elif fmt == "image" and depth != "basic":
            img_data = raw.get("image", {})
            if img_data:
                image = ImageAnalysisFields(**{
                    k: img_data.get(k, "") for k in ImageAnalysisFields.model_fields
                })

        elif fmt == "carousel" and depth != "basic":
            car_data = raw.get("carousel", {})
            if car_data:
                carousel = CarouselAnalysisFields(**{
                    k: car_data.get(k, "") for k in CarouselAnalysisFields.model_fields
                })
    except Exception as e:
        logger.warning(f"[ANALYZER] Format-specific parse error for ad {ad_id}: {e}")

    return AdCreativeAnalysis(
        ad_id=ad_id,
        display_format=fmt,
        analysis_depth=depth,
        core=core,
        video=video,
        image=image,
        carousel=carousel,
    )


def _parse_tiktok_analysis(raw: dict, post: dict) -> TikTokCreativeAnalysis:
    """Parse raw LLM output into structured TikTokCreativeAnalysis."""
    analysis_data = raw.get("analysis", raw)
    analysis = TikTokAnalysisFields(**{
        k: analysis_data.get(k, "") for k in TikTokAnalysisFields.model_fields
    })

    return TikTokCreativeAnalysis(
        post_url=post.get("post_url", ""),
        author_handle=post.get("author_handle", ""),
        analysis=analysis,
        hook_text=raw.get("hook_text"),
        implied_target_persona=raw.get("implied_target_persona"),
        key_insight=raw.get("key_insight"),
    )


# ============== PUBLIC API ==============

async def _pre_download_ad_media(ad: dict) -> tuple[Optional[bytes], str]:
    """Pre-download media for an ad. Returns (bytes, mime_type)."""
    media_url, media_type = _get_media_url(ad)
    if media_url:
        data, mime = await download_media_with_mime(media_url)
        if data:
            return data, mime
    # Fallback to thumbnail
    if ad.get("thumbnail_url"):
        return await download_media_with_mime(ad["thumbnail_url"])
    return None, "image/jpeg"


async def _pre_download_tiktok_media(post: dict) -> tuple[Optional[bytes], str]:
    """Pre-download media for a TikTok post. Returns (bytes, mime_type)."""
    post_url = post.get("post_url", "")
    # Try cache first (fast, no network)
    cached = get_cached_tiktok(post_url)
    if cached:
        return cached, "video/mp4"
    # Try downloading video
    if post.get("media_url"):
        data = await download_media(post["media_url"], timeout=30)
        if data:
            return data, "video/mp4"
    # Try thumbnail
    if post.get("thumb_url"):
        return await download_media_with_mime(post["thumb_url"])
    return None, "video/mp4"


async def _analyze_ad_with_media(
    ad: dict, media_bytes: Optional[bytes], mime_type: str, sem: asyncio.Semaphore
) -> AdCreativeAnalysis:
    """Analyze a single ad using pre-downloaded media."""
    ad_id = ad.get("ad_id", "unknown")
    depth = _determine_depth(ad)
    fmt = (ad.get("display_format") or "").lower()

    async with sem:
        try:
            if not media_bytes:
                logger.warning(f"[ANALYZER] No media for ad {ad_id}, text-only")

            prompt = build_ad_prompt(ad, depth)
            raw = await _call_gemini(prompt, media_bytes, mime_type)

            if not raw:
                return AdCreativeAnalysis(
                    ad_id=ad_id, display_format=fmt,
                    analysis_depth=depth, error="LLM analysis failed"
                )
            return _parse_ad_analysis(raw, ad, depth)

        except Exception as e:
            logger.error(f"[ANALYZER] Error analyzing ad {ad_id}: {e}")
            return AdCreativeAnalysis(
                ad_id=ad_id, display_format=fmt,
                analysis_depth=depth, error=str(e)
            )


async def _analyze_tiktok_with_media(
    post: dict, media_bytes: Optional[bytes], mime_type: str, sem: asyncio.Semaphore
) -> TikTokCreativeAnalysis:
    """Analyze a single TikTok post using pre-downloaded media."""
    post_url = post.get("post_url", "")

    async with sem:
        try:
            prompt = build_tiktok_prompt(post)
            raw = await _call_gemini(prompt, media_bytes, mime_type)

            if not raw:
                return TikTokCreativeAnalysis(
                    post_url=post_url,
                    author_handle=post.get("author_handle", ""),
                    error="LLM analysis failed"
                )
            return _parse_tiktok_analysis(raw, post)

        except Exception as e:
            logger.error(f"[ANALYZER] Error analyzing TikTok {post_url[:60]}: {e}")
            return TikTokCreativeAnalysis(
                post_url=post_url,
                author_handle=post.get("author_handle", ""),
                error=str(e)
            )


async def analyze_batch(
    ads: List[dict],
    tiktok_posts: List[dict],
    max_concurrent: int = 5,
) -> tuple[List[AdCreativeAnalysis], List[TikTokCreativeAnalysis]]:
    """
    Two-phase pipeline:
    Phase 1: Download ALL media in parallel (no rate limit needed)
    Phase 2: Analyze ALL with Gemini in parallel (semaphore for rate limit)
    """
    # Phase 1: Parallel media downloads (fast, no rate limit concern)
    logger.info(f"[ANALYZER] Phase 1: Downloading media for {len(ads)} ads + {len(tiktok_posts)} TikTok")
    download_tasks = (
        [_pre_download_ad_media(ad) for ad in ads] +
        [_pre_download_tiktok_media(post) for post in tiktok_posts]
    )
    media_results = await asyncio.gather(*download_tasks, return_exceptions=True)

    ad_media = []
    for i, r in enumerate(media_results[:len(ads)]):
        if isinstance(r, Exception):
            ad_media.append((None, "image/jpeg"))
        else:
            ad_media.append(r)

    tt_media = []
    for i, r in enumerate(media_results[len(ads):]):
        if isinstance(r, Exception):
            tt_media.append((None, "video/mp4"))
        else:
            tt_media.append(r)

    downloaded_count = sum(1 for m, _ in ad_media + tt_media if m is not None)
    logger.info(f"[ANALYZER] Phase 1 complete: {downloaded_count}/{len(ads) + len(tiktok_posts)} media downloaded")

    # Phase 2: Parallel Gemini analysis (with concurrency control)
    logger.info(f"[ANALYZER] Phase 2: Analyzing with Gemini (concurrency={max_concurrent})")
    sem = asyncio.Semaphore(max_concurrent)

    analysis_tasks = (
        [_analyze_ad_with_media(ad, media_bytes, mime, sem)
         for ad, (media_bytes, mime) in zip(ads, ad_media)] +
        [_analyze_tiktok_with_media(post, media_bytes, mime, sem)
         for post, (media_bytes, mime) in zip(tiktok_posts, tt_media)]
    )

    all_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

    ad_results = []
    for i, r in enumerate(all_results[:len(ads)]):
        if isinstance(r, Exception):
            ad_results.append(AdCreativeAnalysis(
                ad_id=ads[i].get("ad_id", "unknown"),
                display_format=ads[i].get("display_format", ""),
                error=str(r)
            ))
        else:
            ad_results.append(r)

    tt_results = []
    for i, r in enumerate(all_results[len(ads):]):
        if isinstance(r, Exception):
            tt_results.append(TikTokCreativeAnalysis(
                post_url=tiktok_posts[i].get("post_url", ""),
                error=str(r)
            ))
        else:
            tt_results.append(r)

    return ad_results, tt_results
