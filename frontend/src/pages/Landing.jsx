import React from 'react';
import { ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Logo from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

const Landing = () => {
  const navigate = useNavigate();
  const { isAuthenticated, loginWithGoogle } = useAuth();

  const handleStart = () => {
    navigate('/wizard');
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-black/90 border-b border-white/10 z-50" data-testid="nav-bar">
        <div className="max-w-7xl mx-auto px-6 md:px-12 h-16 flex items-center justify-between">
          <Logo size="default" />
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <Button
                variant="ghost"
                className="text-white hover:text-gray-300 uppercase tracking-widest text-sm"
                onClick={() => navigate('/dashboard')}
                data-testid="dashboard-link"
              >
                Dashboard
              </Button>
            ) : (
              <Button
                variant="ghost"
                className="text-white hover:text-gray-300 uppercase tracking-widest text-sm"
                onClick={() => loginWithGoogle()}
                data-testid="sign-in-link"
              >
                Sign In
              </Button>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="pt-16">
        <section className="min-h-[calc(100vh-4rem)] flex flex-col justify-center px-6 md:px-12">
          <div className="max-w-7xl mx-auto w-full">
            {/* Grid background */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-[0.03]">
              <div 
                className="absolute inset-0"
                style={{
                  backgroundImage: `
                    linear-gradient(to right, rgba(255,255,255,0.1) 1px, transparent 1px),
                    linear-gradient(to bottom, rgba(255,255,255,0.1) 1px, transparent 1px)
                  `,
                  backgroundSize: '60px 60px'
                }}
              />
            </div>

            {/* Content */}
            <div className="relative z-10 max-w-4xl">
              {/* Tag */}
              <div 
                className="inline-block mb-8 opacity-0 animate-fade-in-up"
                style={{ animationDelay: '0.1s' }}
              >
                <span className="text-sm uppercase tracking-[0.3em] text-gray-500 font-mono">
                  AI-Powered Ad Intelligence
                </span>
              </div>

              {/* Main Headline */}
              <h1 
                className="font-heading text-5xl md:text-7xl lg:text-8xl font-bold tracking-tighter leading-[0.9] mb-8 opacity-0 animate-fade-in-up"
                style={{ animationDelay: '0.2s' }}
                data-testid="hero-headline"
              >
                Turn your website
                <br />
                <span className="text-gray-500">into a test plan.</span>
              </h1>

              {/* Subheadline */}
              <p 
                className="text-lg md:text-xl text-gray-400 max-w-2xl mb-12 leading-relaxed opacity-0 animate-fade-in-up"
                style={{ animationDelay: '0.3s' }}
                data-testid="hero-subheadline"
              >
                High-impact digital ads in bulk, powered by AI. 
                From strategy to creative, in minutes, not weeks.
              </p>

              {/* CTA */}
              <div 
                className="flex flex-col sm:flex-row gap-4 opacity-0 animate-fade-in-up"
                style={{ animationDelay: '0.4s' }}
              >
                <Button
                  onClick={handleStart}
                  className="bg-white text-black hover:bg-gray-200 rounded-none font-bold uppercase tracking-wider px-8 py-6 text-base transition-transform active:scale-95 group"
                  data-testid="get-started-btn"
                >
                  Get Started
                  <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" strokeWidth={1.5} />
                </Button>
                
                {!isAuthenticated && (
                  <Button
                    variant="outline"
                    onClick={() => loginWithGoogle()}
                    className="bg-transparent border border-white/30 text-white hover:bg-white hover:text-black rounded-none uppercase tracking-wider px-8 py-6 text-base"
                    data-testid="sign-in-btn"
                  >
                    Sign In
                  </Button>
                )}
              </div>
            </div>

            {/* Stats/Social Proof */}
            <div 
              className="mt-24 grid grid-cols-2 md:grid-cols-4 gap-px bg-white/10 opacity-0 animate-fade-in-up"
              style={{ animationDelay: '0.5s' }}
            >
              {[
                { value: '10x', label: 'Faster Production' },
                { value: '∞', label: 'Creative Variations' },
                { value: '24/7', label: 'AI-Powered' },
                { value: '0', label: 'Creative Bottlenecks' },
              ].map((stat, index) => (
                <div 
                  key={index}
                  className="bg-black p-6 md:p-8"
                >
                  <div className="font-heading text-3xl md:text-4xl font-bold mb-2">
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-500 uppercase tracking-wider">
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Philosophy Section */}
        <section className="border-t border-white/10 py-24 px-6 md:px-12">
          <div className="max-w-7xl mx-auto">
            <div className="grid md:grid-cols-2 gap-12 md:gap-24">
              <div>
                <h2 className="font-heading text-3xl md:text-4xl font-bold tracking-tight mb-6">
                  Creativity is not a luxury.
                  <br />
                  <span className="text-gray-500">It is infrastructure.</span>
                </h2>
              </div>
              <div className="space-y-6 text-gray-400">
                <p>
                  In a world where creative production is slow, expensive, and hit-or-miss, 
                  Novara delivers high-impact digital ads at scale.
                </p>
                <p>
                  We combine deep brand intelligence with proven creative frameworks 
                  to generate ads that convert, without the agency overhead.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How it Works */}
        <section className="border-t border-white/10 py-24 px-6 md:px-12">
          <div className="max-w-7xl mx-auto">
            <h2 className="font-heading text-sm uppercase tracking-[0.3em] text-gray-500 mb-12">
              How It Works
            </h2>
            
            <div className="grid md:grid-cols-3 gap-px bg-white/10">
              {[
                {
                  step: '01',
                  title: 'Brief',
                  description: 'Share your website, goals, and target market. Takes 5 minutes.'
                },
                {
                  step: '02',
                  title: 'Intelligence',
                  description: 'Our AI analyzes your brand, competitors, and winning ad patterns.'
                },
                {
                  step: '03',
                  title: 'Create',
                  description: 'Get strategic ad concepts with copy, ready for production.'
                },
              ].map((item, index) => (
                <div 
                  key={index}
                  className="bg-black p-8 md:p-12 group hover:bg-novara-graphite transition-colors"
                >
                  <div className="font-mono text-sm text-gray-600 mb-4">
                    {item.step}
                  </div>
                  <h3 className="font-heading text-2xl font-bold mb-4">
                    {item.title}
                  </h3>
                  <p className="text-gray-500">
                    {item.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="border-t border-white/10 py-24 px-6 md:px-12">
          <div className="max-w-7xl mx-auto text-center">
            <h2 className="font-heading text-4xl md:text-5xl font-bold tracking-tight mb-8">
              Ready to scale your creative?
            </h2>
            <Button
              onClick={handleStart}
              className="bg-white text-black hover:bg-gray-200 rounded-none font-bold uppercase tracking-wider px-12 py-6 text-base transition-transform active:scale-95 group"
              data-testid="bottom-cta-btn"
            >
              Start Now
              <ArrowRight className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1" strokeWidth={1.5} />
            </Button>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/10 py-12 px-6 md:px-12">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
            <Logo size="small" />
            <div className="text-sm text-gray-600">
              Commercial Expression, Engineered.
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default Landing;
