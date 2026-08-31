import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { AIDeploymentApprovalCreate, AISystem } from '../../types';
import { AlertTriangle, Rocket, ShieldAlert } from 'lucide-react';

interface DeploymentApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  system: AISystem | null;
  onSubmit: (data: AIDeploymentApprovalCreate) => Promise<void>;
  isSubmitting?: boolean;
}

export const DeploymentApprovalModal: React.FC<DeploymentApprovalModalProps> = ({
  isOpen,
  onClose,
  system,
  onSubmit,
  isSubmitting = false,
}) => {
  const [targetEnvironment, setTargetEnvironment] = useState<'STAGING' | 'PRODUCTION'>('STAGING');
  const [riskAcceptanceJustification, setRiskAcceptanceJustification] = useState('');
  const [humanOversightMeasures, setHumanOversightMeasures] = useState('');
  const [error, setError] = useState<string | null>(null);

  const isProhibited = system?.regulatory_tier === 'PROHIBITED' || system?.is_prohibited_practice;
  const isDecommissioned = system?.lifecycle_state === 'DECOMMISSIONED';

  useEffect(() => {
    if (isOpen) {
      setTargetEnvironment('STAGING');
      setRiskAcceptanceJustification('');
      setHumanOversightMeasures('');
      setError(null);
    }
  }, [isOpen, system]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isProhibited && targetEnvironment === 'PRODUCTION') {
      setError('Prohibited AI systems cannot be deployed to PRODUCTION under EU AI Act Article 5.');
      return;
    }

    if (!riskAcceptanceJustification.trim() || riskAcceptanceJustification.trim().length < 5) {
      setError('Risk acceptance justification must be at least 5 characters.');
      return;
    }

    if (!humanOversightMeasures.trim() || humanOversightMeasures.trim().length < 5) {
      setError('Human oversight measures (HITL controls) must be at least 5 characters.');
      return;
    }

    try {
      await onSubmit({
        target_environment: targetEnvironment,
        risk_acceptance_justification: riskAcceptanceJustification.trim(),
        human_oversight_measures: humanOversightMeasures.trim(),
      });
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to submit deployment approval request.'
      );
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Request Deployment Approval: ${system?.system_code || ''}`}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-md flex items-start gap-2.5 text-xs text-rose-200">
            <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {isProhibited && (
          <div className="p-3 bg-rose-950/90 border border-rose-800 rounded-md flex items-start gap-2.5 text-xs text-rose-200">
            <ShieldAlert size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block">EU AI Act Article 5 Prohibited Practice</span>
              This system is classified as PROHIBITED and cannot be deployed to PRODUCTION. Staging tests must have strict containment.
            </div>
          </div>
        )}

        {isDecommissioned && (
          <div className="p-3 bg-amber-950/80 border border-amber-800 rounded-md flex items-start gap-2.5 text-xs text-amber-200">
            <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
            <span>Decommissioned systems are permanently locked and cannot request new deployments.</span>
          </div>
        )}

        <div className="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded-md flex items-start gap-2.5 text-xs text-indigo-200">
          <Rocket size={16} className="text-indigo-400 shrink-0 mt-0.5" />
          <span>
            <strong>Four-Eyes Governance:</strong> Submitting this request initiates formal gatekeeping. An independent authorized manager/admin (not the requester) must review and approve before deployment.
          </span>
        </div>

        {/* Target Environment */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Target Environment <span className="text-rose-400">*</span>
          </label>
          <select
            value={targetEnvironment}
            disabled={isDecommissioned}
            onChange={(e) => setTargetEnvironment(e.target.value as 'STAGING' | 'PRODUCTION')}
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500 disabled:opacity-50"
          >
            <option value="STAGING">STAGING (Pre-production validation &amp; testing)</option>
            <option value="PRODUCTION" disabled={isProhibited}>
              PRODUCTION (Live enterprise deployment) {isProhibited ? '— BLOCKED (PROHIBITED)' : ''}
            </option>
          </select>
        </div>

        {/* Risk Acceptance Justification */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Risk Acceptance Justification <span className="text-rose-400">*</span>
          </label>
          <textarea
            rows={3}
            required
            disabled={isDecommissioned}
            value={riskAcceptanceJustification}
            onChange={(e) => setRiskAcceptanceJustification(e.target.value)}
            placeholder="Document ethical justification, risk assessment findings, operational safeguards..."
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 disabled:opacity-50"
          />
        </div>

        {/* Human Oversight Measures */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Human Oversight &amp; HITL Controls <span className="text-rose-400">*</span>
          </label>
          <textarea
            rows={3}
            required
            disabled={isDecommissioned}
            value={humanOversightMeasures}
            onChange={(e) => setHumanOversightMeasures(e.target.value)}
            placeholder="Specify HITL governance controls, kill-switch procedures, fallback mechanisms..."
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 disabled:opacity-50"
          />
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            disabled={isDecommissioned || (isProhibited && targetEnvironment === 'PRODUCTION')}
          >
            Submit Deployment Request
          </Button>
        </div>
      </form>
    </Modal>
  );
};
