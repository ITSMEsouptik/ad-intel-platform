"""
Novara Research Foundation: Search Intent Service v2
Main orchestrator — BRP-based pipeline

Version 2.0 - Feb 2026
Pipeline: Seeds -> Suggest -> Blocklist Clean -> BRP Filter -> Score -> Dedupe -> Bucket -> Top 10 -> LLM Cleanup
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

from .schema import (
    SearchIntentSnapshot,
    SearchIntentDelta,
    SearchIntentInputs,
    SearchIntentStats,
    LLMCleaningAudit,
    RelevanceGateAudit,
    BRPSnapshot,
    ForumQueries,
    SearchIntentSource
)
from .brp import build_brp, BRP
from .google_suggest import GoogleSuggestClient
from .seeds import (
    generate_seeds,
    extract_seed_inputs,
    build_keyword_sets,
    KeywordSets
)
from .cleaning import clean_suggestions
from .relevance_gate import filter_queries
from .bucketing import bucket_queries_with_scores
from .ranking import (
    score_queries,
    rank_and_cap,
    dedupe_by_similarity,
    select_top_10,
    generate_ad_keyword_queries,
    generate_forum_queries
)
from .llm_cleanup import clean_with_llm, apply_llm_cleaning, CleaningStats

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============

REFRESH_DAYS = 14
HISTORY_LIMIT = 10


def _brp_to_snapshot(brp: BRP) -> BRPSnapshot:
    """Convert a BRP object to a storable snapshot"""
    return BRPSnapshot(
        brand_name=brp.brand_name,
        domain=brp.domain,
        geo_city=brp.geo_city,
        geo_country=brp.geo_country,
        business_model=brp.business_model,
        brand_terms=brp.brand_terms,
        service_terms=brp.service_terms,
        category_terms=brp.category_terms,
        geo_terms=brp.geo_terms,
        block_terms_count=len(brp.block_terms),
        geo_block_terms_count=len(brp.geo_block_terms),
        has_ecommerce_signals=brp.has_ecommerce_signals
    )


class SearchIntentService:
    """
    Orchestrates the Search Intent v2 pipeline:
    
    1. Load context (Step 1 + Step 2 + Competitors)
    2. Build BRP (Business Relevance Profile)
    3. Generate seeds + fetch Google Suggest
    4. Blocklist clean (basic normalization)
    5. BRP Relevance Gate (deterministic filter)
    6. Score + Rank + Dedupe
    7. Bucket (deterministic regex)
    8. Select Top 10 + Ad Keywords + Forum Queries
    9. Optional LLM cleanup (clean-only, no generation)
    10. Save snapshot
    """
    
    def __init__(self, db):
        self.db = db
        self.suggest_client = GoogleSuggestClient()
    
    async def _get_competitors_snapshot(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get latest competitors snapshot if available"""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.competitors.latest": 1}
        )
        if not pack:
            return None
        return pack.get("sources", {}).get("competitors", {}).get("latest")
    
    async def build_snapshot(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> SearchIntentSnapshot:
        """
        Build a new SearchIntentSnapshot using BRP-based v2 pipeline.
        """
        logger.info(f"[SEARCH_INTENT_V2] Building snapshot for campaign={campaign_id}")
        
        # ============== 1. BUILD BRP ==============
        brp = build_brp(campaign_brief, website_context_pack)
        brp_snapshot = _brp_to_snapshot(brp)
        logger.info(f"[SEARCH_INTENT_V2] BRP: model={brp.business_model}, "
                    f"services={len(brp.service_terms)}, brand={brp.brand_terms}")
        
        # ============== 2. LOAD COMPETITORS (optional) ==============
        competitors_snapshot = await self._get_competitors_snapshot(campaign_id)
        if competitors_snapshot:
            logger.info("[SEARCH_INTENT_V2] Found competitors data")
        
        # ============== 3. EXTRACT INPUTS + SEEDS ==============
        inputs = extract_seed_inputs(campaign_brief, website_context_pack, competitors_snapshot)
        keyword_sets = build_keyword_sets(inputs)
        seeds = generate_seeds(inputs, keyword_sets)
        
        if not seeds:
            logger.warning("[SEARCH_INTENT_V2] No seeds generated")
            return self._empty_snapshot(inputs, keyword_sets, brp_snapshot)
        
        logger.info(f"[SEARCH_INTENT_V2] Generated {len(seeds)} seeds")
        
        # ============== 4. FETCH SUGGESTIONS ==============
        raw_suggestions = await self.suggest_client.fetch_all_suggestions(
            seeds=seeds,
            language=inputs.language or "en",
            country=inputs.country
        )
        
        raw_count = len(raw_suggestions)
        logger.info(f"[SEARCH_INTENT_V2] Fetched {raw_count} raw suggestions")
        
        if not raw_suggestions:
            raw_suggestions = seeds.copy()
        
        # ============== 5. BLOCKLIST CLEAN (basic normalization) ==============
        cleaned, blocklist_count, _ = clean_suggestions(
            suggestions=raw_suggestions,
            sells_workshops=keyword_sets.sells_workshops,
            allow_discounts=False,
            brand_name=inputs.brand_name,
            min_words=2,
            max_words=10
        )
        
        logger.info(f"[SEARCH_INTENT_V2] After blocklist: {len(cleaned)} (removed {blocklist_count})")
        
        # ============== 6. BRP RELEVANCE GATE ==============
        kept_queries, gate_audit = filter_queries(cleaned, brp)
        
        gate_audit_dict = gate_audit.to_dict()
        gate_audit_model = RelevanceGateAudit(
            raw_count=gate_audit_dict["raw_count"],
            kept_count=gate_audit_dict["kept_count"],
            rejected_geo_mismatch=gate_audit_dict["rejected_geo_mismatch"],
            rejected_product_intent=gate_audit_dict["rejected_product_intent"],
            rejected_procedure_intent=gate_audit_dict["rejected_procedure_intent"],
            rejected_unit_noise=gate_audit_dict["rejected_unit_noise"],
            rejected_too_generic=gate_audit_dict["rejected_too_generic"],
            rejected_missing_service_token=gate_audit_dict["rejected_missing_service_token"],
            rejected_missing_modifier_or_geo=gate_audit_dict["rejected_missing_modifier_or_geo"],
            rejected_junk=gate_audit_dict["rejected_junk"],
            rejected_length=gate_audit_dict["rejected_length"],
            top_rejected_examples=gate_audit_dict.get("top_rejected_examples", {})
        )
        
        filtered_irrelevant = gate_audit_dict["raw_count"] - gate_audit_dict["kept_count"]
        
        logger.info(f"[SEARCH_INTENT_V2] After BRP gate: {len(kept_queries)} "
                    f"(rejected {filtered_irrelevant})")
        
        # ============== 7. SCORE + RANK + DEDUPE ==============
        scored = score_queries(kept_queries, brp)
        ranked = rank_and_cap(scored, total_cap=150)
        deduped = dedupe_by_similarity(ranked, similarity_threshold=0.85)
        
        logger.info(f"[SEARCH_INTENT_V2] After score/rank/dedupe: {len(deduped)}")
        
        # ============== 8. BUCKET ==============
        buckets = bucket_queries_with_scores(deduped, bucket_cap=20)
        
        # ============== 9. SELECT TOP 10 + AD KEYWORDS + FORUM ==============
        top_10 = select_top_10(buckets, deduped, max_per_bucket=3)
        ad_keywords = generate_ad_keyword_queries(deduped, min_words=2, max_words=7, limit=35)
        forum_queries_dict = generate_forum_queries(top_10, buckets, limit_per_platform=15)
        
        # ============== 10. LLM CURATION (optional) ==============
        business_context = {
            "brand_name": brp.brand_name or inputs.brand_name,
            "niche": inputs.niche,
            "city": inputs.city
        }
        
        cleaned_output, cleaning_stats = await clean_with_llm(
            top_10_queries=top_10,
            ad_keyword_queries=ad_keywords,
            intent_buckets=buckets,
            business_context=business_context
        )
        
        final_top_10, final_ad_keywords, final_buckets = apply_llm_cleaning(
            original_top_10=top_10,
            original_ad_keywords=ad_keywords,
            original_buckets=buckets,
            cleaned=cleaned_output,
            stats=cleaning_stats
        )
        
        # Build LLM audit
        llm_audit = None
        if cleaning_stats and cleaning_stats.output_total_unique > 0:
            llm_audit = LLMCleaningAudit(
                input_count=cleaning_stats.input_total_unique,
                output_count=cleaning_stats.output_total_unique,
                removed_count=cleaning_stats.removed_count,
                merged_count=cleaning_stats.merged_count,
                moved_count=cleaning_stats.moved_count,
                added_count=cleaning_stats.added_count,
                invalid_queries_dropped=cleaning_stats.invalid_queries_dropped or [],
                validation_passed=cleaning_stats.validation_passed
            )
        
        # ============== 11. BUILD SNAPSHOT ==============
        now = datetime.now(timezone.utc)
        kept_final = len(deduped)
        
        snapshot = SearchIntentSnapshot(
            version="2.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            brp=brp_snapshot,
            stats=SearchIntentStats(
                seeds_used=len(seeds),
                seed_list=seeds[:40],
                suggestions_raw=raw_count,
                filtered_blocklist=blocklist_count,
                relevance_gate=gate_audit_model,
                filtered_irrelevant=filtered_irrelevant,
                kept_final=kept_final,
                llm_cleaning=llm_audit
            ),
            inputs_used=SearchIntentInputs(
                geo={"city": inputs.city, "country": inputs.country, "language": inputs.language or "en"},
                seeds=seeds,
                service_terms=keyword_sets.service_terms,
                category_terms=keyword_sets.category_terms[:10],
                competitor_terms=keyword_sets.competitor_terms,
                sells_workshops=keyword_sets.sells_workshops
            ),
            top_10_queries=final_top_10,
            intent_buckets=final_buckets,
            ad_keyword_queries=final_ad_keywords,
            forum_queries=ForumQueries(
                reddit=forum_queries_dict.get("reddit", []),
                quora=forum_queries_dict.get("quora", [])
            ),
            delta=SearchIntentDelta()
        )
        
        logger.info(f"[SEARCH_INTENT_V2] Snapshot built: top_10={len(final_top_10)}, "
                    f"ad_keywords={len(final_ad_keywords)}, "
                    f"total_bucketed={sum(len(v) for v in final_buckets.values())}")
        
        return snapshot
    
    def _empty_snapshot(self, inputs, keyword_sets: KeywordSets, brp_snapshot: BRPSnapshot) -> SearchIntentSnapshot:
        """Create empty snapshot when no data available"""
        now = datetime.now(timezone.utc)
        
        return SearchIntentSnapshot(
            version="2.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            brp=brp_snapshot,
            stats=SearchIntentStats(),
            inputs_used=SearchIntentInputs(
                geo={"city": inputs.city, "country": inputs.country, "language": inputs.language},
                seeds=[],
                service_terms=keyword_sets.service_terms,
                category_terms=keyword_sets.category_terms,
                competitor_terms=keyword_sets.competitor_terms,
                sells_workshops=keyword_sets.sells_workshops
            ),
            top_10_queries=[],
            intent_buckets={"price": [], "trust": [], "urgency": [], "comparison": [], "general": []},
            ad_keyword_queries=[],
            forum_queries=ForumQueries(),
            delta=SearchIntentDelta()
        )
    
    def compute_delta(
        self,
        current_snapshot: SearchIntentSnapshot,
        previous_snapshot: Optional[SearchIntentSnapshot]
    ) -> SearchIntentDelta:
        """Compute delta between snapshots"""
        if not previous_snapshot:
            return SearchIntentDelta(
                previous_captured_at=None,
                new_queries_count=len(current_snapshot.top_10_queries),
                removed_queries_count=0,
                notable_new_queries=current_snapshot.top_10_queries[:5]
            )
        
        current_all = set(current_snapshot.top_10_queries)
        for queries in current_snapshot.intent_buckets.values():
            current_all.update(queries)
        
        previous_all = set(previous_snapshot.top_10_queries)
        for queries in previous_snapshot.intent_buckets.values():
            previous_all.update(queries)
        
        new_queries = current_all - previous_all
        removed_queries = previous_all - current_all
        notable = [q for q in current_snapshot.top_10_queries if q in new_queries][:5]
        
        return SearchIntentDelta(
            previous_captured_at=previous_snapshot.captured_at,
            new_queries_count=len(new_queries),
            removed_queries_count=len(removed_queries),
            notable_new_queries=notable
        )
    
    async def get_existing_pack(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get existing research pack"""
        return await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0}
        )
    
    async def save_snapshot(
        self,
        campaign_id: str,
        snapshot: SearchIntentSnapshot
    ) -> Dict[str, Any]:
        """Save snapshot to research_packs"""
        now = datetime.now(timezone.utc)
        
        existing = await self.get_existing_pack(campaign_id)
        
        # Get previous for delta
        previous_snapshot = None
        if existing:
            search_intent_source = existing.get("sources", {}).get("search_intent", {})
            latest_data = search_intent_source.get("latest")
            if latest_data:
                try:
                    previous_snapshot = SearchIntentSnapshot(**latest_data)
                except Exception as e:
                    logger.warning(f"Could not parse previous snapshot: {e}")
        
        # Compute delta
        delta = self.compute_delta(snapshot, previous_snapshot)
        snapshot.delta = delta
        
        snapshot_dict = snapshot.model_dump(mode="json")
        
        if existing:
            update_ops = {
                "$set": {
                    "sources.search_intent.latest": snapshot_dict,
                    "updated_at": now.isoformat()
                }
            }
            
            if previous_snapshot:
                previous_dict = previous_snapshot.model_dump(mode="json")
                update_ops["$push"] = {
                    "sources.search_intent.history": {
                        "$each": [previous_dict],
                        "$position": 0,
                        "$slice": HISTORY_LIMIT
                    }
                }
            
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                update_ops
            )
            
            logger.info("[SEARCH_INTENT_V2] Updated research pack")
        else:
            import uuid
            
            new_pack = {
                "research_pack_id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "sources": {
                    "search_intent": {
                        "latest": snapshot_dict,
                        "history": []
                    }
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            await self.db.research_packs.insert_one(new_pack)
            
            logger.info("[SEARCH_INTENT_V2] Created new research pack")
        
        return await self.get_existing_pack(campaign_id)
    
    async def run(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Full v2 pipeline: build, delta, save.
        """
        try:
            snapshot = await self.build_snapshot(
                campaign_id=campaign_id,
                campaign_brief=campaign_brief,
                website_context_pack=website_context_pack
            )
            
            pack = await self.save_snapshot(campaign_id, snapshot)
            
            if snapshot.stats.kept_final >= 20:
                status = "success"
            elif snapshot.stats.kept_final >= 10:
                status = "partial"
            else:
                status = "low_data"
            
            return {
                "status": status,
                "snapshot": snapshot.model_dump(mode="json"),
                "research_pack": pack,
                "message": f"Generated {snapshot.stats.kept_final} queries, top 10 selected"
            }
            
        except Exception as e:
            logger.exception(f"[SEARCH_INTENT_V2] Pipeline error: {e}")
            return {
                "status": "failed",
                "snapshot": None,
                "research_pack": None,
                "message": str(e)
            }
    
    async def get_latest(self, campaign_id: str) -> Optional[SearchIntentSnapshot]:
        """Get latest snapshot"""
        pack = await self.get_existing_pack(campaign_id)
        if not pack:
            return None
        latest_data = pack.get("sources", {}).get("search_intent", {}).get("latest")
        if not latest_data:
            return None
        try:
            return SearchIntentSnapshot(**latest_data)
        except Exception as e:
            logger.warning(f"Could not parse snapshot: {e}")
            return None
    
    async def get_history(self, campaign_id: str) -> List[SearchIntentSnapshot]:
        """Get snapshot history"""
        pack = await self.get_existing_pack(campaign_id)
        if not pack:
            return []
        history_data = pack.get("sources", {}).get("search_intent", {}).get("history", [])
        snapshots = []
        for data in history_data:
            try:
                snapshots.append(SearchIntentSnapshot(**data))
            except Exception as e:
                logger.warning(f"Could not parse history snapshot: {e}")
        return snapshots
