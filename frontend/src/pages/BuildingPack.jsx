import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Check, Loader2, AlertCircle, Globe, Palette, Image, Tag, Sparkles,
  Search, Zap, BarChart3, MapPin, Target, Megaphone, Link2, ArrowRight
} from 'lucide-react';
import Logo from '@/components/Logo';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

const ease = [0.23, 1, 0.32, 1];

// ─── Stage definitions with rich sub-descriptions ──────────────
const PROGRESS_STAGES = [
  {
    id: 'crawl',
    label: 'Deep-scanning website',
    activeLabel: 'Reading every page like a strategist would...',
    icon: Globe,
    events: ['CRAWL_START', 'CRAWL_DONE', 'EXTRACT_TEXT_START', 'EXTRACT_TEXT_DONE', 'SPA_SERVICES_START', 'SPA_SERVICES_DONE'],
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
  },
  {
    id: 'identity',
    label: 'Decoding brand identity',
    activeLabel: 'Isolating your visual DNA: colors, fonts, imagery...',
    icon: Palette,
    events: ['EXTRACT_IDENTITY_START', 'EXTRACT_IDENTITY_DONE'],
    color: 'text-violet-400',
    bgColor: 'bg-violet-500/20',
    borderColor: 'border-violet-500/30',
  },
  {
    id: 'assets',
    label: 'Curating brand assets',
    activeLabel: 'Ranking imagery by quality and relevance...',
    icon: Image,
    events: ['EXTRACT_ASSETS_START', 'EXTRACT_ASSETS_DONE'],
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20',
    borderColor: 'border-amber-500/30',
  },
  {
    id: 'pricing',
    label: 'Mapping pricing & offers',
    activeLabel: 'Understanding your value proposition and market position...',
    icon: Tag,
    events: ['PRICING_PARSED'],
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20',
    borderColor: 'border-emerald-500/30',
  },
  {
    id: 'summarize',
    label: 'Compiling brand profile',
    activeLabel: 'AI is synthesizing everything into your Business DNA...',
    icon: Sparkles,
    events: ['LLM_SUMMARIZE_START', 'LLM_SUMMARIZE_DONE', 'FINALIZE_START', 'FINALIZE_DONE'],
    color: 'text-rose-400',
    bgColor: 'bg-rose-500/20',
    borderColor: 'border-rose-500/30',
  },
];

const EVENT_TO_STAGE = {};
PROGRESS_STAGES.forEach((stage, idx) => {
  stage.events.forEach(e => { EVENT_TO_STAGE[e] = idx; });
});

// ─── Rich event descriptions ──────────────────────────────────
const EVENT_DESCRIPTIONS = {
  STEP2_STARTED: { text: 'Analysis pipeline initialized', icon: Zap },
  CRAWL_START: { text: 'Navigating to your website...', icon: Globe },
  CRAWL_DONE: {
    text: (p) => `Mapped ${p?.pages_fetched || '?'} pages via ${p?.fetch_method || 'crawler'}`,
    icon: Search,
  },
  EXTRACT_TEXT_START: { text: 'Extracting all visible text content...', icon: BarChart3 },
  EXTRACT_TEXT_DONE: { text: 'Text content captured across all pages', icon: Check },
  SPA_SERVICES_START: { text: 'Probing interactive elements & service tabs...', icon: Zap },
  SPA_SERVICES_DONE: {
    text: (p) => {
      const count = p?.services_count || 0;
      const cats = p?.categories?.length || 0;
      if (count > 0) return `Discovered ${count} services across ${cats} categories`;
      return 'No interactive service catalog detected';
    },
    icon: Tag,
  },
  EXTRACT_IDENTITY_START: { text: 'Analyzing color palette, typography & logo...', icon: Palette },
  EXTRACT_IDENTITY_DONE: {
    text: (p) => `Identified ${p?.colors_count || 0} brand colors and ${p?.fonts_count || 0} typefaces`,
    icon: Palette,
  },
  EXTRACT_ASSETS_START: { text: 'Scanning and ranking all visual assets...', icon: Image },
  EXTRACT_ASSETS_DONE: {
    text: (p) => `Curated top ${p?.assets_count || 0} images by quality score`,
    icon: Image,
  },
  PRICING_PARSED: {
    text: (p) => {
      const count = p?.count || 0;
      const curr = p?.currency || '';
      if (count > 0) return `Detected ${count} price points${curr ? ` in ${curr}` : ''}`;
      return 'No explicit pricing found on site';
    },
    icon: Tag,
  },
  LLM_SUMMARIZE_START: { text: 'AI is reading everything and building your profile...', icon: Sparkles },
  LLM_SUMMARIZE_DONE: {
    text: (p) => `Brand profile generated in ${Math.round(p?.duration_seconds || 0)}s`,
    icon: Check,
  },
  LLM_SUMMARIZE_FAILED: { text: 'AI summary unavailable. Using extracted data', icon: AlertCircle },
  FINALIZE_START: { text: 'Assembling your complete Business DNA...', icon: Sparkles },
  FINALIZE_DONE: {
    text: (p) => `Analysis complete: ${p?.confidence || 100}% confidence`,
    icon: Check,
  },
};

// (Context card options are inlined in the component)


const BuildingPack = () => {
  const { briefId } = useParams();
  const navigate = useNavigate();
  const pollInterval = useRef(null);
  const feedEndRef = useRef(null);

  const [websiteUrl, setWebsiteUrl] = useState('');
  const [websiteTitle, setWebsiteTitle] = useState('');
  const [screenshotUrl, setScreenshotUrl] = useState(null);
  const [currentStage, setCurrentStage] = useState(0);
  const [stageStates, setStageStates] = useState(PROGRESS_STAGES.map(() => 'pending'));
  const [packStatus, setPackStatus] = useState('running');
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [packId, setPackId] = useState(null);
  const [error, setError] = useState(null);
  const [orchestrationStarted, setOrchestrationStarted] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [liveEvents, setLiveEvents] = useState([]);
  const [contextStep, setContextStep] = useState(0);
  const [contextFields, setContextFields] = useState({
    city_or_region: '',
    primary_goal: '',
    destination_type: '',
  });
  const [contextSaved, setContextSaved] = useState(false);

  const saveContext = useCallback(async () => {
    const payload = {};
    if (contextFields.city_or_region) payload.city_or_region = contextFields.city_or_region;
    if (contextFields.primary_goal) payload.primary_goal = contextFields.primary_goal;
    if (contextFields.destination_type) payload.destination_type = contextFields.destination_type;
    if (Object.keys(payload).length === 0) return;
    try {
      await api.patch(`/campaign-briefs/${briefId}`, payload);
      setContextSaved(true);
      setTimeout(() => setContextSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save context:', err);
    }
  }, [briefId, contextFields]);

  useEffect(() => {
    const fetchBrief = async () => {
      try {
        const response = await api.get(`/campaign-briefs/${briefId}`);
        const brief = response.data;
        setWebsiteUrl(brief.brand?.website_url || brief.website_url || '');
      } catch (err) {
        console.error('Failed to fetch brief:', err);
      }
    };
    fetchBrief();
  }, [briefId]);

  useEffect(() => {
    const startOrchestration = async () => {
      try {
        setStartTime(Date.now());
        const response = await api.post(`/orchestrations/${briefId}/start`);
        setPackId(response.data.website_context_pack_id);
        setOrchestrationStarted(true);
        setStageStates(prev => { const u = [...prev]; u[0] = 'running'; return u; });
      } catch (err) {
        console.error('Failed to start orchestration:', err);
        setError('Failed to start analysis. Please try again.');
      }
    };
    startOrchestration();
  }, [briefId]);

  useEffect(() => {
    if (!startTime || packStatus !== 'running') return;
    const timer = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [startTime, packStatus]);

  // Progressive context cards: staggered reveal
  useEffect(() => {
    if (packStatus !== 'running') return;
    const timers = [
      setTimeout(() => setContextStep(1), 6000),
      setTimeout(() => setContextStep(2), 14000),
      setTimeout(() => setContextStep(3), 22000),
    ];
    return () => timers.forEach(clearTimeout);
  }, [packStatus]);

  // Auto-scroll live feed
  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveEvents]);

  useEffect(() => {
    if (!orchestrationStarted) return;

    const pollStatus = async () => {
      try {
        const response = await api.get(`/orchestrations/${briefId}/status`);
        const { steps, website_context_pack, campaign_brief } = response.data;
        if (!website_context_pack) return;

        setPackStatus(website_context_pack.status);
        setPackId(website_context_pack.website_context_pack_id);

        if (campaign_brief?.website_url) setWebsiteUrl(campaign_brief.website_url);
        if (website_context_pack.step2?.site?.title) setWebsiteTitle(website_context_pack.step2.site.title);
        if (website_context_pack.screenshot) setScreenshotUrl(website_context_pack.screenshot);

        const step2 = steps?.find(s => s.step_key === 'STEP2_WEBSITE_CONTEXT');
        if (step2?.progress?.events) {
          const rawEvents = step2.progress.events;
          const eventNames = rawEvents.map(e => e.event);
          const newStageStates = PROGRESS_STAGES.map(() => 'pending');

          // Build rich live feed
          const newLiveEvents = rawEvents.map(e => {
            const desc = EVENT_DESCRIPTIONS[e.event];
            if (!desc) return null;
            const text = typeof desc.text === 'function' ? desc.text(e.payload) : desc.text;
            const EventIcon = desc.icon || Zap;
            const isDone = e.event.endsWith('_DONE') || e.event === 'PRICING_PARSED' || e.event === 'FINALIZE_DONE';
            return { event: e.event, text, timestamp: e.timestamp, icon: EventIcon, isDone };
          }).filter(Boolean);
          setLiveEvents(newLiveEvents);

          let maxCompletedStage = -1;
          let currentRunningStage = 0;

          eventNames.forEach(event => {
            const stageIdx = EVENT_TO_STAGE[event];
            if (stageIdx !== undefined) {
              if (event.endsWith('_DONE') || event === 'PRICING_PARSED') {
                maxCompletedStage = Math.max(maxCompletedStage, stageIdx);
              }
              currentRunningStage = Math.max(currentRunningStage, stageIdx);
            }
          });

          for (let i = 0; i < PROGRESS_STAGES.length; i++) {
            if (i <= maxCompletedStage) newStageStates[i] = 'done';
            else if (i === currentRunningStage && website_context_pack.status === 'running') newStageStates[i] = 'running';
          }

          setStageStates(newStageStates);
          setCurrentStage(currentRunningStage);
        }

        if (website_context_pack.status === 'needs_user_input') {
          setQuestions(website_context_pack.questions || []);
          clearInterval(pollInterval.current);
        }

        if (website_context_pack.status === 'success' || website_context_pack.status === 'partial') {
          clearInterval(pollInterval.current);
          setStageStates(PROGRESS_STAGES.map(() => 'done'));
          setTimeout(() => { navigate(`/pack/${briefId}`, { state: { pack: website_context_pack } }); }, 2000);
        }

        if (website_context_pack.status === 'failed') {
          clearInterval(pollInterval.current);
          setError('Failed to analyze website. Please try again.');
        }
      } catch (err) {
        console.error('Poll error:', err);
      }
    };

    pollInterval.current = setInterval(pollStatus, 2500);
    pollStatus();
    return () => { if (pollInterval.current) clearInterval(pollInterval.current); };
  }, [orchestrationStarted, briefId, navigate]);

  const handleAnswerChange = (field, value) => {
    setAnswers(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmitAnswers = async () => {
    setIsSubmitting(true);
    try {
      await api.post(`/website-context-packs/${packId}/answers`, { answers });
      setPackStatus('running');
      setQuestions([]);
      pollInterval.current = setInterval(async () => {
        try {
          const response = await api.get(`/orchestrations/${briefId}/status`);
          const { website_context_pack } = response.data;
          if (website_context_pack?.status === 'success' || website_context_pack?.status === 'partial') {
            clearInterval(pollInterval.current);
            setPackStatus(website_context_pack.status);
            setStageStates(PROGRESS_STAGES.map(() => 'done'));
            setTimeout(() => { navigate(`/pack/${briefId}`); }, 2000);
          }
        } catch (e) { console.error(e); }
      }, 2500);
    } catch (err) {
      console.error('Failed to submit answers:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderQuestion = (q) => (
    <div key={q.field} className="space-y-3">
      <p className="text-sm text-[var(--novara-text-primary)]">{q.question}</p>
      <div className="grid grid-cols-2 gap-2">
        {q.options?.map((option, i) => (
          <button
            key={i}
            onClick={() => handleAnswerChange(q.field, option)}
            className={`text-left px-3 py-2.5 text-sm rounded-lg border transition-colors ${
              answers[q.field] === option
                ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400'
                : 'border-white/[0.06] hover:border-white/[0.12] text-[var(--novara-text-secondary)]'
            }`}
            data-testid={`option-${q.field}-${i}`}
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );

  const activeStage = PROGRESS_STAGES[currentStage];

  return (
    <div className="min-h-screen bg-black text-[var(--novara-text-primary)]">
      {/* Nav */}
      <nav className="fixed top-0 w-full bg-black/80 backdrop-blur-xl border-b border-white/[0.06] z-50">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-14 flex items-center justify-between">
          <Logo size="default" />
          <div className="flex items-center gap-3">
            {packStatus === 'running' && (
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
                </span>
                <span className="font-mono text-[10px] text-emerald-400/70 tracking-widest uppercase">Analyzing</span>
              </div>
            )}
            <span className="font-mono text-[10px] text-[var(--novara-text-tertiary)] tracking-widest tabular-nums">
              {elapsedTime > 0 ? `${elapsedTime}s` : ''}
            </span>
          </div>
        </div>
      </nav>

      <main className="pt-20 pb-12 px-6 md:px-12">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <motion.div
            className="text-center mb-10"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease }}
          >
            <h1 className="font-heading text-3xl md:text-4xl font-semibold tracking-tight mb-3" data-testid="building-title">
              Generating Business DNA
            </h1>
            <motion.p
              className="text-sm font-mono max-w-md mx-auto"
              key={activeStage?.activeLabel}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <span className={activeStage?.color || 'text-emerald-400'}>
                {packStatus === 'needs_user_input' ? 'We need a quick clarification' :
                 packStatus === 'success' || packStatus === 'partial' ? 'Analysis complete' :
                 activeStage?.activeLabel || 'Processing...'}
              </span>
            </motion.p>
          </motion.div>

          {/* Error */}
          {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-8 p-5 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-3 max-w-xl mx-auto">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-400 text-sm">{error}</p>
                <Button onClick={() => navigate('/wizard')} className="mt-3 bg-white text-black hover:bg-gray-200 rounded-lg text-sm" data-testid="error-start-over-btn">Start Over</Button>
              </div>
            </motion.div>
          )}

          {/* Main progress layout */}
          {!error && packStatus !== 'needs_user_input' && (
            <motion.div
              className="grid lg:grid-cols-12 gap-5"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1, ease }}
            >
              {/* Left column: Preview + Live Feed (7 cols) */}
              <div className="lg:col-span-7 space-y-4">
                {/* Website preview card */}
                <div className="relative overflow-hidden bg-[#0A0A0A]/80 backdrop-blur-md border border-white/[0.06] rounded-xl" data-testid="website-preview-card">
                  <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
                  <div className="aspect-[16/9] bg-black relative">
                    {screenshotUrl ? (
                      <img
                        src={screenshotUrl.startsWith('data:') ? screenshotUrl : `data:image/png;base64,${screenshotUrl}`}
                        alt="Website preview"
                        className="w-full h-full object-cover object-top"
                        data-testid="screenshot-preview"
                      />
                    ) : websiteUrl ? (
                      <div className="w-full h-full relative overflow-hidden">
                        <iframe
                          src={websiteUrl.startsWith('http') ? websiteUrl : `https://${websiteUrl}`}
                          title="Website preview"
                          className="absolute inset-0 border-0 pointer-events-none"
                          sandbox="allow-same-origin"
                          loading="eager"
                          style={{ transform: 'scale(0.5)', transformOrigin: 'top left', width: '200%', height: '200%' }}
                        />
                      </div>
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center">
                        <Globe className="w-10 h-10 text-white/10" />
                      </div>
                    )}
                    {/* Scanning overlay */}
                    {!screenshotUrl && packStatus === 'running' && (
                      <motion.div
                        className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-emerald-400/60 to-transparent pointer-events-none"
                        animate={{ top: ['0%', '100%', '0%'] }}
                        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
                      />
                    )}
                  </div>
                  <div className="px-4 py-3 flex items-center gap-2 border-t border-white/[0.04]">
                    <Globe className="w-3 h-3 text-[var(--novara-text-tertiary)]" />
                    <span className="text-xs font-mono text-[var(--novara-text-tertiary)] truncate">{websiteUrl}</span>
                    {websiteTitle && <span className="text-xs text-[var(--novara-text-secondary)] ml-auto truncate">{websiteTitle}</span>}
                  </div>
                </div>

                {/* Live activity feed */}
                <div className="relative overflow-hidden bg-[#0A0A0A]/80 backdrop-blur-md border border-white/[0.06] rounded-xl p-4" data-testid="live-feed-card">
                  <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="relative flex h-1.5 w-1.5">
                        {packStatus === 'running' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />}
                        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${packStatus === 'running' ? 'bg-emerald-400' : 'bg-white/20'}`} />
                      </span>
                      <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase tracking-[0.2em]">Activity Log</span>
                    </div>
                    <span className="text-[10px] font-mono text-[var(--novara-text-tertiary)] tabular-nums">{liveEvents.length} events</span>
                  </div>
                  <div className="space-y-0.5 max-h-48 overflow-y-auto scrollbar-thin">
                    {liveEvents.length === 0 && packStatus === 'running' && (
                      <div className="flex items-center gap-2 py-2">
                        <Loader2 className="w-3 h-3 animate-spin text-white/20" />
                        <span className="text-xs font-mono text-[var(--novara-text-tertiary)]">Waiting for first signal...</span>
                      </div>
                    )}
                    <AnimatePresence>
                      {liveEvents.map((ev, i) => {
                        const EventIcon = ev.icon;
                        return (
                          <motion.div
                            key={ev.event}
                            className="flex items-start gap-2.5 py-1.5 group"
                            initial={{ opacity: 0, x: -12 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.35, delay: i * 0.02, ease }}
                          >
                            <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 mt-0.5 ${
                              ev.isDone ? 'bg-emerald-500/15 text-emerald-400' : 'bg-white/[0.04] text-white/30'
                            }`}>
                              {ev.isDone ? <Check className="w-2.5 h-2.5" strokeWidth={2.5} /> : <EventIcon className="w-2.5 h-2.5" />}
                            </div>
                            <span className={`text-xs leading-relaxed ${
                              ev.isDone ? 'text-[var(--novara-text-secondary)]' : 'text-[var(--novara-text-tertiary)]'
                            }`}>
                              {ev.text}
                            </span>
                          </motion.div>
                        );
                      })}
                    </AnimatePresence>
                    <div ref={feedEndRef} />
                  </div>
                </div>
              </div>

              {/* Right column: Progress + Context (5 cols) */}
              <div className="lg:col-span-5 space-y-4">
                {/* Progress tracker */}
                <div className="relative overflow-hidden bg-[#0A0A0A]/80 backdrop-blur-md border border-white/[0.06] rounded-xl p-5 sticky top-20" data-testid="progress-tracker">
                  <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
                  <div className="text-[10px] font-mono text-[var(--novara-text-tertiary)] uppercase tracking-[0.2em] mb-5">Pipeline</div>
                  <div className="space-y-1">
                    {PROGRESS_STAGES.map((stage, index) => {
                      const state = stageStates[index];
                      const Icon = stage.icon;
                      const isActive = state === 'running';
                      return (
                        <motion.div
                          key={stage.id}
                          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-300 ${isActive ? 'bg-white/[0.03]' : ''}`}
                          animate={{ opacity: state === 'done' ? 0.5 : isActive ? 1 : 0.3 }}
                          transition={{ duration: 0.3 }}
                          data-testid={`stage-${stage.id}`}
                        >
                          <div className={`w-6 h-6 flex items-center justify-center rounded-md border transition-all duration-300 ${
                            state === 'done' ? `${stage.bgColor} ${stage.borderColor} ${stage.color}` :
                            isActive ? `${stage.borderColor} ${stage.color}` :
                            'border-white/[0.06] text-[var(--novara-text-tertiary)]'
                          }`}>
                            {state === 'done' ? <Check className="w-3 h-3" strokeWidth={2.5} /> :
                             isActive ? <Loader2 className="w-3 h-3 animate-spin" /> :
                             <Icon className="w-3 h-3" strokeWidth={1.5} />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <span className={`text-sm block truncate ${
                              isActive ? 'text-[var(--novara-text-primary)] font-medium' :
                              state === 'done' ? 'text-[var(--novara-text-secondary)]' : 'text-[var(--novara-text-tertiary)]'
                            }`}>{stage.label}</span>
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                  {/* Time + progress bar */}
                  <div className="mt-5 pt-4 border-t border-white/[0.04] space-y-2">
                    <div className="flex justify-between items-center">
                      <p className="text-xs font-mono text-[var(--novara-text-tertiary)]">
                        {elapsedTime > 0 ? `${elapsedTime}s elapsed` : 'Starting...'}
                      </p>
                      <p className="text-xs font-mono text-[var(--novara-text-tertiary)]">~45s</p>
                    </div>
                    <div className="h-1 bg-white/[0.04] rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-emerald-500/60 to-emerald-400/80 rounded-full"
                        initial={{ width: '0%' }}
                        animate={{
                          width: packStatus === 'success' || packStatus === 'partial' ? '100%' :
                                 `${Math.min(95, (stageStates.filter(s => s === 'done').length / PROGRESS_STAGES.length) * 100 + 5)}%`
                        }}
                        transition={{ duration: 0.8, ease }}
                      />
                    </div>
                  </div>
                </div>

                {/* Contextual input: single compact card with all fields */}
                {packStatus === 'running' && contextStep > 0 && (
                  <motion.div
                    className="relative overflow-hidden bg-[#0A0A0A]/80 backdrop-blur-md border border-white/[0.06] rounded-xl"
                    initial={{ opacity: 0, y: 12, borderColor: 'rgba(255,255,255,0.06)' }}
                    animate={{
                      opacity: 1,
                      y: 0,
                      borderColor: ['rgba(255,255,255,0.06)', 'rgba(52,211,153,0.3)', 'rgba(255,255,255,0.06)'],
                    }}
                    transition={{ duration: 0.6, ease, borderColor: { duration: 2, delay: 0.3 } }}
                    data-testid="context-card"
                  >
                    <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-400/20 to-transparent" />
                    <div className="px-4 pt-4 pb-1 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Megaphone className="w-3 h-3 text-emerald-400/60" />
                        <span className="text-[10px] font-mono text-emerald-400/60 uppercase tracking-[0.15em]">Sharpen your results</span>
                      </div>
                      <AnimatePresence>
                        {contextSaved && (
                          <motion.span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                            <Check className="w-2.5 h-2.5" /> Saved
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </div>
                    <div className="p-4 pt-2 space-y-3">
                      {/* Location */}
                      <AnimatePresence>
                        {contextStep >= 1 && (
                          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-1.5" data-testid="context-card-city_or_region">
                            <div className="flex items-center gap-1.5">
                              <MapPin className="w-3 h-3 text-[var(--novara-text-tertiary)]" />
                              <span className="text-xs text-[var(--novara-text-secondary)]">Where is this business based?</span>
                            </div>
                            <input
                              type="text"
                              placeholder="e.g., Dubai, London, New York"
                              value={contextFields.city_or_region}
                              onChange={(e) => setContextFields(p => ({ ...p, city_or_region: e.target.value }))}
                              onBlur={saveContext}
                              className="w-full bg-black/50 border border-white/[0.08] text-[var(--novara-text-primary)] placeholder:text-white/20 h-8 px-3 text-xs rounded-lg focus:outline-none focus:border-white/20 transition-colors"
                              data-testid="context-city_or_region"
                            />
                          </motion.div>
                        )}
                      </AnimatePresence>
                      {/* Goal */}
                      <AnimatePresence>
                        {contextStep >= 2 && (
                          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-1.5 pt-1 border-t border-white/[0.04]" data-testid="context-card-primary_goal">
                            <div className="flex items-center gap-1.5">
                              <Target className="w-3 h-3 text-[var(--novara-text-tertiary)]" />
                              <span className="text-xs text-[var(--novara-text-secondary)]">Advertising goal?</span>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {[{value:'sales_orders',label:'Sales'},{value:'bookings_leads',label:'Leads'},{value:'brand_awareness',label:'Awareness'},{value:'event_launch',label:'Launch'}].map(opt => (
                                <button key={opt.value} onClick={() => { setContextFields(p => ({...p, primary_goal: opt.value})); setTimeout(saveContext, 100); }}
                                  className={`px-2.5 py-1 text-[11px] rounded-md border transition-all duration-200 ${contextFields.primary_goal === opt.value ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400' : 'border-white/[0.06] text-[var(--novara-text-secondary)] hover:border-white/[0.12]'}`}
                                  data-testid={`context-primary_goal-${opt.value}`}
                                >{opt.label}</button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                      {/* Destination */}
                      <AnimatePresence>
                        {contextStep >= 3 && (
                          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-1.5 pt-1 border-t border-white/[0.04]" data-testid="context-card-destination_type">
                            <div className="flex items-center gap-1.5">
                              <Link2 className="w-3 h-3 text-[var(--novara-text-tertiary)]" />
                              <span className="text-xs text-[var(--novara-text-secondary)]">Where should ads drive traffic?</span>
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                              {[{value:'website',label:'Website'},{value:'whatsapp',label:'WhatsApp'},{value:'booking_link',label:'Booking'},{value:'app',label:'App'}].map(opt => (
                                <button key={opt.value} onClick={() => { setContextFields(p => ({...p, destination_type: opt.value})); setTimeout(saveContext, 100); }}
                                  className={`px-2.5 py-1 text-[11px] rounded-md border transition-all duration-200 ${contextFields.destination_type === opt.value ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400' : 'border-white/[0.06] text-[var(--novara-text-secondary)] hover:border-white/[0.12]'}`}
                                  data-testid={`context-destination_type-${opt.value}`}
                                >{opt.label}</button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}

          {/* Micro Questions (backend-driven) */}
          {packStatus === 'needs_user_input' && questions.length > 0 && (
            <motion.div
              className="max-w-xl mx-auto relative overflow-hidden border border-white/[0.06] bg-[#0A0A0A]/80 backdrop-blur-md rounded-xl p-8"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease }}
            >
              <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
              <div className="flex items-center gap-3 mb-6">
                <div className="w-9 h-9 bg-white/10 rounded-lg flex items-center justify-center">
                  <AlertCircle className="w-4 h-4 text-[var(--novara-text-primary)]" strokeWidth={1.5} />
                </div>
                <div>
                  <h2 className="font-heading text-lg font-semibold">Quick check</h2>
                  <p className="text-[var(--novara-text-tertiary)] text-xs font-mono">30 seconds</p>
                </div>
              </div>
              <p className="text-[var(--novara-text-secondary)] text-sm mb-8">
                Your website did not make this 100% clear. Pick one option so we keep the plan accurate.
              </p>
              <div className="space-y-8 mb-8">
                {questions.map(renderQuestion)}
              </div>
              <Button
                onClick={handleSubmitAnswers}
                disabled={isSubmitting || Object.keys(answers).length === 0}
                className="w-full bg-white text-black hover:bg-gray-200 rounded-lg font-medium py-3 disabled:opacity-50"
                data-testid="btn-submit-answers"
              >
                {isSubmitting ? 'Submitting...' : 'Continue'}
              </Button>
            </motion.div>
          )}

          {/* Success */}
          {(packStatus === 'success' || packStatus === 'partial') && (
            <motion.div
              className="text-center max-w-xl mx-auto"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, ease }}
            >
              <motion.div
                className="w-16 h-16 bg-emerald-500/20 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-emerald-500/20"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              >
                <Check className="w-7 h-7 text-emerald-400" strokeWidth={2.5} />
              </motion.div>
              <h2 className="font-heading text-2xl font-semibold mb-2">Your Business DNA is ready</h2>
              <p className="text-[var(--novara-text-tertiary)] text-sm font-mono mb-6">Redirecting to your brand profile...</p>
              <div className="flex justify-center">
                <Button
                  onClick={() => navigate(`/pack/${briefId}`)}
                  className="bg-white text-black hover:bg-gray-100 rounded-lg font-medium px-5 py-2.5 text-sm"
                  data-testid="view-results-btn"
                >
                  View Results <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </motion.div>
          )}
        </div>
      </main>
    </div>
  );
};

export default BuildingPack;
