import React from 'react';
import { motion } from 'framer-motion';
import {
  Users, Search, Calendar, Building2, MessageSquareQuote,
  UsersRound, Newspaper, TrendingUp, Zap, ArrowRight, Play, Eye, Clock,
  CheckCircle2, Circle
} from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { useIntel, STATUS } from '../IntelligenceContext';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';

const MODULE_META = [
  { key: 'customerIntel', label: 'Audience', icon: Users, dataKey: (m) => m.customerIntel?.data?.latest?.segments?.length || m.customerIntel?.data?.latest?.icp_segments?.length || 0, dataLabel: 'segments' },
  { key: 'searchIntent', label: 'Search Demand', icon: Search, dataKey: (m) => m.searchIntent?.data?.latest?.top_10_queries?.length || 0, dataLabel: 'queries' },
  { key: 'seasonality', label: 'Seasonality', icon: Calendar, dataKey: (m) => m.seasonality?.data?.latest?.key_moments?.length || 0, dataLabel: 'moments' },
  { key: 'competitors', label: 'Competitors', icon: Building2, dataKey: (m) => m.competitors?.data?.latest?.competitors?.length || 0, dataLabel: 'found' },
  { key: 'reviews', label: 'Reviews', icon: MessageSquareQuote, dataKey: (m) => m.reviews?.data?.latest?.platform_presence?.length || 0, dataLabel: 'platforms' },
  { key: 'community', label: 'Community', icon: UsersRound, dataKey: (m) => m.community?.data?.latest?.threads?.length || 0, dataLabel: 'threads' },
  { key: 'pressMedia', label: 'Press & Media', icon: Newspaper, dataKey: (m) => m.pressMedia?.data?.latest?.articles?.length || 0, dataLabel: 'articles' },
  { key: 'socialTrends', label: 'Social Trends', icon: TrendingUp, dataKey: (m) => (m.socialTrends?.data?.latest?.shortlist?.tiktok?.length || 0) + (m.socialTrends?.data?.latest?.shortlist?.instagram?.length || 0), dataLabel: 'posts' },
  { key: 'adsIntel', label: 'Ads', icon: Zap, dataKey: (m) => (m.adsIntel?.data?.latest?.competitor_winners?.ads?.length || 0) + (m.adsIntel?.data?.latest?.category_winners?.ads?.length || 0), dataLabel: 'ads' },
];

const statusLabels = {
  [STATUS.FRESH]: { text: 'Ready', class: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15' },
  [STATUS.STALE]: { text: 'Stale', class: 'text-amber-400 bg-amber-500/10 border-amber-500/15' },
  [STATUS.RUNNING]: { text: 'Running', class: 'text-blue-400 bg-blue-500/10 border-blue-500/15' },
  [STATUS.FAILED]: { text: 'Failed', class: 'text-rose-400 bg-rose-500/10 border-rose-500/15' },
  [STATUS.NOT_RUN]: { text: 'Not run', class: 'text-white/20 bg-white/[0.03] border-white/[0.06]' },
};

const MONTH_LABELS = ['J','F','M','A','M','J','J','A','S','O','N','D'];
const MONTH_MAP = {
  jan:0,january:0,feb:1,february:1,mar:2,march:2,apr:3,april:3,
  may:4,jun:5,june:5,jul:6,july:6,aug:7,august:7,sep:8,sept:8,september:8,
  oct:9,october:9,nov:10,november:10,dec:11,december:11
};

const parseActiveMonths = (windowStr) => {
  const s = (windowStr || '').toLowerCase();
  const active = new Set();
  const rangeMatch = s.match(/([a-z]+)\s*[-\u2013to]+\s*([a-z]+)/);
  if (rangeMatch) {
    const start = MONTH_MAP[rangeMatch[1]];
    const end = MONTH_MAP[rangeMatch[2]];
    if (start !== undefined && end !== undefined) {
      if (start <= end) { for (let m = start; m <= end; m++) active.add(m); }
      else { for (let m = start; m < 12; m++) active.add(m); for (let m = 0; m <= end; m++) active.add(m); }
    }
  }
  if (active.size === 0) {
    Object.entries(MONTH_MAP).forEach(([name, idx]) => { if (s.includes(name)) active.add(idx); });
  }
  return active;
};

export const OverviewTab = () => {
  const { modules, setActiveModule } = useIntel();

  const customerData = modules.customerIntel.data?.latest;
  const searchData = modules.searchIntent.data?.latest;
  const seasonData = modules.seasonality.data?.latest;
  const compData = modules.competitors.data?.latest;
  const socialData = modules.socialTrends.data?.latest;
  const adsData = modules.adsIntel.data?.latest;
  const pressData = modules.pressMedia.data?.latest;

  const segments = customerData?.segments || customerData?.icp_segments || [];
  const topQueries = searchData?.top_10_queries?.slice(0, 5) || [];
  const keyMoments = seasonData?.key_moments || [];
  const competitors = compData?.competitors || [];
  const ttShortlist = socialData?.shortlist?.tiktok || [];
  const igShortlist = socialData?.shortlist?.instagram || [];
  const ttItems = ttShortlist.length;
  const igItems = igShortlist.length;
  const cwAds = adsData?.competitor_winners?.ads || [];
  const catAds = adsData?.category_winners?.ads || [];

  // Top 3 social items by trend score
  const topSocial = [...ttShortlist, ...igShortlist]
    .sort((a, b) => (b.score?.trend_score || 0) - (a.score?.trend_score || 0))
    .slice(0, 4);

  // Top 4 ads (2 competitor + 2 category)
  const topAds = [...cwAds.slice(0, 2).map(a => ({ ...a, _lens: 'competitor' })), ...catAds.slice(0, 2).map(a => ({ ...a, _lens: 'category' }))];

  // Intelligence completeness
  const readyCount = MODULE_META.filter(m => modules[m.key]?.status === STATUS.FRESH || modules[m.key]?.status === STATUS.STALE).length;
  const completeness = Math.round((readyCount / MODULE_META.length) * 100);

  return (
    <div data-testid="overview-tab">
      {/* Intelligence Completeness */}
      <section className="mb-8">
        <div className="flex items-center gap-6 mb-6">
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12">
              <svg viewBox="0 0 36 36" className="w-12 h-12 -rotate-90">
                <circle cx="18" cy="18" r="15" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="3" />
                <motion.circle
                  cx="18" cy="18" r="15" fill="none"
                  stroke={completeness === 100 ? '#10b981' : completeness >= 50 ? '#f59e0b' : 'rgba(255,255,255,0.15)'}
                  strokeWidth="3" strokeLinecap="round"
                  strokeDasharray={`${completeness * 0.942} 100`}
                  initial={{ strokeDasharray: '0 100' }}
                  animate={{ strokeDasharray: `${completeness * 0.942} 100` }}
                  transition={{ duration: 1.2, ease: [0.23, 1, 0.32, 1] }}
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-[11px] font-mono text-white/60">{completeness}%</span>
            </div>
            <div>
              <p className="text-white/60 text-sm font-medium">Intelligence Coverage</p>
              <p className="text-white/25 text-xs font-mono">{readyCount}/{MODULE_META.length} modules active</p>
            </div>
          </div>
        </div>
      </section>

      {/* Module health grid */}
      <section className="mb-8">
        <SectionLabel>Module Status</SectionLabel>
        <StaggerContainer className="grid grid-cols-3 md:grid-cols-5 gap-2">
          {MODULE_META.map(({ key, label, icon: Icon, dataKey, dataLabel }) => {
            const status = modules[key]?.status;
            const sl = statusLabels[status] || statusLabels[STATUS.NOT_RUN];
            const dataCount = dataKey ? dataKey(modules) : 0;
            const isReady = status === STATUS.FRESH || status === STATUS.STALE;
            return (
              <StaggerItem key={key}>
                <button
                  onClick={() => setActiveModule(key)}
                  className="w-full p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:border-white/[0.1] transition-all text-left group"
                  data-testid={`overview-module-${key}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <Icon className="w-4 h-4 text-white/20 group-hover:text-white/40 transition-colors" strokeWidth={1.5} />
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full border font-mono ${sl.class}`}>{sl.text}</span>
                  </div>
                  <p className="text-[11px] text-white/50 font-medium">{label}</p>
                  {isReady && dataCount > 0 && (
                    <p className="text-[9px] text-white/20 font-mono mt-1">{dataCount} {dataLabel}</p>
                  )}
                </button>
              </StaggerItem>
            );
          })}
        </StaggerContainer>
      </section>

      {/* Strategic Summary */}
      {(segments.length > 0 || topQueries.length > 0 || competitors.length > 0) && (
        <section className="mb-8">
          <SectionLabel>Strategic Summary</SectionLabel>
          <AntigravityCard className="p-6">
            <div className="space-y-3.5 text-sm text-white/60">
              {segments.length > 0 && (
                <InsightRow icon={Users} label="Audience">
                  {segments.length} segments identified: {segments.map(s => s.segment_name || s.name).join(', ')}
                </InsightRow>
              )}
              {competitors.length > 0 && (
                <InsightRow icon={Building2} label="Compete">
                  {competitors.length} direct competitors: {competitors.map(c => c.name).join(', ')}
                  {compData?.market_overview?.competitive_density && ` \u00B7 ${compData.market_overview.competitive_density} density`}
                </InsightRow>
              )}
              {topQueries.length > 0 && (
                <InsightRow icon={Search} label="Search">
                  Top queries: {topQueries.map(q => q.query || q).join(', ')}
                </InsightRow>
              )}
              {keyMoments.length > 0 && (
                <InsightRow icon={Calendar} label="Timing">
                  {keyMoments.length} buying moments: {keyMoments.slice(0, 3).map(m => m.moment || m.name).join(', ')}
                </InsightRow>
              )}
              {(ttItems > 0 || igItems > 0) && (
                <InsightRow icon={TrendingUp} label="Social">
                  {ttItems + igItems} trending posts ({ttItems} TikTok, {igItems} Instagram)
                </InsightRow>
              )}
              {(cwAds.length > 0 || catAds.length > 0) && (
                <InsightRow icon={Zap} label="Ads">
                  {cwAds.length + catAds.length} winning ads ({cwAds.length} competitor, {catAds.length} category)
                </InsightRow>
              )}
              {pressData?.articles?.length > 0 && (
                <InsightRow icon={Newspaper} label="Press">
                  {pressData.articles.length} articles from {pressData.media_sources?.length || 0} sources
                </InsightRow>
              )}
            </div>
          </AntigravityCard>
        </section>
      )}

      {/* Bento Grid — Visual Quick Access */}
      <section className="mb-8">
        <SectionLabel>Quick Access</SectionLabel>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* Seasonality Timeline */}
          {keyMoments.length > 0 && (
            <SeasonalityPreview moments={keyMoments} onClick={() => setActiveModule('seasonality')} />
          )}

          {/* Top Search Queries */}
          {topQueries.length > 0 && (
            <QuickCard title="Top Search Queries" icon={Search} onClick={() => setActiveModule('searchIntent')}>
              <div className="space-y-1.5">
                {topQueries.map((q, i) => (
                  <div key={i} className="flex items-center gap-3 group/row">
                    <span className="text-white/10 font-mono text-[10px] w-4 text-right">{i + 1}</span>
                    <div className="flex-1 h-[1px] bg-white/[0.03]" />
                    <span className="text-white/50 text-sm">{q.query || q}</span>
                  </div>
                ))}
              </div>
            </QuickCard>
          )}

          {/* Creative Moodboard — Social Trends with Thumbnails */}
          {topSocial.length > 0 && (
            <SocialPreview items={topSocial} totalCount={ttItems + igItems} onClick={() => setActiveModule('socialTrends')} />
          )}

          {/* Ad Swipe File — Ads with Thumbnails */}
          {topAds.length > 0 && (
            <AdsPreview ads={topAds} totalCount={cwAds.length + catAds.length} onClick={() => setActiveModule('adsIntel')} />
          )}

          {/* Competitor Preview */}
          {competitors.length > 0 && (
            <QuickCard title="Competitive Landscape" icon={Building2} onClick={() => setActiveModule('competitors')}>
              <div className="space-y-3">
                {competitors.map((c, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-md bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                        <span className="text-[9px] font-mono text-white/30">{c.name?.charAt(0)}</span>
                      </div>
                      <span className="text-white/55 text-sm">{c.name}</span>
                    </div>
                    {(c.overlap_score || c.overlap_level) && (
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full border font-mono ${
                        (c.overlap_score || c.overlap_level) === 'high' ? 'text-rose-400 bg-rose-500/10 border-rose-500/15' :
                        (c.overlap_score || c.overlap_level) === 'medium' ? 'text-amber-400 bg-amber-500/10 border-amber-500/15' :
                        'text-white/20 bg-white/[0.03] border-white/[0.06]'
                      }`}>{c.overlap_score || c.overlap_level}</span>
                    )}
                  </div>
                ))}
              </div>
            </QuickCard>
          )}

          {/* Press Preview */}
          {pressData?.narratives?.length > 0 && (
            <QuickCard title="Press Coverage" icon={Newspaper} onClick={() => setActiveModule('pressMedia')}>
              <div className="space-y-2">
                {pressData.coverage_summary?.slice(0, 2).map((point, i) => (
                  <p key={i} className="text-white/40 text-xs leading-relaxed"><CleanText>{point}</CleanText></p>
                ))}
                {pressData.articles?.length > 0 && (
                  <div className="pt-2 border-t border-white/[0.04] flex items-center gap-2">
                    <span className="text-[10px] font-mono text-white/20">{pressData.articles.length} article{pressData.articles.length > 1 ? 's' : ''}</span>
                    <span className="text-[10px] text-white/10">from {pressData.media_sources?.length || 0} sources</span>
                  </div>
                )}
              </div>
            </QuickCard>
          )}
        </div>
      </section>
    </div>
  );
};

/* ====== Sub-components ====== */

const InsightRow = ({ icon: Icon, label, children }) => (
  <div className="flex items-start gap-3">
    <div className="flex items-center gap-2 shrink-0 mt-0.5">
      <Icon className="w-3.5 h-3.5 text-white/20" strokeWidth={1.5} />
      <span className="text-[10px] font-mono text-white/20 uppercase w-14">{label}</span>
    </div>
    <p className="text-white/50 text-sm leading-relaxed">{children}</p>
  </div>
);

const QuickCard = ({ title, icon: Icon, onClick, children }) => (
  <AntigravityCard hover className="p-5" onClick={onClick} data-testid={`overview-quick-${title?.toLowerCase().replace(/\s+/g, '-')}`}>
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-white/20" strokeWidth={1.5} />
        <span className="text-[11px] font-mono text-white/25 uppercase tracking-[0.15em]">{title}</span>
      </div>
      <ArrowRight className="w-3.5 h-3.5 text-white/10 group-hover:text-white/20 transition-colors" />
    </div>
    {children}
  </AntigravityCard>
);

/* Seasonality with sparkline chart */
const SeasonalityPreview = ({ moments, onClick }) => {
  const monthActivity = new Array(12).fill(0);
  moments.forEach(m => {
    const active = parseActiveMonths(m.window || m.time_window || '');
    active.forEach(idx => { monthActivity[idx] += (m.demand === 'high' ? 2 : 1); });
  });

  const sparkData = MONTH_LABELS.map((label, idx) => ({ m: label, v: monthActivity[idx] }));

  return (
    <AntigravityCard hover className="p-5" onClick={onClick} data-testid="overview-quick-seasonality">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-white/20" strokeWidth={1.5} />
          <span className="text-[11px] font-mono text-white/25 uppercase tracking-[0.15em]">Buying Timeline</span>
        </div>
        <ArrowRight className="w-3.5 h-3.5 text-white/10" />
      </div>

      {/* Mini sparkline */}
      <div className="mb-3">
        <ResponsiveContainer width="100%" height={50}>
          <AreaChart data={sparkData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
            <defs>
              <linearGradient id="sparkGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="v" stroke="#10b981" strokeWidth={1.5} fill="url(#sparkGradient)" dot={false} animationDuration={800} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Top 3 moments */}
      <div className="space-y-2">
        {moments.slice(0, 3).map((m, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className="text-white/45 text-xs truncate">{m.moment || m.name}</span>
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ml-2 shrink-0 ${
              m.demand === 'high' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15' : 'text-amber-400 bg-amber-500/10 border-amber-500/15'
            }`}>{m.demand}</span>
          </div>
        ))}
      </div>
    </AntigravityCard>
  );
};

/* Social Trends with thumbnail previews */
const SocialPreview = ({ items, totalCount, onClick }) => (
  <AntigravityCard hover className="p-5" onClick={onClick} data-testid="overview-quick-social-trends">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-white/20" strokeWidth={1.5} />
        <span className="text-[11px] font-mono text-white/25 uppercase tracking-[0.15em]">Trending Content</span>
      </div>
      <span className="text-[10px] text-white/15 font-mono">{totalCount} posts</span>
    </div>

    {/* Thumbnail grid */}
    <div className="grid grid-cols-4 gap-1.5 mb-3">
      {items.map((item, i) => {
        const videoId = item.post_url?.match(/\/video\/(\d+)/)?.[1];
        const thumbSrc = videoId
          ? `${process.env.REACT_APP_BACKEND_URL}/api/media/thumb/${videoId}`
          : item.thumb_url || item.media_url;
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.08, duration: 0.3 }}
            className="aspect-[9/14] rounded-md overflow-hidden bg-white/[0.03] border border-white/[0.04] relative group/thumb"
          >
            {thumbSrc ? (
              <img src={thumbSrc} alt="" className="w-full h-full object-cover" loading="lazy"
                onError={e => { e.target.style.display = 'none'; }} />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <TrendingUp className="w-3 h-3 text-white/10" />
              </div>
            )}
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover/thumb:opacity-100 transition-opacity flex items-center justify-center">
              <Play className="w-3 h-3 text-white/80" />
            </div>
            {/* Score bar at bottom */}
            {item.score?.trend_score > 0 && (
              <div className="absolute bottom-0 inset-x-0 h-0.5">
                <div className="h-full bg-emerald-500/70" style={{ width: `${(item.score.trend_score * 100)}%` }} />
              </div>
            )}
          </motion.div>
        );
      })}
    </div>

    <div className="flex items-center justify-between text-[10px] text-white/15 font-mono">
      <span>Top by trend score</span>
      <ArrowRight className="w-3 h-3" />
    </div>
  </AntigravityCard>
);

/* Ads with thumbnail previews */
const AdsPreview = ({ ads, totalCount, onClick }) => (
  <AntigravityCard hover className="p-5" onClick={onClick} data-testid="overview-quick-winning-ads">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-white/20" strokeWidth={1.5} />
        <span className="text-[11px] font-mono text-white/25 uppercase tracking-[0.15em]">Winning Ads</span>
      </div>
      <span className="text-[10px] text-white/15 font-mono">{totalCount} ads</span>
    </div>

    {/* Ad thumbnail strip */}
    <div className="grid grid-cols-4 gap-1.5 mb-3">
      {ads.map((ad, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.08, duration: 0.3 }}
          className="aspect-square rounded-md overflow-hidden bg-white/[0.03] border border-white/[0.04] relative"
        >
          {(ad.thumbnail_url || ad.image_url) ? (
            <img src={ad.thumbnail_url || ad.image_url} alt="" className="w-full h-full object-cover" loading="lazy"
              onError={e => { e.target.style.display = 'none'; }} />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Zap className="w-3 h-3 text-white/10" />
            </div>
          )}
          {ad.days_running && (
            <div className="absolute bottom-0 inset-x-0 bg-black/60 px-1 py-0.5 text-center">
              <span className="text-[7px] font-mono text-white/60">{ad.days_running}d</span>
            </div>
          )}
        </motion.div>
      ))}
    </div>

    <div className="flex items-center gap-2 text-[10px] font-mono text-white/15">
      {ads.some(a => a._lens === 'competitor') && <span>competitor</span>}
      {ads.some(a => a._lens === 'competitor') && ads.some(a => a._lens === 'category') && <span>+</span>}
      {ads.some(a => a._lens === 'category') && <span>category</span>}
      <ArrowRight className="w-3 h-3 ml-auto" />
    </div>
  </AntigravityCard>
);
