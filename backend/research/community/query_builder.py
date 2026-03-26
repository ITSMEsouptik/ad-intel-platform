"""
Novara Research Foundation: Community Intelligence — Query Builder
Version 1.0 - Feb 2026

Generates search queries across 5 families:
1. Pain/objection
2. Best/recommendation
3. Price/value
4. Comparison
5. Trust/legit

Domain allowlist + exclusion lists for forum-specific targeting.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ============== DOMAIN CONFIGURATION ==============

# Allowed forum/community domains
DOMAIN_ALLOWLIST = [
    "reddit.com",
    "quora.com",
    "medium.com",
    "stackexchange.com",
    "indiehackers.com",
    "producthunt.com",
    "hackernews.ycombinator.com",
]

# Niche-specific forum additions
NICHE_FORUMS = {
    "software": ["stackexchange.com", "indiehackers.com", "producthunt.com", "hackernews.ycombinator.com"],
    "saas": ["stackexchange.com", "indiehackers.com", "producthunt.com", "hackernews.ycombinator.com"],
    "ecommerce": ["reddit.com", "quora.com"],
    "beauty": ["reddit.com", "quora.com"],
    "salon": ["reddit.com", "quora.com"],
    "restaurant": ["reddit.com", "quora.com"],
    "food": ["reddit.com", "quora.com"],
    "hotel": ["reddit.com", "quora.com", "tripadvisor.com/ShowTopic"],
    "medical": ["reddit.com", "quora.com", "healthboards.com"],
    "dental": ["reddit.com", "quora.com"],
    "fitness": ["reddit.com", "quora.com", "bodybuilding.com/forum"],
    "real estate": ["reddit.com", "quora.com", "biggerpockets.com"],
    "education": ["reddit.com", "quora.com", "studentroom.co.uk"],
    "automotive": ["reddit.com", "quora.com"],
    "travel": ["reddit.com", "quora.com"],
    "financial": ["reddit.com", "quora.com", "bogleheads.org"],
}

# Domains to EXCLUDE (reviews + employee sites handled separately)
EXCLUDED_DOMAINS = [
    "trustpilot.com", "yelp.com", "g2.com", "capterra.com",
    "google.com/maps", "facebook.com/reviews", "productreview.com.au",
    "glassdoor.com", "indeed.com", "comparably.com", "ambitionbox.com",
    "naukri.com", "kununu.com", "payscale.com",
]

# ============== QUERY FAMILIES ==============

def build_query_plan(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    competitor_names: Optional[List[str]] = None,
    pains_from_intel: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build a structured query plan with 5 families.
    Returns dict with queries list and metadata.
    """

    location = city if city else country
    service_tokens = services[:4] if services else [subcategory]
    comp_names = competitor_names[:3] if competitor_names else []

    queries = []
    families_used = set()

    # Family 1: Pain / Objection
    pain_templates = [
        "{service} problems",
        "{service} issues",
        "why {service} expensive",
        "{service} not worth it",
        "{service} complaints",
        "bad experience {service} {location}",
    ]
    if pains_from_intel:
        for pain in pains_from_intel[:2]:
            pain_templates.append(f"{{service}} {pain}")

    for svc in service_tokens[:2]:
        for tmpl in pain_templates[:4]:
            q = tmpl.format(service=svc, location=location)
            queries.append({"query": q, "family": "pain"})
            families_used.add("pain")

    # Family 2: Best / Recommendation
    rec_templates = [
        "best {service} {location}",
        "{service} recommendation {location}",
        "which {service} {location} reddit",
        "looking for {service} {location}",
    ]
    for svc in service_tokens[:2]:
        for tmpl in rec_templates[:3]:
            q = tmpl.format(service=svc, location=location)
            queries.append({"query": q, "family": "recommendation"})
            families_used.add("recommendation")

    # Family 3: Price / Value
    price_templates = [
        "{service} cost {location}",
        "{service} worth it",
        "{service} pricing",
        "how much {service} {location}",
    ]
    for svc in service_tokens[:2]:
        for tmpl in price_templates[:3]:
            q = tmpl.format(service=svc, location=location)
            queries.append({"query": q, "family": "price"})
            families_used.add("price")

    # Family 4: Comparison
    if comp_names:
        for comp in comp_names[:2]:
            queries.append({"query": f"{brand_name} vs {comp}", "family": "comparison"})
            queries.append({"query": f"{comp} alternative {location}", "family": "comparison"})
            families_used.add("comparison")
    else:
        for svc in service_tokens[:1]:
            queries.append({"query": f"{svc} alternative {location}", "family": "comparison"})
            queries.append({"query": f"best {svc} compared {location}", "family": "comparison"})
            families_used.add("comparison")

    # Family 5: Trust / Legit
    trust_templates = [
        "{brand} legit",
        "{brand} reviews reddit",
        "{brand} scam",
        "{brand} experience",
    ]
    for tmpl in trust_templates:
        q = tmpl.format(brand=brand_name)
        queries.append({"query": q, "family": "trust"})
        families_used.add("trust")

    # Cap at 40 queries
    queries = queries[:40]

    # Get relevant forum domains for this niche
    target_domains = _get_target_domains(niche, subcategory)

    plan = {
        "total_queries": len(queries),
        "families": list(families_used),
        "queries": queries,
        "target_domains": target_domains,
        "excluded_domains": EXCLUDED_DOMAINS,
    }

    logger.info(
        f"[COMMUNITY] Query plan: {len(queries)} queries across {len(families_used)} families, "
        f"targeting {len(target_domains)} domains"
    )

    return plan


def _get_target_domains(niche: str, subcategory: str) -> List[str]:
    """Get forum domains relevant to this niche."""
    domains = set(DOMAIN_ALLOWLIST)

    for key in [niche.lower(), subcategory.lower()]:
        if key in NICHE_FORUMS:
            domains.update(NICHE_FORUMS[key])

    return sorted(list(domains))
