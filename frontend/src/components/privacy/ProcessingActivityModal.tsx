import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { privacyService } from '../../lib/privacyService';
import type {
  ProcessingActivity,
  ProcessingActivityCreate,
  ProcessingActivityUpdate,
  ProcessingLegalBasis,
  TransferMechanism,
} from '../../types';
import { AlertCircle, Globe, RefreshCw } from 'lucide-react';

interface ProcessingActivityModalProps {
  isOpen: boolean;
  onClose: () => void;
  activity?: ProcessingActivity | null;
  onSuccess: () => void;
}

export const ProcessingActivityModal: React.FC<ProcessingActivityModalProps> = ({
  isOpen,
  onClose,
  activity,
  onSuccess,
}) => {
  const isEdit = Boolean(activity);

  const [activityCode, setActivityCode] = useState('');
  const [name, setName] = useState('');
  const [purposeDescription, setPurposeDescription] = useState('');
  const [legalBasis, setLegalBasis] = useState<ProcessingLegalBasis>('CONSENT');
  const [dataSubjectCategories, setDataSubjectCategories] = useState('CUSTOMERS');
  const [personalDataCategories, setPersonalDataCategories] = useState('IDENTIFIERS, CONTACT');
  const [isSpecialCategoryData, setIsSpecialCategoryData] = useState(false);
  const [isAutomatedDecisionMaking, setIsAutomatedDecisionMaking] = useState(false);
  const [isLargeScaleMonitoring, setIsLargeScaleMonitoring] = useState(false);
  const [isVulnerableSubjects, setIsVulnerableSubjects] = useState(false);
  const [isCrossBorderTransfer, setIsCrossBorderTransfer] = useState(false);
  const [transferMechanism, setTransferMechanism] = useState<TransferMechanism>('NONE_INTRA_EEA');
  const [destinationCountry, setDestinationCountry] = useState('');
  const [securityMeasuresSummary, setSecurityMeasuresSummary] = useState('');
  const [dataControllerName, setDataControllerName] = useState('');
  const [businessProcessId, setBusinessProcessId] = useState<string>('');
  const [aiSystemId, setAiSystemId] = useState<string>('');
  const [vendorId, setVendorId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (activity) {
      setActivityCode(activity.activity_code);
      setName(activity.name);
      setPurposeDescription(activity.purpose_description);
      setLegalBasis(activity.legal_basis);
      setDataSubjectCategories(activity.data_subject_categories);
      setPersonalDataCategories(activity.personal_data_categories);
      setIsSpecialCategoryData(activity.is_special_category_data);
      setIsAutomatedDecisionMaking(activity.is_automated_decision_making);
      setIsLargeScaleMonitoring(activity.is_large_scale_monitoring);
      setIsVulnerableSubjects(activity.is_vulnerable_subjects);
      setIsCrossBorderTransfer(activity.is_cross_border_transfer);
      setTransferMechanism(activity.transfer_mechanism);
      setDestinationCountry(activity.destination_country || '');
      setSecurityMeasuresSummary(activity.security_measures_summary || '');
      setDataControllerName(activity.data_controller_name || '');
      setBusinessProcessId(activity.business_process_id ? String(activity.business_process_id) : '');
      setAiSystemId(activity.ai_system_id ? String(activity.ai_system_id) : '');
      setVendorId(activity.vendor_id ? String(activity.vendor_id) : '');
    } else {
      setActivityCode('');
      setName('');
      setPurposeDescription('');
      setLegalBasis('CONSENT');
      setDataSubjectCategories('CUSTOMERS');
      setPersonalDataCategories('IDENTIFIERS, CONTACT');
      setIsSpecialCategoryData(false);
      setIsAutomatedDecisionMaking(false);
      setIsLargeScaleMonitoring(false);
      setIsVulnerableSubjects(false);
      setIsCrossBorderTransfer(false);
      setTransferMechanism('NONE_INTRA_EEA');
      setDestinationCountry('');
      setSecurityMeasuresSummary('');
      setDataControllerName('');
      setBusinessProcessId('');
      setAiSystemId('');
      setVendorId('');
    }
    setErrorMsg(null);
  }, [activity, isOpen]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEdit && activity) {
        const updateData: ProcessingActivityUpdate = {
          name: name.trim(),
          purpose_description: purposeDescription.trim(),
          legal_basis: legalBasis,
          data_subject_categories: dataSubjectCategories.trim(),
          personal_data_categories: personalDataCategories.trim(),
          is_special_category_data: isSpecialCategoryData,
          is_automated_decision_making: isAutomatedDecisionMaking,
          is_large_scale_monitoring: isLargeScaleMonitoring,
          is_vulnerable_subjects: isVulnerableSubjects,
          is_cross_border_transfer: isCrossBorderTransfer,
          transfer_mechanism: isCrossBorderTransfer ? transferMechanism : 'NONE_INTRA_EEA',
          destination_country: isCrossBorderTransfer ? destinationCountry.trim() || null : null,
          security_measures_summary: securityMeasuresSummary.trim() || null,
          data_controller_name: dataControllerName.trim() || null,
          business_process_id: businessProcessId ? Number(businessProcessId) : null,
          ai_system_id: aiSystemId ? Number(aiSystemId) : null,
          vendor_id: vendorId ? Number(vendorId) : null,
        };
        return privacyService.updateProcessingActivity(activity.id, updateData);
      } else {
        const createData: ProcessingActivityCreate = {
          activity_code: activityCode.trim(),
          name: name.trim(),
          purpose_description: purposeDescription.trim(),
          legal_basis: legalBasis,
          data_subject_categories: dataSubjectCategories.trim(),
          personal_data_categories: personalDataCategories.trim(),
          is_special_category_data: isSpecialCategoryData,
          is_automated_decision_making: isAutomatedDecisionMaking,
          is_large_scale_monitoring: isLargeScaleMonitoring,
          is_vulnerable_subjects: isVulnerableSubjects,
          is_cross_border_transfer: isCrossBorderTransfer,
          transfer_mechanism: isCrossBorderTransfer ? transferMechanism : 'NONE_INTRA_EEA',
          destination_country: isCrossBorderTransfer ? destinationCountry.trim() || null : null,
          security_measures_summary: securityMeasuresSummary.trim() || null,
          data_controller_name: dataControllerName.trim() || null,
          business_process_id: businessProcessId ? Number(businessProcessId) : null,
          ai_system_id: aiSystemId ? Number(aiSystemId) : null,
          vendor_id: vendorId ? Number(vendorId) : null,
        };
        return privacyService.createProcessingActivity(createData);
      }
    },
    onSuccess: () => {
      setErrorMsg(null);
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to save processing activity';
      setErrorMsg(msg);
    },
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit RoPA Activity: ${activity?.activity_code}` : 'Register New Processing Activity (RoPA)'}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
        className="space-y-4 max-h-[80vh] overflow-y-auto pr-1"
      >
        {/* Activity Code & Name */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Activity Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              disabled={isEdit}
              value={activityCode}
              onChange={(e) => setActivityCode(e.target.value.toUpperCase())}
              placeholder="e.g. ROPA-HR-001"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 font-mono disabled:opacity-60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Activity Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Global Employee Payroll &amp; Tax"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Purpose Description */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Processing Purpose (GDPR Art 30) <span className="text-rose-400">*</span>
          </label>
          <textarea
            required
            value={purposeDescription}
            onChange={(e) => setPurposeDescription(e.target.value)}
            rows={2}
            placeholder="State the explicit legitimate business purpose for processing personal data..."
            className="w-full bg-slate-950 border border-slate-800 rounded-md p-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 placeholder:text-slate-600"
          />
        </div>

        {/* Legal Basis */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Article 6 Lawful Basis <span className="text-rose-400">*</span>
          </label>
          <select
            value={legalBasis}
            onChange={(e) => setLegalBasis(e.target.value as ProcessingLegalBasis)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
          >
            <option value="CONSENT">CONSENT (Explicit Data Subject Consent)</option>
            <option value="CONTRACT_PERFORMANCE">CONTRACT_PERFORMANCE (Performance of a Contract)</option>
            <option value="LEGAL_OBLIGATION">LEGAL_OBLIGATION (Compliance with Legal Obligation)</option>
            <option value="VITAL_INTERESTS">VITAL_INTERESTS (Protection of Vital Interests)</option>
            <option value="PUBLIC_TASK">PUBLIC_TASK (Performance of Public Task / Authority)</option>
            <option value="LEGITIMATE_INTERESTS">LEGITIMATE_INTERESTS (Legitimate Interests Assessment)</option>
          </select>
        </div>

        {/* Categories */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Data Subject Categories <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={dataSubjectCategories}
              onChange={(e) => setDataSubjectCategories(e.target.value)}
              placeholder="e.g. CUSTOMERS, EMPLOYEES"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Personal Data Categories <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={personalDataCategories}
              onChange={(e) => setPersonalDataCategories(e.target.value)}
              placeholder="e.g. IDENTIFIERS, FINANCIAL, LOCATION"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* DPIA Triggers */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            DPIA Risk Triggers (GDPR Article 35)
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isSpecialCategoryData}
                onChange={(e) => setIsSpecialCategoryData(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Special Category Data (Art 9)</span>
            </label>
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isAutomatedDecisionMaking}
                onChange={(e) => setIsAutomatedDecisionMaking(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Automated Decision / Profiling (Art 22)</span>
            </label>
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isLargeScaleMonitoring}
                onChange={(e) => setIsLargeScaleMonitoring(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Large-Scale Systematic Monitoring</span>
            </label>
            <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={isVulnerableSubjects}
                onChange={(e) => setIsVulnerableSubjects(e.target.checked)}
                className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
              />
              <span>Vulnerable Data Subjects (Minors/Patients)</span>
            </label>
          </div>
        </div>

        {/* Cross-Border Transfer Section */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-3">
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={isCrossBorderTransfer}
              onChange={(e) => setIsCrossBorderTransfer(e.target.checked)}
              className="rounded border-slate-800 bg-slate-900 text-indigo-600 focus:ring-0"
            />
            <span className="flex items-center gap-1.5">
              <Globe size={14} className="text-sky-400" />
              Involves Cross-Border International Data Transfer (Chapter V)
            </span>
          </label>

          {isCrossBorderTransfer && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800/60">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Destination Country
                </label>
                <input
                  type="text"
                  value={destinationCountry}
                  onChange={(e) => setDestinationCountry(e.target.value)}
                  placeholder="e.g. United States, Japan, UK"
                  className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Transfer Safeguard Mechanism
                </label>
                <select
                  value={transferMechanism}
                  onChange={(e) => setTransferMechanism(e.target.value as TransferMechanism)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="ADEQUACY_DECISION">ADEQUACY_DECISION (Art 45)</option>
                  <option value="STANDARD_CONTRACTUAL_CLAUSES_SCC">STANDARD_CONTRACTUAL_CLAUSES_SCC (Art 46)</option>
                  <option value="BINDING_CORPORATE_RULES_BCR">BINDING_CORPORATE_RULES_BCR (Art 47)</option>
                  <option value="DEROGATION_EXPLICIT_CONSENT">DEROGATION_EXPLICIT_CONSENT (Art 49)</option>
                  <option value="NO_SAFEGUARDS_PROHIBITED">NO_SAFEGUARDS_PROHIBITED</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Security Summary & Controller */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Data Controller Entity Name
            </label>
            <input
              type="text"
              value={dataControllerName}
              onChange={(e) => setDataControllerName(e.target.value)}
              placeholder="e.g. Apex Financial Services LLC"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Security Measures Summary
            </label>
            <input
              type="text"
              value={securityMeasuresSummary}
              onChange={(e) => setSecurityMeasuresSummary(e.target.value)}
              placeholder="e.g. AES-256 GCM, TLS 1.3, RBAC &amp; MFA"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Cross-Module Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Business Process ID
            </label>
            <input
              type="number"
              value={businessProcessId}
              onChange={(e) => setBusinessProcessId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">AI System ID</label>
            <input
              type="number"
              value={aiSystemId}
              onChange={(e) => setAiSystemId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Vendor ID</label>
            <input
              type="number"
              value={vendorId}
              onChange={(e) => setVendorId(e.target.value)}
              placeholder="e.g. 1"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
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
              'Update Activity'
            ) : (
              'Register Activity'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
