import React, { useState } from 'react';
import { Newspaper, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';

export const PressMediaTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.pressMedia;
  const latest = data?.latest;
  const [narrativeFilter, setNarrativeFilter] = useState('all');

  const articleCount = latest?.articles?.length || 0;
  const sourceCount = latest?.media_sources?.length || 0;

  return (
    <div data-testid="press-media-tab">
      <ModuleHeader title="Press & Media" moduleKey="pressMedia" status={status} refreshDueInDays={data?.refresh_due_in_days} onRun={() => runModule('pressMedia')} error={error}>
        {articleCount > 0 && (
          <span className="text-white/20 text-xs font-mono">{articleCount} articles from {sourceCount} sources</span>
        )}
      </ModuleHeader>

      {status === STATUS.RUNNING && <ModuleRunning message="Scanning press coverage..." moduleKey="pressMedia" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={Newspaper} title="Press & Media not scanned" onGenerate={() => runModule('pressMedia')} />
      )}

      {latest && (
        <>
          {/* Press Stats */}
          {(articleCount > 0 || latest.narratives?.length > 0) && (
            <AntigravityCard className="p-5 mb-8" data-testid="press-stats">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-heading font-semibold text-white/70">{articleCount}</p>
                  <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider mt-1">Articles</p>
                </div>
                <div>
                  <p className="text-2xl font-heading font-semibold text-white/70">{sourceCount}</p>
                  <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider mt-1">Sources</p>
                </div>
                <div>
                  <p className="text-2xl font-heading font-semibold text-white/70">{latest.narratives?.length || 0}</p>
                  <p className="text-[10px] font-mono text-white/25 uppercase tracking-wider mt-1">Narratives</p>
                </div>
              </div>
            </AntigravityCard>
          )}

          {/* Coverage Summary */}
          {latest.coverage_summary?.length > 0 && (
            <section className="mb-8">
              <SectionLabel>Coverage Summary</SectionLabel>
              <AntigravityCard className="p-5">
                <ol className="space-y-2">
                  {(latest.coverage_summary || []).map((point, i) => (
                    <li key={i} className="flex gap-3 text-white/60 text-sm">
                      <span className="text-white/20 font-mono text-xs shrink-0 mt-0.5">{i + 1}.</span>
                      <CleanText>{point}</CleanText>
                    </li>
                  ))}
                </ol>
              </AntigravityCard>
            </section>
          )}

          {/* Narratives */}
          {latest.narratives?.length > 0 && (
            <section className="mb-10">
              <SectionLabel count={latest.narratives.length}>Media Narratives</SectionLabel>
              <div className="flex flex-wrap gap-2 mb-6">
                <button
                  onClick={() => setNarrativeFilter('all')}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${narrativeFilter === 'all' ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30 hover:text-white/50'}`}
                >All ({latest.narratives.length})</button>
                {[...new Set((latest.narratives || []).map(n => n.type).filter(Boolean))].map(type => (
                  <button
                    key={type}
                    onClick={() => setNarrativeFilter(type)}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${narrativeFilter === type ? 'bg-white/10 border-white/20 text-white' : 'bg-white/[0.03] border-white/[0.06] text-white/30 hover:text-white/50'}`}
                  >{type} ({(latest.narratives || []).filter(n => n.type === type).length})</button>
                ))}
              </div>
              <StaggerContainer className="grid md:grid-cols-2 gap-4">
                {(latest.narratives || [])
                  .filter(n => narrativeFilter === 'all' || n.type === narrativeFilter)
                  .map((narrative, i) => (
                  <StaggerItem key={i}>
                    <NarrativeCard narrative={narrative} index={i} />
                  </StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Articles */}
          {latest.articles?.length > 0 && (
            <section className="mb-10">
              <SectionLabel count={latest.articles.length}>Articles</SectionLabel>
              <StaggerContainer className="space-y-2">
                {(latest.articles || []).map((article, i) => (
                  <StaggerItem key={i}>
                    <ArticleRow article={article} index={i} />
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

const sentimentColors = {
  positive: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15',
  negative: 'text-rose-400 bg-rose-500/10 border-rose-500/15',
  neutral: 'text-white/40 bg-white/5 border-white/10',
  mixed: 'text-amber-400 bg-amber-500/10 border-amber-500/15',
};

const NarrativeCard = ({ narrative, index }) => (
  <AntigravityCard className="p-5" data-testid={`narrative-${index}`}>
    <h3 className="font-medium text-white text-sm mb-2">{narrative.label}</h3>
    <div className="flex flex-wrap gap-1.5 mb-3">
      {narrative.sentiment && (
        <span className={`text-[10px] px-2 py-0.5 rounded-full border uppercase ${sentimentColors[narrative.sentiment] || sentimentColors.neutral}`}>
          {narrative.sentiment}
        </span>
      )}
      {narrative.type && (
        <span className="text-[10px] px-2 py-0.5 rounded-full border bg-white/[0.03] border-white/[0.06] text-white/30 uppercase">{narrative.type}</span>
      )}
      {narrative.frequency && (
        <span className="text-[10px] px-2 py-0.5 rounded-full border bg-white/[0.03] border-white/[0.06] text-white/20 uppercase">{narrative.frequency}</span>
      )}
    </div>
    {narrative.quote && (
      <p className="text-white/40 text-sm italic">&ldquo;<CleanText>{narrative.quote}</CleanText>&rdquo;</p>
    )}
    {narrative.source_count && <p className="text-white/15 text-xs font-mono mt-2">source {narrative.source_count}</p>}
  </AntigravityCard>
);

const ArticleRow = ({ article, index }) => (
  <AntigravityCard className="p-4" hover data-testid={`article-${index}`}>
    <div className="flex items-start justify-between">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          {article.source_domain && <span className="text-[10px] font-mono text-white/20 bg-white/[0.04] px-2 py-0.5 rounded">{article.source_domain}</span>}
          {article.sentiment && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full border ${sentimentColors[article.sentiment] || sentimentColors.neutral}`}>
              {article.sentiment}
            </span>
          )}
        </div>
        <p className="text-white/70 text-sm"><CleanText>{article.title}</CleanText></p>
        {article.key_takeaway && <p className="text-white/30 text-xs mt-1"><CleanText>{article.key_takeaway}</CleanText></p>}
      </div>
      {article.url && (
        <a href={article.url} target="_blank" rel="noopener noreferrer" className="text-white/15 hover:text-white/40 ml-3">
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      )}
    </div>
  </AntigravityCard>
);
