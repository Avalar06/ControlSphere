import React, { useEffect, useState } from 'react';
import { Building2, LogOut, Activity } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/Badge';
import { api } from '../../lib/api';
import type { HealthStatus } from '../../types';

export const Header: React.FC = () => {
  const { user, organization, logout } = useAuth();
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const { data } = await api.get<HealthStatus>('/health');
        setHealth(data);
      } catch {
        setHealth({ status: 'offline', app: 'ControlSphere', version: '1.0.0', environment: 'dev' });
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getRoleBadgeVariant = (role?: string) => {
    switch (role) {
      case 'ADMIN':
        return 'purple';
      case 'GRC_ANALYST':
        return 'info';
      case 'AUDITOR':
        return 'warning';
      case 'VIEWER':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <header className="h-16 bg-slate-950/80 backdrop-blur-xs border-b border-slate-800/80 px-6 flex items-center justify-between shrink-0">
      {/* Organization Context */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800 text-slate-200">
          <Building2 size={15} className="text-indigo-400" />
          <span className="text-xs font-semibold tracking-tight">
            {organization ? organization.name : 'Loading Organization...'}
          </span>
          <span className="text-[10px] text-slate-500 font-mono">TENANT #{organization?.id || 1}</span>
        </div>

        {/* Backend health status badge */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900/50 border border-slate-800 text-[11px] text-slate-400">
          <Activity size={12} className={health?.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'} />
          <span>API:</span>
          <span className={`font-mono font-medium ${health?.status === 'ok' ? 'text-emerald-400' : 'text-rose-400'}`}>
            {health?.status === 'ok' ? 'HEALTHY' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* User info & Actions */}
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-100">{user.full_name}</div>
              <div className="text-[11px] text-slate-400 font-mono">{user.email}</div>
            </div>

            <Badge variant={getRoleBadgeVariant(user.role)}>
              {user.role}
            </Badge>
          </div>
        )}

        <div className="h-4 w-px bg-slate-800" />

        <button
          onClick={logout}
          title="Sign out of ControlSphere"
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-950/30 border border-transparent hover:border-rose-900/50 transition-all cursor-pointer"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
};