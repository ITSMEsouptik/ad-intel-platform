"""
Novara Research Foundation: Seasonality Service
Main orchestrator for building seasonality snapshots

Version 2.1 - Feb 2026
- "Buying Moments" pipeline with post-processing filter
- Updated schema: BuyingMoment replaces KeyMoment
- Audit logging for filter stats
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    SeasonalitySnapshot,
    SeasonalityDelta,
    SeasonalityInputs,
    SeasonalityAudit,
    BuyingMoment,
    WeeklyPatterns
)
from .perplexity_seasonality import call_perplexity_seasonality
from .postprocess import postprocess_moments

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============

REFRESH_DAYS = 30
HISTORY_LIMIT = 10


class SeasonalityService:
    """
    Orchestrates the seasonality v2.1 pipeline:
    1. Extract inputs from Step 1/2
    2. Call Perplexity for buying moments
    3. Post-process: filter generic moments
    4. Parse and structure the response
    5. Compute delta
    6. Save snapshot
    """

    def __init__(self, db):
        self.db = db

    def extract_inputs(
        self,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> SeasonalityInputs:
        """Extract inputs needed for seasonality analysis"""

        # Step 1 inputs
        geo = campaign_brief.get("geo", {})
        city = geo.get("city_or_region", "")
        country = geo.get("country", "")

        # Step 2 inputs — try "step2" schema first, fallback to "data" schema
        step2 = website_context_pack.get("step2", {})

        if step2:
            site = step2.get("site", {})
            classification = step2.get("classification", {})
            offer = step2.get("offer", {})
            brand_summary = step2.get("brand_summary", {})
            pricing = step2.get("pricing", {})
        else:
            data = website_context_pack.get("data", {})
            bi = data.get("brand_identity", {})
            site = data.get("site", {})
            offer = data.get("offer", {})
            pricing = data.get("pricing", {})
            classification = {
                "subcategory": bi.get("category") or bi.get("subcategory") or "",
                "niche": bi.get("niche") or "",
                "industry": bi.get("industry") or "",
            }
            tagline_raw = bi.get("tagline") or ""
            # Don't use tagline if it looks like a domain
            if tagline_raw and tagline_raw.endswith((".com", ".co", ".ae", ".org", ".net")):
                tagline_raw = ""
            brand_summary = {
                "name": bi.get("brand_name") or "",
                "one_liner": bi.get("one_liner_value_prop") or "",
                "tagline": tagline_raw,
                "bullets": [],
            }

        domain = site.get("domain", site.get("final_url", ""))
        subcategory = classification.get("subcategory", "")
        niche = classification.get("niche", "")

        brand_name = brand_summary.get("name", "")
        one_liner = brand_summary.get("one_liner", "")
        tagline = brand_summary.get("tagline", "")
        bullets = brand_summary.get("bullets", [])

        brand_overview_parts = []
        if one_liner and one_liner != "unknown":
            brand_overview_parts.append(one_liner)
        if tagline and tagline != "unknown":
            brand_overview_parts.append(tagline)
        if bullets:
            brand_overview_parts.extend(bullets[:2])
        brand_overview = " | ".join(brand_overview_parts)[:300] if brand_overview_parts else ""

        services = []
        for item in offer.get("offer_catalog", [])[:6]:
            name = item.get("name", "")
            if name and name.lower() != "unknown":
                services.append(name)

        # Fallback: extract service context from primary_offer_summary
        if not services:
            summary = offer.get("primary_offer_summary", "")
            if summary and len(summary) > 10:
                services.append(summary[:200])

        price_range = None
        if pricing.get("count", 0) > 0:
            price_range = {
                "currency": pricing.get("currency", ""),
                "min": pricing.get("min", 0),
                "max": pricing.get("max", 0),
                "avg": pricing.get("avg", 0)
            }

        return SeasonalityInputs(
            geo={"city": city, "country": country},
            brand_name=brand_name,
            domain=domain,
            niche=niche,
            subcategory=subcategory,
            services=services,
            brand_overview=brand_overview,
            price_range=price_range
        )

    async def build_snapshot(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> SeasonalitySnapshot:
        """Build a new SeasonalitySnapshot v2.1."""
        logger.info(f"[SEASONALITY] Building v2.1 snapshot for campaign={campaign_id}")

        # 1. EXTRACT INPUTS
        inputs = self.extract_inputs(campaign_brief, website_context_pack)
        city = inputs.geo.get("city", "")
        country = inputs.geo.get("country", "")
        logger.info(f"[SEASONALITY] Inputs: brand={inputs.brand_name}, city={city}, niche={inputs.niche}")

        # 2. CALL PERPLEXITY
        try:
            raw_result = await call_perplexity_seasonality(
                brand_name=inputs.brand_name,
                domain=inputs.domain,
                city=city,
                country=country,
                subcategory=inputs.subcategory,
                niche=inputs.niche,
                services=inputs.services,
                brand_overview=inputs.brand_overview,
                price_range=inputs.price_range
            )
        except Exception as e:
            logger.error(f"[SEASONALITY] Perplexity call failed: {e}")
            return self._empty_snapshot(inputs)

        # 3. POST-PROCESS: filter generic moments
        raw_moments = raw_result.get("key_moments", [])[:10]
        filtered_moments, audit_data = postprocess_moments(raw_moments)

        # 4. PARSE BUYING MOMENTS
        key_moments = []
        for moment_data in filtered_moments[:8]:
            try:
                moment = BuyingMoment(
                    moment=moment_data.get("moment", moment_data.get("name", "Unknown")),
                    window=moment_data.get("window", moment_data.get("time_window", "")),
                    demand=moment_data.get("demand", moment_data.get("demand_level", "medium")),
                    who=moment_data.get("who", "")[:80],
                    why_now=moment_data.get("why_now", moment_data.get("why_people_buy", ""))[:120],
                    buy_triggers=moment_data.get("buy_triggers", moment_data.get("purchase_triggers", []))[:5],
                    must_answer=moment_data.get("must_answer", "")[:100],
                    best_channels=moment_data.get("best_channels", [])[:4],
                    lead_time=moment_data.get("lead_time", "")[:80]
                )
                key_moments.append(moment)
            except Exception as e:
                logger.warning(f"[SEASONALITY] Error parsing moment: {e}")

        # 5. PARSE WEEKLY PATTERNS
        weekly_raw = raw_result.get("weekly_patterns", {})
        if isinstance(weekly_raw, dict):
            weekly_patterns = WeeklyPatterns(
                peak_days=weekly_raw.get("peak_days", []),
                why=weekly_raw.get("why", "")[:100]
            )
        else:
            weekly_patterns = WeeklyPatterns(
                peak_days=[],
                why=str(weekly_raw[0]) if weekly_raw else ""
            )

        # 6. BUILD SNAPSHOT
        now = datetime.now(timezone.utc)

        snapshot = SeasonalitySnapshot(
            version="2.1",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs_used=inputs,
            key_moments=key_moments,
            evergreen_demand=raw_result.get("evergreen_demand", [])[:10],
            weekly_patterns=weekly_patterns,
            local_insights=raw_result.get("local_insights", [])[:5],
            delta=SeasonalityDelta(),
            audit=SeasonalityAudit(**audit_data)
        )

        logger.info(f"[SEASONALITY] v2.1 snapshot: {len(key_moments)} buying moments (filtered {audit_data.get('filtered_count', 0)})")
        return snapshot

    def _empty_snapshot(self, inputs: SeasonalityInputs) -> SeasonalitySnapshot:
        """Create an empty snapshot when no data available"""
        now = datetime.now(timezone.utc)
        return SeasonalitySnapshot(
            version="2.1",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs_used=inputs,
            key_moments=[],
            evergreen_demand=[],
            weekly_patterns=WeeklyPatterns(),
            local_insights=["Unable to generate seasonality data - please try again"],
            delta=SeasonalityDelta()
        )

    def compute_delta(
        self,
        current_snapshot: SeasonalitySnapshot,
        previous_snapshot: Optional[SeasonalitySnapshot]
    ) -> SeasonalityDelta:
        """Compute delta between current and previous snapshot"""
        if not previous_snapshot:
            return SeasonalityDelta(
                previous_captured_at=None,
                new_moments_count=len(current_snapshot.key_moments),
                removed_moments_count=0,
                notable_changes=[f"Initial analysis with {len(current_snapshot.key_moments)} buying moments"]
            )

        current_names = {m.moment for m in current_snapshot.key_moments}
        previous_names = set()
        for m in previous_snapshot.key_moments:
            # Handle both v2.0 (name) and v2.1 (moment) field names
            moment_name = getattr(m, 'moment', None) or getattr(m, 'name', None) or ''
            previous_names.add(moment_name)

        new_moments = current_names - previous_names
        removed_moments = previous_names - current_names

        notable = []
        if new_moments:
            notable.append(f"New: {', '.join(list(new_moments)[:2])}")
        if removed_moments:
            notable.append(f"Removed: {', '.join(list(removed_moments)[:2])}")

        return SeasonalityDelta(
            previous_captured_at=previous_snapshot.captured_at,
            new_moments_count=len(new_moments),
            removed_moments_count=len(removed_moments),
            notable_changes=notable[:5]
        )

    async def get_existing_pack(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get existing research pack for campaign"""
        return await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0}
        )

    async def save_snapshot(
        self,
        campaign_id: str,
        snapshot: SeasonalitySnapshot
    ) -> Dict[str, Any]:
        """Save snapshot to research_packs collection"""
        now = datetime.now(timezone.utc)

        existing = await self.get_existing_pack(campaign_id)

        previous_snapshot = None
        if existing:
            seasonality_source = existing.get("sources", {}).get("seasonality", {})
            latest_data = seasonality_source.get("latest")
            if latest_data:
                try:
                    previous_snapshot = SeasonalitySnapshot(**latest_data)
                except Exception as e:
                    logger.warning(f"Could not parse previous seasonality snapshot: {e}")

        delta = self.compute_delta(snapshot, previous_snapshot)
        snapshot.delta = delta

        snapshot_dict = snapshot.model_dump(mode="json")

        if existing:
            update_ops = {
                "$set": {
                    "sources.seasonality.latest": snapshot_dict,
                    "updated_at": now.isoformat()
                }
            }

            if previous_snapshot:
                previous_dict = previous_snapshot.model_dump(mode="json")
                update_ops["$push"] = {
                    "sources.seasonality.history": {
                        "$each": [previous_dict],
                        "$position": 0,
                        "$slice": HISTORY_LIMIT
                    }
                }

            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                update_ops
            )
            logger.info(f"[SEASONALITY] Updated research pack for campaign={campaign_id}")
        else:
            import uuid
            new_pack = {
                "research_pack_id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "sources": {
                    "seasonality": {
                        "latest": snapshot_dict,
                        "history": []
                    }
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            await self.db.research_packs.insert_one(new_pack)
            logger.info(f"[SEASONALITY] Created new research pack for campaign={campaign_id}")

        return await self.get_existing_pack(campaign_id)

    async def run(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Full pipeline: build snapshot, compute delta, save."""
        try:
            snapshot = await self.build_snapshot(
                campaign_id=campaign_id,
                campaign_brief=campaign_brief,
                website_context_pack=website_context_pack
            )

            pack = await self.save_snapshot(campaign_id, snapshot)

            if len(snapshot.key_moments) >= 3:
                status = "success"
            elif len(snapshot.key_moments) >= 1:
                status = "partial"
            else:
                status = "low_data"

            return {
                "status": status,
                "snapshot": snapshot.model_dump(mode="json"),
                "research_pack": pack,
                "message": f"Generated {len(snapshot.key_moments)} buying moments"
            }

        except Exception as e:
            logger.exception(f"[SEASONALITY] Error running pipeline: {e}")
            return {
                "status": "failed",
                "snapshot": None,
                "research_pack": None,
                "message": str(e)
            }

    async def get_latest(self, campaign_id: str) -> Optional[SeasonalitySnapshot]:
        """Get latest snapshot for campaign"""
        pack = await self.get_existing_pack(campaign_id)
        if not pack:
            return None

        latest_data = pack.get("sources", {}).get("seasonality", {}).get("latest")
        if not latest_data:
            return None

        try:
            return SeasonalitySnapshot(**latest_data)
        except Exception as e:
            logger.warning(f"Could not parse seasonality snapshot: {e}")
            return None

    async def get_history(self, campaign_id: str) -> List[SeasonalitySnapshot]:
        """Get snapshot history for campaign"""
        pack = await self.get_existing_pack(campaign_id)
        if not pack:
            return []

        history_data = pack.get("sources", {}).get("seasonality", {}).get("history", [])

        snapshots = []
        for data in history_data:
            try:
                snapshots.append(SeasonalitySnapshot(**data))
            except Exception as e:
                logger.warning(f"Could not parse history snapshot: {e}")

        return snapshots
