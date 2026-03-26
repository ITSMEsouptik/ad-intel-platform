# Ad Intel Platform

An AI-powered ad intelligence platform that turns a brand's website into a structured research foundation — before any creative work begins.

The core idea: **research first, create later**. Instead of jumping straight into ad copy and creatives, the platform crawls a brand's website, extracts its DNA, then runs parallel intelligence pipelines across market, search, competitor, and seasonal data. The output is a rich, structured brief that informs ad strategy at scale.

---

## What It Does

A user submits a brand URL and campaign goal. The platform then:

1. **Crawls the website** — visits up to 10 pages, takes a Playwright screenshot, extracts text, colors, fonts, pricing, CTAs, and social links
2. **Extracts Business DNA** — runs the crawl output through Gemini 2.0 Flash to produce a structured brand profile (industry, tone, visual identity, offer catalog, pricing, channels)
3. **Runs the Intelligence Hub** — four independent research pipelines fire in parallel:
   - **Market Intel** — Perplexity sonar-pro synthesizes the competitive landscape and customer psychology
   - **Search Demand** — Google Suggest + Gemini builds a keyword map bucketed by intent (price, trust, urgency, comparison)
   - **Seasonality** — Perplexity identifies peak demand windows, purchase triggers, and cultural/local buying patterns
   **Competitors** — Perplexity finds 3–5 validated direct competitors with pricing tier, overlap score, social handles, and positioning

All results are stored in MongoDB and available in real time via a polling architecture — each module streams its status as it completes.

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────────────┐
│   Step 1        │     │   Step 2        │     │   Intelligence Hub       │
│   Campaign      │────▶│   Business DNA  │────▶│                          │
│   Brief         │     │   Extraction    │     │  ├─ Market Intel         │
└─────────────────┘     └─────────────────┘     │  ├─ Search Demand        │
                                                │  ├─ Seasonality          │
                                                │  └─ Competitors          │
                                                └──────────────────────────┘
```

**Backend:** FastAPI (Python 3.11) · MongoDB (Motor async driver) · Playwright · httpx

**Frontend:** React 19 · Tailwind CSS · shadcn/ui · polling-based real-time updates

**LLMs:** Perplexity AI (sonar, sonar-pro) · Google Gemini 2.0 Flash

**Infra:** Google Cloud Run · Artifact Registry · Firebase Hosting (staging) · GCS (production) · GitHub Actions CI/CD

---

## Key Engineering Details

**Crawler (`backend/crawler.py`)**
- Async multi-page crawl with httpx, respects robots.txt
- Falls back to Jina Reader for JavaScript-heavy SPAs that block headless browsers
- Playwright screenshot with retry + timeout handling
- Color extraction from CSS, inline styles, and image assets
- Logo detection heuristic (size, position, alt text scoring)

**Orchestration (`backend/server.py`)**
- Step 2 runs as a background task; frontend polls `/status` until completion
- Each research module is independently runnable and stores its own snapshot — re-runs don't overwrite history
- Full debug log capture per orchestration run, accessible via `/admin/debug/:briefId`

**Intelligence Hub pipelines (`backend/research/`)**
- Each module lives in its own directory with `run.py`, `prompts.py`, `postprocess.py`
- Search Demand builds up to 28 seed queries from Step 1 + Step 2 context, fetches Google Suggest results, scores relevance, then runs an LLM curation pass for deduplication and typo correction
- Competitor module detects if the brand is a platform/marketplace vs. service provider, then adjusts exclusion logic accordingly (e.g., won't list Fresha as a competitor to a salon)
- URL validation pass on all competitor links before returning results; retries with an exclusion list if fewer than 3 valid competitors found

**Frontend (`frontend/src/`)**
- Auth via Google OAuth with httpOnly session cookies
- Campaign brief wizard with anonymous session support — briefs created before login get linked to the user on auth
- Intelligence Hub cards each manage their own loading/error/success states independently
- Error boundary wraps the hub to prevent one failed module from crashing the whole page

---

## Cost Per Campaign

| Module | Provider | Est. Cost |
|---|---|---|
| Business DNA (Step 2) | Gemini 2.0 Flash | ~$0.001 |
| Market Intel | Perplexity sonar-pro | ~$0.010 |
| Search Demand | Google Suggest (free) + Gemini | ~$0.001 |
| Seasonality | Perplexity sonar | ~$0.006 |
| Competitors | Perplexity sonar (1–3 calls) | ~$0.006–0.018 |
| **Total** | | **~$0.02–0.03** |

---

## Running Locally

**Prerequisites:** Python 3.11, Node.js 20, MongoDB running on `localhost:27017`

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Create backend/.env
cp .env.example .env
# Fill in: MONGO_URL, DB_NAME, PERPLEXITY_API_KEY, GOOGLE_AI_STUDIO_KEY

uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend**
```bash
cd frontend
yarn install

# Create frontend/.env.local
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env.local
echo "REACT_APP_AUTH_URL=<your-oauth-provider-url>" >> .env.local

yarn start
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/campaign-briefs` | Create a campaign brief |
| `POST` | `/api/orchestrations/:id/start` | Start Step 2 extraction |
| `GET` | `/api/orchestrations/:id/status` | Poll extraction progress |
| `GET` | `/api/website-context-packs/by-campaign/:id` | Fetch Business DNA result |
| `POST` | `/api/research/:id/search-intent/run` | Run Search Demand module |
| `GET` | `/api/research/:id/search-intent/latest` | Get latest Search Demand result |
| `POST` | `/api/research/:id/seasonality/run` | Run Seasonality module |
| `GET` | `/api/research/:id/seasonality/latest` | Get latest Seasonality result |
| `POST` | `/api/research/:id/competitors/run` | Run Competitors module |
| `GET` | `/api/research/:id/competitors/latest` | Get latest Competitors result |
| `GET` | `/api/research/:id/ads-intel/latest` | Get latest Market Intel result |

---

## Project Structure

```
ad-intel-platform/
├── backend/
│   ├── server.py                  # FastAPI app, all routes
│   ├── crawler.py                 # Multi-page async web crawler
│   ├── site_summarizer.py         # Gemini-based brand DNA extraction
│   ├── research/
│   │   ├── ads_intel/             # Market Intel module
│   │   ├── search_intent/         # Search Demand module
│   │   ├── seasonality/           # Seasonality module
│   │   ├── competitors/           # Competitors module
│   │   ├── reviews/               # Reviews module
│   │   ├── community/             # Community/forum module
│   │   ├── social_trends/         # Social Trends module
│   │   ├── press_media/           # Press & Media module
│   │   └── creative_analysis/     # Ad creative analysis module
│   ├── tests/                     # Unit + integration tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── intelligence/      # Intelligence Hub UI components
│       │   └── ui/                # shadcn/ui primitives
│       ├── context/
│       │   └── AuthContext.jsx    # Google OAuth + session management
│       ├── lib/
│       │   └── api.js             # Typed API client
│       └── pages/                 # Route-level page components
├── .github/workflows/             # CI/CD — build on push, deploy on dispatch
├── Dockerfile                     # Cloud Run container
└── firebase.json                  # Firebase Hosting config (staging)
```

---

## Deployment

CI runs on every push to `main` (syntax check + build verification). Deploys are manual via `workflow_dispatch` to prevent accidental production pushes.

- **Staging** → Firebase Hosting (automatic HTTPS + SPA routing)
- **Production** → GCS bucket behind a load balancer + Cloud Run backend
- Secrets managed via Google Cloud Secret Manager (API keys, DB connection string)
- Docker image built and pushed to Artifact Registry on each deploy
