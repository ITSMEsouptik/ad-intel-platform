import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, ArrowRight, Globe, MapPin, LogOut, User, Loader2, CheckCircle2, AlertCircle, Dna, BarChart3 } from 'lucide-react';
import Logo from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { campaignBriefApi } from '@/lib/api';

const ease = [0.23, 1, 0.32, 1];

const STATUS_CONFIG = {
  success: { label: 'Ready', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/15', icon: CheckCircle2 },
  partial: { label: 'Partial', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/15', icon: CheckCircle2 },
  processing: { label: 'Processing', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/15', icon: Loader2 },
  failed: { label: 'Failed', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/15', icon: AlertCircle },
  none: { label: 'Not started', color: 'text-[var(--novara-text-tertiary)]', bg: 'bg-white/[0.04] border-white/[0.06]', icon: Globe },
};

const StatusBadge = ({ status }) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.none;
  const Icon = config.icon;
  const isSpinning = status === 'processing';
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest border rounded-md ${config.bg} ${config.color}`} data-testid="pack-status-badge">
      <Icon size={10} className={isSpinning ? 'animate-spin' : ''} />
      {config.label}
    </span>
  );
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { user, logout, isAuthenticated, loading: authLoading } = useAuth();
  const [briefs, setBriefs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate('/');
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchBriefs();
    }
  }, [isAuthenticated]);

  const fetchBriefs = async () => {
    try {
      const data = await campaignBriefApi.list();
      setBriefs(data);
    } catch (error) {
      console.error('Failed to fetch briefs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const getHostname = (url) => {
    try { return new URL(url).hostname; } catch { return url; }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-[var(--novara-text-primary)]">
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-black/80 backdrop-blur-xl border-b border-white/[0.06] z-50">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-14 flex items-center justify-between">
          <Logo size="default" />
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-[var(--novara-text-tertiary)]">
              <User className="w-3.5 h-3.5" strokeWidth={1.5} />
              <span className="text-xs font-mono hidden md:inline">{user?.email}</span>
            </div>
            <Button
              variant="ghost"
              onClick={handleLogout}
              className="text-[var(--novara-text-tertiary)] hover:text-white h-8 w-8 p-0"
              data-testid="logout-btn"
            >
              <LogOut className="w-3.5 h-3.5" strokeWidth={1.5} />
            </Button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="pt-20 pb-12 px-6 md:px-12">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <motion.div
            className="flex flex-col md:flex-row md:items-center md:justify-between mb-10"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease }}
          >
            <div>
              <h1 className="font-heading text-3xl md:text-4xl font-semibold tracking-tight mb-1" data-testid="dashboard-title">
                Campaigns
              </h1>
              <p className="text-sm text-[var(--novara-text-tertiary)]">
                {briefs.length === 0
                  ? 'No campaigns yet. Analyze your first website.'
                  : `${briefs.length} campaign${briefs.length === 1 ? '' : 's'}`
                }
              </p>
            </div>
            <Button
              onClick={() => navigate('/wizard')}
              className="mt-4 md:mt-0 bg-white text-black hover:bg-gray-100 rounded-lg font-medium px-5 py-2.5 text-sm"
              data-testid="create-brief-btn"
            >
              <Plus className="mr-1.5 h-4 w-4" strokeWidth={1.5} />
              New Campaign
            </Button>
          </motion.div>

          {/* Campaign Cards */}
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="w-6 h-6 border-2 border-white/20 border-t-white/70 rounded-full animate-spin" />
            </div>
          ) : briefs.length === 0 ? (
            <motion.div
              className="border border-white/[0.06] bg-[var(--novara-surface)] rounded-xl p-12 text-center"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <div className="max-w-md mx-auto">
                <h2 className="font-heading text-xl font-semibold mb-3">Analyze your first website</h2>
                <p className="text-sm text-[var(--novara-text-tertiary)] mb-8">
                  Paste a URL and we'll extract brand DNA, competitive intel, and ad insights.
                </p>
                <Button
                  onClick={() => navigate('/wizard')}
                  className="bg-white text-black hover:bg-gray-100 rounded-lg font-medium px-6 py-3"
                  data-testid="empty-state-cta"
                >
                  Get Started
                  <ArrowRight className="ml-2 h-4 w-4" strokeWidth={1.5} />
                </Button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              className="space-y-2"
              initial="initial"
              animate="animate"
              variants={{ animate: { transition: { staggerChildren: 0.05 } } }}
            >
              {briefs.map((brief, index) => {
                const packReady = brief.pack_status === 'success' || brief.pack_status === 'partial';
                const displayName = brief.brand_name || getHostname(brief.brand.website_url);

                return (
                  <motion.div
                    key={brief.campaign_brief_id}
                    variants={{ initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease } } }}
                    className="bg-[var(--novara-surface)] border border-white/[0.06] hover:border-white/[0.12] transition-colors duration-200 rounded-xl overflow-hidden group"
                    data-testid={`brief-card-${index}`}
                  >
                    {/* Top row */}
                    <div className="p-5">
                      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2.5 mb-1.5">
                            <h3 className="font-heading text-base font-semibold truncate" data-testid={`brief-name-${index}`}>
                              {displayName}
                            </h3>
                            <StatusBadge status={brief.pack_status} />
                          </div>
                          <div className="flex flex-wrap items-center gap-3 text-[var(--novara-text-tertiary)]">
                            <span className="flex items-center gap-1 font-mono text-[11px]">
                              <Globe className="w-3 h-3" strokeWidth={1.5} />
                              {getHostname(brief.brand.website_url)}
                            </span>
                            {(brief.geo?.city_or_region || brief.geo?.country) && (
                              <span className="flex items-center gap-1 text-[11px]">
                                <MapPin className="w-3 h-3" strokeWidth={1.5} />
                                {brief.geo?.city_or_region ? `${brief.geo.city_or_region}, ` : ''}{brief.geo?.country}
                              </span>
                            )}
                            <span className="text-[11px] font-mono">
                              {new Date(brief.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Action row */}
                    <div className="border-t border-white/[0.04] px-5 py-3 flex items-center gap-2">
                      {packReady ? (
                        <>
                          <button
                            onClick={() => navigate(`/pack/${brief.campaign_brief_id}`)}
                            className="flex items-center gap-1.5 text-xs text-[var(--novara-text-secondary)] hover:text-white transition-colors px-3 py-1.5 border border-white/[0.06] hover:border-white/[0.15] rounded-md"
                            data-testid={`btn-business-dna-${index}`}
                          >
                            <Dna size={12} />
                            Business DNA
                          </button>
                          <button
                            onClick={() => navigate(`/intel/${brief.campaign_brief_id}`)}
                            className="flex items-center gap-1.5 text-xs text-[var(--novara-text-secondary)] hover:text-white transition-colors px-3 py-1.5 border border-white/[0.06] hover:border-white/[0.15] rounded-md"
                            data-testid={`btn-intel-hub-${index}`}
                          >
                            <BarChart3 size={12} />
                            Intelligence Hub
                          </button>
                          <button
                            onClick={() => navigate(`/brief/${brief.campaign_brief_id}`)}
                            className="text-[11px] text-[var(--novara-text-tertiary)] hover:text-[var(--novara-text-secondary)] transition-colors ml-auto font-mono"
                            data-testid={`btn-brief-detail-${index}`}
                          >
                            Details
                          </button>
                        </>
                      ) : brief.pack_status === 'processing' ? (
                        <button
                          onClick={() => navigate(`/building/${brief.campaign_brief_id}`)}
                          className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                          data-testid={`btn-building-${index}`}
                        >
                          <Loader2 size={12} className="animate-spin" />
                          View Progress
                        </button>
                      ) : brief.pack_status === 'failed' ? (
                        <button
                          onClick={() => navigate(`/brief/${brief.campaign_brief_id}`)}
                          className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-300 transition-colors"
                          data-testid={`btn-retry-${index}`}
                        >
                          <AlertCircle size={12} />
                          View Details
                        </button>
                      ) : (
                        <button
                          onClick={() => navigate(`/building/${brief.campaign_brief_id}`)}
                          className="flex items-center gap-1.5 text-xs text-[var(--novara-text-tertiary)] hover:text-[var(--novara-text-secondary)] transition-colors"
                          data-testid={`btn-start-${index}`}
                        >
                          Start Analysis
                          <ArrowRight size={12} />
                        </button>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
