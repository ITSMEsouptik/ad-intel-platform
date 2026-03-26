# Novara - Technical Documentation
## Strategy-Led AI Ad Experimentation Platform

**Version:** 1.0  
**Last Updated:** January 21, 2026  
**Status:** Phase 2 Complete, Phase 3A Complete (with issues)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Data Flow & Logic Diagrams](#4-data-flow--logic-diagrams)
5. [Backend Implementation](#5-backend-implementation)
6. [Frontend Implementation](#6-frontend-implementation)
7. [Database Schema](#7-database-schema)
8. [API Reference](#8-api-reference)
9. [Third-Party Integrations](#9-third-party-integrations)
10. [Current Issues & Bugs](#10-current-issues--bugs)
11. [Pending Work](#11-pending-work)
12. [Optimization Opportunities](#12-optimization-opportunities)
13. [Development Setup](#13-development-setup)
14. [Testing](#14-testing)

---

## 1. Executive Summary

### What is Novara?

Novara is a strategy-led AI ad experimentation platform that transforms a brand's website into actionable ad intelligence. The platform automates the labor-intensive process of:

1. **Understanding a brand** (website analysis)
2. **Market research** (competitor discovery, customer psychology)
3. **Ad strategy** (messaging angles, format recommendations)
4. **Creative generation** (ad copy, visuals) - *planned*

### Core Value Proposition

> "Turn your website into a test plan — high-impact digital ads in bulk, powered by AI. From strategy to creative in minutes, not weeks."

### Current State

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Complete | Campaign Brief Intake (4-screen wizard) |
| Phase 2 | ✅ Complete | Website Context Extraction (crawler + extractor) |
| Step 3A | ⚠️ Issues | Perplexity Intel Pack (market intelligence) |
| Step 3B | 🔜 Planned | Foreplay Ad Analysis |
| Phase 4 | 🔜 Planned | Creative Generation |

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER BROWSER                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Landing   │→ │   Wizard    │→ │ BuildingPack│→ │  PackView   │→ ...   │
│  │   Page      │  │  (4 steps)  │  │  (polling)  │  │  (results)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS (API calls)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KUBERNETES CLUSTER                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         NGINX INGRESS                                │   │
│  │   /api/* → Backend (8001)    /* → Frontend (3000)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                     │                              │                        │
│                     ▼                              ▼                        │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐   │
│  │      FASTAPI BACKEND         │  │        REACT FRONTEND            │   │
│  │         (Port 8001)          │  │         (Port 3000)              │   │
│  │                              │  │                                  │   │
│  │  ┌────────────────────────┐  │  │  ┌────────────────────────────┐ │   │
│  │  │      server.py         │  │  │  │      React Router          │ │   │
│  │  │   - API Routes         │  │  │  │   - Landing                │ │   │
│  │  │   - Orchestration      │  │  │  │   - Wizard                 │ │   │
│  │  │   - Auth               │  │  │  │   - BuildingPack           │ │   │
│  │  └────────────────────────┘  │  │  │   - PackView               │ │   │
│  │              │               │  │  │   - IntelView              │ │   │
│  │  ┌───────────┴───────────┐   │  │  └────────────────────────────┘ │   │
│  │  │                       │   │  │                                  │   │
│  │  ▼                       ▼   │  └──────────────────────────────────┘   │
│  │ ┌──────────┐ ┌──────────────┐│                                         │
│  │ │crawler.py│ │perplexity_   ││                                         │
│  │ │          │ │intel.py     ││                                         │
│  │ └──────────┘ └──────────────┘│                                         │
│  │      │              │        │                                         │
│  │      ▼              ▼        │                                         │
│  │ ┌──────────┐  ┌───────────┐  │                                         │
│  │ │extractor │  │Perplexity │  │                                         │
│  │ │.py       │  │API        │  │                                         │
│  │ └──────────┘  └───────────┘  │                                         │
│  │      │                       │                                         │
│  │      ▼                       │                                         │
│  │ ┌──────────┐                 │                                         │
│  │ │confidence│                 │                                         │
│  │ │.py       │                 │                                         │
│  │ └──────────┘                 │                                         │
│  └──────────────────────────────┘                                         │
│                     │                                                      │
│                     ▼                                                      │
│  ┌──────────────────────────────┐                                         │
│  │          MONGODB             │                                         │
│  │   - campaign_briefs          │                                         │
│  │   - orchestration_runs       │                                         │
│  │   - step_runs                │                                         │
│  │   - website_context_packs    │                                         │
│  │   - perplexity_intel_packs   │                                         │
│  │   - users                    │                                         │
│  │   - user_sessions            │                                         │
│  └──────────────────────────────┘                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ External APIs
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SERVICES                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │ Emergent Auth │  │  Perplexity   │  │  Target       │                   │
│  │ (Google OAuth)│  │  AI API       │  │  Websites     │                   │
│  └───────────────┘  └───────────────┘  └───────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | File(s) | Lines | Responsibility |
|-----------|---------|-------|----------------|
| **API Server** | `server.py` | 932 | Routes, orchestration, auth, CRUD |
| **Web Crawler** | `crawler.py` | 537 | HTTP/Playwright crawling, link discovery |
| **Data Extractor** | `extractor.py` | 527 | HTML parsing, structured data extraction |
| **Confidence Scorer** | `confidence.py` | 228 | Quality scoring, micro-question generation |
| **Perplexity Client** | `perplexity_intel.py` | 651 | Market intelligence via Perplexity API |
| **Frontend Router** | `App.js` | 49 | Route definitions |
| **Wizard** | `Wizard.jsx` | 574 | 4-screen intake form |
| **BuildingPack** | `BuildingPack.jsx` | 380 | Step 2 progress UI |
| **PackView** | `PackView.jsx` | 407 | Website context display |
| **IntelView** | `IntelView.jsx` | 435 | Market intel display |

---

## 3. Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | Latest | Web framework |
| Motor | Latest | Async MongoDB driver |
| Pydantic | v2 | Data validation |
| httpx | Latest | Async HTTP client |
| Playwright | Latest | Browser automation (fallback) |
| BeautifulSoup4 | Latest | HTML parsing |
| lxml | Latest | Fast XML/HTML parser |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.x | UI framework |
| React Router | v6 | Client-side routing |
| Axios | Latest | HTTP client |
| TailwindCSS | 3.x | Styling |
| Shadcn/UI | Latest | Component library |
| Lucide React | Latest | Icons |

### Database

| Technology | Purpose |
|------------|---------|
| MongoDB | Document store |

### External Services

| Service | Purpose | Status |
|---------|---------|--------|
| Emergent Auth | Google OAuth | ✅ Integrated |
| Perplexity AI | Market intelligence | ✅ Integrated |
| Foreplay | Competitor ad library | 🔜 Planned |

---

## 4. Data Flow & Logic Diagrams

### Main User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MAIN USER FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐
    │ Landing │
    │  Page   │
    └────┬────┘
         │ Click "Get Started"
         ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ Wizard  │────▶│ Wizard  │────▶│ Wizard  │────▶│ Wizard  │
    │ Step 1  │     │ Step 2  │     │ Step 3  │     │ Step 4  │
    │         │     │         │     │         │     │         │
    │ Website │     │ Country │     │ Ads     │     │ Name    │
    │ URL     │     │ City    │     │ Intent  │     │ Email   │
    │ Goal    │     │ Dest.   │     │ Budget  │     │         │
    │ Success │     │ Type    │     │         │     │         │
    └─────────┘     └─────────┘     └─────────┘     └────┬────┘
                                                         │
         ┌───────────────────────────────────────────────┘
         │ POST /api/campaign-briefs
         │ POST /api/orchestrations/{id}/start
         ▼
    ┌──────────────┐
    │ BuildingPack │◀──────────────────────────────┐
    │              │                                │
    │ Progress UI  │   GET /api/orchestrations/    │
    │ - Fetching   │        {id}/status            │
    │ - Extracting │                                │
    │ - Scoring    │   Poll every 2 seconds        │
    └──────┬───────┘───────────────────────────────┘
           │
           │ Status: success/partial/needs_user_input
           ▼
    ┌─────────────────┐
    │    PackView     │
    │                 │
    │ Website Context │
    │ - Brand Identity│
    │ - Offer         │
    │ - CTAs          │
    │ - Trust Signals │
    │ - Confidence    │
    └────────┬────────┘
             │
             │ Click "Generate Market Intel"
             ▼
    ┌─────────────────┐
    │   IntelView     │◀────────────────────────────┐
    │                 │                              │
    │ POST .../step-3a/start                        │
    │                 │   GET /api/perplexity-      │
    │ Market Intel    │   intel-packs/by-campaign/  │
    │ - Category      │        {id}                 │
    │ - Competitors   │                              │
    │ - Psychology    │   Poll every 3 seconds      │
    │ - Brand Audit   │                              │
    └─────────────────┘────────────────────────────┘
```

### Step 2: Website Context Extraction (Detailed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 2: WEBSITE CONTEXT EXTRACTION                        │
└─────────────────────────────────────────────────────────────────────────────┘

  POST /api/orchestrations/{brief_id}/start
                    │
                    ▼
        ┌───────────────────┐
        │ Create Records    │
        │ - orchestration   │
        │ - step_run        │
        │ - pack (running)  │
        └─────────┬─────────┘
                  │
                  │ asyncio.create_task()
                  ▼
        ┌───────────────────┐
        │   run_step2()     │
        │   (Background)    │
        └─────────┬─────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │     WebCrawler          │
    │     crawler.py          │
    └─────────────┬───────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    SMART PRIORITY CRAWLING                   │
    │                                                              │
    │  1. Fetch homepage (HTTP first, Playwright fallback)        │
    │  2. Extract all internal links                               │
    │  3. Score links by priority:                                 │
    │     - "about" pages: +20                                     │
    │     - "services/products": +15                               │
    │     - "contact": +10                                         │
    │     - "pricing": +15                                         │
    │     - "testimonials": +12                                    │
    │  4. Crawl top 9 additional pages (10 total max)             │
    │                                                              │
    │  Output: CrawlResult                                         │
    │  - pages: List[PageContent]                                  │
    │  - all_links_found: List[str]                                │
    │  - fetch_method: "http" | "playwright"                       │
    │  - social_links: Dict[str, str]                              │
    │  - errors: List[str]                                         │
    └─────────────────────────────────────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │   ExtractionEngine      │
    │   extractor.py          │
    └─────────────┬───────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    DATA EXTRACTION                           │
    │                                                              │
    │  brand_identity:                                             │
    │    - brand_name (from <title>, og:site_name, h1)            │
    │    - tagline (from meta description, hero text)              │
    │    - one_liner_value_prop                                    │
    │    - visual: logo_url, colors, fonts                         │
    │                                                              │
    │  offer:                                                      │
    │    - offer_type_hint (service/product/saas/info)            │
    │    - primary_offer_summary                                   │
    │    - key_benefits (from <li>, feature sections)              │
    │    - differentiators                                         │
    │    - pricing_mentions (regex for currency)                   │
    │                                                              │
    │  conversion:                                                 │
    │    - primary_action (book/buy/call/dm/whatsapp)             │
    │    - detected_primary_ctas (button text)                     │
    │                                                              │
    │  proof:                                                      │
    │    - testimonials: [{quote, author, role}]                   │
    │    - trust_signals (awards, certifications)                  │
    │                                                              │
    │  site:                                                       │
    │    - social_links: {instagram, facebook, linkedin, etc}      │
    │    - contact_info: {email, phone, address}                   │
    │                                                              │
    │  Output: WebsiteContextPack                                  │
    └─────────────────────────────────────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │   ConfidenceScorer      │
    │   confidence.py         │
    └─────────────┬───────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    CONFIDENCE SCORING                        │
    │                                                              │
    │  Weighted scoring (0-100):                                   │
    │    - brand_name: 15 pts                                      │
    │    - offer_summary: 20 pts                                   │
    │    - key_benefits: 15 pts                                    │
    │    - primary_action: 15 pts                                  │
    │    - detected_ctas: 10 pts                                   │
    │    - trust_signals: 10 pts                                   │
    │    - social_links: 5 pts                                     │
    │    - contact_info: 10 pts                                    │
    │                                                              │
    │  If score < 60:                                              │
    │    - Generate micro-questions for missing fields             │
    │    - Set status = "needs_user_input"                         │
    │                                                              │
    │  Output: ConfidenceResult                                    │
    │    - score: int                                              │
    │    - missing_fields: List[str]                               │
    │    - needs_user_input: bool                                  │
    │    - questions_to_ask: List[Question]                        │
    └─────────────────────────────────────────────────────────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ Save to MongoDB   │
        │ Update step_run   │
        │ Update pack       │
        └───────────────────┘
```

### Step 3A: Perplexity Intel Generation (Detailed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 3A: PERPLEXITY INTEL PACK                           │
└─────────────────────────────────────────────────────────────────────────────┘

  POST /api/orchestrations/{brief_id}/step-3a/start
                    │
                    ▼
        ┌───────────────────────┐
        │ Validate Prerequisites│
        │ - Brief exists        │
        │ - WebsiteContextPack  │
        │   exists              │
        └─────────┬─────────────┘
                  │
                  │ asyncio.create_task()
                  ▼
        ┌───────────────────┐
        │   run_step3a()    │
        │   (Background)    │
        └─────────┬─────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              PERPLEXITY INTEL CLIENT                         │
    │              perplexity_intel.py                             │
    │                                                              │
    │  1. Build user prompt from:                                  │
    │     - CampaignBrief (website, geo, goal, budget)            │
    │     - WebsiteContextPack (brand, offer, CTAs, proof)        │
    │                                                              │
    │  2. Call Perplexity API (sonar-pro model):                  │
    │     - System prompt: Market Intelligence Analyst role        │
    │     - JSON Schema enforcement for structured output          │
    │     - Temperature: 0.2 (low for consistency)                │
    │     - Max tokens: 4000                                       │
    │                                                              │
    │  3. Parse JSON response with retry on failure               │
    └─────────────────────────────────────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              PERPLEXITY INTEL PACK SCHEMA                    │
    │                                                              │
    │  category:                                                   │
    │    - industry, subcategory, confidence_0_100                │
    │                                                              │
    │  geo_context:                                                │
    │    - primary_market, seasonality_or_moments                 │
    │    - local_behavior_notes                                    │
    │                                                              │
    │  customer_psychology:                                        │
    │    - icp_segments (2-4 segments)                            │
    │      - name, description, top_motivations                    │
    │      - preferred_proof, cta_style_notes                      │
    │    - top_pains (3-6)                                         │
    │    - top_objections (3-6)                                    │
    │    - buying_triggers (2-5)                                   │
    │                                                              │
    │  trust_builders:                                             │
    │    - most_credible_proof_types                               │
    │    - category_specific_trust_signals                         │
    │    - risk_reducers                                           │
    │                                                              │
    │  competitors (2-3):                                          │
    │    - name, website, instagram, tiktok                        │
    │    - positioning_summary                                     │
    │                                                              │
    │  foreplay_search_blueprint:                                  │
    │    - competitor_queries (for ad library search)              │
    │    - keyword_queries                                         │
    │    - angle_queries                                           │
    │    - negative_filters                                        │
    │                                                              │
    │  angle_seeds:                                                │
    │    - hook_families, trust_themes, conversion_angles          │
    │                                                              │
    │  positioning_diagnosis:                                      │
    │    - current_promise_one_liner                               │
    │    - differentiation_strength_0_10                           │
    │    - generic_claims_found, potential_whitespace_gaps         │
    │                                                              │
    │  offer_scorecard_and_quick_wins:                             │
    │    - offer_clarity_score_0_10                                │
    │    - what_is_clear, what_is_unclear_or_missing              │
    │    - quick_wins_copy, quick_wins_proof                       │
    │                                                              │
    │  channel_and_format_fit:                                     │
    │    - channel_rankings (meta, google, tiktok, etc)           │
    │    - format_rankings (ugc, before_after, testimonial)       │
    │                                                              │
    │  brand_audit_lite:                                           │
    │    - voice: traits, do_list, dont_list                       │
    │    - archetype: primary, secondary (12 archetypes)          │
    │    - visual_vibe: vibe_keywords, imagery_style_notes         │
    │    - brand_gaps: clarity_gaps, consistency_gaps              │
    │                                                              │
    │  ui_summary:                                                 │
    │    - 5 cards: category, competitors, customer_reality,       │
    │      brand_vibe, quick_wins                                  │
    │                                                              │
    │  sources: URLs from Perplexity search                        │
    └─────────────────────────────────────────────────────────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ Save to MongoDB   │
        │ Update step_run   │
        └───────────────────┘
```

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                                  │
│                    (Optional - Wizard works anonymously)                     │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐
    │ User    │
    │ clicks  │
    │ Sign In │
    └────┬────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │ Redirect to Emergent Auth               │
    │ https://your-auth-provider.com/  │
    │   auth/v1/env/oauth/google?             │
    │   redirect_url=<app_url>                │
    └─────────────────────┬───────────────────┘
                          │
                          │ User authenticates with Google
                          ▼
    ┌─────────────────────────────────────────┐
    │ Redirect back to app with               │
    │ #session_id=<uuid> in URL fragment      │
    └─────────────────────┬───────────────────┘
                          │
                          │ AuthCallback.jsx detects fragment
                          ▼
    ┌─────────────────────────────────────────┐
    │ POST /api/auth/session                  │
    │ Body: { session_id: "<uuid>" }          │
    └─────────────────────┬───────────────────┘
                          │
                          │ Backend exchanges session_id
                          │ with Emergent Auth
                          ▼
    ┌─────────────────────────────────────────┐
    │ Backend:                                │
    │ 1. Call Emergent session-data endpoint  │
    │ 2. Create/update user in MongoDB        │
    │ 3. Create session document              │
    │ 4. Set httpOnly cookie: session_token   │
    │ 5. Return user data                     │
    └─────────────────────┬───────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────┐
    │ Frontend stores user in AuthContext     │
    │ Subsequent requests include cookie      │
    └─────────────────────────────────────────┘


    ┌─────────────────────────────────────────┐
    │ Linking Anonymous Briefs                │
    │                                         │
    │ POST /api/campaign-briefs/link          │
    │                                         │
    │ When user signs in after creating       │
    │ briefs anonymously, this endpoint       │
    │ links all briefs with matching email    │
    │ to the authenticated user.              │
    └─────────────────────────────────────────┘
```

---

## 5. Backend Implementation

### File Structure

```
/app/backend/
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── server.py              # Main FastAPI application (932 lines)
├── crawler.py             # Web crawler (537 lines)
├── extractor.py           # Data extraction (527 lines)
├── confidence.py          # Scoring logic (228 lines)
└── perplexity_intel.py    # Perplexity API client (651 lines)
```

### server.py - Key Components

```python
# Enums for type safety
class GoalType(str, Enum):
    SALES_ORDERS = "sales_orders"
    BOOKINGS_LEADS = "bookings_leads"
    BRAND_AWARENESS = "brand_awareness"
    EVENT_LAUNCH = "event_launch"

class DestinationType(str, Enum):
    WEBSITE = "website"
    WHATSAPP = "whatsapp"
    BOOKING_LINK = "booking_link"
    APP = "app"
    DM = "dm"
    OTHER = "other"

class Track(str, Enum):
    PILOT = "pilot"        # User has run ads before
    FOUNDATION = "foundation"  # User hasn't run ads yet

# Track routing logic
def compute_track(ads_intent: AdsIntent) -> Track:
    if ads_intent == AdsIntent.YES:
        return Track.PILOT
    elif ads_intent == AdsIntent.NOT_YET:
        return Track.FOUNDATION
    else:  # UNSURE
        return Track.PILOT
```

### crawler.py - Key Features

1. **HTTP-first approach**: Uses `httpx` for fast requests
2. **Playwright fallback**: For JavaScript-heavy sites
3. **Smart priority scoring**: Prioritizes valuable pages (about, pricing, services)
4. **Hard limit**: Maximum 10 pages per crawl
5. **Social link extraction**: Finds Instagram, Facebook, LinkedIn, etc.

### extractor.py - Extraction Strategy

| Data Point | Extraction Method |
|------------|-------------------|
| Brand name | `<title>`, `og:site_name`, `<h1>` |
| Tagline | Meta description, hero section |
| Logo | `<img>` with "logo" in src/alt |
| Colors | Inline styles, CSS variables |
| Benefits | `<li>` elements, feature sections |
| CTAs | `<button>`, `<a>` with action words |
| Pricing | Regex for currency patterns |
| Testimonials | Quote elements, review sections |
| Social links | `<a>` to known social domains |

### perplexity_intel.py - API Integration

- **Model**: `sonar-pro` (Perplexity's best model)
- **Temperature**: 0.2 (low for consistency)
- **JSON Schema**: Strict schema enforcement
- **Retry logic**: Automatic retry on JSON parse failure
- **Timeout**: 120 seconds

---

## 6. Frontend Implementation

### File Structure

```
/app/frontend/src/
├── App.js                 # Router setup
├── App.css                # Global styles
├── index.js               # Entry point
├── context/
│   └── AuthContext.jsx    # Authentication state
├── lib/
│   ├── api.js             # Axios instance
│   └── utils.js           # Utility functions
├── components/
│   ├── Logo.jsx           # Brand logo component
│   └── ui/                # Shadcn components
├── pages/
│   ├── Landing.jsx        # Homepage
│   ├── Wizard.jsx         # 4-step intake form
│   ├── BuildingPack.jsx   # Step 2 progress
│   ├── PackView.jsx       # Website context results
│   ├── IntelView.jsx      # Market intel results
│   ├── Dashboard.jsx      # User's briefs list
│   ├── BriefDetail.jsx    # Single brief view
│   └── AuthCallback.jsx   # OAuth callback handler
└── hooks/
    └── use-toast.js       # Toast notifications
```

### Route Configuration (App.js)

```javascript
<Routes>
  <Route path="/" element={<Landing />} />
  <Route path="/wizard" element={<Wizard />} />
  <Route path="/dashboard" element={<Dashboard />} />
  <Route path="/brief/:id" element={<BriefDetail />} />
  <Route path="/building/:briefId" element={<BuildingPack />} />
  <Route path="/pack/:briefId" element={<PackView />} />
  <Route path="/intel/:briefId" element={<IntelView />} />
</Routes>
```

### Wizard.jsx - Step Configuration

| Step | Fields | Validation |
|------|--------|------------|
| 1 | website_url, primary_goal, success_definition | URL format, goal required, max 120 chars |
| 2 | country, city_or_region, destination_type | All required |
| 3 | ads_intent, budget_range_monthly | Selection required |
| 4 | name, email | Email format validation |

### BuildingPack.jsx - Progress Events

| Event | Display Text |
|-------|--------------|
| `STEP2_STARTED` | "Starting analysis..." |
| `STEP2_FETCHED_HOME` | "Fetching your website..." |
| `STEP2_DISCOVERED_PAGES` | "Discovering pages..." |
| `STEP2_EXTRACTED_OFFER` | "Extracting offer..." |
| `STEP2_EXTRACTED_CTA` | "Finding CTAs..." |
| `STEP2_EXTRACTED_ASSETS` | "Scanning assets..." |
| `STEP2_EXTRACTED_SOCIALS` | "Finding social links..." |
| `STEP2_CONFIDENCE_SCORED` | "Scoring confidence..." |
| `STEP2_COMPLETED` | "Analysis complete!" |

---

## 7. Database Schema

### Collections

#### campaign_briefs

```javascript
{
  campaign_brief_id: "uuid",
  created_at: "2026-01-21T12:00:00Z",
  updated_at: "2026-01-21T12:00:00Z",
  track: "pilot" | "foundation",
  user_id: "user_xxx" | null,  // null for anonymous
  
  contact: {
    name: "John Doe",
    email: "john@example.com"
  },
  
  brand: {
    website_url: "https://example.com"
  },
  
  goal: {
    primary_goal: "bookings_leads",
    success_definition: "5 bookings per day"
  },
  
  geo: {
    country: "United States",
    city_or_region: "New York"
  },
  
  destination: {
    type: "website"
  },
  
  ads_intent: "yes" | "not_yet" | "unsure",
  budget_range_monthly: "<300" | "300-1000" | "1000-5000" | "5000+" | "not_sure",
  
  raw_intake: { /* original form data */ }
}
```

#### orchestration_runs

```javascript
{
  orchestration_id: "uuid",
  campaign_brief_id: "uuid",
  status: "running" | "completed" | "failed",
  created_at: "2026-01-21T12:00:00Z",
  updated_at: "2026-01-21T12:00:00Z"
}
```

#### step_runs

```javascript
{
  step_run_id: "uuid",
  orchestration_id: "uuid",
  campaign_brief_id: "uuid",
  step_key: "STEP2_WEBSITE_CONTEXT" | "STEP3A_INTEL_PERPLEXITY",
  status: "pending" | "running" | "needs_user_input" | "completed" | "failed",
  progress: {
    events: [
      {
        event: "STEP2_FETCHED_HOME",
        timestamp: "2026-01-21T12:00:00Z",
        payload: {}
      }
    ]
  },
  created_at: "2026-01-21T12:00:00Z",
  updated_at: "2026-01-21T12:00:00Z"
}
```

#### website_context_packs

```javascript
{
  website_context_pack_id: "uuid",
  campaign_brief_id: "uuid",
  status: "running" | "success" | "partial" | "needs_user_input" | "failed",
  confidence_score: 75,
  questions: [],  // Micro-questions if needs_user_input
  
  data: {
    source: {
      pages_fetched: 5,
      pages_attempted: 10,
      fetch_method: "http",
      crawl_timestamp: "2026-01-21T12:00:00Z"
    },
    
    brand_identity: {
      brand_name: "Acme Inc",
      tagline: "Quality products",
      one_liner_value_prop: "Best widgets in town",
      visual: {
        logo_asset_url: "https://...",
        primary_colors_hex: ["#000000", "#FFFFFF"],
        font_families: ["Inter", "Arial"]
      }
    },
    
    offer: {
      offer_type_hint: "service" | "product" | "saas" | "info" | "unknown",
      primary_offer_summary: "...",
      key_benefits: ["Fast", "Reliable", "Affordable"],
      differentiators: ["24/7 support"],
      pricing_mentions: ["$99/mo", "Starting at $49"]
    },
    
    conversion: {
      primary_action: "book_appointment" | "buy_now" | "call" | "dm" | "unknown",
      detected_primary_ctas: ["Book Now", "Get Started", "Contact Us"]
    },
    
    proof: {
      testimonials: [
        { quote: "Great service!", author: "Jane D.", role: "CEO" }
      ],
      trust_signals: ["100+ reviews", "Award winner"]
    },
    
    site: {
      social_links: {
        instagram: "https://instagram.com/acme",
        facebook: "https://facebook.com/acme"
      },
      contact_info: {
        email: "hello@acme.com",
        phone: "+1-555-1234"
      }
    },
    
    quality: {
      confidence_score_0_100: 75,
      missing_fields: ["pricing"]
    }
  },
  
  created_at: "2026-01-21T12:00:00Z",
  updated_at: "2026-01-21T12:00:00Z"
}
```

#### perplexity_intel_packs

```javascript
{
  intel_pack_id: "uuid",
  campaign_brief_id: "uuid",
  status: "running" | "success" | "failed",
  search_results: [],  // Raw Perplexity search results
  
  data: {
    category: {
      industry: "Beauty & Personal Care",
      subcategory: "Hair Salons",
      confidence_0_100: 85,
      notes: "..."
    },
    
    geo_context: { /* ... */ },
    customer_psychology: { /* ... */ },
    trust_builders: { /* ... */ },
    
    competitors: [
      {
        name: "Competitor A",
        website: "https://...",
        instagram: "competitor_a",
        tiktok: "@competitor_a",
        positioning_summary: "..."
      }
    ],
    
    foreplay_search_blueprint: {
      competitor_queries: ["competitor a ads", "competitor b instagram"],
      keyword_queries: ["hair salon ads", "beauty salon marketing"],
      angle_queries: ["before after hair", "transformation"],
      negative_filters: ["wholesale", "b2b"]
    },
    
    brand_audit_lite: {
      voice: {
        traits: ["friendly", "professional"],
        do_list: ["Use casual tone"],
        dont_list: ["Avoid jargon"]
      },
      archetype: {
        primary: "caregiver",
        secondary: "creator"
      },
      visual_vibe: {
        vibe_keywords: ["warm", "inviting"]
      }
    },
    
    ui_summary: {
      cards: [
        { id: "category", title: "Category Fit", chips: [...], bullets: [...] },
        { id: "competitors", title: "Competitors", chips: [...], bullets: [...] },
        { id: "customer_reality", title: "Customer Reality", chips: [...], bullets: [...] },
        { id: "brand_vibe", title: "Brand Vibe", chips: [...], bullets: [...] },
        { id: "quick_wins", title: "Quick Wins", chips: [...], bullets: [...] }
      ]
    },
    
    sources: [
      { title: "...", url: "https://..." }
    ]
  },
  
  created_at: "2026-01-21T12:00:00Z",
  updated_at: "2026-01-21T12:00:00Z"
}
```

#### users

```javascript
{
  user_id: "user_abc123",
  email: "john@example.com",
  name: "John Doe",
  picture: "https://...",
  created_at: "2026-01-21T12:00:00Z"
}
```

#### user_sessions

```javascript
{
  user_id: "user_abc123",
  session_token: "token_xyz",
  expires_at: "2026-01-28T12:00:00Z",
  created_at: "2026-01-21T12:00:00Z"
}
```

---

## 8. API Reference

### Campaign Briefs

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/campaign-briefs` | POST | Optional | Create campaign brief |
| `/api/campaign-briefs/{id}` | GET | None | Get brief by ID |
| `/api/campaign-briefs` | GET | Required | List user's briefs |
| `/api/campaign-briefs/link` | POST | Required | Link anonymous briefs to user |

### Orchestration

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/orchestrations/{briefId}/start` | POST | None | Start Step 2 |
| `/api/orchestrations/{briefId}/status` | GET | None | Get full pipeline status |

### Website Context

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/website-context-packs/by-campaign/{briefId}` | GET | None | Get Step 2 results |
| `/api/website-context-packs/{packId}/micro-input` | POST | None | Submit micro-input answers |

### Perplexity Intel

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/orchestrations/{briefId}/step-3a/start` | POST | None | Start Step 3A |
| `/api/perplexity-intel-packs/by-campaign/{briefId}` | GET | None | Get Step 3A results |

### Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/session` | POST | None | Exchange session_id for token |
| `/api/auth/me` | GET | Required | Get current user |
| `/api/auth/logout` | POST | Required | Logout |

---

## 9. Third-Party Integrations

### Emergent Auth (Google OAuth)

- **Status**: ✅ Integrated
- **Provider**: Emergent-managed OAuth
- **Endpoint**: `https://your-auth-provider.com/auth/v1/env/oauth/google`
- **Notes**: Optional - wizard works anonymously

### Perplexity AI

- **Status**: ✅ Integrated
- **Model**: `sonar-pro`
- **API**: `https://api.perplexity.ai/chat/completions`
- **Key Location**: `/app/backend/.env` as `PERPLEXITY_API_KEY`
- **Features Used**:
  - Structured JSON output
  - Web search integration
  - Source citations

### Foreplay (Planned)

- **Status**: 🔜 Not yet integrated
- **Purpose**: Competitor ad library search
- **Requires**: User API key
- **Integration Point**: Will use `foreplay_search_blueprint` from Step 3A

---

## 10. Current Issues & Bugs

### Critical Issues

| Issue | Component | Description | Impact |
|-------|-----------|-------------|--------|
| **Unknown** | Multiple | User reports "a lot of things are broken" | Needs investigation |

### Known Limitations

| Limitation | Component | Description | Workaround |
|------------|-----------|-------------|------------|
| Shadcn Dropdowns | Testing | Testing agent struggles with Select components | Manual testing required |
| Long Polling | BuildingPack, IntelView | Uses polling instead of WebSockets | Consider SSE upgrade |
| Playwright Dependency | crawler.py | Heavy dependency for fallback | Consider lighter alternatives |

### Debugging Checklist

1. **Backend not starting?**
   ```bash
   tail -n 100 /var/log/supervisor/backend.err.log
   ```

2. **Frontend not loading?**
   ```bash
   tail -n 100 /var/log/supervisor/frontend.err.log
   ```

3. **API returning errors?**
   ```bash
   curl -s http://localhost:8001/api/ | jq
   ```

4. **MongoDB connection issues?**
   - Check `MONGO_URL` in `/app/backend/.env`
   - Verify MongoDB is running: `sudo supervisorctl status mongodb`

---

## 11. Pending Work

### P0 - Critical (Blocking)

1. **Investigate "broken" features** - User reported issues need identification

### P1 - High Priority

1. **Step 3B: Foreplay Integration**
   - Requires Foreplay API key from user
   - Use `foreplay_search_blueprint` to query competitor ads
   - Extract ad formats, hooks, angles

2. **Phase 3: Copywriting Agent**
   - Generate headlines and hooks
   - Ad copy variations
   - Framework matching (PAS, AIDA, etc.)

3. **Admin Log Viewer**
   - `/admin/logs` route
   - Real-time log streaming
   - Filter by step/campaign

### P2 - Medium Priority

1. **Real-time Updates**
   - Replace polling with Server-Sent Events (SSE)
   - WebSocket for bidirectional communication

2. **Asset Storage**
   - Download and store logos/images
   - S3/R2 integration

3. **Experiment Engine**
   - A/B test planning
   - Hypothesis tracking

### P3 - Future

1. **Analytics & Learning**
   - Performance data ingestion
   - Learning loop

2. **Image/Video Generation**
   - AI creative generation
   - Template system

---

## 12. Optimization Opportunities

### Performance

| Area | Current | Optimization | Impact |
|------|---------|--------------|--------|
| **Crawling** | Sequential page fetches | Parallel fetching with asyncio.gather | 2-3x faster |
| **Polling** | 2-3 second intervals | Server-Sent Events | Real-time updates, less server load |
| **Perplexity API** | Single request | Caching for similar queries | Cost reduction |
| **Frontend Bundle** | Full Shadcn import | Tree-shaking unused components | Smaller bundle |

### Code Quality

| Area | Current State | Improvement |
|------|---------------|-------------|
| **Error Handling** | Basic try/catch | Structured error types, better user feedback |
| **Logging** | Print statements | Structured logging with correlation IDs |
| **Testing** | Pytest + Playwright | Add unit tests for extractor/scorer |
| **Types** | Partial Pydantic | Full type coverage, TypeScript strict mode |

### Architecture

| Area | Current | Recommendation |
|------|---------|----------------|
| **Background Tasks** | asyncio.create_task | Consider Celery/Redis for production |
| **Rate Limiting** | None | Add rate limiting for API endpoints |
| **Caching** | None | Redis for session caching, API response caching |
| **Monitoring** | Basic logs | Add Sentry, metrics (Prometheus) |

### Database

| Area | Current | Recommendation |
|------|---------|----------------|
| **Indexes** | None defined | Add indexes on campaign_brief_id, user_id |
| **TTL** | None | Add TTL on user_sessions |
| **Aggregation** | Direct queries | Aggregation pipelines for analytics |

---

## 13. Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB
- Playwright browsers (for crawler fallback)

### Environment Variables

#### Backend (`/app/backend/.env`)

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=novara
PERPLEXITY_API_KEY=pplx-xxxxxxxx
```

#### Frontend (`/app/frontend/.env`)

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

### Running Locally

```bash
# Backend
cd /app/backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd /app/frontend
yarn install
yarn start
```

### Supervisor Commands

```bash
# Check status
sudo supervisorctl status

# Restart services
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# View logs
tail -f /var/log/supervisor/backend.out.log
tail -f /var/log/supervisor/frontend.out.log
```

---

## 14. Testing

### Test Files

- `/app/tests/test_novara_step3a.py` - Backend API tests
- `/app/test_reports/iteration_*.json` - Test results

### Running Tests

```bash
cd /app
pytest tests/ -v
```

### Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| API Health | 1 | ✅ |
| Campaign Brief CRUD | 2 | ✅ |
| Step 2 Orchestration | 3 | ✅ |
| Step 3A Intel | 3 | ✅ |
| Edge Cases | 3 | ✅ |
| **Total** | **13** | **100%** |

### Manual Testing

For Shadcn Select components (known automation issues):

1. Navigate to wizard manually
2. Click dropdown trigger
3. Wait for options to appear
4. Click desired option

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Campaign Brief** | User's initial input about their brand and goals |
| **Website Context Pack** | Structured data extracted from user's website |
| **Perplexity Intel Pack** | Market intelligence generated by Perplexity AI |
| **Orchestration** | The overall pipeline run for a campaign |
| **Step Run** | Individual step within an orchestration |
| **Track** | User routing: Pilot (has run ads) vs Foundation (hasn't) |
| **Micro-questions** | Follow-up questions when extraction confidence is low |
| **Foreplay** | Third-party ad library for competitor research |

---

## Appendix B: Contact & Resources

- **Preview URL**: http://localhost:8001
- **Repository**: (via Emergent platform)
- **Perplexity API Docs**: https://docs.perplexity.ai

---

*Document generated: January 21, 2026*
