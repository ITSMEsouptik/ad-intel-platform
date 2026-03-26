import React, { useState } from 'react';
import { MessageSquareQuote, ChevronDown, ChevronUp, Star, AlertTriangle, ExternalLink, Shield, TrendingUp, Building2 } from 'lucide-react';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';

export const ReviewsTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.reviews;
  const latest = data?.latest;

  const hasPlatforms = latest?.platform_presence?.length > 0;
  const hasStrengths = latest?.strength_themes?.length > 0;
  const hasWeaknesses = latest?.weakness_themes?.length > 0;
  const hasSnippets = latest?.social_proof_snippets?.length > 0;
  const hasTrustSignals = latest?.trust_signals?.length > 0;
  const hasCompReputation = latest?.competitor_reputation && Object.keys(latest.competitor_reputation).length > 0;
  const hasBrandReality = latest?.brand_vs_reality && Object.keys(latest.brand_vs_reality).length > 0;
  const hasAnyData = hasPlatforms || hasStrengths || hasWeaknesses || hasSnippets || hasTrustSignals || hasCompReputation || hasBrandReality;

  return (
    <div data-testid="reviews-tab">
      <ModuleHeader title="Reviews" moduleKey="reviews" status={status} refreshDueInDays={data?.refresh_due_in_days} onRun={() => runModule('reviews')} error={error}>
        {latest?.social_proof_readiness && (
          <span className={`text-xs font-mono px-2.5 py-1 rounded-full border ${
            latest.social_proof_readiness === 'strong' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15' :
            latest.social_proof_readiness === 'moderate' ? 'text-amber-400 bg-amber-500/10 border-amber-500/15' :
            'text-rose-400 bg-rose-500/10 border-rose-500/15'
          }`}>
            Social Proof: {latest.social_proof_readiness}
          </span>
        )}
      </ModuleHeader>

      {status === STATUS.RUNNING && <ModuleRunning message="Scanning review platforms..." moduleKey="reviews" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={MessageSquareQuote} title="Reviews not scanned yet" onGenerate={() => runModule('reviews')} />
      )}

      {latest && (
        <>
          {/* Review Health Summary - always show when data exists */}
          <AntigravityCard className="p-5 mb-8" data-testid="review-health-summary">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricBlock label="Platforms" value={latest.platform_presence?.length || 0} />
              <MetricBlock label="Strengths" value={latest.strength_themes?.length || 0} color="emerald" />
              <MetricBlock label="Weaknesses" value={latest.weakness_themes?.length || 0} color="rose" />
              <MetricBlock label="Trust Signals" value={latest.trust_signals?.length || 0} color="blue" />
            </div>
          </AntigravityCard>

          {/* Review Gap Alert - when platforms are empty */}
          {!hasPlatforms && (
            <AntigravityCard className="p-5 mb-8 border-l-2 border-l-amber-500/40" data-testid="review-gap-alert">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-white/80 text-sm font-medium mb-1">Review Gap Detected</h3>
                  <p className="text-white/40 text-sm leading-relaxed">
                    No customer review platforms with active reviews found. This is a significant gap: prospects researching this brand will find no social proof.
                    Consider building presence on Google Maps, Trustpilot, or industry-specific review platforms before investing in paid acquisition.
                  </p>
                </div>
              </div>
            </AntigravityCard>
          )}

          {/* Trust Signals - these exist even when platforms are empty */}
          {hasTrustSignals && (
            <section className="mb-10">
              <SectionLabel count={latest.trust_signals.length}>Trust Signals Found</SectionLabel>
              <StaggerContainer className="space-y-2">
                {latest.trust_signals.map((signal, i) => (
                  <StaggerItem key={i}>
                    <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-white/[0.02] border border-white/[0.04]" data-testid={`trust-signal-${i}`}>
                      <Shield className="w-4 h-4 text-emerald-400/50 shrink-0 mt-0.5" />
                      <p className="text-white/60 text-sm"><CleanText>{signal}</CleanText></p>
                    </div>
                  </StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Platform Presence */}
          {hasPlatforms && (
            <section className="mb-10">
              <SectionLabel count={latest.platform_presence.length}>Platform Presence</SectionLabel>
              <StaggerContainer className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {latest.platform_presence.map((plat, i) => (
                  <StaggerItem key={i}>
                    <AntigravityCard className="p-5" data-testid={`platform-${i}`}>
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-white text-sm">{plat.platform}</h3>
                        {plat.approximate_rating && (
                          <div className="flex items-center gap-1">
                            <Star className="w-3.5 h-3.5 text-amber-400" fill="currentColor" />
                            <span className="text-amber-400 text-sm font-mono">{plat.approximate_rating}</span>
                          </div>
                        )}
                      </div>
                      {plat.review_count && <p className="text-white/30 text-xs font-mono">{plat.review_count} reviews</p>}
                      {plat.url && (
                        <a href={plat.url} target="_blank" rel="noopener noreferrer"
                           className="text-white/20 text-xs hover:text-white/40 mt-2 flex items-center gap-1">
                          View <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </AntigravityCard>
                  </StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Strength Themes */}
          {hasStrengths && (
            <section className="mb-10">
              <SectionLabel count={latest.strength_themes.length}>Strengths</SectionLabel>
              <div className="space-y-2">
                {latest.strength_themes.map((theme, i) => (
                  <ThemeRow key={i} theme={theme} type="strength" index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Weakness Themes */}
          {hasWeaknesses && (
            <section className="mb-10">
              <SectionLabel count={latest.weakness_themes.length}>Weaknesses</SectionLabel>
              <div className="space-y-2">
                {latest.weakness_themes.map((theme, i) => (
                  <ThemeRow key={i} theme={theme} type="weakness" index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Social Proof Snippets */}
          {hasSnippets && (
            <section className="mb-10">
              <SectionLabel count={latest.social_proof_snippets.length}>Best Quotes</SectionLabel>
              <StaggerContainer className="grid md:grid-cols-2 gap-4">
                {latest.social_proof_snippets.map((snippet, i) => (
                  <StaggerItem key={i}>
                    <AntigravityCard className="p-5">
                      <p className="text-white/60 text-sm italic">&ldquo;{snippet.quote || snippet}&rdquo;</p>
                      {snippet.source && <p className="text-white/20 text-xs mt-2 font-mono">{snippet.source}</p>}
                    </AntigravityCard>
                  </StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Competitor Reputation */}
          {hasCompReputation && (
            <section className="mb-10">
              <SectionLabel>Competitor Reputation Landscape</SectionLabel>
              <StaggerContainer className="space-y-3">
                {Object.entries(latest.competitor_reputation).map(([competitor, info], i) => (
                  <StaggerItem key={i}>
                    <AntigravityCard className="p-4" data-testid={`comp-reputation-${i}`}>
                      <div className="flex items-center gap-2 mb-2">
                        <Building2 className="w-4 h-4 text-white/20" />
                        <h4 className="text-white/70 text-sm font-medium">{competitor}</h4>
                      </div>
                      {typeof info === 'string' ? (
                        <p className="text-white/40 text-sm pl-6"><CleanText>{info}</CleanText></p>
                      ) : typeof info === 'object' ? (
                        <div className="pl-6 space-y-1">
                          {Object.entries(info).map(([k, v]) => (
                            <p key={k} className="text-white/40 text-sm"><span className="text-white/20 font-mono text-xs">{k.replace(/_/g, ' ')}: </span><CleanText>{typeof v === 'string' ? v : JSON.stringify(v)}</CleanText></p>
                          ))}
                        </div>
                      ) : null}
                    </AntigravityCard>
                  </StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Brand vs Reality */}
          {hasBrandReality && (
            <section className="mb-10">
              <SectionLabel>Brand Perception vs Reality</SectionLabel>
              <AntigravityCard className="p-5" data-testid="brand-vs-reality">
                <div className="space-y-3">
                  {Object.entries(latest.brand_vs_reality).map(([key, value]) => (
                    <div key={key} className="flex items-start gap-3">
                      <TrendingUp className="w-4 h-4 text-white/15 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-white/30 text-xs font-mono uppercase tracking-wider">{key.replace(/_/g, ' ')}</span>
                        <p className="text-white/55 text-sm mt-0.5"><CleanText>{typeof value === 'string' ? value : JSON.stringify(value)}</CleanText></p>
                      </div>
                    </div>
                  ))}
                </div>
              </AntigravityCard>
            </section>
          )}

          {/* Audit section removed - internal debug data */}
        </>
      )}
    </div>
  );
};

const ThemeRow = ({ theme, type, index }) => {
  const [expanded, setExpanded] = useState(false);
  const isStrength = type === 'strength';
  const freqColors = { frequent: 'text-white/60 bg-white/5', moderate: 'text-white/30 bg-white/[0.03]', occasional: 'text-white/20 bg-white/[0.02]' };
  const sevColors = { deal_breaker: 'text-rose-400 bg-rose-500/10', moderate: 'text-amber-400 bg-amber-500/10', minor: 'text-white/30 bg-white/5' };

  return (
    <AntigravityCard className={`p-4 ${isStrength ? 'border-emerald-500/5' : 'border-rose-500/5'}`} data-testid={`${type}-theme-${index}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 flex-1">
          <span className="text-sm text-white/70">{theme.theme}</span>
          <span className={`px-2 py-0.5 text-[10px] rounded-full ${freqColors[theme.frequency] || freqColors.moderate}`}>{theme.frequency}</span>
          {!isStrength && theme.severity && (
            <span className={`px-2 py-0.5 text-[10px] rounded-full ${sevColors[theme.severity] || sevColors.minor}`}>
              {theme.severity === 'deal_breaker' ? 'deal breaker' : theme.severity}
            </span>
          )}
        </div>
        {theme.evidence?.length > 0 && (
          <button onClick={() => setExpanded(!expanded)} className="text-white/20 hover:text-white/40 ml-2">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
      </div>
      {expanded && theme.evidence?.length > 0 && (
        <div className="mt-3 space-y-2 pl-3 border-l border-white/[0.04]">
          {theme.evidence.map((q, qi) => (
            <p key={qi} className="text-xs text-white/30 italic">&ldquo;{q}&rdquo;</p>
          ))}
        </div>
      )}
    </AntigravityCard>
  );
};

const MetricBlock = ({ label, value, color }) => {
  const colorMap = {
    emerald: 'text-emerald-400',
    rose: 'text-rose-400',
    blue: 'text-blue-400',
    amber: 'text-amber-400',
  };
  return (
    <div className="text-center">
      <p className={`text-2xl font-heading font-semibold ${colorMap[color] || 'text-white/70'}`}>{value}</p>
      <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider mt-1">{label}</p>
    </div>
  );
};
