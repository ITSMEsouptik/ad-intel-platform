import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  ChevronDown, 
  ChevronRight, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Clock,
  RefreshCw,
  Copy,
  ExternalLink,
  ArrowLeft
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Status badge component
const StatusBadge = ({ status }) => {
  const styles = {
    success: 'bg-green-500/20 text-green-400 border-green-500/30',
    running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    partial: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    not_started: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    needs_user_input: 'bg-orange-500/20 text-orange-400 border-orange-500/30'
  };
  
  const icons = {
    success: <CheckCircle className="w-3 h-3" />,
    running: <RefreshCw className="w-3 h-3 animate-spin" />,
    partial: <AlertTriangle className="w-3 h-3" />,
    failed: <XCircle className="w-3 h-3" />,
    not_started: <Clock className="w-3 h-3" />,
    needs_user_input: <AlertTriangle className="w-3 h-3" />
  };
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium border rounded ${styles[status] || styles.not_started}`}>
      {icons[status] || icons.not_started}
      {status?.replace(/_/g, ' ') || 'unknown'}
    </span>
  );
};

// Collapsible section component
const CollapsibleSection = ({ title, children, defaultOpen = false, level = "info" }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  const levelStyles = {
    info: 'border-gray-700',
    success: 'border-green-700',
    warning: 'border-yellow-700',
    error: 'border-red-700'
  };
  
  return (
    <div className={`border ${levelStyles[level]} rounded mb-2`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-white/5 transition-colors"
      >
        <span className="flex items-center gap-2 font-medium text-sm">
          {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          {title}
        </span>
      </button>
      {isOpen && (
        <div className="px-3 pb-3 border-t border-gray-800">
          {children}
        </div>
      )}
    </div>
  );
};

// JSON viewer component
const JsonViewer = ({ data, maxHeight = "300px" }) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="relative">
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 p-1 bg-gray-800 rounded hover:bg-gray-700 transition-colors"
        title="Copy JSON"
      >
        {copied ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
      </button>
      <pre 
        className="bg-gray-900 p-3 rounded text-xs overflow-auto font-mono"
        style={{ maxHeight }}
      >
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
};

// Key-value display component
const KeyValue = ({ label, value, type = "text" }) => {
  if (value === null || value === undefined || value === '') {
    return (
      <div className="flex gap-2 py-1 text-sm">
        <span className="text-gray-500 min-w-[140px]">{label}:</span>
        <span className="text-gray-600 italic">not found</span>
      </div>
    );
  }
  
  if (type === "list" && Array.isArray(value)) {
    return (
      <div className="py-1 text-sm">
        <span className="text-gray-500">{label}:</span>
        <ul className="ml-4 mt-1">
          {value.slice(0, 10).map((item, i) => (
            <li key={i} className="text-gray-300 py-0.5">• {typeof item === 'object' ? JSON.stringify(item) : item}</li>
          ))}
          {value.length > 10 && <li className="text-gray-500 italic">... and {value.length - 10} more</li>}
        </ul>
      </div>
    );
  }
  
  if (type === "object" && typeof value === 'object') {
    return (
      <div className="py-1 text-sm">
        <span className="text-gray-500">{label}:</span>
        <JsonViewer data={value} maxHeight="150px" />
      </div>
    );
  }
  
  return (
    <div className="flex gap-2 py-1 text-sm">
      <span className="text-gray-500 min-w-[140px]">{label}:</span>
      <span className="text-gray-300">{String(value)}</span>
    </div>
  );
};

// Campaign List Component
const CampaignList = ({ campaigns, selectedId, onSelect }) => {
  return (
    <div className="space-y-2">
      {campaigns.map((campaign) => (
        <button
          key={campaign.campaign_brief_id}
          onClick={() => onSelect(campaign.campaign_brief_id)}
          className={`w-full p-3 rounded border text-left transition-colors ${
            selectedId === campaign.campaign_brief_id
              ? 'border-white bg-white/10'
              : 'border-gray-700 hover:border-gray-600 hover:bg-white/5'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium text-sm truncate max-w-[200px]">
              {campaign.website_url?.replace(/https?:\/\/(www\.)?/, '') || 'No URL'}
            </span>
            {campaign.has_errors && <XCircle className="w-4 h-4 text-red-400" />}
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>{new Date(campaign.created_at).toLocaleDateString()}</span>
            <span>•</span>
            <StatusBadge status={campaign.step3a_status !== 'not_started' ? campaign.step3a_status : campaign.step2_status} />
          </div>
        </button>
      ))}
    </div>
  );
};

// Step 1 Debug Panel
const Step1Panel = ({ data }) => {
  if (!data) return <p className="text-gray-500 text-sm">No data</p>;
  
  return (
    <div className="space-y-4">
      <CollapsibleSection title="📝 Raw Form Input" defaultOpen={true}>
        <div className="mt-2 space-y-1">
          <KeyValue label="Website URL" value={data.input?.website_url} />
          <KeyValue label="Primary Goal" value={data.input?.primary_goal} />
          <KeyValue label="Success Definition" value={data.input?.success_definition} />
          <KeyValue label="Country" value={data.input?.country} />
          <KeyValue label="City/Region" value={data.input?.city_or_region} />
          <KeyValue label="Destination" value={data.input?.destination_type} />
          <KeyValue label="Ads Intent" value={data.input?.ads_intent} />
          <KeyValue label="Budget Range" value={data.input?.budget_range} />
          <KeyValue label="Contact Name" value={data.input?.contact_name} />
          <KeyValue label="Contact Email" value={data.input?.contact_email} />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="⚙️ Computed Values">
        <div className="mt-2 space-y-1">
          <KeyValue label="Track" value={data.computed?.track} />
          <KeyValue label="Created At" value={data.computed?.created_at} />
        </div>
      </CollapsibleSection>
    </div>
  );
};

// Step 2 Debug Panel
const Step2Panel = ({ data, status, confidence }) => {
  if (!data) return <p className="text-gray-500 text-sm">Step 2 not started yet</p>;
  
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 mb-4">
        <StatusBadge status={status} />
        {confidence && (
          <span className="text-sm">
            Confidence: <span className={confidence >= 60 ? 'text-green-400' : 'text-yellow-400'}>{confidence}/100</span>
          </span>
        )}
      </div>
      
      <CollapsibleSection title="🌐 Crawl Source" defaultOpen={true}>
        <div className="mt-2 space-y-1">
          <KeyValue label="Input URL" value={data.source?.website_url} />
          <KeyValue label="Final URL" value={data.source?.final_url} />
          <KeyValue label="Fetch Method" value={data.source?.fetch_method} />
          <KeyValue label="Pages Attempted" value={data.source?.pages_attempted} />
          <KeyValue label="Pages Fetched" value={data.source?.pages_fetched} />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="🏷️ Brand Identity">
        <div className="mt-2 space-y-1">
          <KeyValue label="Brand Name" value={data.brand_identity?.brand_name} />
          <KeyValue label="Tagline" value={data.brand_identity?.tagline} />
          <KeyValue label="Value Prop" value={data.brand_identity?.one_liner_value_prop} />
          <KeyValue label="Logo URL" value={data.brand_identity?.visual?.logo_asset_url} />
          <KeyValue label="Colors" value={data.brand_identity?.visual?.primary_colors_hex} type="list" />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="💼 Offer">
        <div className="mt-2 space-y-1">
          <KeyValue label="Offer Type" value={data.offer?.offer_type_hint} />
          <KeyValue label="Offer Summary" value={data.offer?.primary_offer_summary} />
          <KeyValue label="Key Benefits" value={data.offer?.key_benefits} type="list" />
          <KeyValue label="Differentiators" value={data.offer?.differentiators} type="list" />
          <KeyValue label="Pricing" value={data.offer?.pricing_mentions} type="list" />
          <KeyValue label="FAQ Questions" value={data.offer?.faq_questions} type="list" />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="✅ Proof & Trust">
        <div className="mt-2 space-y-1">
          <KeyValue label="Trust Signals" value={data.proof?.trust_signals} type="list" />
          <KeyValue label="Testimonials" value={data.proof?.testimonials?.length || 0} />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="🎯 Conversion">
        <div className="mt-2 space-y-1">
          <KeyValue label="Primary Action" value={data.conversion?.primary_action} />
          <KeyValue label="CTAs Found" value={data.conversion?.detected_primary_ctas} type="list" />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="📱 Site Info">
        <div className="mt-2 space-y-1">
          <KeyValue label="Social Links" value={data.site?.social_links} type="object" />
          <KeyValue label="Emails" value={data.site?.contact?.emails} type="list" />
          <KeyValue label="Phones" value={data.site?.contact?.phones} type="list" />
          <KeyValue label="Currency" value={data.site?.currency_hint} />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="📄 Pages Crawled">
        <div className="mt-2">
          {data.content_index?.pages_crawled?.map((page, i) => (
            <div key={i} className="border border-gray-800 rounded p-2 mb-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-gray-400">{page.url}</span>
                <span className="text-xs bg-gray-800 px-2 py-0.5 rounded">{page.page_type}</span>
              </div>
              <p className="text-sm text-gray-300 mt-1">{page.title}</p>
              <p className="text-xs text-gray-500 mt-1">H1: {page.h1 || 'none'}</p>
            </div>
          ))}
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="📊 Quality Assessment">
        <div className="mt-2 space-y-1">
          <KeyValue label="Confidence Score" value={`${data.quality?.confidence_score_0_100}/100`} />
          <KeyValue label="Missing Fields" value={data.quality?.missing_fields} type="list" />
          <KeyValue label="Warnings" value={data.quality?.warnings} type="list" />
          <KeyValue label="Errors" value={data.quality?.errors} type="list" />
        </div>
      </CollapsibleSection>
    </div>
  );
};

// Step 3A Debug Panel
const Step3APanel = ({ data, status, briefId }) => {
  const [prompt, setPrompt] = useState(null);
  const [rawResponse, setRawResponse] = useState(null);
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [loadingRaw, setLoadingRaw] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState('output');
  
  const loadPrompt = async () => {
    if (prompt) return; // Already loaded
    setLoadingPrompt(true);
    try {
      const response = await axios.get(`${API_URL}/api/debug/campaign/${briefId}/prompt`);
      setPrompt(response.data);
    } catch (error) {
      console.error('Error loading prompt:', error);
    }
    setLoadingPrompt(false);
  };
  
  const loadRawResponse = async () => {
    if (rawResponse) return; // Already loaded
    setLoadingRaw(true);
    try {
      const response = await axios.get(`${API_URL}/api/debug/campaign/${briefId}/raw-response`);
      setRawResponse(response.data);
    } catch (error) {
      console.error('Error loading raw response:', error);
    }
    setLoadingRaw(false);
  };
  
  // Load data when switching tabs
  useEffect(() => {
    if (activeSubTab === 'payload' && !prompt) {
      loadPrompt();
    }
    if (activeSubTab === 'raw' && !rawResponse) {
      loadRawResponse();
    }
  }, [activeSubTab]);
  
  if (!data && status === 'not_started') {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 text-sm mb-4">Step 3A not started yet</p>
        <button
          onClick={loadPrompt}
          disabled={loadingPrompt}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded text-sm transition-colors"
        >
          {loadingPrompt ? 'Loading...' : 'Preview What Will Be Sent to Perplexity'}
        </button>
        {prompt && (
          <div className="mt-4 text-left">
            <PromptPayloadView prompt={prompt} />
          </div>
        )}
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <StatusBadge status={status} />
        
        {/* Sub-tabs for Step 3A */}
        <div className="flex bg-gray-800 rounded p-1">
          {[
            { id: 'output', label: 'AI Output' },
            { id: 'payload', label: '📤 Sent' },
            { id: 'raw', label: '📥 Raw Response' },
            { id: 'analysis', label: '🔍 Analysis' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                activeSubTab === tab.id
                  ? 'bg-white text-black'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Payload Tab - What was sent to Perplexity */}
      {activeSubTab === 'payload' && (
        <div className="space-y-4">
          {loadingPrompt ? (
            <div className="text-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
              <p className="text-gray-500 text-sm">Loading prompt data...</p>
            </div>
          ) : prompt ? (
            <PromptPayloadView prompt={prompt} />
          ) : (
            <button
              onClick={loadPrompt}
              className="w-full py-4 bg-white/5 hover:bg-white/10 rounded text-sm transition-colors"
            >
              Load Prompt Payload
            </button>
          )}
        </div>
      )}
      
      {/* Raw Response Tab - What Perplexity returned */}
      {activeSubTab === 'raw' && (
        <div className="space-y-4">
          {loadingRaw ? (
            <div className="text-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
              <p className="text-gray-500 text-sm">Loading raw response...</p>
            </div>
          ) : rawResponse ? (
            <RawResponseView data={rawResponse} />
          ) : (
            <button
              onClick={loadRawResponse}
              className="w-full py-4 bg-white/5 hover:bg-white/10 rounded text-sm transition-colors"
            >
              Load Raw API Response
            </button>
          )}
        </div>
      )}
      
      {/* Analysis Tab - Data quality insights */}
      {activeSubTab === 'analysis' && (
        <DataQualityAnalysis data={data} />
      )}
      
      {/* Output Tab - Perplexity response */}
      {activeSubTab === 'output' && (
        <Step3AOutputView data={data} />
      )}
    </div>
  );
};

// Prompt Payload View Component
const PromptPayloadView = ({ prompt }) => {
  const [copied, setCopied] = useState(null);
  
  const handleCopy = (text, type) => {
    navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };
  
  return (
    <div className="space-y-4">
      {/* API Configuration */}
      <CollapsibleSection title="⚙️ API Configuration" defaultOpen={true}>
        <div className="mt-2 grid grid-cols-2 gap-4">
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Endpoint</p>
            <p className="text-sm font-mono">{prompt.api_config?.endpoint}</p>
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Model</p>
            <p className="text-sm font-mono text-green-400">{prompt.api_config?.model}</p>
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Temperature</p>
            <p className="text-sm font-mono">{prompt.api_config?.temperature}</p>
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Max Tokens</p>
            <p className="text-sm font-mono">{prompt.api_config?.max_tokens}</p>
          </div>
        </div>
        <div className="mt-2 flex gap-4 text-xs text-gray-500">
          <span>System prompt: {prompt.system_prompt_chars} chars</span>
          <span>User prompt: {prompt.user_prompt_chars} chars</span>
          <span>Schema: {prompt.schema_fields} fields</span>
        </div>
      </CollapsibleSection>
      
      {/* System Prompt */}
      <CollapsibleSection title="🤖 System Prompt (Role Definition)" defaultOpen={false}>
        <div className="mt-2 relative">
          <button
            onClick={() => handleCopy(prompt.system_prompt, 'system')}
            className="absolute top-2 right-2 p-1 bg-gray-700 rounded hover:bg-gray-600 transition-colors z-10"
            title="Copy"
          >
            {copied === 'system' ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <pre className="bg-gray-900 p-4 rounded text-xs overflow-auto whitespace-pre-wrap max-h-48 font-mono">
            {prompt.system_prompt}
          </pre>
        </div>
      </CollapsibleSection>
      
      {/* User Prompt - THE MAIN ONE */}
      <CollapsibleSection title="📝 User Prompt (Input Data + Instructions)" defaultOpen={true} level="success">
        <div className="mt-2 relative">
          <button
            onClick={() => handleCopy(prompt.user_prompt, 'user')}
            className="absolute top-2 right-2 p-1 bg-gray-700 rounded hover:bg-gray-600 transition-colors z-10"
            title="Copy"
          >
            {copied === 'user' ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <pre className="bg-gray-900 p-4 rounded text-xs overflow-auto whitespace-pre-wrap max-h-[500px] font-mono leading-relaxed">
            {prompt.user_prompt}
          </pre>
        </div>
        <div className="mt-2 p-2 bg-blue-900/20 border border-blue-800 rounded text-xs">
          <p className="text-blue-400 font-medium mb-1">💡 What's in this prompt:</p>
          <ul className="text-gray-400 space-y-1">
            <li>• <strong>Brand context:</strong> Website URL, geo, goal, budget from Step 1</li>
            <li>• <strong>Known brand facts:</strong> Extracted data from Step 2 (brand name, offer, CTAs, etc.)</li>
            <li>• <strong>Tasks:</strong> Instructions for what Perplexity should analyze and return</li>
          </ul>
        </div>
      </CollapsibleSection>
      
      {/* Full API Request Payload */}
      <CollapsibleSection title="📦 Full API Request (JSON)" defaultOpen={false}>
        <div className="mt-2 relative">
          <button
            onClick={() => handleCopy(JSON.stringify({
              model: prompt.api_config?.model,
              messages: [
                { role: "system", content: prompt.system_prompt },
                { role: "user", content: prompt.user_prompt }
              ],
              temperature: prompt.api_config?.temperature,
              max_tokens: prompt.api_config?.max_tokens,
              response_format: { type: "json_schema", json_schema: { schema: "..." } }
            }, null, 2), 'full')}
            className="absolute top-2 right-2 p-1 bg-gray-700 rounded hover:bg-gray-600 transition-colors z-10"
            title="Copy"
          >
            {copied === 'full' ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <pre className="bg-gray-900 p-4 rounded text-xs overflow-auto max-h-64 font-mono">
{`{
  "model": "${prompt.api_config?.model}",
  "messages": [
    { "role": "system", "content": "<system_prompt>" },
    { "role": "user", "content": "<user_prompt>" }
  ],
  "temperature": ${prompt.api_config?.temperature},
  "max_tokens": ${prompt.api_config?.max_tokens},
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "schema": { /* ${prompt.schema_fields} fields enforced */ }
    }
  }
}`}
          </pre>
        </div>
      </CollapsibleSection>
    </div>
  );
};

// Raw Response View Component - Shows exact Perplexity API response
const RawResponseView = ({ data }) => {
  const [copied, setCopied] = useState(null);
  
  const handleCopy = (text, type) => {
    navigator.clipboard.writeText(typeof text === 'string' ? text : JSON.stringify(text, null, 2));
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };
  
  const apiResponse = data?.raw_api_response || {};
  const usage = apiResponse?.usage || {};
  const durationSeconds = apiResponse?.response_duration_seconds;
  
  return (
    <div className="space-y-4">
      {/* API Response Metadata */}
      <CollapsibleSection title="📊 Response Metadata" defaultOpen={true}>
        <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Status Code</p>
            <p className={`text-lg font-mono ${apiResponse.status_code === 200 ? 'text-green-400' : 'text-red-400'}`}>
              {apiResponse.status_code || 'N/A'}
            </p>
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Model Used</p>
            <p className="text-sm font-mono text-blue-400">{apiResponse.model || data?.api_metadata?.model || 'N/A'}</p>
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Response Time</p>
            <p className={`text-lg font-mono ${durationSeconds > 30 ? 'text-yellow-400' : 'text-green-400'}`}>
              {durationSeconds ? `${durationSeconds}s` : 'N/A'}
            </p>
            {durationSeconds && (
              <p className="text-xs text-gray-500 mt-1">
                {durationSeconds < 20 ? '⚡ Fast' : durationSeconds < 40 ? '⏱️ Normal' : '🐢 Slow'}
              </p>
            )}
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Citations</p>
            <p className="text-sm font-mono">{data?.api_metadata?.citations_count || apiResponse.citations?.length || 0}</p>
          </div>
        </div>
      </CollapsibleSection>
      
      {/* Token Usage */}
      <CollapsibleSection title="💰 Token Usage (Cost)" defaultOpen={true}>
        <div className="mt-2 grid grid-cols-3 gap-3">
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Prompt Tokens</p>
            <p className="text-lg font-mono">{usage.prompt_tokens || 'N/A'}</p>
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Completion Tokens</p>
            <p className="text-lg font-mono">{usage.completion_tokens || 'N/A'}</p>
          </div>
          <div className="bg-gray-900 p-3 rounded">
            <p className="text-xs text-gray-500 mb-1">Total Tokens</p>
            <p className="text-lg font-mono text-yellow-400">{usage.total_tokens || (usage.prompt_tokens + usage.completion_tokens) || 'N/A'}</p>
          </div>
        </div>
        {usage.total_tokens && (
          <p className="mt-2 text-xs text-gray-500">
            Estimated cost: ~${((usage.total_tokens / 1000) * 0.001).toFixed(4)} (at $0.001/1K tokens)
          </p>
        )}
      </CollapsibleSection>
      
      {/* Raw Content (the actual JSON string returned) */}
      <CollapsibleSection title="📄 Raw JSON Content (Perplexity's Response)" defaultOpen={true} level="success">
        <div className="mt-2 relative">
          <button
            onClick={() => handleCopy(data?.raw_content, 'content')}
            className="absolute top-2 right-2 p-1 bg-gray-700 rounded hover:bg-gray-600 transition-colors z-10"
            title="Copy"
          >
            {copied === 'content' ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <pre className="bg-gray-900 p-4 rounded text-xs overflow-auto whitespace-pre-wrap max-h-[500px] font-mono leading-relaxed">
            {data?.raw_content ? 
              (typeof data.raw_content === 'string' ? 
                JSON.stringify(JSON.parse(data.raw_content), null, 2) : 
                JSON.stringify(data.raw_content, null, 2)
              ) : 'No raw content available'
            }
          </pre>
        </div>
        <div className="mt-2 p-2 bg-green-900/20 border border-green-800 rounded text-xs">
          <p className="text-green-400 font-medium">✅ This is the EXACT JSON that Perplexity returned</p>
          <p className="text-gray-400 mt-1">This is what gets parsed and stored as the intel pack data.</p>
        </div>
      </CollapsibleSection>
      
      {/* Full API Response Object */}
      <CollapsibleSection title="🔧 Full API Response Object" defaultOpen={false}>
        <div className="mt-2 relative">
          <button
            onClick={() => handleCopy(apiResponse.response_body, 'full')}
            className="absolute top-2 right-2 p-1 bg-gray-700 rounded hover:bg-gray-600 transition-colors z-10"
            title="Copy"
          >
            {copied === 'full' ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <pre className="bg-gray-900 p-4 rounded text-xs overflow-auto max-h-96 font-mono">
            {JSON.stringify(apiResponse.response_body, null, 2) || 'No response body available'}
          </pre>
        </div>
      </CollapsibleSection>
      
      {/* Citations */}
      {(apiResponse.citations?.length > 0 || data?.search_results?.length > 0) && (
        <CollapsibleSection title="📚 Citations & Sources" defaultOpen={false}>
          <div className="mt-2 space-y-2">
            {(apiResponse.citations || data?.search_results || []).map((citation, i) => (
              <div key={i} className="bg-gray-900 p-2 rounded text-xs">
                {typeof citation === 'string' ? (
                  <a href={citation} target="_blank" rel="noopener noreferrer" 
                     className="text-blue-400 hover:underline break-all">
                    {citation}
                  </a>
                ) : (
                  <>
                    <p className="font-medium text-gray-300">{citation.title || `Source ${i + 1}`}</p>
                    <a href={citation.url} target="_blank" rel="noopener noreferrer" 
                       className="text-blue-400 hover:underline break-all text-xs">
                      {citation.url}
                    </a>
                  </>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
};

// Data Quality Analysis Component
const DataQualityAnalysis = ({ data }) => {
  // Analyze the quality of data
  const analysis = {
    category: {
      label: 'Category Detection',
      score: data?.category?.confidence_0_100 || 0,
      status: (data?.category?.confidence_0_100 || 0) >= 80 ? 'good' : (data?.category?.confidence_0_100 || 0) >= 60 ? 'ok' : 'poor',
      details: `${data?.category?.industry || 'Unknown'} > ${data?.category?.subcategory || 'Unknown'}`
    },
    competitors: {
      label: 'Competitor Discovery',
      score: Math.min(100, (data?.competitors?.length || 0) * 33),
      status: (data?.competitors?.length || 0) >= 3 ? 'good' : (data?.competitors?.length || 0) >= 2 ? 'ok' : 'poor',
      details: `Found ${data?.competitors?.length || 0} competitors`
    },
    psychology: {
      label: 'Customer Psychology',
      score: Math.min(100, ((data?.customer_psychology?.icp_segments?.length || 0) * 20) + ((data?.customer_psychology?.top_pains?.length || 0) * 10)),
      status: (data?.customer_psychology?.icp_segments?.length || 0) >= 3 ? 'good' : (data?.customer_psychology?.icp_segments?.length || 0) >= 2 ? 'ok' : 'poor',
      details: `${data?.customer_psychology?.icp_segments?.length || 0} ICPs, ${data?.customer_psychology?.top_pains?.length || 0} pains`
    },
    brandAudit: {
      label: 'Brand Audit',
      score: data?.brand_audit_lite?.archetype?.primary ? 80 : 40,
      status: data?.brand_audit_lite?.archetype?.primary ? 'good' : 'ok',
      details: `Archetype: ${data?.brand_audit_lite?.archetype?.primary || 'Unknown'}`
    },
    sources: {
      label: 'Research Sources',
      score: Math.min(100, (data?.sources?.length || 0) * 12),
      status: (data?.sources?.length || 0) >= 5 ? 'good' : (data?.sources?.length || 0) >= 3 ? 'ok' : 'poor',
      details: `${data?.sources?.length || 0} sources cited`
    }
  };
  
  const statusColors = {
    good: 'text-green-400 bg-green-400/20',
    ok: 'text-yellow-400 bg-yellow-400/20',
    poor: 'text-red-400 bg-red-400/20'
  };
  
  return (
    <div className="space-y-4">
      <div className="p-4 bg-gray-900 rounded">
        <h4 className="text-sm font-medium mb-3">📊 Intelligence Quality Scores</h4>
        <div className="space-y-3">
          {Object.entries(analysis).map(([key, item]) => (
            <div key={key} className="flex items-center gap-3">
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm">{item.label}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${statusColors[item.status]}`}>
                    {item.status.toUpperCase()}
                  </span>
                </div>
                <div className="h-2 bg-gray-800 rounded overflow-hidden">
                  <div 
                    className={`h-full transition-all ${
                      item.status === 'good' ? 'bg-green-500' : 
                      item.status === 'ok' ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${item.score}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{item.details}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Data Gaps / Warnings */}
      <CollapsibleSection title="⚠️ Potential Data Gaps" defaultOpen={true} level="warning">
        <div className="mt-2 space-y-2">
          {!data?.competitors?.length && (
            <div className="p-2 bg-red-900/20 border border-red-800 rounded text-xs text-red-300">
              No competitors found - may need manual research
            </div>
          )}
          {(data?.competitors || []).some(c => !c.instagram && !c.tiktok) && (
            <div className="p-2 bg-yellow-900/20 border border-yellow-800 rounded text-xs text-yellow-300">
              Some competitors missing social media links
            </div>
          )}
          {!data?.brand_audit_lite?.archetype?.primary && (
            <div className="p-2 bg-yellow-900/20 border border-yellow-800 rounded text-xs text-yellow-300">
              Brand archetype not identified with confidence
            </div>
          )}
          {(data?.sources?.length || 0) < 3 && (
            <div className="p-2 bg-yellow-900/20 border border-yellow-800 rounded text-xs text-yellow-300">
              Limited research sources ({data?.sources?.length || 0}) - results may be less reliable
            </div>
          )}
          {data?.category?.confidence_0_100 < 70 && (
            <div className="p-2 bg-yellow-900/20 border border-yellow-800 rounded text-xs text-yellow-300">
              Category confidence is low ({data?.category?.confidence_0_100}%) - may need verification
            </div>
          )}
          {!data?.competitors?.length && !data?.brand_audit_lite && !data?.category && (
            <div className="p-2 bg-gray-800 rounded text-xs text-gray-400">
              ✅ No major data gaps detected
            </div>
          )}
        </div>
      </CollapsibleSection>
      
      {/* Input vs Output Comparison */}
      <CollapsibleSection title="🔄 Input → Output Transformation" defaultOpen={false}>
        <div className="mt-2 text-xs text-gray-400">
          <p className="mb-2">How Perplexity enriched the data:</p>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-2">Input (Step 2)</th>
                <th className="text-left py-2">Output (Step 3A)</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-800">
                <td className="py-2">Brand name extracted</td>
                <td className="py-2">+ Industry classification, archetype, voice traits</td>
              </tr>
              <tr className="border-b border-gray-800">
                <td className="py-2">Offer summary</td>
                <td className="py-2">+ Positioning diagnosis, whitespace gaps, quick wins</td>
              </tr>
              <tr className="border-b border-gray-800">
                <td className="py-2">Geo location</td>
                <td className="py-2">+ Local behaviors, seasonality, market context</td>
              </tr>
              <tr className="border-b border-gray-800">
                <td className="py-2">CTAs found</td>
                <td className="py-2">+ Channel rankings, format recommendations</td>
              </tr>
              <tr>
                <td className="py-2">Trust signals</td>
                <td className="py-2">+ Competitor analysis, ICP segments, objections</td>
              </tr>
            </tbody>
          </table>
        </div>
      </CollapsibleSection>
    </div>
  );
};

// Step 3A Output View (the AI response)
const Step3AOutputView = ({ data }) => {
  return (
    <div className="space-y-4">
      <CollapsibleSection title="🏭 Category" defaultOpen={true}>
        <div className="mt-2 space-y-1">
          <KeyValue label="Industry" value={data?.category?.industry} />
          <KeyValue label="Subcategory" value={data?.category?.subcategory} />
          <KeyValue label="Confidence" value={`${data?.category?.confidence_0_100}%`} />
          <KeyValue label="Notes" value={data?.category?.notes} />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="🌍 Geo Context">
        <div className="mt-2 space-y-1">
          <KeyValue label="Primary Market" value={data?.geo_context?.primary_market} />
          <KeyValue label="Seasonality" value={data?.geo_context?.seasonality_or_moments} type="list" />
          <KeyValue label="Local Behaviors" value={data?.geo_context?.local_behavior_notes} />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="🏢 Competitors">
        <div className="mt-2">
          {data?.competitors?.map((comp, i) => (
            <div key={i} className="border border-gray-800 rounded p-2 mb-2">
              <p className="font-medium text-sm">{comp.name}</p>
              {comp.website && (
                <a href={comp.website} target="_blank" rel="noopener noreferrer" 
                   className="text-xs text-blue-400 hover:underline flex items-center gap-1">
                  {comp.website} <ExternalLink className="w-3 h-3" />
                </a>
              )}
              {comp.instagram && <p className="text-xs text-gray-500">IG: @{comp.instagram}</p>}
              {comp.positioning_summary && (
                <p className="text-xs text-gray-400 mt-1">{comp.positioning_summary}</p>
              )}
            </div>
          ))}
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="🧠 Customer Psychology">
        <div className="mt-2 space-y-2">
          <div>
            <p className="text-xs text-gray-500 mb-1">ICP Segments:</p>
            {data?.customer_psychology?.icp_segments?.map((seg, i) => (
              <div key={i} className="bg-gray-900 rounded p-2 mb-1 text-xs">
                <p className="font-medium">{seg.name}</p>
                <p className="text-gray-400">{seg.description}</p>
              </div>
            ))}
          </div>
          <KeyValue label="Top Pains" value={data?.customer_psychology?.top_pains} type="list" />
          <KeyValue label="Top Objections" value={data?.customer_psychology?.top_objections} type="list" />
          <KeyValue label="Buying Triggers" value={data?.customer_psychology?.buying_triggers} type="list" />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="🎨 Brand Audit">
        <div className="mt-2 space-y-1">
          <KeyValue label="Voice Traits" value={data?.brand_audit_lite?.voice?.traits} type="list" />
          <KeyValue label="Do List" value={data?.brand_audit_lite?.voice?.do_list} type="list" />
          <KeyValue label="Don't List" value={data?.brand_audit_lite?.voice?.dont_list} type="list" />
          <KeyValue label="Archetype" value={data?.brand_audit_lite?.archetype?.primary} />
          <KeyValue label="Secondary" value={data?.brand_audit_lite?.archetype?.secondary} />
          <KeyValue label="Visual Vibe" value={data?.brand_audit_lite?.visual_vibe?.vibe_keywords} type="list" />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="🔍 Foreplay Search Blueprint">
        <div className="mt-2 space-y-1">
          <KeyValue label="Competitor Queries" value={data?.foreplay_search_blueprint?.competitor_queries} type="list" />
          <KeyValue label="Keyword Queries" value={data?.foreplay_search_blueprint?.keyword_queries} type="list" />
          <KeyValue label="Angle Queries" value={data?.foreplay_search_blueprint?.angle_queries} type="list" />
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="📊 UI Summary Cards">
        <div className="mt-2">
          {data?.ui_summary?.cards?.map((card, i) => (
            <div key={i} className="border border-gray-800 rounded p-2 mb-2">
              <p className="font-medium text-sm">{card.title}</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {card.chips?.map((chip, j) => (
                  <span key={j} className="text-xs bg-gray-800 px-2 py-0.5 rounded">{chip}</span>
                ))}
              </div>
              <ul className="mt-1 text-xs text-gray-400">
                {card.bullets?.map((b, j) => <li key={j}>• {b}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </CollapsibleSection>
      
      <CollapsibleSection title="📚 Sources">
        <div className="mt-2">
          {data?.sources?.map((source, i) => (
            <a 
              key={i}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-xs text-blue-400 hover:underline py-1 truncate"
            >
              {source.title || source.url}
            </a>
          ))}
        </div>
      </CollapsibleSection>
    </div>
  );
};

// Main Debug Dashboard Component
const DebugDashboard = () => {
  const { briefId } = useParams();
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [debugData, setDebugData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [activeTab, setActiveTab] = useState('step1');
  
  // Load campaigns list
  const loadCampaigns = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/debug/campaigns`);
      setCampaigns(response.data.campaigns);
      
      // Auto-select if briefId in URL or first campaign
      if (briefId) {
        setSelectedCampaign(briefId);
      } else if (response.data.campaigns.length > 0 && !selectedCampaign) {
        setSelectedCampaign(response.data.campaigns[0].campaign_brief_id);
      }
    } catch (error) {
      console.error('Error loading campaigns:', error);
    }
    setLoading(false);
  }, [briefId, selectedCampaign]);
  
  // Load debug data for selected campaign
  const loadDebugData = useCallback(async () => {
    if (!selectedCampaign) return;
    
    try {
      const response = await axios.get(`${API_URL}/api/debug/campaign/${selectedCampaign}`);
      setDebugData(response.data);
    } catch (error) {
      console.error('Error loading debug data:', error);
    }
  }, [selectedCampaign]);
  
  // Initial load
  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);
  
  // Load debug data when campaign selected
  useEffect(() => {
    if (selectedCampaign) {
      loadDebugData();
    }
  }, [selectedCampaign, loadDebugData]);
  
  // Auto-refresh
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        loadDebugData();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, loadDebugData]);
  
  const handleCampaignSelect = (id) => {
    setSelectedCampaign(id);
    navigate(`/admin/debug/${id}`, { replace: true });
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="border-b border-gray-800 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/')}
              className="p-2 hover:bg-white/10 rounded transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-bold">🔍 Debug Dashboard</h1>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded"
              />
              Auto-refresh
            </label>
            <button
              onClick={loadDebugData}
              className="p-2 hover:bg-white/10 rounded transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>
      
      <div className="max-w-7xl mx-auto p-4 flex gap-6">
        {/* Sidebar - Campaign List */}
        <aside className="w-80 flex-shrink-0">
          <h2 className="text-sm font-medium text-gray-400 mb-3">Recent Campaigns</h2>
          <CampaignList 
            campaigns={campaigns}
            selectedId={selectedCampaign}
            onSelect={handleCampaignSelect}
          />
        </aside>
        
        {/* Main Content */}
        <main className="flex-1 min-w-0">
          {debugData ? (
            <>
              {/* Campaign Header */}
              <div className="mb-6">
                <h2 className="text-lg font-bold">
                  {debugData.step1?.data?.input?.website_url?.replace(/https?:\/\/(www\.)?/, '') || 'Unknown'}
                </h2>
                <p className="text-sm text-gray-500">
                  Campaign ID: {selectedCampaign?.slice(0, 8)}...
                </p>
              </div>
              
              {/* Step Tabs */}
              <div className="flex border-b border-gray-800 mb-4">
                {[
                  { id: 'step1', label: 'Step 1: Brief', status: debugData.step1?.status },
                  { id: 'step2', label: 'Step 2: Extract', status: debugData.step2?.status },
                  { id: 'step3a', label: 'Step 3A: Intel', status: debugData.step3a?.status },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-white text-white'
                        : 'border-transparent text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      {tab.label}
                      <StatusBadge status={tab.status} />
                    </span>
                  </button>
                ))}
              </div>
              
              {/* Tab Content */}
              <div className="bg-gray-900/50 rounded-lg p-4">
                {activeTab === 'step1' && <Step1Panel data={debugData.step1?.data} />}
                {activeTab === 'step2' && (
                  <Step2Panel 
                    data={debugData.step2?.data} 
                    status={debugData.step2?.status}
                    confidence={debugData.step2?.confidence_score}
                  />
                )}
                {activeTab === 'step3a' && (
                  <Step3APanel 
                    data={debugData.step3a?.data} 
                    status={debugData.step3a?.status}
                    briefId={selectedCampaign}
                  />
                )}
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-gray-500">
              Select a campaign to view debug data
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default DebugDashboard;
