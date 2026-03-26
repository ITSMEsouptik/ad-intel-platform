"""
Novara Research Foundation: Social Trends — Handle Discovery
Version 1.0 - Feb 2026

Discovers IG + TikTok handles for the brand and competitors.
Order of truth:
1. Step 2 channels extraction
2. Perplexity (sonar) fallback for missing handles
"""

import os
import logging
import httpx
import json
from typing import Dict, Any, Optional, List

from .schema import SocialHandle

logger = logging.getLogger(__name__)

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


def extract_handles_from_step2(step2: Dict[str, Any]) -> List[SocialHandle]:
    """Extract social handles from Step 2 channels data."""
    handles = []
    channels = step2.get("channels", {})

    # channels can be: { social: [{ platform, url, handle }], messaging: [...] }
    social_list = []

    if isinstance(channels, dict):
        social_list = channels.get("social", [])
        if not social_list and not channels.get("messaging"):
            # Maybe channels itself is { instagram: "...", tiktok: "..." }
            for platform_key in ["instagram", "tiktok"]:
                val = channels.get(platform_key, "")
                if val and isinstance(val, str):
                    handle = val.strip().lstrip("@").replace("https://instagram.com/", "").replace("https://tiktok.com/@", "")
                    if handle:
                        social_list.append({"platform": platform_key, "handle": handle})
    elif isinstance(channels, list):
        social_list = channels

    for ch in social_list:
        if not isinstance(ch, dict):
            continue
        platform = str(ch.get("platform", "")).lower().strip()
        handle = str(ch.get("handle", "")).strip().lstrip("@")
        url = str(ch.get("url", "")).strip()

        # Try to extract handle from URL if handle is empty
        if not handle and url:
            if "instagram.com/" in url:
                handle = url.split("instagram.com/")[-1].strip("/").split("?")[0]
                platform = "instagram"
            elif "tiktok.com/@" in url:
                handle = url.split("tiktok.com/@")[-1].strip("/").split("?")[0]
                platform = "tiktok"

        if platform == "instagram" and handle:
            handles.append(SocialHandle(
                platform="instagram",
                handle=handle,
                url=url or f"https://instagram.com/{handle}",
                source="step2_channels",
            ))
        elif platform == "tiktok" and handle:
            handles.append(SocialHandle(
                platform="tiktok",
                handle=handle,
                url=url or f"https://tiktok.com/@{handle}",
                source="step2_channels",
            ))

    logger.info(f"[HANDLES] Step 2 extraction: {len(handles)} handles found")
    return handles


async def discover_handles_perplexity(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    missing_platforms: List[str],
) -> List[SocialHandle]:
    """
    Fallback: Use Perplexity to find social handles.
    Only called for platforms not found in Step 2.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        logger.warning("[HANDLES] No PERPLEXITY_API_KEY, skipping fallback")
        return []

    if not missing_platforms:
        return []

    location = f"{city}, {country}" if city else country
    platforms_str = " and ".join(missing_platforms)

    prompt = f"""Find the official {platforms_str} accounts for this business:

Business: {brand_name}
Website: {domain}
Location: {location}
Category: {subcategory}

Return ONLY a JSON object with the handles you find. Be 100% sure these are the OFFICIAL accounts for this specific business (match the domain/location/category).

Format:
{{
  "instagram": "handle_without_at_sign_or_null",
  "tiktok": "handle_without_at_sign_or_null"
}}

If you cannot find an official account with confidence, use null for that platform."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You find official social media accounts for businesses. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 200,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(PERPLEXITY_URL, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            # Parse JSON from response
            text = content.strip()
            if text.startswith("```"):
                lines = text.split("\n")[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)

            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end])
            else:
                logger.warning("[HANDLES] Perplexity returned no JSON")
                return []

            handles = []
            for platform in missing_platforms:
                handle = parsed.get(platform)
                if handle and isinstance(handle, str) and handle.lower() != "null":
                    handle = handle.strip().lstrip("@")
                    if handle:
                        handles.append(SocialHandle(
                            platform=platform,
                            handle=handle,
                            url=f"https://{'instagram.com' if platform == 'instagram' else 'tiktok.com/@'}/{handle}",
                            source="perplexity_fallback",
                        ))

            logger.info(f"[HANDLES] Perplexity fallback: {len(handles)} handles found for {missing_platforms}")
            return handles

    except Exception as e:
        logger.error(f"[HANDLES] Perplexity fallback failed: {e}")
        return []


async def discover_all_handles(
    step2: Dict[str, Any],
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
) -> List[SocialHandle]:
    """
    Discover IG + TikTok handles using all available sources.
    """
    # 1. Extract from Step 2
    handles = extract_handles_from_step2(step2)

    # 2. Check what's missing
    found_platforms = {h.platform for h in handles}
    missing = [p for p in ["instagram", "tiktok"] if p not in found_platforms]

    # 3. Perplexity fallback for missing
    if missing:
        logger.info(f"[HANDLES] Missing platforms: {missing}, trying Perplexity fallback")
        fallback = await discover_handles_perplexity(
            brand_name=brand_name,
            domain=domain,
            city=city,
            country=country,
            subcategory=subcategory,
            missing_platforms=missing,
        )
        handles.extend(fallback)

    found = {h.platform: h.handle for h in handles}
    logger.info(f"[HANDLES] Final result: {found}")
    return handles


async def discover_competitor_handles(
    competitor_names: List[str],
    competitor_websites: List[str],
    city: str,
    country: str,
    subcategory: str,
) -> List[Dict[str, Any]]:
    """
    Discover IG + TikTok handles for competitors.
    Uses competitor websites in the prompt for much higher accuracy.
    Returns list of { name: str, handles: [SocialHandle] }
    """
    if not competitor_names:
        return []

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return []

    location = f"{city}, {country}" if city else country

    # Build competitor list with websites for better discovery
    comp_lines = []
    for i, name in enumerate(competitor_names[:5]):
        website = competitor_websites[i] if i < len(competitor_websites) else ""
        if website:
            comp_lines.append(f"- {name} (website: {website})")
        else:
            comp_lines.append(f"- {name}")
    comp_block = "\n".join(comp_lines)

    prompt = f"""Find the official Instagram and TikTok accounts for these businesses in {location} ({subcategory}):

{comp_block}

Search the web for each business. Check their websites for social media links. Look at their footer, about page, or contact page for official social handles.

Return a JSON object mapping each company name to their handles:
{{
{chr(10).join(f'  "{name}": {{ "instagram": "handle_or_null", "tiktok": "handle_or_null" }}' + (',' if i < len(competitor_names[:5])-1 else '') for i, name in enumerate(competitor_names[:5]))}
}}

Only return handles you are confident are the OFFICIAL accounts. Use null if unsure."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "You find official social media accounts for businesses. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(PERPLEXITY_URL, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            text = content.strip()
            if text.startswith("```"):
                lines = text.split("\n")[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines)

            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end])
            else:
                return []

            competitors = []
            for name in competitor_names[:5]:
                # Try exact match or case-insensitive
                comp_data = parsed.get(name)
                if not comp_data:
                    for k, v in parsed.items():
                        if k.lower() == name.lower():
                            comp_data = v
                            break

                if not comp_data or not isinstance(comp_data, dict):
                    continue

                handles = []
                for platform in ["instagram", "tiktok"]:
                    handle = comp_data.get(platform)
                    if handle and isinstance(handle, str) and handle.lower() != "null":
                        handle = handle.strip().lstrip("@")
                        if handle:
                            handles.append(SocialHandle(
                                platform=platform,
                                handle=handle,
                                url=f"https://{'instagram.com' if platform == 'instagram' else 'tiktok.com/@'}/{handle}",
                                source="perplexity_competitor",
                            ))

                if handles:
                    competitors.append({"name": name, "handles": [h.model_dump() for h in handles]})

            logger.info(f"[HANDLES] Competitor discovery: {len(competitors)} competitors with handles")
            return competitors

    except Exception as e:
        logger.error(f"[HANDLES] Competitor handle discovery failed: {e}")
        return []
