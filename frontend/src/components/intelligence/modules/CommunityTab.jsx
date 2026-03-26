import React, { useState } from 'react';
import { UsersRound, ExternalLink, ChevronDown, ChevronUp, MessageCircle } from 'lucide-react';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';

export const CommunityTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.community;
  const latest = data?.latest;
  const [themeFilter, setThemeFilter] = useState('all');

  return (
    <div data-testid="community-tab">
      <ModuleHeader title="Community" moduleKey="community" status={status} refreshDueInDays={data?.refresh_due_in_days} onRun={() => runModule('community')} error={error} />

      {status === STATUS.RUNNING && <ModuleRunning message="Scanning community discussions..." moduleKey="community" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={UsersRound} title="Community analysis not run" onGenerate={() => runModule('community')} />
      )}

      {latest && (
        <>
          {latest.threads?.length > 0 ? (
            <>
              {/* Themes */}
              {latest.themes?.length > 0 && (
                <section className="mb-8">
                  <SectionLabel count={latest.themes.length}>Discussion Themes</SectionLabel>
                  <div className="flex flex-wrap gap-2 mb-6">
                    <button
                      onClick={() => setThemeFilter('all')}
                      className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${themeFilter === 'all' ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30 hover:text-white/50'}`}
                    >All ({latest.threads.length})</button>
                    {latest.themes.map((theme, i) => (
                      <button
                        key={i}
                        onClick={() => setThemeFilter(theme.label)}
                        className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${themeFilter === theme.label ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30 hover:text-white/50'}`}
                      >{theme.label} ({theme.thread_count || 0})</button>
                    ))}
                  </div>
                </section>
              )}

              {/* Threads */}
              <section className="mb-10">
                <SectionLabel count={latest.threads.length}>Threads</SectionLabel>
                <StaggerContainer className="space-y-2">
                  {latest.threads
                    .filter(t => themeFilter === 'all' || t.theme === themeFilter)
                    .map((thread, i) => (
                    <StaggerItem key={i}>
                      <ThreadRow thread={thread} index={i} />
                    </StaggerItem>
                  ))}
                </StaggerContainer>
              </section>

              {/* Language Bank */}
              {latest.language_bank?.phrases?.length > 0 && (
                <section className="mb-10">
                  <SectionLabel count={latest.language_bank?.phrases?.length}>Language Bank</SectionLabel>
                  <div className="flex flex-wrap gap-2">
                    {(latest.language_bank?.phrases || []).map((phrase, i) => (
                      <span key={i} className="text-xs px-3 py-1.5 bg-white/[0.04] border border-white/[0.06] text-white/50 rounded-lg">{phrase}</span>
                    ))}
                  </div>
                </section>
              )}
            </>
          ) : (
            <EmptyCommunity />
          )}
        </>
      )}
    </div>
  );
};

const EmptyCommunity = () => (
  <AntigravityCard className="p-8 text-center mb-10">
    <UsersRound className="w-8 h-8 text-white/10 mx-auto mb-3" strokeWidth={1.5} />
    <p className="text-white/40 text-sm mb-2">No community discussions found</p>
    <p className="text-white/20 text-xs max-w-md mx-auto">
      No relevant forum threads (Reddit, Quora, etc.) were found for this brand or category. This is common for niche or local brands.
    </p>
  </AntigravityCard>
);

const ThreadRow = ({ thread, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <AntigravityCard className="p-4" hover data-testid={`thread-${index}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {thread.domain && <span className="text-[10px] font-mono text-white/20 bg-white/[0.04] px-2 py-0.5 rounded">{thread.domain}</span>}
            {thread.theme && <span className="text-[10px] text-white/15">{thread.theme}</span>}
          </div>
          <p className="text-white/70 text-sm truncate"><CleanText>{thread.title || thread.query}</CleanText></p>
          {thread.takeaway && <p className="text-white/30 text-xs mt-1"><CleanText>{thread.takeaway}</CleanText></p>}
        </div>
        <div className="flex items-center gap-2 ml-3 shrink-0">
          {thread.url && (
            <a href={thread.url} target="_blank" rel="noopener noreferrer" className="text-white/15 hover:text-white/40">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          {thread.top_quotes?.length > 0 && (
            <button onClick={() => setExpanded(!expanded)} className="text-white/15 hover:text-white/40">
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>
      {expanded && thread.top_quotes?.length > 0 && (
        <div className="mt-3 space-y-2 pl-3 border-l border-white/[0.04]">
          {thread.top_quotes.map((q, qi) => (
            <p key={qi} className="text-xs text-white/30 italic">&ldquo;{q}&rdquo;</p>
          ))}
        </div>
      )}
    </AntigravityCard>
  );
};
