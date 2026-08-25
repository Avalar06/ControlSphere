import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ShieldCheck,
  FolderCheck,
  AlertTriangle,
  FileCheck2,
  CalendarCheck,
  BookOpen,
  Sparkles,
  Users,
  ScrollText,
  Settings,
  Shield,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon;
  tag?: string;
}

interface NavGroup {
  group: string;
  items: NavItem[];
}

export const Sidebar: React.FC = () => {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('ADMIN');
  const isAuditor = hasRole('AUDITOR', 'ADMIN');

  const navGroups: NavGroup[] = [
    {
      group: 'Core',
      items: [
        { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      ],
    },
    {
      group: 'Compliance & Controls',
      items: [
        { name: 'Frameworks', path: '/frameworks', icon: ShieldCheck, tag: 'Phase 2' },
        { name: 'Controls Library', path: '/controls', icon: Shield, tag: 'Phase 2' },
        { name: 'Assessments', path: '/assessments', icon: FileCheck2, tag: 'Phase 4' },
      ],
    },
    {
      group: 'Evidence & Assurance',
      items: [
        { name: 'Evidence Library', path: '/evidence', icon: FolderCheck, tag: 'Phase 3' },
        { name: 'Audits & Readiness', path: '/audits', icon: CalendarCheck, tag: 'Phase 7' },
      ],
    },
    {
      group: 'Risk & Remediation',
      items: [
        { name: 'Risk Register', path: '/risks', icon: AlertTriangle, tag: 'Phase 5' },
        { name: 'Policies', path: '/policies', icon: BookOpen, tag: 'Phase 2' },
      ],
    },
    {
      group: 'AI Governance',
      items: [
        { name: 'AI GRC Analyst', path: '/ai-analyst', icon: Sparkles, tag: 'Phase 9' },
      ],
    },
    {
      group: 'Administration',
      items: [
        ...(isAdmin ? [{ name: 'User Management', path: '/users', icon: Users }] : []),
        ...(isAuditor ? [{ name: 'Audit Logs', path: '/audit-logs', icon: ScrollText }] : []),
        { name: 'Settings', path: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-slate-950/95 border-r border-slate-800/80 flex flex-col h-screen select-none shrink-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-slate-800/80 bg-slate-950">
        <div className="h-8 w-8 rounded-md bg-indigo-600 flex items-center justify-center text-white shadow-xs font-bold text-base">
          CS
        </div>
        <div>
          <span className="font-bold tracking-tight text-slate-100 text-base">
            ControlSphere
          </span>
          <span className="block text-[10px] text-slate-400 font-mono uppercase tracking-wider">
            GRC &amp; Security Platform
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
        {navGroups.map((group) => {
          if (group.items.length === 0) return null;
          return (
            <div key={group.group}>
              <div className="px-3 mb-2 text-[11px] font-semibold tracking-wider text-slate-500 uppercase">
                {group.group}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-3 py-2 text-xs font-medium rounded-md transition-all ${
                          isActive
                            ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                        }`
                      }
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon size={16} />
                        <span>{item.name}</span>
                      </div>
                      {item.tag && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-800/90 text-slate-400 font-mono">
                          {item.tag}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/60">
        <div className="flex items-center justify-between text-xs px-2 py-1.5 rounded bg-slate-900/60 border border-slate-800/50">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[11px] text-slate-400 font-medium">Engine v1.0.0</span>
          </div>
          <span className="text-[10px] font-mono text-indigo-400">ONLINE</span>
        </div>
      </div>
    </aside>
  );
};