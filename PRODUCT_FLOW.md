# Novara: Product Flow & Vision
> How the system works, why each step matters, and where we're headed
> Feb 2026

---

## The Big Picture

Novara takes a business website and turns it into ready-to-run ad creatives. The full journey:

```
Website URL  -->  Understand the Brand  -->  Research the Market  -->  Creative Strategy  -->  Ad Assets
     1                   2                         3                        4                    5
```

**Steps 1-3 are built. Steps 4-5 are next.**

Everything we've built so far is the intelligence layer — the research engine that feeds the creative machine. Without deep, accurate brand understanding and competitive intelligence, any creative output would be generic. The research phase ensures every ad we eventually generate is informed by real data: what competitors are doing, what's winning, what the audience responds to, and what makes this brand unique.

---

## What We've Built (Steps 1-3)

### Step 1: "Tell us about your business"

**What happens**: The user enters their website URL and country. Optionally, they answer a few quick context questions — their goal (sales, bookings, awareness), budget range, and whether they're already running ads.

**Why it matters for creative strategy**: This is the creative brief seed. A beauty salon in Dubai targeting bookings needs completely different creative than a SaaS tool in London targeting signups. The goal and budget shape everything downstream — tone, format, platform selection, and urgency of messaging.

**What we learn**:
- The business and where it operates
- What success looks like to them
- How ready they are for paid ads
- Where they want to send traffic (website, WhatsApp, booking page)

---

### Step 2: "Let us study your brand"

**What happens**: We automatically analyze the business's website — crawling pages, reading content, extracting visual identity, finding services/products, and using AI to summarize everything into a structured brand profile.

**Why it matters for creative strategy**: This is the brand bible that ensures every ad *feels* like it belongs to this business. Without it, we'd produce generic ads that could belong to anyone. With it, we can match their tone, use their actual colors and fonts, reference their real services and pricing, and highlight their genuine differentiators.

**What we extract**:

| What | Why it matters for ads |
|------|----------------------|
| **Brand name, tagline, one-liner** | Headlines and copy need to reflect how the brand talks about itself |
| **Industry classification** (e.g., "Beauty & Wellness > At-home Services > Bridal Makeup, Dubai") | Determines which competitor ads to study, which trends to follow |
| **Brand DNA** — values, tone of voice, aesthetic, visual vibe | A luxury brand needs elegant, restrained creative. A fun, youthful brand needs bold, energetic creative. This data drives those decisions |
| **Services/products with pricing** | Ad copy needs to reference real offers. "Keratin Treatment from AED 350" is 10x more compelling than generic "Book now" |
| **Visual identity** — logo, brand colors, fonts | Ads must be visually on-brand. We use these exact assets in the final creative |
| **CTAs and conversion flow** | If the brand drives traffic to WhatsApp, the ad CTA should be "Message us". If it's a booking link, "Book now". This shapes the creative |
| **Social channels** | Tells us where the brand is already active and where ads should run |
| **Screenshot of their site** | Visual reference for the creative strategy — match the vibe |

**The user sees**: A beautiful "Brand Overview" card showing everything we found, organized into a clean, scannable layout. They can verify accuracy and correct anything we got wrong.

---

### Step 3: "Let us research your market"

This is the Intelligence Hub — 8 independent research modules that each answer a critical strategic question. Each module runs on-demand and stores snapshots that refresh every 14 days.

#### 3.1 Competitors
**Question it answers**: "Who are you competing against?"

**What we find**: 2-3 direct competitors with their websites, social presence, positioning, and price tier.

**Why it matters for creative**: You can't differentiate if you don't know what others are saying. The competitor list directly feeds the Ads Intelligence module, and their positioning reveals white space for the brand's messaging.

#### 3.2 Ads Intelligence
**Question it answers**: "What ads are working in your space right now?"

**What we do**: Pull real ads from competitors and the broader category. Score every ad on 8 quality signals (longevity, format, content, CTA, etc.) to identify proven winners. Then detect patterns across the top performers.

**What the user sees**:
- A gallery of real competitor and category ads, each with a quality score and tier (Proven Winner / Strong Performer / Rising / Notable)
- Pattern insights like "Video ads dominate your top performers" or "80% of winning ads include a clear CTA"
- Each ad shows exactly why it was picked and what makes it strong

**Why it matters for creative**: This is the swipe file. When we build creative strategy, we'll reference these patterns directly — "Your competitors' proven winners are long-running video ads on Facebook with strong CTAs. Your strategy should include video-first creative with clear booking CTAs."

#### 3.3 Reviews & Reputation
**Question it answers**: "What do people say about you online?"

**What we find**: Review platforms, ratings, strength themes (what people love), weakness themes (what they complain about), and real customer quotes.

**Why it matters for creative**: Customer language is the best ad copy. A review that says "They came to my house and did my wedding makeup perfectly" is more persuasive than any copywriter's headline. Strength themes become ad angles. Weakness themes tell us what NOT to promise.

#### 3.4 Customer Intel
**Question it answers**: "Who is your ideal customer and what drives them?"

**What we find**: Target persona, buying triggers, decision-making factors, pain points, and what motivates them.

**Why it matters for creative**: Ads that speak to a specific person outperform generic ads. "Busy Dubai moms who want salon-quality results at home" is a creative brief. "Women who like beauty" is not.

#### 3.5 Search Intent
**Question it answers**: "What are people searching for when they need what you sell?"

**What we do**: Generate seed keywords from the brand profile, run them through Google's autocomplete, filter for relevance, and bucket them by intent type (price-shopping, trust-seeking, urgency, comparison, general).

**Why it matters for creative**: 
- Price-intent queries ("keratin treatment cost Dubai") tell us to lead with pricing in some ads
- Trust-intent queries ("best salon reviews Dubai") tell us to lead with social proof
- Urgency queries ("same day makeup artist") tell us to lead with availability
- Each bucket maps to a different creative angle

#### 3.6 Seasonality
**Question it answers**: "When should you be advertising more or less?"

**What we find**: Key calendar moments, seasonal demand patterns, and buying triggers specific to the business's location and niche.

**Why it matters for creative**: A bridal makeup business should surge creative in wedding season. A fitness studio should push "New Year" creative in December. This data shapes the campaign calendar.

#### 3.7 Community
**Question it answers**: "What are real people saying in forums and communities?"

**What we find**: Real threads from Reddit, Quora, and niche forums. Themes, language patterns, and how people talk about this category.

**Why it matters for creative**: Forum language is raw and authentic. It reveals objections we need to overcome, questions we should answer in ads, and the exact words real people use (not marketing jargon).

#### 3.8 Social Trends
**Question it answers**: "What content is working on social media in your space?"

**Why it matters for creative**: Shows what formats, topics, and styles are currently resonating. Helps ensure our creative recommendations are timely, not stale.

---

## What We're Building Next (Steps 4-5)

### Step 4: Creative Strategy

**Goal**: Synthesize ALL of the research above into actionable creative directions.

This is the bridge between intelligence and execution. The creative strategy takes everything we've learned and produces:

**4.1 Creative Angles** — 3-5 distinct messaging themes, each backed by specific research findings:
- *Example*: "Social Proof" angle — backed by strong review themes + customer quotes from Reviews module
- *Example*: "Price Transparency" angle — backed by price-intent search queries + competitor pricing gaps
- *Example*: "Convenience" angle — backed by customer persona pain points + community forum language

**4.2 Platform Recommendations** — which platforms to prioritize and why:
- Based on: where competitors' winning ads run (Ads Intel patterns), where the brand already has presence (channels), where the target audience lives (Customer Intel)

**4.3 Format Recommendations** — video vs static vs carousel:
- Based on: what's winning in their category (Ads Intel patterns show "Video ads dominate top performers"), platform best practices, budget constraints

**4.4 Messaging Matrix** — specific copy directions for each angle x platform x funnel stage:
- Awareness: headline + hook
- Consideration: body copy + proof points
- Conversion: CTA + offer

**4.5 Visual Direction** — mood, style, and reference points:
- Based on: brand DNA (aesthetic, visual vibe), brand colors/fonts, screenshot of their site, winning ad visuals from competitors

**4.6 Campaign Calendar** — when to launch what:
- Based on: seasonality data, competitor timing patterns

---

### Step 5: Asset Generation

**Goal**: Generate the actual ad creatives — ready to upload to ad platforms.

**5.1 Static Ads**:
- Multiple formats (1:1, 4:5, 9:16, 16:9) for different placements
- On-brand visuals using their colors, fonts, logo
- Copy from the messaging matrix
- Each static tied to a specific angle + platform + funnel stage

**5.2 Video Ads**:
- Short-form (15s, 30s) for Reels/Stories/TikTok
- Hook + body + CTA structure
- Text overlays, transitions, brand elements
- Script generated from creative strategy

**5.3 Ad Variations**:
- A/B test versions for each creative (different headlines, different hooks, different CTAs)
- Based on the multiple angles from the strategy phase

---

## How It All Connects

```
RESEARCH (Built)                    STRATEGY (Next)              ASSETS (After)
                                    
Brand Overview ----+                
                   |                
Competitors -------+--- Creative    
                   |    Angles      --> Static Ads
Ads Intelligence --+    |           --> Video Ads  
                   |    Platform &  --> Ad Variations
Reviews -----------+    Format Recs 
                   |    |           
Customer Intel ----+    Messaging   
                   |    Matrix      
Search Intent -----+    |           
                   |    Visual      
Seasonality -------+    Direction   
                   |    |           
Community ---------+    Campaign    
                   |    Calendar    
Social Trends -----+                
```

Each research module feeds specific parts of the creative strategy:

| Research Module | Feeds Into |
|----------------|------------|
| Brand Overview | Visual direction, brand voice, service-specific copy |
| Competitors | Differentiation angles, positioning gaps |
| Ads Intelligence | Format recs, platform recs, what's proven to work |
| Reviews | Social proof angles, customer language for copy |
| Customer Intel | Persona targeting, pain point messaging |
| Search Intent | Keyword-based ad copy, intent-matched angles |
| Seasonality | Campaign timing, seasonal messaging |
| Community | Authentic language, objection handling |
| Social Trends | Trending formats, timely hooks |

---

## Summary

**What we have**: A comprehensive intelligence engine that deeply understands any brand and its competitive landscape. Every piece of data collected serves a specific purpose in the creative pipeline.

**What's next**: Transform that intelligence into creative strategy (angles, messaging, visual direction, calendar) and then into actual ad assets (statics, videos, variations).

**The value**: A business owner enters their website URL and gets back a complete ads package — researched, strategized, and produced — without needing a creative agency, media buyer, or strategist. The entire funnel from "I have a business" to "Here are your ads" is automated and data-driven.
