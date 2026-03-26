"""
Novara Creative Analysis: Service Orchestrator
Gathers ads from Ads Intel + posts from Social Trends,
dispatches multimodal analysis, aggregates patterns, saves snapshot.
"""

import logging
import uuid
import asyncio
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    CreativeAnalysisSnapshot, PatternSummary,
    AdCreativeAnalysis, TikTokCreativeAnalysis,
)
from .analyzer import analyze_batch
from .media_cache import cache_tiktok_videos

logger = logging.getLogger(__name__)

REFRESH_DAYS = 14
HISTORY_CAP = 5
TOP_TIKTOK_COUNT = 15
MAX_CONCURRENT_ANALYSIS = 5


class CreativeAnalysisService:
    def __init__(self, db):
        self.db = db

    async def _gather_ads(self, campaign_id: str) -> List[dict]:
        """Get scored ads from the latest Ads Intel snapshot."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.ads_intel.latest": 1},
        )
        if not pack:
            return []

        latest = pack.get("sources", {}).get("ads_intel", {}).get("latest")
        if not latest:
            return []

        ads = []
        for lens_key in ("competitor_winners", "category_winners"):
            lens_data = latest.get(lens_key, {})
            for ad in lens_data.get("ads", []):
                if ad.get("media_url") or ad.get("thumbnail_url"):
                    ads.append(ad)

        # Sort by score descending (analyze best ads first)
        ads.sort(key=lambda a: a.get("score", 0), reverse=True)
        return ads

    async def _gather_tiktok_posts(self, campaign_id: str) -> List[dict]:
        """Get top TikTok posts by save_rate from Social Trends snapshot."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.social_trends.latest": 1},
        )
        if not pack:
            return []

        latest = pack.get("sources", {}).get("social_trends", {}).get("latest")
        if not latest:
            return []

        shortlist = latest.get("shortlist", {})
        tiktok_posts = shortlist.get("tiktok", [])

        # Sort by save_rate descending, take top N
        def _save_rate(p):
            score = p.get("score", {})
            return score.get("save_rate", 0) if isinstance(score, dict) else 0

        tiktok_posts.sort(key=_save_rate, reverse=True)
        return tiktok_posts[:TOP_TIKTOK_COUNT]

    def _build_pattern_summary(
        self,
        ad_analyses: List[AdCreativeAnalysis],
        tt_analyses: List[TikTokCreativeAnalysis],
    ) -> PatternSummary:
        """Aggregate patterns from all analyses."""
        # Count ad-level patterns
        hook_types = Counter()
        msg_structures = Counter()
        visual_styles = Counter()
        tones = Counter()
        all_proof = Counter()
        personas = []
        insights = []
        frameworks = []
        format_notes = []

        for a in ad_analyses:
            if a.error:
                continue
            c = a.core
            if c.hook_type:
                hook_types[c.hook_type] += 1
            if c.messaging_structure:
                msg_structures[c.messaging_structure] += 1
            if c.visual_style:
                visual_styles[c.visual_style] += 1
            if c.tone:
                tones[c.tone] += 1
            for p in c.proof_elements:
                all_proof[p] += 1
            if c.implied_target_persona:
                personas.append(c.implied_target_persona)
            if c.key_insight:
                insights.append(c.key_insight)
            if c.replicable_framework:
                frameworks.append(c.replicable_framework)

        # TikTok patterns
        tt_formats = Counter()
        for t in tt_analyses:
            if t.error:
                continue
            if t.analysis.content_format:
                tt_formats[t.analysis.content_format] += 1
            if t.key_insight:
                insights.append(t.key_insight)
            if t.analysis.replicable_framework:
                frameworks.append(t.analysis.replicable_framework)

        # Format distribution insights
        video_count = sum(1 for a in ad_analyses if a.display_format == "video" and not a.error)
        image_count = sum(1 for a in ad_analyses if a.display_format == "image" and not a.error)
        total_ads = video_count + image_count
        if total_ads > 0:
            if video_count > image_count:
                format_notes.append(f"Video ads dominate ({video_count}/{total_ads} analyzed ads)")
            elif image_count > video_count:
                format_notes.append(f"Static image ads dominate ({image_count}/{total_ads} analyzed ads)")

        if tt_formats:
            top_tt_fmt = tt_formats.most_common(1)[0]
            format_notes.append(f"Top TikTok format: {top_tt_fmt[0]} ({top_tt_fmt[1]} posts)")

        def _to_ranked(counter: Counter, top_n: int = 5) -> List[Dict[str, Any]]:
            return [{"value": k, "count": v} for k, v in counter.most_common(top_n)]

        return PatternSummary(
            dominant_hook_types=_to_ranked(hook_types),
            dominant_messaging_structures=_to_ranked(msg_structures),
            dominant_visual_styles=_to_ranked(visual_styles),
            dominant_tones=_to_ranked(tones),
            common_proof_elements=[p for p, _ in all_proof.most_common(8)],
            persona_patterns=personas[:6],
            format_insights=format_notes,
            top_key_insights=insights[:10],
            top_replicable_frameworks=frameworks[:10],
        )

    async def run(self, campaign_id: str) -> Dict[str, Any]:
        """Full Creative Analysis pipeline."""
        logger.info(f"[CREATIVE_ANALYSIS] Starting for campaign {campaign_id}")
        start_time = datetime.now(timezone.utc)

        # 1. Gather inputs in parallel
        ads, tiktok_posts = await asyncio.gather(
            self._gather_ads(campaign_id),
            self._gather_tiktok_posts(campaign_id),
        )

        logger.info(f"[CREATIVE_ANALYSIS] Gathered {len(ads)} ads + {len(tiktok_posts)} TikTok posts")

        if not ads and not tiktok_posts:
            return {
                "status": "no_data",
                "snapshot": None,
                "message": "No ads or TikTok posts available. Run Ads Intel and Social Trends first.",
            }

        # 2. Pre-cache TikTok videos (in case they weren't cached during Social Trends)
        if tiktok_posts:
            tt_dicts = [{"post_url": p.get("post_url", ""), "media_url": p.get("media_url")} for p in tiktok_posts]
            await cache_tiktok_videos(tt_dicts, max_concurrent=8)

        # 3. Run parallel analysis
        ad_analyses, tt_analyses = await analyze_batch(
            ads=ads,
            tiktok_posts=tiktok_posts,
            max_concurrent=MAX_CONCURRENT_ANALYSIS,
        )

        # 4. Build pattern summary
        pattern_summary = self._build_pattern_summary(ad_analyses, tt_analyses)

        # 5. Build audit
        ad_success = sum(1 for a in ad_analyses if not a.error)
        tt_success = sum(1 for t in tt_analyses if not t.error)
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

        audit = {
            "ads_analyzed": len(ad_analyses),
            "ads_succeeded": ad_success,
            "ads_failed": len(ad_analyses) - ad_success,
            "tiktok_analyzed": len(tt_analyses),
            "tiktok_succeeded": tt_success,
            "tiktok_failed": len(tt_analyses) - tt_success,
            "total_time_seconds": round(elapsed, 1),
            "depth_distribution": {
                "full": sum(1 for a in ad_analyses if a.analysis_depth == "full"),
                "standard": sum(1 for a in ad_analyses if a.analysis_depth == "standard"),
                "basic": sum(1 for a in ad_analyses if a.analysis_depth == "basic"),
            },
        }

        # 6. Determine status
        total = ad_success + tt_success
        if total == 0:
            status = "failed"
        elif total < (len(ads) + len(tiktok_posts)) * 0.5:
            status = "partial"
        else:
            status = "success"

        # 7. Build snapshot
        now = datetime.now(timezone.utc)
        snapshot = CreativeAnalysisSnapshot(
            version="1.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            ad_analyses=ad_analyses,
            tiktok_analyses=tt_analyses,
            pattern_summary=pattern_summary,
            audit=audit,
            status=status,
        )

        # 8. Save
        await self._save_snapshot(campaign_id, snapshot)

        logger.info(
            f"[CREATIVE_ANALYSIS] Complete: {ad_success}/{len(ad_analyses)} ads + "
            f"{tt_success}/{len(tt_analyses)} TikTok in {elapsed:.1f}s"
        )

        return {
            "status": status,
            "snapshot": snapshot.model_dump(mode="json"),
            "message": f"Analyzed {ad_success} ads + {tt_success} TikTok posts in {elapsed:.1f}s",
        }

    # ============== PERSISTENCE ==============

    async def get_latest(self, campaign_id: str) -> Optional[CreativeAnalysisSnapshot]:
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.creative_analysis.latest": 1},
        )
        if not pack:
            return None
        latest = pack.get("sources", {}).get("creative_analysis", {}).get("latest")
        if not latest:
            return None
        try:
            return CreativeAnalysisSnapshot(**latest)
        except Exception as e:
            logger.warning(f"[CREATIVE_ANALYSIS] Failed to parse snapshot: {e}")
            return None

    async def get_history(self, campaign_id: str) -> List[CreativeAnalysisSnapshot]:
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.creative_analysis.history": 1},
        )
        if not pack:
            return []
        history = pack.get("sources", {}).get("creative_analysis", {}).get("history", [])
        results = []
        for item in history:
            try:
                results.append(CreativeAnalysisSnapshot(**item))
            except Exception:
                pass
        return results

    async def _save_snapshot(self, campaign_id: str, snapshot: CreativeAnalysisSnapshot):
        snapshot_dict = snapshot.model_dump(mode="json")
        now = datetime.now(timezone.utc).isoformat()

        existing = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "campaign_id": 1},
        )

        if not existing:
            await self.db.research_packs.insert_one({
                "research_pack_id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "sources": {
                    "creative_analysis": {"latest": snapshot_dict, "history": []},
                },
                "created_at": now,
                "updated_at": now,
            })
        else:
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                {
                    "$set": {
                        "sources.creative_analysis.latest": snapshot_dict,
                        "updated_at": now,
                    },
                    "$push": {
                        "sources.creative_analysis.history": {
                            "$each": [snapshot_dict],
                            "$position": 0,
                            "$slice": HISTORY_CAP,
                        }
                    },
                },
            )
        logger.info(f"[CREATIVE_ANALYSIS] Saved snapshot for campaign {campaign_id}")
