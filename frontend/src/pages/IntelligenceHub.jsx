import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { IntelProvider, useIntel } from '@/components/intelligence/IntelligenceContext';
import { IntelLayout } from '@/components/intelligence/layout/IntelLayout';
import {
  OverviewTab,
  CustomerIntelTab,
  SearchDemandTab,
  SeasonalityTab,
  CompetitorsTab,
  ReviewsTab,
  CommunityTab,
  PressMediaTab,
  SocialTrendsTab,
  AdsIntelTab,
} from '@/components/intelligence/modules';

const MODULE_COMPONENTS = {
  overview: OverviewTab,
  customerIntel: CustomerIntelTab,
  searchIntent: SearchDemandTab,
  seasonality: SeasonalityTab,
  competitors: CompetitorsTab,
  reviews: ReviewsTab,
  community: CommunityTab,
  pressMedia: PressMediaTab,
  socialTrends: SocialTrendsTab,
  adsIntel: AdsIntelTab,
};

class ModuleErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidUpdate(prevProps) {
    if (prevProps.moduleKey !== this.props.moduleKey) {
      this.setState({ hasError: false });
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center py-24 text-white/30 text-sm font-mono">
          Failed to render module — try refreshing.
        </div>
      );
    }
    return this.props.children;
  }
}

const IntelContent = () => {
  const { activeModule } = useIntel();
  const ActiveComponent = MODULE_COMPONENTS[activeModule] || OverviewTab;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeModule}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
      >
        <ModuleErrorBoundary moduleKey={activeModule}>
          <ActiveComponent />
        </ModuleErrorBoundary>
      </motion.div>
    </AnimatePresence>
  );
};

export default function IntelligenceHub() {
  return (
    <IntelProvider>
      <IntelLayout>
        <IntelContent />
      </IntelLayout>
    </IntelProvider>
  );
}
