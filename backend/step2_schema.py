"""
Novara Step 2: Schema Definitions
Pydantic models matching the Step2Summary and Step2Internal JSON schemas

Updated Feb 2026 - Final spec implementation
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ============== ENUMS ==============

class LogoType(str, Enum):
    LOGO = "logo"
    ICON = "icon"
    WORDMARK = "wordmark"


class ColorRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ACCENT = "accent"
    BG = "bg"
    TEXT = "text"
    MUTED = "muted"
    UNKNOWN = "unknown"


class FontRole(str, Enum):
    HEADING = "heading"
    BODY = "body"
    ACCENT = "accent"
    UNKNOWN = "unknown"


class FontSource(str, Enum):
    CSS = "css"
    GOOGLE = "google"
    UNKNOWN = "unknown"


class OfferType(str, Enum):
    SERVICE = "service"
    PRODUCT = "product"
    SUBSCRIPTION = "subscription"
    MARKETPLACE = "marketplace"
    SAAS = "saas"
    UNKNOWN = "unknown"


class DestinationType(str, Enum):
    WEBSITE = "website"
    WHATSAPP = "whatsapp"
    FORM = "form"
    APP = "app"
    UNKNOWN = "unknown"


class AssetKind(str, Enum):
    LOGO = "logo"
    HERO = "hero"
    OG = "og"
    PRODUCT = "product"
    TEAM = "team"
    GALLERY = "gallery"
    ICON = "icon"
    UNKNOWN = "unknown"


# ============== STEP 2 PUBLIC SCHEMA ==============

class SiteInfo(BaseModel):
    """Site metadata"""
    input_url: str
    final_url: str
    domain: str = "unknown"
    title: str = "unknown"
    meta_description: str = "unknown"
    language: str = "unknown"


class Classification(BaseModel):
    """Industry classification - 3-tier hierarchy"""
    industry: str = "unknown"  # Broad: e.g., "Beauty & Wellness"
    subcategory: str = "unknown"  # Mid: e.g., "On-demand Beauty Services"
    niche: str = "unknown"  # Specific: e.g., "At-home Hair & Makeup (Dubai)"
    tags: List[str] = Field(default_factory=list, max_length=10)  # e.g., ["bridal", "home service"]


class BrandSummary(BaseModel):
    """Brand summary with bullets and tagline"""
    name: str = "unknown"
    tagline: str = "unknown"
    one_liner: str = "unknown"
    bullets: List[str] = Field(default_factory=list, max_length=5)  # Max 5, each <= 90 chars


class BrandDNA(BaseModel):
    """Brand DNA - values, tone, aesthetic"""
    values: List[str] = Field(default_factory=list, max_length=6)
    tone_of_voice: List[str] = Field(default_factory=list, max_length=6)
    aesthetic: List[str] = Field(default_factory=list, max_length=6)
    visual_vibe: List[str] = Field(default_factory=list, max_length=6)


class LogoCandidate(BaseModel):
    """Logo candidate"""
    url: str
    score: int = 50
    reason: str = ""


class LogoInfo(BaseModel):
    """Logo information with primary and candidates"""
    primary_url: str = ""
    type: LogoType = LogoType.LOGO
    width: int = 0
    height: int = 0
    candidates: List[LogoCandidate] = Field(default_factory=list, max_length=5)


class ColorInfo(BaseModel):
    """Color with role"""
    hex: str
    role: ColorRole = ColorRole.UNKNOWN


class FontInfo(BaseModel):
    """Font with role and source"""
    family: str
    role: FontRole = FontRole.UNKNOWN
    source: FontSource = FontSource.UNKNOWN


class Identity(BaseModel):
    """Visual identity - logo, colors, fonts"""
    logo: LogoInfo = Field(default_factory=LogoInfo)
    colors: List[ColorInfo] = Field(default_factory=list, max_length=8)  # Max 8 colors
    fonts: List[FontInfo] = Field(default_factory=list, max_length=6)


class OfferCatalogItem(BaseModel):
    """Single item in offer catalog"""
    name: str
    description: str = ""
    price_hint: str = ""


class Offer(BaseModel):
    """Offer details"""
    value_prop: str = "unknown"
    key_benefits: List[str] = Field(default_factory=list, max_length=5)
    offer_catalog: List[OfferCatalogItem] = Field(default_factory=list, max_length=20)


class ObservedPrice(BaseModel):
    """Single observed price"""
    value: float
    currency: str = "AED"
    raw: str
    source_url: str = ""


class Pricing(BaseModel):
    """Pricing statistics"""
    currency: str = "unknown"
    count: int = 0
    min: float = 0
    avg: float = 0
    max: float = 0
    observed_prices: List[ObservedPrice] = Field(default_factory=list, max_length=50)


class Conversion(BaseModel):
    """Conversion flow"""
    primary_action: str = "unknown"
    ctas: List[str] = Field(default_factory=list, max_length=10)
    destination_type: DestinationType = DestinationType.UNKNOWN


# ============== CHANNELS (Updated) ==============

class ChannelLink(BaseModel):
    """A single channel link"""
    platform: str
    url: str
    handle: str = ""


class Channels(BaseModel):
    """All discovered channels"""
    social: List[ChannelLink] = Field(default_factory=list)  # Instagram, TikTok, YouTube, etc.
    messaging: List[ChannelLink] = Field(default_factory=list)  # WhatsApp, Telegram
    apps: List[ChannelLink] = Field(default_factory=list)  # App Store, Google Play
    other: List[ChannelLink] = Field(default_factory=list)  # Any other links


class ImageAsset(BaseModel):
    """Single image asset"""
    url: str
    kind: AssetKind = AssetKind.UNKNOWN
    score_0_100: int = 50
    alt: str = ""
    width: int = 0
    height: int = 0


class Assets(BaseModel):
    """Captured assets"""
    image_assets: List[ImageAsset] = Field(default_factory=list, max_length=100)


class Step2Data(BaseModel):
    """Main Step 2 public data structure"""
    site: SiteInfo
    classification: Classification = Field(default_factory=Classification)
    brand_summary: BrandSummary = Field(default_factory=BrandSummary)
    brand_dna: BrandDNA = Field(default_factory=BrandDNA)
    identity: Identity = Field(default_factory=Identity)
    offer: Offer = Field(default_factory=Offer)
    pricing: Pricing = Field(default_factory=Pricing)
    conversion: Conversion = Field(default_factory=Conversion)
    channels: Channels = Field(default_factory=Channels)
    assets: Assets = Field(default_factory=Assets)


class Step2Summary(BaseModel):
    """Complete Step 2 Summary (public fields)"""
    step2: Step2Data


# ============== STEP 2 INTERNAL SCHEMA ==============

class AnalysisQuality(BaseModel):
    """Internal quality metrics (NOT shown in UI)"""
    confidence_score_0_100: int = 0
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)


class ExtractionStats(BaseModel):
    """Extraction statistics for debugging"""
    pages_crawled: int = 0
    css_files_fetched: int = 0
    css_fetch_failures: int = 0
    assets_found: int = 0
    assets_after_dedup: int = 0
    prices_found: int = 0
    channels_found: int = 0


class RawExtraction(BaseModel):
    """Raw extraction data for debugging"""
    pages_crawled: int = 0
    text_chunks: List[str] = Field(default_factory=list)
    headings: List[str] = Field(default_factory=list)
    raw_css_fonts: List[str] = Field(default_factory=list)
    raw_css_colors: List[str] = Field(default_factory=list)
    structured_data_jsonld: List[str] = Field(default_factory=list)


class LLMCallInfo(BaseModel):
    """LLM call metadata"""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0
    attempt: int = 1


class Step2InternalData(BaseModel):
    """Internal Step 2 data"""
    analysis_quality: AnalysisQuality = Field(default_factory=AnalysisQuality)
    extraction_stats: ExtractionStats = Field(default_factory=ExtractionStats)
    raw_extraction: RawExtraction = Field(default_factory=RawExtraction)
    llm_call: LLMCallInfo = Field(default_factory=LLMCallInfo)


class Step2Internal(BaseModel):
    """Complete Step 2 Internal (NOT shown in UI)"""
    step2_internal: Step2InternalData


# ============== HELPER FUNCTIONS ==============

def create_empty_step2_data(input_url: str, final_url: str, domain: str = "") -> Step2Data:
    """Create an empty Step2Data with required fields"""
    return Step2Data(
        site=SiteInfo(
            input_url=input_url,
            final_url=final_url,
            domain=domain or final_url.split('//')[-1].split('/')[0]
        )
    )


def create_empty_step2_internal() -> Step2InternalData:
    """Create an empty Step2InternalData"""
    return Step2InternalData()


# ============== LLM OUTPUT SCHEMA (for JSON schema enforcement) ==============

STEP2_LLM_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["classification", "brand_summary", "brand_dna", "offer", "conversion"],
    "properties": {
        "classification": {
            "type": "object",
            "additionalProperties": False,
            "required": ["industry", "subcategory", "niche"],
            "properties": {
                "industry": {"type": "string", "maxLength": 50},
                "subcategory": {"type": "string", "maxLength": 60},
                "niche": {"type": "string", "maxLength": 80},
                "tags": {
                    "type": "array",
                    "maxItems": 10,
                    "items": {"type": "string", "maxLength": 25}
                }
            }
        },
        "brand_summary": {
            "type": "object",
            "additionalProperties": False,
            "required": ["name", "one_liner", "bullets"],
            "properties": {
                "name": {"type": "string", "maxLength": 60},
                "tagline": {"type": "string", "maxLength": 100},
                "one_liner": {"type": "string", "maxLength": 150},
                "bullets": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 5,
                    "items": {"type": "string", "maxLength": 90}
                }
            }
        },
        "brand_dna": {
            "type": "object",
            "additionalProperties": False,
            "required": ["values", "tone_of_voice", "aesthetic", "visual_vibe"],
            "properties": {
                "values": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                },
                "tone_of_voice": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                },
                "aesthetic": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                },
                "visual_vibe": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string", "maxLength": 25}
                }
            }
        },
        "offer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["value_prop", "key_benefits"],
            "properties": {
                "value_prop": {"type": "string", "maxLength": 200},
                "key_benefits": {
                    "type": "array",
                    "maxItems": 5,
                    "items": {"type": "string", "maxLength": 90}
                },
                "offer_catalog": {
                    "type": "array",
                    "maxItems": 20,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string", "maxLength": 60},
                            "description": {"type": "string", "maxLength": 120},
                            "price_hint": {"type": "string", "maxLength": 40}
                        }
                    }
                }
            }
        },
        "conversion": {
            "type": "object",
            "additionalProperties": False,
            "required": ["primary_action", "destination_type"],
            "properties": {
                "primary_action": {"type": "string", "maxLength": 60},
                "destination_type": {
                    "type": "string",
                    "enum": ["website", "whatsapp", "form", "app", "unknown"]
                }
            }
        }
    }
}
