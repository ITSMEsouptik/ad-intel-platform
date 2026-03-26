import React, { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Check, Globe, Target, MapPin, Link2, TrendingUp, Wallet, Copy, ExternalLink } from 'lucide-react';
import Logo from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { campaignBriefApi } from '@/lib/api';

const BriefDetail = () => {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, loginWithGoogle } = useAuth();
  
  const [brief, setBrief] = useState(location.state?.brief || null);
  const [loading, setLoading] = useState(!location.state?.brief);
  const [copied, setCopied] = useState(false);
  const isNew = location.state?.isNew;

  useEffect(() => {
    if (!brief && id) {
      fetchBrief();
    }
  }, [id, brief]);

  const fetchBrief = async () => {
    try {
      const data = await campaignBriefApi.getById(id);
      setBrief(data);
    } catch (error) {
      console.error('Failed to fetch brief:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyBriefId = () => {
    navigator.clipboard.writeText(brief.campaign_brief_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getTrackBadge = (track) => {
    return track === 'pilot' ? (
      <span className="px-3 py-1 bg-white text-black text-xs uppercase tracking-wider font-bold">
        Pilot Track
      </span>
    ) : (
      <span className="px-3 py-1 bg-white/10 text-white border border-white/20 text-xs uppercase tracking-wider">
        Foundation Track
      </span>
    );
  };

  const formatGoal = (goal) => {
    const map = {
      'sales_orders': 'Get More Sales / Orders',
      'bookings_leads': 'Get More Bookings / Leads',
      'brand_awareness': 'Build Brand Awareness',
      'event_launch': 'Promote an Event / Launch',
    };
    return map[goal] || goal;
  };

  const formatBudget = (budget) => {
    const map = {
      '<300': 'Under $300',
      '300-1000': '$300 - $1,000',
      '1000-5000': '$1,000 - $5,000',
      '5000+': '$5,000+',
      'not_sure': 'Not Sure',
    };
    return map[budget] || budget;
  };

  const formatDestType = (type) => {
    const map = {
      'website': 'Website',
      'whatsapp': 'WhatsApp',
      'booking_link': 'Booking Link',
      'app': 'App',
      'dm': 'DM',
      'other': 'Other',
    };
    return map[type] || type;
  };

  const formatAdsIntent = (intent) => {
    const map = {
      'yes': 'Yes, in next 30 days',
      'not_yet': 'Not yet',
      'unsure': 'Unsure',
    };
    return map[intent] || intent;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white font-mono text-sm animate-pulse">
          Loading brief...
        </div>
      </div>
    );
  }

  if (!brief) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <h1 className="font-heading text-2xl font-bold mb-4">Brief not found</h1>
          <Button
            onClick={() => navigate('/')}
            className="bg-white text-black hover:bg-gray-200 rounded-none"
          >
            Go Home
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-black/90 border-b border-white/10 z-50">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-16 flex items-center justify-between">
          <Logo size="default" />
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <Button
                variant="ghost"
                onClick={() => navigate('/dashboard')}
                className="text-white hover:text-gray-300 uppercase tracking-widest text-sm"
                data-testid="dashboard-link"
              >
                Dashboard
              </Button>
            ) : (
              <Button
                variant="ghost"
                onClick={() => loginWithGoogle()}
                className="text-white hover:text-gray-300 uppercase tracking-widest text-sm"
                data-testid="sign-in-link"
              >
                Sign In
              </Button>
            )}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="pt-24 pb-12 px-6 md:px-12">
        <div className="max-w-4xl mx-auto">
          {/* Success Banner (only for new briefs) */}
          {isNew && (
            <div className="mb-8 p-6 bg-white/5 border border-white/10 animate-fade-in-up">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 bg-white text-black flex items-center justify-center flex-shrink-0">
                  <Check className="w-5 h-5" strokeWidth={2} />
                </div>
                <div>
                  <h2 className="font-heading text-xl font-bold mb-2">Campaign Brief Created</h2>
                  <p className="text-gray-400 mb-4">
                    Your brief has been saved. Sign in with Google to track your campaigns and access them anytime.
                  </p>
                  {!isAuthenticated && (
                    <Button
                      onClick={() => loginWithGoogle(`/brief/${brief.campaign_brief_id}`)}
                      className="bg-white text-black hover:bg-gray-200 rounded-none font-bold uppercase tracking-wider px-6 py-3"
                      data-testid="sign-in-to-save-btn"
                    >
                      Sign in to Save
                      <ArrowRight className="ml-2 h-4 w-4" strokeWidth={1.5} />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Header */}
          <div className="mb-12">
            <div className="flex items-center gap-4 mb-4">
              {getTrackBadge(brief.track)}
              <button
                onClick={copyBriefId}
                className="flex items-center gap-2 text-gray-500 hover:text-white transition-colors text-sm font-mono"
                data-testid="copy-brief-id"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    {brief.campaign_brief_id.slice(0, 8)}...
                  </>
                )}
              </button>
            </div>
            <h1 className="font-heading text-4xl md:text-5xl font-bold tracking-tight mb-4" data-testid="brief-title">
              Campaign Brief
            </h1>
            <p className="text-gray-500">
              Created {new Date(brief.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>

          {/* Brief Details Grid */}
          <div className="grid gap-px bg-white/10 mb-12">
            {/* Brand */}
            <div className="bg-black p-6 md:p-8">
              <div className="flex items-center gap-3 text-gray-500 mb-4">
                <Globe className="w-5 h-5" strokeWidth={1.5} />
                <span className="text-sm uppercase tracking-wider">Website</span>
              </div>
              <a 
                href={brief.brand.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-lg text-white hover:text-gray-300 transition-colors flex items-center gap-2"
                data-testid="brief-website"
              >
                {brief.brand.website_url}
                <ExternalLink className="w-4 h-4" strokeWidth={1.5} />
              </a>
            </div>

            {/* Goal */}
            <div className="grid md:grid-cols-2 gap-px bg-white/10">
              <div className="bg-black p-6 md:p-8">
                <div className="flex items-center gap-3 text-gray-500 mb-4">
                  <Target className="w-5 h-5" strokeWidth={1.5} />
                  <span className="text-sm uppercase tracking-wider">Goal</span>
                </div>
                <p className="text-xl font-bold" data-testid="brief-goal">{formatGoal(brief.goal.primary_goal)}</p>
              </div>
              <div className="bg-black p-6 md:p-8">
                <div className="text-gray-500 mb-4">
                  <span className="text-sm uppercase tracking-wider">Success Definition</span>
                </div>
                <p className="text-white" data-testid="brief-success">{brief.goal.success_definition}</p>
              </div>
            </div>

            {/* Location */}
            <div className="bg-black p-6 md:p-8">
              <div className="flex items-center gap-3 text-gray-500 mb-4">
                <MapPin className="w-5 h-5" strokeWidth={1.5} />
                <span className="text-sm uppercase tracking-wider">Location</span>
              </div>
              <p className="text-xl" data-testid="brief-location">
                {brief.geo.city_or_region}, {brief.geo.country}
              </p>
            </div>

            {/* Destination */}
            <div className="bg-black p-6 md:p-8">
              <div className="flex items-center gap-3 text-gray-500 mb-4">
                <Link2 className="w-5 h-5" strokeWidth={1.5} />
                <span className="text-sm uppercase tracking-wider">Conversion Destination</span>
              </div>
              <p className="text-xl" data-testid="brief-dest-type">{formatDestType(brief.destination.type)}</p>
            </div>

            {/* Ads & Budget */}
            <div className="grid md:grid-cols-2 gap-px bg-white/10">
              <div className="bg-black p-6 md:p-8">
                <div className="flex items-center gap-3 text-gray-500 mb-4">
                  <TrendingUp className="w-5 h-5" strokeWidth={1.5} />
                  <span className="text-sm uppercase tracking-wider">Ads Intent</span>
                </div>
                <p className="text-xl" data-testid="brief-ads-intent">{formatAdsIntent(brief.ads_intent)}</p>
              </div>
              <div className="bg-black p-6 md:p-8">
                <div className="flex items-center gap-3 text-gray-500 mb-4">
                  <Wallet className="w-5 h-5" strokeWidth={1.5} />
                  <span className="text-sm uppercase tracking-wider">Monthly Budget</span>
                </div>
                <p className="text-xl" data-testid="brief-budget">{formatBudget(brief.budget_range_monthly)}</p>
              </div>
            </div>

            {/* Contact */}
            <div className="bg-black p-6 md:p-8">
              <div className="text-gray-500 mb-4">
                <span className="text-sm uppercase tracking-wider">Contact</span>
              </div>
              <p className="text-xl mb-1" data-testid="brief-contact-name">{brief.contact.name}</p>
              <p className="text-gray-400 font-mono" data-testid="brief-contact-email">{brief.contact.email}</p>
            </div>
          </div>

          {/* Next Steps */}
          <div className="p-8 bg-novara-graphite border border-white/10">
            <h2 className="font-heading text-xl font-bold mb-4">What's Next?</h2>
            <p className="text-gray-400 mb-6">
              Your brand DNA has been extracted. Explore your results or dive into market intelligence.
            </p>
            <div className="flex flex-wrap gap-4">
              <Button
                onClick={() => navigate(`/pack/${brief.campaign_brief_id}`)}
                className="bg-white text-black hover:bg-gray-200 rounded-none font-bold uppercase tracking-wider px-6 py-3"
                data-testid="go-to-pack-btn"
              >
                Business DNA
                <ArrowRight className="ml-2 h-4 w-4" strokeWidth={1.5} />
              </Button>
              <Button
                onClick={() => navigate(`/intel/${brief.campaign_brief_id}`)}
                className="bg-transparent border border-white/30 text-white hover:bg-white hover:text-black rounded-none uppercase tracking-wider px-6 py-3"
                data-testid="go-to-intel-btn"
              >
                Intelligence Hub
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate('/wizard')}
                className="text-gray-500 hover:text-white rounded-none uppercase tracking-wider px-6 py-3"
                data-testid="create-another-btn"
              >
                Create Another
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default BriefDetail;
