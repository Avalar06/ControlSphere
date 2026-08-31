import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { AISystem } from '../../types';
import { Activity, AlertTriangle, Calculator, Cpu, ShieldCheck } from 'lucide-react';

interface ARIExposureCardProps {
  system: AISystem;
  onOpenCalculator?: () => void;
}

export const ARIExposureCard: React.FC<ARIExposureCardProps> = ({
  system,
  onOpenCalculator,
}) => {
  const ari = Number(system.algorithmic_risk_index) || 0.0;

  // Determine ARI severity band (visual styling only, not overriding backend)
  const getRiskBand = (score: number) => {
    if (score >= 80.0) return { label: 'CRITICAL', color: 'text-rose-400', bg: 'bg-rose-950/40', border: 'border-rose-800/80', badge: 'danger' as const };
    if (score >= 60.0) return { label: 'HIGH', color: 'text-orange-400', bg: 'bg-orange-950/40', border: 'border-orange-800/80', badge: 'warning' as const };
    if (score >= 40.0) return { label: 'MODERATE', color: 'text-amber-400', bg: 'bg-amber-950/40', border: 'border-amber-800/80', badge: 'warning' as const };
    if (score >= 20.0) return { label: 'LOW', color: 'text-sky-400', bg: 'bg-sky-950/40', border: 'border-sky-800/80', badge: 'info' as const };
    return { label: 'MINIMAL', color: 'text-emerald-400', bg: 'bg-emerald-950/40', border: 'border-emerald-800/80', badge: 'success' as const };
  };

  const riskBand = getRiskBand(ari);

  // Latest model card safety parameters if present
  const latestModelCard = system.model_cards && system.model_cards.length > 0
    ? system.model_cards[system.model_cards.length - 1]
    : null;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-950/80 border border-indigo-700/60 text-indigo-400">
            <Activity size={18} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Algorithmic Risk Index (ARI) Telemetry
            </h3>
            <span className="text-[11px] text-slate-400">
              Server-Authoritative Mathematical Risk Calculation
            </span>
          </div>
        </div>

        {onOpenCalculator && (
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenCalculator}
            className="flex items-center gap-1.5 text-xs text-indigo-300 border-indigo-700/50 hover:bg-indigo-950/40"
          >
            <Calculator size={14} />
            <span>Interactive Calculator</span>
          </Button>
        )}
      </div>

      <div className="p-5 space-y-6">
        {/* Top Score Showcase */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            className={`p-4 rounded-xl border ${riskBand.bg} ${riskBand.border} flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Authoritative ARI Score
              </span>
              <Badge variant={riskBand.badge}>{riskBand.label} RISK</Badge>
            </div>

            <div className="flex items-baseline gap-2 my-1">
              <span className={`text-4xl font-extrabold font-mono tracking-tight ${riskBand.color}`}>
                {ari.toFixed(2)}
              </span>
              <span className="text-xs text-slate-500 font-mono">/ 100.00</span>
            </div>

            {/* Visual Score Meter Bar */}
            <div className="w-full bg-slate-950 rounded-full h-2 mt-2 overflow-hidden border border-slate-800">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  ari >= 80 ? 'bg-rose-500' : ari >= 60 ? 'bg-orange-500' : ari >= 40 ? 'bg-amber-500' : ari >= 20 ? 'bg-sky-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(100, ari)}%` }}
              />
            </div>
          </div>

          {/* EU AI Act Regulatory Classification */}
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/70 flex flex-col justify-between">
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                EU AI Act Classification
              </span>
              <div className="mt-1">
                <Badge
                  variant={
                    system.regulatory_tier === 'PROHIBITED'
                      ? 'danger'
                      : system.regulatory_tier === 'HIGH_RISK' || system.regulatory_tier === 'GPAI_SYSTEMIC_RISK'
                      ? 'warning'
                      : 'info'
                  }
                  className="text-xs px-2 py-1"
                >
                  {system.regulatory_tier.replace(/_/g, ' ')}
                </Badge>
              </div>
            </div>

            <div className="text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-800/80">
              {system.is_prohibited_practice ? (
                <span className="text-rose-400 font-semibold flex items-center gap-1">
                  <AlertTriangle size={13} /> Article 5 Prohibited Practice
                </span>
              ) : system.requires_conformity_assessment ? (
                <span className="text-amber-400 font-semibold flex items-center gap-1">
                  <ShieldCheck size={13} /> Conformity Assessment Mandated
                </span>
              ) : (
                <span className="text-slate-400">Standard Governance Monitoring</span>
              )}
            </div>
          </div>

          {/* Autonomy & Oversight */}
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/70 flex flex-col justify-between">
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Autonomy &amp; Operational Tier
              </span>
              <div className="text-sm font-semibold text-slate-200 mt-1 flex items-center gap-1.5">
                <Cpu size={15} className="text-indigo-400" />
                {system.autonomy_level.replace(/_/g, ' ')}
              </div>
            </div>

            <div className="text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-800/80">
              Data Sensitivity: <strong className="text-slate-300">{system.data_sensitivity}</strong>
            </div>
          </div>
        </div>

        {/* Mathematical Parameter Components */}
        <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-xl space-y-3">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            ARI Mathematical Component Factors
          </h4>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase block">Regulatory Base Risk</span>
              <span className="text-sm font-bold text-slate-200 font-mono">
                {system.regulatory_tier === 'PROHIBITED'
                  ? '100.0'
                  : system.regulatory_tier === 'HIGH_RISK'
                  ? '65.0'
                  : system.regulatory_tier === 'GPAI_SYSTEMIC_RISK'
                  ? '50.0'
                  : system.regulatory_tier === 'LIMITED_RISK'
                  ? '25.0'
                  : '5.0'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase block">Autonomy Multiplier</span>
              <span className="text-sm font-bold text-slate-200 font-mono">
                {system.autonomy_level === 'FULL_AUTONOMY'
                  ? '1.40x'
                  : system.autonomy_level === 'HUMAN_ON_THE_LOOP'
                  ? '1.20x'
                  : system.autonomy_level === 'HUMAN_IN_THE_LOOP'
                  ? '1.00x'
                  : '0.80x'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase block">Data Sensitivity Addon</span>
              <span className="text-sm font-bold text-slate-200 font-mono">
                {system.data_sensitivity === 'RESTRICTED_PII_PHI'
                  ? '+15.0'
                  : system.data_sensitivity === 'CONFIDENTIAL'
                  ? '+8.0'
                  : system.data_sensitivity === 'INTERNAL'
                  ? '+2.0'
                  : '+0.0'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-900 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-400 uppercase block">Active Model Card</span>
              <span className="text-sm font-bold text-slate-200 font-mono">
                {latestModelCard ? `v${latestModelCard.version}` : 'None'}
              </span>
            </div>
          </div>

          {latestModelCard && (
            <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800/80 text-[11px] text-slate-400 flex flex-wrap items-center gap-x-4 gap-y-1">
              <span>
                Hallucination Rate: <strong className="text-slate-200 font-mono">{Number(latestModelCard.hallucination_rate_percent).toFixed(2)}%</strong>
              </span>
              <span>
                Injection Resistance: <strong className="text-slate-200 font-mono">{Number(latestModelCard.prompt_injection_resistance_score).toFixed(2)}%</strong>
              </span>
              <span>
                Toxicity Filter: <strong className="text-slate-200 font-mono">{Number(latestModelCard.toxicity_filter_efficiency_score).toFixed(2)}%</strong>
              </span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
