import React from 'react';
import { twMerge } from 'tailwind-merge';

export const Table: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <div className="w-full overflow-x-auto rounded border border-slate-800/80">
    <table className={twMerge('w-full text-left border-collapse text-sm', className)}>
      {children}
    </table>
  </div>
);

export const TableHead: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <thead className="bg-slate-950/80 text-xs uppercase font-semibold text-slate-400 border-b border-slate-800 tracking-wider">
    {children}
  </thead>
);

export const TableBody: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <tbody className="divide-y divide-slate-800/60 bg-slate-900/40 text-slate-200">
    {children}
  </tbody>
);

export const TableRow: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <tr className={twMerge('hover:bg-slate-800/40 transition-colors', className)}>
    {children}
  </tr>
);

export const TableHeaderCell: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <th className={twMerge('px-4 py-3 font-medium', className)}>{children}</th>
);

export const TableCell: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <td className={twMerge('px-4 py-3 font-normal text-slate-300', className)}>
    {children}
  </td>
);