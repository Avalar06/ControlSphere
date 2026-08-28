import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { resilienceService } from '../../lib/resilienceService';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { BusinessImpactAnalysis, OutageCostCalculationResult } from '../../types';
import {
  Activity,
  AlertTriangle,
  Calculator,
  CheckCircle2,
  Clock,
  Info,
  RotateCw,
} from 'lucide-react';

interface OutageImpactCardProps {
  bia: BusinessImpactAnalysis;
}

export const OutageImpactCard: React.FC<OutageImpactCardProps> = ({ bia }) => {
  const [durationHours, setDurationHours] = useState<number>(bia.rto_hours || 4.0);
  const [serverResult, setServerResult] = useState<OutageCostCalculationResult | null>(null);

  // Client-side Display Preview calculation (UX only)
  const previewVariableCost = Math.round(durationHours * bia.hourly_downtime_cost * 100) / 100;
  const previewTotalLoss = Math.round((bia.fixed_outage_cost + previewVariableCost) * 100) / 100;

  // Max slider range based on MTD
  const maxHours = Math.max(48, Math.ceil(bia.mtd_hours * 1.5));

  // Threshold flags
  const isPastRto = durationHours > bia.rto_hours;
  const isPastMtd = durationHours > bia.mtd_hours;

  const serverCalcMutation = useMutation({
    mutationFn: async (hours: number) => {
      return resilienceService.calculateOutageLoss({
        duration_hours: hours,
        hourly_downtime_cost: bia.hourly_downtime_cost,
        fixed_outage_cost: bia.fixed_outage_cost,
      });
    },
    onSuccess: (data) => {
      setServerResult(data);
    },
  });

  return (
    <Card className="border-indigo-950/80 bg-slate-900/90 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Calculator className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Deterministic Outage Loss Simulator
              <Badge variant="info">Server-Authoritative</Badge>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Financial disruption model: <span className="font-mono text-indigo-300">Total = Fixed + (Hourly × H)</span>
            </p>
          </div>
        </div>

        <Button
          variant="secondary"
          onClick={() => serverCalcMutation.mutate(durationHours)}
          disabled={serverCalcMutation.isPending}
          className="text-xs flex items-center gap-1.5 self-start sm:self-auto"
        >
          <RotateCw className={`h-3.5 w-3.5 ${serverCalcMutation.isPending ? 'animate-spin' : ''}`} />
          {serverCalcMutation.isPending ? 'Calculating...' : 'Run Server Calculation'}
        </Button>
      </div>

      {/* Main Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Outage Duration
          </span>
          <div className="mt-2 flex items-baseline gap-1.5">
            <span className="text-2xl font-mono font-bold text-slate-100">
              {durationHours.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400 font-mono">hours</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-[11px]">
            {isPastMtd ? (
              <span className="text-rose-400 font-semibold flex items-center gap-1">
                <AlertTriangle size={12} /> Exceeds MTD ({bia.mtd_hours}h)
              </span>
            ) : isPastRto ? (
              <span className="text-amber-400 font-semibold flex items-center gap-1">
                <Clock size={12} /> Exceeds RTO ({bia.rto_hours}h)
              </span>
            ) : (
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 size={12} /> Within RTO target
              </span>
            )}
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Fixed Initial Cost
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-slate-200">
              ${bia.fixed_outage_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2">
            Initial incident response &amp; disruption
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Variable Downtime Cost
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-indigo-300">
              ${previewVariableCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-2">
            ${bia.hourly_downtime_cost.toLocaleString()}/hr × {durationHours.toFixed(1)}h
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-gradient-to-br from-indigo-950/60 to-purple-950/60 border border-indigo-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-300">
              Total Projected Loss
            </span>
            {serverResult && (
              <Badge variant="success">Verified</Badge>
            )}
          </div>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-white">
              ${(serverResult ? serverResult.total_projected_loss : previewTotalLoss).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
          </div>
          <span className="text-[10px] text-indigo-300/80 font-mono mt-2">
            {serverResult ? 'Server-verified calculation' : 'Real-time linear preview'}
          </span>
        </div>
      </div>

      {/* Interactive Slider */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-300">
          <span className="font-semibold flex items-center gap-1.5">
            <Activity className="h-4 w-4 text-indigo-400" />
            Adjust Outage Duration (Hours):
          </span>
          <span className="font-mono text-indigo-400 font-bold bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/50">
            {durationHours.toFixed(1)} Hours
          </span>
        </div>

        <input
          type="range"
          min="0"
          max={maxHours}
          step="0.5"
          value={durationHours}
          onChange={(e) => {
            setDurationHours(parseFloat(e.target.value));
            setServerResult(null); // Clear previous server verification when slider moves
          }}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
        />

        <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-1">
          <span>0h (Incident Start)</span>
          <span className="text-amber-400">RTO Target ({bia.rto_hours}h)</span>
          <span className="text-rose-400">MTD Limit ({bia.mtd_hours}h)</span>
          <span>{maxHours}h (Extended Outage)</span>
        </div>
      </div>

      {/* SVG Mathematical Cost Curve & Threshold Timeline */}
      <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800/80 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-200">
            Recovery Thresholds &amp; Cost Curve Progression
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            RPO: {bia.rpo_hours}h | RTO: {bia.rto_hours}h | MTD: {bia.mtd_hours}h
          </span>
        </div>

        <div className="relative w-full h-28 bg-slate-900/80 rounded-lg border border-slate-800 p-2 flex items-center justify-center overflow-hidden">
          <svg className="w-full h-full" viewBox="0 0 500 100" preserveAspectRatio="none">
            {/* Grid Lines */}
            <line x1="0" y1="85" x2="500" y2="85" stroke="#334155" strokeWidth="1" />
            <line x1="0" y1="45" x2="500" y2="45" stroke="#1e293b" strokeWidth="1" strokeDasharray="3,3" />

            {/* RTO Line marker */}
            <line
              x1={(bia.rto_hours / maxHours) * 500}
              y1="10"
              x2={(bia.rto_hours / maxHours) * 500}
              y2="85"
              stroke="#fbbf24"
              strokeWidth="1.5"
              strokeDasharray="4,4"
            />
            <text
              x={(bia.rto_hours / maxHours) * 500 + 4}
              y="22"
              fill="#fbbf24"
              fontSize="9"
              fontFamily="monospace"
            >
              RTO {bia.rto_hours}h
            </text>

            {/* MTD Line marker */}
            <line
              x1={(bia.mtd_hours / maxHours) * 500}
              y1="10"
              x2={(bia.mtd_hours / maxHours) * 500}
              y2="85"
              stroke="#f43f5e"
              strokeWidth="1.5"
              strokeDasharray="4,4"
            />
            <text
              x={(bia.mtd_hours / maxHours) * 500 + 4}
              y="22"
              fill="#f43f5e"
              fontSize="9"
              fontFamily="monospace"
            >
              MTD {bia.mtd_hours}h
            </text>

            {/* Current Position Marker */}
            <line
              x1={(durationHours / maxHours) * 500}
              y1="5"
              x2={(durationHours / maxHours) * 500}
              y2="85"
              stroke="#6366f1"
              strokeWidth="2"
            />
            <circle
              cx={(durationHours / maxHours) * 500}
              cy={85 - ((durationHours * bia.hourly_downtime_cost + bia.fixed_outage_cost) / (maxHours * bia.hourly_downtime_cost + bia.fixed_outage_cost)) * 65}
              r="4.5"
              fill="#818cf8"
            />

            {/* Cost Progression Curve */}
            <path
              d={`M 0,${85 - (bia.fixed_outage_cost / (maxHours * bia.hourly_downtime_cost + bia.fixed_outage_cost)) * 65} L 500,20`}
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.5"
            />
          </svg>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <Info className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
          <span>
            Deterministic financial disruption loss accumulates strictly linearly at{' '}
            <span className="font-mono text-slate-200">${bia.hourly_downtime_cost.toLocaleString()}</span> per hour beyond initial fixed mobilization costs.
          </span>
        </div>
      </div>
    </Card>
  );
};
