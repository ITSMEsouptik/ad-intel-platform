"""
Novara Research Foundation: Competitor Discovery Service
Main orchestrator for discovering competitors

Version 3.0 - Feb 2026
- Passes enriched context to Perplexity
- Handles structured market_overview
- Removed category_search_terms
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    CompetitorSnapshot,
    CompetitorDelta,
    CompetitorInputs,
    Competitor,
    MarketOverview
)
from .perplexity_competitors import call_perplexity_competitors

logger = logging.getLogger(__name__)

REFRESH_DAYS = 30
HISTORY_LIMIT = 10


class CompetitorService:
    """Orchestrates the competitor discovery pipeline."""
    
    def __init__(self, db):
        self.db = db
    
    def extract_inputs(
        self,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract all inputs needed for competitor discovery."""
        
        # Step 1 inputs
        geo = campaign_brief.get("geo", {})
        city = geo.get("city_or_region", "")
        country = geo.get("country", "")
        
        # Step 2 inputs
        step2 = website_context_pack.get("step2", {})
        
        site = step2.get("site", {})
        classification = step2.get("classification", {})
        offer = step2.get("offer", {})
        brand_summary = step2.get("brand_summary", {})
        brand_dna = step2.get("brand_dna", {})
        conversion = step2.get("conversion", {})
        pricing = step2.get("pricing", {})
        
        # Domain
        domain = site.get("domain", site.get("final_url", ""))
        
        # Classification
        subcategory = classification.get("subcategory", "")
        niche = classification.get("niche", "")
        
        # Brand summary
        brand_name = brand_summary.get("name", "")
        tagline = brand_summary.get("tagline", "")
        one_liner = brand_summary.get("one_liner", "")
        bullets = brand_summary.get("bullets", [])
        
        # Build brand overview
        brand_overview_parts = []
        if one_liner and one_liner != "unknown":
            brand_overview_parts.append(one_liner)
        if tagline and tagline != "unknown":
            brand_overview_parts.append(tagline)
        if bullets:
            brand_overview_parts.extend(bullets[:2])
        brand_overview = " | ".join(brand_overview_parts)[:300] if brand_overview_parts else ""
        
        # Offer
        value_prop = offer.get("value_prop", "")
        key_benefits = offer.get("key_benefits", [])
        
        # Services
        services = []
        for item in offer.get("offer_catalog", [])[:6]:
            name = item.get("name", "")
            if name and name.lower() != "unknown":
                services.append(name)
        
        # Brand DNA
        values = brand_dna.get("values", [])
        tone_of_voice = brand_dna.get("tone_of_voice", [])
        aesthetic = brand_dna.get("aesthetic", [])
        
        # Conversion
        destination_type = conversion.get("destination_type", "website")
        primary_action = conversion.get("primary_action", "")
        
        # Price range
        price_range = None
        if pricing.get("count", 0) > 0:
            price_range = {
                "currency": pricing.get("currency", ""),
                "min": pricing.get("min", 0),
                "max": pricing.get("max", 0),
                "avg": pricing.get("avg", 0)
            }
        
        return {
            "geo": {"city": city, "country": country},
            "brand_name": brand_name,
            "domain": domain,
            "subcategory": subcategory,
            "niche": niche,
            "services": services,
            "brand_overview": brand_overview,
            "price_range": price_range,
            # Enriched context
            "tagline": tagline,
            "one_liner": one_liner,
            "bullets": bullets,
            "value_prop": value_prop,
            "key_benefits": key_benefits,
            "values": values,
            "tone_of_voice": tone_of_voice,
            "aesthetic": aesthetic,
            "destination_type": destination_type,
            "primary_action": primary_action
        }
    
    async def build_snapshot(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> CompetitorSnapshot:
        """Build a new CompetitorSnapshot."""
        logger.info(f"[COMPETITORS] Building snapshot for campaign={campaign_id}")
        
        # Extract all inputs
        inputs = self.extract_inputs(campaign_brief, website_context_pack)
        
        city = inputs["geo"]["city"]
        country = inputs["geo"]["country"]
        
        logger.info(f"[COMPETITORS] Brand: {inputs['brand_name']}, Location: {city or country}, Niche: {inputs['niche']}")
        
        # Call Perplexity with enriched context
        try:
            raw_result = await call_perplexity_competitors(
                brand_name=inputs["brand_name"],
                domain=inputs["domain"],
                city=city,
                country=country,
                subcategory=inputs["subcategory"],
                niche=inputs["niche"],
                services=inputs["services"],
                brand_overview=inputs["brand_overview"],
                price_range=inputs["price_range"],
                # Enriched context
                tagline=inputs["tagline"],
                one_liner=inputs["one_liner"],
                bullets=inputs["bullets"],
                value_prop=inputs["value_prop"],
                key_benefits=inputs["key_benefits"],
                values=inputs["values"],
                tone_of_voice=inputs["tone_of_voice"],
                aesthetic=inputs["aesthetic"],
                destination_type=inputs["destination_type"],
                primary_action=inputs["primary_action"]
            )
        except Exception as e:
            logger.error(f"[COMPETITORS] Perplexity call failed: {e}")
            return self._empty_snapshot(inputs)
        
        # Parse competitors
        competitors = []
        for comp_data in raw_result.get("competitors", [])[:5]:
            try:
                competitor = Competitor(
                    name=comp_data.get("name", "Unknown"),
                    website=comp_data.get("website", ""),
                    instagram_url=comp_data.get("instagram_url"),
                    instagram_handle=comp_data.get("instagram_handle"),
                    tiktok_url=comp_data.get("tiktok_url"),
                    tiktok_handle=comp_data.get("tiktok_handle"),
                    what_they_do=comp_data.get("what_they_do", "")[:80],
                    positioning=comp_data.get("positioning", "")[:100],
                    why_competitor=comp_data.get("why_competitor", "")[:80],
                    price_tier=comp_data.get("price_tier", "mid-range"),
                    estimated_size=comp_data.get("estimated_size", "medium"),
                    overlap_score=comp_data.get("overlap_score", "medium"),
                    strengths=comp_data.get("strengths", []),
                    weaknesses=comp_data.get("weaknesses", []),
                    ad_strategy_summary=comp_data.get("ad_strategy_summary"),
                    social_presence=comp_data.get("social_presence", []),
                )
                competitors.append(competitor)
            except Exception as e:
                logger.warning(f"[COMPETITORS] Error parsing competitor: {e}")
        
        # Parse market overview
        market_data = raw_result.get("market_overview", {})
        market_overview = MarketOverview(
            competitive_density=market_data.get("competitive_density", "moderate"),
            dominant_player_type=market_data.get("dominant_player_type", "")[:100],
            market_insight=market_data.get("market_insight", "")[:150],
            ad_landscape_note=market_data.get("ad_landscape_note", "")[:150]
        )
        
        # Build inputs for storage
        inputs_used = CompetitorInputs(
            geo=inputs["geo"],
            brand_name=inputs["brand_name"],
            domain=inputs["domain"],
            subcategory=inputs["subcategory"],
            niche=inputs["niche"],
            services=inputs["services"],
            brand_overview=inputs["brand_overview"],
            price_range=inputs["price_range"]
        )
        
        now = datetime.now(timezone.utc)
        
        snapshot = CompetitorSnapshot(
            version="3.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs_used=inputs_used,
            competitors=competitors,
            market_overview=market_overview,
            delta=CompetitorDelta()
        )
        
        logger.info(f"[COMPETITORS] Snapshot built: {len(competitors)} competitors")
        
        return snapshot
    
    def _empty_snapshot(self, inputs: Dict[str, Any]) -> CompetitorSnapshot:
        """Create an empty snapshot when no data available."""
        now = datetime.now(timezone.utc)
        
        inputs_used = CompetitorInputs(
            geo=inputs.get("geo", {}),
            brand_name=inputs.get("brand_name", ""),
            domain=inputs.get("domain", ""),
            subcategory=inputs.get("subcategory", ""),
            niche=inputs.get("niche", ""),
            services=inputs.get("services", []),
            brand_overview=inputs.get("brand_overview", ""),
            price_range=inputs.get("price_range")
        )
        
        return CompetitorSnapshot(
            version="3.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs_used=inputs_used,
            competitors=[],
            market_overview=MarketOverview(),
            delta=CompetitorDelta()
        )
    
    def compute_delta(
        self,
        current_snapshot: CompetitorSnapshot,
        previous_snapshot: Optional[CompetitorSnapshot]
    ) -> CompetitorDelta:
        """Compute delta between snapshots."""
        
        if not previous_snapshot:
            return CompetitorDelta(
                previous_captured_at=None,
                new_competitors_count=len(current_snapshot.competitors),
                removed_competitors_count=0,
                notable_changes=[f"Initial discovery: {len(current_snapshot.competitors)} competitors found"]
            )
        
        current_names = {c.name.lower() for c in current_snapshot.competitors}
        previous_names = {c.name.lower() for c in previous_snapshot.competitors}
        
        new_competitors = current_names - previous_names
        removed_competitors = previous_names - current_names
        
        notable = []
        if new_competitors:
            notable.append(f"New: {', '.join(list(new_competitors)[:2])}")
        if removed_competitors:
            notable.append(f"Removed: {', '.join(list(removed_competitors)[:2])}")
        
        return CompetitorDelta(
            previous_captured_at=previous_snapshot.captured_at,
            new_competitors_count=len(new_competitors),
            removed_competitors_count=len(removed_competitors),
            notable_changes=notable[:5]
        )
    
    async def get_existing_pack(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get existing research pack for campaign."""
        return await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0}
        )
    
    async def save_snapshot(
        self,
        campaign_id: str,
        snapshot: CompetitorSnapshot
    ) -> Dict[str, Any]:
        """Save snapshot to research_packs collection."""
        
        now = datetime.now(timezone.utc)
        existing = await self.get_existing_pack(campaign_id)
        
        previous_snapshot = None
        if existing:
            competitors_source = existing.get("sources", {}).get("competitors", {})
            latest_data = competitors_source.get("latest")
            if latest_data:
                try:
                    previous_snapshot = CompetitorSnapshot(**latest_data)
                except Exception as e:
                    logger.warning(f"Could not parse previous snapshot: {e}")
        
        delta = self.compute_delta(snapshot, previous_snapshot)
        snapshot.delta = delta
        
        snapshot_dict = snapshot.model_dump(mode="json")
        
        if existing:
            update_ops = {
                "$set": {
                    "sources.competitors.latest": snapshot_dict,
                    "updated_at": now.isoformat()
                }
            }
            
            if previous_snapshot:
                previous_dict = previous_snapshot.model_dump(mode="json")
                update_ops["$push"] = {
                    "sources.competitors.history": {
                        "$each": [previous_dict],
                        "$position": 0,
                        "$slice": HISTORY_LIMIT
                    }
                }
            
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                update_ops
            )
            
            logger.info(f"[COMPETITORS] Updated research pack for campaign={campaign_id}")
        else:
            import uuid
            
            new_pack = {
                "research_pack_id": str(uuid.uuid4()),
                "campaign_id": campaign_id,
                "sources": {
                    "competitors": {
                        "latest": snapshot_dict,
                        "history": []
                    }
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            await self.db.research_packs.insert_one(new_pack)
            
            logger.info(f"[COMPETITORS] Created new research pack for campaign={campaign_id}")
        
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
            
            if len(snapshot.competitors) >= 3:
                status = "success"
            elif len(snapshot.competitors) >= 1:
                status = "partial"
            else:
                status = "failed"
            
            return {
                "status": status,
                "snapshot": snapshot.model_dump(mode="json"),
                "research_pack": pack,
                "message": f"Found {len(snapshot.competitors)} competitors"
            }
            
        except Exception as e:
            logger.exception(f"[COMPETITORS] Error running pipeline: {e}")
            return {
                "status": "failed",
                "snapshot": None,
                "research_pack": None,
                "message": str(e)
            }
    
    async def get_latest(self, campaign_id: str) -> Optional[CompetitorSnapshot]:
        """Get latest snapshot for campaign."""
        pack = await self.get_existing_pack(campaign_id)
        
        if not pack:
            return None
        
        latest_data = pack.get("sources", {}).get("competitors", {}).get("latest")
        
        if not latest_data:
            return None
        
        try:
            return CompetitorSnapshot(**latest_data)
        except Exception as e:
            logger.warning(f"Could not parse competitor snapshot: {e}")
            return None
    
    async def get_history(self, campaign_id: str) -> List[CompetitorSnapshot]:
        """Get snapshot history for campaign."""
        pack = await self.get_existing_pack(campaign_id)
        
        if not pack:
            return []
        
        history_data = pack.get("sources", {}).get("competitors", {}).get("history", [])
        
        snapshots = []
        for data in history_data:
            try:
                snapshots.append(CompetitorSnapshot(**data))
            except Exception as e:
                logger.warning(f"Could not parse history snapshot: {e}")
        
        return snapshots
