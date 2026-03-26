"""
Novara Research Foundation: Reviews & Reputation Service
Version 1.5 - Feb 2026

Orchestrates:
1. Gather inputs (Step 1 + Step 2 + Competitors)
2. Extract brand claims for cross-referencing
3. Detect app store URLs from Step 2 channels
4. Determine geo + niche platforms (incl. app stores)
5. Call Perplexity (Discovery — with recency + owner response)
6. Call Perplexity (Deep Analysis — with brand vs reality)
7. Post-process + compute readiness score
8. Build snapshot + save
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from .schema import (
    ReviewsSnapshot,
    ReviewsDelta,
    ReviewsAudit,
    ReviewsInputs,
    ReviewPlatform,
    StrengthTheme,
    WeaknessTheme,
    SocialProofSnippet,
    CompetitorReputation,
    BrandVsReality,
    BrandClaimCheck,
)
from .perplexity_reviews import (
    PERPLEXITY_MODEL,
    get_platforms_for_context,
    fetch_reviews_discovery,
    fetch_reviews_analysis,
)
from .postprocess import postprocess_reviews

logger = logging.getLogger(__name__)

REFRESH_DAYS = 30
HISTORY_CAP = 10


class ReviewsService:
    def __init__(self, db):
        self.db = db

    def extract_inputs(
        self,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract inputs for reviews pipeline, including brand claims and app store URLs."""

        geo = campaign_brief.get("geo", {})
        city = geo.get("city_or_region", "")
        country = geo.get("country", "")

        step2 = website_context_pack.get("step2", {})
        site = step2.get("site", {})
        classification = step2.get("classification", {})
        offer = step2.get("offer", {})
        brand_summary = step2.get("brand_summary", {})
        channels = step2.get("channels", {})

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

        # v1.5: Extract app store URLs from channels
        app_store_urls = []
        for app_link in channels.get("apps", []):
            url = app_link.get("url", "") if isinstance(app_link, dict) else str(app_link)
            if url:
                app_store_urls.append(url)

        # v1.5: Extract brand claims for cross-referencing
        brand_claims = []
        value_prop = offer.get("value_prop", "")
        if value_prop and value_prop != "unknown":
            brand_claims.append(value_prop)
        for benefit in offer.get("key_benefits", [])[:5]:
            if benefit and benefit != "unknown":
                brand_claims.append(benefit)
        for bullet in bullets[:3]:
            if bullet and bullet not in brand_claims:
                brand_claims.append(bullet)

        return {
            "geo": {"city": city, "country": country},
            "brand_name": brand_name,
            "domain": domain,
            "subcategory": subcategory,
            "niche": niche,
            "services": services,
            "brand_overview": brand_overview,
            "app_store_urls": app_store_urls,
            "brand_claims": brand_claims,
        }

    async def run(
        self,
        campaign_id: str,
        campaign_brief: Dict[str, Any],
        website_context_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Full pipeline: discovery -> analysis -> postprocess -> save."""

        try:
            logger.info(f"[REVIEWS] Starting v1.5 pipeline for campaign {campaign_id}")

            # 1. Extract inputs
            inputs = self.extract_inputs(campaign_brief, website_context_pack)
            city = inputs["geo"]["city"]
            country = inputs["geo"]["country"]

            logger.info(f"[REVIEWS] Brand: {inputs['brand_name']}, Location: {city or country}")
            logger.info(f"[REVIEWS] App store URLs: {inputs['app_store_urls']}")
            logger.info(f"[REVIEWS] Brand claims for cross-ref: {len(inputs['brand_claims'])}")

            # 2. Get geo + niche platforms (including app stores)
            geo_platforms, niche_platforms, combined_platforms = get_platforms_for_context(
                country=country,
                niche=inputs["niche"],
                subcategory=inputs["subcategory"],
                app_store_urls=inputs["app_store_urls"]
            )

            logger.info(f"[REVIEWS] Platforms to check: {len(combined_platforms)} ({len(geo_platforms)} geo + {len(niche_platforms)} niche)")

            # 3. Call 1: Discovery (with app store hints)
            discovery_result = await fetch_reviews_discovery(
                brand_name=inputs["brand_name"],
                domain=inputs["domain"],
                city=city,
                country=country,
                subcategory=inputs["subcategory"],
                niche=inputs["niche"],
                services=inputs["services"],
                brand_overview=inputs["brand_overview"],
                platforms_to_check=combined_platforms,
                app_store_urls=inputs["app_store_urls"]
            )

            if not discovery_result:
                raise RuntimeError("Reviews discovery call failed — no response from Perplexity")

            discovery_tokens = discovery_result.pop("_tokens", 0)
            platforms_found = discovery_result.get("platforms_found", [])
            logger.info(f"[REVIEWS] Discovery found {len(platforms_found)} platforms")

            # 3b. Fallback: if 0 platforms found, retry with broader category search
            from .postprocess import _is_employee_review_site, _url_has_wrong_city
            valid_platforms = [
                p for p in platforms_found
                if p.get("has_reviews")
                and not _is_employee_review_site(p.get("url", ""))
                and not (city and _url_has_wrong_city(p.get("url", ""), city))
            ]

            if len(valid_platforms) == 0:
                logger.info("[REVIEWS] 0 valid platforms found, trying broader category search...")
                broad_result = await fetch_reviews_discovery(
                    brand_name=inputs["brand_name"],
                    domain=inputs["domain"],
                    city=city,
                    country=country,
                    subcategory=inputs["subcategory"],
                    niche=inputs["niche"],
                    services=inputs["services"],
                    brand_overview=inputs["brand_overview"],
                    platforms_to_check=combined_platforms,
                    app_store_urls=inputs["app_store_urls"],
                    broad_search=True
                )
                if broad_result:
                    broad_tokens = broad_result.pop("_tokens", 0)
                    discovery_tokens += broad_tokens
                    broad_platforms = broad_result.get("platforms_found", [])
                    # Filter employee review sites from broad results too
                    valid_broad = [
                        p for p in broad_platforms
                        if p.get("has_reviews")
                        and not _is_employee_review_site(p.get("url", ""))
                        and not (city and _url_has_wrong_city(p.get("url", ""), city))
                    ]
                    if valid_broad:
                        logger.info(f"[REVIEWS] Broad search found {len(valid_broad)} valid platforms")
                        discovery_result["platforms_found"] = valid_broad
                        platforms_found = valid_broad
                        valid_platforms = valid_broad
                    else:
                        logger.info(f"[REVIEWS] Broad search found {len(broad_platforms)} platforms but none valid after filtering")

            # 4. Get competitor names for comparison
            competitor_names = await self._get_competitor_names(campaign_id)

            # 4a. Check if discovery found any valid platforms (re-check after broad search)
            has_review_platforms = len(valid_platforms) > 0

            # 5. Call 2: Deep Analysis
            # Only pass brand_claims if we have platforms with actual reviews
            analysis_result = await fetch_reviews_analysis(
                brand_name=inputs["brand_name"],
                domain=inputs["domain"],
                city=city,
                country=country,
                subcategory=inputs["subcategory"],
                niche=inputs["niche"],
                services=inputs["services"],
                brand_overview=inputs["brand_overview"],
                discovery_results=discovery_result,
                competitor_names=competitor_names,
                brand_claims=inputs["brand_claims"] if has_review_platforms else None
            )

            if not analysis_result:
                raise RuntimeError("Reviews analysis call failed — no response from Perplexity")

            analysis_tokens = analysis_result.pop("_tokens", 0)

            # 6. Post-process (includes readiness score computation)
            # Skip BVR claims if no review platforms
            processed, pp_stats = postprocess_reviews(
                discovery_result,
                analysis_result,
                brand_city=city,
                brand_domain=inputs["domain"],
                brand_claims=inputs["brand_claims"]
            )

            # 7. Build snapshot
            snapshot = self._build_snapshot(
                processed=processed,
                inputs=inputs,
                geo_platforms=geo_platforms,
                niche_platforms=niche_platforms,
                discovery_tokens=discovery_tokens,
                analysis_tokens=analysis_tokens,
                pp_stats=pp_stats
            )

            # 8. Compute delta
            previous = await self.get_latest(campaign_id)
            if previous:
                snapshot.delta = self._compute_delta(previous, snapshot)

            # 9. Save
            await self.save_snapshot(campaign_id, snapshot)

            # Determine status
            platform_count = len(snapshot.platform_presence)
            strength_count = len(snapshot.strength_themes)

            if platform_count >= 2 and strength_count >= 2:
                status = "success"
            elif platform_count >= 1 or strength_count >= 1:
                status = "partial"
            else:
                status = "low_data"

            logger.info(
                f"[REVIEWS] Pipeline complete: {platform_count} platforms, "
                f"{strength_count} strengths, readiness={snapshot.social_proof_readiness}, status={status}"
            )

            return {
                "status": status,
                "snapshot": snapshot.model_dump(mode="json"),
                "message": f"Found reviews on {platform_count} platforms, {strength_count} strength themes, readiness: {snapshot.social_proof_readiness}"
            }

        except Exception as e:
            logger.exception(f"[REVIEWS] Pipeline error: {e}")
            return {
                "status": "failed",
                "snapshot": None,
                "message": str(e)
            }

    async def _get_competitor_names(self, campaign_id: str) -> List[str]:
        """Get competitor names from existing research pack."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.competitors.latest.competitors": 1}
        )
        if not pack:
            return []

        competitors = (pack.get("sources", {})
                         .get("competitors", {})
                         .get("latest", {})
                         .get("competitors", []))

        return [c.get("name", "") for c in competitors[:3] if c.get("name")]

    def _build_snapshot(
        self,
        processed: Dict[str, Any],
        inputs: Dict[str, Any],
        geo_platforms: List[str],
        niche_platforms: List[str],
        discovery_tokens: int,
        analysis_tokens: int,
        pp_stats: Dict[str, Any]
    ) -> ReviewsSnapshot:
        """Build validated snapshot from processed data."""
        now = datetime.now(timezone.utc)

        # Parse platforms
        platforms = []
        total_reviews = 0
        for p in processed.get("platform_presence", []):
            platforms.append(ReviewPlatform(
                platform=p.get("platform", ""),
                url=p.get("url"),
                approximate_rating=p.get("approximate_rating"),
                approximate_count=p.get("approximate_count"),
                has_reviews=p.get("has_reviews", False),
                recency=p.get("recency", "unknown"),
                owner_responds=p.get("owner_responds"),
                response_quality=p.get("response_quality", "unknown"),
                is_app_store=p.get("is_app_store", False),
            ))
            count_str = p.get("approximate_count", "") or ""
            try:
                num = int(''.join(filter(str.isdigit, str(count_str))))
                total_reviews += num
            except (ValueError, TypeError):
                pass

        # Parse strength themes
        strengths = [
            StrengthTheme(
                theme=s.get("theme", ""),
                evidence=s.get("evidence", []),
                frequency=s.get("frequency", "moderate")
            ) for s in processed.get("strength_themes", [])
        ]

        # Parse weakness themes
        weaknesses = [
            WeaknessTheme(
                theme=w.get("theme", ""),
                evidence=w.get("evidence", []),
                frequency=w.get("frequency", "moderate"),
                severity=w.get("severity", "minor")
            ) for w in processed.get("weakness_themes", [])
        ]

        # Parse snippets (with is_paraphrased)
        snippets = [
            SocialProofSnippet(
                quote=sn.get("quote", ""),
                platform=sn.get("platform", ""),
                context=sn.get("context", ""),
                is_paraphrased=sn.get("is_paraphrased", True),
            ) for sn in processed.get("social_proof_snippets", [])
        ]

        # Parse competitor reputation
        comp_rep = [
            CompetitorReputation(
                name=cr.get("name", ""),
                approximate_rating=cr.get("approximate_rating"),
                primary_platform=cr.get("primary_platform", ""),
                reputation_gap=cr.get("reputation_gap", "")
            ) for cr in processed.get("competitor_reputation", [])
        ]

        # Parse brand vs reality (v1.5)
        bvr_checks = [
            BrandClaimCheck(
                claim=c.get("claim", ""),
                review_alignment=c.get("review_alignment", "not_mentioned"),
                evidence=c.get("evidence", ""),
            ) for c in processed.get("brand_vs_reality", [])
        ]
        bvr = BrandVsReality(
            claims_checked=len(bvr_checks),
            supported=sum(1 for c in bvr_checks if c.review_alignment == "supported"),
            contradicted=sum(1 for c in bvr_checks if c.review_alignment == "contradicted"),
            not_mentioned=sum(1 for c in bvr_checks if c.review_alignment == "not_mentioned"),
            checks=bvr_checks,
            summary=self._build_bvr_summary(bvr_checks),
        )

        # Build audit
        audit = ReviewsAudit(
            platforms_checked=len(geo_platforms) + len(niche_platforms),
            platforms_with_reviews=len([p for p in platforms if p.has_reviews]),
            total_approximate_reviews=total_reviews,
            discovery_model=PERPLEXITY_MODEL,
            analysis_model=PERPLEXITY_MODEL,
            discovery_tokens=discovery_tokens,
            analysis_tokens=analysis_tokens,
            geo_platforms_used=geo_platforms,
            niche_platforms_used=niche_platforms,
            postprocess_stats=pp_stats
        )

        inputs_used = ReviewsInputs(
            geo=inputs["geo"],
            brand_name=inputs["brand_name"],
            domain=inputs["domain"],
            subcategory=inputs["subcategory"],
            niche=inputs["niche"],
            services=inputs["services"],
            brand_overview=inputs["brand_overview"],
            app_store_urls=inputs.get("app_store_urls", []),
            brand_claims=inputs.get("brand_claims", []),
        )

        return ReviewsSnapshot(
            version="1.5",
            captured_at=now,
            refresh_due_at=now + timedelta(days=REFRESH_DAYS),
            inputs_used=inputs_used,
            social_proof_readiness=processed.get("social_proof_readiness", "unknown"),
            reputation_summary=processed.get("reputation_summary", []),
            platform_presence=platforms,
            strength_themes=strengths,
            weakness_themes=weaknesses,
            social_proof_snippets=snippets,
            trust_signals=processed.get("trust_signals", []),
            competitor_reputation=comp_rep,
            brand_vs_reality=bvr,
            audit=audit,
            delta=ReviewsDelta()
        )

    def _build_bvr_summary(self, checks: List[BrandClaimCheck]) -> str:
        """Generate a one-line summary of brand vs reality alignment."""
        if not checks:
            return ""
        total = len(checks)
        supported = sum(1 for c in checks if c.review_alignment == "supported")
        contradicted = sum(1 for c in checks if c.review_alignment == "contradicted")

        if supported == total:
            return "All brand claims are backed by customer reviews"
        elif contradicted == 0:
            return f"{supported}/{total} brand claims supported by reviews, none contradicted"
        elif contradicted >= total / 2:
            return f"Caution: {contradicted}/{total} brand claims contradicted by customer feedback"
        else:
            return f"{supported}/{total} claims supported, {contradicted} contradicted by reviews"

    def _compute_delta(self, old: ReviewsSnapshot, new: ReviewsSnapshot) -> ReviewsDelta:
        """Compute changes between snapshots."""
        notable = []

        old_ratings = {p.platform: p.approximate_rating for p in old.platform_presence if p.approximate_rating}
        new_ratings = {p.platform: p.approximate_rating for p in new.platform_presence if p.approximate_rating}

        for platform, new_rating in new_ratings.items():
            old_rating = old_ratings.get(platform)
            if old_rating and new_rating != old_rating:
                diff = new_rating - old_rating
                direction = "up" if diff > 0 else "down"
                notable.append(f"{platform}: {old_rating} -> {new_rating} ({direction})")

        old_platforms = {p.platform for p in old.platform_presence}
        new_platforms = {p.platform for p in new.platform_presence}
        added = new_platforms - old_platforms
        if added:
            notable.append(f"New platforms: {', '.join(list(added)[:2])}")

        # v1.5: Track readiness score changes
        if old.social_proof_readiness != new.social_proof_readiness:
            notable.append(f"Readiness: {old.social_proof_readiness} -> {new.social_proof_readiness}")

        rating_change = None
        for platform_name in ["Google Maps", "Google"]:
            old_r = old_ratings.get(platform_name)
            new_r = new_ratings.get(platform_name)
            if old_r and new_r:
                rating_change = round(new_r - old_r, 1)
                break

        return ReviewsDelta(
            previous_captured_at=old.captured_at,
            notable_changes=notable[:5],
            rating_change=rating_change
        )

    async def get_latest(self, campaign_id: str) -> Optional[ReviewsSnapshot]:
        """Get latest Reviews snapshot."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.reviews.latest": 1}
        )
        if not pack:
            return None

        latest = pack.get("sources", {}).get("reviews", {}).get("latest")
        if not latest:
            return None

        try:
            return ReviewsSnapshot(**latest)
        except Exception as e:
            logger.warning(f"[REVIEWS] Failed to parse snapshot: {e}")
            return None

    async def save_snapshot(self, campaign_id: str, snapshot: ReviewsSnapshot):
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
                    "reviews": {"latest": snapshot_dict, "history": []},
                    "customer_intel": {"latest": None, "history": []},
                    "search_intent": {"latest": None, "history": []},
                    "seasonality": {"latest": None, "history": []},
                    "competitors": {"latest": None, "history": []}
                },
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            })
        else:
            await self.db.research_packs.update_one(
                {"campaign_id": campaign_id},
                {
                    "$set": {
                        "sources.reviews.latest": snapshot_dict,
                        "updated_at": now.isoformat()
                    },
                    "$push": {
                        "sources.reviews.history": {
                            "$each": [snapshot_dict],
                            "$position": 0,
                            "$slice": HISTORY_CAP
                        }
                    }
                }
            )

        logger.info(f"[REVIEWS] Saved v1.5 snapshot for campaign {campaign_id}")

    async def get_history(self, campaign_id: str) -> List[ReviewsSnapshot]:
        """Get Reviews history."""
        pack = await self.db.research_packs.find_one(
            {"campaign_id": campaign_id},
            {"_id": 0, "sources.reviews.history": 1}
        )
        if not pack:
            return []

        history = pack.get("sources", {}).get("reviews", {}).get("history", [])
        snapshots = []
        for item in history:
            try:
                snapshots.append(ReviewsSnapshot(**item))
            except Exception as e:
                logger.warning(f"[REVIEWS] Failed to parse history snapshot: {e}")
        return snapshots
