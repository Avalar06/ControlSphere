import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { privacyService } from '../../lib/privacyService';
import type {
  DataTransferAssessment,
  DataTransferCalculatePreviewResponse,
  DataTransferCreate,
  JurisdictionRiskTier,
  TransferMechanism,
} from '../../types';
import {
  AlertCircle,
  Calculator,
  RefreshCw,
} from 'lucide-react';

interface DataTransferModalProps {
  isOpen: boolean;
  onClose: () => void;
  transfer?: DataTransferAssessment | null;
  processingActivityId?: number;
  onSuccess: () => void;
}

export const DataTransferModal: React.FC<DataTransferModalProps> = ({
  isOpen,
  onClose,
  transfer,
  processingActivityId,
  onSuccess,
}) => {
  const isEdit = Boolean(transfer);

  const [transferCode, setTransferCode] = useState('');
  const [activityId, setActivityId] = useState<number>(processingActivityId || 1);
  const [sourceCountry, setSourceCountry] = useState('EU_EEA');
  const [destinationCountry, setDestinationCountry] = useState('');
  const [jurisdictionTier, setJurisdictionTier] =
    useState<JurisdictionRiskTier>('MODERATE_SAFEGUARDS_REQUIRED');
  const [transferMechanism, setTransferMechanism] =
    useState<TransferMechanism>('STANDARD_CONTRACTUAL_CLAUSES_SCC');
  const [supplementaryDescription, setSupplementaryDescription] = useState('');
  const [supplementaryScore, setSupplementaryScore] = useState<number>(10.0);
  const [governmentAccessRisk, setGovernmentAccessRisk] = useState<number>(50.0);
  const [legalRemediesScore, setLegalRemediesScore] = useState<number>(50.0);
  const [auditNotes, setAuditNotes] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Server calculation preview state
  const [previewResult, setPreviewResult] =
    useState<DataTransferCalculatePreviewResponse | null>(null);

  useEffect(() => {
    if (transfer) {
      setTransferCode(transfer.transfer_code);
      setActivityId(transfer.processing_activity_id);
      setSourceCountry(transfer.source_country);
      setDestinationCountry(transfer.destination_country);
      setJurisdictionTier(transfer.destination_jurisdiction_tier);
      setTransferMechanism(transfer.transfer_mechanism);
      setSupplementaryDescription(transfer.supplementary_safeguards_description || '');
      setSupplementaryScore(transfer.supplementary_measures_score);
      setGovernmentAccessRisk(transfer.government_access_risk_score);
      setLegalRemediesScore(transfer.legal_remedies_score);
      setAuditNotes(transfer.audit_notes || '');
    } else {
      setTransferCode('');
      setActivityId(processingActivityId || 1);
      setSourceCountry('EU_EEA');
      setDestinationCountry('');
      setJurisdictionTier('MODERATE_SAFEGUARDS_REQUIRED');
      setTransferMechanism('STANDARD_CONTRACTUAL_CLAUSES_SCC');
      setSupplementaryDescription('');
      setSupplementaryScore(10.0);
      setGovernmentAccessRisk(50.0);
      setLegalRemediesScore(50.0);
      setAuditNotes('');
    }
    setErrorMsg(null);
  }, [transfer, processingActivityId, isOpen]);

  // Fetch live server TRI preview
  const fetchPreview = async () => {
    try {
      const res = await privacyService.calculateTransferPreview({
        destination_jurisdiction_tier: jurisdictionTier,
        transfer_mechanism: transferMechanism,
        supplementary_measures_score: supplementaryScore,
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
  }, [isOpen, jurisdictionTier, transferMechanism, supplementaryScore]);

  const mutation = useMutation({
    mutationFn: async () => {
      const createData: DataTransferCreate = {
        transfer_code: transferCode.trim(),
        processing_activity_id: activityId,
        source_country: sourceCountry.trim(),
        destination_country: destinationCountry.trim(),
        destination_jurisdiction_tier: jurisdictionTier,
        transfer_mechanism: transferMechanism,
        supplementary_safeguards_description: supplementaryDescription.trim() || null,
        supplementary_measures_score: supplementaryScore,
        government_access_risk_score: governmentAccessRisk,
        legal_remedies_score: legalRemediesScore,
        audit_notes: auditNotes.trim() || null,
      };
      return privacyService.createDataTransfer(createData);
    },
    onSuccess: () => {
      setErrorMsg(null);
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to save transfer assessment';
      setErrorMsg(msg);
    },
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        isEdit
          ? `Transfer Assessment: ${transfer?.transfer_code}`
          : 'Conduct Transfer Impact Assessment (TIA)'
      }
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
              <Calculator size={13} className="text-sky-400" />
              Server-Authoritative TRI Live Preview
            </span>
            <Badge variant="info">TIA GOVERNANCE</Badge>
          </div>
          {previewResult ? (
            <div className="p-2.5 rounded bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <div className="text-[10px] text-slate-400 font-medium">
                  Transfer Risk Index (TRI)
                </div>
                <div className="text-xs text-slate-500 mt-0.5">
                  Jurisdiction base + mechanism risk - supplementary reduction
                </div>
              </div>
              <div className="text-2xl font-bold font-mono text-sky-400">
                {previewResult.transfer_risk_index.toFixed(1)}{' '}
                <span className="text-xs text-slate-500 font-normal">/ 100</span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500 py-1 flex items-center gap-2">
              <RefreshCw size={13} className="animate-spin" />
              <span>Querying transfer risk formula...</span>
            </div>
          )}
        </div>

        {/* Code & Activity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Transfer Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              disabled={isEdit}
              value={transferCode}
              onChange={(e) => setTransferCode(e.target.value.toUpperCase())}
              placeholder="e.g. TIA-US-001"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 font-mono disabled:opacity-60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Target Activity ID <span className="text-rose-400">*</span>
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

        {/* Source & Destination */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Source Country / Region
            </label>
            <input
              type="text"
              value={sourceCountry}
              onChange={(e) => setSourceCountry(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Destination Country <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={destinationCountry}
              onChange={(e) => setDestinationCountry(e.target.value)}
              placeholder="e.g. United States, Japan, Brazil"
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Jurisdiction Tier & Mechanism */}
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Destination Jurisdiction Risk Tier
            </label>
            <select
              value={jurisdictionTier}
              onChange={(e) => setJurisdictionTier(e.target.value as JurisdictionRiskTier)}
              className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500"
            >
              <option value="ADEQUATE_EEA_EQUIVALENT">
                ADEQUATE_EEA_EQUIVALENT (Adequacy Decision Countries)
              </option>
              <option value="MODERATE_SAFEGUARDS_REQUIRED">
                MODERATE_SAFEGUARDS_REQUIRED (Standard Third Countries e.g. US with DPF)
              </option>
              <option value="HIGH_RISK_SURVEILLANCE">
                HIGH_RISK_SURVEILLANCE (Broad Government Access Laws)
              </option>
              <option value="RESTRICTED_EMBARGOED">
                RESTRICTED_EMBARGOED (Sanctioned / Restricted Jurisdictions)
              </option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Transfer Safeguard Mechanism (GDPR Chapter V)
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

        {/* Supplementary Measures */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Supplementary Safeguards Description (Schrems II)
          </label>
          <textarea
            value={supplementaryDescription}
            onChange={(e) => setSupplementaryDescription(e.target.value)}
            rows={2}
            placeholder="Document technical encryption (BYOK), organizational policies, or contractual supplementary clauses..."
            className="w-full bg-slate-950 border border-slate-800 rounded-md p-2 text-xs text-slate-200 focus:outline-hidden focus:border-indigo-500 placeholder:text-slate-600"
          />
        </div>

        {/* Sliders */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Supplementary Measures Mitigation Score</span>
              <span className="font-mono text-sky-400">-{supplementaryScore.toFixed(0)} pts</span>
            </div>
            <input
              type="range"
              min="0"
              max="30"
              value={supplementaryScore}
              onChange={(e) => setSupplementaryScore(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Foreign Government Surveillance Exposure Score</span>
              <span className="font-mono text-indigo-400">{governmentAccessRisk.toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={governmentAccessRisk}
              onChange={(e) => setGovernmentAccessRisk(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Data Subject Judicial Redress Score</span>
              <span className="font-mono text-indigo-400">{legalRemediesScore.toFixed(0)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={legalRemediesScore}
              onChange={(e) => setLegalRemediesScore(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
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
              'Update TIA'
            ) : (
              'Submit TIA'
            )}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
