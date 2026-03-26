import React from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import Landing from '@/pages/Landing';
import Wizard from '@/pages/Wizard';
import Dashboard from '@/pages/Dashboard';
import BriefDetail from '@/pages/BriefDetail';
import AuthCallback from '@/pages/AuthCallback';
import BuildingPack from '@/pages/BuildingPack';
import PackView from '@/pages/PackView';
import IntelligenceHub from '@/pages/IntelligenceHub';
import DebugDashboard from '@/pages/DebugDashboard';
import '@/App.css';

// Router wrapper to handle auth callback detection
const AppRouter = () => {
  const location = useLocation();
  
  // Check URL fragment for session_id synchronously during render
  // This prevents race conditions by processing new session_id FIRST
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/wizard" element={<Wizard />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/brief/:id" element={<BriefDetail />} />
      <Route path="/building/:briefId" element={<BuildingPack />} />
      <Route path="/pack/:briefId" element={<PackView />} />
      <Route path="/intel/:briefId" element={<IntelligenceHub />} />
      <Route path="/research/:briefId" element={<IntelligenceHub />} />
      <Route path="/admin/debug" element={<DebugDashboard />} />
      <Route path="/admin/debug/:briefId" element={<DebugDashboard />} />
    </Routes>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
