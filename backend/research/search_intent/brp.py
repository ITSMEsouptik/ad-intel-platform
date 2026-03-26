"""
Novara Research Foundation: Business Relevance Profile (BRP)
Dynamically builds a brand-agnostic relevance profile from Step 1 + Step 2.

Version 2.1 - Feb 2026
- Added medical business model
- Added has_ecommerce_signals detection
- Handles both step2 and old data format
"""

import logging
import re
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BRP(BaseModel):
    """Business Relevance Profile — built per campaign from Step 1 + Step 2"""
    brand_name: str = ""
    domain: str = ""
    geo_city: Optional[str] = None
    geo_country: Optional[str] = None

    business_model: Literal[
        "service_booking", "ecommerce", "medical", "saas", "app", "unknown"
    ] = "unknown"

    brand_terms: List[str] = Field(default_factory=list)
    service_terms: List[str] = Field(default_factory=list)
    category_terms: List[str] = Field(default_factory=list)
    geo_terms: List[str] = Field(default_factory=list)
    allowed_intents: List[str] = Field(
        default_factory=lambda: ["price", "trust", "urgency", "comparison", "general"]
    )

    block_terms: List[str] = Field(default_factory=list)
    geo_block_terms: List[str] = Field(default_factory=list)

    # v2.1 additions
    has_ecommerce_signals: bool = False


# ============== BUSINESS MODEL INFERENCE ==============

BOOKING_SIGNALS = [
    "book", "booking", "appointment", "reserve", "schedule",
    "contact us", "get a quote", "request", "consult", "consultation",
    "call now", "whatsapp", "enquire", "inquire"
]

ECOMMERCE_SIGNALS = [
    "add to cart", "buy now", "shop now", "checkout", "add to bag",
    "purchase", "order now", "shop", "store", "product", "products",
    "shipping", "delivery", "cart"
]

SAAS_SIGNALS = [
    "free trial", "start free", "pricing plans", "demo", "request demo",
    "sign up free", "api", "software", "platform", "dashboard",
    "integration", "enterprise", "saas"
]

APP_SIGNALS = [
    "app store", "google play", "download app", "get the app",
    "available on ios", "available on android", "mobile app"
]

MEDICAL_SIGNALS = [
    "clinic", "doctor", "dermatologist", "dermatology", "dentist", "dental",
    "surgeon", "surgery", "medical", "hospital", "patient", "treatment",
    "procedure", "therapy", "diagnosis", "prescription", "health",
    "botox", "filler", "laser", "transplant", "cosmetic surgery"
]

# Model-specific block terms
SERVICE_BLOCK_TERMS = [
    "kit", "brush", "brushes", "accessories", "accessory",
    "amazon", "noon", "aliexpress", "shein", "temu",
    "buy online", "coupon code", "review product",
    "unboxing", "haul", "swatch", "swatches"
]

SAAS_BLOCK_TERMS = [
    "amazon", "noon", "aliexpress", "buy physical",
    "booking", "appointment", "reserve"
]

# Common geo terms to detect foreign geo references
KNOWN_GEOS = [
    "india", "pakistan", "bangladesh", "nigeria", "kenya", "ghana",
    "south africa", "uk", "usa", "us", "canada", "australia",
    "philippines", "indonesia", "malaysia", "singapore", "thailand",
    "egypt", "saudi arabia", "qatar", "oman", "bahrain", "kuwait",
    "germany", "france", "italy", "spain", "brazil", "mexico",
    "turkey", "iran", "iraq", "japan", "china", "korea",
    "united kingdom", "united states", "united arab emirates",
    "sri lanka", "nepal", "vietnam", "cambodia", "myanmar",
    "london", "new york", "los angeles", "chicago", "toronto",
    "mumbai", "delhi", "bangalore", "hyderabad", "chennai", "kolkata",
    "lagos", "nairobi", "karachi", "lahore", "dhaka",
    "sydney", "melbourne", "dubai", "abu dhabi", "sharjah", "ajman",
    "riyadh", "jeddah", "doha", "muscat", "manama",
    "paris", "berlin", "madrid", "rome", "amsterdam",
    "tokyo", "shanghai", "beijing", "seoul", "bangkok",
    "istanbul", "cairo", "casablanca", "johannesburg", "cape town",
    "san francisco", "seattle", "boston", "miami", "houston", "dallas",
    "vancouver", "montreal", "auckland", "jakarta", "manila",
    "kuala lumpur", "ho chi minh", "hanoi"
]


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL"""
    domain = url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    domain = domain.split("/")[0].split("?")[0]
    return domain


def _tokenize_domain(domain: str) -> List[str]:
    """Extract meaningful tokens from domain name"""
    name = domain.split(".")[0]
    tokens = re.split(r'[-_]', name)
    return [t for t in tokens if len(t) > 2]


def _text_has_signals(text: str, signals: List[str]) -> int:
    """Count how many signals appear in text"""
    text_lower = text.lower()
    return sum(1 for s in signals if s in text_lower)


def _detect_ecommerce_signals(step2: Dict[str, Any], old_data: Dict[str, Any]) -> bool:
    """Detect if the brand has ecommerce/product-selling signals from Step 2 data.
    Must be strong evidence — a single generic word like 'order' is not enough."""
    strong_ecom_markers = [
        "add to cart", "buy online", "buy now", "shop now", "checkout",
        "add to bag", "shipping", "free delivery", "order online"
    ]

    # New format
    if step2:
        offer = step2.get("offer", {})
        conversion = step2.get("conversion", {})
        # If offer_type_hint says "product" or "ecommerce", trust it
        offer_hint = str(offer.get("offer_type_hint", "")).lower()
        if offer_hint in ("product", "ecommerce", "physical_product"):
            return True
        if offer_hint == "service":
            return False

        all_text = ""
        for item in offer.get("offer_catalog", []):
            all_text += " " + item.get("name", "") + " " + item.get("description", "")
        all_text += " " + str(conversion.get("primary_action_text", ""))
        all_text = all_text.lower()
        if any(m in all_text for m in strong_ecom_markers):
            return True

    # Old format
    if old_data:
        offer = old_data.get("offer", {})
        offer_hint = str(offer.get("offer_type_hint", "")).lower()
        if offer_hint in ("product", "ecommerce", "physical_product"):
            return True
        if offer_hint == "service":
            return False

        conversion = old_data.get("conversion", {})
        ctas = " ".join(conversion.get("detected_primary_ctas", [])).lower()
        if any(m in ctas for m in strong_ecom_markers):
            return True

    return False


def infer_business_model(
    campaign_brief: Dict[str, Any],
    step2: Dict[str, Any]
) -> str:
    """
    Infer business model from Step 1 + Step 2 data.
    Handles both new step2 and old data format.
    """
    destination_type = campaign_brief.get("destination", {}).get("type", "")
    if isinstance(destination_type, str):
        destination_type = destination_type.lower()

    conversion = step2.get("conversion", {})
    offer = step2.get("offer", {})
    classification = step2.get("classification", {})

    primary_action = str(conversion.get("primary_action", "")).lower()
    primary_action_text = str(conversion.get("primary_action_text", "")).lower()
    value_prop = str(offer.get("value_prop", offer.get("one_liner_value_prop", ""))).lower()
    tags = [t.lower() for t in classification.get("tags", [])]

    offer_catalog = offer.get("offer_catalog", [])
    catalog_names = " ".join(item.get("name", "") for item in offer_catalog).lower()

    brand_identity = step2.get("brand_identity", {})
    old_value_prop = str(brand_identity.get("one_liner_value_prop", "")).lower()
    offer_summary = str(offer.get("primary_offer_summary", "")).lower()
    detected_ctas = " ".join(conversion.get("detected_primary_ctas", [])).lower()

    all_text = (
        f"{primary_action} {primary_action_text} {value_prop} {catalog_names} "
        f"{' '.join(tags)} {old_value_prop} {offer_summary} {detected_ctas}"
    )

    scores = {
        "service_booking": 0,
        "ecommerce": 0,
        "medical": 0,
        "saas": 0,
        "app": 0
    }

    if destination_type in ["whatsapp", "booking_link"]:
        scores["service_booking"] += 3
    elif destination_type == "app":
        scores["app"] += 3

    scores["service_booking"] += _text_has_signals(all_text, BOOKING_SIGNALS)
    scores["ecommerce"] += _text_has_signals(all_text, ECOMMERCE_SIGNALS)
    scores["medical"] += _text_has_signals(all_text, MEDICAL_SIGNALS)
    scores["saas"] += _text_has_signals(all_text, SAAS_SIGNALS)
    scores["app"] += _text_has_signals(all_text, APP_SIGNALS)

    best = max(scores, key=scores.get)
    if scores[best] >= 2:
        return best

    return "unknown"


def _extract_service_terms(step2: Dict[str, Any], old_data: Dict[str, Any] = None) -> List[str]:
    """
    Extract service terms dynamically from Step 2 data.
    Handles both new (step2) and old (data) formats.
    """
    terms = []
    seen = set()

    def _add(phrase: str):
        p = phrase.strip().lower()
        if p and p not in seen and p != "unknown" and len(p) >= 3:
            if len(p.split()) <= 4:
                seen.add(p)
                terms.append(p)

    # --- New format: step2 ---
    if step2:
        offer = step2.get("offer", {})
        classification = step2.get("classification", {})

        for item in offer.get("offer_catalog", [])[:8]:
            name = item.get("name", "")
            if name:
                _add(name)
                for word in name.lower().split():
                    if len(word) >= 4 and word not in {"with", "without", "simple", "premium", "basic", "standard"}:
                        _add(word)

        niche = classification.get("niche", "")
        if niche and niche.lower() != "unknown":
            _add(niche)
            for word in niche.lower().split():
                if len(word) >= 4 and word not in {"home", "service", "services"}:
                    _add(word)

        for tag in classification.get("tags", [])[:6]:
            if tag.lower() not in {"unknown", "luxury", "premium", "professional", "expert", "best", "top"}:
                _add(tag)

        for benefit in offer.get("key_benefits", [])[:4]:
            words = benefit.lower().split()
            if 2 <= len(words) <= 4:
                _add(benefit)

        value_prop = offer.get("value_prop", "")
        if value_prop:
            for word in value_prop.lower().split():
                if len(word) >= 5 and word not in {"their", "about", "these", "which", "where", "there", "being", "every"}:
                    _add(word)

    # --- Old format: data key fallback ---
    if not terms and old_data:
        brand_identity = old_data.get("brand_identity", {})
        offer = old_data.get("offer", {})

        brand_name = brand_identity.get("brand_name", "")
        if brand_name:
            service_keywords = {
                "makeup", "hair", "beauty", "salon", "spa", "facial", "massage",
                "skincare", "bridal", "nail", "nails", "lash", "lashes", "waxing",
                "threading", "manicure", "pedicure", "grooming", "styling",
                "cleaning", "plumbing", "painting", "moving", "catering",
                "photography", "fitness", "yoga", "dental", "clinic"
            }
            bn_lower = brand_name.lower()
            for kw in service_keywords:
                if kw in bn_lower:
                    _add(kw)

            if "hair" in bn_lower and "makeup" in bn_lower:
                _add("hair and makeup")
            if "makeup" in bn_lower:
                _add("makeup artist")
            if "home service" in bn_lower:
                _add("home service")

        summary = offer.get("primary_offer_summary", "")
        if summary:
            summary_lower = summary.lower()
            service_hints = [
                "makeup", "hair", "beauty", "salon", "spa", "facial", "massage",
                "skincare", "bridal", "nail", "waxing", "threading", "lash",
                "grooming", "styling", "booking", "service"
            ]
            for hint in service_hints:
                if hint in summary_lower:
                    _add(hint)

        value_prop = brand_identity.get("one_liner_value_prop", "")
        if value_prop:
            for word in value_prop.lower().split():
                if len(word) >= 5 and word not in {"their", "about", "these", "which", "where", "there", "being", "every", "beauty", "anywhere", "anytime", "unleash"}:
                    _add(word)

    return terms[:20]


def _extract_category_terms(step2: Dict[str, Any], old_data: Dict[str, Any] = None) -> List[str]:
    """Extract industry/category terms from Step 2 classification"""
    terms = []
    seen = set()

    def _add(phrase: str):
        p = phrase.strip().lower()
        if p and p not in seen and p != "unknown" and len(p) >= 3:
            seen.add(p)
            terms.append(p)

    if step2:
        classification = step2.get("classification", {})
        _add(classification.get("industry", ""))
        _add(classification.get("subcategory", ""))
        _add(classification.get("niche", ""))
        for tag in classification.get("tags", [])[:5]:
            _add(tag)

    if not terms and old_data:
        seed_insights = old_data.get("seed_insights", {})
        if seed_insights:
            _add(seed_insights.get("industry", ""))
            _add(seed_insights.get("sub_industry", ""))
            _add(seed_insights.get("niche", ""))

        brand_name = old_data.get("brand_identity", {}).get("brand_name", "").lower()
        if any(kw in brand_name for kw in ["beauty", "makeup", "hair", "salon", "spa"]):
            _add("beauty")
            _add("beauty services")
        if "home service" in brand_name:
            _add("home services")

    return terms[:10]


def build_brp(
    campaign_brief: Dict[str, Any],
    website_context_pack: Dict[str, Any]
) -> BRP:
    """
    Build a Business Relevance Profile from Step 1 + Step 2.
    Handles both new (step2 key) and old (data key) formats.
    """
    step2 = website_context_pack.get("step2") or {}
    old_data = website_context_pack.get("data") or {}
    source = step2 if step2 else old_data

    brand_url = campaign_brief.get("brand", {}).get("website_url", "")
    domain = _extract_domain(brand_url) if brand_url else ""

    brand_name = ""
    if step2:
        brand_name = step2.get("brand_summary", {}).get("name", "")
    if not brand_name and old_data:
        brand_name = old_data.get("brand_identity", {}).get("brand_name", "")

    geo = campaign_brief.get("geo", {})
    geo_city = geo.get("city_or_region", "")
    geo_country = geo.get("country", "")

    business_model = infer_business_model(campaign_brief, source)
    logger.info(f"[BRP] Inferred business_model: {business_model}")

    # Ecommerce signals
    has_ecommerce_signals = _detect_ecommerce_signals(step2, old_data)
    logger.info(f"[BRP] has_ecommerce_signals: {has_ecommerce_signals}")

    # Brand terms
    brand_terms = []
    if brand_name and brand_name.lower() != "unknown":
        brand_terms.append(brand_name.lower())
    brand_terms.extend(_tokenize_domain(domain))
    brand_terms = list(dict.fromkeys(brand_terms))

    service_terms = _extract_service_terms(step2, old_data)
    category_terms = _extract_category_terms(step2, old_data)

    geo_terms = []
    if geo_city:
        geo_terms.append(geo_city.lower())
    if geo_country:
        geo_terms.append(geo_country.lower())
    geo_terms.append("near me")
    geo_terms = list(dict.fromkeys(geo_terms))

    # Block terms (model-specific)
    block_terms = []
    if business_model == "service_booking":
        block_terms = SERVICE_BLOCK_TERMS.copy()
    elif business_model == "saas":
        block_terms = SAAS_BLOCK_TERMS.copy()

    # Geo block terms
    campaign_geos = {g.lower() for g in [geo_city, geo_country] if g}
    if geo_country:
        country_lower = geo_country.lower()
        if "united arab emirates" in country_lower:
            campaign_geos.update(["uae", "dubai", "abu dhabi", "sharjah", "ajman"])
        elif "united kingdom" in country_lower:
            campaign_geos.update(["uk", "london", "england"])
        elif "united states" in country_lower:
            campaign_geos.update(["usa", "us"])
    if geo_city:
        campaign_geos.add(geo_city.lower())

    geo_block_terms = [g for g in KNOWN_GEOS if g.lower() not in campaign_geos]

    brp = BRP(
        brand_name=brand_name,
        domain=domain,
        geo_city=geo_city,
        geo_country=geo_country,
        business_model=business_model,
        brand_terms=brand_terms,
        service_terms=service_terms,
        category_terms=category_terms,
        geo_terms=geo_terms,
        block_terms=block_terms,
        geo_block_terms=geo_block_terms,
        has_ecommerce_signals=has_ecommerce_signals
    )

    logger.info(f"[BRP] Built: model={business_model}, services={len(service_terms)}, "
                f"categories={len(category_terms)}, ecom={has_ecommerce_signals}")

    return brp
