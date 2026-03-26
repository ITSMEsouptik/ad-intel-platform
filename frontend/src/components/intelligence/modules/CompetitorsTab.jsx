import React from 'react';
import { Building2, Globe, ExternalLink } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, Cell } from 'recharts';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';

export const CompetitorsTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.competitors;
  const latest = data?.latest;

  const delta = latest?.delta?.new_competitors_count > 0
    ? { count: latest.delta.new_competitors_count, label: 'new competitors' }
    : null;

  return (
    <div data-testid="competitors-tab">
      <ModuleHeader title="Competitors" moduleKey="competitors" status={status} refreshDueInDays={data?.refresh_due_in_days} delta={delta} onRun={() => runModule('competitors')} error={error} />

      {status === STATUS.RUNNING && <ModuleRunning message="Discovering competitors..." submessage="This takes 30-60 seconds" moduleKey="competitors" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={Building2} title="Competitor Discovery not run" description="Identify direct competitors with their positioning and social presence." onGenerate={() => runModule('competitors')} />
      )}

      {latest && (
        <>
          {/* Market breadcrumb */}
          {latest.inputs_used && (latest.inputs_used.subcategory || latest.inputs_used.niche) && (
            <div className="mb-6">
              <span className="text-white/30 font-mono text-xs">
                {[latest.inputs_used.subcategory, latest.inputs_used.niche].filter(Boolean).join(' \u2192 ')}
              </span>
              {latest.inputs_used.geo?.city && (
                <span className="text-white/15 font-mono text-xs ml-2">({latest.inputs_used.geo.city}, {latest.inputs_used.geo.country})</span>
              )}
            </div>
          )}

          {/* Market Overview */}
          {latest.market_overview && (
            <AntigravityCard className="p-5 mb-8">
              <span className="text-[11px] font-mono text-white/30 uppercase tracking-[0.2em] mb-4 block">Market Overview</span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {latest.market_overview.competitive_density && (
                  <div>
                    <span className="text-[10px] text-white/20 font-mono">Competitive Density</span>
                    <p className="text-white/70 font-medium capitalize">{latest.market_overview.competitive_density}</p>
                  </div>
                )}
                {latest.market_overview.dominant_player_type && (
                  <div>
                    <span className="text-[10px] text-white/20 font-mono">Who Dominates</span>
                    <p className="text-white/70 font-medium"><CleanText>{latest.market_overview.dominant_player_type}</CleanText></p>
                  </div>
                )}
                {latest.market_overview.market_insight && (
                  <div className="md:col-span-2">
                    <span className="text-[10px] text-white/20 font-mono">Market Insight</span>
                    <p className="text-white/50 text-sm mt-1"><CleanText>{latest.market_overview.market_insight}</CleanText></p>
                  </div>
                )}
                {latest.market_overview.ad_landscape_note && (
                  <div className="md:col-span-2">
                    <span className="text-[10px] text-white/20 font-mono">Ad Landscape</span>
                    <p className="text-white/50 text-sm mt-1"><CleanText>{latest.market_overview.ad_landscape_note}</CleanText></p>
                  </div>
                )}
              </div>
            </AntigravityCard>
          )}

          {/* Legacy market_context */}
          {!latest.market_overview && latest.market_context && (
            <AntigravityCard className="p-5 mb-8">
              <span className="text-[11px] font-mono text-white/30 uppercase tracking-[0.2em] mb-3 block">Market Overview</span>
              <p className="text-white/50 text-sm"><CleanText>{latest.market_context}</CleanText></p>
            </AntigravityCard>
          )}

          {/* Competitor Comparison Chart */}
          {latest.competitors?.length > 0 && (
            <section className="mb-10">
              <SectionLabel>Competitive Comparison</SectionLabel>
              <AntigravityCard className="p-5" data-testid="competitor-comparison-chart">
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart
                    data={latest.competitors.map(c => ({
                      name: c.name,
                      strengths: (c.strengths || []).length,
                      weaknesses: (c.weaknesses || []).length,
                      overlap: (c.overlap_score || c.overlap_level) === 'high' ? 3 : (c.overlap_score || c.overlap_level) === 'medium' ? 2 : 1,
                    }))}
                    margin={{ top: 8, right: 12, left: -8, bottom: 0 }}
                  >
                    <XAxis
                      dataKey="name"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11, fontFamily: 'monospace' }}
                    />
                    <YAxis hide />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload;
                        return (
                          <div className="bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2">
                            <p className="text-xs text-white/70 font-medium mb-1">{d.name}</p>
                            <p className="text-[10px] text-emerald-400">{d.strengths} strengths</p>
                            <p className="text-[10px] text-rose-400">{d.weaknesses} weaknesses</p>
                          </div>
                        );
                      }}
                    />
                    <Bar dataKey="strengths" fill="#10b981" fillOpacity={0.5} radius={[4, 4, 0, 0]} name="Strengths" animationDuration={800} />
                    <Bar dataKey="weaknesses" fill="#f43f5e" fillOpacity={0.5} radius={[4, 4, 0, 0]} name="Weaknesses" animationDuration={800} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="flex items-center gap-4 mt-3 pt-3 border-t border-white/[0.04]">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-sm bg-emerald-500/50" />
                    <span className="text-[9px] text-white/25 font-mono">Strengths</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-sm bg-rose-500/50" />
                    <span className="text-[9px] text-white/25 font-mono">Weaknesses</span>
                  </div>
                </div>
              </AntigravityCard>
            </section>
          )}

          {/* Competitor Cards */}
          {latest.competitors?.length > 0 && (
            <section className="mb-10">
              <SectionLabel count={latest.competitors.length}>Direct Competitors</SectionLabel>
              <StaggerContainer className="space-y-4">
                {latest.competitors.map((comp, i) => (
                  <StaggerItem key={i}>
                    <CompetitorCard comp={comp} index={i} />
                  </StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}
        </>
      )}
    </div>
  );
};

const CompetitorCard = ({ comp, index }) => {
  const strengths = comp.strengths || [];
  const weaknesses = comp.weaknesses || [];
  const adStrategy = comp.ad_strategy_summary;
  const socialPresence = comp.social_presence || [];
  // Map backend field names: website (not website_url), overlap_score (not overlap_level)
  const websiteUrl = comp.website || comp.website_url;
  const overlapLevel = comp.overlap_score || comp.overlap_level || 'low';
  const overlapColors = {
    high: { border: 'border-l-rose-500/40', badge: 'text-rose-400 bg-rose-500/10 border-rose-500/15', label: 'High Overlap' },
    medium: { border: 'border-l-amber-500/40', badge: 'text-amber-400 bg-amber-500/10 border-amber-500/15', label: 'Medium Overlap' },
    low: { border: 'border-l-white/10', badge: 'text-white/30 bg-white/5 border-white/10', label: 'Low Overlap' },
  };
  const overlap = overlapColors[overlapLevel] || overlapColors.low;

  return (
    <AntigravityCard className={`p-5 border-l-2 ${overlap.border}`} data-testid={`competitor-card-${index}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center shrink-0">
            <span className="text-sm font-heading font-medium text-white/30">{comp.name?.charAt(0)}</span>
          </div>
          <div>
            <h3 className="font-heading text-lg font-medium text-white">{comp.name}</h3>
            {websiteUrl && (
              <a href={websiteUrl.startsWith('http') ? websiteUrl : `https://${websiteUrl}`}
                 target="_blank" rel="noopener noreferrer"
                 className="text-white/25 text-xs hover:text-white/50 transition-colors flex items-center gap-1 mt-0.5">
                <Globe className="w-3 h-3" /> {websiteUrl.replace(/^https?:\/\//, '')}
              </a>
            )}
          </div>
        </div>
        <span className={`px-2.5 py-1 text-[10px] uppercase tracking-wider border rounded-lg font-mono ${overlap.badge}`}>{overlap.label}</span>
      </div>

      {/* What they do + Why competitor */}
      {(comp.what_they_do || comp.positioning) && (
        <div className="mb-4 space-y-1">
          {comp.what_they_do && <p className="text-white/50 text-sm"><CleanText>{comp.what_they_do}</CleanText></p>}
          {comp.positioning && <p className="text-white/30 text-sm italic"><CleanText>{comp.positioning}</CleanText></p>}
          {comp.why_competitor && <p className="text-white/20 text-xs font-mono mt-1"><CleanText>{comp.why_competitor}</CleanText></p>}
        </div>
      )}

      {/* Price tier + Size */}
      <div className="flex items-center gap-2 mb-4">
        {comp.price_tier && (
          <span className="text-[10px] px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded-md text-white/30 font-mono capitalize">{comp.price_tier}</span>
        )}
        {comp.estimated_size && (
          <span className="text-[10px] px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded-md text-white/30 font-mono capitalize">{comp.estimated_size}</span>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        {strengths.length > 0 && (
          <div>
            <span className="text-[10px] text-emerald-400 uppercase tracking-wider font-mono">Strengths</span>
            <ul className="mt-1.5 space-y-1">
              {strengths.map((s, j) => (
                <li key={j} className="text-white/50 text-sm flex gap-2"><span className="text-emerald-400/50">+</span><CleanText>{s}</CleanText></li>
              ))}
            </ul>
          </div>
        )}
        {weaknesses.length > 0 && (
          <div>
            <span className="text-[10px] text-rose-400 uppercase tracking-wider font-mono">Weaknesses</span>
            <ul className="mt-1.5 space-y-1">
              {weaknesses.map((w, j) => (
                <li key={j} className="text-white/50 text-sm flex gap-2"><span className="text-rose-400/50">&minus;</span><CleanText>{w}</CleanText></li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {adStrategy && (
        <div className="mb-4">
          <span className="text-[10px] text-violet-400 uppercase tracking-wider font-mono">Ad Strategy</span>
          <p className="text-white/50 text-sm mt-1"><CleanText>{typeof adStrategy === 'string' ? adStrategy : adStrategy.summary || ''}</CleanText></p>
        </div>
      )}

      {socialPresence.length > 0 && (
        <div className="pt-3 border-t border-white/[0.04]">
          <span className="text-[10px] text-white/20 font-mono uppercase tracking-wider">Social Presence</span>
          <div className="flex flex-wrap gap-2 mt-2">
            {socialPresence.map((sp, j) => (
              <a key={j} href={sp.url} target="_blank" rel="noopener noreferrer"
                 className="text-xs px-3 py-1.5 bg-white/[0.04] border border-white/[0.06] text-white/40 rounded-lg hover:bg-white/[0.08] hover:border-white/[0.12] transition-all flex items-center gap-2">
                <span className="font-medium">{sp.platform}</span>
                {sp.followers_approx && <span className="text-white/20 font-mono text-[10px]">{sp.followers_approx}</span>}
                <ExternalLink className="w-3 h-3 text-white/15" />
              </a>
            ))}
          </div>
        </div>
      )}
    </AntigravityCard>
  );
};
