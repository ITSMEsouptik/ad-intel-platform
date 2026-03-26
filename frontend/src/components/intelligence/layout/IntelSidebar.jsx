import React from 'react';
import { motion } from 'framer-motion';
import {
  LayoutGrid, Users, Search, Calendar, Building2,
  MessageSquareQuote, UsersRound, Newspaper, TrendingUp, Zap, Loader2
} from 'lucide-react';
import { useIntel, STATUS } from '../IntelligenceContext';

const MODULES = [
  { key: 'overview', label: 'Overview', icon: LayoutGrid },
  { key: 'customerIntel', label: 'Audience', icon: Users },
  { key: 'searchIntent', label: 'Search Demand', icon: Search },
  { key: 'seasonality', label: 'Seasonality', icon: Calendar },
  { key: 'competitors', label: 'Competitors', icon: Building2 },
  { key: 'reviews', label: 'Reviews', icon: MessageSquareQuote },
  { key: 'community', label: 'Community', icon: UsersRound },
  { key: 'pressMedia', label: 'Press & Media', icon: Newspaper },
  { key: 'socialTrends', label: 'Social Trends', icon: TrendingUp },
  { key: 'adsIntel', label: 'Ads', icon: Zap },
];

const StatusDot = ({ status }) => {
  const styles = {
    [STATUS.FRESH]: 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]',
    [STATUS.STALE]: 'bg-amber-500',
    [STATUS.RUNNING]: 'bg-blue-500 animate-pulse',
    [STATUS.FAILED]: 'bg-rose-500',
    [STATUS.NOT_RUN]: 'bg-white/10',
  };
  return <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${styles[status] || styles[STATUS.NOT_RUN]}`} />;
};

export const IntelSidebar = () => {
  const { activeModule, setActiveModule, modules } = useIntel();

  return (
    <aside className="w-56 h-full border-r border-white/[0.06] bg-[#050505] hidden md:flex flex-col shrink-0 z-20" data-testid="intel-sidebar">
      {/* Module list */}
      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        <div className="px-3 mb-4">
          <span className="text-[10px] font-mono text-white/20 uppercase tracking-[0.2em]">Modules</span>
        </div>
        {MODULES.map(({ key, label, icon: Icon }) => {
          const isActive = activeModule === key;
          const status = key === 'overview' ? null : modules[key]?.status;
          const isRunning = status === STATUS.RUNNING;

          return (
            <motion.button
              key={key}
              onClick={() => setActiveModule(key)}
              whileTap={{ scale: 0.98 }}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left
                transition-colors duration-200 relative group
                ${isActive
                  ? 'bg-white/[0.08] text-white'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/[0.03]'
                }
              `}
              data-testid={`sidebar-${key}`}
            >
              {/* Active indicator */}
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-white rounded-r-full"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}

              {isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin text-blue-400 shrink-0" />
              ) : (
                <Icon className="w-4 h-4 shrink-0" strokeWidth={1.5} />
              )}

              <span className="text-[13px] font-medium truncate">{label}</span>

              {/* Status dot */}
              {status && !isRunning && (
                <div className="ml-auto">
                  <StatusDot status={status} />
                </div>
              )}
            </motion.button>
          );
        })}
      </nav>
    </aside>
  );
};
