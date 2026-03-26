# Novara Intelligence Hub — Redesign Blueprint

> **Visual Theme:** Google Antigravity × Linear Dark Mode
> **Identity:** The Creative Strategy Weapon
> **No gamification.** Dopamine through craft.

---

## Design Principles

1. **Precision over Decoration** — Every pixel serves data clarity
2. **Depth over Flatness** — Subtle layering, blurs, floating weightlessness
3. **Motion as Feedback** — Fluid, physics-based interactions
4. **Engineered Feel** — Distinct borders, clear hierarchy, monospace data

---

## Typography

| Role | Font | Usage |
|------|------|-------|
| Headings | Space Grotesk | Section headers only (h1, h2) |
| Body/UI | Manrope | All UI elements, buttons, reading text |
| Data | JetBrains Mono | Metrics, IDs, technical labels, timestamps |

**Rule:** Never pure white (#FFFFFF) for body text — use 80% or 70% opacity.

---

## Color System

### Backgrounds (Layered Depth)
- `#030303` — Base (app background)
- `#0A0A0A` — Layer 1 (main content area)
- `#141414` — Layer 2 (floating cards)
- `rgba(20,20,20,0.6)` — Floating panels (with backdrop-blur)

### Borders
- `rgba(255,255,255,0.06)` — Subtle (default)
- `rgba(255,255,255,0.15)` — Active/hover
- `rgba(255,255,255,0.4)` — Highlight/focus

### Text
- `#EDEDED` — Primary
- `#A1A1A1` — Secondary
- `#525252` — Muted

### Accents
- `#FFFFFF` — Brand/primary actions
- `#3B82F6` — Action blue
- `#10B981` — Success/fresh
- `#F59E0B` — Warning/stale
- `#E11D48` — Error

---

## Layout: Sidebar + Content

Replace 9 cramped horizontal tabs with a **sticky left sidebar**.

```
┌──────────────────────────────────────────────────┐
│  NOVARA                           Export │ Run All │
├─────────┬────────────────────────────────────────┤
│         │                                        │
│ Overview│    Main Content Area                   │
│ ─────── │    (Module detail view)                │
│ Audience│                                        │
│ Search  │    ┌─────────┐ ┌─────────┐            │
│ Season  │    │ Card 1  │ │ Card 2  │            │
│ Compete │    │         │ │         │            │
│ Reviews │    └─────────┘ └─────────┘            │
│ Communi │                                        │
│ Press   │    ┌─────────────────────┐            │
│ Social  │    │ Card 3 (wide)      │            │
│ Ads     │    │                     │            │
│         │    └─────────────────────┘            │
└─────────┴────────────────────────────────────────┘
```

---

## Component Architecture

```
src/components/intelligence/
├── IntelLayout.jsx              # Sidebar + content wrapper
├── IntelSidebar.jsx             # Left nav with module list + status dots
├── IntelligenceContext.js       # Shared state (data, loading, run controls)
├── ui/
│   ├── AntigravityCard.jsx      # Floating glassmorphism card
│   ├── StatusIndicator.jsx      # Fresh/Stale/Running badges
│   └── MetricDisplay.jsx        # Animated number display
└── modules/
    ├── OverviewTab.jsx          # Bento grid synthesis of all modules
    ├── CustomerIntelTab.jsx
    ├── SearchDemandTab.jsx
    ├── SeasonalityTab.jsx
    ├── CompetitorsTab.jsx
    ├── ReviewsTab.jsx
    ├── CommunityTab.jsx
    ├── PressMediaTab.jsx
    ├── SocialTrendsTab.jsx
    └── AdsTab.jsx
```

---

## Key Card Component: "AntigravityCard"

```
className="relative overflow-hidden rounded-xl
           border border-white/5
           bg-[#0A0A0A]/80 backdrop-blur-md
           shadow-2xl
           transition-all duration-300
           hover:border-white/10
           group"
```

Visual enhancements:
- Subtle top-border glow on hover (pseudo-element)
- Noise texture overlay at 2% opacity
- Staggered entrance animation (framer-motion)

---

## Motion Presets (Framer Motion)

```js
// Fade In (for cards, sections)
{ initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.4, ease: [0.23, 1, 0.32, 1] } }

// Stagger Container (for lists, grids)
{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } }

// Hover Lift (for interactive cards)
{ whileHover: { y: -2, scale: 1.005 }, transition: { duration: 0.2 } }
```

---

## Module-Specific Notes

| Module | Key Improvement |
|--------|----------------|
| **Overview** | NEW. Bento grid synthesizing all 9 modules. Default landing view. |
| **Customer Intel** | Collapsible persona cards. Hide citation markers [1][5]. |
| **Search Demand** | Visual bar charts for intent buckets. |
| **Seasonality** | Better timeline/heatmap visualization. |
| **Competitors** | Split view: list vs detail. Comparison bars. |
| **Reviews** | Actionable empty state ("Consider building presence on..."). |
| **Community** | Actionable empty state with specific forum suggestions. |
| **Press & Media** | Narrative cards with sentiment color coding. |
| **Social Trends** | Masonry gallery with zoom modal. |
| **Ads** | Masonry gallery with winning creative callouts. |

---

## New Features

1. **Export** — PDF report (html2canvas + jspdf), CSV keywords download
2. **Run Comparison** — Delta highlights between pipeline runs
3. **Real-time Progress** — Skeleton → data transition with progress indicator
4. **Overview Tab** — Single-view synthesis of all intelligence

---

## Refactor Steps (Implementation Order)

1. Create `/components/intelligence/` directory structure
2. Create `IntelligenceContext.js` — extract all state management
3. Create `IntelLayout.jsx` — sidebar + content area wrapper
4. Create `IntelSidebar.jsx` — left navigation with status indicators
5. Extract each module into its own component file
6. Build `OverviewTab.jsx` — the synthesis view
7. Replace monolithic `IntelligenceHub.jsx` with composed layout
8. Add framer-motion animations and transitions
9. Add Export and Comparison features
