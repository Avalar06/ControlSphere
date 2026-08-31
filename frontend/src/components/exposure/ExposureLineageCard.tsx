import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Link } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  Building2,
  Layers,
  Shield,
  Target,
} from 'lucide-react';
import type { VulnerabilityExposure } from '../../types';

interface ExposureLineageCardProps {
  exposure?: VulnerabilityExposure;
}

export const ExposureLineageCard: React.FC<ExposureLineageCardProps> = ({ exposure }) => {
  const hasRemediation = !!exposure?.remediation_plan_id;
  const linkedProcesses = exposure?.asset_links?.filter((l) => !!l.process_id) || [];
  const linkedVendors = exposure?.asset_links?.filter((l) => !!l.vendor_id) || [];
  const linkedControls = exposure?.asset_links?.filter((l) => !!l.control_id) || [];

  return (
    <Card className="p-6 space-y-6 bg-slate-900/60 border-slate-800">
      <div className="space-y-1 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-indigo-400" />
          <h3 className="text-base font-bold text-slate-100">
            Enterprise Threat & Vulnerability Governance Lineage
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Cross-module traceability mapping technical vulnerabilities to business processes, vendors, controls, and corrective actions.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
        {/* Step 1: Upstream Controls & Vendors */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              1. Upstream Controls & Vendors
            </span>
            <Badge variant="default" className="text-[10px]">P2 / P9</Badge>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-1.5 text-slate-300">
              <Shield className="h-3.5 w-3.5 text-emerald-400" />
              <span>Controls: {linkedControls.length} linked</span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-300">
              <Building2 className="h-3.5 w-3.5 text-amber-400" />
              <span>Vendors: {linkedVendors.length} linked</span>
            </div>
          </div>
        </div>

        {/* Step 2: Operational Resilience Impact */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              2. Business Impact (Phase 13)
            </span>
            <Badge variant="info" className="text-[10px]">RESILIENCE</Badge>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-1.5 text-slate-300">
              <Activity className="h-3.5 w-3.5 text-indigo-400" />
              <span>Processes: {linkedProcesses.length} linked</span>
            </div>
            {exposure && (
              <div className="text-[11px] text-slate-400">
                Blast Multiplier: <span className="text-indigo-300 font-semibold">{exposure.asset_links && exposure.asset_links.some(l => l.process_tier === 'TIER_1') ? '1.25×' : '1.00×'}</span>
              </div>
            )}
          </div>
        </div>

        {/* Step 3: Threat Exposure Catalog (Phase 14) */}
        <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/40 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-300">
              3. Threat Exposure (Phase 14)
            </span>
            <Badge variant="danger" className="text-[10px]">EXPOSURE-GRC</Badge>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="font-mono font-bold text-slate-100">
              {exposure?.cve_id || 'Active CVE Catalog'}
            </div>
            {exposure && (
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Index:</span>
                <span className="font-bold text-rose-400">{exposure.exposure_index.toFixed(2)}</span>
                {exposure.cisa_kev && <Badge variant="danger" className="text-[9px]">KEV</Badge>}
              </div>
            )}
          </div>
        </div>

        {/* Step 4: Corrective Remediation (Phase 11) */}
        <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              4. Remediation (Phase 11)
            </span>
            <Badge variant="success" className="text-[10px]">CAPA</Badge>
          </div>
          <div className="space-y-2 text-xs">
            {hasRemediation ? (
              <Link
                to={`/remediations/${exposure?.remediation_plan_id}`}
                className="inline-flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 font-medium"
              >
                <Target className="h-3.5 w-3.5" />
                <span>CAPA Plan #{exposure?.remediation_plan_id}</span>
                <ArrowRight className="h-3 w-3 ml-1" />
              </Link>
            ) : (
              <span className="text-slate-500">No CAPA plan spawned</span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
};
