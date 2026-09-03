import React from 'react';
import { Shield, Layers, Cloud, Key, CheckCircle, Package, Cpu, Lock, Users, AlertOctagon } from 'lucide-react';

interface DomainMaturityRadarProps {
  domains: Record<string, { name: string; score: number; weight: number }>;
}

export const DomainMaturityRadar: React.FC<DomainMaturityRadarProps> = ({ domains }) => {
  const getDomainIcon = (key: string) => {
    switch (key) {
      case 'framework_controls':
        return <Layers className="h-4 w-4 text-blue-500" />;
      case 'threat_exposure':
        return <Shield className="h-4 w-4 text-rose-500" />;
      case 'cloud_security':
        return <Cloud className="h-4 w-4 text-sky-500" />;
      case 'identity_governance':
        return <Key className="h-4 w-4 text-purple-500" />;
      case 'remediation_health':
        return <CheckCircle className="h-4 w-4 text-emerald-500" />;
      case 'supply_chain':
        return <Package className="h-4 w-4 text-amber-500" />;
      case 'ai_governance':
        return <Cpu className="h-4 w-4 text-violet-500" />;
      case 'privacy':
        return <Lock className="h-4 w-4 text-teal-500" />;
      case 'tprm':
        return <Users className="h-4 w-4 text-orange-500" />;
      case 'incidents_resilience':
        return <AlertOctagon className="h-4 w-4 text-red-500" />;
      default:
        return <Layers className="h-4 w-4 text-slate-500" />;
    }
  };

  const getBarColor = (score: number) => {
    if (score >= 85) return 'bg-emerald-500';
    if (score >= 70) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">
            Cross-Domain Governance Maturity Matrix
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Weighted composite scoring across all 10 authoritative platform modules.
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
          10 Dimensions
        </span>
      </div>

      <div className="space-y-3.5 mt-4">
        {Object.entries(domains).map(([key, domain]) => {
          const weightedContribution = domain.score * domain.weight;
          return (
            <div
              key={key}
              className="p-3 rounded-lg border border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-slate-50 dark:hover:bg-slate-800/80 transition-colors"
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  {getDomainIcon(key)}
                  <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                    {domain.name}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    Weight: {(domain.weight * 100).toFixed(0)}%
                  </span>
                  <span className="text-sm font-bold text-slate-900 dark:text-white min-w-[3rem] text-right">
                    {domain.score.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${getBarColor(
                    domain.score
                  )}`}
                  style={{ width: `${Math.min(100, Math.max(0, domain.score))}%` }}
                />
              </div>

              <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                <span>Contribution to overall:</span>
                <span className="font-semibold text-slate-600 dark:text-slate-300">
                  +{weightedContribution.toFixed(1)} pts
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
