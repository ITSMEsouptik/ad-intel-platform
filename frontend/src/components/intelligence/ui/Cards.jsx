import React from 'react';
import { motion } from 'framer-motion';

/**
 * Antigravity-inspired floating card with glassmorphism.
 * The core visual building block for the Intelligence Hub.
 */
export const AntigravityCard = ({ children, className = '', hover = false, ...props }) => (
  <motion.div
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
    whileHover={hover ? { y: -2, transition: { duration: 0.2 } } : undefined}
    className={`
      relative overflow-hidden rounded-xl
      border border-white/[0.06]
      bg-[#0A0A0A]/80
      ${hover ? 'hover:border-white/[0.12] hover:bg-[#0E0E0E]/80 hover:shadow-lg hover:shadow-white/[0.02] cursor-pointer' : ''}
      transition-colors duration-300
      ${className}
    `}
    {...props}
  >
    {/* Subtle top glow */}
    <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
    {children}
  </motion.div>
);

/**
 * Stagger container for animating children sequentially
 */
export const StaggerContainer = ({ children, className = '', delay = 0.06 }) => (
  <motion.div
    initial="hidden"
    animate="show"
    variants={{
      hidden: { opacity: 0 },
      show: { opacity: 1, transition: { staggerChildren: delay } },
    }}
    className={className}
  >
    {children}
  </motion.div>
);

/**
 * Stagger item — child of StaggerContainer
 */
export const StaggerItem = ({ children, className = '' }) => (
  <motion.div
    variants={{
      hidden: { opacity: 0, y: 12 },
      show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.23, 1, 0.32, 1] } },
    }}
    className={className}
  >
    {children}
  </motion.div>
);

/**
 * Section label — mono, uppercase, muted
 */
export const SectionLabel = ({ children, count, className = '' }) => (
  <div className={`flex items-center gap-3 mb-4 ${className}`}>
    <h2 className="text-[11px] font-mono text-white/30 uppercase tracking-[0.2em]">{children}</h2>
    {count !== undefined && (
      <span className="text-[10px] font-mono text-white/20 bg-white/[0.04] px-2 py-0.5 rounded-full">{count}</span>
    )}
  </div>
);

/**
 * Clean text that strips citation markers like [1], [5] from display
 */
export const CleanText = ({ children, className = '' }) => {
  if (typeof children !== 'string') return <span className={className}>{children}</span>;
  const cleaned = children.replace(/\[\d+\]/g, '').replace(/\[\d+$/g, '').replace(/\[\d+[,\s\d]*\]/g, '').trim();
  return <span className={className}>{cleaned}</span>;
};

/**
 * Skeleton loader for module content placeholders
 */
export const ModuleSkeleton = ({ rows = 3 }) => (
  <div className="space-y-4 animate-pulse" data-testid="module-skeleton">
    <div className="h-6 w-48 bg-white/[0.04] rounded-lg" />
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <div className="h-4 bg-white/[0.03] rounded-md" style={{ width: `${80 - i * 12}%` }} />
        </div>
      ))}
    </div>
    <div className="grid grid-cols-2 gap-4">
      <div className="h-24 bg-white/[0.03] rounded-xl" />
      <div className="h-24 bg-white/[0.03] rounded-xl" />
    </div>
  </div>
);

