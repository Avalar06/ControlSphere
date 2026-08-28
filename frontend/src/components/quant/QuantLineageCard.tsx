import React from 'react';
import { Card } from '../ui/Card';
import {
  Activity,
  Calculator,
  Flame,
  Layers,
  ShieldAlert,
  Target,
  TrendingUp,
} from 'lucide-react';

export const QuantLineageCard: React.FC = () => {
  return (
    <Card className="border-indigo-950/70 bg-slate-900/90">
      <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-slate-800">
        <Layers className="h-5 w-5 text-indigo-400" />
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            QUANTUM-GRC Multi-Phase Risk Lineage & Data Flow
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Phase 12 transforms upstream qualitative governance into server-authoritative financial exposure.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
        {/* Step 1 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 5 Core</span>
              <ShieldAlert className="h-4 w-4 text-amber-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">Qualitative Risk</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              1-25 matrix ordinal scoring & threat intelligence.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">Risk Register Link</span>
        </div>

        {/* Step 2 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 7 & 4</span>
              <Activity className="h-4 w-4 text-emerald-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">CCM & Findings</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              Live health scores (0-100) & finding severity penalties.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">CS Base - Penalties</span>
        </div>

        {/* Step 3 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 9 & 10</span>
              <Flame className="h-4 w-4 text-rose-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">TPRM & Incidents</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              Vendor risk tiering & historical incident loss calibration.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">Threat Context</span>
        </div>

        {/* Step 4 */}
        <div className="p-3 bg-indigo-950/40 border border-indigo-800/80 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-300 uppercase font-bold">Phase 12 Core</span>
              <Calculator className="h-4 w-4 text-indigo-300" />
            </div>
            <h4 className="text-xs font-semibold text-indigo-100">FAIR Decomposition</h4>
            <p className="text-[11px] text-indigo-200/80 mt-1">
              LEF = TEF(mean) * VULN<br />
              SLE = PL + (SL * SLoP)
            </p>
          </div>
          <span className="text-[10px] text-indigo-400 font-mono mt-2 block font-bold">
            ALE = LEF * SLE
          </span>
        </div>

        {/* Step 5 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 12 Sim</span>
              <TrendingUp className="h-4 w-4 text-cyan-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">Monte Carlo VaR</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              50,000 trials PERT simulation deriving P10 to P99 tail losses.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">Empirical 95% VaR</span>
        </div>

        {/* Step 6 */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-indigo-400 uppercase font-bold">Phase 11 Link</span>
              <Target className="h-4 w-4 text-purple-400" />
            </div>
            <h4 className="text-xs font-semibold text-slate-200">ROSI & Appetite</h4>
            <p className="text-[11px] text-slate-400 mt-1">
              ROSI% financial return on CAPA & Board Appetite breach tracking.
            </p>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-2 block">Four-Eyes Governance</span>
        </div>
      </div>
    </Card>
  );
};