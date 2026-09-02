import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { supplyChainService } from '../../lib/supplyChainService';
import type { SupplyChainExemptionCreate } from '../../types';
import { AlertCircle, RefreshCw, ShieldCheck } from 'lucide-react';

interface SupplyChainExemptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  productId?: number | null;
  componentId?: number | null;
  onSuccess: () => void;
}

export const SupplyChainExemptionModal: React.FC<SupplyChainExemptionModalProps> = ({
  isOpen,
  onClose,
  productId,
  componentId,
  onSuccess,
}) => {
  const [exemptionCode, setExemptionCode] = useState('');
  const [reason, setReason] = useState('');
  const [compensatingControls, setCompensatingControls] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [targetProductId, setTargetProductId] = useState<string>('');
  const [targetComponentId, setTargetComponentId] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const codeSuffix = Math.random().toString(36).substring(2, 7).toUpperCase();
      setExemptionCode(`EX-SC-${codeSuffix}`);
      setReason('');
      setCompensatingControls('');
      const defaultDate = new Date();
      defaultDate.setDate(defaultDate.getDate() + 90);
      setExpiresAt(defaultDate.toISOString().split('T')[0]);
      setTargetProductId(productId ? String(productId) : '');
      setTargetComponentId(componentId ? String(componentId) : '');
      setErrorMsg(null);
    }
  }, [isOpen, productId, componentId]);

  const mutation = useMutation({
    mutationFn: async () => {
      const data: SupplyChainExemptionCreate = {
        exemption_code: exemptionCode.trim().toUpperCase(),
        reason: reason.trim(),
        compensating_controls: compensatingControls.trim(),
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
        software_product_id: targetProductId ? Number(targetProductId) : null,
        component_id: targetComponentId ? Number(targetComponentId) : null,
      };

      return supplyChainService.createExemption(data);
    },
    onSuccess: () => {
      onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to submit exemption request.';
      setErrorMsg(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!exemptionCode.trim()) {
      setErrorMsg('Exemption Code is required.');
      return;
    }
    if (reason.trim().length < 5) {
      setErrorMsg('Audit Justification Reason must be at least 5 characters.');
      return;
    }
    if (compensatingControls.trim().length < 5) {
      setErrorMsg('Compensating Controls explanation must be at least 5 characters.');
      return;
    }
    if (!targetProductId && !targetComponentId) {
      setErrorMsg('Either a Software Product ID or Component ID must be designated for exemption.');
      return;
    }
    setErrorMsg(null);
    mutation.mutate();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Request Supply Chain Risk Exemption (Four-Eyes SoD)"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMsg && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg flex items-start gap-2.5 text-xs text-rose-400">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-300 flex items-start gap-2">
          <ShieldCheck size={16} className="shrink-0 mt-0.5 text-indigo-400" />
          <span>
            Exemption requests require independent review and approval by an authorized Manager or Admin under Segregation of Duties (SoD) policy. Requesters cannot approve their own exemptions.
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Exemption Code <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. EX-SC-2026-001"
              value={exemptionCode}
              onChange={(e) => setExemptionCode(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Expiration Date
            </label>
            <input
              type="date"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Product ID
            </label>
            <input
              type="number"
              placeholder="e.g. 1"
              value={targetProductId}
              onChange={(e) => setTargetProductId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Component ID
            </label>
            <input
              type="number"
              placeholder="e.g. 5"
              value={targetComponentId}
              onChange={(e) => setTargetComponentId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Business &amp; Technical Justification Reason <span className="text-rose-400">*</span>
          </label>
          <textarea
            rows={2}
            placeholder="Explain why this vulnerable or copyleft dependency cannot immediately be replaced..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Compensating Controls &amp; Mitigations <span className="text-rose-400">*</span>
          </label>
          <textarea
            rows={2}
            placeholder="Document network perimeter segmentation, WAF rules, container isolation, or sandboxing..."
            value={compensatingControls}
            onChange={(e) => setCompensatingControls(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={mutation.isPending} className="flex items-center gap-1.5">
            {mutation.isPending && <RefreshCw size={14} className="animate-spin" />}
            <span>Submit Exemption</span>
          </Button>
        </div>
      </form>
    </Modal>
  );
};
