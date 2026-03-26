import React from 'react';
import { motion } from 'framer-motion';
import { Calendar, Clock, Check, Globe, Sparkles } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceDot } from 'recharts';
import { useIntel, STATUS } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';

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

const MomentCard = ({ moment, index }) => {
  const demandColors = {
    high: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
    medium: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
  };
  const demandColor = demandColors[moment.demand] || demandColors[moment.demand_level] || 'bg-white/5 text-white/40 border-white/10';
  const activeMonths = parseActiveMonths(moment.window || moment.time_window || '');

  return (
    <AntigravityCard className="p-5" data-testid={`moment-card-${index}`}>
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-heading text-base font-medium text-white">{moment.moment || moment.name}</h3>
        <span className={`px-2 py-0.5 text-[10px] uppercase tracking-wider border rounded-md shrink-0 ml-3 ${demandColor}`}>
          {moment.demand || moment.demand_level}
        </span>
      </div>

      {/* Month ribbon */}
      <div className="flex gap-0.5 mb-4">
        {MONTH_LABELS.map((label, mIdx) => (
          <div key={mIdx} className={`flex-1 text-center py-1 text-[9px] font-mono rounded-sm ${
            activeMonths.has(mIdx) ? 'bg-white/15 text-white font-medium' : 'bg-white/[0.03] text-white/20'
          }`}>{label}</div>
        ))}
      </div>

      {moment.lead_time && (
        <div className="mb-3 flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-white/25" />
          <span className="text-xs text-white/30 font-mono">Lead: {moment.lead_time}</span>
        </div>
      )}

      {moment.who && (
        <div className="mb-3">
          <span className="text-[10px] text-blue-400 uppercase tracking-wider font-mono">Who</span>
          <p className="text-white/60 text-sm mt-1"><CleanText>{moment.who}</CleanText></p>
        </div>
      )}

      {(moment.why_now || moment.why_people_buy) && (
        <div className="mb-3">
          <span className="text-[10px] text-amber-400 uppercase tracking-wider font-mono">Why Now</span>
          <p className="text-white/60 text-sm mt-1"><CleanText>{moment.why_now || moment.why_people_buy}</CleanText></p>
        </div>
      )}

      {(moment.buy_triggers || moment.purchase_triggers)?.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] text-emerald-400 uppercase tracking-wider font-mono">Buy Triggers</span>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {(moment.buy_triggers || moment.purchase_triggers).map((t, j) => (
              <span key={j} className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/15 text-emerald-300 text-xs rounded-md">
                <CleanText>{t}</CleanText>
              </span>
            ))}
          </div>
        </div>
      )}

      {moment.must_answer && (
        <div className="mb-3">
          <span className="text-[10px] text-rose-400 uppercase tracking-wider font-mono">Must Answer</span>
          <p className="text-white/60 text-sm mt-1 italic">&ldquo;<CleanText>{moment.must_answer}</CleanText>&rdquo;</p>
        </div>
      )}

      {moment.best_channels?.length > 0 && (
        <div className="mt-auto pt-3 border-t border-white/[0.04]">
          <span className="text-[10px] text-white/20 font-mono">Channels</span>
          <div className="flex gap-1.5 mt-1.5 flex-wrap">
            {(moment.best_channels || []).map((ch, j) => (
              <span key={j} className="text-xs px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] text-white/40 rounded-md">{ch}</span>
            ))}
          </div>
        </div>
      )}
    </AntigravityCard>
  );
};

const MONTH_FULL = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

const DemandTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-[#1a1a1a] border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-xs text-white/70 font-medium mb-1">{d.month}</p>
      {d.moments.length > 0 ? (
        d.moments.map((m, i) => <p key={i} className="text-[10px] text-white/50">{m}</p>)
      ) : (
        <p className="text-[10px] text-white/30">No key moments</p>
      )}
    </div>
  );
};

const YearHeatmap = ({ moments }) => {
  const monthActivity = new Array(12).fill(0);
  const monthMoments = new Array(12).fill(null).map(() => []);

  moments.forEach(m => {
    const active = parseActiveMonths(m.window || m.time_window || '');
    active.forEach(idx => {
      monthActivity[idx] += (m.demand === 'high' ? 3 : m.demand === 'medium' ? 2 : 1);
      monthMoments[idx].push(m.moment || m.name);
    });
  });
  const maxActivity = Math.max(...monthActivity, 1);
  const currentMonth = new Date().getMonth();

  const chartData = MONTH_FULL.map((month, idx) => ({
    month,
    demand: monthActivity[idx],
    intensity: monthActivity[idx] / maxActivity,
    moments: monthMoments[idx],
    isCurrent: idx === currentMonth,
  }));

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={140}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="demandGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="month"
            axisLine={false}
            tickLine={false}
            tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 10, fontFamily: 'monospace' }}
          />
          <YAxis hide domain={[0, 'dataMax + 1']} />
          <Tooltip content={<DemandTooltip />} cursor={false} />
          <ReferenceLine x={MONTH_FULL[currentMonth]} stroke="rgba(16,185,129,0.3)" strokeDasharray="3 3" />
          <Area
            type="monotone"
            dataKey="demand"
            stroke="#10b981"
            strokeWidth={2}
            fill="url(#demandGradient)"
            dot={(props) => {
              const { cx, cy, payload } = props;
              if (payload.moments.length === 0) return null;
              return (
                <circle
                  key={props.index}
                  cx={cx}
                  cy={cy}
                  r={payload.isCurrent ? 5 : 3.5}
                  fill={payload.isCurrent ? '#10b981' : '#0A0A0A'}
                  stroke="#10b981"
                  strokeWidth={payload.isCurrent ? 2.5 : 1.5}
                />
              );
            }}
            animationDuration={1200}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 pt-1">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-full border-2 border-emerald-500 bg-[#0A0A0A]" />
          <span className="text-[9px] text-white/20 font-mono">Key moment</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-6 h-[2px] bg-emerald-500/30" style={{ backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(16,185,129,0.3) 3px, rgba(16,185,129,0.3) 6px)' }} />
          <span className="text-[9px] text-white/20 font-mono">Now ({MONTH_FULL[currentMonth]})</span>
        </div>
      </div>
    </div>
  );
};

export const SeasonalityTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.seasonality;
  const latest = data?.latest;

  return (
    <div data-testid="seasonality-tab">
      <ModuleHeader title="Seasonality" moduleKey="seasonality" status={status} refreshDueInDays={data?.refresh_due_in_days} onRun={() => runModule('seasonality')} error={error} />

      {status === STATUS.RUNNING && <ModuleRunning message="Analyzing seasonal patterns..." moduleKey="seasonality" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={Calendar} title="Seasonality not analyzed yet" description="Discover key moments, buying triggers, and seasonal patterns for your market." onGenerate={() => runModule('seasonality')} />
      )}

      {latest && (
        <>
          {/* Full-Year Calendar Heatmap */}
          {latest.key_moments?.length > 0 && (
            <section className="mb-10">
              <SectionLabel>Annual Demand Map</SectionLabel>
              <AntigravityCard className="p-5">
                <YearHeatmap moments={latest.key_moments} />
              </AntigravityCard>
            </section>
          )}

          {/* Key Moments */}
          {latest.key_moments?.length > 0 && (
            <section className="mb-10">
              <SectionLabel count={latest.key_moments.length}>Buying Moments</SectionLabel>
              <p className="text-white/20 text-xs mb-6">When specific people have specific reasons to buy NOW</p>
              <StaggerContainer className="grid md:grid-cols-2 gap-4">
                {latest.key_moments.map((moment, i) => (
                  <StaggerItem key={i}><MomentCard moment={moment} index={i} /></StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Evergreen + Weekly */}
          <div className="grid md:grid-cols-2 gap-4 mb-10">
            {latest.evergreen_demand?.length > 0 && (
              <AntigravityCard className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="w-4 h-4 text-white/40" strokeWidth={1.5} />
                  <span className="text-[11px] font-mono text-white/30 uppercase tracking-[0.2em]">Evergreen Demand</span>
                </div>
                <ul className="space-y-2">
                  {latest.evergreen_demand.map((item, i) => (
                    <li key={i} className="flex items-start gap-2 text-white/60 text-sm">
                      <Check className="w-3.5 h-3.5 text-emerald-400/50 mt-0.5 shrink-0" />
                      <CleanText>{item}</CleanText>
                    </li>
                  ))}
                </ul>
              </AntigravityCard>
            )}

            {latest.weekly_patterns && (latest.weekly_patterns.peak_days?.length > 0 || latest.weekly_patterns.why) && (
              <AntigravityCard className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-4 h-4 text-white/40" strokeWidth={1.5} />
                  <span className="text-[11px] font-mono text-white/30 uppercase tracking-[0.2em]">Weekly Patterns</span>
                </div>
                {latest.weekly_patterns.peak_days?.length > 0 && (
                  <div className="mb-3">
                    <div className="flex gap-2 mt-1.5">
                      {latest.weekly_patterns.peak_days.map((day, i) => (
                        <span key={i} className="px-3 py-1 bg-blue-500/10 border border-blue-500/15 text-blue-300 text-sm rounded-md">{day}</span>
                      ))}
                    </div>
                  </div>
                )}
                {latest.weekly_patterns.why && <p className="text-white/40 text-sm mt-2"><CleanText>{latest.weekly_patterns.why}</CleanText></p>}
              </AntigravityCard>
            )}
          </div>

          {/* Local Insights */}
          {latest.local_insights?.length > 0 && (
            <section className="mb-10">
              <AntigravityCard className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Globe className="w-4 h-4 text-white/40" strokeWidth={1.5} />
                  <span className="text-[11px] font-mono text-white/30 uppercase tracking-[0.2em]">Local Insights</span>
                </div>
                <ul className="space-y-2">
                  {latest.local_insights.map((note, i) => (
                    <li key={i} className="text-white/50 text-sm flex items-start gap-2">
                      <Globe className="w-3.5 h-3.5 text-white/20 mt-0.5 shrink-0" />
                      <CleanText>{note}</CleanText>
                    </li>
                  ))}
                </ul>
              </AntigravityCard>
            </section>
          )}
        </>
      )}
    </div>
  );
};
