import React from 'react';
import { Card } from '../ui/Card';
import {
  Activity,
  Building2,
  Calculator,
  Clock,
  Layers,
} from 'lucide-react';

export const ResilienceLineageCard: React.FC = () => {
  return (
    <Card className="border-indigo-950/70 bg-slate-900/90 space-y-4">
      <div className="flex items-center gap-2.5 pb-3 border-b border-slate-800">
        <Layers className="h-5 w-5 text-indigo-400" />
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            RESILIENCE-GRC Multi-Module Governance Lineage
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Operational resilience maps business critical processes across upstream suppliers, internal safeguards, and downstream disruption loss.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        {/* Stage 1 */}
        <div className="p-3 bg-indigo-950/40 border border-indigo-800/80 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-300 uppercase font-bold">Phase 13 Catalog</span>
              <Layers className="h-4 w-4 text-indigo-400" />
            </div>
            <h4 className="text-xs font-semibold text-indigo-100">Business Processes</h4>
            <p className="text-[11px] text-indigo-200/80 mt-1">
              Criticality Tiers 1–4, system boundaries, and process ownership.
            </p>
          </div>
          <span className="text-[10px] text-indigo-400 font-mono mt-2 block font-bold">
            Governed Inventory
          </span>
        </div>

        {/* Stage 2 */}
        <div className="p-3 bg-indigo-950/40 border border-indigo-800/80 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-300 uppercase font-bold">Phase 13 Baseline</span>
              <Clock className="h-4 w-4 text-amber-400" />
            </div>
            <h4 className="text-xs font-semibold text-indigo-100">BIA &amp; Outage Loss</h4>
            <p className="text-[11px] text-indigo-200/80 mt-1">
              RTO, RPO, MTD &amp; deterministic hourly disruption modeling.
            </p>
          </div>
          <span className="text-[10px] text-amber-400 font-mono mt-2 block font-bold">
            Four-Eyes Baselines
          </span>
        </div>

        {/* Stage 3 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 9 TPRM</span>
              <Building2 className="h-4 w-4 text-purple-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">Vendor Dependencies</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              Critical supplier tiering, SLA agreements, and 4th-party concentration.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">Supply Chain Risk</span>
        </div>

        {/* Stage 4 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 2 &amp; 7</span>
              <Activity className="h-4 w-4 text-emerald-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">Safeguards &amp; CCM</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              Organization controls and continuous telemetry health monitoring.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">Internal Defense</span>
        </div>

        {/* Stage 5 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 10 &amp; 12</span>
              <Calculator className="h-4 w-4 text-cyan-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">Incidents &amp; VaR</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              Material breach disclosure &amp; FAIR empirical Monte Carlo quantification.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">Closed-Loop GRC</span>
        </div>
      </div>
    </Card>
  );
};
