import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { resilienceService } from '../../lib/resilienceService';
import { tprmService } from '../../lib/tprmService';
import { remediationService } from '../../lib/remediationService';
import type {
  AIAutonomyLevel,
  AIDataSensitivity,
  AIHostingType,
  AIRegulatoryTier,
  AISystem,
  AISystemCreate,
  AISystemType,
  AISystemUpdate,
} from '../../types';
import { AlertTriangle, Bot, Layers, ShieldAlert } from 'lucide-react';

interface AISystemModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: AISystemCreate | AISystemUpdate) => Promise<void>;
  initialData?: AISystem | null;
  isSubmitting?: boolean;
}

export const AISystemModal: React.FC<AISystemModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isSubmitting = false,
}) => {
  const isEdit = !!initialData;

  const [systemCode, setSystemCode] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemType, setSystemType] = useState<AISystemType>('LLM_APPLICATION');
  const [regulatoryTier, setRegulatoryTier] = useState<AIRegulatoryTier>('HIGH_RISK');
  const [autonomyLevel, setAutonomyLevel] = useState<AIAutonomyLevel>('HUMAN_IN_THE_LOOP');
  const [dataSensitivity, setDataSensitivity] = useState<AIDataSensitivity>('INTERNAL');
  const [hostingType, setHostingType] = useState<AIHostingType>('CLOUD_THIRD_PARTY');

  // Technical Telemetry
  const [foundationModelName, setFoundationModelName] = useState('');
  const [modelVersion, setModelVersion] = useState('');
  const [trainingDataCutoff, setTrainingDataCutoff] = useState('');
  const [parametersBillion, setParametersBillion] = useState<string>('');
  const [contextWindowTokens, setContextWindowTokens] = useState<string>('');
  const [computeFlopsExponent, setComputeFlopsExponent] = useState<string>('');

  // Cross-Module Lineage
  const [businessProcessId, setBusinessProcessId] = useState<number | ''>('');
  const [vendorId, setVendorId] = useState<number | ''>('');
  const [remediationPlanId, setRemediationPlanId] = useState<number | ''>('');

  const [error, setError] = useState<string | null>(null);

  // Fetch candidate Business Processes (Phase 13)
  const { data: processes = [] } = useQuery({
    queryKey: ['resilience-processes-lookup'],
    queryFn: () => resilienceService.listProcesses({ limit: 100 }),
    enabled: isOpen,
  });

  // Fetch candidate Vendors (Phase 9)
  const { data: vendors = [] } = useQuery({
    queryKey: ['tprm-vendors-lookup'],
    queryFn: () => tprmService.listVendors({ limit: 100 }),
    enabled: isOpen,
  });

  // Fetch candidate Remediation Plans (Phase 11)
  const { data: remediationPlans = [] } = useQuery({
    queryKey: ['remediation-plans-lookup'],
    queryFn: () => remediationService.listPlans({ limit: 100 }),
    enabled: isOpen,
  });

  useEffect(() => {
    if (initialData) {
      setSystemCode(initialData.system_code);
      setName(initialData.name);
      setDescription(initialData.description || '');
      setSystemType(initialData.system_type);
      setRegulatoryTier(initialData.regulatory_tier);
      setAutonomyLevel(initialData.autonomy_level);
      setDataSensitivity(initialData.data_sensitivity);
      setHostingType(initialData.hosting_type);
      setFoundationModelName(initialData.foundation_model_name || '');
      setModelVersion(initialData.model_version || '');
      setTrainingDataCutoff(initialData.training_data_cutoff || '');
      setParametersBillion(
        initialData.parameters_billion !== null && initialData.parameters_billion !== undefined
          ? String(initialData.parameters_billion)
          : ''
      );
      setContextWindowTokens(
        initialData.context_window_tokens !== null && initialData.context_window_tokens !== undefined
          ? String(initialData.context_window_tokens)
          : ''
      );
      setComputeFlopsExponent(
        initialData.compute_flops_exponent !== null && initialData.compute_flops_exponent !== undefined
          ? String(initialData.compute_flops_exponent)
          : ''
      );
      setBusinessProcessId(initialData.business_process_id || '');
      setVendorId(initialData.vendor_id || '');
      setRemediationPlanId(initialData.remediation_plan_id || '');
    } else {
      setSystemCode('');
      setName('');
      setDescription('');
      setSystemType('LLM_APPLICATION');
      setRegulatoryTier('HIGH_RISK');
      setAutonomyLevel('HUMAN_IN_THE_LOOP');
      setDataSensitivity('INTERNAL');
      setHostingType('CLOUD_THIRD_PARTY');
      setFoundationModelName('');
      setModelVersion('');
      setTrainingDataCutoff('');
      setParametersBillion('');
      setContextWindowTokens('');
      setComputeFlopsExponent('');
      setBusinessProcessId('');
      setVendorId('');
      setRemediationPlanId('');
    }
    setError(null);
  }, [initialData, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isEdit && !systemCode.trim()) {
      setError('System code is required (e.g. AI-SYS-001).');
      return;
    }
    if (!name.trim() || name.trim().length < 2) {
      setError('System name must be at least 2 characters.');
      return;
    }

    try {
      if (isEdit) {
        const updatePayload: AISystemUpdate = {
          name: name.trim(),
          description: description.trim() || null,
          system_type: systemType,
          regulatory_tier: regulatoryTier,
          autonomy_level: autonomyLevel,
          data_sensitivity: dataSensitivity,
          hosting_type: hostingType,
          foundation_model_name: foundationModelName.trim() || null,
          model_version: modelVersion.trim() || null,
          training_data_cutoff: trainingDataCutoff.trim() || null,
          parameters_billion: parametersBillion ? parseFloat(parametersBillion) : null,
          context_window_tokens: contextWindowTokens ? parseInt(contextWindowTokens, 10) : null,
          compute_flops_exponent: computeFlopsExponent ? parseFloat(computeFlopsExponent) : null,
          business_process_id: businessProcessId === '' ? null : Number(businessProcessId),
          vendor_id: vendorId === '' ? null : Number(vendorId),
          remediation_plan_id: remediationPlanId === '' ? null : Number(remediationPlanId),
        };
        await onSubmit(updatePayload);
      } else {
        const createPayload: AISystemCreate = {
          system_code: systemCode.trim().toUpperCase(),
          name: name.trim(),
          description: description.trim() || null,
          system_type: systemType,
          regulatory_tier: regulatoryTier,
          autonomy_level: autonomyLevel,
          data_sensitivity: dataSensitivity,
          hosting_type: hostingType,
          foundation_model_name: foundationModelName.trim() || null,
          model_version: modelVersion.trim() || null,
          training_data_cutoff: trainingDataCutoff.trim() || null,
          parameters_billion: parametersBillion ? parseFloat(parametersBillion) : null,
          context_window_tokens: contextWindowTokens ? parseInt(contextWindowTokens, 10) : null,
          compute_flops_exponent: computeFlopsExponent ? parseFloat(computeFlopsExponent) : null,
          business_process_id: businessProcessId === '' ? null : Number(businessProcessId),
          vendor_id: vendorId === '' ? null : Number(vendorId),
          remediation_plan_id: remediationPlanId === '' ? null : Number(remediationPlanId),
        };
        await onSubmit(createPayload);
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to save AI system. Please verify parameters.'
      );
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit AI System: ${initialData?.system_code}` : 'Register New AI System'}
    >
      <form onSubmit={handleSubmit} className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
        {error && (
          <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-md flex items-start gap-2.5 text-xs text-rose-200">
            <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {regulatoryTier === 'PROHIBITED' && (
          <div className="p-3 bg-rose-950/60 border border-rose-800/80 rounded-md flex items-start gap-2.5 text-xs text-rose-200">
            <ShieldAlert size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block">EU AI Act Article 5 — Prohibited Practice</span>
              Systems classified as Prohibited are permanently banned from staging or production deployments.
            </div>
          </div>
        )}

        {/* System Code & Name */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              System Code {!isEdit && <span className="text-rose-400">*</span>}
            </label>
            <input
              type="text"
              required={!isEdit}
              disabled={isEdit}
              value={systemCode}
              onChange={(e) => setSystemCode(e.target.value)}
              placeholder="AI-SYS-001"
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 disabled:opacity-50 uppercase font-mono"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              System Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Underwriting Copilot Engine"
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            System Description
          </label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Operational description, functional scope, and architecture..."
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        {/* Governance & Classification Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              System Type <span className="text-rose-400">*</span>
            </label>
            <select
              value={systemType}
              onChange={(e) => setSystemType(e.target.value as AISystemType)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="LLM_APPLICATION">LLM Application (Generative)</option>
              <option value="AGENTIC_WORKFLOW">Agentic Workflow (Autonomous)</option>
              <option value="EMBEDDED_ML">Embedded Machine Learning</option>
              <option value="COMPUTER_VISION">Computer Vision & Biometrics</option>
              <option value="RECOMMENDER">Recommender System</option>
              <option value="PREDICTIVE_ANALYTICS">Predictive Analytics & Scoring</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              EU AI Act Regulatory Tier <span className="text-rose-400">*</span>
            </label>
            <select
              value={regulatoryTier}
              onChange={(e) => setRegulatoryTier(e.target.value as AIRegulatoryTier)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="PROHIBITED">Prohibited (Unacceptable Risk)</option>
              <option value="HIGH_RISK">High Risk (Annex III / Critical)</option>
              <option value="GPAI_SYSTEMIC_RISK">GPAI with Systemic Risk</option>
              <option value="LIMITED_RISK">Limited Risk (Transparency)</option>
              <option value="MINIMAL_RISK">Minimal / Low Risk</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Autonomy Level <span className="text-rose-400">*</span>
            </label>
            <select
              value={autonomyLevel}
              onChange={(e) => setAutonomyLevel(e.target.value as AIAutonomyLevel)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="NO_AUTONOMY">No Autonomy (Deterministic / Manual)</option>
              <option value="HUMAN_IN_THE_LOOP">Human-in-the-Loop (HITL)</option>
              <option value="HUMAN_ON_THE_LOOP">Human-on-the-Loop (HOTL)</option>
              <option value="FULL_AUTONOMY">Full Autonomy (Autonomous Execution)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Data Sensitivity <span className="text-rose-400">*</span>
            </label>
            <select
              value={dataSensitivity}
              onChange={(e) => setDataSensitivity(e.target.value as AIDataSensitivity)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="PUBLIC">Public Data</option>
              <option value="INTERNAL">Internal Business Data</option>
              <option value="CONFIDENTIAL">Confidential Corporate Data</option>
              <option value="RESTRICTED_PII_PHI">Restricted PII / PHI</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Hosting Architecture <span className="text-rose-400">*</span>
            </label>
            <select
              value={hostingType}
              onChange={(e) => setHostingType(e.target.value as AIHostingType)}
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="CLOUD_THIRD_PARTY">Cloud Third-Party SaaS / API</option>
              <option value="ON_PREMISE_SELF_HOSTED">On-Premise / Self-Hosted Cluster</option>
              <option value="HYBRID_VPC">Hybrid Dedicated VPC</option>
              <option value="EDGE_DEVICE">Edge Device / Embedded Firmware</option>
            </select>
          </div>
        </div>

        {/* Technical Architecture & Specs */}
        <div className="pt-2 border-t border-slate-800">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <Bot size={14} className="text-indigo-400" />
            Model Architecture &amp; Telemetry
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Foundation Model
              </label>
              <input
                type="text"
                value={foundationModelName}
                onChange={(e) => setFoundationModelName(e.target.value)}
                placeholder="e.g. GPT-4o, Claude 3.5"
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Model Version
              </label>
              <input
                type="text"
                value={modelVersion}
                onChange={(e) => setModelVersion(e.target.value)}
                placeholder="e.g. 2026-05-v1"
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Data Cutoff Date
              </label>
              <input
                type="text"
                value={trainingDataCutoff}
                onChange={(e) => setTrainingDataCutoff(e.target.value)}
                placeholder="e.g. 2025-12"
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Parameters (Billions)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={parametersBillion}
                onChange={(e) => setParametersBillion(e.target.value)}
                placeholder="e.g. 70.0"
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Context Window (Tokens)
              </label>
              <input
                type="number"
                step="1"
                min="0"
                value={contextWindowTokens}
                onChange={(e) => setContextWindowTokens(e.target.value)}
                placeholder="e.g. 128000"
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Compute FLOPs (10^N)
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={computeFlopsExponent}
                onChange={(e) => setComputeFlopsExponent(e.target.value)}
                placeholder="e.g. 25.5"
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>
          </div>
        </div>

        {/* Cross-Module Lineage Connections */}
        <div className="pt-2 border-t border-slate-800">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <Layers size={14} className="text-indigo-400" />
            Cross-Module Governance Lineage
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Business Process (Phase 13)
              </label>
              <select
                value={businessProcessId}
                onChange={(e) =>
                  setBusinessProcessId(e.target.value ? Number(e.target.value) : '')
                }
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="">-- None / Unlinked --</option>
                {processes.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.criticality_tier})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Vendor / Third-Party (Phase 9)
              </label>
              <select
                value={vendorId}
                onChange={(e) =>
                  setVendorId(e.target.value ? Number(e.target.value) : '')
                }
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="">-- None / Internal --</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.trade_name || v.legal_name} ({v.effective_tier || v.calculated_tier})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Remediation Plan (Phase 11)
              </label>
              <select
                value={remediationPlanId}
                onChange={(e) =>
                  setRemediationPlanId(e.target.value ? Number(e.target.value) : '')
                }
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
              >
                <option value="">-- None / No Active CAPA --</option>
                {remediationPlans.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title} ({r.status})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isSubmitting}>
            {isEdit ? 'Save Changes' : 'Register AI System'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
