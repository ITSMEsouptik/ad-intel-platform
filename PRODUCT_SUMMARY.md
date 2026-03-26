# Novara - Product Feature Summary
> **Last Updated:** February 10, 2026  
> **Version:** 3.0

---

## 🎯 Product Overview

**Novara** is a strategy-led AI ad experimentation platform that helps brands and agencies build high-impact digital ads at scale. The platform gathers comprehensive intelligence about a business before any creative work begins.

**Core Philosophy:** Research First, Create Later
- Gather structured intelligence about the brand
- Understand the market, competitors, and customer behavior
- Then (future) generate ad strategies and creatives based on data

---

## 🏗️ System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│   STEP 1        │     │   STEP 2        │     │   INTELLIGENCE HUB      │
│   Campaign      │────▶│   Business DNA  │────▶│   (Research Foundation) │
│   Brief         │     │   Extraction    │     │                         │
└─────────────────┘     └─────────────────┘     │  ├─ Market Intel        │
                                                │  ├─ Search Demand       │
                                                │  ├─ Seasonality         │
                                                │  └─ Competitors         │
                                                └─────────────────────────┘
```

**Tech Stack:**
- Frontend: React 18 + TailwindCSS + Shadcn UI
- Backend: FastAPI (Python)
- Database: MongoDB
- Web Crawling: httpx + Playwright
- LLM Providers: Perplexity AI (sonar), Google Gemini 2.0 Flash

---

## 📝 STEP 1: Campaign Brief Intake

**Purpose:** Collect essential information about the brand and campaign goals.

**What We Capture:**

| Field | Description |
|-------|-------------|
| Website URL | Brand's website for crawling |
| Business Goal | Brand awareness, lead generation, sales, etc. |
| Country | Target market country |
| City/Region | Specific geographic targeting |
| Destination Type | Where traffic goes (website, WhatsApp, app, form) |
| Ads Intent | What they want to achieve with ads |
| Budget Range | Monthly ad spend range |
| Contact Info | Name and email |

**User Flow:**
1. Enter website URL
2. Select business goal
3. Choose target geography
4. Provide contact information
5. Redirects to Step 2 (Business DNA extraction)

---

## 🧬 STEP 2: Business DNA Extraction

**Purpose:** Automatically extract everything we need to know about the brand from their website.

**How It Works:**
1. **Crawl** - Visits up to 10 pages on the website
2. **Screenshot** - Captures hero screenshot using Playwright
3. **Extract** - Pulls text, images, colors, fonts, pricing
4. **Summarize** - Uses Gemini 2.0 Flash to structure the data
5. **Post-process** - Cleans and validates all outputs

### Data Extracted:

#### Site Information
- Input URL, Final URL (after redirects), Domain
- Page title, Meta description, Language

#### Classification
| Field | Example |
|-------|---------|
| Industry | "Beauty & Wellness" |
| Subcategory | "On-demand Beauty Services" |
| Niche | "At-home Hair & Makeup Dubai" |
| Tags | ["bridal", "home service", "corporate"] |

#### Brand Summary
- **Name:** Brand name extracted from website
- **Tagline:** Brand's tagline or slogan
- **One-liner:** Single sentence describing what they do
- **Bullets:** 3-5 key facts about the business (concrete, specific)

#### Brand DNA (Chips)
| Category | Example Values |
|----------|----------------|
| Values | "Convenience", "Empowerment", "Quality" |
| Tone of Voice | "Friendly", "Professional", "Modern" |
| Aesthetic | "Clean", "Feminine", "Minimal" |
| Visual Vibe | "Soft Pink", "White Space", "Lifestyle" |

#### Visual Identity
- **Logo:** Primary logo URL with candidates
- **Colors:** Up to 6 brand colors with roles (primary, secondary, accent)
- **Fonts:** Up to 3 fonts (heading, body, accent)

#### Offer Information
- **Value Proposition:** Core value statement
- **Key Benefits:** 3-5 specific benefits
- **Offer Catalog:** List of services/products with descriptions and price hints

#### Pricing Intelligence
- Currency detected
- Price range (min, avg, max)
- Number of prices found
- Source URLs for each price

#### Conversion Information
- Primary CTA (e.g., "Book Now", "Get Started")
- All CTAs found on site
- Destination type (website, WhatsApp, form, app)

#### Channels
- Social media (Instagram, TikTok, YouTube, Facebook, LinkedIn, Twitter)
- Messaging (WhatsApp, Telegram)
- Apps (App Store, Google Play)

#### Assets
- Image assets extracted from website (filtered for quality)

---

## 🔬 INTELLIGENCE HUB (Research Foundation)

**Purpose:** Gather market intelligence from multiple sources to inform ad strategy.

**Location:** `/intel/:campaignId`

**4 Research Modules:**

---

### 1️⃣ Market Intel

**Purpose:** High-level market overview and competitive landscape.

**Data Source:** Perplexity AI (sonar-pro model with web search)

**What It Provides:**
- Market overview and trends
- Competitive landscape analysis
- Customer psychology insights
- Key market dynamics

---

### 2️⃣ Search Demand (v2)

**Purpose:** Understand what potential customers are searching for.

**Data Sources:**
- Google Suggest API (free, no key) - Raw query generation
- Gemini 2.0 Flash - Curation and quality cleanup

**Pipeline:**
```
1. Build keyword sets from Step 1 + Step 2 data
2. Generate smart seed queries (up to 28 seeds)
3. Fetch Google Suggest results
4. Filter through blocklist
5. Score relevance (brand + niche matching)
6. Classify into intent buckets
7. LLM curation (typo fix, deduplication, validation)
8. Return top 10 + ad keywords + forum queries
```

**What It Provides:**

| Output | Description |
|--------|-------------|
| Top 10 Queries | Most relevant search queries |
| Intent Buckets | Queries grouped by intent: Price, Trust, Urgency, Comparison, General |
| Ad Keywords | High-intent queries good for ad targeting |
| Forum Queries | Reddit and Quora search queries for research |

**Example Output:**
```
Top Queries:
- "home salon dubai"
- "bridal makeup artist at home"
- "party makeup dubai price"

Intent Buckets:
- Price: "how much does home makeup cost dubai"
- Trust: "best home beauty service dubai reviews"
- Urgency: "last minute bridal makeup dubai"
```

---

### 3️⃣ Seasonality

**Purpose:** Identify when demand peaks and what triggers purchases.

**Data Source:** Perplexity AI (sonar model with web search)

**What It Provides:**

| Output | Description |
|--------|-------------|
| Key Moments | 4-6 calendar moments with demand levels |
| Time Windows | When each moment occurs |
| Why People Buy | Real motivation during each period |
| Purchase Triggers | Specific events that trigger buying |
| Booking Patterns | When customers typically book relative to events |
| Evergreen Demand | Year-round reasons people buy |
| Weekly Patterns | Peak days and why |
| Local Insights | Cultural/regional factors affecting demand |

**Example Output:**
```
Key Moments:
1. Wedding Season (Feb-May) - HIGH demand
   - Triggers: "Wedding invitation received", "Engagement announcement"
   - Booking: 2-4 weeks before event

2. Ramadan/Eid (varies) - HIGH demand
   - Triggers: "Eid preparations", "Family gatherings"
   - Booking: 1-2 weeks before

3. National Day (Dec 2) - MODERATE demand
   - Triggers: "Holiday events", "Celebrations"
```

---

### 4️⃣ Competitors (v3.0)

**Purpose:** Find direct competitors and understand the competitive landscape.

**Data Source:** Perplexity AI (sonar model with web search)

**Smart Features:**

| Feature | Description |
|---------|-------------|
| Business Type Detection | Automatically detects if brand is a "platform/marketplace" or "service provider" |
| Price Tier Detection | Uses price data + brand signals (aesthetic, tone) to determine tier |
| URL Validation | Validates all competitor websites are actually working |
| Retry Logic | If < 3 valid competitors, retries with exclusion list |
| Platform Exclusion | Excludes marketplaces (Fresha, Booksy, etc.) when client is a service provider |

**What It Provides:**

#### Market Overview (Structured)
| Field | Description |
|-------|-------------|
| Competitive Density | Low, Moderate, High, or Saturated |
| Dominant Player Type | Who dominates (independents, chains, platforms, mixed) |
| Market Insight | Non-obvious insight about the market |
| Ad Landscape Note | What to expect in paid ads (who's advertising, common angles) |

#### For Each Competitor (3-5)
| Field | Description |
|-------|-------------|
| Name | Competitor brand name |
| Website | Validated, working root domain |
| Instagram URL/Handle | If active account exists |
| TikTok URL/Handle | If active account exists |
| What They Do | One sentence description |
| Positioning | Their main value proposition |
| Why Competitor | Specific reason they compete |
| Price Tier | Budget, mid-range, premium, luxury |
| Estimated Size | Small, medium, large |
| Overlap Score | High, medium, low |

**Example Output:**
```
Market Overview:
- Density: Moderate
- Dominates: Independents
- Insight: "Independents thrive on bespoke luxury experiences"
- Ad Landscape: "Heavy Meta ads from platforms, independents rely on Instagram organic"

Competitors:
1. Nooora (nooora.com) - HIGH overlap, premium, large
   - "Premium at-home beauty platform for Dubai's luxury market"
   - Why: "Same target audience, similar service offering"

2. Ruuby (ruuby.com) - HIGH overlap, luxury, large
   - "On-demand beauty concierge service"
   - Why: "Direct competitor in premium home beauty segment"
```

---

## 🛠️ Admin & Debug Tools

**Debug Dashboard:** `/admin/debug/:campaignId`
- View raw data from all pipeline stages
- Monitor crawl progress
- Inspect LLM responses
- Real-time log viewing

---

## 📊 Data Flow Summary

```
User Input (Step 1)
       │
       ▼
Website Crawl (Step 2)
       │
       ├──▶ Brand DNA Pack (stored)
       │
       ▼
Intelligence Hub
       │
       ├──▶ Market Intel ──▶ Perplexity sonar-pro ──▶ Market overview
       │
       ├──▶ Search Demand ──▶ Google Suggest + Gemini ──▶ Search queries
       │
       ├──▶ Seasonality ──▶ Perplexity sonar ──▶ Calendar moments
       │
       └──▶ Competitors ──▶ Perplexity sonar + URL validation ──▶ Competitor profiles
```

---

## 🔮 Future Phases (Not Yet Built)

1. **Creative Strategy Layer** - Synthesize research into ad angles, hooks, messaging frameworks
2. **Ad Sampling** - Show what ads look like in the niche
3. **Copywriting Agent** - Generate ad copy based on research
4. **Experiment Engine** - A/B testing framework
5. **Analytics Dashboard** - Performance tracking
6. **Image/Video Generation** - Creative asset generation

---

## 💰 Cost Structure (Per Campaign)

| Module | Provider | Estimated Cost |
|--------|----------|----------------|
| Step 2 (Business DNA) | Gemini 2.0 Flash | ~$0.001 |
| Market Intel | Perplexity sonar-pro | ~$0.01 |
| Search Demand | Google Suggest (free) + Gemini | ~$0.001 |
| Seasonality | Perplexity sonar | ~$0.006 |
| Competitors | Perplexity sonar (1-3 calls) | ~$0.006-0.018 |
| **Total per campaign** | | **~$0.02-0.03** |

---

## 🔗 Key URLs

| Page | URL |
|------|-----|
| Homepage | `/` |
| Campaign Wizard | `/wizard` |
| Building Progress | `/building/:briefId` |
| Business DNA View | `/pack/:briefId` |
| Intelligence Hub | `/intel/:briefId` |
| Debug Dashboard | `/admin/debug/:briefId` |

---

## 📝 API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/campaign-briefs` | Create new campaign |
| POST | `/api/orchestrations/:briefId/start` | Start Step 2 extraction |
| GET | `/api/orchestrations/:briefId/status` | Poll extraction progress |
| GET | `/api/website-context-packs/by-campaign/:briefId` | Get Business DNA |
| POST | `/api/research/:briefId/search-intent/run` | Run search demand |
| GET | `/api/research/:briefId/search-intent/latest` | Get search demand data |
| POST | `/api/research/:briefId/seasonality/run` | Run seasonality |
| GET | `/api/research/:briefId/seasonality/latest` | Get seasonality data |
| POST | `/api/research/:briefId/competitors/run` | Run competitors |
| GET | `/api/research/:briefId/competitors/latest` | Get competitors data |
