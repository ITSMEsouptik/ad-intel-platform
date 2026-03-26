import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, Globe, ExternalLink, Instagram, Youtube, Linkedin,
  X, Copy, Check, ChevronDown, ChevronRight
} from 'lucide-react';
import Logo from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

// ─── Motion presets ────────────────────────────────────────────
const ease = [0.23, 1, 0.32, 1];
const fadeUp = { initial: { opacity: 0, y: 24 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.5, ease } };
const stagger = { animate: { transition: { staggerChildren: 0.06 } } };
const item = { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease } } };

// ─── TikTok icon ───────────────────────────────────────────────
const TikTokIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className || "w-4 h-4"}>
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
);

// ─── Social icons (SVG for those not in lucide) ───────────────
const TwitterIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className || "w-4 h-4"}>
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </svg>
);
const FacebookIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className || "w-4 h-4"}>
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);
const PinterestIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className || "w-4 h-4"}>
    <path d="M12.017 0C5.396 0 .029 5.367.029 11.987c0 5.079 3.158 9.417 7.618 11.162-.105-.949-.199-2.403.041-3.439.219-.937 1.406-5.957 1.406-5.957s-.359-.72-.359-1.781c0-1.668.967-2.914 2.171-2.914 1.023 0 1.518.769 1.518 1.69 0 1.029-.655 2.568-.994 3.995-.283 1.194.599 2.169 1.777 2.169 2.133 0 3.772-2.249 3.772-5.495 0-2.873-2.064-4.882-5.012-4.882-3.414 0-5.418 2.561-5.418 5.207 0 1.031.397 2.138.893 2.738a.36.36 0 0 1 .083.345l-.333 1.36c-.053.22-.174.267-.402.161-1.499-.698-2.436-2.889-2.436-4.649 0-3.785 2.75-7.262 7.929-7.262 4.163 0 7.398 2.967 7.398 6.931 0 4.136-2.607 7.464-6.227 7.464-1.216 0-2.359-.631-2.75-1.378l-.748 2.853c-.271 1.043-1.002 2.35-1.492 3.146C9.57 23.812 10.763 24 12.017 24c6.624 0 11.99-5.367 11.99-11.988C24.007 5.367 18.641 0 12.017 0z"/>
  </svg>
);

const SOCIAL_ICONS = {
  instagram: Instagram, youtube: Youtube, linkedin: Linkedin,
  twitter: TwitterIcon, facebook: FacebookIcon, tiktok: TikTokIcon,
  pinterest: PinterestIcon
};

// ─── Data Quality Scorecard ────────────────────────────────────
const DataQualityBar = ({ step2 }) => {
  const checks = useMemo(() => {
    const s = step2 || {};
    return [
      { label: 'Logo', ok: !!s.identity?.logo?.primary_url },
      { label: 'Colors', ok: (s.identity?.colors?.length || 0) > 0 },
      { label: 'Fonts', ok: (s.identity?.fonts?.length || 0) > 0 },
      { label: 'Pricing', ok: (s.pricing?.count || 0) > 0 },
      { label: 'Social', ok: (s.channels?.social?.length || 0) > 0 },
      { label: 'Catalog', ok: (s.offer?.offer_catalog?.length || 0) > 0 },
    ];
  }, [step2]);

  const filled = checks.filter(c => c.ok).length;
  const pct = Math.round((filled / checks.length) * 100);

  return (
    <div data-testid="data-quality-scorecard" className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-[var(--novara-text-tertiary)] uppercase tracking-widest">Extraction Quality</span>
        <span className="text-sm font-mono text-[var(--novara-text-primary)]">{pct}%</span>
      </div>
      <div className="flex gap-1">
        {checks.map((c, i) => (
          <TooltipProvider key={i} delayDuration={100}>
            <Tooltip>
              <TooltipTrigger asChild>
                <motion.div
                  className={`h-1.5 flex-1 rounded-full ${c.ok ? 'bg-emerald-400' : 'bg-white/[0.06]'}`}
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: 0.3 + i * 0.08, duration: 0.4, ease }}
                  style={{ transformOrigin: 'left' }}
                />
              </TooltipTrigger>
              <TooltipContent side="bottom" className="bg-[var(--novara-surface-highlight)] border-white/10 text-xs">
                {c.label}: {c.ok ? 'Found' : 'Not detected'}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ))}
      </div>
      <div className="flex gap-3 flex-wrap">
        {checks.map((c, i) => (
          <span key={i} className={`text-[10px] font-mono tracking-wide ${c.ok ? 'text-emerald-400/70' : 'text-[var(--novara-text-tertiary)]'}`}>
            {c.ok ? '\u2713' : '\u2715'} {c.label}
          </span>
        ))}
      </div>
    </div>
  );
};

// ─── Bento Card wrapper (AntigravityCard-inspired) ─────────────
const BentoCard = ({ children, className = '', span = '', delay = 0, testId }) => (
  <motion.div
    variants={item}
    data-testid={testId}
    className={`
      relative overflow-hidden rounded-xl
      bg-[#0A0A0A]/80 backdrop-blur-md
      border border-white/[0.06]
      hover:border-white/[0.12] hover:shadow-lg hover:shadow-white/[0.02]
      transition-all duration-300
      ${span} ${className}
    `}
    whileHover={{ y: -2, transition: { duration: 0.2 } }}
  >
    {/* Subtle top-edge glow */}
    <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
    {children}
  </motion.div>
);

const SectionLabel = ({ children }) => (
  <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-[var(--novara-text-tertiary)]">{children}</span>
);

// ─── Color Swatch ──────────────────────────────────────────────
const ColorSwatch = ({ hex, role, isLarge }) => {
  const [copied, setCopied] = useState(false);
  const copy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hex);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="group flex flex-col items-center gap-2 cursor-pointer" onClick={copy}>
      <div
        className={`${isLarge ? 'w-16 h-16' : 'w-12 h-12'} rounded-lg border border-white/[0.06] group-hover:border-white/20 transition-colors duration-200 relative`}
        style={{ backgroundColor: hex }}
      >
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-black/40 rounded-lg">
          {copied ? <Check className="w-3 h-3 text-white" /> : <Copy className="w-3 h-3 text-white" />}
        </div>
      </div>
      <span className="font-mono text-[10px] text-[var(--novara-text-tertiary)] group-hover:text-[var(--novara-text-secondary)] transition-colors">
        {hex.toUpperCase()}
      </span>
      {role && role !== 'unknown' && (
        <span className="text-[9px] text-[var(--novara-text-tertiary)] capitalize -mt-1">{role}</span>
      )}
    </div>
  );
};

// ─── Grouped Catalog Section ───────────────────────────────────
const CatalogGroup = ({ group }) => {
  const [open, setOpen] = useState(false);
  const items = group.services || group.items || [];
  
  return (
    <div className="border border-white/[0.06] rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors duration-200 text-left group"
        onClick={() => setOpen(!open)}
        data-testid={`catalog-group-${group.category}`}
      >
        <div className="flex items-center gap-3">
          <ChevronDown className={`w-3.5 h-3.5 text-[var(--novara-text-tertiary)] transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
          <span className="text-[var(--novara-text-primary)] font-medium">{group.category || 'General'}</span>
          <span className="font-mono text-xs text-[var(--novara-text-tertiary)]">{group.count || items.length} items</span>
        </div>
        <div className="flex items-center gap-3">
          {group.price_range?.min != null && group.price_range?.max != null && (
            <span className="font-mono text-xs text-emerald-400/70">
              {group.price_range.min === group.price_range.max
                ? `${group.price_range.min}`
                : `${group.price_range.min} - ${group.price_range.max}`}
            </span>
          )}
        </div>
      </button>
      <AnimatePresence>
        {open && items.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-3 pt-1 space-y-0 border-t border-white/[0.04]">
              {items.map((svc, i) => (
                <div key={i} className="py-2.5 border-b border-white/[0.03] last:border-0 hover:bg-white/[0.01] -mx-1 px-1 rounded transition-colors" data-testid={`service-item-${i}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0 pr-4">
                      <span className="text-sm text-[var(--novara-text-secondary)] block">{svc.name}</span>
                      {svc.duration && (
                        <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)] mt-0.5 block">{svc.duration}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {svc.price_display && (
                        <span className="font-mono text-xs text-emerald-400/70">{svc.price_display}</span>
                      )}
                      {svc.booking_url && (
                        <a href={svc.booking_url} target="_blank" rel="noopener noreferrer" className="text-[var(--novara-text-tertiary)] hover:text-[var(--novara-text-secondary)] transition-colors" onClick={(e) => e.stopPropagation()}>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                  {svc.description && (
                    <p className="text-[11px] text-[var(--novara-text-tertiary)] mt-1 leading-relaxed">{svc.description}</p>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ─── Price Range Viz ───────────────────────────────────────────
const PriceRange = ({ pricing }) => {
  if (!pricing || !pricing.count) return null;
  const { min, avg, max, currency } = pricing;
  const sym = { USD: '$', EUR: '\u20ac', GBP: '\u00a3', INR: '\u20b9', AED: 'AED ' }[currency] || `${currency} `;
  const fmt = (v) => v != null ? `${sym}${v.toLocaleString()}` : '--';
  const pct = min != null && max != null && max > min ? ((avg - min) / (max - min)) * 100 : 50;

  return (
    <div className="space-y-4">
      {/* Range bar */}
      <div className="relative h-2 bg-white/[0.04] rounded-full overflow-hidden">
        <motion.div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-500/40 to-emerald-400/60 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: '100%' }}
          transition={{ delay: 0.5, duration: 0.8, ease }}
        />
        {avg != null && (
          <motion.div
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[var(--novara-surface)]"
            initial={{ left: '0%' }}
            animate={{ left: `${pct}%` }}
            transition={{ delay: 0.8, duration: 0.6, ease }}
          />
        )}
      </div>
      {/* Labels */}
      <div className="flex justify-between items-end">
        <div>
          <span className="block text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase">Min</span>
          <span className="font-mono text-lg text-[var(--novara-text-primary)]">{fmt(min)}</span>
        </div>
        {avg != null && (
          <div className="text-center">
            <span className="block text-[10px] font-mono text-emerald-400/70 uppercase">Avg</span>
            <span className="font-mono text-lg text-emerald-400">{fmt(avg)}</span>
          </div>
        )}
        <div className="text-right">
          <span className="block text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase">Max</span>
          <span className="font-mono text-lg text-[var(--novara-text-primary)]">{fmt(max)}</span>
        </div>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════
// Main PackView
// ═══════════════════════════════════════════════════════════════
export default function PackView() {
  const { briefId } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated, loginWithGoogle } = useAuth();

  const [pack, setPack] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(null);
  const [logoBg, setLogoBg] = useState('dark');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.get(`/website-context-packs/by-campaign/${briefId}`);
        setPack(response.data);
      } catch (err) {
        console.error('Failed to fetch pack:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [briefId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          <span className="font-mono text-xs text-[var(--novara-text-tertiary)] tracking-widest uppercase">Loading Business DNA</span>
        </motion.div>
      </div>
    );
  }

  const step2 = pack?.step2;
  if (!step2) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="font-heading text-2xl font-semibold text-[var(--novara-text-primary)]">Pack not found</h1>
          <p className="text-sm text-[var(--novara-text-tertiary)]">This brief may still be processing or doesn't exist.</p>
          <Button onClick={() => navigate('/')} className="bg-white text-black hover:bg-gray-200 rounded-lg">Go Home</Button>
        </div>
      </div>
    );
  }

  const { site, classification, brand_summary, brand_dna, identity, offer, pricing, conversion, channels, assets, contact } = step2;
  const logoUrl = identity?.logo?.primary_url || null;
  const imageAssets = assets?.image_assets || [];
  const groupedCatalog = offer?.grouped_catalog || [];
  const offerCatalog = offer?.offer_catalog || [];
  const socialChannels = channels?.social || [];

  const getSocialIcon = (platform) => SOCIAL_ICONS[platform] || Globe;

  return (
    <div className="min-h-screen bg-black text-[var(--novara-text-primary)]">
      {/* ─── Nav ─────────────────────────────────── */}
      <nav className="fixed top-0 w-full bg-black/80 backdrop-blur-xl border-b border-white/[0.06] z-50" data-testid="pack-nav">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <Logo size="default" />
          <div className="flex items-center gap-2">
            {isAuthenticated ? (
              <Button variant="ghost" onClick={() => navigate('/dashboard')} className="text-[var(--novara-text-secondary)] hover:text-white text-xs font-mono tracking-wider" data-testid="dashboard-link">
                Dashboard
              </Button>
            ) : (
              <Button variant="ghost" onClick={() => loginWithGoogle()} className="text-[var(--novara-text-secondary)] hover:text-white text-xs font-mono tracking-wider" data-testid="sign-in-link">
                Sign In
              </Button>
            )}
          </div>
        </div>
      </nav>

      {/* ─── Image Modal ─────────────────────────── */}
      <AnimatePresence>
        {selectedImage && (
          <motion.div
            className="fixed inset-0 bg-black/95 z-[100] flex items-center justify-center p-8 cursor-zoom-out"
            onClick={() => setSelectedImage(null)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            data-testid="image-modal"
          >
            <button className="absolute top-6 right-6 text-white/40 hover:text-white transition-colors" onClick={() => setSelectedImage(null)}>
              <X className="w-6 h-6" />
            </button>
            <motion.img
              src={selectedImage}
              alt="Asset preview"
              className="max-w-full max-h-full object-contain rounded-lg"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.25, ease }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Main ────────────────────────────────── */}
      <main className="pt-20 pb-24 px-6">
        <motion.div
          className="max-w-7xl mx-auto"
          initial="initial"
          animate="animate"
          variants={stagger}
        >
          {/* ─── Header Row ──────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
            {/* Brand Header */}
            <motion.div variants={item} className="lg:col-span-8 space-y-4">
              <div className="flex items-center gap-3">
                {classification?.industry && classification.industry !== 'unknown' && (
                  <span className="px-2.5 py-1 bg-white/[0.06] border border-white/[0.06] rounded-md text-[10px] font-mono uppercase tracking-widest text-[var(--novara-text-secondary)]">
                    {classification.industry}
                  </span>
                )}
                {classification?.niche && classification.niche !== 'unknown' && (
                  <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)]">{classification.niche}</span>
                )}
              </div>
              <h1 className="font-heading text-4xl sm:text-5xl font-semibold tracking-tight" data-testid="pack-title">
                {brand_summary?.name || site?.title || 'Brand Analysis'}
              </h1>
              {brand_summary?.tagline && brand_summary.tagline !== 'unknown' && (
                <p className="text-lg text-[var(--novara-text-secondary)] max-w-2xl leading-relaxed">{brand_summary.tagline}</p>
              )}
              {brand_summary?.one_liner && brand_summary.one_liner !== 'unknown' && (
                <p className="text-sm text-[var(--novara-text-tertiary)] max-w-2xl">{brand_summary.one_liner}</p>
              )}
            </motion.div>

            {/* Scorecard */}
            <motion.div variants={item} className="lg:col-span-4">
              <div className="relative overflow-hidden bg-[#0A0A0A]/80 backdrop-blur-md border border-white/[0.06] rounded-xl p-5">
                <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
                <DataQualityBar step2={step2} />
              </div>
            </motion.div>
          </div>

          {/* ─── Bento Grid ──────────────────────── */}
          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-4"
            variants={stagger}
          >
            {/* ── Brand DNA ─────────────────────── */}
            {(brand_dna?.values?.length > 0 || brand_dna?.tone_of_voice?.length > 0 || brand_summary?.bullets?.length > 0) && (
              <BentoCard span="lg:col-span-12" testId="brand-dna-card">
                <div className="p-6 space-y-5">
                  <SectionLabel>Brand Overview</SectionLabel>
                  {brand_summary?.bullets?.length > 0 && (
                    <div className="space-y-2">
                      {brand_summary.bullets
                        .filter(b => !(/\d[\d,]*\s*(AED|USD|EUR|GBP|INR|\$|£)|\b(price|pricing|cost|from\s+\w+\s+\d)/i.test(b)))
                        .map((b, i) => (
                        <div key={i} className="flex items-start gap-2.5 text-sm text-[var(--novara-text-secondary)]">
                          <div className="w-1 h-1 rounded-full bg-emerald-400 mt-2 flex-shrink-0" />
                          {b}
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-x-6 gap-y-4 pt-2">
                    {brand_dna?.values?.length > 0 && (
                      <div>
                        <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase tracking-widest block mb-2">Values</span>
                        <div className="flex flex-wrap gap-1.5">
                          {brand_dna.values.map((v, i) => (
                            <span key={i} className="px-2.5 py-1 text-xs bg-emerald-500/10 text-emerald-400/80 border border-emerald-500/15 rounded-md">{v}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {brand_dna?.tone_of_voice?.length > 0 && (
                      <div>
                        <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase tracking-widest block mb-2">Tone</span>
                        <div className="flex flex-wrap gap-1.5">
                          {brand_dna.tone_of_voice.map((t, i) => (
                            <span key={i} className="px-2.5 py-1 text-xs bg-blue-500/10 text-blue-400/80 border border-blue-500/15 rounded-md">{t}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {brand_dna?.aesthetic?.length > 0 && (
                      <div>
                        <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase tracking-widest block mb-2">Aesthetic</span>
                        <div className="flex flex-wrap gap-1.5">
                          {brand_dna.aesthetic.map((a, i) => (
                            <span key={i} className="px-2.5 py-1 text-xs bg-purple-500/10 text-purple-400/80 border border-purple-500/15 rounded-md">{a}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {brand_dna?.visual_vibe?.length > 0 && (
                      <div>
                        <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase tracking-widest block mb-2">Vibe</span>
                        <div className="flex flex-wrap gap-1.5">
                          {brand_dna.visual_vibe.map((v, i) => (
                            <span key={i} className="px-2.5 py-1 text-xs bg-amber-500/10 text-amber-400/80 border border-amber-500/15 rounded-md">{v}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </BentoCard>
            )}

            {/* ── Logo ──────────────────────────── */}
            {logoUrl && (
              <BentoCard span="lg:col-span-3" testId="logo-card">
                <div className="p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <SectionLabel>Logo</SectionLabel>
                    <div className="flex gap-1">
                      <button onClick={() => setLogoBg('dark')} className={`w-5 h-5 rounded bg-black border ${logoBg === 'dark' ? 'border-white/40' : 'border-white/10'}`} />
                      <button onClick={() => setLogoBg('light')} className={`w-5 h-5 rounded bg-white border ${logoBg === 'light' ? 'border-white/40' : 'border-white/10'}`} />
                    </div>
                  </div>
                  <div
                    className={`rounded-lg flex items-center justify-center aspect-[4/3] cursor-pointer ${logoBg === 'dark' ? 'bg-black' : 'bg-white'}`}
                    onClick={() => setSelectedImage(logoUrl)}
                  >
                    <img src={logoUrl} alt="Logo" className="max-h-16 max-w-[80%] object-contain" onError={(e) => e.target.style.display = 'none'} />
                  </div>
                </div>
              </BentoCard>
            )}

            {/* ── Colors ────────────────────────── */}
            {identity?.colors?.length > 0 && (
              <BentoCard span={logoUrl ? "lg:col-span-5" : "lg:col-span-6"} testId="colors-card">
                <div className="p-5 space-y-4">
                  <SectionLabel>Color Palette</SectionLabel>
                  <div className="flex flex-wrap gap-4">
                    {identity.colors.map((c, i) => (
                      <ColorSwatch key={i} hex={c.hex} role={c.role} isLarge={identity.colors.length <= 5} />
                    ))}
                  </div>
                </div>
              </BentoCard>
            )}

            {/* ── Fonts ─────────────────────────── */}
            {identity?.fonts?.length > 0 && (
              <BentoCard span={logoUrl ? "lg:col-span-4" : "lg:col-span-6"} testId="fonts-card">
                <div className="p-5 space-y-4">
                  <SectionLabel>Typography</SectionLabel>
                  <div className="space-y-3">
                    {identity.fonts.map((font, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
                        <span className="text-[var(--novara-text-primary)] text-base">{font.family || font.name}</span>
                        <span className="font-mono text-[10px] text-[var(--novara-text-tertiary)] uppercase">{font.role}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </BentoCard>
            )}

            {/* ── Brand Assets (moved up for visibility) ── */}
            {imageAssets.length > 0 && (
              <BentoCard span="lg:col-span-12" testId="assets-card">
                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <SectionLabel>Brand Assets</SectionLabel>
                    <span className="font-mono text-[10px] text-[var(--novara-text-tertiary)]">{imageAssets.length} images</span>
                  </div>
                  <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
                    {imageAssets.slice(0, 18).map((asset, i) => (
                      <motion.div
                        key={i}
                        className="aspect-square bg-white/[0.02] rounded-lg overflow-hidden cursor-pointer border border-white/[0.04] hover:border-white/[0.12] transition-colors duration-200"
                        onClick={() => setSelectedImage(asset.url)}
                        whileHover={{ scale: 1.03 }}
                        transition={{ duration: 0.2 }}
                      >
                        <img
                          src={asset.url}
                          alt={asset.alt || 'Brand asset'}
                          className="w-full h-full object-cover"
                          loading="lazy"
                          onError={(e) => { e.target.parentElement.style.display = 'none'; }}
                        />
                      </motion.div>
                    ))}
                  </div>
                </div>
              </BentoCard>
            )}

            {/* ── Pricing ───────────────────────── */}
            {pricing?.count > 0 && (
              <BentoCard span="lg:col-span-5" testId="pricing-card">
                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <SectionLabel>Pricing</SectionLabel>
                    <span className="font-mono text-[10px] text-[var(--novara-text-tertiary)]">{pricing.count} data points</span>
                  </div>
                  <PriceRange pricing={pricing} />
                </div>
              </BentoCard>
            )}

            {/* ── Value Prop ────────────────────── */}
            {offer?.value_prop && offer.value_prop !== 'unknown' && (
              <BentoCard span={pricing?.count > 0 ? "lg:col-span-7" : "lg:col-span-12"} testId="value-prop-card">
                <div className="p-5 space-y-4">
                  <SectionLabel>Value Proposition</SectionLabel>
                  <p className="text-sm text-[var(--novara-text-primary)] leading-relaxed font-body">{offer.value_prop}</p>
                  {offer?.key_benefits?.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {offer.key_benefits.slice(0, 4).map((b, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-[var(--novara-text-secondary)]">
                          <Check className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />
                          <span>{b}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </BentoCard>
            )}

            {/* ── Offer Catalog ─────────────────── */}
            {(groupedCatalog.length > 0 || offerCatalog.length > 0) && (
              <BentoCard span="lg:col-span-7" testId="catalog-card">
                <div className="p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <SectionLabel>Services & Products</SectionLabel>
                    <span className="font-mono text-[10px] text-[var(--novara-text-tertiary)]">
                      {groupedCatalog.length > 0
                        ? `${groupedCatalog.reduce((a, g) => a + (g.count || 0), 0)} items`
                        : `${offerCatalog.length} items`}
                    </span>
                  </div>
                  {groupedCatalog.length > 0 ? (
                    <div className="space-y-2">
                      {groupedCatalog.map((g, i) => <CatalogGroup key={i} group={g} />)}
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {offerCatalog.slice(0, 10).map((svc, i) => (
                        <div key={i} className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0 text-sm">
                          <span className="text-[var(--novara-text-secondary)]">{svc.name}</span>
                          {svc.price_hint && <span className="font-mono text-xs text-emerald-400/70">{svc.price_hint}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </BentoCard>
            )}

            {/* ── Social + Contact ──────────────── */}
            <BentoCard span="lg:col-span-5" testId="channels-card">
              <div className="p-5 space-y-5">
                {/* Social */}
                {socialChannels.length > 0 && (
                  <div className="space-y-3">
                    <SectionLabel>Social Channels</SectionLabel>
                    <div className="space-y-1.5">
                      {socialChannels.map((ch, i) => {
                        const Icon = getSocialIcon(ch.platform);
                        return (
                          <a
                            key={i}
                            href={ch.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.03] transition-colors duration-200 group"
                            data-testid={`social-${ch.platform}`}
                          >
                            <div className="w-8 h-8 rounded-md bg-white/[0.04] flex items-center justify-center group-hover:bg-white/[0.08] transition-colors">
                              <Icon className="w-4 h-4 text-[var(--novara-text-secondary)]" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <span className="text-sm capitalize text-[var(--novara-text-primary)]">{ch.platform}</span>
                              {ch.handle && (
                                <span className="block text-[11px] font-mono text-[var(--novara-text-tertiary)] truncate">@{ch.handle}</span>
                              )}
                            </div>
                            <ExternalLink className="w-3.5 h-3.5 text-[var(--novara-text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity" />
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* CTAs */}
                {conversion?.ctas?.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-white/[0.04]">
                    <SectionLabel>Detected CTAs</SectionLabel>
                    <div className="flex flex-wrap gap-1.5">
                      {conversion.ctas.slice(0, 8).map((cta, i) => {
                        const isPrimary = cta === conversion.primary_action;
                        return (
                          <span
                            key={i}
                            className={`px-2.5 py-1 text-[11px] rounded-md border transition-colors ${
                              isPrimary
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 font-medium'
                                : 'bg-white/[0.03] border-white/[0.06] text-[var(--novara-text-tertiary)]'
                            }`}
                            data-testid={`cta-${i}${isPrimary ? '-primary' : ''}`}
                          >
                            {cta}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </BentoCard>

          </motion.div>
        </motion.div>
      </main>

      {/* Sticky bottom action bar */}
      <motion.div
        className="fixed bottom-0 inset-x-0 z-40"
        initial={{ y: 80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 1.2, duration: 0.5, ease }}
      >
        <div className="bg-black/80 backdrop-blur-xl border-t border-white/[0.06]">
          <div className="max-w-7xl mx-auto px-6 md:px-12 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
              <span className="text-sm text-[var(--novara-text-secondary)] truncate hidden sm:block">
                Business DNA ready. Explore deeper insights
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <Button
                variant="ghost"
                onClick={() => navigate('/wizard')}
                className="text-[var(--novara-text-tertiary)] hover:text-white rounded-lg text-xs px-3 py-1.5"
                data-testid="create-another-btn"
              >
                New Analysis
              </Button>
              <Button
                data-testid="intelligence-hub-btn"
                onClick={() => navigate(`/intel/${briefId}`)}
                className="bg-white text-black hover:bg-gray-100 rounded-lg font-medium px-4 py-2 text-sm"
              >
                Intelligence Hub
                <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
