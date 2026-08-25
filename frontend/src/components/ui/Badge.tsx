import React from 'react';
import { twMerge } from 'tailwind-merge';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  className,
}) => {
  const variantStyles = {
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    success: 'bg-emerald-950/70 text-emerald-300 border-emerald-800/80',
    warning: 'bg-amber-950/70 text-amber-300 border-amber-800/80',
    danger: 'bg-rose-950/70 text-rose-300 border-rose-800/80',
    info: 'bg-sky-950/70 text-sky-300 border-sky-800/80',
    purple: 'bg-indigo-950/70 text-indigo-300 border-indigo-800/80',
  };

  return (
    <span
      className={twMerge(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border tracking-wide uppercase',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
};