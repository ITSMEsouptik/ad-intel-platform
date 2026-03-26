import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Search, DollarSign, Star, Clock, GitCompare, Copy, Check,
  ExternalLink, Hash
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const BUCKET_ICONS = { price: DollarSign, trust: Star, urgency: Clock, comparison: GitCompare, general: Search };
const BUCKET_COLORS = {
  price: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/15',
  trust: 'text-amber-400 bg-amber-500/10 border-amber-500/15',
  urgency: 'text-rose-400 bg-rose-500/10 border-rose-500/15',
  comparison: 'text-blue-400 bg-blue-500/10 border-blue-500/15',
  general: 'text-white/50 bg-white/5 border-white/10',
};

export const SearchDemandTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.searchIntent;
  const latest = data?.latest;
  const [copiedQuery, setCopiedQuery] = useState(null);

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedQuery(index);
    setTimeout(() => setCopiedQuery(null), 2000);
  };

  const delta = latest?.delta?.new_queries_count > 0
    ? { count: latest.delta.new_queries_count, label: 'new queries' }
    : null;

  // Enrich queries with bucket info from intent_buckets map
  const intentBuckets = latest?.intent_buckets || {};
  const queryBucketMap = {};
  Object.entries(intentBuckets).forEach(([bucket, queries]) => {
    (queries || []).forEach(q => { queryBucketMap[typeof q === 'string' ? q : q.query || q] = bucket; });
  });
  const enrichedTopQueries = (latest?.top_10_queries || []).map(q => {
    const text = typeof q === 'string' ? q : q.query || String(q);
    return { query: text, bucket: queryBucketMap[text] || 'general' };
  });
  const enrichedAdKeywords = (latest?.ad_keyword_queries || []).map(q => {
    const text = typeof q === 'string' ? q : q.query || String(q);
    return { query: text, bucket: queryBucketMap[text] || 'general' };
  });

  return (
    <div data-testid="search-demand-tab">
      <ModuleHeader
        title="Search Demand"
        moduleKey="searchIntent"
        status={status}
        refreshDueInDays={data?.refresh_due_in_days}
        delta={delta}
        onRun={() => runModule('searchIntent')}
        error={error}
      />

      {status === STATUS.RUNNING && <ModuleRunning message="Mining search intent..." submessage="Analyzing Google Suggest + AI curation" moduleKey="searchIntent" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={Search} title="Search Demand not generated yet" onGenerate={() => runModule('searchIntent')} />
      )}

      {latest && (
        <>
          {/* Intent Distribution */}
          {enrichedAdKeywords.length > 0 && (
            <section className="mb-8">
              <IntentDistribution queries={enrichedAdKeywords} />
            </section>
          )}

          {/* Top 10 Queries */}
          {enrichedTopQueries.length > 0 && (
            <section className="mb-10">
              <SectionLabel count={enrichedTopQueries.length}>Top Queries</SectionLabel>

              {/* Horizontal bar chart */}
              <AntigravityCard className="p-5 mb-4" data-testid="queries-chart">
                <ResponsiveContainer width="100%" height={Math.max(200, enrichedTopQueries.length * 32)}>
                  <BarChart
                    data={enrichedTopQueries.map((q, i) => ({
                      query: q.query,
                      rank: enrichedTopQueries.length - i,
                      bucket: q.bucket,
                    }))}
                    layout="vertical"
                    margin={{ top: 0, right: 12, left: 0, bottom: 0 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis
                      dataKey="query"
                      type="category"
                      axisLine={false}
                      tickLine={false}
                      width={200}
                      tick={{ fill: 'rgba(255,255,255,0.45)', fontSize: 11, fontFamily: 'monospace' }}
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload;
                        return (
                          <div className="bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2">
                            <p className="text-xs text-white/70">{d.query}</p>
                            <p className="text-[10px] text-white/30 font-mono capitalize">Intent: {d.bucket}</p>
                          </div>
                        );
                      }}
                    />
                    <Bar dataKey="rank" radius={[0, 4, 4, 0]} animationDuration={800}>
                      {enrichedTopQueries.map((q, i) => {
                        const colors = { price: '#10b981', trust: '#f59e0b', urgency: '#f43f5e', comparison: '#3b82f6', general: 'rgba(255,255,255,0.2)' };
                        return <Cell key={i} fill={colors[q.bucket] || colors.general} fillOpacity={0.6} />;
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </AntigravityCard>

              {/* Query list with actions */}
              <StaggerContainer className="space-y-1.5">
                {enrichedTopQueries.map((q, i) => (
                  <StaggerItem key={i}>
                    <div className="flex items-center gap-3 group px-4 py-2.5 rounded-lg hover:bg-white/[0.03] transition-colors duration-200" data-testid={`query-${i}`}>
                      <span className="text-white/15 font-mono text-xs w-5 text-right">{i + 1}</span>
                      <span className="flex-1 text-white/70 text-sm"><CleanText>{q.query || q}</CleanText></span>
                      {q.bucket && (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border font-mono ${BUCKET_COLORS[q.bucket] || BUCKET_COLORS.general}`}>
                          {q.bucket}
                        </span>
                      )}
                      <button
                        onClick={() => copyToClipboard(q.query || q, i)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-white/30 hover:text-white"
                      >
                        {copiedQuery === i ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                      <button
                        onClick={() => window.open(`https://www.google.com/search?q=${encodeURIComponent(q.query || q)}`, '_blank')}
                        className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 text-white/30 hover:text-white"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Ad Keywords by bucket */}
          {enrichedAdKeywords.length > 0 && (
            <section className="mb-10">
              <SectionLabel count={enrichedAdKeywords.length}>Ad Keywords</SectionLabel>
              <AdKeywordBuckets queries={enrichedAdKeywords} />
            </section>
          )}

          {/* Forum Queries */}
          {latest.forum_queries && (latest.forum_queries.reddit?.length > 0 || latest.forum_queries.quora?.length > 0) && (
            <section className="mb-10" data-testid="forum-queries-section">
              <SectionLabel count={(latest.forum_queries.reddit?.length || 0) + (latest.forum_queries.quora?.length || 0)}>Forum Queries</SectionLabel>
              <Tabs defaultValue={latest.forum_queries.reddit?.length > 0 ? "reddit" : "quora"} className="w-full">
                <TabsList className="bg-transparent border-b border-white/[0.06] w-full justify-start rounded-none h-auto p-0 mb-4 gap-0">
                  {latest.forum_queries.reddit?.length > 0 && (
                    <TabsTrigger value="reddit" className="data-[state=active]:bg-white/[0.06] data-[state=active]:border-b-2 data-[state=active]:border-orange-400/50 rounded-none px-4 py-2.5 text-xs uppercase tracking-wider text-white/30 data-[state=active]:text-orange-400">
                      Reddit ({latest.forum_queries.reddit?.length})
                    </TabsTrigger>
                  )}
                  {latest.forum_queries.quora?.length > 0 && (
                    <TabsTrigger value="quora" className="data-[state=active]:bg-white/[0.06] data-[state=active]:border-b-2 data-[state=active]:border-red-400/50 rounded-none px-4 py-2.5 text-xs uppercase tracking-wider text-white/30 data-[state=active]:text-red-400">
                      Quora ({latest.forum_queries.quora?.length})
                    </TabsTrigger>
                  )}
                </TabsList>
                {latest.forum_queries.reddit?.length > 0 && (
                  <TabsContent value="reddit" className="mt-0">
                    <div className="flex flex-wrap gap-2">
                      {latest.forum_queries.reddit.map((q, i) => (
                        <a key={i} href={`https://www.google.com/search?q=${encodeURIComponent(typeof q === 'string' ? q : q.query || q)}`} target="_blank" rel="noopener noreferrer"
                           className="text-xs px-3 py-1.5 bg-orange-500/[0.06] border border-orange-500/10 text-white/50 rounded-lg hover:bg-orange-500/[0.12] hover:text-white/70 transition-all flex items-center gap-1.5">
                          {(typeof q === 'string' ? q : q.query || q).replace('site:reddit.com ', '')}
                          <ExternalLink className="w-3 h-3 text-white/20" />
                        </a>
                      ))}
                    </div>
                  </TabsContent>
                )}
                {latest.forum_queries.quora?.length > 0 && (
                  <TabsContent value="quora" className="mt-0">
                    <div className="flex flex-wrap gap-2">
                      {latest.forum_queries.quora.map((q, i) => (
                        <a key={i} href={`https://www.google.com/search?q=${encodeURIComponent(typeof q === 'string' ? q : q.query || q)}`} target="_blank" rel="noopener noreferrer"
                           className="text-xs px-3 py-1.5 bg-red-500/[0.06] border border-red-500/10 text-white/50 rounded-lg hover:bg-red-500/[0.12] hover:text-white/70 transition-all flex items-center gap-1.5">
                          {(typeof q === 'string' ? q : q.query || q).replace('site:quora.com ', '')}
                          <ExternalLink className="w-3 h-3 text-white/20" />
                        </a>
                      ))}
                    </div>
                  </TabsContent>
                )}
              </Tabs>
            </section>
          )}
        </>
      )}
    </div>
  );
};

const AdKeywordBuckets = ({ queries }) => {
  const buckets = {};
  queries.forEach(q => {
    const b = q.bucket || 'general';
    if (!buckets[b]) buckets[b] = [];
    buckets[b].push(q);
  });

  const bucketKeys = Object.keys(buckets);

  return (
    <Tabs defaultValue={bucketKeys[0] || 'general'} className="w-full">
      <TabsList className="bg-transparent border-b border-white/[0.06] w-full justify-start rounded-none h-auto p-0 mb-6 gap-0">
        {bucketKeys.map(bucket => {
          const Icon = BUCKET_ICONS[bucket] || Search;
          return (
            <TabsTrigger
              key={bucket}
              value={bucket}
              className="data-[state=active]:bg-white/[0.06] data-[state=active]:border-b-2 data-[state=active]:border-white/30 rounded-none px-4 py-2.5 text-xs uppercase tracking-wider text-white/30 data-[state=active]:text-white/70"
            >
              <Icon className="w-3.5 h-3.5 mr-1.5" />
              {bucket} ({buckets[bucket].length})
            </TabsTrigger>
          );
        })}
      </TabsList>
      {bucketKeys.map(bucket => (
        <TabsContent key={bucket} value={bucket} className="mt-0">
          <div className="flex flex-wrap gap-2">
            {buckets[bucket].map((q, i) => (
              <span key={i} className={`text-xs px-3 py-1.5 rounded-lg border ${BUCKET_COLORS[bucket] || BUCKET_COLORS.general}`}>
                {q.query || q}
              </span>
            ))}
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
};

const BUCKET_BAR_COLORS = {
  price: 'bg-emerald-500/60',
  trust: 'bg-amber-500/60',
  urgency: 'bg-rose-500/60',
  comparison: 'bg-blue-500/60',
  general: 'bg-white/20',
};

const IntentDistribution = ({ queries }) => {
  const buckets = {};
  queries.forEach(q => {
    const b = q.bucket || 'general';
    buckets[b] = (buckets[b] || 0) + 1;
  });
  const total = queries.length;
  const entries = Object.entries(buckets).sort((a, b) => b[1] - a[1]);

  return (
    <AntigravityCard className="p-5" data-testid="intent-distribution">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[11px] font-mono text-white/30 uppercase tracking-[0.2em]">Intent Distribution</span>
        <span className="text-[10px] font-mono text-white/20">{total} keywords</span>
      </div>
      {/* Stacked bar */}
      <div className="flex rounded-full h-2 overflow-hidden mb-4 bg-white/[0.03]">
        {entries.map(([bucket, count]) => (
          <motion.div
            key={bucket}
            initial={{ width: 0 }}
            animate={{ width: `${(count / total) * 100}%` }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
            className={`${BUCKET_BAR_COLORS[bucket] || BUCKET_BAR_COLORS.general}`}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        {entries.map(([bucket, count]) => {
          const Icon = BUCKET_ICONS[bucket] || Search;
          return (
            <div key={bucket} className="flex items-center gap-1.5">
              <Icon className="w-3 h-3 text-white/25" />
              <span className="text-[10px] text-white/40 capitalize">{bucket}</span>
              <span className="text-[10px] text-white/20 font-mono">{count}</span>
              <span className="text-[9px] text-white/10 font-mono">({Math.round((count / total) * 100)}%)</span>
            </div>
          );
        })}
      </div>
    </AntigravityCard>
  );
};

