import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { DPIARiskBand } from '../../types';
import { AlertTriangle, ShieldAlert } from 'lucide-react';

interface PrivacyRiskCardProps {
  inherentRiskScore?: number;
  residualRiskScore?: number;
  riskBand?: DPIARiskBand;
  transferRiskIndex?: number;
  priorConsultationRequired?: boolean;
  title?: string;
  className?: string;
}

export const PrivacyRiskCard: React.FC<PrivacyRiskCardProps> = ({
  inherentRiskScore,
  residualRiskScore,
  riskBand,
  transferRiskIndex,
  priorConsultationRequired,
  title = 'Privacy Risk & Impact Telemetry',
  className = '',
}) => {
  const getRiskBandBadge = (band?: DPIARiskBand) => {
    switch (band) {
      case 'LOW':
        return <Badge variant="success">LOW RISK</Badge>;
      case 'MODERATE':
        return <Badge variant="info">MODERATE RISK</Badge>;
      case 'HIGH':
        return <Badge variant="warning">HIGH RISK</Badge>;
      case 'VERY_HIGH':
        return <Badge variant="danger">VERY HIGH RISK</Badge>;
      case 'CRITICAL':
        return <Badge variant="danger">CRITICAL RISK</Badge>;
      default:
        return <Badge variant="default">NOT ASSESSED</Badge>;
    }
  };

  const getScoreColor = (score?: number) => {
    if (score === undefined || score === null) return 'text-slate-400';
    if (score < 25) return 'text-emerald-400';
    if (score < 50) return 'text-sky-400';
    if (score < 75) return 'text-amber-400';
    if (score < 90) return 'text-orange-400';
    return 'text-rose-400';
  };

  return (
    <Card className={`p-5 bg-slate-900/90 border-slate-800 ${className}`}>
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <ShieldAlert size={18} className="text-indigo-400" />
          <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
        </div>
        {riskBand && getRiskBandBadge(riskBand)}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Inherent Risk Score */}
        {inherentRiskScore !== undefined && (
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
              Inherent Risk (IRS)
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold font-mono ${getScoreColor(inherentRiskScore)}`}>
                {inherentRiskScore.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500">/ 100</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Pre-mitigation baseline privacy exposure
            </p>
          </div>
        )}

        {/* Residual Risk Score */}
        {residualRiskScore !== undefined && (
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
              Residual Risk (RRS)
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold font-mono ${getScoreColor(residualRiskScore)}`}>
                {residualRiskScore.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500">/ 100</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Post-safeguard net privacy risk
            </p>
          </div>
        )}

        {/* Transfer Risk Index (TRI) */}
        {transferRiskIndex !== undefined && (
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider mb-1">
              Transfer Risk Index (TRI)
            </div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold font-mono ${getScoreColor(transferRiskIndex)}`}>
                {transferRiskIndex.toFixed(1)}
              </span>
              <span className="text-xs text-slate-500">/ 100</span>
            </div>
            <p className="text-[10px] text-slate-500 mt-1">
              Jurisdiction &amp; transfer mechanism risk
            </p>
          </div>
        )}
      </div>

      {/* Prior Consultation Alert */}
      {priorConsultationRequired && (
        <div className="mt-4 p-3 rounded-lg bg-rose-950/30 border border-rose-800/60 flex items-start gap-2.5">
          <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-semibold text-rose-300">
              GDPR Article 36 Prior Consultation Triggered
            </div>
            <div className="text-[11px] text-rose-300/80 mt-0.5">
              High residual risk (RRS &ge; 80.0) requires mandatory prior consultation with the Data Protection Authority (DPA) before processing begins.
            </div>
          </div>
        </div>
      )}

      <div className="mt-3 pt-2 text-[10px] text-slate-500 flex items-center justify-between border-t border-slate-800/50">
        <span>Authoritative backend calculation</span>
        <span className="font-mono">GDPR / ISO 27701 / NIST Privacy</span>
      </div>
    </Card>
  );
};
