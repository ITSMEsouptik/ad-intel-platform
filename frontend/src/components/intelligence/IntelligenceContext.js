import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '@/lib/api';

const STATUS = {
  NOT_RUN: 'not_run',
  RUNNING: 'running',
  FRESH: 'fresh',
  STALE: 'stale',
  FAILED: 'failed',
};

const IntelContext = createContext(null);

export const useIntel = () => {
  const ctx = useContext(IntelContext);
  if (!ctx) throw new Error('useIntel must be used within IntelProvider');
  return ctx;
};

export { STATUS };

const MODULE_KEYS = [
  'customerIntel', 'searchIntent', 'seasonality', 'competitors',
  'reviews', 'community', 'pressMedia', 'socialTrends', 'adsIntel', 'creativeAnalysis'
];

const API_MAP = {
  customerIntel: { fetch: 'customer-intel/latest', run: 'customer-intel/run', refreshDays: 14 },
  searchIntent: { fetch: 'search-intent/latest', run: 'search-intent/run', refreshDays: 14 },
  seasonality: { fetch: 'seasonality/latest', run: 'seasonality/run', refreshDays: 30 },
  competitors: { fetch: 'competitors/latest', run: 'competitors/run', refreshDays: 30 },
  reviews: { fetch: 'reviews/latest', run: 'reviews/run', refreshDays: 30 },
  community: { fetch: 'community/latest', run: 'community/run', refreshDays: 30 },
  pressMedia: { fetch: 'press-media/latest', run: 'press-media/run', refreshDays: 30 },
  socialTrends: { fetch: 'social-trends/latest', run: 'social-trends/run', refreshDays: 7, async: true },
  adsIntel: { fetch: 'ads-intel/latest', run: 'ads-intel/run', refreshDays: 14, async: true },
  creativeAnalysis: { fetch: 'creative-analysis/latest', run: 'creative-analysis/run', refreshDays: 14, async: true, autoRun: false },
};

const normalizeError = (err) => ({
  message: err?.response?.data?.detail || err?.message || 'Unknown error',
  status: err?.response?.status || null,
});

const ASYNC_JOB_TTL = 180000; // 3 minutes — matches polling timeout

const runningMarkerKey = (briefId, moduleKey) => `novara_running_${briefId}_${moduleKey}`;

const saveRunningMarker = (briefId, key) => {
  try { localStorage.setItem(runningMarkerKey(briefId, key), String(Date.now())); } catch (_) {}
};

const clearRunningMarker = (briefId, key) => {
  try { localStorage.removeItem(runningMarkerKey(briefId, key)); } catch (_) {}
};

const getRunningMarker = (briefId, key) => {
  try {
    const ts = localStorage.getItem(runningMarkerKey(briefId, key));
    if (!ts) return null;
    const age = Date.now() - Number(ts);
    if (age < ASYNC_JOB_TTL) return age;
    localStorage.removeItem(runningMarkerKey(briefId, key));
    return null;
  } catch (_) { return null; }
};

export const IntelProvider = ({ children }) => {
  const { briefId } = useParams();
  const navigate = useNavigate();

  const [activeModule, setActiveModule] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [step2Complete, setStep2Complete] = useState(null);
  const [initialLoadDone, setInitialLoadDone] = useState(false);

  // Module state: { data, status, error } for each key
  const [modules, setModules] = useState(() => {
    const initial = {};
    MODULE_KEYS.forEach(k => {
      initial[k] = { data: null, status: STATUS.NOT_RUN, error: null };
    });
    return initial;
  });

  const updateModule = useCallback((key, updates) => {
    setModules(prev => ({ ...prev, [key]: { ...prev[key], ...updates } }));
  }, []);

  // Shared async polling — used by runModule and reload recovery
  const startAsyncPoll = useCallback((key, prevCapturedAt) => {
    const config = API_MAP[key];
    const pollInterval = setInterval(async () => {
      try {
        const resp = await api.get(`/research/${briefId}/${config.fetch}`);
        if (resp.data.has_data) {
          const newCapturedAt = resp.data.latest?.captured_at || null;
          if (!prevCapturedAt || newCapturedAt !== prevCapturedAt) {
            clearRunningMarker(briefId, key);
            setModules(prev => ({ ...prev, [key]: { ...prev[key], data: resp.data, status: STATUS.FRESH } }));
            clearInterval(pollInterval);
          }
        }
      } catch (_) {}
    }, 5000);
    const timeoutId = setTimeout(() => {
      clearRunningMarker(briefId, key);
      clearInterval(pollInterval);
      setModules(prev => {
        if (prev[key].status === STATUS.RUNNING) {
          return { ...prev, [key]: { ...prev[key], status: STATUS.FAILED, error: { message: 'Pipeline timed out. Try refreshing.' } } };
        }
        return prev;
      });
    }, ASYNC_JOB_TTL);
    return () => { clearInterval(pollInterval); clearTimeout(timeoutId); };
  }, [briefId]);

  // Generic fetch
  const fetchModule = useCallback(async (key) => {
    const config = API_MAP[key];
    try {
      const response = await api.get(`/research/${briefId}/${config.fetch}`);
      const d = response.data;
      let status = STATUS.NOT_RUN;
      if (d.has_data) {
        status = d.status === 'stale' ? STATUS.STALE : STATUS.FRESH;
      }
      updateModule(key, { data: d, status, error: null });
      return d;
    } catch (err) {
      if (err.response?.status === 404) {
        updateModule(key, { status: STATUS.NOT_RUN });
        return null;
      }
      updateModule(key, { status: STATUS.NOT_RUN });
      return null;
    }
  }, [briefId, updateModule]);

  // Generic run
  const runModule = useCallback(async (key) => {
    const config = API_MAP[key];

    setModules(prev => {
      if (prev[key]?.status === STATUS.RUNNING) return prev;
      return { ...prev, [key]: { ...prev[key], status: STATUS.RUNNING, error: null } };
    });

    // Capture timestamp of current data so we can detect when NEW data arrives
    let prevCapturedAt = null;
    setModules(prev => {
      prevCapturedAt = prev[key]?.data?.latest?.captured_at || null;
      return prev;
    });

    try {
      if (config.async) {
        // Async pipeline: POST then poll
        saveRunningMarker(briefId, key);
        await api.post(`/research/${briefId}/${config.run}`);
        startAsyncPoll(key, prevCapturedAt);
      } else {
        // Sync: POST and get result
        const response = await api.post(`/research/${briefId}/${config.run}`);
        setModules(prev => ({
          ...prev,
          [key]: {
            ...prev[key],
            data: { has_data: true, status: 'fresh', latest: response.data.snapshot, refresh_due_in_days: config.refreshDays },
            status: STATUS.FRESH,
          }
        }));
      }
    } catch (err) {
      clearRunningMarker(briefId, key);
      console.error(`${key} run failed`, err);
      setModules(prev => ({ ...prev, [key]: { ...prev[key], status: STATUS.FAILED, error: normalizeError(err) } }));
    }
  }, [briefId, startAsyncPoll]);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      let hasStep2 = false;
      try {
        const packRes = await api.get(`/website-context-packs/by-campaign/${briefId}`);
        const packStatus = packRes.data?.status;
        hasStep2 = packStatus === 'success' || packStatus === 'partial';
        setStep2Complete(hasStep2);
      } catch {
        setStep2Complete(false);
      }

      const results = await Promise.allSettled(MODULE_KEYS.map(k => fetchModule(k)));
      setLoading(false);
      setInitialLoadDone(true);

      if (!hasStep2) return;

      // Phase 1: Auto-run independent modules (all except adsIntel and creativeAnalysis)
      // Phase 2: adsIntel depends on competitors data, so it runs after competitors completes
      // creativeAnalysis is auto-triggered by backend after adsIntel + socialTrends complete
      const INDEPENDENT_MODULES = MODULE_KEYS.filter(k => k !== 'adsIntel' && k !== 'creativeAnalysis');

      const modulesNeedingRun = [];
      INDEPENDENT_MODULES.forEach((key) => {
        const idx = MODULE_KEYS.indexOf(key);
        const result = results[idx];
        const data = result.status === 'fulfilled' ? result.value : null;
        if (!data || !data.has_data) {
          // For async modules: check if a job was already started this session (survived reload)
          const config = API_MAP[key];
          if (config.async && getRunningMarker(briefId, key) !== null) {
            // Job is still within its TTL — re-attach polling without re-POSTing
            updateModule(key, { status: STATUS.RUNNING, error: null });
            startAsyncPoll(key, null);
          } else {
            modulesNeedingRun.push(key);
            runModule(key);
          }
        }
      });

      // Check if adsIntel needs to run
      const adsIdx = MODULE_KEYS.indexOf('adsIntel');
      const adsResult = results[adsIdx];
      const adsData = adsResult.status === 'fulfilled' ? adsResult.value : null;
      const adsNeedsRun = !adsData || !adsData.has_data;

      if (adsNeedsRun) {
        // Check if already running (reload recovery)
        if (getRunningMarker(briefId, 'adsIntel') !== null) {
          updateModule('adsIntel', { status: STATUS.RUNNING, error: null });
          startAsyncPoll('adsIntel', null);
        } else if (modulesNeedingRun.includes('competitors')) {
          // If competitors also needs to run, wait for it to complete first
          const pollCompetitors = setInterval(async () => {
            try {
              const resp = await api.get(`/research/${briefId}/competitors/latest`);
              if (resp.data.has_data) {
                clearInterval(pollCompetitors);
                runModule('adsIntel');
              }
            } catch (_) { /* still waiting */ }
          }, 3000);
          // Safety timeout: run adsIntel anyway after 120s
          setTimeout(() => { clearInterval(pollCompetitors); runModule('adsIntel'); }, 120000);
        } else {
          // Competitors already has data — run adsIntel immediately
          runModule('adsIntel');
        }
      }

      // Poll for Creative Analysis (auto-triggered by backend after adsIntel + socialTrends)
      const caIdx = MODULE_KEYS.indexOf('creativeAnalysis');
      const caResult = results[caIdx];
      const caData = caResult.status === 'fulfilled' ? caResult.value : null;
      if (!caData || !caData.has_data) {
        // Check if already running (reload recovery)
        if (getRunningMarker(briefId, 'creativeAnalysis') !== null) {
          updateModule('creativeAnalysis', { status: STATUS.RUNNING, error: null });
          startAsyncPoll('creativeAnalysis', null);
        } else {
          const pollCA = setInterval(async () => {
            try {
              const resp = await api.get(`/research/${briefId}/creative-analysis/latest`);
              if (resp.data.has_data) {
                clearInterval(pollCA);
                setModules(prev => ({
                  ...prev,
                  creativeAnalysis: {
                    ...prev.creativeAnalysis,
                    data: resp.data,
                    status: STATUS.FRESH,
                  }
                }));
              }
            } catch (_) { /* still waiting */ }
          }, 8000);
          // Safety timeout: stop polling after 5 minutes
          setTimeout(() => clearInterval(pollCA), 300000);
        }
      }
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [briefId]);

  const value = {
    briefId,
    navigate,
    activeModule,
    setActiveModule,
    loading,
    step2Complete,
    initialLoadDone,
    modules,
    fetchModule,
    runModule,
    STATUS,
  };

  return <IntelContext.Provider value={value}>{children}</IntelContext.Provider>;
};
