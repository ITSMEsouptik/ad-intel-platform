"""
Novara Research Foundation: Press & Media Intelligence Service
Version 1.0 - Feb 2026

Orchestrates:
1. Gather inputs (Step 1 + Step 2 + optional modules)
2. Build query plan (5 families)
3. Call Perplexity (Discovery — find articles)
4. Call Perplexity (Analysis — extract narratives + quotes)
5. Post-process + validate
6. Build snapshot + save
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    PressMediaSnapshot,
    PressMediaDelta,
    PressMediaAudit,
    PressMediaInputs,
    PressArticle,
    MediaNarrative,
    PressQuote,
    MediaSource,
)
from .query_builder import build_query_plan
from .perplexity_press import (
    PERPLEXITY_MODEL,
    fetch_press_discovery,
    fetch_press_analysis,
)
from .postprocess import postprocess_press_media

logger = logging.getLogger(__name__)

REFRESH_DAYS = 30
HISTORY_CAP = 10


class PressMediaService:
    def __init__(self, db):
        self.db = db

    def extract_inputs(
        self,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract inputs for press/media pipeline."""

        geo = campaign_brief.get("geo", {})
        city = geo.get("city_or_region", "")
        country = geo.get("country", "")

        step2 = website_context_pack.get("step2", {})
        site = step2.get("site", {})
        classification = step2.get("classification", {})
        offer = step2.get("offer", {})
        brand_summary = step2.get("brand_summary", {})

        domain = site.get("domain", site.get("final_url", ""))
        subcategory = classification.get("subcategory", "")
        niche = classification.get("niche", "")
        brand_name = brand_summary.get("name", "")
        one_liner = brand_summary.get("one_liner", "")
        tagline = brand_summary.get("tagline", "")
        bullets = brand_summary.get("bullets", [])

        parts = []
        if one_liner and one_liner != "unknown":
            parts.append(one_liner)
        if tagline and tagline != "unknown":
            parts.append(tagline)
        if bullets:
            parts.extend(bullets[:2])
        brand_overview = " | ".join(parts)[:300] if parts else ""

        services = []
        for item in offer.get("offer_catalog", [])[:6]:
            name = item.get("name", "")
            if name and name.lower() != "unknown":
                services.append(name)

        return {
            "geo": {"city": city, "country": country},
            "brand_name": brand_name,
            "domain": domain,
            "subcategory": subcategory,
            "niche": niche,
            "services": services,
            "brand_overview": brand_overview,
        }

    async def _get_optional_context(self, campaign_id: str) -> Dict[str, Any]:
        """Get optional context from other modules (review strengths/weaknesses, competitor names)."""
        context = {}

        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0,
             "sources.reviews.latest.strength_themes": 1,
             "sources.reviews.latest.weakness_themes": 1,
             "sources.competitors.latest.competitors": 1}
        )
        if not pack:
            return context

        sources = pack.get("sources", {})

        # Extract strength/weakness themes from reviews
        rev_latest = sources.get("reviews", {}).get("latest", {})
        strengths = rev_latest.get("strength_themes", [])
        if strengths:
            context["review_strengths"] = [s.get("theme", "") for s in strengths[:3] if s.get("theme")]
        weaknesses = rev_latest.get("weakness_themes", [])
        if weaknesses:
            context["review_weaknesses"] = [w.get("theme", "") for w in weaknesses[:3] if w.get("theme")]

        # Extract competitor names
        comp_latest = sources.get("competitors", {}).get("latest", {})
        competitors = comp_latest.get("competitors", [])
        if competitors:
            context["competitor_names"] = [c.get("name", "") for c in competitors[:3] if c.get("name")]

        return context

    async def run(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Full pipeline: query plan -> discovery -> analysis -> postprocess -> save."""

        try:
            logger.info(f"[PRESS] Starting v1.0 pipeline for campaign {campaign_id}")

            # 1. Extract inputs
            inputs = self.extract_inputs(campaign_brief, website_context_pack)
            city = inputs["geo"]["city"]
            country = inputs["geo"]["country"]

            logger.info(f"[PRESS] Brand: {inputs['brand_name']}, Location: {city or country}")

            # 2. Get optional context from other modules
            optional_context = await self._get_optional_context(campaign_id)
            competitor_names = optional_context.get("competitor_names", [])

            modules_used = []
            if competitor_names:
                modules_used.append("competitors")
            if optional_context.get("review_strengths") or optional_context.get("review_weaknesses"):
                modules_used.append("reviews")

            logger.info(f"[PRESS] Optional context from: {modules_used}")

            # 3. Build query plan
            query_plan = build_query_plan(
                brand_name=inputs["brand_name"],
                domain=inputs["domain"],
                city=city,
                country=country,
                subcategory=inputs["subcategory"],
                niche=inputs["niche"],
                services=inputs["services"],
                competitor_names=competitor_names,
            )

            logger.info(f"[PRESS] Query plan: {query_plan['total_queries']} queries across {len(query_plan['families'])} families")

            # 4. Call 1: Discovery
            discovery_result = await fetch_press_discovery(
                brand_name=inputs["brand_name"],
                domain=inputs["domain"],
                city=city,
                country=country,
                subcategory=inputs["subcategory"],
                niche=inputs["niche"],
                services=inputs["services"],
                brand_overview=inputs["brand_overview"],
                query_plan=query_plan,
            )

            if not discovery_result:
                raise RuntimeError("Press discovery call failed — no response from Perplexity")

            discovery_tokens = discovery_result.pop("_tokens", 0)
            articles_found = discovery_result.get("articles", [])
            logger.info(f"[PRESS] Discovery found {len(articles_found)} articles")

            # 5. Call 2: Analysis — SKIP if fewer than 2 articles
            analysis_result = {}
            analysis_tokens = 0

            if len(articles_found) >= 2:
                analysis_response = await fetch_press_analysis(
                    brand_name=inputs["brand_name"],
                    domain=inputs["domain"],
                    city=city,
                    country=country,
                    subcategory=inputs["subcategory"],
                    niche=inputs["niche"],
                    services=inputs["services"],
                    brand_overview=inputs["brand_overview"],
                    articles=articles_found,
                    optional_context=optional_context if optional_context else None,
                )

                if analysis_response:
                    analysis_tokens = analysis_response.pop("_tokens", 0)
                    analysis_result = analysis_response
                else:
                    logger.warning("[PRESS] Analysis call failed, proceeding with articles only")
            else:
                logger.info(f"[PRESS] Skipping analysis — only {len(articles_found)} articles (need >= 2)")

            # 6. Post-process
            processed, pp_stats = postprocess_press_media(
                discovery_result,
                analysis_result,
                brand_domain=inputs["domain"],
            )

            # 7. Build snapshot
            snapshot = self._build_snapshot(
                processed=processed,
                inputs=inputs,
                query_plan=query_plan,
                modules_used=modules_used,
                discovery_tokens=discovery_tokens,
                analysis_tokens=analysis_tokens,
                pp_stats=pp_stats,
            )

            # 8. Compute delta
            previous = await self.get_latest(campaign_id)
            if previous:
                snapshot.delta = self._compute_delta(previous, snapshot)

            # 9. Save
            await self.save_snapshot(campaign_id, snapshot)

            article_count = len(snapshot.articles)
            narrative_count = len(snapshot.narratives)
            source_count = len(snapshot.media_sources)

            if article_count >= 5 and narrative_count >= 2:
                status = "success"
            elif article_count >= 1 or narrative_count >= 1:
                status = "partial"
            else:
                status = "low_data"

            logger.info(
                f"[PRESS] Pipeline complete: {article_count} articles from {source_count} sources, "
                f"{narrative_count} narratives, status={status}"
            )

            return {
                "status": status,
                "snapshot": snapshot.model_dump(mode="json"),
                "message": f"Found {article_count} articles from {source_count} sources, {narrative_count} narratives"
            }

        except Exception as e:
            logger.exception(f"[PRESS] Pipeline error: {e}")
            return {
                "status": "failed",
                "snapshot": None,
                "message": str(e)
            }

    def _build_snapshot(
        self,
        processed: Dict[str, Any],
        inputs: Dict[str, Any],
        query_plan: Dict[str, Any],
        modules_used: List[str],
        discovery_tokens: int,
        analysis_tokens: int,
        pp_stats: Dict[str, Any],
    ) -> PressMediaSnapshot:
        """Build validated snapshot from processed data."""
        now = datetime.now(timezone.utc)

        articles = [PressArticle(**a) for a in processed.get("articles", [])]
        narratives = [MediaNarrative(**n) for n in processed.get("narratives", [])]
        key_quotes = [PressQuote(**q) for q in processed.get("key_quotes", [])]
        media_sources = [MediaSource(**s) for s in processed.get("media_sources", [])]

        audit = PressMediaAudit(
            queries_generated=query_plan.get("total_queries", 0),
            query_families_used=query_plan.get("families", []),
            articles_discovered=pp_stats.get("articles_raw", 0),
            articles_after_filter=pp_stats.get("articles_kept", 0),
            sources_found=pp_stats.get("sources_found", []),
            narratives_raw=pp_stats.get("narratives_raw", 0),
            narratives_kept=pp_stats.get("narratives_kept", 0),
            discovery_model=PERPLEXITY_MODEL,
            analysis_model=PERPLEXITY_MODEL,
            discovery_tokens=discovery_tokens,
            analysis_tokens=analysis_tokens,
            postprocess_stats=pp_stats,
        )

        inputs_used = PressMediaInputs(
            geo=inputs["geo"],
            brand_name=inputs["brand_name"],
            domain=inputs["domain"],
            subcategory=inputs["subcategory"],
            niche=inputs["niche"],
            services=inputs["services"],
            brand_overview=inputs["brand_overview"],
            competitors_used=bool("competitors" in modules_used),
            optional_modules_used=modules_used,
        )

        compact_plan = {
            "total_queries": query_plan.get("total_queries", 0),
            "families": query_plan.get("families", []),
            "target_domains": query_plan.get("target_domains", []),
        }

        return PressMediaSnapshot(
            version="1.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs_used=inputs_used,
            query_plan=compact_plan,
            articles=articles,
            narratives=narratives,
            key_quotes=key_quotes,
            media_sources=media_sources,
            coverage_summary=processed.get("coverage_summary", []),
            coverage_gaps=processed.get("coverage_gaps", []),
            pr_opportunities=processed.get("pr_opportunities", []),
            audit=audit,
            delta=PressMediaDelta(),
        )

    def _compute_delta(self, old: PressMediaSnapshot, new: PressMediaSnapshot) -> PressMediaDelta:
        """Compute changes between snapshots."""
        old_sources = set(s.domain for s in old.media_sources if s.domain)
        new_sources = set(s.domain for s in new.media_sources if s.domain)
        new_source_list = sorted(list(new_sources - old_sources))

        old_labels = {n.label for n in old.narratives}
        new_labels = {n.label for n in new.narratives}

        return PressMediaDelta(
            previous_captured_at=old.captured_at,
            new_sources=new_source_list[:5],
            new_articles_count=max(0, len(new.articles) - len(old.articles)),
            new_narrative_labels=sorted(list(new_labels - old_labels))[:5],
            removed_narrative_labels=sorted(list(old_labels - new_labels))[:5],
        )

    async def get_latest(self, campaign_id: str) -> Optional[PressMediaSnapshot]:
        """Get latest Press & Media snapshot."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.press_media.latest": 1}
        )
        if not pack:
            return None

        latest = pack.get("sources", {}).get("press_media", {}).get("latest")
        if not latest:
            return None

        try:
            return PressMediaSnapshot(**latest)
        except Exception as e:
            logger.warning(f"[PRESS] Failed to parse snapshot: {e}")
            return None

    async def save_snapshot(self, campaign_id: str, snapshot: PressMediaSnapshot):
        """Save snapshot to research_packs."""
        snapshot_dict = snapshot.model_dump(mode="json")

        existing = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "campaign_id": 1}
        )

        now = datetime.now(timezone.utc)

        if not existing:
            import uuid
            await self.db.research_packs.insert_one({
                "research_pack_id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "sources": {
                    "press_media": {"latest": snapshot_dict, "history": []},
                    "community": {"latest": None, "history": []},
                    "customer_intel": {"latest": None, "history": []},
                    "search_intent": {"latest": None, "history": []},
                    "seasonality": {"latest": None, "history": []},
                    "competitors": {"latest": None, "history": []},
                    "reviews": {"latest": None, "history": []},
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            })
        else:
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                {
                    "$set": {
                        "sources.press_media.latest": snapshot_dict,
                        "updated_at": now.isoformat()
                    },
                    "$push": {
                        "sources.press_media.history": {
                            "$each": [snapshot_dict],
                            "$position": 0,
                            "$slice": HISTORY_CAP
                        }
                    }
                }
            )

        logger.info(f"[PRESS] Saved snapshot for campaign {campaign_id}")

    async def get_history(self, campaign_id: str) -> List[PressMediaSnapshot]:
        """Get Press & Media history."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.press_media.history": 1}
        )
        if not pack:
            return []

        history = pack.get("sources", {}).get("press_media", {}).get("history", [])
        snapshots = []
        for item in history:
            try:
                snapshots.append(PressMediaSnapshot(**item))
            except Exception as e:
                logger.warning(f"[PRESS] Failed to parse history snapshot: {e}")
        return snapshots
