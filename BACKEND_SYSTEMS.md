# Novara Platform: Backend Systems Reference
> For product team brainstorming and feature planning
> Last updated: Feb 22, 2026

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Data Flow: End-to-End](#2-data-flow-end-to-end)
3. [Step 1: Campaign Brief (User Intake)](#3-step-1-campaign-brief)
4. [Step 2: Website Context Extraction](#4-step-2-website-context-extraction)
5. [Step 3A: Perplexity Intel Pack](#5-step-3a-perplexity-intel-pack)
6. [Intelligence Hub: Research Modules](#6-intelligence-hub-research-modules)
7. [API Cost Map](#7-api-cost-map)
8. [Database Collections](#8-database-collections)
9. [3rd Party Dependencies](#9-3rd-party-dependencies)
10. [Known Limitations & Opportunities](#10-known-limitations--opportunities)

---

## 1. System Overview

Novara is a backend pipeline that takes a **company website URL** and produces a full **brand intelligence dossier** through automated scraping, AI analysis, and multi-source research.

**Stack**: FastAPI + MongoDB + React
**Core principle**: Each pipeline step is **independently runnable and re-runnable** with snapshot-based storage (every run creates a timestamped snapshot, enabling history/diff).

```
User enters URL + Country
        |
        v
  [Step 1: Campaign Brief]  -----> Stored in MongoDB
        |
        v
  [Step 2: Website Context]  -----> Crawl + Scrape + LLM Summarize
        |
        v
  [Step 3A: Perplexity Intel] ----> Market research via Perplexity
        |
        v
  [Intelligence Hub]  ------------> 8 independent research modules
        |                           (each can run/re-run independently)
        v
  [Frontend Display]  ------------> PackView (Brand Overview)
                                    IntelligenceHub (Deep Dive Tabs)
```

---

## 2. Data Flow: End-to-End

### Phase 1: Input Collection
```
Wizard UI --POST--> /api/campaign-briefs
                    Creates: campaign_brief document
                    Contains: website_url, country, city, goal, budget, ads_intent
```

### Phase 2: Website Analysis (Step 2)
```
Frontend --POST--> /api/orchestrations/{id}/start
                   |
                   v
            Background task: run_step2()
                   |
    +--------------+---------------+
    |              |               |
    v              v               v
  Crawl         Extract         Summarize
  (Playwright   (Brand ID,     (Gemini 3 Flash
   + HTTP)       Assets,        or Perplexity
                 Pricing,       fallback)
                 Channels)
                   |
                   v
            website_context_pack (MongoDB)
```

### Phase 3: Market Intel (Step 3A)
```
Frontend --POST--> /api/orchestrations/{id}/step-3a/start
                   |
                   v
            Perplexity sonar-pro
            (single call with structured JSON output)
                   |
                   v
            perplexity_intel_pack (MongoDB)
            Contains: category, competitors, audience persona,
                      content angles, seasonality hints
```

### Phase 4: Intelligence Hub (8 Modules)
```
Frontend triggers each module independently:
  POST /api/research/{id}/competitors/run
  POST /api/research/{id}/ads-intel/run
  POST /api/research/{id}/reviews/run
  POST /api/research/{id}/customer-intel/run
  POST /api/research/{id}/search-intent/run
  POST /api/research/{id}/seasonality/run
  POST /api/research/{id}/community/run
  POST /api/research/{id}/social-trends/run
```

---

## 3. Step 1: Campaign Brief

**What it does**: Captures user intent and business context.

**Inputs collected**:
| Field | Purpose |
|-------|---------|
| `website_url` | The target to analyze |
| `country` | Geo-targeting for all downstream modules |
| `city_or_region` | Local market context |
| `primary_goal` | sales_orders / bookings_leads / brand_awareness / event_launch |
| `success_definition` | Free-text, max 120 chars |
| `destination_type` | website / whatsapp / booking_link / app / dm |
| `ads_intent` | yes / not_yet / unsure (determines "track": pilot vs foundation) |
| `budget_range_monthly` | <300 / 300-1000 / 1000-5000 / 5000+ / not_sure |

**Track routing logic**:
- `ads_intent == "yes"` -> Pilot track (ready for ads)
- `ads_intent == "not_yet"` -> Foundation track (needs prep work)
- `ads_intent == "unsure"` -> Defaults to Pilot

**Authentication**: Google OAuth via Emergent Auth. Anonymous users can create briefs; briefs are linked to accounts via email on login.

---

## 4. Step 2: Website Context Extraction

**File**: `step2_pipeline.py` (pure functions) + `server.py` (orchestration)

This is the most complex pipeline. It runs **7 stages** in sequence:

### Stage 1: Crawl (`crawler.py`)
- **Strategy**: HTTP-first with Playwright fallback
- **Smart Priority Crawl**: Prioritizes pages by type (homepage > services > about > pricing > contact)
- **Hard Limit**: Max ~10 pages to control cost/time
- **Output**: `CrawlResult` with raw HTML, extracted text, links, screenshot, CSS

**How it works**:
1. Fetch homepage via httpx (fast, no JS)
2. Parse HTML with BeautifulSoup, extract all internal links
3. Classify links by page type (booking, services, about, etc.)
4. Fetch priority pages via httpx
5. If JS-heavy site detected (< 500 chars), fall back to Playwright headless Chrome
6. Capture full-page screenshot of homepage via Playwright
7. Collect CSS files for brand identity extraction

### Stage 2: Extract Raw (`extractor.py`)
- Parses crawled HTML into structured data: text chunks, headings, CTAs, price mentions, emails, phones
- Feeds downstream stages (LLM, pricing, channels)

### Stage 2A: Jina Enrichment
- **Trigger**: Only if crawl returned < 500 chars of text (JS-heavy SPAs)
- **Action**: Calls Jina Reader API (`r.jina.ai/{url}`) for rendered markdown
- **Purpose**: Fills content gaps for React/Wix/Squarespace sites
- **Cost**: Free tier, no API key needed

### Stage 2B: SPA Service Extraction (`spa_service_extractor.py`)
- **Trigger**: If a booking/services page is detected in crawled links
- **Method 1**: Playwright - opens the booking page, clicks through Wix tab widgets, extracts all services with names, prices, durations, descriptions, booking URLs
- **Method 2**: Jina Reader fallback if Playwright fails
- **Resilience**: Uses `_find_browser_executable()` to auto-discover Playwright Chrome path (permanent fix for env issues)

**Output structure per service**:
```json
{
  "name": "Keratin Treatment",
  "category": "Hair",
  "price": "AED 350",
  "duration": "90 min",
  "description": "...",
  "booking_url": "https://..."
}
```

### Stage 3: Brand Identity (`brand_identity.py`)
- Parses CSS for colors (hex values with role assignment: primary/secondary/accent/bg)
- Parses CSS and HTML for fonts (filters system fonts, keeps brand fonts only)
- **No API calls** - purely computational

### Stage 4: Assets (`assets.py`)
- Ranks all discovered images by quality score (0-100)
- Detects logo (favicon, og:image, highest-ranked small image)
- Deduplicates Wix-style resized variants

### Stage 5: Pricing (`pricing.py`)
- Aggregates all price mentions from crawl + SPA extraction
- Computes min/avg/max, detects currency
- **No API calls** - regex-based extraction

### Stage 5B: Channels (`channels.py` + fallbacks)
- Extracts social media profiles from HTML links
- **Fallback chain** if crawler finds nothing:
  1. Jina Reader (scrape rendered page for social links)
  2. Perplexity sonar (ask "What are the social profiles for X?")
- Deduplicates by platform

### Stage 6: LLM Summarization (`gemini_site_summarizer.py`)
- **Primary**: Gemini 3 Flash via Google AI SDK
- **Fallback**: Perplexity sonar-pro
- **Input**: All raw text chunks + pricing data
- **Output**: Structured JSON matching `STEP2_LLM_OUTPUT_SCHEMA`:
  - Classification (industry/subcategory/niche/tags)
  - Brand summary (name/tagline/one_liner/bullets)
  - Brand DNA (values/tone/aesthetic/visual_vibe)
  - Offer (value_prop/key_benefits/catalog)
  - Conversion (primary_action/destination_type)

### Stage 7: Build Output
- Assembles all stage outputs into final `step2_data` (public) and `step2_internal` (debug)
- Computes confidence score (0-100) based on data completeness
- Determines status: `success` (>=70), `partial` (>=50), `needs_review` (<50), `failed`

---

## 5. Step 3A: Perplexity Intel Pack

**File**: `perplexity_intel.py`

**What it does**: Single Perplexity sonar-pro call that generates a structured market intelligence pack.

**Input**: Campaign brief + Website context pack (from Step 2)

**Output fields**:
- `category`: Industry classification with market size hints
- `competitors`: 3-5 competitors with URLs, positioning, tier (budget/mid/premium)
- `audience_persona`: Target customer archetype
- `content_angles`: Recommended marketing angles
- `seasonality_hints`: Key calendar moments for the business

**Config**: model=sonar-pro, temperature=0.2, max_tokens=4000

**Purpose**: Provides the initial competitor list and market context that seeds the Intelligence Hub modules.

---

## 6. Intelligence Hub: Research Modules

Each module follows the same pattern:
1. **Gather inputs** from Step 1 + Step 2 + other modules (never blocks on missing data)
2. **Call Perplexity** (or Foreplay for ads) with a purpose-built prompt
3. **Post-process** the response into a typed schema
4. **Save snapshot** to MongoDB (with timestamp + refresh_due_at)
5. **Return** the snapshot to the frontend

### 6.1 Competitors Module
**Files**: `research/competitors/`
**API**: Perplexity sonar (1 call)
**What it finds**: 2-3 direct competitors with:
- Website URL, social profiles
- Positioning summary
- Price tier (budget/mid/premium)
- Key differentiators
**Used by**: Ads Intel (as seeds), Search Intent (as keyword source), Reviews (for comparison)

### 6.2 Ads Intelligence Module
**Files**: `research/ads_intel/`
**API**: Foreplay API (multiple calls)
**Pipeline**:
```
Competitor Seeds -----> Foreplay: domain -> brand lookup -> fetch ads (limit 80)
                        |
Category Seeds -------> Foreplay: discovery_ads(query, limit 80, min_days 30)
                        |
Both streams ---------> Postprocess (normalize, deduplicate)
                        |
                ---------> Composite Scoring (8 signals, 0-100)
                        |
                ---------> Shortlist (diversity caps per brand/query)
                        |
                ---------> Pattern Detection (zero-cost trait analysis)
                        |
                ---------> Build Snapshot + Save
```

**Composite Scoring (8 signals, max 100 points)**:
| Signal | Max Points | What it measures |
|--------|-----------|-----------------|
| Longevity | 35 | How long the ad has been running (90+ days = max) |
| Liveness | 15 | Is the ad currently active? |
| Recency | 15 | How recently started + still running = active investment |
| Format | 10 | Video (10) > Carousel (7) > Image (4) |
| Content | 10 | Has both headline AND body text? |
| CTA | 5 | Has a call-to-action button? |
| Landing Page | 5 | Has a landing page URL? |
| Preview | 5 | Has a real visual preview (not just avatar)? |

**Tiers**:
- Proven Winner (>= 70): Long-running, active, well-crafted
- Strong Performer (>= 50): Solid metrics
- Rising (>= 30): Newer but promising
- Notable (< 30): Shortlisted for relevance

**Pattern Detection** (zero API cost):
Analyzes the top-scored ads to detect common traits:
- Format dominance (e.g., "Video ads dominate top performers")
- Platform distribution (e.g., "Facebook leads for high-scoring ads")
- Average longevity of top ads
- Active rate among top ads
- CTA and content richness patterns
- Competitor vs category source split

**Foreplay API cost per run**:
- Best case: ~10 API calls (5 competitor lookups + 5 ad fetches)
- Worst case: ~39 API calls (all fallbacks trigger)
- Shortlisting keeps ~40 ads from potentially 1000+ raw

### 6.3 Reviews & Reputation Module
**Files**: `research/reviews/`
**API**: Perplexity sonar (2 calls)
**Pipeline**:
1. **Discovery call**: Find all review platforms (Google, Yelp, TripAdvisor, app stores, niche platforms)
2. **Analysis call**: Extract themes, quotes, trust signals, compute reputation readiness score
**Output**: Strength themes, weakness themes, social proof snippets, brand vs reality comparison

### 6.4 Customer Intel Module
**Files**: `research/customer_intel/`
**API**: Perplexity sonar (1 call)
**What it produces**: Target customer persona, buying triggers, decision-making factors, pain points

### 6.5 Search Intent Module
**Files**: `research/search_intent/`
**API**: Google Suggest (free) + optional Perplexity (1 call for LLM curation)
**Pipeline**:
```
Seeds (from Step 2 + Competitors)
    |
    v
Google Suggest API (autocomplete queries)
    |
    v
Blocklist Cleaning (remove irrelevant queries)
    |
    v
BRP Filter (Brand Relevance Profile scoring)
    |
    v
Scoring + Deduplication
    |
    v
Bucketing (price / trust / urgency / comparison / general)
    |
    v
Top 10 Selection
    |
    v
Optional LLM Cleanup (Perplexity)
    |
    v
Derived outputs: ad keywords + forum queries
```

### 6.6 Seasonality Module
**Files**: `research/seasonality/`
**API**: Perplexity sonar (1 call)
**What it produces**: Key calendar moments, buying triggers, seasonal demand patterns specific to the business's location and niche

### 6.7 Community Module
**Files**: `research/community/`
**API**: Perplexity sonar (2 calls: discovery + synthesis)
**What it finds**: Real forum threads (Reddit, Quora, niche forums), extracts themes, language bank, audience insights

### 6.8 Social Trends Module
**Files**: `research/social_trends/`
**API**: Multiple (handle discovery + content analysis)
**What it does**: Discovers social handles for the brand and competitors, analyzes content trends

---

## 7. API Cost Map

**Per analysis run (one URL)**:

| Step | Provider | Calls | Model | Est. Cost |
|------|----------|-------|-------|-----------|
| Step 2: LLM Summarize | Google AI (Gemini 3 Flash) | 1 | gemini-3-flash | ~$0.01 |
| Step 2: Social fallback | Perplexity | 0-1 | sonar | ~$0.005 |
| Step 2: Jina enrichment | Jina | 0-1 | - | Free |
| Step 3A: Intel Pack | Perplexity | 1 | sonar-pro | ~$0.05 |
| Competitors | Perplexity | 1 | sonar | ~$0.01 |
| Ads Intel | Foreplay | 10-39 | - | Per Foreplay plan |
| Reviews | Perplexity | 2 | sonar | ~$0.02 |
| Customer Intel | Perplexity | 1 | sonar | ~$0.01 |
| Search Intent | Google Suggest + Perplexity | 10-20 + 0-1 | sonar | ~$0.01 |
| Seasonality | Perplexity | 1 | sonar | ~$0.01 |
| Community | Perplexity | 2 | sonar | ~$0.02 |

**Total estimated cost per full analysis: ~$0.13 + Foreplay**

**Cost-free operations**: Brand identity, assets, pricing, pattern detection, scoring

---

## 8. Database Collections

| Collection | Purpose | Key Fields |
|-----------|---------|------------|
| `users` | User accounts | user_id, email, name, picture |
| `user_sessions` | Auth sessions | session_token, user_id, expires_at |
| `campaign_briefs` | Step 1 intake | campaign_brief_id, brand.website_url, geo, goal |
| `orchestration_runs` | Pipeline coordination | orchestration_id, campaign_brief_id, status |
| `step_runs` | Individual step tracking | step_run_id, step_key, progress.events[] |
| `website_context_packs` | Step 2 output | step2 (public data), step2_internal (debug), screenshot |
| `perplexity_intel_packs` | Step 3A output | data (structured intel), raw_api_response |
| `research_packs` | Aggregated research | sources.{module_name} |
| `research_snapshots_{module}` | Per-module snapshots | campaign_id, snapshot data, captured_at |
| `debug_logs` | Debug events | campaign_brief_id, events[] |

**Snapshot pattern**: Every research module stores its latest snapshot + maintains a history collection. Each snapshot has `captured_at` and `refresh_due_at` (default 14 days).

---

## 9. 3rd Party Dependencies

| Service | Used For | Key Required | Rate Limits |
|---------|----------|-------------|-------------|
| **Perplexity AI** | Market research (sonar, sonar-pro) | PERPLEXITY_API_KEY | Per plan |
| **Google AI (Gemini)** | Site summarization (primary) | GOOGLE_AI_API_KEY | Per plan |
| **Foreplay API** | Ad library data | FOREPLAY_API_KEY | Per plan |
| **Jina Reader** | SPA content fallback | None (free tier) | Best-effort |
| **Google Suggest** | Autocomplete queries | None | Best-effort |
| **Playwright** | Headless Chrome for SPAs | None (installed) | Local resource |
| **Emergent Auth** | Google OAuth | Managed by platform | N/A |
| **OpenAI (Emergent Key)** | Available for future use | EMERGENT_LLM_KEY | Per balance |

---

## 10. Known Limitations & Opportunities

### Current Limitations
1. **No Google/LinkedIn Ads**: Foreplay covers Meta (Facebook/Instagram) and TikTok. Google Ads Library and LinkedIn require separate integrations.
2. **Static analysis only**: We crawl once and analyze. No ongoing monitoring or alerting.
3. **No A/B comparison**: Can't compare two brands side-by-side.
4. **Single-market focus**: Geo-filtering works, but multi-market comparison is not built.
5. **No ad spend estimation**: We see ad creatives and duration, but not spend data.

### Opportunities for Future Features
1. **Trend Tracking**: Store snapshots over time -> show how competitors' ad strategies evolve
2. **Ad Swipe File**: Let users bookmark/save winning ads into personal collections
3. **Creative Recommendations**: Use scoring patterns to generate "Here's what to try next" suggestions
4. **Alert System**: "Competitor X just launched a new video campaign"
5. **Multi-brand Dashboard**: Agency view comparing multiple client brands
6. **Export to Ad Platforms**: Generate ad copy/creative briefs based on winning patterns
7. **Landing Page Analysis**: Scrape and score competitor landing pages
8. **Budget Estimation**: Correlate ad longevity + format + platform with estimated spend ranges
9. **Seasonal Playbook**: Auto-generate a 12-month content/ad calendar based on seasonality + competitor timing
10. **Integration with Ad Platforms**: Push recommended keywords/audiences directly to Meta/Google Ads

---

*This document covers the backend as of Feb 22, 2026. Frontend architecture is documented separately in PRD.md.*
