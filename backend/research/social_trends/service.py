"""
Novara Research Foundation: Social Trends Intelligence Service
Version 3.0 - Feb 2026

Orchestrates the full pipeline:
1. Load inputs (Step 1 geo + Step 2 Business DNA + Competitors)
2. Discover handles (brand + competitors)
3. Build keyword+hashtag SQL queries (video_desc + hashtags + date range + engagement)
4. Shofo fetch (budgeted): 4 query strategies + brand/competitor handles
5. Normalize into TrendItems (using cover_url, collect_count, web_video_url)
6. Score with v2.0 formula (save_rate, overperformance, engagement, recency)
7. Shortlist with diversity rules
8. Extract trending audio (TikTok)
9. Compute delta
10. Save snapshot
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    SocialTrendsSnapshot,
    SocialTrendsInputs,
    SocialTrendsAudit,
    SocialTrendsDelta,
    SocialTrendSet,
    TrendItem,
    TrendScore,
    PostMetrics,
    HandleSet,
    SocialHandle,
    TrendingAudio,
)
from .budget import BudgetTracker, SHORTLIST_MAX_PER_PLATFORM
from .handle_discovery import discover_all_handles, discover_competitor_handles
from .query_builder import build_query_plan
from .scoring import score_item, WEIGHTS
from .shortlist import build_shortlist, extract_trending_audio
from . import shofo_client

logger = logging.getLogger(__name__)

REFRESH_DAYS = 7
HISTORY_CAP = 10
WINDOW_DAYS = 30


class SocialTrendsService:
    def __init__(self, db):
        self.db = db

    def extract_inputs(
        self,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract all inputs needed for the pipeline."""
        geo = campaign_brief.get("geo", {})
        city = geo.get("city_or_region", "")
        country = geo.get("country", "")

        step2 = website_context_pack.get("step2", {})
        classification = step2.get("classification", {})
        offer = step2.get("offer", {})
        brand_summary = step2.get("brand_summary", {})
        site = step2.get("site", {})

        services = []
        for item in offer.get("offer_catalog", [])[:6]:
            name = item.get("name", "")
            if name and name.lower() != "unknown":
                services.append(name)

        return {
            "step2": step2,
            "geo": {"city": city, "country": country},
            "brand_name": brand_summary.get("name", ""),
            "domain": site.get("domain", site.get("final_url", "")),
            "subcategory": classification.get("subcategory", ""),
            "niche": classification.get("niche", ""),
            "industry": classification.get("industry", ""),
            "services": services,
            "tags": classification.get("tags", []),
        }

    async def _get_competitor_info(self, campaign_id: str) -> List[Dict[str, str]]:
        """Get competitor names and websites from research pack."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.competitors.latest.competitors": 1},
        )
        if not pack:
            return []

        comps = pack.get("sources", {}).get("competitors", {}).get("latest", {}).get("competitors", [])
        return [
            {"name": c.get("name", ""), "website": c.get("website", "")}
            for c in comps[:5]
            if c.get("name")
        ]

    # ============== NORMALIZATION ==============

    def _normalize_tiktok_sql_item(
        self, row: Dict[str, Any], lens: str, source_query: str, query_type: str = ""
    ) -> Dict[str, Any]:
        """Normalize a TikTok SQL row into a TrendItem dict (v2.0)."""
        video_id = str(row.get("video_id", ""))
        author = str(row.get("author_unique_id", ""))

        # Prefer web_video_url (reliable permalink)
        post_url = row.get("web_video_url", "")
        if not post_url and author and video_id:
            post_url = f"https://tiktok.com/@{author}/video/{video_id}"

        # Use cover_url directly (no oEmbed needed!)
        thumb_url = row.get("cover_url") or None

        # Handle create_time (Unix timestamp)
        create_time = row.get("create_time")
        posted_at = None
        if create_time:
            try:
                if isinstance(create_time, (int, float)):
                    posted_at = datetime.fromtimestamp(create_time, tz=timezone.utc).isoformat()
                else:
                    posted_at = str(create_time)
            except Exception:
                pass

        caption = str(row.get("video_desc", "") or "")[:180]

        # Music info
        music_author = row.get("music_author_name")
        if not music_author and isinstance(row.get("music"), dict):
            music_author = row["music"].get("author")

        return {
            "platform": "tiktok",
            "lens": lens,
            "query_type": query_type,
            "source_query": source_query,
            "author_handle": author,
            "author_follower_count": row.get("author_follower_count"),
            "author_verified": row.get("author_verified"),
            "post_url": post_url,
            "thumb_url": thumb_url,
            "media_url": row.get("video_url_list"),
            "media_type": "video",
            "caption": caption,
            "posted_at": posted_at,
            "duration": row.get("video_duration") or row.get("duration"),
            "hashtags": row.get("hashtags", []) or [],
            "metrics": {
                "views": row.get("play_count"),
                "likes": row.get("digg_count") or row.get("like_count", 0),
                "comments": row.get("comment_count", 0),
                "shares": row.get("share_count"),
                "saves": row.get("collect_count"),
            },
            "music_title": row.get("music_title"),
            "music_author": music_author,
        }

    def _normalize_tiktok_api_item(
        self, item: Dict[str, Any], lens: str, source_query: str, query_type: str = ""
    ) -> Dict[str, Any]:
        """Normalize a TikTok profile/hashtag/feed API item."""
        video_id = str(item.get("video_id", ""))
        author = str(item.get("author_unique_id", item.get("author", "")))
        post_url = item.get("web_video_url", "")
        if not post_url and author and video_id:
            post_url = f"https://tiktok.com/@{author}/video/{video_id}"

        thumb_url = item.get("cover_url") or None

        create_time = item.get("create_time")
        posted_at = None
        if create_time:
            try:
                if isinstance(create_time, (int, float)):
                    posted_at = datetime.fromtimestamp(create_time, tz=timezone.utc).isoformat()
                else:
                    posted_at = str(create_time)
            except Exception:
                pass

        caption = str(item.get("video_desc", item.get("description", "")) or "")[:180]

        return {
            "platform": "tiktok",
            "lens": lens,
            "query_type": query_type,
            "source_query": source_query,
            "author_handle": author,
            "author_follower_count": item.get("author_follower_count"),
            "author_verified": item.get("author_verified"),
            "post_url": post_url,
            "thumb_url": thumb_url,
            "media_url": item.get("video_url_list"),
            "media_type": "video",
            "caption": caption,
            "posted_at": posted_at,
            "duration": item.get("video_duration") or item.get("duration"),
            "hashtags": item.get("hashtags", []) or [],
            "metrics": {
                "views": item.get("play_count"),
                "likes": item.get("digg_count") or item.get("like_count", 0),
                "comments": item.get("comment_count", 0),
                "shares": item.get("share_count"),
                "saves": item.get("collect_count"),
            },
            "music_title": item.get("music_title"),
            "music_author": item.get("music_author_name"),
        }

    def _normalize_ig_item(
        self, item: Dict[str, Any], lens: str, source_query: str, query_type: str = ""
    ) -> Dict[str, Any]:
        """Normalize an Instagram post into a TrendItem dict."""
        post_id = str(item.get("id", ""))
        post_url = f"https://instagram.com/p/{post_id}" if post_id else ""
        author = ""
        if isinstance(item.get("author"), dict):
            author = item["author"].get("username", "")
        elif item.get("username"):
            author = item["username"]

        caption = str(item.get("caption", "") or "")[:180]

        return {
            "platform": "instagram",
            "lens": lens,
            "query_type": query_type,
            "source_query": source_query,
            "author_handle": author,
            "author_follower_count": None,
            "author_verified": None,
            "post_url": post_url,
            "thumb_url": item.get("media_url"),
            "media_url": item.get("media_url") or item.get("video_url"),
            "media_type": item.get("media_type", "image"),
            "caption": caption,
            "posted_at": item.get("created_at"),
            "duration": None,
            "hashtags": item.get("hashtags", []) or [],
            "metrics": {
                "views": None,
                "likes": item.get("like_count", 0),
                "comments": item.get("comment_count", 0),
                "shares": None,
                "saves": None,
            },
            "music_title": None,
            "music_author": None,
        }

    # ============== FETCH PIPELINES ==============

    async def _fetch_brand_competitors(
        self,
        brand_handles: List[SocialHandle],
        competitor_handles: List[Dict[str, Any]],
        budget: BudgetTracker,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch posts from brand + competitor handles."""
        ig_items = []
        tt_items = []

        # Build set of all known handles for official/mention labeling
        known_handles = set()
        for h in brand_handles:
            known_handles.add(h.handle.lower().replace(".", ""))
            known_handles.add(h.handle.lower())
        for comp in competitor_handles:
            for h in comp.get("handles", []):
                handle_str = h.handle if isinstance(h, SocialHandle) else h.get("handle", "")
                if handle_str:
                    known_handles.add(handle_str.lower().replace(".", ""))
                    known_handles.add(handle_str.lower())

        all_handles = list(brand_handles)
        for comp in competitor_handles:
            for h in comp.get("handles", []):
                if isinstance(h, dict):
                    all_handles.append(SocialHandle(**h))
                elif isinstance(h, SocialHandle):
                    all_handles.append(h)

        for handle in all_handles:
            if not budget.can_fetch(5):
                logger.warning("[SOCIAL] Budget exhausted during brand/competitor fetch")
                break

            cap = budget.cap_for_source(f"{handle.platform[:2]}_handle")
            if cap <= 0:
                continue

            try:
                if handle.platform == "instagram":
                    result = await shofo_client.ig_user_posts(
                        username=handle.handle,
                        count=cap,
                        reels_only=True,
                    )
                    if result and isinstance(result.get("data"), dict):
                        posts = result["data"].get("posts", [])
                        if posts:
                            budget.record_fetch(f"ig:@{handle.handle}", len(posts), result.get("request_id", ""))
                            for p in posts:
                                ig_items.append(self._normalize_ig_item(p, "brand_competitors", f"@{handle.handle}", "handle"))

                elif handle.platform == "tiktok":
                    # Strategy 1: Profile endpoint (live fetch)
                    result = await shofo_client.tiktok_profile(
                        username=handle.handle,
                        count=cap,
                    )
                    if result and isinstance(result.get("data"), dict) and result["data"].get("videos"):
                        videos = result["data"]["videos"]
                        budget.record_fetch(f"tt:@{handle.handle}", len(videos), result.get("request_id", ""))
                        for v in videos:
                            tt_items.append(self._normalize_tiktok_api_item(v, "brand_competitors", f"@{handle.handle}", "handle"))
                    else:
                        # Strategy 2: SQL fallback (pre-indexed)
                        sql_query = f"SELECT * FROM videos WHERE author_unique_id = '{handle.handle}' ORDER BY play_count DESC"
                        sql_result = await shofo_client.tiktok_sql(query=sql_query, limit=cap)
                        sql_found = False
                        if sql_result and isinstance(sql_result.get("data"), dict):
                            rows = sql_result["data"].get("rows", sql_result["data"].get("videos", []))
                            if rows:
                                sql_found = True
                                budget.record_fetch(f"tt:sql:@{handle.handle}", len(rows), sql_result.get("request_id", ""))
                                for row in rows:
                                    tt_items.append(self._normalize_tiktok_sql_item(row, "brand_competitors", f"@{handle.handle}", "handle"))

                        if not sql_found:
                            # Strategy 3: Hashtag search (finds their posts + UGC about them)
                            # Try both the handle AND a simplified version of it
                            clean_handle = handle.handle.replace(".", "").replace("_", "").lower()
                            # Also try just the core brand name (strip country codes like .ae, .uk, .com)
                            core_name = handle.handle.split(".")[0].replace("_", "").lower()
                            hashtags_to_try = list(dict.fromkeys([core_name, clean_handle]))  # dedupe, core_name first

                            for ht in hashtags_to_try:
                                if not budget.can_fetch(5):
                                    break
                                hashtag_result = await shofo_client.tiktok_hashtag(
                                    hashtag=ht, count=cap,
                                )
                                if hashtag_result and isinstance(hashtag_result.get("data"), dict):
                                    h_videos = hashtag_result["data"].get("videos", [])
                                    if h_videos:
                                        budget.record_fetch(f"tt:#{ht}", len(h_videos), hashtag_result.get("request_id", ""))
                                        for v in h_videos:
                                            tt_items.append(self._normalize_tiktok_api_item(v, "brand_competitors", f"#{ht}", "handle"))
                                        logger.info(f"[SOCIAL] Hashtag fallback for @{handle.handle}: {len(h_videos)} videos via #{ht}")
                                        break  # Found data, stop trying

            except Exception as e:
                logger.warning(f"[SOCIAL] Error fetching {handle.platform} @{handle.handle}: {e}")

        logger.info(f"[SOCIAL] Brand+Competitors: {len(ig_items)} IG, {len(tt_items)} TT items")

        # Strategy 4: For competitors with NO TikTok handle, search their name as a TikTok hashtag
        for comp in competitor_handles:
            comp_name = comp.get("name", "")
            comp_platforms = {h.platform if isinstance(h, SocialHandle) else h.get("platform") for h in comp.get("handles", [])}
            if "tiktok" not in comp_platforms and comp_name:
                if not budget.can_fetch(5):
                    break
                clean_name = comp_name.lower().replace(" ", "").replace("'", "").replace("&", "and")
                cap = budget.cap_for_source("tt_keyword")
                if cap <= 0:
                    continue
                try:
                    result = await shofo_client.tiktok_hashtag(hashtag=clean_name, count=cap)
                    if result and isinstance(result.get("data"), dict):
                        h_videos = result["data"].get("videos", [])
                        if h_videos:
                            budget.record_fetch(f"tt:#{clean_name}", len(h_videos), result.get("request_id", ""))
                            for v in h_videos:
                                tt_items.append(self._normalize_tiktok_api_item(v, "brand_competitors", f"#{clean_name}", "handle"))
                            logger.info(f"[SOCIAL] Competitor TikTok via hashtag #{clean_name}: {len(h_videos)} videos")
                except Exception as e:
                    logger.warning(f"[SOCIAL] Hashtag search for competitor #{clean_name} failed: {e}")

        if tt_items:
            logger.info(f"[SOCIAL] Brand+Competitors after hashtag fallback: {len(ig_items)} IG, {len(tt_items)} TT items")

        # Label posts as "official" (from known account) or "mention" (UGC about them)
        for item in ig_items + tt_items:
            author = (item.get("author_handle") or "").lower().replace(".", "")
            if author and author in known_handles:
                item["content_label"] = "official"
            else:
                item["content_label"] = "mention"

        return {"instagram": ig_items, "tiktok": tt_items}

    async def _fetch_category_trends(
        self,
        query_plan: Dict[str, Any],
        budget: BudgetTracker,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch category trend posts via smart SQL queries (v2.0).
        Uses 4 query strategies: viral, breakout, most_saved, most_discussed.
        Falls back to hashtag endpoint if SQL returns nothing.
        """
        ig_items = []
        tt_items = []
        ig_available = True  # circuit breaker for IG

        # ---- TikTok: Smart SQL queries (primary strategy) ----
        for sql_query_spec in query_plan.get("sql_queries", []):
            if not budget.can_fetch(10):
                logger.warning("[SOCIAL] Budget exhausted during category fetch")
                break

            query_type = sql_query_spec["type"]
            sql_query = sql_query_spec["query"]
            limit = min(sql_query_spec["limit"], budget.remaining)
            label = sql_query_spec["label"]

            try:
                result = await shofo_client.tiktok_sql(query=sql_query, limit=limit)
                if result and isinstance(result.get("data"), dict):
                    rows = result["data"].get("rows", [])
                    if rows:
                        budget.record_fetch(f"tt:sql:{query_type}", len(rows), result.get("request_id", ""))
                        for row in rows:
                            tt_items.append(self._normalize_tiktok_sql_item(
                                row, "category_trends", label, query_type
                            ))
                        logger.info(f"[SOCIAL] SQL {query_type}: {len(rows)} items ({label})")
                    else:
                        logger.info(f"[SOCIAL] SQL {query_type}: 0 items ({label})")
                else:
                    logger.warning(f"[SOCIAL] SQL {query_type} failed or empty response")
            except Exception as e:
                logger.warning(f"[SOCIAL] Error on SQL {query_type}: {e}")

        # ---- Instagram: hashtag queries (may be unavailable) ----
        for hashtag in query_plan.get("ig_hashtags", []):
            if not ig_available:
                break
            if not budget.can_fetch(5):
                break
            cap = budget.cap_for_source("ig_hashtag")
            if cap <= 0:
                break

            try:
                result = await shofo_client.ig_hashtag(
                    keyword=hashtag,
                    count=cap,
                    feed_type="reels",
                )
                if result and isinstance(result.get("data"), dict):
                    posts = result["data"].get("posts", [])
                    if posts:
                        budget.record_fetch(f"ig:#{hashtag}", len(posts), result.get("request_id", ""))
                        for p in posts:
                            ig_items.append(self._normalize_ig_item(p, "category_trends", f"#{hashtag}", "hashtag"))
                elif result is None:
                    logger.info("[SOCIAL] IG hashtag endpoint unavailable, skipping remaining IG queries")
                    ig_available = False
            except Exception as e:
                logger.warning(f"[SOCIAL] Error fetching IG #{hashtag}: {e}")
                ig_available = False

        logger.info(f"[SOCIAL] Category Trends: {len(ig_items)} IG, {len(tt_items)} TT items")

        # Label all category trend posts
        for item in ig_items + tt_items:
            item["content_label"] = "category"

        return {"instagram": ig_items, "tiktok": tt_items}

    # ============== MAIN PIPELINE ==============

    async def run(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Full pipeline (v2.0)."""
        try:
            logger.info(f"[SOCIAL] Starting v2.0 pipeline for campaign {campaign_id}")

            # 1. Extract inputs
            inputs = self.extract_inputs(campaign_brief, website_context_pack)
            city = inputs["geo"]["city"]
            country = inputs["geo"]["country"]

            logger.info(f"[SOCIAL] Brand: {inputs['brand_name']}, Location: {city or country}")

            # 2. Discover handles (brand)
            brand_handles = await discover_all_handles(
                step2=inputs["step2"],
                brand_name=inputs["brand_name"],
                domain=inputs["domain"],
                city=city,
                country=country,
                subcategory=inputs["subcategory"],
            )

            # 3. Get competitor names + discover their handles
            competitor_info = await self._get_competitor_info(campaign_id)
            competitor_handles = []
            if competitor_info:
                competitor_handles = await discover_competitor_handles(
                    competitor_names=[c["name"] for c in competitor_info],
                    competitor_websites=[c.get("website", "") for c in competitor_info],
                    city=city,
                    country=country,
                    subcategory=inputs["subcategory"],
                )

            logger.info(f"[SOCIAL] Handles: {len(brand_handles)} brand, {len(competitor_handles)} competitors")

            # 4. Build query plan (v2.0 with smart SQL)
            query_plan = build_query_plan(
                brand_name=inputs["brand_name"],
                subcategory=inputs["subcategory"],
                niche=inputs["niche"],
                industry=inputs["industry"],
                tags=inputs["tags"],
                services=inputs["services"],
                city=city,
                country=country,
            )

            # 5. Fetch data (budgeted) — health check Shofo first
            budget = BudgetTracker()

            from . import shofo_client
            shofo_up = await shofo_client.health_check()
            if not shofo_up:
                logger.warning("[SOCIAL_TRENDS] Shofo is down — skipping TikTok/IG fetch, returning service_unavailable")
                return {
                    "status": "service_unavailable",
                    "has_data": False,
                    "latest": {
                        "handles": {"brand": brand_handles, "competitors": competitor_handles},
                        "shortlist": {"tiktok": [], "instagram": []},
                        "trending_audio": [],
                        "lenses": {},
                        "audit": {"note": "Shofo service was down during this run. Re-run later."},
                    },
                }

            bc_data = await self._fetch_brand_competitors(brand_handles, competitor_handles, budget)
            cat_data = await self._fetch_category_trends(query_plan, budget)

            # 6. Score all items with v2.0 formula
            all_ig = bc_data["instagram"] + cat_data["instagram"]
            all_tt = bc_data["tiktok"] + cat_data["tiktok"]

            for item in all_ig + all_tt:
                item["score"] = score_item(item)

            # 7. Build shortlists
            ig_shortlist = build_shortlist(all_ig, "instagram", SHORTLIST_MAX_PER_PLATFORM)
            tt_shortlist = build_shortlist(all_tt, "tiktok", SHORTLIST_MAX_PER_PLATFORM)

            # 8. Extract trending audio from TikTok
            trending_audio = extract_trending_audio(all_tt)

            # 8.5. Fetch fresh thumbnails via oEmbed + cache to disk
            try:
                all_shortlisted = ig_shortlist + tt_shortlist
                # Step A: oEmbed for fresh thumbnail URLs
                tt_urls = [item["post_url"] for item in all_shortlisted if item.get("platform") == "tiktok" and item.get("post_url")]
                oembed_map = await shofo_client.batch_tiktok_oembed(tt_urls)

                # Step B: Update items with fresh oEmbed URLs
                for item in all_shortlisted:
                    fresh_url = oembed_map.get(item.get("post_url"))
                    if fresh_url:
                        item["thumb_url"] = fresh_url

                # Step C: Download and cache thumbnails to disk
                from media_cache import batch_cache_thumbnails
                await batch_cache_thumbnails(all_shortlisted)

                # Step D: Download and cache videos to disk (top items)
                from media_cache import batch_cache_videos
                await batch_cache_videos(all_shortlisted, max_concurrent=3, max_videos=20)
            except Exception as e:
                logger.warning(f"[SOCIAL] Media caching failed (non-fatal): {e}")

            # 9. Build snapshot
            snapshot = self._build_snapshot(
                inputs=inputs,
                brand_handles=brand_handles,
                competitor_handles=competitor_handles,
                query_plan=query_plan,
                bc_data=bc_data,
                cat_data=cat_data,
                ig_shortlist=ig_shortlist,
                tt_shortlist=tt_shortlist,
                trending_audio=trending_audio,
                budget=budget,
            )

            # 10. Delta
            previous = await self.get_latest(campaign_id)
            if previous:
                snapshot.delta = self._compute_delta(previous, snapshot)

            # 11. Save
            await self.save_snapshot(campaign_id, snapshot)

            # 12. Background-cache top TikTok videos for Creative Analysis
            if tt_shortlist:
                try:
                    from research.creative_analysis.media_cache import cache_tiktok_videos
                    # Sort by save_rate, take top 15
                    sorted_tt = sorted(
                        tt_shortlist,
                        key=lambda p: (p.get("score", {}).get("save_rate", 0) if isinstance(p.get("score"), dict) else 0),
                        reverse=True,
                    )[:15]
                    asyncio.create_task(cache_tiktok_videos(sorted_tt, max_concurrent=8))
                    logger.info(f"[SOCIAL] Started background caching of {len(sorted_tt)} TikTok videos")
                except Exception as cache_err:
                    logger.warning(f"[SOCIAL] TikTok video caching skipped: {cache_err}")

            ig_count = len(ig_shortlist)
            tt_count = len(tt_shortlist)
            total = ig_count + tt_count

            if total >= 20:
                status = "success"
            elif total >= 5:
                status = "partial"
            else:
                status = "low_data"

            logger.info(
                f"[SOCIAL] Pipeline v3.0 complete: {ig_count} IG + {tt_count} TT shortlisted, "
                f"{len(trending_audio)} trending audio, budget: ${budget.cost_estimate:.4f}, "
                f"keywords={query_plan.get('keywords', {}).get('desc_keywords', [])}, status={status}"
            )

            # Auto-trigger Creative Analysis if Ads Intel also has data
            if total > 0:
                try:
                    from research.creative_analysis.service import CreativeAnalysisService
                    ca_service = CreativeAnalysisService(self.db)
                    has_ads = bool(await self.db.research_packs.find_one(
                        {"campaign_id": campaign_id, "sources.ads_intel.latest": {"$exists": True}},
                        {"_id": 0, "campaign_id": 1}
                    ))
                    if has_ads:
                        asyncio.create_task(ca_service.run(campaign_id))
                        logger.info(f"[SOCIAL] Auto-triggered Creative Analysis for campaign {campaign_id}")
                    else:
                        logger.info("[SOCIAL] Ads Intel not ready yet, Creative Analysis deferred")
                except Exception as ca_err:
                    logger.warning(f"[SOCIAL] Creative Analysis auto-trigger failed: {ca_err}")

            return {
                "status": status,
                "snapshot": snapshot.model_dump(mode="json"),
                "message": f"Shortlisted {ig_count} IG + {tt_count} TT posts, {len(trending_audio)} trending audio tracks",
            }

        except Exception as e:
            logger.exception(f"[SOCIAL] Pipeline error: {e}")
            return {
                "status": "failed",
                "snapshot": None,
                "message": str(e),
            }

    def _build_snapshot(
        self,
        inputs: Dict[str, Any],
        brand_handles: List[SocialHandle],
        competitor_handles: List[Dict[str, Any]],
        query_plan: Dict[str, Any],
        bc_data: Dict[str, List],
        cat_data: Dict[str, List],
        ig_shortlist: List[Dict],
        tt_shortlist: List[Dict],
        trending_audio: List[Dict],
        budget: BudgetTracker,
    ) -> SocialTrendsSnapshot:
        """Build the validated snapshot."""
        now = datetime.now(timezone.utc)

        def _to_trend_items(items: List[Dict]) -> List[TrendItem]:
            result = []
            for i in items:
                metrics = i.get("metrics", {})
                score_data = i.get("score", {})
                result.append(TrendItem(
                    platform=i.get("platform", "instagram"),
                    lens=i.get("lens", "category_trends"),
                    query_type=i.get("query_type"),
                    content_label=i.get("content_label"),
                    source_query=i.get("source_query", ""),
                    author_handle=i.get("author_handle", ""),
                    author_follower_count=i.get("author_follower_count"),
                    author_verified=i.get("author_verified"),
                    post_url=i.get("post_url", ""),
                    thumb_url=i.get("thumb_url"),
                    media_url=i.get("media_url"),
                    media_type=i.get("media_type"),
                    caption=i.get("caption"),
                    posted_at=i.get("posted_at"),
                    duration=i.get("duration"),
                    hashtags=i.get("hashtags", [])[:10],
                    metrics=PostMetrics(
                        views=metrics.get("views"),
                        likes=metrics.get("likes", 0),
                        comments=metrics.get("comments", 0),
                        shares=metrics.get("shares"),
                        saves=metrics.get("saves"),
                    ),
                    score=TrendScore(
                        trend_score=score_data.get("trend_score", 0),
                        engagement_rate=score_data.get("engagement_rate"),
                        recency_score=score_data.get("recency_score", 0),
                        save_rate=score_data.get("save_rate"),
                        overperformance_ratio=score_data.get("overperformance_ratio"),
                    ),
                    music_title=i.get("music_title"),
                    music_author=i.get("music_author"),
                ))
            return result

        # Build lens data
        bc_ig_set = SocialTrendSet(
            items=_to_trend_items(bc_data["instagram"]),
            total_raw_fetched=len(bc_data["instagram"]),
            queries_used=[f"@{h.handle}" for h in brand_handles if h.platform == "instagram"],
        )
        bc_tt_set = SocialTrendSet(
            items=_to_trend_items(bc_data["tiktok"]),
            total_raw_fetched=len(bc_data["tiktok"]),
            queries_used=[f"@{h.handle}" for h in brand_handles if h.platform == "tiktok"],
        )
        cat_ig_set = SocialTrendSet(
            items=_to_trend_items(cat_data["instagram"]),
            total_raw_fetched=len(cat_data["instagram"]),
            queries_used=query_plan.get("ig_hashtags", []),
        )
        cat_tt_set = SocialTrendSet(
            items=_to_trend_items(cat_data["tiktok"]),
            total_raw_fetched=len(cat_data["tiktok"]),
            queries_used=[q["label"] for q in query_plan.get("sql_queries", [])],
        )

        # Audit
        budget_summary = budget.summary()
        audit = SocialTrendsAudit(
            raw_records_fetched=budget_summary["total_records"],
            by_source_query_counts=budget_summary["by_source_query_counts"],
            shofo_cost_estimate=budget_summary["cost_estimate"],
            request_ids=budget_summary["request_ids"],
            handles_discovered=len(brand_handles) + sum(len(c.get("handles", [])) for c in competitor_handles),
            handle_sources=[h.source for h in brand_handles],
            ig_hashtags_queried=len(query_plan.get("ig_hashtags", [])),
            tiktok_queries_run=len(query_plan.get("sql_queries", [])),
            shortlist_ig_count=len(ig_shortlist),
            shortlist_tiktok_count=len(tt_shortlist),
            scoring_config=WEIGHTS,
        )

        # Inputs used
        inputs_used = SocialTrendsInputs(
            geo=inputs["geo"],
            brand_name=inputs["brand_name"],
            domain=inputs["domain"],
            subcategory=inputs["subcategory"],
            niche=inputs["niche"],
            industry=inputs["industry"],
            services=inputs["services"],
            tags=inputs["tags"],
            competitors_used=[c["name"] for c in competitor_handles],
        )

        # Handles
        handle_set = HandleSet(
            brand=[h for h in brand_handles],
            competitors=competitor_handles,
        )

        # Trending audio
        audio_items = [TrendingAudio(**a) for a in trending_audio]

        return SocialTrendsSnapshot(
            version="2.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            window_days=WINDOW_DAYS,
            inputs_used=inputs_used,
            handles=handle_set,
            lenses={
                "brand_competitors": {"instagram": bc_ig_set, "tiktok": bc_tt_set},
                "category_trends": {"instagram": cat_ig_set, "tiktok": cat_tt_set},
            },
            shortlist={
                "instagram": _to_trend_items(ig_shortlist),
                "tiktok": _to_trend_items(tt_shortlist),
            },
            trending_audio=audio_items,
            audit=audit,
            delta=SocialTrendsDelta(),
        )

    def _compute_delta(
        self, old: SocialTrendsSnapshot, new: SocialTrendsSnapshot
    ) -> SocialTrendsDelta:
        """Compute changes between snapshots."""
        old_urls = set()
        for platform_items in old.shortlist.values():
            for item in platform_items:
                if item.post_url:
                    old_urls.add(item.post_url)

        new_urls = set()
        notable_new = []
        for platform_items in new.shortlist.values():
            for item in platform_items:
                if item.post_url:
                    new_urls.add(item.post_url)
                    if item.post_url not in old_urls and item.score.trend_score > 0.5:
                        notable_new.append(item.post_url)

        return SocialTrendsDelta(
            previous_captured_at=old.captured_at,
            new_items_count=len(new_urls - old_urls),
            dropped_items_count=len(old_urls - new_urls),
            notable_new_items=notable_new[:5],
        )

    async def get_latest(self, campaign_id: str) -> Optional[SocialTrendsSnapshot]:
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.social_trends.latest": 1},
        )
        if not pack:
            return None
        latest = pack.get("sources", {}).get("social_trends", {}).get("latest")
        if not latest:
            return None
        try:
            return SocialTrendsSnapshot(**latest)
        except Exception as e:
            logger.warning(f"[SOCIAL] Failed to parse snapshot: {e}")
            return None

    async def save_snapshot(self, campaign_id: str, snapshot: SocialTrendsSnapshot):
        snapshot_dict = snapshot.model_dump(mode="json")
        now = datetime.now(timezone.utc)

        existing = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "campaign_id": 1},
        )

        if not existing:
            await self.db.research_packs.insert_one({
                "research_pack_id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "sources": {
                    "social_trends": {"latest": snapshot_dict, "history": []},
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            })
        else:
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                {
                    "$set": {
                        "sources.social_trends.latest": snapshot_dict,
                        "updated_at": now.isoformat(),
                    },
                    "$push": {
                        "sources.social_trends.history": {
                            "$each": [snapshot_dict],
                            "$position": 0,
                            "$slice": HISTORY_CAP,
                        }
                    },
                },
            )
        logger.info(f"[SOCIAL] Saved snapshot for campaign {campaign_id}")

    async def get_history(self, campaign_id: str) -> List[SocialTrendsSnapshot]:
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.social_trends.history": 1},
        )
        if not pack:
            return []
        history = pack.get("sources", {}).get("social_trends", {}).get("history", [])
        snapshots = []
        for item in history:
            try:
                snapshots.append(SocialTrendsSnapshot(**item))
            except Exception as e:
                logger.warning(f"[SOCIAL] Failed to parse history: {e}")
        return snapshots
