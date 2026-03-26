import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Download } from 'lucide-react';
import { useIntel } from '../IntelligenceContext';
import { IntelSidebar } from './IntelSidebar';
import Logo from '@/components/Logo';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';

export const IntelLayout = ({ children }) => {
  const { briefId, navigate, loading } = useIntel();
  const { isAuthenticated, loginWithGoogle } = useAuth();
  const [downloading, setDownloading] = useState(false);

  const handleDownloadPDF = async () => {
    setDownloading(true);
    try {
      const response = await api.get(`/research/${briefId}/export/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `novara-report-${briefId.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('PDF download failed', err);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-screen w-full bg-[#030303] flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="text-center"
        >
          <Loader2 className="w-6 h-6 animate-spin text-white/60 mx-auto mb-4" />
          <div className="text-white/40 font-mono text-xs tracking-wider uppercase">Loading Intelligence</div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-[#030303] overflow-hidden" data-testid="intel-layout">
      {/* Sidebar */}
      <IntelSidebar />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top header */}
        <header className="h-14 border-b border-white/[0.06] bg-[#030303]/80 backdrop-blur-xl flex items-center justify-between px-6 shrink-0 z-30">
          <div className="flex items-center gap-6">
            <Logo size="small" />
            <div className="h-4 w-px bg-white/10" />
            <span className="text-white/30 font-mono text-[11px] tracking-wider uppercase">Intelligence Hub</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              onClick={handleDownloadPDF}
              disabled={downloading}
              className="text-white/50 hover:text-white hover:bg-white/5 text-xs uppercase tracking-wider h-8 px-3 gap-1.5"
              data-testid="download-report-btn"
            >
              {downloading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
              Report
            </Button>
            <div className="h-4 w-px bg-white/[0.06]" />
            <Button
              variant="ghost"
              onClick={() => navigate(`/pack/${briefId}`)}
              className="text-white/50 hover:text-white hover:bg-white/5 text-xs uppercase tracking-wider h-8 px-3"
              data-testid="nav-business-dna"
            >
              Business DNA
            </Button>
            {isAuthenticated ? (
              <Button
                variant="ghost"
                onClick={() => navigate('/dashboard')}
                className="text-white/50 hover:text-white hover:bg-white/5 text-xs uppercase tracking-wider h-8 px-3"
                data-testid="nav-dashboard"
              >
                Dashboard
              </Button>
            ) : (
              <Button
                variant="ghost"
                onClick={() => loginWithGoogle()}
                className="text-white/50 hover:text-white hover:bg-white/5 text-xs uppercase tracking-wider h-8 px-3"
                data-testid="nav-sign-in"
              >
                Sign In
              </Button>
            )}
          </div>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto scroll-smooth">
          <div className="max-w-6xl mx-auto px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
