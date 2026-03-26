import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Globe, ChevronDown } from 'lucide-react';
import Logo from '@/components/Logo';
import { campaignBriefApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

const COUNTRIES = [
  { name: 'United States', currency: 'USD', symbol: '$', rate: 1 },
  { name: 'United Kingdom', currency: 'GBP', symbol: '£', rate: 0.79 },
  { name: 'Canada', currency: 'CAD', symbol: 'C$', rate: 1.36 },
  { name: 'Australia', currency: 'AUD', symbol: 'A$', rate: 1.53 },
  { name: 'Germany', currency: 'EUR', symbol: '€', rate: 0.92 },
  { name: 'France', currency: 'EUR', symbol: '€', rate: 0.92 },
  { name: 'Spain', currency: 'EUR', symbol: '€', rate: 0.92 },
  { name: 'Italy', currency: 'EUR', symbol: '€', rate: 0.92 },
  { name: 'Netherlands', currency: 'EUR', symbol: '€', rate: 0.92 },
  { name: 'Sweden', currency: 'SEK', symbol: 'kr', rate: 10.5 },
  { name: 'Norway', currency: 'NOK', symbol: 'kr', rate: 10.8 },
  { name: 'Denmark', currency: 'DKK', symbol: 'kr', rate: 6.9 },
  { name: 'India', currency: 'INR', symbol: '₹', rate: 83 },
  { name: 'Singapore', currency: 'SGD', symbol: 'S$', rate: 1.34 },
  { name: 'Japan', currency: 'JPY', symbol: '¥', rate: 149 },
  { name: 'South Korea', currency: 'KRW', symbol: '₩', rate: 1320 },
  { name: 'Brazil', currency: 'BRL', symbol: 'R$', rate: 4.97 },
  { name: 'Mexico', currency: 'MXN', symbol: 'MX$', rate: 17.1 },
  { name: 'United Arab Emirates', currency: 'AED', symbol: 'د.إ', rate: 3.67 },
  { name: 'Saudi Arabia', currency: 'SAR', symbol: '﷼', rate: 3.75 },
  { name: 'South Africa', currency: 'ZAR', symbol: 'R', rate: 18.5 },
  { name: 'Other', currency: 'USD', symbol: '$', rate: 1 },
];

const Wizard = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [country, setCountry] = useState('');
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');
  const [error, setError] = useState('');
  const [urlFocused, setUrlFocused] = useState(false);

  // Filter countries based on search
  const filteredCountries = useMemo(() => {
    if (!countrySearch) return COUNTRIES;
    return COUNTRIES.filter(c => c.name.toLowerCase().includes(countrySearch.toLowerCase()));
  }, [countrySearch]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (!e.target.closest('[data-testid="country-selector"]')) {
        setShowCountryDropdown(false);
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  const validate = () => {
    if (!websiteUrl.trim()) {
      setError('Enter your website URL');
      return false;
    }
    const urlPattern = /^(https?:\/\/)?[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+/;
    if (!urlPattern.test(websiteUrl.trim())) {
      setError('Enter a valid domain (e.g., yoursite.com)');
      return false;
    }
    if (!country) {
      setError('Select your country');
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    setError('');
    if (!validate()) return;
    setIsSubmitting(true);
    try {
      const brief = await campaignBriefApi.create({
        website_url: websiteUrl.trim(),
        country,
        name: user?.name || '',
        email: user?.email || '',
      });
      navigate(`/building/${brief.campaign_brief_id}`);
    } catch (err) {
      console.error('Failed to create brief:', err);
      setError('Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && websiteUrl && country) {
      handleSubmit();
    }
  };

  const selectedCountryObj = COUNTRIES.find(c => c.name === country);

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Nav */}
      <nav className="fixed top-0 w-full bg-black/90 border-b border-white/10 z-50">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-16 flex items-center justify-between">
          <Logo size="default" />
          <button
            onClick={() => navigate('/')}
            className="text-gray-500 hover:text-white text-sm uppercase tracking-wider transition-colors"
            data-testid="exit-wizard-btn"
          >
            Exit
          </button>
        </div>
      </nav>

      {/* Hero input */}
      <main className="flex-1 flex items-center justify-center px-6 pt-16">
        <div className="w-full max-w-2xl">
          {/* Header */}
          <div className="mb-12 text-center">
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500 mb-4">
              Ad Intelligence
            </p>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-tight">
              Enter your website.
              <br />
              <span className="text-gray-500">Get your ad strategy.</span>
            </h1>
          </div>

          {/* URL Input — the hero */}
          <div className="space-y-4">
            <div
              className={`relative border transition-all duration-200 ${
                urlFocused
                  ? 'border-white bg-white/[0.03]'
                  : 'border-white/20 hover:border-white/40'
              }`}
            >
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500">
                <Globe size={18} />
              </div>
              <input
                type="text"
                value={websiteUrl}
                onChange={(e) => { setWebsiteUrl(e.target.value); setError(''); }}
                onFocus={() => setUrlFocused(true)}
                onBlur={() => setUrlFocused(false)}
                onKeyDown={handleKeyDown}
                placeholder="yourwebsite.com"
                className="w-full bg-transparent text-white placeholder:text-gray-600 h-16 pl-12 pr-4 text-lg font-mono focus:outline-none"
                autoFocus
                data-testid="input-website-url"
              />
            </div>

            {/* Country selector */}
            <div className="relative" data-testid="country-selector">
              <button
                type="button"
                onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                className={`w-full flex items-center justify-between border transition-colors h-14 px-4 text-left ${
                  country
                    ? 'border-white/20 text-white'
                    : 'border-white/10 text-gray-500'
                } hover:border-white/40`}
                data-testid="select-country"
              >
                <span className={country ? 'text-white' : 'text-gray-500'}>
                  {country || 'Select your target country'}
                </span>
                <ChevronDown size={16} className={`transition-transform ${showCountryDropdown ? 'rotate-180' : ''}`} />
              </button>

              {showCountryDropdown && (
                <div className="absolute z-50 w-full mt-1 bg-[#111] border border-white/20 max-h-64 overflow-auto">
                  <div className="sticky top-0 bg-[#111] border-b border-white/10 p-2">
                    <input
                      type="text"
                      value={countrySearch}
                      onChange={(e) => setCountrySearch(e.target.value)}
                      placeholder="Search..."
                      className="w-full bg-transparent text-white placeholder:text-gray-600 text-sm px-2 py-1.5 focus:outline-none"
                      autoFocus
                    />
                  </div>
                  {filteredCountries.map(c => (
                    <button
                      key={c.name}
                      type="button"
                      onClick={() => {
                        setCountry(c.name);
                        setShowCountryDropdown(false);
                        setCountrySearch('');
                        setError('');
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm transition-colors ${
                        country === c.name
                          ? 'bg-white/10 text-white'
                          : 'text-gray-400 hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Error */}
            {error && (
              <p className="text-red-400 text-sm" data-testid="wizard-error">{error}</p>
            )}

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={isSubmitting || !websiteUrl || !country}
              className={`w-full h-14 font-medium text-sm uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                isSubmitting || !websiteUrl || !country
                  ? 'bg-white/10 text-gray-500 cursor-not-allowed'
                  : 'bg-white text-black hover:bg-gray-200'
              }`}
              data-testid="btn-analyze"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  Analyze <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>

          {/* Subtle hint */}
          <p className="text-center text-xs text-gray-600 mt-6">
            We'll analyze your brand, competitors, and winning ads in your category.
          </p>
        </div>
      </main>
    </div>
  );
};

export default Wizard;
