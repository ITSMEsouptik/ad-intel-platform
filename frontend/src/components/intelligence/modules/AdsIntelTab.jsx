import React, { useState, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, ExternalLink, Clock, X, Play, Target, Search, Globe, Info, Trophy, TrendingUp, Flame, Star, Video, Smartphone, Timer, Radio, MousePointerClick, FileText, GitBranch, Lightbulb } from 'lucide-react';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard } from '../ui/Cards';
import { AdCreativeInsightPanel } from '../ui/CreativeInsightPanel';

const isVideoUrl = (url) => url && (url.endsWith('.mp4') || url.endsWith('.webm') || url.endsWith('.mov'));
const isVideoAd = (ad) => ad.format === 'video' || ad.display_format === 'video' || isVideoUrl(ad.media_url);

const TIER_CONFIG = {
  proven_winner: { label: 'Proven Winner', icon: Trophy, color: 'text-amber-400', bg: 'bg-amber-500/20 border-amber-500/30', badgeBg: 'bg-amber-500/80', shortBg: 'bg-amber-500/15 text-amber-400' },
  strong_performer: { label: 'Strong Performer', icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/20 border-emerald-500/30', badgeBg: 'bg-emerald-500/70', shortBg: 'bg-emerald-500/15 text-emerald-400' },
  rising: { label: 'Rising', icon: Flame, color: 'text-blue-400', bg: 'bg-blue-500/20 border-blue-500/30', badgeBg: 'bg-blue-500/70', shortBg: 'bg-blue-500/15 text-blue-400' },
  notable: { label: 'Notable', icon: Star, color: 'text-white/40', bg: 'bg-white/5 border-white/10', badgeBg: 'bg-white/20', shortBg: 'bg-white/5 text-white/40' },
};

const SIGNAL_LABELS = {
  longevity: 'Longevity',
  liveness: 'Active',
  format: 'Format',
  cta: 'CTA',
  landing_page: 'Landing Page',
  preview: 'Preview',
  content: 'Content',
  recency: 'Recency',
};

const SIGNAL_MAX = { longevity: 35, liveness: 15, format: 10, cta: 5, landing_page: 5, preview: 5, content: 10, recency: 15 };

export const AdsIntelTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.adsIntel;
  const latest = data?.latest;

  // Get creative analysis data for enrichment
  const caData = modules.creativeAnalysis?.data;
  const caLatest = caData?.latest;
  const adAnalysesMap = useMemo(() => {
    const map = {};
    if (caLatest?.ad_analyses) {
      for (const a of caLatest.ad_analyses) {
        if (a.ad_id) map[a.ad_id] = a;
      }
    }
    return map;
  }, [caLatest]);

  const [lensFilter, setLensFilter] = useState('all');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [modal, setModal] = useState(null);

  // Memoize ad arrays to prevent recalculation on every render
  const { cwAds, catwAds, allAds, totalCount } = useMemo(() => {
    const cw = latest?.competitor_winners || {};
    const catw = latest?.category_winners || {};
    const _cwAds = cw.ads || [];
    const _catwAds = catw.ads || [];
    const normalizeAd = (a, lens) => ({
      ...a,
      _lens: lens,
      platform: a.platform || a.publisher_platform || 'Facebook',
      format: a.format || a.display_format,
      brand: a.brand || a.brand_name,
      days_running: a.days_running || a.running_days,
      score: a.score || 0,
      tier: a.tier || 'notable',
      score_signals: a.score_signals || {},
    });
    const _allAds = [..._cwAds.map(a => normalizeAd(a, 'competitor')), ..._catwAds.map(a => normalizeAd(a, 'category'))];
    return { cwAds: _cwAds, catwAds: _catwAds, allAds: _allAds, totalCount: _allAds.length };
  }, [latest]);

  const cw = latest?.competitor_winners || {};
  const catw = latest?.category_winners || {};

  const filteredAds = allAds
    .filter(a => lensFilter === 'all' || a._lens === lensFilter)
    .filter(a => platformFilter === 'all' || (a.platform || 'facebook').toLowerCase().includes(platformFilter));

  const platforms = [...new Set(allAds.map(a => (a.platform || 'Facebook').toLowerCase()))];

  const catQueries = catw?.stats?.queries_used || [];
  const compBrands = cw?.stats?.brands_queried || 0;
  const auditInfo = latest?.audit || {};
  const geo = latest?.inputs?.geo || {};

  return (
    <div data-testid="ads-intel-tab">
      <ModuleHeader title="Ads" moduleKey="adsIntel" status={status} refreshDueInDays={data?.refresh_due_in_days} onRun={() => runModule('adsIntel')} error={error}>
        {totalCount > 0 && <span className="text-white/20 text-xs font-mono">{totalCount} ads shortlisted</span>}
      </ModuleHeader>

      {status === STATUS.RUNNING && !latest && <ModuleRunning message="Fetching ad intelligence..." submessage="Scanning Foreplay ad library (30-60s)" moduleKey="adsIntel" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={Zap} title="Ad Intelligence not run" description="Discover winning ads from competitors and your category." onGenerate={() => runModule('adsIntel')} />
      )}

      {latest && totalCount === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <Zap className="w-8 h-8 text-white/10 mb-3" strokeWidth={1.5} />
          <p className="text-white/40 text-sm">No ads found</p>
        </div>
      )}

      {latest && totalCount > 0 && (
        <>
          {/* Pipeline summary */}
          <AntigravityCard className="p-4 mb-6" data-testid="ads-pipeline-summary">
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-[11px] font-mono text-white/30">
              {geo?.city && <span className="flex items-center gap-1.5"><Globe className="w-3 h-3 text-white/15" />Target: {geo.city}, {geo.country}</span>}
              <span className="flex items-center gap-1.5"><Search className="w-3 h-3 text-white/15" />{auditInfo.total_ads_seen || 0} ads scanned</span>
              <span className="flex items-center gap-1.5"><Target className="w-3 h-3 text-white/15" />{totalCount} shortlisted</span>
              {auditInfo.total_ads_seen > 0 && <span className="text-white/15">{Math.round(((auditInfo.total_ads_seen - totalCount) / auditInfo.total_ads_seen) * 100)}% filtered out</span>}
            </div>
          </AntigravityCard>

          {/* Top Performing Patterns */}
          <PatternsCard patterns={latest?.patterns} />

          {/* Filters with context */}
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <div className="flex gap-1.5">
              {[
                { key: 'all', label: 'All', count: allAds.length },
                { key: 'competitor', label: 'From Your Competitors', count: cwAds.length },
                { key: 'category', label: 'Industry Trends', count: catwAds.length },
              ].map(f => (
                <button key={f.key} onClick={() => setLensFilter(f.key)}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${lensFilter === f.key ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30 hover:text-white/50'}`}
                  data-testid={`ads-lens-${f.key}`}>
                  {f.label} ({f.count})
                </button>
              ))}
            </div>
            {platforms.length > 1 && (
              <div className="flex gap-1.5">
                <button onClick={() => setPlatformFilter('all')}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${platformFilter === 'all' ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30'}`}>
                  All Platforms
                </button>
                {platforms.map(p => (
                  <button key={p} onClick={() => setPlatformFilter(p)}
                    className={`px-3 py-1.5 text-xs rounded-lg border transition-colors capitalize ${platformFilter === p ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30'}`}>
                    {p}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Context line for active filter */}
          <div className="flex items-start gap-2 mb-6 pl-1">
            <Info className="w-3 h-3 text-white/10 mt-0.5 shrink-0" />
            <p className="text-[11px] text-white/20 leading-relaxed">
              {lensFilter === 'competitor' && cwAds.length > 0 && `Ads from ${compBrands} known competitor brand${compBrands !== 1 ? 's' : ''}, ranked by quality score. Higher-scored ads signal proven, well-crafted creatives.`}
              {lensFilter === 'competitor' && cwAds.length === 0 && 'No active ads found from your competitors. They may not be running paid campaigns right now.'}
              {lensFilter === 'category' && `Trending ads in your category${catQueries.length > 0 ? ` based on: ${catQueries.map(q => `"${q}"`).join(', ')}` : ''}. Scored by longevity, format, and engagement signals.`}
              {lensFilter === 'all' && `Competitor ads + category trends combined. Sorted by composite quality score.`}
            </p>
          </div>

          {/* Gallery */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3" data-testid="ads-gallery">
            {filteredAds.map((ad, i) => (
              <AdCard key={`${ad.ad_id || i}`} ad={ad} index={i} onClick={() => setModal(ad)} />
            ))}
          </motion.div>
        </>
      )}

      <AnimatePresence>{modal && <AdDetailModal ad={modal} onClose={() => setModal(null)} creativeAnalysis={adAnalysesMap[modal.ad_id]} />}</AnimatePresence>
    </div>
  );
};

const PATTERN_ICONS = {
  format: Video, platform: Smartphone, longevity: Timer,
  liveness: Radio, cta: MousePointerClick, content: FileText, source: GitBranch,
};

const PatternsCard = ({ patterns }) => {
  if (!patterns || patterns.length === 0) return null;
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
      className="mb-6" data-testid="ads-patterns-card">
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="w-3.5 h-3.5 text-amber-400/60" />
        <span className="text-xs font-medium text-white/50 uppercase tracking-wider">Top Performing Patterns</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {patterns.map((p, i) => {
          const Icon = PATTERN_ICONS[p.type] || Lightbulb;
          return (
            <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.05 }}
              className="group relative px-3.5 py-3 rounded-lg border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/[0.1] transition-all"
              data-testid={`ads-pattern-${i}`}>
              <div className="flex items-start gap-2.5">
                <div className="w-6 h-6 rounded-md bg-white/[0.05] flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-3 h-3 text-white/30" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-white/70 font-medium leading-snug">{p.text}</p>
                  <p className="text-[10px] text-white/25 leading-relaxed mt-0.5">{p.detail}</p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};

const AdCard = ({ ad, index, onClick }) => {
  const lensColors = { competitor: 'bg-rose-500/70 text-white', category: 'bg-blue-500/70 text-white' };
  const lensLabels = { competitor: 'competitor', category: 'trend' };
  const platform = (ad.platform || 'Facebook').toLowerCase();
  const platformShort = platform.includes('facebook') ? 'FB' : platform.includes('instagram') ? 'IG' : platform.includes('tiktok') ? 'TT' : platform.substring(0, 2).toUpperCase();
  const daysRunning = ad.days_running;
  const brandName = ad.brand;
  const isVideo = isVideoAd(ad);
  const videoRef = useRef(null);
  const [imgFailed, setImgFailed] = React.useState(false);
  const hasRealPreview = ad.has_preview !== false;
  const tierCfg = TIER_CONFIG[ad.tier] || TIER_CONFIG.notable;
  const TierIcon = tierCfg.icon;

  const handleMouseEnter = () => {
    if (isVideo && videoRef.current) {
      videoRef.current.play().catch(() => {});
    }
  };
  const handleMouseLeave = () => {
    if (isVideo && videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  const PlaceholderPreview = () => (
    <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-white/[0.04] to-white/[0.01] p-4 text-center">
      <span className="text-white/50 text-sm font-medium mb-1 line-clamp-2">{brandName || 'Ad'}</span>
      {ad.headline && <span className="text-white/20 text-[10px] line-clamp-2">{ad.headline}</span>}
      {ad.display_format === 'carousel' && <span className="text-white/15 text-[9px] mt-2 uppercase tracking-wider">Carousel Ad</span>}
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.5), duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
      className="group relative border border-white/[0.06] bg-[#0A0A0A] hover:border-white/[0.12] transition-all cursor-pointer overflow-hidden rounded-lg"
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      data-testid={`ad-card-${index}`}
    >
      <div className="aspect-square bg-black/40 relative overflow-hidden">
        {isVideo && ad.media_url ? (
          <>
            <video
              ref={videoRef}
              src={ad.media_url}
              poster={ad.thumbnail_url || ''}
              muted
              loop
              playsInline
              preload="none"
              className="w-full h-full object-cover"
              onError={() => setImgFailed(true)}
            />
            {imgFailed && <PlaceholderPreview />}
            {!imgFailed && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none group-hover:opacity-0 transition-opacity duration-300">
                <div className="w-10 h-10 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center">
                  <Play className="w-4 h-4 text-white fill-white ml-0.5" />
                </div>
              </div>
            )}
          </>
        ) : !imgFailed && hasRealPreview && (ad.thumbnail_url || ad.media_url) ? (
          <img src={ad.thumbnail_url || ad.media_url} alt="" className="w-full h-full object-cover" loading="lazy"
            onError={() => setImgFailed(true)} />
        ) : (
          <PlaceholderPreview />
        )}
        {/* Top-left badges */}
        <div className="absolute top-2 left-2 flex gap-1">
          <span className="px-1.5 py-0.5 text-[8px] font-bold uppercase rounded bg-white/20 text-white backdrop-blur-sm">{platformShort}</span>
          {isVideo && <span className="px-1.5 py-0.5 text-[8px] font-bold uppercase rounded bg-white/20 text-white backdrop-blur-sm">video</span>}
        </div>
        {/* Top-right: tier badge */}
        {ad.tier && ad.tier !== 'notable' && (
          <div className={`absolute top-2 right-2 flex items-center gap-1 px-1.5 py-0.5 rounded backdrop-blur-sm ${tierCfg.badgeBg}`} data-testid={`ad-tier-badge-${index}`}>
            <TierIcon className="w-2.5 h-2.5 text-white" />
            <span className="text-[8px] font-bold uppercase text-white">{ad.score}</span>
          </div>
        )}
        {/* Bottom badges */}
        <div className="absolute bottom-2 left-2 right-2 flex justify-between items-end">
          {daysRunning > 0 && (
            <span className="px-1.5 py-0.5 text-[8px] font-bold uppercase rounded bg-black/60 text-white/70 backdrop-blur-sm">{daysRunning}d</span>
          )}
          {ad._lens && (
            <span className={`px-1.5 py-0.5 text-[8px] font-bold uppercase rounded ${lensColors[ad._lens] || 'bg-white/20'}`}>
              {lensLabels[ad._lens] || ad._lens}
            </span>
          )}
        </div>
      </div>
      <div className="p-3">
        <div className="flex items-center justify-between gap-1">
          <p className="text-white/70 text-xs font-medium truncate flex-1">{brandName || ad.advertiser_name || 'Unknown'}</p>
          {ad.score > 0 && (
            <span className={`text-[10px] font-mono shrink-0 ${tierCfg.color}`}>{ad.score}</span>
          )}
        </div>
        <p className="text-white/30 text-[10px] truncate mt-0.5">{ad.headline || ''}</p>
        {daysRunning > 0 && (
          <p className="text-white/15 text-[10px] mt-1 font-mono flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" /> {daysRunning}d running
          </p>
        )}
      </div>
    </motion.div>
  );
};

const ScoreBar = ({ label, value, max }) => (
  <div className="flex items-center gap-2">
    <span className="text-[10px] text-white/30 w-20 shrink-0">{label}</span>
    <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
      <div className="h-full rounded-full bg-white/20 transition-all" style={{ width: `${Math.round((value / max) * 100)}%` }} />
    </div>
    <span className="text-[10px] text-white/20 font-mono w-8 text-right">{value}/{max}</span>
  </div>
);

const AdDetailModal = ({ ad, onClose, creativeAnalysis }) => {
  const isVideo = isVideoAd(ad);
  const tierCfg = TIER_CONFIG[ad.tier] || TIER_CONFIG.notable;
  const TierIcon = tierCfg.icon;
  const signals = ad.score_signals || {};

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose} data-testid="ad-modal">
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
        className="bg-[#111] border border-white/10 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto rounded-xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <span className="text-sm text-white font-medium">{ad.brand || ad.brand_name || 'Unknown Brand'}</span>
            {ad._lens && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded uppercase font-bold ${ad._lens === 'competitor' ? 'bg-rose-500/20 text-rose-400' : 'bg-blue-500/20 text-blue-400'}`}>
                {ad._lens === 'competitor' ? 'competitor' : 'trend'}
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white"><X className="w-4 h-4" /></button>
        </div>

        {/* Media: Video or Image */}
        {isVideo && ad.media_url ? (
          <div className="bg-black">
            <video
              src={ad.media_url}
              poster={ad.thumbnail_url || ''}
              controls
              playsInline
              preload="metadata"
              className="w-full max-h-80 object-contain"
              data-testid="ad-modal-video"
            />
          </div>
        ) : (ad.thumbnail_url || ad.media_url) && ad.has_preview !== false ? (
          <div className="bg-black">
            <img src={ad.thumbnail_url || ad.media_url} alt="" className="w-full object-contain max-h-80"
              onError={e => { e.target.parentElement.style.display = 'none'; }} />
          </div>
        ) : (
          <div className="bg-white/[0.02] py-8 flex flex-col items-center justify-center">
            <span className="text-white/20 text-xs uppercase tracking-wider">{ad.display_format || 'Ad'} Preview Unavailable</span>
          </div>
        )}

        <div className="p-4 space-y-3">
          {/* Tier + Score header */}
          {ad.score > 0 && (
            <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border ${tierCfg.bg}`} data-testid="ad-score-display">
              <TierIcon className={`w-5 h-5 ${tierCfg.color}`} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${tierCfg.color}`}>{tierCfg.label}</span>
                  <span className="text-white/20 text-xs font-mono">{ad.score}/100</span>
                </div>
              </div>
            </div>
          )}

          {/* Score breakdown */}
          {Object.keys(signals).length > 0 && (
            <div className="space-y-1.5 px-1" data-testid="ad-score-breakdown">
              {Object.entries(SIGNAL_LABELS).map(([key, label]) => {
                const val = signals[key] || 0;
                const max = SIGNAL_MAX[key] || 10;
                if (val === 0) return null;
                return <ScoreBar key={key} label={label} value={val} max={max} />;
              })}
            </div>
          )}

          {ad.headline && <p className="text-white/70 text-sm font-medium">{ad.headline}</p>}
          {ad.text && <p className="text-white/40 text-sm leading-relaxed">{ad.text}</p>}

          {ad.why_shortlisted && (
            <div className="flex items-start gap-2 px-3 py-2 bg-white/[0.03] rounded-lg border border-white/[0.04]" data-testid="ad-why-picked">
              <Target className="w-3.5 h-3.5 text-white/20 shrink-0 mt-0.5" />
              <div>
                <span className="text-[10px] text-white/20 font-mono uppercase block mb-0.5">Why this ad was picked</span>
                <p className="text-white/50 text-xs">{ad.why_shortlisted}</p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-3 text-xs text-white/30 font-mono pt-1">
            {ad.days_running > 0 && <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{ad.days_running}d running</span>}
            {ad.platform && <span className="capitalize">{ad.platform}</span>}
            {ad.format && <span>{ad.format}</span>}
            {ad.cta && <span className="text-white/20">{ad.cta.replace(/_/g, ' ').toLowerCase()}</span>}
            {ad.live && <span className="text-emerald-400/60">active now</span>}
          </div>

          <div className="flex flex-wrap gap-2 pt-1">
            {ad.landing_page_url && (
              <a href={ad.landing_page_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 text-xs text-white bg-white/[0.06] hover:bg-white/10 border border-white/[0.06] transition-colors rounded-lg">
                <ExternalLink className="w-3 h-3" />Landing Page
              </a>
            )}
            {ad.foreplay_url && (
              <a href={ad.foreplay_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 text-xs text-white bg-white/[0.06] hover:bg-white/10 border border-white/[0.06] transition-colors rounded-lg">
                <ExternalLink className="w-3 h-3" />Foreplay
              </a>
            )}
          </div>

          {/* Creative Analysis Enrichment */}
          <AdCreativeInsightPanel analysis={creativeAnalysis} />
        </div>
      </motion.div>
    </motion.div>
  );
};
