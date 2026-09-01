import React from 'react';
import { Link } from 'react-router-dom';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import {
  Bot,
  Building2,
  ExternalLink,
  Layers,
  Link2,
  Target,
} from 'lucide-react';

interface PrivacyLineageCardProps {
  businessProcessId?: number | null;
  aiSystemId?: number | null;
  vendorId?: number | null;
  remediationPlanId?: number | null;
  className?: string;
}

export const PrivacyLineageCard: React.FC<PrivacyLineageCardProps> = ({
  businessProcessId,
  aiSystemId,
  vendorId,
  remediationPlanId,
  className = '',
}) => {
  const hasLineage =
    Boolean(businessProcessId) ||
    Boolean(aiSystemId) ||
    Boolean(vendorId) ||
    Boolean(remediationPlanId);

  return (
    <Card className={`p-5 bg-slate-900/90 border-slate-800 ${className}`}>
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Link2 size={18} className="text-cyan-400" />
          <h4 className="text-sm font-semibold text-slate-200">
            Cross-Module GRC Lineage &amp; Integrations
          </h4>
        </div>
        <Badge variant={hasLineage ? 'info' : 'default'}>
          {hasLineage ? 'LINKED' : 'UNLINKED'}
        </Badge>
      </div>

      {!hasLineage ? (
        <div className="py-6 text-center text-xs text-slate-500">
          No cross-module GRC associations recorded for this privacy entity.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {/* Business Process (Phase 13) */}
          {businessProcessId && (
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-indigo-950/50 border border-indigo-800/50 text-indigo-400">
                  <Layers size={16} />
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-mono uppercase">
                    Phase 13 Resilience
                  </div>
                  <div className="text-xs font-medium text-slate-200">
                    Business Process #{businessProcessId}
                  </div>
                </div>
              </div>
              <Link
                to={`/resilience/processes/${businessProcessId}`}
                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-indigo-400 transition-colors"
                title="View Business Process"
              >
                <ExternalLink size={14} />
              </Link>
            </div>
          )}

          {/* AI System (Phase 15) */}
          {aiSystemId && (
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-purple-950/50 border border-purple-800/50 text-purple-400">
                  <Bot size={16} />
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-mono uppercase">
                    Phase 15 AI-GRC
                  </div>
                  <div className="text-xs font-medium text-slate-200">
                    AI System #{aiSystemId}
                  </div>
                </div>
              </div>
              <Link
                to={`/ai-governance/systems/${aiSystemId}`}
                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-purple-400 transition-colors"
                title="View AI System"
              >
                <ExternalLink size={14} />
              </Link>
            </div>
          )}

          {/* Third-Party Vendor (Phase 9) */}
          {vendorId && (
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-amber-950/50 border border-amber-800/50 text-amber-400">
                  <Building2 size={16} />
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-mono uppercase">
                    Phase 9 TPRM
                  </div>
                  <div className="text-xs font-medium text-slate-200">
                    Third-Party Vendor #{vendorId}
                  </div>
                </div>
              </div>
              <Link
                to={`/vendors/${vendorId}`}
                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-amber-400 transition-colors"
                title="View Vendor"
              >
                <ExternalLink size={14} />
              </Link>
            </div>
          )}

          {/* Remediation CAPA Plan (Phase 11) */}
          {remediationPlanId && (
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded bg-emerald-950/50 border border-emerald-800/50 text-emerald-400">
                  <Target size={16} />
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 font-mono uppercase">
                    Phase 11 Remediation
                  </div>
                  <div className="text-xs font-medium text-slate-200">
                    CAPA Plan #{remediationPlanId}
                  </div>
                </div>
              </div>
              <Link
                to={`/remediations/${remediationPlanId}`}
                className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400 transition-colors"
                title="View Remediation Plan"
              >
                <ExternalLink size={14} />
              </Link>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
