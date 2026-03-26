"""
Novara Research Foundation: Community Intelligence Service
Version 1.0 - Feb 2026

Orchestrates:
1. Gather inputs (Step 1 + Step 2 + optional modules)
2. Build query plan (5 families)
3. Call Perplexity (Discovery — find threads)
4. Call Perplexity (Synthesis — extract themes + language)
5. Post-process + validate
6. Build snapshot + save
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    CommunitySnapshot,
    CommunityDelta,
    CommunityAudit,
    CommunityInputs,
    CommunityThread,
    CommunityTheme,
    CommunityLanguageBank,
)
from .query_builder import build_query_plan
from .perplexity_community import (
    PERPLEXITY_MODEL,
    fetch_community_discovery,
    fetch_community_synthesis,
)
from .postprocess import postprocess_community

logger = logging.getLogger(__name__)

REFRESH_DAYS = 30
HISTORY_CAP = 10


class CommunityService:
    def __init__(self, db):
        self.db = db

    def extract_inputs(
        self,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract inputs for community pipeline."""

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
        """Get optional context from other modules (customer intel pains, review weaknesses)."""
        context = {}

        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0,
             "sources.customer_intel.latest.segments": 1,
             "sources.reviews.latest.weakness_themes": 1,
             "sources.competitors.latest.competitors": 1}
        )
        if not pack:
            return context

        sources = pack.get("sources", {})

        # Extract pains from customer intel segments
        ci_latest = sources.get("customer_intel", {}).get("latest", {})
        segments = ci_latest.get("segments", [])
        pains = []
        for seg in segments[:3]:
            triggers = seg.get("trigger_map", {}).get("moment_triggers", [])
            pains.extend(triggers[:2])
        if pains:
            context["pains"] = pains[:5]

        # Extract weakness themes from reviews
        rev_latest = sources.get("reviews", {}).get("latest", {})
        weaknesses = rev_latest.get("weakness_themes", [])
        if weaknesses:
            context["review_weaknesses"] = [w.get("theme", "") for w in weaknesses[:5] if w.get("theme")]

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
        """Full pipeline: query plan -> discovery -> synthesis -> postprocess -> save."""

        try:
            logger.info(f"[COMMUNITY] Starting v1.0 pipeline for campaign {campaign_id}")

            # 1. Extract inputs
            inputs = self.extract_inputs(campaign_brief, website_context_pack)
            city = inputs["geo"]["city"]
            country = inputs["geo"]["country"]

            logger.info(f"[COMMUNITY] Brand: {inputs['brand_name']}, Location: {city or country}")

            # 2. Get optional context from other modules
            optional_context = await self._get_optional_context(campaign_id)
            competitor_names = optional_context.get("competitor_names", [])
            pains = optional_context.get("pains", [])

            modules_used = []
            if competitor_names:
                modules_used.append("competitors")
            if optional_context.get("pains"):
                modules_used.append("customer_intel")
            if optional_context.get("review_weaknesses"):
                modules_used.append("reviews")

            logger.info(f"[COMMUNITY] Optional context from: {modules_used}")

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
                pains_from_intel=pains,
            )

            logger.info(f"[COMMUNITY] Query plan: {query_plan['total_queries']} queries across {len(query_plan['families'])} families")

            # 4. Call 1: Discovery
            discovery_result = await fetch_community_discovery(
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
                raise RuntimeError("Community discovery call failed — no response from Perplexity")

            discovery_tokens = discovery_result.pop("_tokens", 0)
            threads_found = discovery_result.get("threads", [])
            logger.info(f"[COMMUNITY] Discovery found {len(threads_found)} threads")

            # 4a. Pre-filter threads to check if we have enough valid forum threads
            from .postprocess import _is_excluded_domain, _is_forum_domain
            valid_forum_threads = [
                t for t in threads_found
                if not _is_excluded_domain(t.get("url", ""), inputs["domain"])
                and _is_forum_domain(t.get("url", ""))
            ]
            logger.info(f"[COMMUNITY] Valid forum threads after pre-filter: {len(valid_forum_threads)}")

            # 4b. Fallback: if 0 threads, retry with broader category-level queries
            if len(valid_forum_threads) == 0:
                logger.info("[COMMUNITY] 0 threads found, retrying with broader category search...")
                broad_plan = build_query_plan(
                    brand_name="",
                    domain="",
                    city=city,
                    country=country,
                    subcategory=inputs["subcategory"],
                    niche=inputs["niche"],
                    services=inputs["services"],
                    competitor_names=competitor_names,
                    pains_from_intel=pains,
                )
                broad_result = await fetch_community_discovery(
                    brand_name=inputs["brand_name"],
                    domain=inputs["domain"],
                    city=city,
                    country=country,
                    subcategory=inputs["subcategory"],
                    niche=inputs["niche"],
                    services=inputs["services"],
                    brand_overview=inputs["brand_overview"],
                    query_plan=broad_plan,
                    broad_search=True,
                )
                if broad_result:
                    broad_tokens = broad_result.pop("_tokens", 0)
                    discovery_tokens += broad_tokens
                    broad_threads = broad_result.get("threads", [])
                    valid_broad = [
                        t for t in broad_threads
                        if not _is_excluded_domain(t.get("url", ""), inputs["domain"])
                        and _is_forum_domain(t.get("url", ""))
                    ]
                    if valid_broad:
                        logger.info(f"[COMMUNITY] Broad search found {len(valid_broad)} threads")
                        valid_forum_threads = valid_broad
                        discovery_result["threads"] = broad_threads

            # 5. Call 2: Synthesis — run if we have at least 1 valid forum thread
            synthesis_result = {}
            synthesis_tokens = 0

            if len(valid_forum_threads) >= 1:
                synthesis_response = await fetch_community_synthesis(
                    brand_name=inputs["brand_name"],
                    domain=inputs["domain"],
                    city=city,
                    country=country,
                    subcategory=inputs["subcategory"],
                    niche=inputs["niche"],
                    services=inputs["services"],
                    brand_overview=inputs["brand_overview"],
                    threads=valid_forum_threads,
                    optional_context=optional_context if optional_context else None,
                )

                if synthesis_response:
                    synthesis_tokens = synthesis_response.pop("_tokens", 0)
                    synthesis_result = synthesis_response
                else:
                    logger.warning("[COMMUNITY] Synthesis call failed, proceeding with threads only")
            else:
                logger.info(f"[COMMUNITY] Skipping synthesis — only {len(valid_forum_threads)} valid forum threads (need >= 1)")

            # 6. Post-process (with brand_domain for exclusion)
            processed, pp_stats = postprocess_community(
                discovery_result,
                synthesis_result,
                brand_domain=inputs["domain"],
            )

            # 7. Build snapshot
            snapshot = self._build_snapshot(
                processed=processed,
                inputs=inputs,
                query_plan=query_plan,
                modules_used=modules_used,
                discovery_tokens=discovery_tokens,
                synthesis_tokens=synthesis_tokens,
                pp_stats=pp_stats,
            )

            # 8. Compute delta
            previous = await self.get_latest(campaign_id)
            if previous:
                snapshot.delta = self._compute_delta(previous, snapshot)

            # 9. Save
            await self.save_snapshot(campaign_id, snapshot)

            thread_count = len(snapshot.threads)
            theme_count = len(snapshot.themes)
            domain_count = len(pp_stats.get("domains_found", []))

            if thread_count >= 5 and theme_count >= 3:
                status = "success"
            elif thread_count >= 1 or theme_count >= 1:
                status = "partial"
            else:
                status = "low_data"

            logger.info(
                f"[COMMUNITY] Pipeline complete: {thread_count} threads from {domain_count} domains, "
                f"{theme_count} themes, status={status}"
            )

            return {
                "status": status,
                "snapshot": snapshot.model_dump(mode="json"),
                "message": f"Found {thread_count} threads from {domain_count} domains, {theme_count} themes"
            }

        except Exception as e:
            logger.exception(f"[COMMUNITY] Pipeline error: {e}")
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
        synthesis_tokens: int,
        pp_stats: Dict[str, Any],
    ) -> CommunitySnapshot:
        """Build validated snapshot from processed data."""
        now = datetime.now(timezone.utc)

        threads = [
            CommunityThread(**t) for t in processed.get("threads", [])
        ]

        themes = [
            CommunityTheme(**th) for th in processed.get("themes", [])
        ]

        lb_data = processed.get("language_bank", {})
        language_bank = CommunityLanguageBank(
            phrases=lb_data.get("phrases", []),
            words=lb_data.get("words", []),
        )

        audit = CommunityAudit(
            queries_generated=query_plan.get("total_queries", 0),
            query_families_used=query_plan.get("families", []),
            threads_discovered=pp_stats.get("threads_raw", 0),
            threads_after_dedup=pp_stats.get("threads_kept", 0),
            domains_found=pp_stats.get("domains_found", []),
            themes_raw=pp_stats.get("themes_raw", 0),
            themes_kept=pp_stats.get("themes_kept", 0),
            discovery_model=PERPLEXITY_MODEL,
            synthesis_model=PERPLEXITY_MODEL,
            discovery_tokens=discovery_tokens,
            synthesis_tokens=synthesis_tokens,
            postprocess_stats=pp_stats,
        )

        inputs_used = CommunityInputs(
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

        # Compact query plan for storage (don't store full query list)
        compact_plan = {
            "total_queries": query_plan.get("total_queries", 0),
            "families": query_plan.get("families", []),
            "target_domains": query_plan.get("target_domains", []),
        }

        return CommunitySnapshot(
            version="1.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs_used=inputs_used,
            query_plan=compact_plan,
            threads=threads,
            themes=themes,
            language_bank=language_bank,
            audience_notes=processed.get("audience_notes", []),
            creative_implications=processed.get("creative_implications", []),
            gaps_to_research=processed.get("gaps_to_research", []),
            audit=audit,
            delta=CommunityDelta(),
        )

    def _compute_delta(self, old: CommunitySnapshot, new: CommunitySnapshot) -> CommunityDelta:
        """Compute changes between snapshots."""
        old_domains = set(t.domain for t in old.threads if t.domain)
        new_domains = set(t.domain for t in new.threads if t.domain)
        new_domain_list = sorted(list(new_domains - old_domains))

        old_labels = {th.label for th in old.themes}
        new_labels = {th.label for th in new.themes}

        return CommunityDelta(
            previous_captured_at=old.captured_at,
            new_domains=new_domain_list[:5],
            new_threads_count=max(0, len(new.threads) - len(old.threads)),
            new_theme_labels=sorted(list(new_labels - old_labels))[:5],
            removed_theme_labels=sorted(list(old_labels - new_labels))[:5],
        )

    async def get_latest(self, campaign_id: str) -> Optional[CommunitySnapshot]:
        """Get latest Community snapshot."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.community.latest": 1}
        )
        if not pack:
            return None

        latest = pack.get("sources", {}).get("community", {}).get("latest")
        if not latest:
            return None

        try:
            return CommunitySnapshot(**latest)
        except Exception as e:
            logger.warning(f"[COMMUNITY] Failed to parse snapshot: {e}")
            return None

    async def save_snapshot(self, campaign_id: str, snapshot: CommunitySnapshot):
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
                    "community": {"latest": snapshot_dict, "history": []},
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
                        "sources.community.latest": snapshot_dict,
                        "updated_at": now.isoformat()
                    },
                    "$push": {
                        "sources.community.history": {
                            "$each": [snapshot_dict],
                            "$position": 0,
                            "$slice": HISTORY_CAP
                        }
                    }
                }
            )

        logger.info(f"[COMMUNITY] Saved snapshot for campaign {campaign_id}")

    async def get_history(self, campaign_id: str) -> List[CommunitySnapshot]:
        """Get Community history."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.community.history": 1}
        )
        if not pack:
            return []

        history = pack.get("sources", {}).get("community", {}).get("history", [])
        snapshots = []
        for item in history:
            try:
                snapshots.append(CommunitySnapshot(**item))
            except Exception as e:
                logger.warning(f"[COMMUNITY] Failed to parse history snapshot: {e}")
        return snapshots
