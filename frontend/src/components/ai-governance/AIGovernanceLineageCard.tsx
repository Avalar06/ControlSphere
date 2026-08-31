import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { AISystem } from '../../types';
import {
  ArrowRight,
  Bot,
  Building2,
  ExternalLink,
  Layers,
  Network,
} from 'lucide-react';

interface AIGovernanceLineageCardProps {
  system: AISystem;
}

export const AIGovernanceLineageCard: React.FC<AIGovernanceLineageCardProps> = ({ system }) => {
  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-sky-950/80 border border-sky-700/60 text-sky-400">
            <Network size={18} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Cross-Module Governance Lineage
            </h3>
            <span className="text-[11px] text-slate-400">
              Interconnected GRC Dependency Graph &amp; Upstream / Downstream Impact
            </span>
          </div>
        </div>

        <Badge variant="purple" className="text-xs">
          PHASE 15 UNIFIED LINEAGE
        </Badge>
      </div>

      <div className="p-5 space-y-6">
        {/* Lineage Graph Flow Visualization */}
        <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl">
          <div className="flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
            {/* Vendor Node */}
            <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 w-full md:w-1/3 text-center">
              <div className="flex items-center justify-center gap-1.5 text-slate-400 font-semibold mb-1">
                <Building2 size={14} className="text-amber-400" />
                <span>TPRM Provider (Phase 9)</span>
              </div>
              <div className="font-bold text-slate-200 truncate">
                {system.vendor_id ? (
                  <Link
                    to={`/vendors/${system.vendor_id}`}
                    className="text-indigo-400 hover:underline flex items-center justify-center gap-1"
                  >
                    <span>Vendor #{system.vendor_id}</span>
                    <ExternalLink size={12} />
                  </Link>
                ) : (
                  <span className="text-slate-500 italic">Internal Proprietary</span>
                )}
              </div>
            </div>

            <ArrowRight size={16} className="text-slate-600 hidden md:block" />

            {/* AI System Core Node */}
            <div className="p-3 bg-indigo-950/40 rounded-lg border border-indigo-700/60 w-full md:w-1/3 text-center shadow-xs">
              <div className="flex items-center justify-center gap-1.5 text-indigo-300 font-semibold mb-1">
                <Bot size={14} className="text-indigo-400" />
                <span>AI System (Phase 15)</span>
              </div>
              <div className="font-bold text-slate-100 font-mono text-xs truncate">
                {system.system_code} — {system.name}
              </div>
            </div>

            <ArrowRight size={16} className="text-slate-600 hidden md:block" />

            {/* Business Process Node */}
            <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 w-full md:w-1/3 text-center">
              <div className="flex items-center justify-center gap-1.5 text-slate-400 font-semibold mb-1">
                <Layers size={14} className="text-sky-400" />
                <span>Business Process (Phase 13)</span>
              </div>
              <div className="font-bold text-slate-200 truncate">
                {system.business_process_id ? (
                  <Link
                    to={`/resilience/processes/${system.business_process_id}`}
                    className="text-sky-400 hover:underline flex items-center justify-center gap-1"
                  >
                    <span>Process #{system.business_process_id}</span>
                    <ExternalLink size={12} />
                  </Link>
                ) : (
                  <span className="text-slate-500 italic">No Process Linked</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Dependency Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Phase 13 Process Link */}
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-400 font-semibold uppercase tracking-wider">
                  Operational Resilience
                </span>
                <Badge variant={system.business_process_id ? 'info' : 'default'} className="text-[10px]">
                  {system.business_process_id ? 'LINKED' : 'UNLINKED'}
                </Badge>
              </div>
              <p className="text-xs text-slate-300">
                {system.business_process_id
                  ? `Supports Critical Business Process #${system.business_process_id}. Outage impacts BIA criticality multipliers.`
                  : 'No operational business process currently mapped.'}
              </p>
            </div>

            {system.business_process_id && (
              <Link
                to={`/resilience/processes/${system.business_process_id}`}
                className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold"
              >
                <span>View Process Resilience Profile</span>
                <ArrowRight size={13} />
              </Link>
            )}
          </div>

          {/* Phase 9 Vendor Link */}
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-400 font-semibold uppercase tracking-wider">
                  Third-Party TPRM
                </span>
                <Badge variant={system.vendor_id ? 'warning' : 'default'} className="text-[10px]">
                  {system.vendor_id ? 'THIRD-PARTY' : 'IN-HOUSE'}
                </Badge>
              </div>
              <p className="text-xs text-slate-300">
                {system.vendor_id
                  ? `Supplied by external Vendor #${system.vendor_id}. Subject to third-party AI risk audits and SLA controls.`
                  : 'Internally developed and hosted model.'}
              </p>
            </div>

            {system.vendor_id && (
              <Link
                to={`/vendors/${system.vendor_id}`}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 font-semibold"
              >
                <span>View TPRM Vendor Dossier</span>
                <ArrowRight size={13} />
              </Link>
            )}
          </div>

          {/* Phase 11 Remediation Link */}
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-slate-400 font-semibold uppercase tracking-wider">
                  Remediation &amp; CAPA
                </span>
                <Badge variant={system.remediation_plan_id ? 'purple' : 'default'} className="text-[10px]">
                  {system.remediation_plan_id ? 'ACTIVE CAPA' : 'NO CAPA'}
                </Badge>
              </div>
              <p className="text-xs text-slate-300">
                {system.remediation_plan_id
                  ? `Remediation Plan #${system.remediation_plan_id} active to address algorithmic safety / compliance gaps.`
                  : 'No active corrective action plan required.'}
              </p>
            </div>

            {system.remediation_plan_id && (
              <Link
                to={`/remediations/${system.remediation_plan_id}`}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
              >
                <span>View Corrective Action Plan</span>
                <ArrowRight size={13} />
              </Link>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
};
