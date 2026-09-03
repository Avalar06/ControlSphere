import React from 'react';
import { ShieldCheck, TrendingUp, AlertTriangle, DollarSign, Award, Activity } from 'lucide-react';
import type { ExecutiveTelemetryResponse } from '../../types';

interface ExecutivePostureHeroProps {
  telemetry: ExecutiveTelemetryResponse;
  onCaptureSnapshot?: () => void;
  canManage?: boolean;
}

export const ExecutivePostureHero: React.FC<ExecutivePostureHeroProps> = ({
  telemetry,
  onCaptureSnapshot,
  canManage = false,
}) => {
  const getScoreBadge = (score: number) => {
    if (score >= 85) return { label: 'OPTIMAL POSTURE', bg: 'bg-emerald-500/20 text-emerald-400' };
    if (score >= 70) return { label: 'ELEVATED ASSURANCE', bg: 'bg-amber-500/20 text-amber-400' };
    return { label: 'CRITICAL ATTENTION', bg: 'bg-rose-500/20 text-rose-400' };
  };

  const badge = getScoreBadge(telemetry.overall_posture_score);

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 p-6 md:p-8 text-white border border-slate-700/60 shadow-2xl">
      {/* Background Decorative Glow */}
      <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />
      <div className="absolute -left-20 -bottom-20 h-64 w-64 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-semibold tracking-wider text-slate-300 uppercase">
              Server-Authoritative Cyber Telemetry
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badge.bg}`}>
              {badge.label}
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white">
            Board & Executive Cyber Governance
          </h1>
          <p className="mt-1 text-sm text-slate-300 max-w-2xl">
            Synthesized across 10 security, compliance, identity, resilience, and exposure domains into deterministic, audit-grade board telemetry.
          </p>
        </div>

        {canManage && onCaptureSnapshot && (
          <button
            onClick={onCaptureSnapshot}
            className="self-start md:self-auto inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/30 hover:shadow-indigo-500/50"
          >
            <ShieldCheck className="h-4 w-4" />
            Capture Immutable Snapshot
          </button>
        )}
      </div>

      {/* Hero Metrics Row */}
      <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Metric 1: Overall Posture */}
        <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Posture Score</span>
            <Activity className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-white">
              {telemetry.overall_posture_score.toFixed(1)}%
            </span>
          </div>
          <span className="text-[11px] text-emerald-400 font-semibold mt-1 block">
            10 Domains Weighted
          </span>
        </div>

        {/* Metric 2: Inherent Risk */}
        <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Inherent Risk</span>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-amber-300">
              {telemetry.inherent_risk_index.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400">/ 25</span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">
            Pre-Control Baseline
          </span>
        </div>

        {/* Metric 3: Residual Risk */}
        <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Residual Risk</span>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-emerald-300">
              {telemetry.residual_risk_index.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400">/ 25</span>
          </div>
          <span className="text-[11px] text-emerald-400 font-semibold mt-1 block">
            -{telemetry.risk_reduction_percentage.toFixed(0)}% Mitigation
          </span>
        </div>

        {/* Metric 4: Financial ALE */}
        <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Annualized Loss</span>
            <DollarSign className="h-4 w-4 text-rose-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-xl sm:text-2xl font-black text-white">
              ${(telemetry.financial_exposure_ale / 1000).toFixed(1)}k
            </span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">
            Appetite: {telemetry.financial_appetite_utilization_pct.toFixed(0)}% Utilized
          </span>
        </div>

        {/* Metric 5: Audit Readiness */}
        <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Audit Readiness</span>
            <Award className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-cyan-300">
              {telemetry.audit_readiness_index.toFixed(1)}%
            </span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">
            Evidence & Controls
          </span>
        </div>

        {/* Metric 6: Remediation SLA */}
        <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium">Remediation SLA</span>
            <ShieldCheck className="h-4 w-4 text-violet-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black text-violet-300">
              {telemetry.remediation_sla_health_score.toFixed(1)}%
            </span>
          </div>
          <span className="text-[11px] text-slate-400 mt-1 block">
            CAPA Governance
          </span>
        </div>
      </div>
    </div>
  );
};
