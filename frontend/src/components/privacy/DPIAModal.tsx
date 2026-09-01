import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { privacyService } from '../../lib/privacyService';
import type {
  DPIAAssessment,
  DPIACalculatePreviewResponse,
  DPIACreate,
  DPIAUpdate,
} from '../../types';
import {
  AlertCircle,
  AlertTriangle,
  Calculator,
  RefreshCw,
} from 'lucide-react';

interface DPIAModalProps {
  isOpen: boolean;
  onClose: () => void;
  dpia?: DPIAAssessment | null;
  processingActivityId?: number;
  onSuccess: () => void;
}

export const DPIAModal: React.FC<DPIAModalProps> = ({
  isOpen,
  onClose,
  dpia,
  processingActivityId,
  onSuccess,
}) => {
  const isEdit = Boolean(dpia);

  const [assessmentCode, setAssessmentCode] = useState('');
  const [activityId, setActivityId] = useState<number>(processingActivityId || 1);
  const [necessityScore, setNecessityScore] = useState<number>(80.0);
  const [rightsScore, setRightsScore] = useState<number>(85.0);
  const [safeguardsScore, setSafeguardsScore] = useState<number>(50.0);
  const [automatedDecisionRisk, setAutomatedDecisionRisk] = useState(false);
  const [largeScaleMonitoringRisk, setLargeScaleMonitoringRisk] = useState(false);
  const [vulnerableSubjectsRisk, setVulnerableSubjectsRisk] = useState(false);
  const [remediationPlanId, setRemediationPlanId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Server calculation preview state
  const [previewResult, setPreviewResult] = useState<DPIACalculatePreviewResponse | null>(null);

  useEffect(() => {
    if (dpia) {
      setAssessmentCode(dpia.assessment_code);
      setActivityId(dpia.processing_activity_id);
      setNecessityScore(dpia.necessity_proportionality_score);
      setRightsScore(dpia.data_subject_rights_score);
      setSafeguardsScore(dpia.safeguards_mitigation_score);
      setAutomatedDecisionRisk(dpia.automated_decision_making_risk);
      setLargeScaleMonitoringRisk(dpia.large_scale_monitoring_risk);
      setVulnerableSubjectsRisk(dpia.vulnerable_subjects_risk);
      setRemediationPlanId(dpia.remediation_plan_id ? String(dpia.remediation_plan_id) : '');
    } else {
      setAssessmentCode('');
      setActivityId(processingActivityId || 1);
      setNecessityScore(80.0);
      setRightsScore(85.0);
      setSafeguardsScore(50.0);
      setAutomatedDecisionRisk(false);
      setLargeScaleMonitoringRisk(false);
      setVulnerableSubjectsRisk(false);
      setRemediationPlanId('');
    }
    setErrorMsg(null);
  }, [dpia, processingActivityId, isOpen]);

  // Fetch live server calculation preview
  const fetchPreview = async () => {
    try {
      const res = await privacyService.calculateDPIAPreview({
        automated_decision_making_risk: automatedDecisionRisk,
        large_scale_monitoring_risk: largeScaleMonitoringRisk,
        vulnerable_subjects_risk: vulnerableSubjectsRisk,
        safeguards_mitigation_score: safeguardsScore,
      });
      setPreviewResult(res);
    } catch {
      // Fallback silently if preview unavailable
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchPreview();
    }
  }, [
    isOpen,
    automatedDecisionRisk,
    largeScaleMonitoringRisk,
    vulnerableSubjectsRisk,
    safeguardsScore,
  ]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEdit && dpia) {
        const updateData: DPIAUpdate = {
          necessity_proportionality_score: necessityScore,
          data_subject_rights_score: rightsScore,
          safeguards_mitigation_score: safeguardsScore,
          automated_decision_making_risk: automatedDecisionRisk,
          large_scale_monitoring_risk: largeScaleMonitoringRisk,
          vulnerable_subjects_risk: vulnerableSubjectsRisk,
          remediation_plan_id: remediationPlanId ? Number(remediationPlanId) : null,
        };
        return privacyService.updateDPIA(dpia.id, updateData);
      } else {
        const createData: DPIACreate = {
          assessment_code: assessmentCode.trim(),
          processing_activity_id: activityId,
          necessity_proportionality_score: necessityScore,
          data_subject_rights_score: rightsScore,
          safeguards_mitigation_score: safeguardsScore,
          automated_decision_making_risk: automatedDecisionRisk,
          large_scale_monitoring_risk: largeScaleMonitoringRisk,
          vulnerable_subjects_risk: vulnerableSubjectsRisk,
          prior_consultation_required: previewResult?.prior_consultation_required ?? false,
          remediation_plan_id: remediationPlanId ? Number(remediationPlanId) : null,
        };
        return privacyService.createDPIA(createData);
      }
    },
    onSuccess: () => {
      setErrorMsg(null);
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to save DPIA assessment';
      setErrorMsg(msg);
    },
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Update DPIA: ${dpia?.assessment_code}` : 'Conduct Data Protection Impact Assessment (DPIA)'}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="space-y-4 max-h-[80vh] overflow-y-auto pr-1"
      >
        {/* Dynamic Server Preview Banner */}
        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Calculator size={13} className="text-indigo-400" />
              Server-Authoritative Live Risk Preview
            </span>
            {previewResult && (
              <Badge
                variant={
                  previewResult.risk_band === 'LOW'
                    ? 'success'
                    : previewResult.risk_band === 'MODERATE'
                    ? 'info'
                    : previewResult.risk_band === 'HIGH'
                    ? 'warning'
                    : 'danger'
                }
              >
                {previewResult.risk_band}
              </Badge>
            )}
          </div>
          {previewResult ? (
            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="p-2 rounded bg-slate-900 border border-slate-800">
                <div className="text-[10px] text-slate-400">Inherent Risk (IRS)</div>
                <div className="text-lg font-bold font-mono text-amber-400">
                  {previewResult.inherent_risk_score.toFixed(1)} / 100
                </div>
              </div>
              <div className="p-2 rounded bg-slate-900 border border-slate-800">
                <div className="text-[10px] text-slate-400">Residual Risk (RRS)</div>
                <div className="text-lg font-bold font-mono text-indigo-400">
                  {previewResult.residual_risk_score.toFixed(1)} / 100
                </div>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500 py-1 flex items-center gap-2">
              <RefreshCw size={13} className="animate-spin" />
              <span>Querying backend risk formula...</span>
            </div>
          )}
          {previewResult?.prior_consultation_required && (
            <div className="p-2 rounded bg-rose-950/40 border border-rose-800/60 text-[11px] text-rose-300 flex items-start gap-1.5">
              <AlertTriangle size={13} className="shrink-0 mt-0.5" />
              <span>Residual risk &ge; 80.0 will trigger mandatory GDPR Art 36 Prior Consultation.</span>
            </div>
          )}
        </div>

        {/* Code & Activity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Assessment Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              disabled={isEdit}
              value={assessmentCode}
              onChange={(e) => setAssessmentCode(e.target.value.toUpperCase())}
              placeholder="e.g. DPIA-HR-001"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 font-mono disabled:opacity-60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Target Processing Activity ID <span className="text-rose-400">*</span>
            </label>
            <input
              type="number"
              required
              disabled={isEdit || Boolean(processingActivityId)}
              value={activityId}
              onChange={(e) => setActivityId(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 disabled:opacity-60"
            />
          </div>
        </div>

        {/* Assessment Score Sliders */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Necessity &amp; Proportionality Score</span>
              <span className="font-mono text-indigo-400">{necessityScore.toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={necessityScore}
              onChange={(e) => setNecessityScore(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Data Subject Rights Protection Score</span>
              <span className="font-mono text-indigo-400">{rightsScore.toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={rightsScore}
              onChange={(e) => setRightsScore(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Safeguards &amp; Technical Mitigations</span>
              <span className="font-mono text-indigo-400">{safeguardsScore.toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={safeguardsScore}
              onChange={(e) => setSafeguardsScore(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>
        </div>

        {/* Risk Trigger Flags */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            DPIA Trigger Checkpoints
          </div>
          <div className="space-y-1.5 text-xs">
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={automatedDecisionRisk}
                onChange={(e) => setAutomatedDecisionRisk(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>High Risk Automated Decision-Making / Profiling</span>
            </label>
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={largeScaleMonitoringRisk}
                onChange={(e) => setLargeScaleMonitoringRisk(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>High Risk Systematic Monitoring on Large Scale</span>
            </label>
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={vulnerableSubjectsRisk}
                onChange={(e) => setVulnerableSubjectsRisk(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Processing Involves Vulnerable Subjects</span>
            </label>
          </div>
        </div>

        {/* Remediation Plan Linkage */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Linked CAPA Remediation Plan ID (Optional)
          </label>
          <input
            type="number"
            value={remediationPlanId}
            onChange={(e) => setRemediationPlanId(e.target.value)}
            placeholder="e.g. 1 (from Phase 11 Remediation)"
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        {/* Error message */}
        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-800/80 flex items-start gap-2 text-xs text-rose-300">
            <AlertCircle size={15} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button variant="ghost" type="button" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? (
              <span className="flex items-center gap-1.5">
                <RefreshCw size={14} className="animate-spin" />
                Saving...
              </span>
            ) : isEdit ? (
              'Update DPIA'
            ) : (
              'Submit DPIA'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
