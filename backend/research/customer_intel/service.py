"""
Novara Research Foundation: Customer Intel Service
Version 1.1 - Feb 2026

Orchestrates Customer Intel generation:
1. Gather inputs (Step 1 + Step 2 + optional modules)
2. Call Perplexity sonar with grounded prompt
3. Post-validate + prune fluff + enforce constraints
4. Save snapshot + delta
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    CustomerIntelSnapshot,
    CustomerIntelDelta,
    CustomerIntelAudit,
    SegmentCard,
    TriggerMap,
    LanguageBank,
)
from .perplexity_customer_intel import fetch_customer_intel
from .postprocess import postprocess_customer_intel

logger = logging.getLogger(__name__)

REFRESH_DAYS = 14
HISTORY_CAP = 10


class CustomerIntelService:
    def __init__(self, db):
        self.db = db

    async def run(self, campaign_id: str) -> Dict[str, Any]:
        """
        Run Customer Intel v1.1 pipeline.
        Returns dict with status, snapshot, message.
        """
        logger.info(f"[CUSTOMER_INTEL] Starting v1.1 for campaign {campaign_id}")

        # 1. GATHER INPUTS
        step1, step2, search_demand, seasonality, competitors = await self._gather_inputs(campaign_id)

        if not step1 or not step2:
            raise ValueError("Campaign brief (Step 1) and Business DNA (Step 2) are required")

        # 2. CALL PERPLEXITY (with auto-retry)
        raw_result = await fetch_customer_intel(
            step1=step1,
            step2=step2,
            search_demand=search_demand,
            seasonality=seasonality,
            competitors=competitors
        )

        if not raw_result:
            raise RuntimeError("Customer Intel LLM call failed — no response from Perplexity")

        # 3. POST-PROCESS
        offer_catalog = raw_result.get("_offer_catalog", [])
        search_phrases = raw_result.get("_search_phrases", [])
        missing_inputs = raw_result.get("_missing_inputs", [])
        retry_count = raw_result.get("_retry_count", 0)
        llm_model = raw_result.get("_llm_model", "sonar")
        llm_tokens = raw_result.get("_llm_tokens", 0)

        processed, audit_data = postprocess_customer_intel(
            raw=raw_result,
            offer_catalog=offer_catalog,
            search_phrases=search_phrases
        )

        # 4. BUILD SNAPSHOT
        snapshot = self._build_snapshot(processed, audit_data, missing_inputs, retry_count, llm_model, llm_tokens)

        # 5. COMPUTE DELTA
        previous = await self.get_latest(campaign_id)
        if previous:
            snapshot.delta = self._compute_delta(previous, snapshot)

        # 6. SAVE
        await self.save_snapshot(campaign_id, snapshot)

        segment_count = len(snapshot.segments)
        if segment_count >= 2:
            status = "success"
        elif segment_count >= 1:
            status = "partial"
        else:
            status = "low_data"

        logger.info(f"[CUSTOMER_INTEL] v1.1 complete: {segment_count} segments, status={status}")

        return {
            "status": status,
            "snapshot": snapshot.model_dump(mode="json"),
            "message": f"Generated {segment_count} customer segments"
        }

    async def _gather_inputs(self, campaign_id: str):
        """Gather all available inputs. Never fail on missing optional modules."""

        # Step 1 — REQUIRED
        step1 = await self.db.campaign_briefs.find_one(
            {"campaign_brief_id": campaign_id},
            {"_id": 0}
        )

        # Step 2 — REQUIRED
        step2_pack = await self.db.website_context_packs.find_one(
            {"campaign_brief_id": campaign_id},
            {"_id": 0}
        )
        step2 = step2_pack.get("step2", step2_pack.get("data", {})) if step2_pack else None

        # Research modules — OPTIONAL
        research_pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0}
        )

        search_demand = None
        seasonality = None
        competitors = None

        if research_pack:
            sources = research_pack.get("sources", {})

            si = sources.get("search_intent", {})
            if si.get("latest"):
                search_demand = si["latest"]
                logger.info("[CUSTOMER_INTEL] Search Demand data available")

            seas = sources.get("seasonality", {})
            if seas.get("latest"):
                seasonality = seas["latest"]
                logger.info("[CUSTOMER_INTEL] Seasonality data available")

            comp = sources.get("competitors", {})
            if comp.get("latest"):
                competitors = comp["latest"]
                logger.info("[CUSTOMER_INTEL] Competitors data available")

        return step1, step2, search_demand, seasonality, competitors

    def _build_snapshot(
        self,
        processed: Dict[str, Any],
        audit_data: Dict[str, Any],
        missing_inputs: List[str],
        retry_count: int,
        llm_model: str,
        llm_tokens: int
    ) -> CustomerIntelSnapshot:
        """Build validated snapshot from processed data."""
        now = datetime.now(timezone.utc)

        # Parse segments
        segments = []
        for seg_data in processed.get("segments", [])[:3]:
            segments.append(SegmentCard(
                segment_name=str(seg_data.get("segment_name", ""))[:48],
                jtbd=str(seg_data.get("jtbd", ""))[:120],
                core_motives=[str(m)[:90] for m in seg_data.get("core_motives", [])[:3]],
                top_pains=[str(p)[:90] for p in seg_data.get("top_pains", [])[:3]],
                top_objections=[str(o)[:90] for o in seg_data.get("top_objections", [])[:3]],
                best_proof=[str(p)[:90] for p in seg_data.get("best_proof", [])[:3]],
                risk_reducers=[str(r)[:90] for r in seg_data.get("risk_reducers", [])[:3]],
                best_offer_items=[str(o)[:80] for o in seg_data.get("best_offer_items", [])[:3]],
                best_channel_focus=[str(c)[:50] for c in seg_data.get("best_channel_focus", [])[:2]],
                search_language=[str(s)[:80] for s in seg_data.get("search_language", [])[:6]],
            ))

        # Parse trigger map
        tm_data = processed.get("trigger_map", {})
        trigger_map = TriggerMap(
            moment_triggers=[str(t)[:90] for t in tm_data.get("moment_triggers", [])[:5]],
            urgency_triggers=[str(t)[:90] for t in tm_data.get("urgency_triggers", [])[:5]],
            planned_triggers=[str(t)[:90] for t in tm_data.get("planned_triggers", [])[:5]],
        )

        # Parse language bank
        lb_data = processed.get("language_bank", {})
        language_bank = LanguageBank(
            desire_phrases=[str(p)[:90] for p in lb_data.get("desire_phrases", [])[:12]],
            anxiety_phrases=[str(p)[:90] for p in lb_data.get("anxiety_phrases", [])[:12]],
            intent_phrases=[str(p)[:90] for p in lb_data.get("intent_phrases", [])[:12]],
        )

        # Audit
        audit = CustomerIntelAudit(
            **audit_data,
            missing_inputs=missing_inputs,
            retry_count=retry_count,
            llm_model=llm_model,
            llm_tokens_used=llm_tokens
        )

        return CustomerIntelSnapshot(
            version="1.1",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            summary_bullets=[str(b)[:90] for b in processed.get("summary_bullets", [])[:3]],
            segments=segments,
            trigger_map=trigger_map,
            language_bank=language_bank,
            audit=audit,
            delta=CustomerIntelDelta()
        )

    def _compute_delta(self, old: CustomerIntelSnapshot, new: CustomerIntelSnapshot) -> CustomerIntelDelta:
        """Compute what changed between snapshots."""
        old_names = set()
        for s in old.segments:
            old_names.add(s.segment_name)
        # Handle v1.0 legacy
        if hasattr(old, 'icp_segments'):
            for s in getattr(old, 'icp_segments', []):
                old_names.add(getattr(s, 'name', ''))

        new_names = {s.segment_name for s in new.segments}

        added = new_names - old_names
        removed = old_names - new_names

        notable = []
        if added:
            notable.append(f"New segments: {', '.join(list(added)[:2])}")
        if removed:
            notable.append(f"Removed: {', '.join(list(removed)[:2])}")

        return CustomerIntelDelta(
            notable_changes=notable[:5],
            new_segments_count=len(added),
            removed_segments_count=len(removed)
        )

    async def get_latest(self, campaign_id: str) -> Optional[CustomerIntelSnapshot]:
        """Get latest Customer Intel snapshot from DB."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.customer_intel.latest": 1}
        )

        if not pack:
            return None

        latest = pack.get("sources", {}).get("customer_intel", {}).get("latest")
        if not latest:
            return None

        try:
            return CustomerIntelSnapshot(**latest)
        except Exception as e:
            logger.warning(f"[CUSTOMER_INTEL] Failed to parse snapshot: {e}")
            return None

    async def save_snapshot(self, campaign_id: str, snapshot: CustomerIntelSnapshot):
        """Save snapshot to research_packs with history management."""
        snapshot_dict = snapshot.model_dump(mode="json")

        existing = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "campaign_id": 1}
        )

        if not existing:
            await self.db.research_packs.insert_one({
                "campaign_id": campaign_id,
                "sources": {
                    "customer_intel": {"latest": snapshot_dict, "history": []},
                    "search_intent": {"latest": None, "history": []},
                    "seasonality": {"latest": None, "history": []},
                    "competitors": {"latest": None, "history": []}
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        else:
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                {
                    "$set": {
                        "sources.customer_intel.latest": snapshot_dict,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    },
                    "$push": {
                        "sources.customer_intel.history": {
                            "$each": [snapshot_dict],
                            "$position": 0,
                            "$slice": HISTORY_CAP
                        }
                    }
                }
            )

        logger.info(f"[CUSTOMER_INTEL] Saved v1.1 snapshot for campaign {campaign_id}")

    async def get_history(self, campaign_id: str) -> List[CustomerIntelSnapshot]:
        """Get Customer Intel history."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.customer_intel.history": 1}
        )

        if not pack:
            return []

        history_raw = pack.get("sources", {}).get("customer_intel", {}).get("history", [])
        snapshots = []
        for item in history_raw:
            try:
                snapshots.append(CustomerIntelSnapshot(**item))
            except Exception as e:
                logger.warning(f"[CUSTOMER_INTEL] Failed to parse history snapshot: {e}")

        return snapshots
