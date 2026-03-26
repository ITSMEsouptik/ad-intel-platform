import React, { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { exchangeSession } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      // Extract session_id from URL fragment
      const hash = location.hash;
      const params = new URLSearchParams(hash.replace('#', ''));
      const sessionId = params.get('session_id');

      if (!sessionId) {
        console.error('No session_id in URL');
        navigate('/');
        return;
      }

      try {
        await exchangeSession(sessionId);
        // Clear the hash and navigate to dashboard
        navigate('/dashboard', { replace: true });
      } catch (error) {
        console.error('Auth callback failed:', error);
        navigate('/');
      }
    };

    processAuth();
  }, [location.hash, exchangeSession, navigate]);

  // Minimal loading UI - process silently
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-white font-mono text-sm animate-pulse">
        Authenticating...
      </div>
    </div>
  );
};

export default AuthCallback;
