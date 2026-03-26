import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, Loader2, AlertCircle, GitCompare, ArrowUp, ArrowDown, Minus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { STATUS, useIntel } from '../IntelligenceContext';
import api from '@/lib/api';

const API_SLUG_MAP = {
  customerIntel: 'customer-intel',
  searchIntent: 'search-intent',
  seasonality: 'seasonality',
  competitors: 'competitors',
  reviews: 'reviews',
  community: 'community',
  pressMedia: 'press-media',
  socialTrends: 'social-trends',
  adsIntel: 'ads-intel',
};

/**
 * Module header with status badge, delta info, compare toggle, and refresh button.
 */
export const ModuleHeader = ({ title, moduleKey, status, refreshDueInDays, delta, onRun, error, onRetry, children }) => {
  const { briefId } = useIntel();
  const [showCompare, setShowCompare] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [loadingCompare, setLoadingCompare] = useState(false);

  const slug = API_SLUG_MAP[moduleKey];

  const fetchComparison = useCallback(async () => {
    if (!slug || !briefId) return;
    setLoadingCompare(true);
    try {
      const res = await api.get(`/research/${briefId}/${slug}/compare`);
      setComparison(res.data);
    } catch {
      setComparison({ has_comparison: false, message: 'Could not load comparison' });
    } finally {
      setLoadingCompare(false);
    }
  }, [briefId, slug]);

  const handleToggleCompare = () => {
    if (!showCompare && !comparison) fetchComparison();
    setShowCompare(prev => !prev);
  };

  const statusConfig = {
    [STATUS.RUNNING]: { text: 'Running...', dotClass: 'bg-blue-500 animate-pulse', textClass: 'text-blue-400' },
    [STATUS.FRESH]: { text: `Fresh${refreshDueInDays ? ` \u00B7 ${refreshDueInDays}d until refresh` : ''}`, dotClass: 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]', textClass: 'text-emerald-400' },
    [STATUS.STALE]: { text: 'Stale \u00B7 Refresh recommended', dotClass: 'bg-amber-500', textClass: 'text-amber-400' },
    [STATUS.FAILED]: { text: 'Failed', dotClass: 'bg-rose-500', textClass: 'text-rose-400' },
    [STATUS.NOT_RUN]: { text: 'Not run yet', dotClass: 'bg-white/20', textClass: 'text-white/30' },
  };
  const cfg = statusConfig[status] || statusConfig[STATUS.NOT_RUN];
  const hasFreshData = status === STATUS.FRESH || status === STATUS.STALE;

  return (
    <div className="mb-8">
      <h1 className="text-2xl font-heading font-semibold text-white mb-4 tracking-tight">{title}</h1>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
            <span className={`h-2 w-2 rounded-full ${cfg.dotClass}`} />
            <span className={`text-xs font-mono ${cfg.textClass}`}>{cfg.text}</span>
          </div>

          {delta && (
            <motion.span
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-emerald-400 text-xs font-mono bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20"
            >
              +{delta.count} {delta.label}
            </motion.span>
          )}

          {children}
        </div>

        <div className="flex items-center gap-2">
          {hasFreshData && slug && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleToggleCompare}
              className={`h-8 px-3 gap-1.5 rounded-lg text-xs ${showCompare ? 'text-blue-400 bg-blue-500/10 hover:bg-blue-500/15' : 'text-white/40 hover:text-white hover:bg-white/5'}`}
              data-testid={`compare-${moduleKey}`}
            >
              <GitCompare className="w-3.5 h-3.5" />
              Compare
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onRun}
            disabled={status === STATUS.RUNNING}
            className="text-white/40 hover:text-white hover:bg-white/5 h-8 px-3 gap-2 rounded-lg"
            data-testid={`refresh-${title?.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${status === STATUS.RUNNING ? 'animate-spin' : ''}`} />
            <span className="text-xs">Refresh</span>
          </Button>
        </div>
      </div>

      {/* Comparison Panel */}
      <AnimatePresence>
        {showCompare && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
            className="overflow-hidden mb-4"
          >
            <ComparisonPanel
              comparison={comparison}
              loading={loadingCompare}
              onClose={() => setShowCompare(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-rose-500/5 border border-rose-500/20 rounded-xl flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <AlertCircle className="w-4 h-4 text-rose-400" />
            <div>
              <p className="text-sm font-medium text-rose-400">{title} failed</p>
              {error.message && <p className="text-xs text-white/30 mt-0.5">{error.message}</p>}
            </div>
          </div>
          <Button
            onClick={onRetry || onRun}
            size="sm"
            className="bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-lg h-7 text-xs"
          >
            Retry
          </Button>
        </motion.div>
      )}
    </div>
  );
};

/**
 * Comparison panel showing deltas between runs
 */
const ComparisonPanel = ({ comparison, loading, onClose }) => {
  if (loading) {
    return (
      <div className="p-4 bg-blue-500/5 border border-blue-500/10 rounded-xl">
        <div className="flex items-center gap-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
          <span className="text-xs text-blue-400/60 font-mono">Loading comparison...</span>
        </div>
      </div>
    );
  }

  if (!comparison?.has_comparison) {
    return (
      <div className="p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCompare className="w-3.5 h-3.5 text-white/20" />
          <span className="text-xs text-white/40">{comparison?.message || 'No previous run to compare against'}</span>
        </div>
        <button onClick={onClose} className="text-white/20 hover:text-white/40">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  const { deltas } = comparison;

  if (!deltas || deltas.length === 0) {
    return (
      <div className="p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Minus className="w-3.5 h-3.5 text-white/20" />
          <span className="text-xs text-white/40">No changes detected between runs</span>
        </div>
        <button onClick={onClose} className="text-white/20 hover:text-white/40">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 bg-blue-500/5 border border-blue-500/10 rounded-xl" data-testid="comparison-panel">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <GitCompare className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-[11px] font-mono text-blue-400/80 uppercase tracking-wider">Run Comparison</span>
        </div>
        <button onClick={onClose} className="text-white/20 hover:text-white/40">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {deltas.map((d, i) => (
          <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.03]">
            {d.direction === 'up' ? (
              <ArrowUp className="w-3 h-3 text-emerald-400 shrink-0" />
            ) : (
              <ArrowDown className="w-3 h-3 text-rose-400 shrink-0" />
            )}
            <div className="min-w-0">
              <p className="text-[10px] text-white/30 font-mono truncate">{formatFieldName(d.field)}</p>
              <p className={`text-xs font-mono ${d.direction === 'up' ? 'text-emerald-400' : 'text-rose-400'}`}>
                {d.previous} &rarr; {d.current}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const formatFieldName = (field) =>
  field.replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

/**
 * Loading state with progress indicators
 */
export const ModuleRunning = ({ message = 'Analyzing...', submessage = 'This may take 20-40 seconds', moduleKey }) => {
  const { briefId } = useIntel();
  const [progress, setProgress] = useState(null);
  const slug = API_SLUG_MAP[moduleKey];

  useEffect(() => {
    if (!slug || !briefId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await api.get(`/research/${briefId}/${slug}/progress`);
        if (!cancelled) setProgress(res.data);
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 4000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [briefId, slug]);

  const progressPct = progress?.progress_pct || 0;
  const events = progress?.events || [];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center py-20"
    >
      <div className="relative mb-6">
        <div className="absolute inset-0 bg-blue-500/20 rounded-full blur-xl animate-pulse" />
        <Loader2 className="w-8 h-8 animate-spin text-white/60 relative" />
      </div>
      <p className="text-white/50 text-sm">{message}</p>
      <p className="text-white/20 text-xs mt-1 font-mono">{submessage}</p>

      {/* Progress bar */}
      {progressPct > 0 && (
        <div className="mt-6 w-full max-w-xs">
          <div className="flex justify-between mb-1.5">
            <span className="text-[10px] text-white/20 font-mono">Progress</span>
            <span className="text-[10px] text-white/30 font-mono">{progressPct}%</span>
          </div>
          <div className="h-1 bg-white/[0.04] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              className="h-full bg-blue-500/60 rounded-full"
            />
          </div>
        </div>
      )}

      {/* Progress events timeline */}
      {events.length > 0 && (
        <div className="mt-4 w-full max-w-xs space-y-1.5">
          {events.slice(-4).map((e, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className="flex items-center gap-2"
            >
              <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${i === events.slice(-4).length - 1 ? 'bg-blue-500 animate-pulse' : 'bg-white/10'}`} />
              <span className="text-[10px] text-white/25 font-mono truncate">
                {e.event?.replace(/_/g, ' ').toLowerCase()}
              </span>
            </motion.div>
          ))}
        </div>
      )}

      {/* Skeleton preview */}
      <div className="mt-8 w-full max-w-md space-y-3 animate-pulse">
        <div className="h-3 bg-white/[0.03] rounded-full w-3/4 mx-auto" />
        <div className="h-3 bg-white/[0.03] rounded-full w-1/2 mx-auto" />
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="h-20 bg-white/[0.02] rounded-xl" />
          <div className="h-20 bg-white/[0.02] rounded-xl" />
        </div>
      </div>
    </motion.div>
  );
};

/**
 * Empty state when module hasn't been run
 */
export const ModuleEmpty = ({ icon: Icon, title, description, onGenerate }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="flex flex-col items-center justify-center py-24"
  >
    <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mb-4">
      <Icon className="w-5 h-5 text-white/20" strokeWidth={1.5} />
    </div>
    <p className="text-white/40 text-sm mb-1">{title}</p>
    {description && <p className="text-white/20 text-xs mb-6 max-w-sm text-center">{description}</p>}
    {onGenerate && (
      <Button
        onClick={onGenerate}
        className="bg-white text-black hover:bg-white/90 rounded-lg text-xs font-medium h-8 px-4"
        data-testid="generate-module"
      >
        Generate Now
      </Button>
    )}
  </motion.div>
);
