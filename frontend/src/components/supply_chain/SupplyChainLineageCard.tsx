import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Layers, Bot, Building2, Target, ArrowUpRight } from 'lucide-react';
import type { SoftwareProduct } from '../../types';

interface SupplyChainLineageCardProps {
  product: SoftwareProduct;
}

export const SupplyChainLineageCard: React.FC<SupplyChainLineageCardProps> = ({ product }) => {
  return (
    <Card>
      <CardHeader
        title="Cross-Module GRC Lineage &amp; Dependencies"
        subtitle="End-to-end traceability across Resilience, AI Models, Vendor TPRM, and Remediation."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Phase 13: Operational Resilience */}
        <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Layers size={13} className="text-sky-400" />
                <span>Business Process</span>
              </span>
              <Badge variant="info">Phase 13</Badge>
            </div>
            {product.business_process_id ? (
              <div>
                <span className="text-xs font-semibold text-slate-200 block">
                  Process ID #{product.business_process_id}
                </span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Critical business operation supported by this software asset.
                </span>
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">No business process mapped</span>
            )}
          </div>
          {product.business_process_id && (
            <Link
              to={`/resilience/processes/${product.business_process_id}`}
              className="mt-3 text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium transition-colors"
            >
              <span>View BIA Process</span>
              <ArrowUpRight size={13} />
            </Link>
          )}
        </div>

        {/* Phase 15: AI Governance */}
        <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Bot size={13} className="text-purple-400" />
                <span>AI System Linkage</span>
              </span>
              <Badge variant="purple">Phase 15</Badge>
            </div>
            {product.ai_system_id ? (
              <div>
                <span className="text-xs font-semibold text-slate-200 block">
                  AI System ID #{product.ai_system_id}
                </span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Embedded LLM / ML model pipeline dependency.
                </span>
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">No AI model linked</span>
            )}
          </div>
          {product.ai_system_id && (
            <Link
              to={`/ai-governance/systems/${product.ai_system_id}`}
              className="mt-3 text-[11px] text-purple-400 hover:text-purple-300 flex items-center gap-1 font-medium transition-colors"
            >
              <span>View AI System Card</span>
              <ArrowUpRight size={13} />
            </Link>
          )}
        </div>

        {/* Phase 9: Third-Party Vendor */}
        <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Building2 size={13} className="text-emerald-400" />
                <span>Third-Party Vendor</span>
              </span>
              <Badge variant="success">Phase 9</Badge>
            </div>
            {product.vendor_id ? (
              <div>
                <span className="text-xs font-semibold text-slate-200 block">
                  Vendor ID #{product.vendor_id}
                </span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  COTS or SaaS supplier under TPRM governance.
                </span>
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">Internal / 1st Party Code</span>
            )}
          </div>
          {product.vendor_id && (
            <Link
              to={`/vendors/${product.vendor_id}`}
              className="mt-3 text-[11px] text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-medium transition-colors"
            >
              <span>View Vendor Profile</span>
              <ArrowUpRight size={13} />
            </Link>
          )}
        </div>

        {/* Phase 11: CAPA Remediation */}
        <div className="p-3.5 bg-slate-900/60 border border-slate-800 rounded-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Target size={13} className="text-rose-400" />
                <span>CAPA Remediation</span>
              </span>
              <Badge variant="danger">Phase 11</Badge>
            </div>
            {product.remediation_plan_id ? (
              <div>
                <span className="text-xs font-semibold text-slate-200 block">
                  Plan ID #{product.remediation_plan_id}
                </span>
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Governed corrective action plan active for component risks.
                </span>
              </div>
            ) : (
              <span className="text-xs text-slate-500 italic">No open remediation plan</span>
            )}
          </div>
          {product.remediation_plan_id && (
            <Link
              to={`/remediations/${product.remediation_plan_id}`}
              className="mt-3 text-[11px] text-rose-400 hover:text-rose-300 flex items-center gap-1 font-medium transition-colors"
            >
              <span>View CAPA Plan</span>
              <ArrowUpRight size={13} />
            </Link>
          )}
        </div>
      </div>
    </Card>
  );
};
