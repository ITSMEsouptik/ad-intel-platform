"""
Novara Research Foundation: Seed Generation v3
Spec-aligned: base seeds + 5-pattern expansion

Version 3.0 - Dec 2025
- Base seeds from: niche, subcategory, offer_catalog, primary_action
- 5 query patterns per base seed: {seed}, {seed} {city}, {seed} near me, {seed} price, best {seed}
- Competitor seeds as separate group
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============== CONSTANTS ==============

MAX_BASE_SEEDS = 8  # Cap on base terms before expansion
MAX_EXPANDED_SEEDS = 40  # Cap on total seeds after expansion

# Workshop-related tokens for detection
WORKSHOP_TOKENS = ["workshop", "class", "training", "masterclass", "course", "session", "bootcamp", "academy"]


@dataclass
class KeywordSets:
    """Keyword sets derived from business context"""
    service_terms: List[str] = field(default_factory=list)
    category_terms: List[str] = field(default_factory=list)
    geo_terms: List[str] = field(default_factory=list)
    competitor_terms: List[str] = field(default_factory=list)
    sells_workshops: bool = False


@dataclass
class SeedGenerationInputs:
    """Structured inputs for seed generation"""
    # From Step 1 (campaign_briefs)
    city: str = ""
    country: str = ""
    language: str = "en"
    
    # From Step 2 (website_context_packs.step2)
    industry: str = ""
    subcategory: str = ""
    niche: str = ""
    tags: List[str] = None
    services: List[str] = None  # From offer_catalog[].name
    brand_name: str = ""
    primary_action: str = ""  # From conversion.primary_action
    headings: List[str] = None  # For workshop detection fallback
    
    # From Competitors module (research_packs.sources.competitors.latest)
    competitors: List[str] = None
    category_search_terms: List[str] = None
    
    def __post_init__(self):
        self.tags = self.tags or []
        self.services = self.services or []
        self.headings = self.headings or []
        self.competitors = self.competitors or []
        self.category_search_terms = self.category_search_terms or []


def detect_sells_workshops(inputs: SeedGenerationInputs) -> bool:
    """Detect if brand sells workshops/classes/training."""
    for service in inputs.services:
        service_lower = service.lower()
        for token in WORKSHOP_TOKENS:
            if token in service_lower:
                logger.info(f"Workshop detected in service: {service}")
                return True
    
    for heading in inputs.headings:
        heading_lower = heading.lower()
        for token in WORKSHOP_TOKENS:
            if token in heading_lower:
                logger.info(f"Workshop detected in heading: {heading}")
                return True
    
    return False


def _strip_geo_from_phrase(phrase: str, city: str, country: str) -> str:
    """Remove geo references from a phrase"""
    result = phrase.lower()
    for geo in [city.lower(), country.lower(), "uae", "uk", "usa", "india"]:
        if geo:
            result = result.replace(f" {geo}", "").replace(f"{geo} ", "").strip()
    return result.strip()


def extract_seed_inputs(
    campaign_brief: Dict[str, Any],
    website_context_pack: Dict[str, Any],
    competitors_snapshot: Optional[Dict[str, Any]] = None
) -> SeedGenerationInputs:
    """Extract seed generation inputs from existing packs"""
    
    # Step 1 inputs
    geo = campaign_brief.get("geo", {})
    city = geo.get("city_or_region", "")
    country = geo.get("country", "")
    
    # Step 2 inputs
    step2 = website_context_pack.get("step2", {})
    step2_internal = website_context_pack.get("step2_internal", {})
    old_data = website_context_pack.get("data", {})
    
    language = "en"
    industry = ""
    subcategory = ""
    niche = ""
    tags = []
    services = []
    brand_name = ""
    primary_action = ""
    headings = []
    
    if step2:
        classification = step2.get("classification", {})
        offer = step2.get("offer", {})
        brand_summary = step2.get("brand_summary", {})
        site = step2.get("site", {})
        conversion = step2.get("conversion", {})
        raw_extraction = step2_internal.get("raw_extraction", {})
        
        language = site.get("language", "en")
        
        for item in offer.get("offer_catalog", [])[:5]:
            name = item.get("name", "")
            if name and name.lower() not in ["unknown", "n/a", ""]:
                services.append(name)
        
        industry = classification.get("industry", "")
        subcategory = classification.get("subcategory", "")
        niche = classification.get("niche", "")
        tags = [t for t in classification.get("tags", []) if t and t.lower() != "unknown"]
        brand_name = brand_summary.get("name", "")
        primary_action = conversion.get("primary_action", "")
        headings = raw_extraction.get("headings", [])[:20] if raw_extraction else []
    
    elif old_data:
        old_offer = old_data.get("offer", {})
        old_brand = old_data.get("brand_identity", {})
        old_site = old_data.get("site", {})
        seed_insights = old_data.get("seed_insights", {})
        
        language = old_site.get("language", "en")
        brand_name = old_brand.get("brand_name", old_brand.get("name", old_site.get("title", "")))
        
        # Extract services from brand name patterns
        if brand_name and len(brand_name.split()) > 2:
            if "home service" in brand_name.lower():
                services.append("home service")
            if "hair" in brand_name.lower():
                services.append("hair")
            if "makeup" in brand_name.lower():
                services.append("makeup")
            if "beauty" in brand_name.lower():
                services.append("beauty")
        
        offer_summary = old_offer.get("primary_offer_summary", "")
        if offer_summary:
            summary_lower = offer_summary.lower()
            beauty_services = ["makeup", "hair", "beauty", "salon", "spa", "facial",
                              "manicure", "pedicure", "waxing", "bridal", "nail", "massage", "skincare"]
            for svc in beauty_services:
                if svc in summary_lower and svc not in services:
                    services.append(svc)
        
        for svc in old_offer.get("services", [])[:5]:
            if isinstance(svc, str) and svc.lower() not in ["unknown", ""]:
                services.append(svc)
            elif isinstance(svc, dict):
                name = svc.get("name", "")
                if name and name.lower() not in ["unknown", ""]:
                    services.append(name)
        
        if not industry:
            if any(kw in brand_name.lower() for kw in ["beauty", "makeup", "hair", "salon", "spa"]):
                industry = "beauty and wellness"
        
        industry = industry or seed_insights.get("industry", seed_insights.get("industry_hint", ""))
        subcategory = seed_insights.get("sub_industry", "")
        niche = seed_insights.get("niche", "")
        
        raw_tags = seed_insights.get("keywords", [])
        for tag in raw_tags:
            if not tag or "," in tag or len(tag) > 25 or len(tag) < 3:
                continue
            if tag.lower() in ["unknown", "unleash", "touch", "anywhere", "anytime"]:
                continue
            if tag.lower() not in tags:
                tags.append(tag.lower())
    
    # Competitors
    competitors = []
    category_search_terms = []
    
    if competitors_snapshot:
        for comp in competitors_snapshot.get("competitors", [])[:3]:
            name = comp.get("name", "")
            if name and name.lower() not in ["unknown", "n/a", ""]:
                competitors.append(name)
        category_search_terms = competitors_snapshot.get("category_search_terms", [])[:15]
    
    return SeedGenerationInputs(
        city=city,
        country=country,
        language=language,
        industry=industry,
        subcategory=subcategory,
        niche=niche,
        tags=tags,
        services=services,
        brand_name=brand_name,
        primary_action=primary_action,
        headings=headings,
        competitors=competitors,
        category_search_terms=category_search_terms
    )


def build_keyword_sets(inputs: SeedGenerationInputs) -> KeywordSets:
    """Build keyword sets from business context."""
    sells_workshops = detect_sells_workshops(inputs)
    
    # Service terms: extract simple keywords from offer_catalog
    service_terms = []
    service_keywords = {
        "makeup", "hair", "hairstyle", "haircut", "facial", "manicure", "pedicure",
        "waxing", "threading", "massage", "spa", "nails", "lashes", "brows",
        "bridal", "grooming", "skincare", "beauty", "styling", "blowout", "color",
        "highlights", "keratin", "extensions", "mehndi", "henna"
    }
    
    found_keywords = set()
    for service in inputs.services[:5]:
        service_lower = service.lower()
        for keyword in service_keywords:
            if keyword in service_lower and keyword not in found_keywords:
                found_keywords.add(keyword)
                service_terms.append(keyword)
    
    if not service_terms:
        for service in inputs.services[:3]:
            words = service.lower().strip().split()[:3]
            if words:
                service_terms.append(" ".join(words))
    
    if "makeup" in found_keywords and "hair" in found_keywords:
        service_terms.append("hair and makeup")
    if "makeup" in found_keywords:
        service_terms.append("makeup artist")
    if "bridal" in found_keywords:
        service_terms.append("bridal makeup")
    
    # Category terms
    category_terms = []
    
    if inputs.subcategory and inputs.subcategory.lower() != "unknown":
        subcat = _strip_geo_from_phrase(inputs.subcategory, inputs.city, inputs.country)
        if subcat:
            category_terms.append(subcat)
    
    if inputs.niche and inputs.niche.lower() != "unknown":
        niche = _strip_geo_from_phrase(inputs.niche, inputs.city, inputs.country)
        if niche and niche not in category_terms:
            category_terms.append(niche)
    
    geo_and_generic_tags = {
        "dubai", "abu dhabi", "sharjah", "london", "new york", "uae", "usa", "uk",
        "india", "mumbai", "corporate", "editorial", "workshops", "events", "luxury",
        "premium", "professional", "expert", "best", "top", "local"
    }
    
    for tag in inputs.tags[:5]:
        tag_lower = tag.lower().strip()
        if tag_lower in geo_and_generic_tags or tag_lower in category_terms or len(tag_lower) < 3:
            continue
        category_terms.append(tag_lower)
    
    for term in inputs.category_search_terms[:10]:
        term_lower = term.lower()
        if term_lower not in category_terms:
            category_terms.append(term_lower)
    
    # Geo terms
    geo_terms = []
    if inputs.city:
        geo_terms.append(inputs.city.lower())
    if inputs.country:
        geo_terms.append(inputs.country.lower())
    geo_terms.append("near me")
    
    # Competitor terms
    competitor_terms = [c.lower() for c in inputs.competitors[:3] if c]
    
    # Dedupe each list
    service_terms = list(dict.fromkeys(service_terms))
    category_terms = list(dict.fromkeys(category_terms))
    geo_terms = list(dict.fromkeys(geo_terms))
    competitor_terms = list(dict.fromkeys(competitor_terms))
    
    logger.info(f"Built keyword sets: services={len(service_terms)}, category={len(category_terms)}, "
                f"geo={len(geo_terms)}, competitors={len(competitor_terms)}, workshops={sells_workshops}")
    
    return KeywordSets(
        service_terms=service_terms,
        category_terms=category_terms,
        geo_terms=geo_terms,
        competitor_terms=competitor_terms,
        sells_workshops=sells_workshops
    )


def _dedupe_seeds(seeds: List[str]) -> List[str]:
    """Deduplicate seeds preserving order"""
    seen: Set[str] = set()
    deduped = []
    
    for seed in seeds:
        cleaned = " ".join(seed.lower().split()).strip(".,;:!?")
        if cleaned and cleaned not in seen and len(cleaned) >= 3:
            seen.add(cleaned)
            deduped.append(cleaned)
    
    return deduped


def generate_base_seeds(inputs: SeedGenerationInputs, keyword_sets: KeywordSets) -> List[str]:
    """
    Generate BASE seed terms (before pattern expansion).
    
    Sources per spec:
    - Step 2: niche, subcategory, offer_catalog items (service_terms), primary_action
    - Competitors: competitor names (if exists)
    """
    base_seeds: List[str] = []
    
    # 1. Niche (highest priority)
    if inputs.niche and inputs.niche.lower() != "unknown":
        niche = _strip_geo_from_phrase(inputs.niche, inputs.city, inputs.country)
        if niche:
            base_seeds.append(niche)
    
    # 2. Subcategory
    if inputs.subcategory and inputs.subcategory.lower() != "unknown":
        subcat = _strip_geo_from_phrase(inputs.subcategory, inputs.city, inputs.country)
        if subcat and subcat not in base_seeds:
            base_seeds.append(subcat)
    
    # 3. Service terms from offer_catalog
    for term in keyword_sets.service_terms[:4]:
        if term not in base_seeds:
            base_seeds.append(term)
    
    # 4. Competitor names (separate group, limited)
    for comp in keyword_sets.competitor_terms[:2]:
        if comp not in base_seeds:
            base_seeds.append(comp)
    
    return _dedupe_seeds(base_seeds[:MAX_BASE_SEEDS])


def expand_seeds_with_patterns(base_seeds: List[str], city: str) -> List[str]:
    """
    Expand each base seed with 5 query patterns per spec:
    1. {seed}
    2. {seed} {city}
    3. {seed} near me
    4. {seed} price
    5. best {seed}
    """
    expanded: List[str] = []
    city_lower = city.lower().strip() if city else ""
    
    for seed in base_seeds:
        # Pattern 1: {seed}
        expanded.append(seed)
        
        # Pattern 2: {seed} {city}
        if city_lower and city_lower not in seed:
            expanded.append(f"{seed} {city_lower}")
        
        # Pattern 3: {seed} near me
        if "near me" not in seed:
            expanded.append(f"{seed} near me")
        
        # Pattern 4: {seed} price
        if "price" not in seed:
            expanded.append(f"{seed} price")
        
        # Pattern 5: best {seed}
        if not seed.startswith("best "):
            expanded.append(f"best {seed}")
    
    return expanded


def generate_seeds(inputs: SeedGenerationInputs, keyword_sets: KeywordSets) -> List[str]:
    """
    Generate seed phrases for Google Suggest (spec-aligned v3).
    
    1. Generate base seeds from niche/subcategory/services/competitors
    2. Expand each base seed with 5 patterns
    3. Dedupe and cap
    
    Returns:
        List of unique seed phrases
    """
    # Generate base seeds
    base_seeds = generate_base_seeds(inputs, keyword_sets)
    
    logger.info(f"Base seeds ({len(base_seeds)}): {base_seeds}")
    
    if not base_seeds:
        logger.warning("[SEEDS] No base seeds generated")
        return []
    
    # Expand with 5-pattern approach
    city = inputs.city or ""
    expanded = expand_seeds_with_patterns(base_seeds, city)
    
    # Dedupe and cap
    final_seeds = _dedupe_seeds(expanded)[:MAX_EXPANDED_SEEDS]
    
    logger.info(f"Generated {len(final_seeds)} seeds from {len(base_seeds)} base seeds")
    
    return final_seeds


def get_seed_generation_config() -> Dict[str, Any]:
    """Return configuration used for seed generation"""
    return {
        "max_base_seeds": MAX_BASE_SEEDS,
        "max_expanded_seeds": MAX_EXPANDED_SEEDS,
        "patterns": ["{seed}", "{seed} {city}", "{seed} near me", "{seed} price", "best {seed}"],
        "workshop_tokens": WORKSHOP_TOKENS,
        "version": "3.0"
    }
