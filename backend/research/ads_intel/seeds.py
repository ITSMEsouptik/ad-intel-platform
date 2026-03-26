"""
Novara Ads Intelligence: Seed / Query Builder
Builds competitor domains + category search queries from campaign data.

Category keyword cascade:
  Tier 1: category_search_terms from Competitors module (geo-specific, curated)
  Tier 2: Same terms with geo stripped (broader match)
  Tier 3: Single/double-word core terms extracted from the search terms
  Tier 4: Brand name / offer / classification fallback
"""

import logging
import re
from typing import Dict, Any, List, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Common geo / stop words to strip when broadening queries
GEO_STOP_WORDS = {
    "dubai", "abu dhabi", "sharjah", "riyadh", "jeddah", "doha", "kuwait",
    "mumbai", "delhi", "bangalore", "london", "new york", "los angeles",
    "at", "in", "for", "the", "a", "an", "and", "or", "of", "to",
}


def normalize_domain(url_or_domain: str) -> str:
    """Extract clean domain from URL or domain string."""
    url = url_or_domain.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.lower().strip("/")
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url_or_domain.strip().lower()


def build_competitor_seeds(
    competitor_list: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Build competitor lookup seeds from the competitors module data.
    Each seed has 'domain', 'name', and 'what_they_do' for brand lookup
    and context-enriched fallback queries.
    """
    seeds = []
    seen_domains = set()

    for comp in competitor_list:
        name = comp.get("name", "")
        website = comp.get("website", "")
        domain = normalize_domain(website)
        what_they_do = comp.get("what_they_do", "")

        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            seeds.append({"domain": domain, "name": name, "what_they_do": what_they_do})
        elif name and not domain:
            seeds.append({"domain": "", "name": name, "what_they_do": what_they_do})

    logger.info(f"[ADS_INTEL] Built {len(seeds)} competitor seeds")
    return seeds


# Industry signal words grouped by sector — used for context-enriched queries
# and business context validation
INDUSTRY_SIGNALS = {
    "beauty": ["beauty", "salon", "spa", "skincare", "lash", "lashes", "nails", "makeup",
               "facial", "grooming", "waxing", "threading", "manicure", "pedicure",
               "hair", "bridal", "aesthetics", "blowout", "brow", "tanning", "wellness"],
    "fitness": ["fitness", "gym", "yoga", "pilates", "workout", "training", "crossfit",
                "personal trainer", "exercise"],
    "food": ["restaurant", "cafe", "catering", "food", "delivery", "kitchen", "bakery",
             "coffee", "dining", "meal"],
    "health": ["clinic", "dental", "therapy", "chiropractic", "medical", "doctor",
               "physiotherapy", "derma", "health", "care"],
    "home": ["cleaning", "plumbing", "landscaping", "home service", "repair", "maintenance",
             "handyman", "pest control", "moving"],
    "education": ["tutoring", "coaching", "courses", "learning", "school", "academy",
                  "training", "classes"],
    "tech": ["software", "app", "saas", "platform", "digital", "tech", "cloud", "ai",
             "automation"],
}


def extract_business_signals(what_they_do: str, niche: str = "") -> List[str]:
    """
    Extract industry signal words from a competitor's description.
    Returns a flat list of relevant keywords for query enrichment and validation.
    """
    text = f"{what_they_do} {niche}".lower()
    if not text.strip():
        return []

    signals = []
    for sector, words in INDUSTRY_SIGNALS.items():
        matches = [w for w in words if w in text]
        if matches:
            signals.extend(matches)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in signals:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique


def build_enriched_query(competitor_name: str, what_they_do: str, niche: str = "") -> str:
    """
    Build a context-enriched Foreplay query from competitor name + business context.
    e.g., 'Belita' + 'luxury beauty services' → 'Belita beauty'
    Skips if the signal word is already in the competitor name.
    """
    signals = extract_business_signals(what_they_do, niche)
    name_lower = competitor_name.lower()
    for signal in signals:
        if signal not in name_lower:
            return f"{competitor_name} {signal}"
    return competitor_name


def _strip_geo(term: str, geo_city: str = "", geo_country: str = "") -> str:
    """Remove geo tokens from a search term to broaden it."""
    words = term.lower().split()
    city_lower = geo_city.lower() if geo_city else ""
    country_lower = geo_country.lower() if geo_country else ""

    filtered = []
    for w in words:
        if w in GEO_STOP_WORDS:
            continue
        if city_lower and w == city_lower:
            continue
        if country_lower and w in country_lower.split():
            continue
        filtered.append(w)

    result = " ".join(filtered).strip()
    return result if len(result) > 2 else term


def _extract_core_terms(search_terms: List[str], geo_city: str = "", geo_country: str = "") -> List[str]:
    """
    Extract unique 2-3 word core terms from search terms.
    Focuses on industry/category-specific terms, not generic service words.
    E.g., from "bridal makeup home dubai" → "bridal makeup", "hair salon", "beauty salon"
    """
    # Words that are too generic for ad discovery
    generic_words = {"home", "service", "services", "online", "call", "visit", "mobile", "ladies", "women", "men"}

    word_freq: Dict[str, int] = {}
    bigram_freq: Dict[str, int] = {}

    city_lower = geo_city.lower() if geo_city else ""

    for term in search_terms:
        words = [w for w in term.lower().split()
                 if w not in GEO_STOP_WORDS and w != city_lower and len(w) > 2
                 and w not in generic_words]
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1
        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i+1]}"
            bigram_freq[bg] = bigram_freq.get(bg, 0) + 1

    # Sort by frequency
    top_bigrams = sorted(bigram_freq.items(), key=lambda x: -x[1])
    top_words = sorted(word_freq.items(), key=lambda x: -x[1])

    core = []
    seen = set()
    # Bigrams: category-specific pairs (e.g., "bridal makeup", "hair salon")
    for bg, _ in top_bigrams[:4]:
        if bg not in seen:
            seen.add(bg)
            core.append(bg)
    # Single words: high-frequency category terms (e.g., "makeup", "salon", "bridal")
    for w, freq in top_words[:4]:
        if w not in seen:
            seen.add(w)
            core.append(w)

    return core[:6]


def _extract_niche_queries(competitors: List[Dict[str, Any]], geo_city: str = "") -> List[str]:
    """
    Mine competitor descriptions to build highly specific, service-oriented ad queries.
    Focuses on the business MODEL + specific SERVICE to find similar businesses,
    not product brands. E.g., "lash studio", "blow dry bar", "beauty salon near me".
    """
    descriptions = [c.get("what_they_do", "") for c in competitors if c.get("what_they_do")]
    if not descriptions:
        return []

    combined = " ".join(descriptions).lower()
    city_lower = geo_city.lower().strip() if geo_city else ""

    # Step 1: Detect business venue/model types
    venue_types = []
    for phrase in [
        "studio", "salon", "spa", "bar", "clinic", "lounge", "suite",
        "parlor", "parlour", "boutique", "center", "centre",
        "at-home", "at home", "on-demand", "on demand", "mobile", "doorstep", "concierge",
    ]:
        if phrase in combined:
            clean = phrase.replace("-", " ")
            if clean not in venue_types:
                venue_types.append(clean)

    # Step 2: Detect service categories (broad)
    categories = []
    for cat in ["beauty", "salon", "spa", "wellness", "grooming", "skincare", "aesthetics", "hair", "nails", "lash"]:
        if cat in combined:
            categories.append(cat)

    # Step 3: Detect specific services offered
    services = []
    for service in [
        "lash extensions", "lashes", "nails", "makeup", "hair", "facial", "facials",
        "massage", "blowout", "blow dry", "threading", "waxing", "tanning",
        "bridal", "manicure", "pedicure", "eyebrow", "microblading", "botox",
        "lip filler", "skin care", "hair color", "balayage", "keratin",
        "eyelash", "brow", "mani pedi", "nail art", "hair extensions",
        "body treatment", "laser", "microneedling", "dermaplaning",
    ]:
        if service in combined:
            services.append(service)

    queries = []
    seen = set()

    def _add(q: str):
        q = q.strip()
        q_l = q.lower()
        if q_l and q_l not in seen and len(q) > 3 and (not city_lower or city_lower not in q_l):
            seen.add(q_l)
            queries.append(q)

    # Tier A: [category] + [venue type] → "beauty salon", "lash studio", "hair salon"
    # These are the BEST queries for finding similar SERVICE businesses
    for c in categories[:3]:
        for v in venue_types[:3]:
            if c == v:
                continue  # Skip "spa spa", "salon salon" etc.
            if v in ("at home", "on demand", "mobile", "doorstep", "concierge"):
                _add(f"{v} {c}")  # "at home beauty", "mobile salon"
            else:
                _add(f"{c} {v}")  # "beauty salon", "lash studio", "hair bar"

    # Tier B: [specific service] + [venue] → "lash extensions studio", "blow dry bar"
    for s in services[:4]:
        for v in venue_types[:2]:
            if v not in ("at home", "on demand", "mobile", "doorstep", "concierge"):
                _add(f"{s} {v}")

    # Tier C: Specific service queries (direct niche terms)
    for s in services[:6]:
        _add(s)

    # Tier D: Appointment/booking queries for service businesses
    if categories:
        _add(f"book {categories[0]} appointment")

    return queries[:10]


def build_category_queries(
    category_search_terms: List[str],
    classification: Dict[str, Any],
    offer: Dict[str, Any],
    geo: Dict[str, str],
    brand_name: str = "",
    competitors: List[Dict[str, Any]] = None,
) -> List[str]:
    """
    Build category search queries from the most specific data available.

    Priority:
      1. Niche queries mined from competitor descriptions (most relevant)
      2. category_search_terms from Competitors module (geo-specific)
      3. Geo-stripped versions of those terms
      4. Core bigrams/unigrams from search terms
      5. Classification niche/subcategory (NOT industry — too broad)
      6. Brand name / offer fallback

    Returns up to 12 queries. Broad industry-level categories are deliberately excluded.
    """
    queries = []
    seen: Set[str] = set()
    city = geo.get("city", geo.get("city_or_region", ""))
    country = geo.get("country", "")

    def _add(q: str):
        q = q.strip()
        q_lower = q.lower()
        if q_lower and q_lower not in seen and len(q) > 2:
            seen.add(q_lower)
            queries.append(q)

    # === NEW Tier 0: Niche queries from competitor descriptions ===
    if competitors:
        niche_queries = _extract_niche_queries(competitors, city)
        for nq in niche_queries:
            _add(nq)
        logger.info(f"[ADS_INTEL] Niche queries from competitors: {niche_queries}")

    # === Tier 1: Geo-specific terms from Competitors module ===
    if category_search_terms:
        for term in category_search_terms[:4]:
            _add(term)

    # === Tier 2: Geo-stripped versions (broader) ===
    if category_search_terms:
        for term in category_search_terms[:6]:
            stripped = _strip_geo(term, city, country)
            _add(stripped)

    # === Tier 3: Core bigrams/unigrams (broadest category terms) ===
    if category_search_terms:
        core_terms = _extract_core_terms(category_search_terms, city, country)
        for ct in core_terms:
            _add(ct)

    # === Tier 4: Classification niche/subcategory (NOT industry) ===
    niche = classification.get("niche", "").strip()
    subcategory = classification.get("subcategory", "").strip()
    # Deliberately skip industry — it's too broad (e.g., "Beauty & Wellness")

    # Break niche/subcategory into ad-friendly terms instead of using verbatim
    # "Hair & Makeup Home Service Dubai" → "hair", "makeup", "home service"
    for label in [niche, subcategory]:
        if label and label.lower() != "unknown":
            stripped = _strip_geo(label, city, country)
            # Add the full label only if it's short (≤3 words)
            words = stripped.split()
            if len(words) <= 3:
                _add(stripped)
            # Also extract meaningful sub-phrases
            for segment in re.split(r'[&,/\-]+', stripped):
                segment = segment.strip()
                if segment and len(segment) > 2:
                    _add(segment)

    # === Tier 5: Service-keyword fallback ===
    # When all above tiers are empty, extract individual service keywords
    # from niche/subcategory to form simple ad queries
    if len(queries) < 3:
        all_text = f"{niche} {subcategory}".lower()
        service_keywords = [
            "beauty", "salon", "spa", "wellness", "grooming", "skincare",
            "hair", "nails", "lash", "lashes", "makeup", "facial", "massage",
            "waxing", "threading", "blowout", "manicure", "pedicure", "bridal",
            "barber", "clinic", "aesthetics", "derma", "tattoo", "piercing",
            "fitness", "yoga", "pilates", "dental", "chiropractic", "therapy",
            "cleaning", "plumbing", "landscaping", "catering", "photography",
            "tutoring", "coaching", "consulting", "design", "marketing",
        ]
        found_services = [kw for kw in service_keywords if kw in all_text]
        # Generate simple, ad-friendly queries from found keywords
        for svc in found_services[:4]:
            _add(f"{svc} services")
            _add(f"{svc} near me")
            _add(svc)

    # === Tier 6: Brand name / offer fallback ===
    if not queries:
        if brand_name:
            stripped_brand = _strip_geo(brand_name, city, country)
            _add(stripped_brand)
        summary = offer.get("primary_offer_summary", "")
        if summary and len(summary) > 5:
            words = summary.split()[:4]
            _add(" ".join(words))

    if not queries:
        _add("ads")

    queries = queries[:12]
    logger.info(f"[ADS_INTEL] Built {len(queries)} category queries: {queries}")
    return queries
