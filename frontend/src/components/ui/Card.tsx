import React from 'react';
import { twMerge } from 'tailwind-merge';

export const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <div className={twMerge('bg-slate-900/90 border border-slate-800/90 rounded-lg p-5 shadow-sm', className)}>
    {children}
  </div>
);

export const CardHeader: React.FC<{
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}> = ({ title, subtitle, action, className }) => (
  <div className={twMerge('flex items-center justify-between pb-4 mb-4 border-b border-slate-800/80', className)}>
    <div>
      <h3 className="text-base font-semibold text-slate-100 tracking-tight">{title}</h3>
      {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
    </div>
    {action && <div>{action}</div>}
  </div>
);