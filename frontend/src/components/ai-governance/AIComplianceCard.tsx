import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { AISystem } from '../../types';
import { AlertOctagon, CheckCircle2, FileText, HelpCircle, Shield, ShieldAlert } from 'lucide-react';

interface AIComplianceCardProps {
  system: AISystem;
}

export const AIComplianceCard: React.FC<AIComplianceCardProps> = ({ system }) => {
  const complianceScore = Number(system.eu_compliance_score) || 0.0;
  const isProhibited = system.regulatory_tier === 'PROHIBITED' || system.is_prohibited_practice;
  const isHighRisk = system.regulatory_tier === 'HIGH_RISK';
  const isGpai = system.regulatory_tier === 'GPAI_SYSTEMIC_RISK';

  const getComplianceStatus = () => {
    if (isProhibited) {
      return {
        label: 'PROHIBITED PRACTICE',
        variant: 'danger' as const,
        description: 'Unacceptable risk under EU AI Act Article 5. Permanently banned from enterprise deployment.',
        icon: AlertOctagon,
      };
    }
    if (complianceScore >= 80.0) {
      return {
        label: 'CONFORMITY ASSURED',
        variant: 'success' as const,
        description: 'Meets comprehensive EU AI Act conformity and governance standards.',
        icon: CheckCircle2,
      };
    }
    if (complianceScore >= 50.0) {
      return {
        label: 'PENDING ASSESSMENT',
        variant: 'warning' as const,
        description: 'Additional technical controls, safety benchmarks, and documentation required.',
        icon: HelpCircle,
      };
    }
    return {
      label: 'NON-CONFORMANT',
      variant: 'danger' as const,
      description: 'Substantial regulatory non-compliance. Deployment is restricted until gaps are remediated.',
      icon: ShieldAlert,
    };
  };

  const status = getComplianceStatus();
  const StatusIcon = status.icon;

  return (
    <Card className="border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-emerald-950/80 border border-emerald-700/60 text-emerald-400">
            <Shield size={18} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              EU AI Act &amp; Regulatory Conformity
            </h3>
            <span className="text-[11px] text-slate-400">
              Harmonized European Artificial Intelligence Regulatory Compliance
            </span>
          </div>
        </div>

        <Badge variant={status.variant} className="text-xs px-2.5 py-1">
          {status.label}
        </Badge>
      </div>

      <div className="p-5 space-y-6">
        {/* Status Callout */}
        <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl flex items-start gap-3">
          <StatusIcon size={20} className={status.variant === 'danger' ? 'text-rose-400' : status.variant === 'warning' ? 'text-amber-400' : 'text-emerald-400'} />
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-slate-200">
                EU AI Act Compliance Score:
              </span>
              <span className="text-lg font-mono font-extrabold text-slate-100">
                {complianceScore.toFixed(1)} / 100.0
              </span>
            </div>
            <p className="text-xs text-slate-400">{status.description}</p>
          </div>
        </div>

        {/* Regulatory Requirements Checklist */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <FileText size={14} className="text-indigo-400" />
            Mandatory Compliance Obligations Matrix
          </h4>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs">
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 flex items-start justify-between">
              <div>
                <span className="font-semibold text-slate-200 block">
                  Fundamental Rights Impact Assessment (FRIA)
                </span>
                <span className="text-[11px] text-slate-400">
                  {isHighRisk ? 'Mandatory prior to high-risk deployment' : 'Recommended best practice'}
                </span>
              </div>
              <Badge variant={isHighRisk ? 'warning' : 'default'} className="text-[10px]">
                {isHighRisk ? 'MANDATORY' : 'OPTIONAL'}
              </Badge>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 flex items-start justify-between">
              <div>
                <span className="font-semibold text-slate-200 block">
                  Quality Management System (QMS)
                </span>
                <span className="text-[11px] text-slate-400">
                  {isHighRisk || isGpai ? 'Article 17 Continuous Compliance' : 'Standard Governance'}
                </span>
              </div>
              <Badge variant={isHighRisk || isGpai ? 'warning' : 'default'} className="text-[10px]">
                {isHighRisk || isGpai ? 'REQUIRED' : 'STANDARD'}
              </Badge>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 flex items-start justify-between">
              <div>
                <span className="font-semibold text-slate-200 block">
                  Model Card &amp; Technical Documentation
                </span>
                <span className="text-[11px] text-slate-400">
                  {system.model_cards && system.model_cards.length > 0
                    ? `${system.model_cards.length} versions published`
                    : 'No model card registered'}
                </span>
              </div>
              <Badge
                variant={system.model_cards && system.model_cards.length > 0 ? 'success' : 'danger'}
                className="text-[10px]"
              >
                {system.model_cards && system.model_cards.length > 0 ? 'ACTIVE' : 'MISSING'}
              </Badge>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800/80 flex items-start justify-between">
              <div>
                <span className="font-semibold text-slate-200 block">
                  Human Oversight &amp; Four-Eyes Gate
                </span>
                <span className="text-[11px] text-slate-400">
                  {system.autonomy_level === 'NO_AUTONOMY' || system.autonomy_level === 'HUMAN_IN_THE_LOOP'
                    ? 'HITL Operational Controls Active'
                    : 'HOTL / Autonomous System'}
                </span>
              </div>
              <Badge
                variant={
                  system.autonomy_level === 'HUMAN_IN_THE_LOOP' || system.autonomy_level === 'NO_AUTONOMY'
                    ? 'success'
                    : 'warning'
                }
                className="text-[10px]"
              >
                {system.autonomy_level === 'HUMAN_IN_THE_LOOP' ? 'HITL PASS' : 'HOTL REVIEW'}
              </Badge>
            </div>
          </div>
        </div>

        {/* Prohibited Alert Banner */}
        {isProhibited && (
          <div className="p-3.5 bg-rose-950/80 border border-rose-800 rounded-xl text-xs text-rose-200 space-y-1">
            <span className="font-bold flex items-center gap-1 text-rose-300">
              <AlertOctagon size={16} /> Article 5 Absolute Ban Active
            </span>
            <p className="text-rose-300/90 text-[11px]">
              Deploying cognitive behavioral manipulation, biometric categorization of sensitive traits, or social scoring violates international law and is blocked by platform authorization guardrails.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
};
