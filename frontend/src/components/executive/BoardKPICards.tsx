import React from 'react';
import { AlertTriangle, ShieldAlert, DollarSign } from 'lucide-react';
import type { TopRiskItem, CriticalFindingItem } from '../../types';

interface BoardKPICardsProps {
  topRisks: TopRiskItem[];
  criticalFindings: CriticalFindingItem[];
  financialAle: number;
  var95: number;
  appetiteUtilization: number;
}

export const BoardKPICards: React.FC<BoardKPICardsProps> = ({
  topRisks,
  criticalFindings,
  financialAle,
  var95,
  appetiteUtilization,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Card 1: Top Material Risks */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <h3 className="font-bold text-slate-900 dark:text-white">Top Material Risks</h3>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
              {topRisks.length} Ranked
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Highest inherent severity risks prioritized for executive oversight.
          </p>

          <div className="space-y-2.5">
            {topRisks.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-3 text-center">No open material risks recorded.</p>
            ) : (
              topRisks.map((risk) => (
                <div
                  key={risk.id}
                  className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between"
                >
                  <div className="truncate pr-2">
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                      {risk.title}
                    </p>
                    <span className="text-[10px] text-slate-400">{risk.risk_category}</span>
                  </div>
                  <div className="text-right whitespace-nowrap">
                    <span className="text-xs font-bold text-amber-600 dark:text-amber-400">
                      Score {risk.inherent_score}
                    </span>
                    {risk.residual_score != null && (
                      <span className="text-[10px] text-emerald-500 block">
                        Res: {risk.residual_score}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Card 2: Critical Open Findings */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-rose-500" />
              <h3 className="font-bold text-slate-900 dark:text-white">Critical Findings</h3>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
              {criticalFindings.length} Active
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Audit and vulnerability findings requiring immediate executive tracking.
          </p>

          <div className="space-y-2.5">
            {criticalFindings.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-3 text-center">No critical audit findings active.</p>
            ) : (
              criticalFindings.map((finding) => (
                <div
                  key={finding.id}
                  className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between"
                >
                  <div className="truncate pr-2">
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                      {finding.title}
                    </p>
                    <span className="text-[10px] text-slate-400">
                      {finding.owner_name || 'Unassigned'} • Due: {finding.due_date || 'No Date'}
                    </span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-500/10 text-rose-500 border border-rose-500/20">
                    {finding.severity}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Card 3: FAIR Loss Quantification */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-emerald-500" />
              <h3 className="font-bold text-slate-900 dark:text-white">FAIR Loss Quantification</h3>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
              FAIR Standard
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Probabilistic cyber loss modeling against board risk appetite.
          </p>

          <div className="space-y-3">
            <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <span className="text-xs text-slate-500 block">Annualized Loss Expectancy (ALE)</span>
              <span className="text-2xl font-extrabold text-slate-900 dark:text-white">
                ${financialAle.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <span className="text-xs text-slate-500 block">95th Percentile Tail Loss (VaR 95%)</span>
              <span className="text-xl font-bold text-slate-800 dark:text-slate-200">
                ${var95.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-slate-500">Board Appetite Utilization</span>
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  {appetiteUtilization.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    appetiteUtilization > 100
                      ? 'bg-rose-500'
                      : appetiteUtilization > 80
                      ? 'bg-amber-500'
                      : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(100, appetiteUtilization)}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
