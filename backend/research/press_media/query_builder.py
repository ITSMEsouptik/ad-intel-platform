"""
Novara Research Foundation: Press & Media Intelligence — Query Builder
Version 1.0 - Feb 2026

Generates search queries across 5 families:
1. Brand coverage — direct brand mentions in press
2. Industry/category news — broader industry coverage
3. Founder/leadership — people behind the brand
4. Awards/recognition — accolades and rankings
5. Controversy/issues — negative coverage
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============== PRESS DOMAIN TARGETING ==============

# High-authority press/media domains to search
PRESS_DOMAINS_GLOBAL = [
    "forbes.com", "bloomberg.com", "reuters.com", "bbc.com",
    "techcrunch.com", "wired.com", "theverge.com",
    "entrepreneur.com", "inc.com", "businessinsider.com",
]

PRESS_DOMAINS_REGIONAL = {
    "UAE": ["gulfnews.com", "khaleejtimes.com", "arabianbusiness.com", "thenationalnews.com", "timeoutdubai.com"],
    "United Arab Emirates": ["gulfnews.com", "khaleejtimes.com", "arabianbusiness.com", "thenationalnews.com", "timeoutdubai.com"],
    "Saudi Arabia": ["arabnews.com", "saudigazette.com.sa", "arabianbusiness.com"],
    "India": ["economictimes.indiatimes.com", "livemint.com", "yourstory.com", "inc42.com"],
    "United States": ["nytimes.com", "washingtonpost.com", "cnbc.com", "fortune.com"],
    "United Kingdom": ["theguardian.com", "telegraph.co.uk", "independent.co.uk", "cityam.com"],
    "Australia": ["smh.com.au", "afr.com", "news.com.au"],
    "Singapore": ["straitstimes.com", "channelnewsasia.com", "businesstimes.com.sg"],
    "Germany": ["handelsblatt.com", "spiegel.de"],
    "Canada": ["globeandmail.com", "financialpost.com"],
}

NICHE_PRESS_DOMAINS = {
    "beauty": ["allure.com", "vogue.com", "elle.com", "cosmopolitan.com", "byrdie.com", "refinery29.com"],
    "salon": ["allure.com", "vogue.com", "elle.com", "byrdie.com"],
    "restaurant": ["eater.com", "foodandwine.com", "bon appetit", "timeout.com"],
    "food": ["eater.com", "foodandwine.com", "delish.com"],
    "hotel": ["cntraveler.com", "travelandleisure.com", "lonelyplanet.com", "tripadvisor.com/Tourism"],
    "hospitality": ["cntraveler.com", "travelandleisure.com", "hotelmanagement.net"],
    "medical": ["healthline.com", "webmd.com", "medicalnewstoday.com"],
    "dental": ["healthline.com", "webmd.com"],
    "fitness": ["menshealth.com", "womenshealthmag.com", "shape.com"],
    "software": ["techcrunch.com", "producthunt.com", "venturebeat.com", "sifted.eu"],
    "saas": ["techcrunch.com", "saastr.com", "venturebeat.com"],
    "ecommerce": ["retaildive.com", "digitalcommerce360.com", "shopify.com/blog"],
    "real estate": ["propertyfinder.ae", "bayut.com/mybayut", "arabianbusiness.com"],
    "education": ["edtechmagazine.com", "edsurge.com"],
    "financial": ["finextra.com", "paymentsdive.com"],
    "automotive": ["motortrend.com", "caranddriver.com", "autocar.co.uk"],
    "travel": ["cntraveler.com", "travelandleisure.com", "lonelyplanet.com"],
}

# Domains to EXCLUDE (forums, review platforms, employee sites)
EXCLUDED_DOMAINS = [
    "reddit.com", "quora.com", "stackexchange.com",
    "trustpilot.com", "yelp.com", "g2.com", "capterra.com",
    "glassdoor.com", "indeed.com", "comparably.com",
    "google.com/maps", "facebook.com",
]


def build_query_plan(
    brand_name: str,
    domain: str,
    city: str,
    country: str,
    subcategory: str,
    niche: str,
    services: List[str],
    competitor_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build a structured query plan with 5 families for press/media discovery.
    """

    location = city if city else country
    service_tokens = services[:3] if services else [subcategory]

    queries = []
    families_used = set()

    # Family 1: Brand coverage (direct mentions)
    brand_templates = [
        '"{brand}" news',
        '"{brand}" press',
        '"{brand}" {location} article',
        '"{brand}" interview',
        '"{brand}" feature',
        '"{brand}" announcement',
    ]
    for tmpl in brand_templates[:5]:
        q = tmpl.format(brand=brand_name, location=location)
        queries.append({"query": q, "family": "brand_coverage"})
        families_used.add("brand_coverage")

    # Family 2: Industry/category news
    industry_templates = [
        "{service} industry {location} news",
        "{service} market {location}",
        "best {service} {location} article",
        "{service} trends {location}",
    ]
    for svc in service_tokens[:2]:
        for tmpl in industry_templates[:3]:
            q = tmpl.format(service=svc, location=location)
            queries.append({"query": q, "family": "industry_news"})
            families_used.add("industry_news")

    # Family 3: Founder / leadership
    founder_templates = [
        '"{brand}" founder interview',
        '"{brand}" CEO profile',
        '"{brand}" story origin',
    ]
    for tmpl in founder_templates[:2]:
        q = tmpl.format(brand=brand_name)
        queries.append({"query": q, "family": "leadership"})
        families_used.add("leadership")

    # Family 4: Awards / recognition
    awards_templates = [
        '"{brand}" award',
        '"{brand}" best {subcategory} {location}',
        '"{brand}" ranking',
        '"{brand}" recognition',
    ]
    for tmpl in awards_templates[:3]:
        q = tmpl.format(brand=brand_name, subcategory=subcategory, location=location)
        queries.append({"query": q, "family": "awards"})
        families_used.add("awards")

    # Family 5: Controversy / negative coverage
    controversy_templates = [
        '"{brand}" controversy',
        '"{brand}" complaint news',
        '"{brand}" issue',
    ]
    for tmpl in controversy_templates[:2]:
        q = tmpl.format(brand=brand_name)
        queries.append({"query": q, "family": "controversy"})
        families_used.add("controversy")

    # Cap at 25 queries (press is more focused than community)
    queries = queries[:25]

    # Get relevant press domains for this context
    target_domains = _get_target_domains(country, niche, subcategory)

    plan = {
        "total_queries": len(queries),
        "families": list(families_used),
        "queries": queries,
        "target_domains": target_domains,
        "excluded_domains": EXCLUDED_DOMAINS,
    }

    logger.info(
        f"[PRESS] Query plan: {len(queries)} queries across {len(families_used)} families, "
        f"targeting {len(target_domains)} domains"
    )

    return plan


def _get_target_domains(country: str, niche: str, subcategory: str) -> List[str]:
    """Get press domains relevant to this geo + niche."""
    domains = set(PRESS_DOMAINS_GLOBAL)

    # Add regional
    if country in PRESS_DOMAINS_REGIONAL:
        domains.update(PRESS_DOMAINS_REGIONAL[country])

    # Add niche-specific
    for key in [niche.lower(), subcategory.lower()]:
        if key in NICHE_PRESS_DOMAINS:
            domains.update(NICHE_PRESS_DOMAINS[key])

    return sorted(list(domains))
