import React from 'react';
import { Users, Search, Check } from 'lucide-react';
import { useIntel } from '../IntelligenceContext';
import { ModuleHeader, ModuleRunning, ModuleEmpty } from '../ui/ModuleShell';
import { AntigravityCard, StaggerContainer, StaggerItem, SectionLabel, CleanText } from '../ui/Cards';
import { STATUS } from '../IntelligenceContext';

const SegmentCard = ({ segment, index, total }) => {
  const name = segment.segment_name || segment.name;
  const jtbd = segment.jtbd || segment.job_to_be_done;
  const motives = segment.core_motives || segment.motivations || [];
  const pains = segment.top_pains || segment.pains || [];
  const objections = segment.top_objections || segment.objections || [];
  const proof = segment.best_proof || [];
  const riskReducers = segment.risk_reducers || [];
  const offerItems = segment.best_offer_items || [];
  const channels = segment.best_channel_focus || segment.best_channels || [];

  const sections = [
    { label: 'Motives', items: motives, color: 'emerald', prefix: '+' },
    { label: 'Pains', items: pains, color: 'red', prefix: '\u2013' },
    { label: 'Objections', items: objections, color: 'amber', prefix: '?' },
  ];

  return (
    <AntigravityCard className="p-5 flex flex-col" data-testid={`segment-card-${index}`}>
      <div className="flex items-start gap-3 mb-3">
        <div className="w-7 h-7 rounded-lg bg-white/[0.06] border border-white/[0.08] flex items-center justify-center shrink-0">
          <span className="text-[11px] font-mono text-white/40">{index + 1}</span>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-heading text-base font-medium text-white">{name}</h3>
          {jtbd && <p className="text-white/40 text-sm mt-1 italic leading-relaxed"><CleanText>{jtbd}</CleanText></p>}
        </div>
      </div>

      {sections.map(({ label, items, color, prefix }) => items.length > 0 && (
        <div key={label} className="mb-3">
          <span className={`text-[10px] text-${color}-400 uppercase tracking-wider font-mono`}>{label}</span>
          <ul className="mt-1 space-y-1">
            {items.map((item, j) => (
              <li key={j} className="text-white/60 text-sm flex gap-2">
                <span className={`text-${color}-400/50`}>{prefix}</span>
                <CleanText>{item}</CleanText>
              </li>
            ))}
          </ul>
        </div>
      ))}

      {proof.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] text-blue-400 uppercase tracking-wider font-mono">Proof</span>
          <ul className="mt-1 space-y-1">
            {proof.map((p, j) => (
              <li key={j} className="text-white/60 text-sm flex gap-2">
                <Check className="w-3.5 h-3.5 text-blue-400/50 mt-0.5 shrink-0" />
                <CleanText>{p}</CleanText>
              </li>
            ))}
          </ul>
        </div>
      )}

      {riskReducers.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] text-cyan-400 uppercase tracking-wider font-mono">Risk Reducers</span>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {riskReducers.map((r, j) => (
              <span key={j} className="px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/15 text-cyan-300 text-xs rounded-md">
                <CleanText>{r}</CleanText>
              </span>
            ))}
          </div>
        </div>
      )}

      {offerItems.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] text-violet-400 uppercase tracking-wider font-mono">Offer Match</span>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {offerItems.map((o, j) => (
              <span key={j} className="px-2 py-0.5 bg-violet-500/10 border border-violet-500/15 text-violet-300 text-xs rounded-md">
                <CleanText>{o}</CleanText>
              </span>
            ))}
          </div>
        </div>
      )}

      {channels.length > 0 && (
        <div className="mt-auto pt-3 border-t border-white/[0.04]">
          <span className="text-[10px] text-white/20 font-mono">Best channels</span>
          <div className="flex gap-1.5 mt-1.5 flex-wrap">
            {channels.map((ch, j) => (
              <span key={j} className="text-xs px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] text-white/40 rounded-md">{ch}</span>
            ))}
          </div>
        </div>
      )}
    </AntigravityCard>
  );
};

export const CustomerIntelTab = () => {
  const { modules, runModule } = useIntel();
  const { data, status, error } = modules.customerIntel;
  const latest = data?.latest;

  const delta = latest?.delta?.new_segments_count > 0
    ? { count: latest.delta.new_segments_count, label: 'new segments' }
    : null;

  return (
    <div data-testid="customer-intel-tab">
      <ModuleHeader
        title="Audience"
        moduleKey="customerIntel"
        status={status}
        refreshDueInDays={data?.refresh_due_in_days}
        delta={delta}
        onRun={() => runModule('customerIntel')}
        error={error}
      />

      {status === STATUS.RUNNING && <ModuleRunning message="Analyzing customer signals..." moduleKey="customerIntel" />}
      {status === STATUS.NOT_RUN && !latest && (
        <ModuleEmpty icon={Users} title="Customer Intel not generated yet" onGenerate={() => runModule('customerIntel')} />
      )}

      {latest && (
        <>
          {/* Summary */}
          {latest.summary_bullets?.length > 0 && (
            <AntigravityCard className="p-6 mb-8">
              <ul className="space-y-3">
                {latest.summary_bullets.map((bullet, i) => (
                  <li key={i} className="flex items-start gap-3 text-white/70 text-sm">
                    <span className="text-emerald-400/60 mt-0.5">&bull;</span>
                    <CleanText>{bullet}</CleanText>
                  </li>
                ))}
              </ul>
            </AntigravityCard>
          )}

          {/* Segments */}
          {(latest.segments || latest.icp_segments)?.length > 0 && (
            <section className="mb-10">
              <SectionLabel count={(latest.segments || latest.icp_segments).length}>Customer Segments</SectionLabel>
              <p className="text-white/20 text-xs mb-6">Grounded in your offer catalog and real search behavior</p>
              <StaggerContainer className="grid gap-4 md:grid-cols-3">
                {(latest.segments || latest.icp_segments).map((seg, i) => (
                  <StaggerItem key={i}><SegmentCard segment={seg} index={i} total={(latest.segments || latest.icp_segments).length} /></StaggerItem>
                ))}
              </StaggerContainer>
            </section>
          )}

          {/* Trigger Map */}
          {(latest.trigger_map || latest.triggers) && (
            <TriggerMapSection data={latest} />
          )}

          {/* Language Bank */}
          {latest.language_bank && (
            <LanguageBankSection data={latest.language_bank} />
          )}
        </>
      )}
    </div>
  );
};

const TriggerMapSection = ({ data }) => {
  const groups = [
    { label: 'Moment Triggers', items: data.trigger_map?.moment_triggers || data.triggers?.moments || [], color: 'emerald' },
    { label: 'Urgency Triggers', items: data.trigger_map?.urgency_triggers || data.triggers?.urgency_triggers || [], color: 'red' },
    { label: 'Planned Triggers', items: data.trigger_map?.planned_triggers || data.triggers?.planned_triggers || [], color: 'blue' },
  ].filter(g => g.items.length > 0);

  if (groups.length === 0) return null;

  return (
    <section className="mb-10">
      <SectionLabel>Trigger Map</SectionLabel>
      <p className="text-white/20 text-xs mb-6">What makes people start searching</p>
      <div className="grid md:grid-cols-3 gap-4">
        {groups.map(({ label, items, color }) => (
          <AntigravityCard key={label} className="p-5">
            <span className={`text-[10px] text-${color}-400 uppercase tracking-wider font-mono`}>{label}</span>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {items.map((item, i) => (
                <span key={i} className={`text-xs px-2.5 py-1 bg-${color}-500/10 border border-${color}-500/15 text-${color}-300 rounded-md`}>
                  <CleanText>{item}</CleanText>
                </span>
              ))}
            </div>
          </AntigravityCard>
        ))}
      </div>
    </section>
  );
};

const LanguageBankSection = ({ data }) => {
  const groups = [
    { label: 'Desire Phrases', items: data.desire_phrases || data.desire_words || [], color: 'emerald' },
    { label: 'Anxiety Phrases', items: data.anxiety_phrases || data.anxiety_words || [], color: 'red' },
    { label: 'Intent Phrases', items: data.intent_phrases || data.intent_words || [], color: 'blue' },
  ].filter(g => g.items.length > 0);

  if (groups.length === 0) return null;

  return (
    <section className="mb-10">
      <SectionLabel>Language Bank</SectionLabel>
      <p className="text-white/20 text-xs mb-6">Real phrases customers use: for ads, landing pages, and hooks</p>
      <div className="grid md:grid-cols-3 gap-4">
        {groups.map(({ label, items, color }) => (
          <AntigravityCard key={label} className="p-5">
            <span className={`text-[10px] text-${color}-400 uppercase tracking-wider font-mono mb-3 block`}>{label}</span>
            <div className="flex flex-wrap gap-1.5">
              {items.map((item, i) => (
                <span key={i} className={`text-xs px-2 py-1 bg-${color}-500/10 border border-${color}-500/15 text-${color}-300 rounded-md`}>
                  <CleanText>{item}</CleanText>
                </span>
              ))}
            </div>
          </AntigravityCard>
        ))}
      </div>
    </section>
  );
};
