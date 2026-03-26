import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain, ChevronDown, Zap, Eye, Target, MessageSquare,
  Lightbulb, Volume2, Layers, Sparkles, Shield
} from 'lucide-react';

const Tag = ({ children, color = 'white/10' }) => (
  <span className={`inline-block px-2 py-0.5 text-[10px] font-medium bg-${color} rounded border border-white/[0.06] text-white/70`}>
    {children}
  </span>
);

const FieldRow = ({ icon: Icon, label, value, highlight }) => {
  if (!value || value === 'N/A' || value === 'none') return null;
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      {Icon && <Icon className="w-3.5 h-3.5 text-white/20 shrink-0 mt-0.5" />}
      <div className="flex-1 min-w-0">
        <span className="text-[10px] text-white/25 uppercase tracking-wider block">{label}</span>
        <p className={`text-xs leading-relaxed mt-0.5 ${highlight ? 'text-white/80' : 'text-white/50'}`}>{value}</p>
      </div>
    </div>
  );
};

const Section = ({ title, icon: Icon, children, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  const hasContent = React.Children.toArray(children).some(c => c !== null);
  if (!hasContent) return null;

  return (
    <div className="border-t border-white/[0.04]">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 py-2.5 px-1 text-left group"
        data-testid={`ca-section-${title.toLowerCase().replace(/\s/g, '-')}`}
      >
        <Icon className="w-3.5 h-3.5 text-white/30" />
        <span className="text-[11px] font-medium text-white/50 flex-1">{title}</span>
        <ChevronDown className={`w-3 h-3 text-white/20 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pb-3 px-1 space-y-0.5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const AdCreativeInsightPanel = ({ analysis }) => {
  const [expanded, setExpanded] = useState(false);

  if (!analysis || analysis.error) return null;

  const c = analysis.core || {};
  const v = analysis.video;
  const img = analysis.image;
  const car = analysis.carousel;

  return (
    <div className="mt-3 border border-white/[0.06] rounded-lg bg-white/[0.02] overflow-hidden" data-testid="creative-analysis-panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
        data-testid="creative-analysis-toggle"
      >
        <Brain className="w-4 h-4 text-violet-400" />
        <span className="text-xs font-medium text-white/70 flex-1">Creative Analysis</span>
        <span className="text-[10px] text-white/25 font-mono mr-2">{analysis.analysis_depth}</span>
        <ChevronDown className={`w-3.5 h-3.5 text-white/25 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4">
              {/* Key Insight — always visible at top */}
              {c.key_insight && (
                <div className="mb-3 px-3 py-2.5 bg-violet-500/10 border border-violet-500/20 rounded-lg" data-testid="ca-key-insight">
                  <div className="flex items-start gap-2">
                    <Lightbulb className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5" />
                    <p className="text-xs text-white/70 leading-relaxed">{c.key_insight}</p>
                  </div>
                </div>
              )}

              {/* Replicable Framework */}
              {c.replicable_framework && (
                <div className="mb-3 px-3 py-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg" data-testid="ca-framework">
                  <div className="flex items-start gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="text-[10px] text-amber-400/80 uppercase tracking-wider block mb-0.5">Replicable Framework</span>
                      <p className="text-xs text-white/70 leading-relaxed">{c.replicable_framework}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Hook & Scroll Stop */}
              <Section title="Hook Analysis" icon={Zap} defaultOpen={true}>
                <FieldRow icon={Zap} label="Hook Type" value={c.hook_type?.replace(/_/g, ' ')} />
                <FieldRow icon={MessageSquare} label="Hook Text" value={c.hook_text} highlight />
                <FieldRow icon={Brain} label="Hook Psychology" value={c.hook_psychology} />
                <FieldRow icon={Eye} label="Scroll-Stop Mechanism" value={c.scroll_stop_mechanism} />
              </Section>

              {/* Strategy & Messaging */}
              <Section title="Strategy & Messaging" icon={Target}>
                <FieldRow icon={Layers} label="Messaging Structure" value={c.messaging_structure?.replace(/_/g, ' ')} />
                <FieldRow label="Body Narrative" value={c.body_narrative} />
                <FieldRow icon={Target} label="Target Persona" value={c.implied_target_persona} />
                <FieldRow label="Awareness Stage" value={c.implied_awareness_stage?.replace(/_/g, ' ')} />
                <FieldRow icon={Shield} label="Competitive Positioning" value={c.competitive_positioning} />
              </Section>

              {/* Visual & Production */}
              <Section title="Visual & Production" icon={Eye}>
                <FieldRow label="Visual Style" value={c.visual_style?.replace(/_/g, ' ')} />
                <FieldRow label="Production Quality" value={c.production_quality?.replace(/_/g, ' ')} />
                <FieldRow label="Talent" value={c.talent_archetype?.replace(/_/g, ' ')} />
                <FieldRow label="Setting" value={c.setting_environment?.replace(/_/g, ' ')} />
              </Section>

              {/* Video-specific */}
              {v && (
                <Section title="Video Analysis" icon={Volume2}>
                  <FieldRow label="Pacing" value={v.pacing?.replace(/_/g, ' ')} />
                  <FieldRow icon={Volume2} label="Audio Strategy" value={v.audio_strategy?.replace(/_/g, ' ')} />
                  <FieldRow label="Music Mood" value={v.music_mood?.replace(/_/g, ' ')} />
                  <FieldRow label="Transitions" value={v.transition_patterns?.replace(/_/g, ' ')} />
                  <FieldRow label="Hook Visual" value={v.hook_visual_technique?.replace(/_/g, ' ')} />
                  {v.emotional_arc && <FieldRow icon={Brain} label="Emotional Arc" value={v.emotional_arc} highlight />}
                  {v.on_screen_text?.length > 0 && (
                    <div className="py-1.5 pl-6">
                      <span className="text-[10px] text-white/25 uppercase tracking-wider block mb-1">On-Screen Text</span>
                      <div className="flex flex-wrap gap-1">
                        {v.on_screen_text.map((t, i) => <Tag key={i}>{t}</Tag>)}
                      </div>
                    </div>
                  )}
                  {v.narrative_arc_beats?.length > 0 && (
                    <div className="py-1.5 pl-6">
                      <span className="text-[10px] text-white/25 uppercase tracking-wider block mb-1">Narrative Arc</span>
                      <div className="flex flex-wrap gap-1">
                        {v.narrative_arc_beats.map((b, i) => <Tag key={i}>{b.replace(/_/g, ' ')}</Tag>)}
                      </div>
                    </div>
                  )}
                </Section>
              )}

              {/* Image-specific */}
              {img && (
                <Section title="Image Analysis" icon={Eye}>
                  <FieldRow label="Layout" value={img.layout_structure?.replace(/_/g, ' ')} />
                  <FieldRow label="Text Hierarchy" value={img.text_hierarchy?.replace(/_/g, ' ')} />
                  <FieldRow label="Info Density" value={img.information_density?.replace(/_/g, ' ')} />
                  <FieldRow label="Color Mood" value={img.color_mood?.replace(/_/g, ' ')} />
                </Section>
              )}

              {/* Carousel-specific */}
              {car && (
                <Section title="Carousel Analysis" icon={Layers}>
                  <FieldRow label="Opening Card" value={car.opening_card_strategy?.replace(/_/g, ' ')} />
                  <FieldRow label="Card Narrative" value={car.card_narrative_type?.replace(/_/g, ' ')} />
                  <FieldRow label="Swipe Motivation" value={car.swipe_motivation?.replace(/_/g, ' ')} />
                </Section>
              )}

              {/* Persuasion */}
              <Section title="Persuasion Elements" icon={Shield}>
                <FieldRow label="CTA" value={c.cta_language} />
                <FieldRow label="CTA Psychology" value={c.cta_psychology?.replace(/_/g, ' ')} />
                <FieldRow label="Urgency" value={c.urgency_mechanics?.replace(/_/g, ' ')} />
                <FieldRow label="Tone" value={c.tone?.replace(/_/g, ' ')} />
                <FieldRow label="Voice" value={c.voice_person?.replace(/_/g, ' ')} />
                {c.proof_elements?.length > 0 && (
                  <div className="py-1.5 pl-6">
                    <span className="text-[10px] text-white/25 uppercase tracking-wider block mb-1">Proof Elements</span>
                    <div className="flex flex-wrap gap-1">
                      {c.proof_elements.map((p, i) => <Tag key={i}>{p}</Tag>)}
                    </div>
                  </div>
                )}
              </Section>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};


export const TikTokCreativeInsightPanel = ({ analysis }) => {
  const [expanded, setExpanded] = useState(false);

  if (!analysis || analysis.error) return null;

  const a = analysis.analysis || {};

  return (
    <div className="mt-3 border border-white/[0.06] rounded-lg bg-white/[0.02] overflow-hidden" data-testid="tiktok-analysis-panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
        data-testid="tiktok-analysis-toggle"
      >
        <Brain className="w-4 h-4 text-violet-400" />
        <span className="text-xs font-medium text-white/70 flex-1">Creative Analysis</span>
        <ChevronDown className={`w-3.5 h-3.5 text-white/25 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4">
              {/* Key Insight */}
              {analysis.key_insight && (
                <div className="mb-3 px-3 py-2.5 bg-violet-500/10 border border-violet-500/20 rounded-lg" data-testid="tt-key-insight">
                  <div className="flex items-start gap-2">
                    <Lightbulb className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5" />
                    <p className="text-xs text-white/70 leading-relaxed">{analysis.key_insight}</p>
                  </div>
                </div>
              )}

              {/* Replicable Framework */}
              {a.replicable_framework && (
                <div className="mb-3 px-3 py-2.5 bg-amber-500/10 border border-amber-500/20 rounded-lg" data-testid="tt-framework">
                  <div className="flex items-start gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="text-[10px] text-amber-400/80 uppercase tracking-wider block mb-0.5">Replicable Framework</span>
                      <p className="text-xs text-white/70 leading-relaxed">{a.replicable_framework}</p>
                    </div>
                  </div>
                </div>
              )}

              <FieldRow icon={Layers} label="Content Format" value={a.content_format?.replace(/_/g, ' ')} />
              <FieldRow icon={Zap} label="Hook Technique" value={a.hook_technique} />
              {analysis.hook_text && <FieldRow icon={MessageSquare} label="Hook Text" value={analysis.hook_text} highlight />}
              <FieldRow icon={Brain} label="Hook Psychology" value={a.hook_psychology} />
              <FieldRow label="Production Style" value={a.production_style?.replace(/_/g, ' ')} />
              <FieldRow icon={Volume2} label="Audio Strategy" value={a.audio_strategy?.replace(/_/g, ' ')} />
              <FieldRow icon={Eye} label="Why Users Save This" value={a.save_worthy_reason} highlight />
              {analysis.implied_target_persona && <FieldRow icon={Target} label="Target Persona" value={analysis.implied_target_persona} />}

              {a.trending_elements?.length > 0 && (
                <div className="py-1.5">
                  <span className="text-[10px] text-white/25 uppercase tracking-wider block mb-1.5">Trending Elements to Adopt</span>
                  <div className="flex flex-wrap gap-1">
                    {a.trending_elements.map((el, i) => <Tag key={i}>{el}</Tag>)}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
