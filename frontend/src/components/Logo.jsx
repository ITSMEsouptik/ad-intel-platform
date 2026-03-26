import React from 'react';

const Logo = ({ className = '', size = 'default' }) => {
  const sizeClasses = {
    small: 'text-lg',
    default: 'text-xl',
    large: 'text-2xl',
    hero: 'text-3xl md:text-4xl',
  };

  return (
    <div className={`font-heading font-bold tracking-tight ${sizeClasses[size]} ${className}`}>
      <span className="text-white">NOVARA</span>
    </div>
  );
};

export default Logo;
