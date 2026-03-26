import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp, Play, Eye, Heart, MessageCircle, Share2,
  Bookmark, Music, ExternalLink, Users, X, Loader2
} from 'lucide-react';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { SectionLabel } from '../ui/Cards';
import { TikTokCreativeInsightPanel } from '../ui/CreativeInsightPanel';
import api from '@/lib/api';

export const SocialTrendsTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.socialTrends;
  const latest = data?.latest;

  // Get creative analysis data for TikTok enrichment
  const caData = modules.creativeAnalysis?.data;
  const caLatest = caData?.latest;
  const ttAnalysesMap = useMemo(() => {
    const map = {};
    if (caLatest?.tiktok_analyses) {
      for (const t of caLatest.tiktok_analyses) {
        if (t.post_url) map[t.post_url] = t;
      }
    }
    return map;
  }, [caLatest]);

  const [lens, setLens] = useState('shortlist');
  const [platform, setPlatform] = useState('all');
  const [queryType, setQueryType] = useState('all');
  const [contentLabel, setContentLabel] = useState('all');
  const [sortBy, setSortBy] = useState('trend_score');
  const [modal, setModal] = useState(null);

  if (!latest && status !== STATUS.RUNNING && status !== STATUS.NOT_RUN) return null;

  const igShortlist = latest?.shortlist?.instagram || [];
  const ttShortlist = latest?.shortlist?.tiktok || [];
  const allShortlist = [...igShortlist, ...ttShortlist];
  const totalCount = allShortlist.length;

  const getFilteredItems = () => {
    let items;
    if (lens === 'shortlist') {
      items = platform === 'all' ? allShortlist : platform === 'instagram' ? igShortlist : ttShortlist;
    } else {
      const lensData = latest?.lenses?.[lens] || {};
      const ig = lensData.instagram?.items || [];
      const tt = lensData.tiktok?.items || [];
      items = platform === 'instagram' ? ig : platform === 'tiktok' ? tt : [...ig, ...tt];
    }
    if (queryType !== 'all' && lens === 'shortlist') items = items.filter(i => i.query_type === queryType);
    if (contentLabel !== 'all') items = items.filter(i => i.content_label === contentLabel);

    return [...items].sort((a, b) => {
      const as = a.score || {}, bs = b.score || {}, am = a.metrics || {}, bm = b.metrics || {};
      switch (sortBy) {
        case 'save_rate': return (bs.save_rate || 0) - (as.save_rate || 0);
        case 'overperformance': return (bs.overperformance_ratio || 0) - (as.overperformance_ratio || 0);
        case 'views': return (bm.views || 0) - (am.views || 0);
        case 'recency': return (bs.recency_score || 0) - (as.recency_score || 0);
        case 'saves': return (bm.saves || 0) - (am.saves || 0);
        default: return (bs.trend_score || 0) - (as.trend_score || 0);
      }
    });
  };

  const displayItems = latest ? getFilteredItems() : [];

  return (
    <div data-testid="social-trends-tab">
      <ModuleHeader title="Social Trends" moduleKey="socialTrends" status={status} refreshDueInDays={data?.refresh_due_in_days} onRun={() => runModule('socialTrends')} error={error}>
        {totalCount > 0 && <span className="text-white/20 text-xs font-mono">{totalCount} items curated</span>}
      </ModuleHeader>

      {status === STATUS.RUNNING && !latest && <ModuleRunning message="Scanning social platforms..." submessage="Fetching TikTok + Instagram trends (30-60s)" moduleKey="socialTrends" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={TrendingUp} title="Social Trends not scanned" onGenerate={() => runModule('socialTrends')} />
      )}

      {latest && totalCount === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <TrendingUp className="w-8 h-8 text-white/10 mb-3" strokeWidth={1.5} />
          <p className="text-white/40 text-sm">No social trend data found</p>
          <p className="text-white/20 text-xs mt-1 max-w-md text-center">
            No Instagram or TikTok content was found for this brand's category.
          </p>
        </div>
      )}

      {latest && totalCount > 0 && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <div className="flex rounded-lg overflow-hidden border border-white/[0.06]">
              {[{ key: 'shortlist', label: 'Curated' }, { key: 'category_trends', label: 'Category' }, { key: 'brand_competitors', label: 'Brand' }].map(l => (
                <button key={l.key} onClick={() => setLens(l.key)}
                  className={`px-3 py-1.5 text-xs transition-colors ${lens === l.key ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/50'}`}
                  data-testid={`social-lens-${l.key}`}>{l.label}</button>
              ))}
            </div>

            <div className="flex gap-1.5">
              {[{ key: 'all', label: 'All', count: allShortlist.length }, { key: 'tiktok', label: 'TikTok', count: ttShortlist.length }, { key: 'instagram', label: 'Instagram', count: igShortlist.length }].map(p => (
                <button key={p.key} onClick={() => setPlatform(p.key)}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${platform === p.key ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30 hover:text-white/50'}`}
                  data-testid={`social-platform-${p.key}`}>{p.label} ({p.count})</button>
              ))}
            </div>

            {lens === 'shortlist' && (
              <div className="flex gap-1.5 ml-auto">
                {[{ key: 'all', label: 'All' }, { key: 'viral', label: 'Viral' }, { key: 'breakout', label: 'Breakout' }, { key: 'most_saved', label: 'Saved' }, { key: 'most_discussed', label: 'Discussed' }].map(qt => (
                  <button key={qt.key} onClick={() => setQueryType(qt.key)}
                    className={`px-2 py-1 text-[10px] rounded-md border transition-colors ${queryType === qt.key ? 'bg-white/10 border-white/20 text-white' : 'text-white/20 border-white/[0.04] hover:border-white/10'}`}
                    data-testid={`social-qtype-${qt.key}`}>{qt.label}</button>
                ))}
              </div>
            )}
          </div>

          {/* Sort + content label */}
          <div className="flex items-center gap-3 mb-6">
            <span className="text-[10px] text-white/15 uppercase tracking-wider font-mono">Sort</span>
            <select value={sortBy} onChange={e => setSortBy(e.target.value)}
              className="bg-white/[0.04] border border-white/[0.06] text-xs text-white/50 px-2 py-1 rounded-md focus:outline-none focus:border-white/15 appearance-none cursor-pointer"
              data-testid="social-sort-select">
              <option value="trend_score">Trend Score</option>
              <option value="save_rate">Save Rate</option>
              <option value="overperformance">Overperformance</option>
              <option value="saves">Most Saved</option>
              <option value="views">Most Viewed</option>
              <option value="recency">Most Recent</option>
            </select>
            <div className="w-px h-4 bg-white/[0.06]" />
            <span className="text-[10px] text-white/15 uppercase tracking-wider font-mono">Source</span>
            <div className="flex gap-1.5">
              {[{ key: 'all', label: 'All' }, { key: 'official', label: 'Official' }, { key: 'mention', label: 'Mention' }, { key: 'category', label: 'Category' }].map(cl => (
                <button key={cl.key} onClick={() => setContentLabel(cl.key)}
                  className={`px-2 py-1 text-[10px] rounded-md border transition-colors ${contentLabel === cl.key ? 'bg-white/10 border-white/20 text-white' : 'text-white/20 border-white/[0.04] hover:border-white/10'}`}
                  data-testid={`social-clabel-${cl.key}`}>{cl.label}</button>
              ))}
            </div>
          </div>

          {/* Gallery */}
          {displayItems.length > 0 ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3" data-testid="social-gallery">
              {displayItems.map((item, i) => (
                <SocialCard key={`${item.post_url}-${i}`} item={item} index={i} onClick={() => setModal(item)} />
              ))}
            </motion.div>
          ) : (
            <p className="text-white/20 text-sm text-center py-12">No items match the current filters.</p>
          )}
        </>
      )}

      {/* Modal */}
      <AnimatePresence>{modal && <SocialDetailModal item={modal} onClose={() => setModal(null)} creativeAnalysis={ttAnalysesMap[modal.post_url]} />}</AnimatePresence>
    </div>
  );
};

const SocialCard = ({ item, index, onClick }) => {
  const videoIdMatch = item.post_url?.match(/\/video\/(\d+)/);
  const videoId = videoIdMatch ? videoIdMatch[1] : null;
  const cachedThumb = videoId ? `${process.env.REACT_APP_BACKEND_URL}/api/media/thumb/${videoId}` : null;
  const hasThumbnail = cachedThumb || item.thumb_url || item.media_url;
  const isVideo = item.media_type === 'video' || item.media_type === 'reel' || item.platform === 'tiktok';
  const score = item.score || {};
  const metrics = item.metrics || {};

  const qtColors = {
    breakout: 'bg-amber-500/80 text-black', most_saved: 'bg-emerald-500/80 text-black',
    most_discussed: 'bg-blue-500/80 text-white', viral: 'bg-white/80 text-black',
  };
  const clColors = { official: 'bg-cyan-500/70 text-black', competitor: 'bg-rose-500/70 text-white' };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.5), duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
      className="group relative border border-white/[0.06] bg-[#0A0A0A] hover:border-white/[0.12] transition-all cursor-pointer overflow-hidden rounded-lg"
      onClick={onClick}
      data-testid={`social-card-${index}`}
    >
      <div className="aspect-[9/16] bg-black/40 relative overflow-hidden">
        {hasThumbnail ? (
          <img src={cachedThumb || item.thumb_url || item.media_url} alt=""
            className="w-full h-full object-cover" loading="lazy"
            onError={e => { if (cachedThumb && e.target.src === cachedThumb && item.thumb_url) e.target.src = item.thumb_url; else e.target.style.display = 'none'; }} />
        ) : (
          <div className="w-full h-full flex items-center justify-center"><TrendingUp className="w-6 h-6 text-white/10" /></div>
        )}
        {/* Badges */}
        <div className="absolute top-2 left-2 flex gap-1">
          <span className={`px-1.5 py-0.5 text-[8px] font-bold uppercase rounded ${item.platform === 'tiktok' ? 'bg-black/60 text-white' : 'bg-gradient-to-r from-purple-600 to-pink-500 text-white'}`}>
            {item.platform === 'tiktok' ? 'TT' : 'IG'}
          </span>
          {item.query_type && item.query_type !== 'viral' && (
            <span className={`px-1.5 py-0.5 text-[8px] font-bold uppercase rounded ${qtColors[item.query_type] || 'bg-white/20 text-white'}`}>
              {item.query_type === 'most_saved' ? 'SAVED' : item.query_type === 'most_discussed' ? 'DISCUSSED' : item.query_type.toUpperCase()}
            </span>
          )}
        </div>
        {isVideo && <Play className="absolute top-2 right-2 w-3.5 h-3.5 text-white/50" />}
        {/* Content label */}
        {item.content_label && item.content_label !== 'category' && (
          <span className={`absolute bottom-2 right-2 px-1.5 py-0.5 text-[8px] font-bold uppercase rounded ${clColors[item.content_label] || 'bg-white/20 text-white'}`}>
            {item.content_label}
          </span>
        )}
        {/* Hover stats overlay */}
        <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col justify-end p-3">
          <div className="space-y-1 text-[10px] font-mono text-white/80">
            {metrics.views != null && <div className="flex items-center gap-1"><Eye className="w-3 h-3" />{(metrics.views || 0).toLocaleString()}</div>}
            {metrics.likes != null && <div className="flex items-center gap-1"><Heart className="w-3 h-3" />{(metrics.likes || 0).toLocaleString()}</div>}
            {score.trend_score > 0 && <div className="text-emerald-400">Score: {(score.trend_score * 100).toFixed(0)}</div>}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const SocialDetailModal = ({ item, onClose, creativeAnalysis }) => {
  const [videoState, setVideoState] = useState('idle');
  const [videoBlobUrl, setVideoBlobUrl] = useState(null);
  const videoRef = useRef(null);
  const videoMatch = item.post_url?.match(/\/video\/(\d+)/);
  const videoId = videoMatch ? videoMatch[1] : null;
  const cachedThumb = videoId ? `${process.env.REACT_APP_BACKEND_URL}/api/media/thumb/${videoId}` : null;
  const thumbSrc = cachedThumb || item.thumb_url || item.media_url;
  const isVideo = item.media_type === 'video' || item.media_type === 'reel' || item.platform === 'tiktok';
  const hasMediaUrl = item.media_url && (Array.isArray(item.media_url) ? item.media_url.length > 0 : true);
  const m = item.metrics || {};
  const s = item.score || {};

  useEffect(() => { return () => { if (videoBlobUrl) URL.revokeObjectURL(videoBlobUrl); }; }, [videoBlobUrl]);

  const handlePlay = async () => {
    if (!videoId) return;
    setVideoState('loading');
    const mediaUrl = Array.isArray(item.media_url) ? item.media_url[0] : item.media_url;
    try {
      const cacheResp = await api.post(`/media/cache-video/${videoId}`, { video_url: mediaUrl || '' });
      if (cacheResp.data.status !== 'cached' && cacheResp.data.status !== 'already_cached') { setVideoState('error'); return; }
      const resp = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/media/video/${videoId}`);
      if (!resp.ok) { setVideoState('error'); return; }
      const blob = await resp.blob();
      setVideoBlobUrl(URL.createObjectURL(blob));
      setVideoState('playing');
    } catch { setVideoState('error'); }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose} data-testid="social-modal">
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="bg-[#111] border border-white/10 max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto rounded-xl" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <span className={`px-1.5 py-0.5 text-[9px] font-bold uppercase rounded ${item.platform === 'tiktok' ? 'bg-white/10 text-white' : 'bg-gradient-to-r from-purple-600 to-pink-500 text-white'}`}>
              {item.platform === 'tiktok' ? 'TikTok' : 'Instagram'}
            </span>
            <span className="text-sm text-white/70">@{item.author_handle}</span>
          </div>
          <button onClick={onClose} className="text-white/30 hover:text-white" data-testid="social-modal-close"><X className="w-4 h-4" /></button>
        </div>

        {/* Media */}
        <div className="aspect-[9/16] max-h-80 bg-black overflow-hidden relative">
          {videoState === 'playing' && videoBlobUrl ? (
            <video ref={videoRef} src={videoBlobUrl} controls playsInline className="w-full h-full object-contain" data-testid="social-modal-video" onLoadedData={e => { e.target.play().catch(() => {}); }} />
          ) : (
            <>
              {thumbSrc && <img src={thumbSrc} alt="" className="w-full h-full object-contain"
                onError={e => { if (cachedThumb && e.target.src === cachedThumb && item.thumb_url) e.target.src = item.thumb_url; else e.target.style.display = 'none'; }} />}
              {isVideo && videoId && videoState !== 'error' && hasMediaUrl && (
                <button onClick={handlePlay} disabled={videoState === 'loading'}
                  className="absolute inset-0 flex items-center justify-center bg-black/30 hover:bg-black/40 transition-colors" data-testid="social-modal-play-btn">
                  {videoState === 'loading' ? <Loader2 className="w-10 h-10 text-white animate-spin" /> :
                    <div className="w-14 h-14 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center hover:bg-white/30 transition-colors"><Play className="w-7 h-7 text-white ml-1" /></div>}
                </button>
              )}
              {videoState === 'error' && <div className="absolute bottom-2 left-2 right-2 bg-rose-500/20 border border-rose-500/30 px-3 py-1.5 text-[10px] text-rose-400 text-center rounded">Video unavailable</div>}
            </>
          )}
        </div>

        {/* Content */}
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-4 text-sm text-white/50">
            {m.views != null && <span className="flex items-center gap-1.5"><Eye className="w-3.5 h-3.5 text-white/25" />{m.views?.toLocaleString()}</span>}
            <span className="flex items-center gap-1.5"><Heart className="w-3.5 h-3.5 text-white/25" />{m.likes?.toLocaleString()}</span>
            <span className="flex items-center gap-1.5"><MessageCircle className="w-3.5 h-3.5 text-white/25" />{m.comments?.toLocaleString()}</span>
            {m.shares != null && <span className="flex items-center gap-1.5"><Share2 className="w-3.5 h-3.5 text-white/25" />{m.shares?.toLocaleString()}</span>}
            {m.saves > 0 && <span className="flex items-center gap-1.5 text-emerald-400"><Bookmark className="w-3.5 h-3.5" />{m.saves?.toLocaleString()}</span>}
          </div>
          {s.trend_score > 0 && (
            <div className="flex flex-wrap items-center gap-3 text-xs text-white/30 font-mono">
              <span>Trend: <span className="text-emerald-400">{(s.trend_score * 100).toFixed(0)}</span></span>
              {s.save_rate != null && <span>Save%: <span className="text-emerald-400">{(s.save_rate * 100).toFixed(2)}%</span></span>}
              {s.overperformance_ratio != null && <span>Overperf: <span className="text-amber-400">{s.overperformance_ratio > 999 ? `${(s.overperformance_ratio/1000).toFixed(1)}K` : s.overperformance_ratio.toFixed(0)}x</span></span>}
              {s.engagement_rate != null && <span>ER: <span className="text-white/60">{(s.engagement_rate * 100).toFixed(2)}%</span></span>}
            </div>
          )}
          {item.caption && <p className="text-sm text-white/50 leading-relaxed">{item.caption}</p>}
          {item.music_title && (
            <div className="flex items-center gap-2 text-xs text-white/25"><Music className="w-3 h-3" /><span>{item.music_title}</span></div>
          )}
          {item.hashtags?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {(item.hashtags || []).slice(0, 8).map((tag, j) => <span key={j} className="px-1.5 py-0.5 text-[10px] bg-white/[0.04] text-white/30 border border-white/[0.06] rounded">#{tag}</span>)}
            </div>
          )}
          <div className="flex items-center gap-3 text-[10px] text-white/15 pt-2 border-t border-white/[0.04] font-mono">
            {item.source_query && <span>Source: {item.source_query}</span>}
            {item.posted_at && <span>{new Date(item.posted_at).toLocaleDateString()}</span>}
            {item.duration && <span>{item.duration}s</span>}
          </div>
          {item.post_url && (
            <a href={item.post_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 text-xs text-white bg-white/[0.06] hover:bg-white/10 border border-white/[0.06] transition-colors rounded-lg" data-testid="social-modal-open">
              <ExternalLink className="w-3 h-3" />Open in {item.platform === 'tiktok' ? 'TikTok' : 'Instagram'}
            </a>
          )}

          {/* Creative Analysis Enrichment */}
          <TikTokCreativeInsightPanel analysis={creativeAnalysis} />
        </div>
      </motion.div>
    </motion.div>
  );
};
