"""
Novara Ads Intelligence: Service Orchestrator
Runs the full pipeline:
1. Load inputs (Step1 geo + Step2 classification + Competitors)
2. Competitor lens: domain → brand lookup → fetch ads → postprocess → score → shortlist
3. Category lens: build queries → discovery ads (geo-first → global fallback) → postprocess → score → shortlist
4. Merge, build snapshot, compute delta, save
"""

import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import AdsIntelSnapshot, AdsLensResult, AdCard
from .foreplay_client import ForeplayClient, ForeplayAPIError
from .seeds import build_competitor_seeds, build_category_queries, normalize_domain, extract_business_signals, build_enriched_query
from .scoring import shortlist_competitor_ads, shortlist_category_ads, compute_ad_patterns
from .postprocess import postprocess_ads

logger = logging.getLogger(__name__)

REFRESH_DAYS = int(os.environ.get("ADS_INTEL_REFRESH_DAYS", "14"))
HISTORY_CAP = 10
COMPETITOR_FETCH_LIMIT = int(os.environ.get("ADS_INTEL_COMPETITOR_AD_FETCH_LIMIT", "50"))
CATEGORY_FETCH_LIMIT = int(os.environ.get("ADS_INTEL_CATEGORY_AD_FETCH_LIMIT", "50"))
SHORTLIST_TOTAL = int(os.environ.get("ADS_INTEL_SHORTLIST_TOTAL", "40"))


class AdsIntelService:
    def __init__(self, db):
        self.db = db
        self.client = ForeplayClient()

    def _extract_inputs(
        self,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract all inputs needed for the pipeline.
        Handles both 'step2' schema and 'data' schema from website_context_packs.
        """
        geo = campaign_brief.get("geo", {})

        # Try step2 schema first, fallback to data schema
        step2 = website_context_pack.get("step2", {})
        data = website_context_pack.get("data", {})

        if step2:
            classification = step2.get("classification", {})
            offer = step2.get("offer", {})
            brand_summary = step2.get("brand_summary", {})
            site = step2.get("site", {})
        else:
            # Use 'data' schema
            bi = data.get("brand_identity", {})
            brand_name_raw = bi.get("brand_name") or ""
            tagline = bi.get("tagline") or ""
            value_prop = bi.get("one_liner_value_prop") or ""

            # Don't use tagline as niche if it looks like a domain
            niche_candidate = ""
            if tagline and not tagline.endswith((".com", ".co", ".ae", ".org", ".net")):
                niche_candidate = tagline

            classification = {
                "industry": bi.get("industry") or "",
                "subcategory": bi.get("category") or bi.get("subcategory") or "",
                "niche": bi.get("niche") or niche_candidate or "",
                "tags": [],
            }
            offer = data.get("offer", {})
            # Use brand_name as a category signal when classification is empty
            brand_summary = {
                "name": brand_name_raw,
                "value_prop": value_prop,
            }
            site = data.get("site", {})

        return {
            "geo": {
                "city": geo.get("city_or_region", ""),
                "country": geo.get("country", ""),
            },
            "classification": classification,
            "offer": offer,
            "brand_name": brand_summary.get("name", ""),
            "domain": site.get("domain", site.get("final_url", "")),
            "niche": classification.get("niche", ""),
            "subcategory": classification.get("subcategory", ""),
            "industry": classification.get("industry", ""),
        }

    async def _get_competitor_list(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get competitors from research pack."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.competitors.latest": 1},
        )
        if not pack:
            return []
        latest = pack.get("sources", {}).get("competitors", {}).get("latest", {})
        comps = latest.get("competitors", [])
        return [c for c in comps[:5] if c.get("name") or c.get("website")]

    async def _get_category_search_terms(self, campaign_id: str) -> List[str]:
        """Get category_search_terms from competitors module output."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.competitors.latest.category_search_terms": 1},
        )
        if not pack:
            return []
        return (
            pack.get("sources", {})
            .get("competitors", {})
            .get("latest", {})
            .get("category_search_terms", [])
        )

    # ============== COMPETITOR LENS ==============

    @staticmethod
    def _brand_name_match(competitor_name: str, ad_brand_name: str) -> bool:
        """
        Check if an ad's brand name closely matches a competitor name.
        Strict enough to avoid false positives but flexible for common variations.
        """
        if not competitor_name or not ad_brand_name:
            return False
        comp = competitor_name.lower().strip()
        brand = ad_brand_name.lower().strip()
        # Exact match
        if comp == brand:
            return True
        # Normalize: remove common suffixes/punctuation for comparison
        import re
        comp_clean = re.sub(r'[^a-z0-9\s]', '', comp).strip()
        brand_clean = re.sub(r'[^a-z0-9\s]', '', brand).strip()
        if comp_clean == brand_clean:
            return True
        # Comp is a significant portion of brand (>60% of brand length)
        if comp_clean in brand_clean and len(comp_clean) >= len(brand_clean) * 0.6:
            return True
        # Brand is contained in comp (brand is shorter/abbreviated form)
        if brand_clean in comp_clean and len(brand_clean) >= len(comp_clean) * 0.6:
            return True
        # Word-boundary match: competitor name appears as a whole word in ad brand
        # e.g., "Ruuby" matches "Ruuby London" or "The Ruuby"
        if len(comp_clean) >= 3:
            pattern = r'\b' + re.escape(comp_clean) + r'\b'
            if re.search(pattern, brand_clean):
                return True
        return False

    @staticmethod
    def _passes_business_context(ad: Dict, signals: List[str]) -> bool:
        """
        Check if an ad's content matches the competitor's business context.
        Looks for industry signal words in the ad's headline, body, or landing page URL.
        """
        if not signals:
            return True  # No signals to check against — let it pass

        # Build combined text from all available ad fields
        parts = [
            ad.get("headline", "") or "",
            ad.get("body_text", "") or ad.get("body", "") or "",
            ad.get("landing_page_url", "") or ad.get("link_url", "") or "",
            ad.get("brand_name", "") or "",
            ad.get("page_name", "") or "",
        ]
        ad_text = " ".join(parts).lower()

        if not ad_text.strip():
            return False

        for signal in signals:
            if signal in ad_text:
                return True
        return False

    async def _run_competitor_lens(
        self, competitor_seeds: List[Dict[str, str]], audit: Dict
    ) -> List[Dict[str, Any]]:
        """
        Competitor Winners lens:
        For each competitor:
          1. Try domain → brand lookup → fetch longest-running ads (most reliable)
          2. If domain fails → context-enriched discovery query (name + business type)
             Then: name match + business context validation to filter results
        """
        all_ads = []
        # Get niche from the first seed's context for fallback enrichment
        campaign_niche = ""
        for s in competitor_seeds:
            if s.get("what_they_do"):
                campaign_niche = s["what_they_do"]
                break

        for seed in competitor_seeds:
            domain = seed.get("domain", "")
            name = seed.get("name", "")
            what_they_do = seed.get("what_they_do", "")

            if not domain and not name:
                continue

            # Extract business signals for this competitor
            signals = extract_business_signals(what_they_do, campaign_niche)

            try:
                found_via_domain = False

                # Step 1: Try brand lookup by domain (cheapest, most accurate)
                if domain:
                    brands = await self.client.get_brands_by_domain(domain)
                    audit["api_calls"] = audit.get("api_calls", 0) + 1

                    if brands:
                        brand = brands[0] if isinstance(brands, list) else brands
                        brand_id = str(brand.get("id", brand.get("_id", brand.get("brandId", ""))))
                        brand_name = brand.get("name", name)

                        if brand_id:
                            logger.info(f"[ADS_INTEL] Found brand: {brand_name} (id={brand_id}) for {domain}")
                            ads = await self.client.get_ads_by_brand_ids(
                                brand_ids=[brand_id],
                                limit=COMPETITOR_FETCH_LIMIT,
                                order="longest_running",
                            )
                            audit["api_calls"] = audit.get("api_calls", 0) + 1
                            audit["total_ads_seen"] = audit.get("total_ads_seen", 0) + len(ads)

                            for ad in ads:
                                ad["brand_name"] = brand_name
                                ad["brand_id"] = brand_id

                            cleaned = postprocess_ads(ads, lens="competitor")
                            all_ads.extend(cleaned)
                            found_via_domain = len(cleaned) > 0
                            if found_via_domain:
                                logger.info(f"[ADS_INTEL] Competitor '{brand_name}': {len(cleaned)} winning ads via domain")

                # Step 2: Context-enriched name search fallback
                if not found_via_domain and name:
                    enriched_query = build_enriched_query(name, what_they_do, campaign_niche)
                    queries_to_try = [enriched_query]
                    # If enriched query differs from plain name, add plain name as a second attempt
                    if enriched_query.lower() != name.lower():
                        queries_to_try.append(name)

                    matched_ads = []
                    total_raw = 0
                    total_rejected_name = 0
                    total_rejected_context = 0
                    used_query = ""

                    for query in queries_to_try:
                        logger.info(f"[ADS_INTEL] Trying fallback query: '{query}' for competitor '{name}'")
                        ads = await self.client.discovery_ads(
                            query=query,
                            limit=15,
                            order="longest_running",
                        )
                        audit["api_calls"] = audit.get("api_calls", 0) + 1
                        audit["total_ads_seen"] = audit.get("total_ads_seen", 0) + len(ads)
                        total_raw += len(ads)

                        # Filter: name match OR domain match + business context validation
                        for ad in ads:
                            ad_brand = ad.get("brand_name") or ad.get("name") or ad.get("brand", {}).get("name", "")
                            # Also check the ad's landing page domain against competitor domain
                            ad_landing = ad.get("link_url") or ad.get("landing_page_url") or ""
                            ad_domain = normalize_domain(ad_landing) if ad_landing else ""
                            domain_matches = domain and ad_domain and (
                                domain in ad_domain or ad_domain in domain
                            )

                            name_matches = self._brand_name_match(name, ad_brand)
                            if not name_matches and not domain_matches:
                                total_rejected_name += 1
                                continue
                            if not self._passes_business_context(ad, signals):
                                total_rejected_context += 1
                                logger.debug(f"[ADS_INTEL] Rejected ad (context mismatch): brand='{ad_brand}', signals={signals[:3]}")
                                continue
                            ad["brand_name"] = ad_brand or name
                            matched_ads.append(ad)

                        if matched_ads:
                            used_query = query
                            break  # Got results, no need to try next query

                    if matched_ads:
                        cleaned = postprocess_ads(matched_ads, lens="competitor")
                        all_ads.extend(cleaned)
                        logger.info(
                            f"[ADS_INTEL] Competitor '{name}': {len(cleaned)} ads via enriched search "
                            f"(query='{used_query}', {total_raw} raw, {total_rejected_name} name-rejected, {total_rejected_context} context-rejected)"
                        )
                    else:
                        logger.info(
                            f"[ADS_INTEL] Competitor '{name}': 0 matched ads "
                            f"({total_raw} raw across {len(queries_to_try)} queries, {total_rejected_name} name-rejected, {total_rejected_context} context-rejected) — skipping"
                        )
                        audit.setdefault("skipped_competitors", []).append(f"{name} ({domain})")

            except ForeplayAPIError as e:
                logger.warning(f"[ADS_INTEL] Foreplay error for {domain}: {e}")
                audit.setdefault("errors", []).append(f"{domain}: {str(e)}")
            except Exception as e:
                logger.warning(f"[ADS_INTEL] Error processing competitor {domain}: {e}")
                audit.setdefault("errors", []).append(f"{domain}: {str(e)}")

        return all_ads

    # ============== CATEGORY LENS ==============

    async def _run_category_lens(
        self, queries: List[str], geo: Dict[str, str], audit: Dict
    ) -> List[Dict[str, Any]]:
        """
        Category Winners lens with keyword cascade:
        Iterates through queries (most specific → broadest).
        Stops early once we have enough ads (>= target shortlist).
        Uses longest_running order. First tries with min 30-day filter,
        retries without it if a query returns 0 results.
        """
        all_ads = []
        target_ads = 30

        for query in queries:
            if len(all_ads) >= target_ads:
                logger.info(f"[ADS_INTEL] Category cascade stopping — already have {len(all_ads)} candidates")
                break

            try:
                # First attempt: with running_duration_min_days=30 for proven winners
                ads = await self.client.discovery_ads(
                    query=query,
                    limit=CATEGORY_FETCH_LIMIT,
                    order="longest_running",
                    running_duration_min_days=30,
                )
                audit["api_calls"] = audit.get("api_calls", 0) + 1
                audit["total_ads_seen"] = audit.get("total_ads_seen", 0) + len(ads)

                logger.info(f"[ADS_INTEL] Category query '{query}': {len(ads)} raw ads (longest_running, min 30d)")

                # Retry without min_days filter if 0 results
                if not ads:
                    ads = await self.client.discovery_ads(
                        query=query,
                        limit=CATEGORY_FETCH_LIMIT,
                        order="longest_running",
                    )
                    audit["api_calls"] = audit.get("api_calls", 0) + 1
                    audit["total_ads_seen"] = audit.get("total_ads_seen", 0) + len(ads)
                    logger.info(f"[ADS_INTEL] Category query '{query}' retry (no min_days): {len(ads)} raw ads")

                cleaned = postprocess_ads(ads, lens="category")
                for ad in cleaned:
                    ad["_source_query"] = query
                all_ads.extend(cleaned)

                logger.info(f"[ADS_INTEL] Category '{query}': {len(cleaned)} ads after postprocess (running total: {len(all_ads)})")

            except ForeplayAPIError as e:
                logger.warning(f"[ADS_INTEL] Foreplay error for category '{query}': {e}")
                audit.setdefault("errors", []).append(f"category:{query}: {str(e)}")
            except Exception as e:
                logger.warning(f"[ADS_INTEL] Error for category '{query}': {e}")
                audit.setdefault("errors", []).append(f"category:{query}: {str(e)}")

        return all_ads

    # ============== BUILD SNAPSHOT ==============

    def _build_ad_cards(self, ads: List[Dict[str, Any]], lens: str) -> List[AdCard]:
        """Convert raw ad dicts to AdCard models with composite scoring."""
        cards = []
        for ad in ads:
            score_data = ad.get("_score", {})
            cards.append(AdCard(
                ad_id=ad["ad_id"],
                brand_name=ad.get("brand_name"),
                brand_id=ad.get("brand_id"),
                publisher_platform=ad.get("publisher_platform", "unknown"),
                display_format=ad.get("display_format"),
                live=ad.get("live"),
                start_date=str(ad["start_date"]) if ad.get("start_date") else None,
                end_date=str(ad["end_date"]) if ad.get("end_date") else None,
                last_seen_date=str(ad["last_seen_date"]) if ad.get("last_seen_date") else None,
                running_days=ad.get("_running_days") or ad.get("running_days"),
                text=ad.get("text"),
                headline=ad.get("headline"),
                cta=ad.get("cta"),
                media_url=ad.get("media_url"),
                thumbnail_url=ad.get("thumbnail_url"),
                landing_page_url=ad.get("landing_page_url"),
                has_preview=ad.get("has_preview", True),
                score=score_data.get("total", 0) if isinstance(score_data, dict) else 0,
                tier=score_data.get("tier", "notable") if isinstance(score_data, dict) else "notable",
                score_signals=score_data.get("signals", {}) if isinstance(score_data, dict) else {},
                lens=lens,
                why_shortlisted=ad.get("why_shortlisted", "Shortlisted for relevance."),
            ))
        return cards

    # ============== MAIN PIPELINE ==============

    async def run(self, campaign_id: str) -> Dict[str, Any]:
        """Full Ad Intelligence pipeline."""
        logger.info(f"[ADS_INTEL] Starting pipeline for campaign {campaign_id}")

        # Load inputs
        brief = await self.db.campaign_briefs.find_one(
            {"campaign_brief_id": campaign_id}, {"_id": 0}
        )
        if not brief:
            raise ValueError("Campaign brief not found")

        website_pack = await self.db.website_context_packs.find_one(
            {"campaign_brief_id": campaign_id}, {"_id": 0}
        )
        if not website_pack:
            raise ValueError("Website context pack not found. Complete Step 2 first.")

        inputs = self._extract_inputs(brief, website_pack)
        audit = {"api_calls": 0, "total_ads_seen": 0, "errors": []}
        now = datetime.now(timezone.utc)

        # ---- COMPETITOR LENS ----
        competitor_list = await self._get_competitor_list(campaign_id)
        competitor_seeds = build_competitor_seeds(competitor_list)
        competitor_notes = []

        if not competitor_seeds:
            competitor_notes.append("No competitors available — run Competitors module first.")
            comp_shortlisted = []
        else:
            comp_raw = await self._run_competitor_lens(competitor_seeds, audit)
            comp_shortlisted = shortlist_competitor_ads(comp_raw, max_total=25)

        # ---- CATEGORY LENS ----
        category_search_terms = await self._get_category_search_terms(campaign_id)
        category_queries = build_category_queries(
            category_search_terms=category_search_terms,
            classification=inputs["classification"],
            offer=inputs["offer"],
            geo=inputs["geo"],
            brand_name=inputs.get("brand_name", ""),
            competitors=competitor_list,
        )
        cat_raw = await self._run_category_lens(category_queries, inputs["geo"], audit)
        cat_shortlisted = shortlist_category_ads(cat_raw, max_total=15, geo=inputs["geo"])

        # ---- BUILD SNAPSHOT ----
        comp_cards = self._build_ad_cards(comp_shortlisted, "competitor")
        cat_cards = self._build_ad_cards(cat_shortlisted, "category")

        # Compute winning patterns from scored ads (zero API cost)
        all_scored = comp_shortlisted + cat_shortlisted
        ad_patterns = compute_ad_patterns(all_scored)

        # Compute delta vs previous
        previous = await self.get_latest(campaign_id)
        delta = {}
        if previous:
            old_ids = set()
            for ad in previous.competitor_winners.ads + previous.category_winners.ads:
                old_ids.add(ad.ad_id)
            new_ids = {ad.ad_id for ad in comp_cards + cat_cards}
            delta = {
                "new_ads_count": len(new_ids - old_ids),
                "removed_ads_count": len(old_ids - new_ids),
            }

        snapshot = AdsIntelSnapshot(
            version="1.0",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs={
                "geo": inputs["geo"],
                "competitor_domains": [s["domain"] for s in competitor_seeds],
                "category_queries": category_queries,
                "platforms": ["facebook", "instagram", "tiktok"],
            },
            competitor_winners=AdsLensResult(
                ads=comp_cards,
                stats={
                    "total_raw": len(comp_shortlisted),
                    "brands_queried": len(competitor_seeds),
                },
                notes=competitor_notes,
            ),
            category_winners=AdsLensResult(
                ads=cat_cards,
                stats={
                    "total_raw": len(cat_shortlisted),
                    "queries_used": category_queries,
                },
            ),
            patterns=ad_patterns,
            audit={
                "api_calls": audit["api_calls"],
                "total_ads_seen": audit["total_ads_seen"],
                "kept": len(comp_cards) + len(cat_cards),
                "errors": audit.get("errors", []),
                "skipped_competitors": audit.get("skipped_competitors", []),
            },
            delta=delta,
        )

        # Save
        await self._save_snapshot(campaign_id, snapshot)

        total = len(comp_cards) + len(cat_cards)
        status = "success" if total >= 10 else "partial" if total >= 1 else "low_data"

        logger.info(
            f"[ADS_INTEL] Pipeline complete: {len(comp_cards)} competitor + {len(cat_cards)} category = {total} total"
        )

        # Auto-trigger Creative Analysis if Social Trends also has data
        if total > 0:
            try:
                from research.creative_analysis.service import CreativeAnalysisService
                ca_service = CreativeAnalysisService(self.db)
                has_social = bool(await self.db.research_packs.find_one(
                    {"campaign_id": campaign_id, "sources.social_trends.latest": {"$exists": True}},
                    {"_id": 0, "campaign_id": 1}
                ))
                if has_social:
                    asyncio.create_task(ca_service.run(campaign_id))
                    logger.info(f"[ADS_INTEL] Auto-triggered Creative Analysis for campaign {campaign_id}")
                else:
                    logger.info("[ADS_INTEL] Social Trends not ready yet, Creative Analysis deferred")
            except Exception as ca_err:
                logger.warning(f"[ADS_INTEL] Creative Analysis auto-trigger failed: {ca_err}")

        return {
            "status": status,
            "snapshot": snapshot.model_dump(mode="json"),
            "message": f"Shortlisted {len(comp_cards)} competitor + {len(cat_cards)} category ads ({total} total)",
        }

    # ============== PERSISTENCE ==============

    async def get_latest(self, campaign_id: str) -> Optional[AdsIntelSnapshot]:
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.ads_intel.latest": 1},
        )
        if not pack:
            return None
        latest = pack.get("sources", {}).get("ads_intel", {}).get("latest")
        if not latest:
            return None
        try:
            return AdsIntelSnapshot(**latest)
        except Exception as e:
            logger.warning(f"[ADS_INTEL] Failed to parse snapshot: {e}")
            return None

    async def get_history(self, campaign_id: str) -> List[AdsIntelSnapshot]:
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.ads_intel.history": 1},
        )
        if not pack:
            return []
        history = pack.get("sources", {}).get("ads_intel", {}).get("history", [])
        snapshots = []
        for item in history:
            try:
                snapshots.append(AdsIntelSnapshot(**item))
            except Exception:
                pass
        return snapshots

    async def _save_snapshot(self, campaign_id: str, snapshot: AdsIntelSnapshot):
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
                    "ads_intel": {"latest": snapshot_dict, "history": []},
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            })
        else:
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                {
                    "$set": {
                        "sources.ads_intel.latest": snapshot_dict,
                        "updated_at": now.isoformat(),
                    },
                    "$push": {
                        "sources.ads_intel.history": {
                            "$each": [snapshot_dict],
                            "$position": 0,
                            "$slice": HISTORY_CAP,
                        }
                    },
                },
            )
        logger.info(f"[ADS_INTEL] Saved snapshot for campaign {campaign_id}")
