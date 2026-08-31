import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type {
  ExposureSeverity,
  VulnerabilityExposure,
  VulnerabilityExposureCreate,
  VulnerabilityExposureUpdate,
} from '../../types';
import { AlertTriangle, ShieldAlert } from 'lucide-react';

interface ExposureModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: VulnerabilityExposureCreate | VulnerabilityExposureUpdate) => Promise<void>;
  initialData?: VulnerabilityExposure | null;
  isSubmitting?: boolean;
}

export const ExposureModal: React.FC<ExposureModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isSubmitting = false,
}) => {
  const isEdit = !!initialData;

  const [cveId, setCveId] = useState('');
  const [cweId, setCweId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [cvssScore, setCvssScore] = useState<number>(0.0);
  const [cvssVector, setCvssVector] = useState('');
  const [epssScore, setEpssScore] = useState<number>(0.0);
  const [cisaKev, setCisaKev] = useState<boolean>(false);
  const [severity, setSeverity] = useState<ExposureSeverity>('MEDIUM');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setCveId(initialData.cve_id || '');
      setCweId(initialData.cwe_id || '');
      setTitle(initialData.title || '');
      setDescription(initialData.description || '');
      setCvssScore(initialData.cvss_score || 0.0);
      setCvssVector(initialData.cvss_vector || '');
      setEpssScore(initialData.epss_score || 0.0);
      setCisaKev(initialData.cisa_kev || false);
      setSeverity(initialData.severity || 'MEDIUM');
    } else {
      setCveId('');
      setCweId('');
      setTitle('');
      setDescription('');
      setCvssScore(7.5);
      setCvssVector('');
      setEpssScore(0.25);
      setCisaKev(false);
      setSeverity('HIGH');
    }
    setError(null);
  }, [initialData, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isEdit && !cveId.trim()) {
      setError('CVE identifier is required (e.g. CVE-2026-1001).');
      return;
    }
    if (!title.trim() || title.trim().length < 2) {
      setError('Title must be at least 2 characters.');
      return;
    }
    if (cvssScore < 0.0 || cvssScore > 10.0) {
      setError('CVSS score must be between 0.0 and 10.0.');
      return;
    }
    if (epssScore < 0.0 || epssScore > 1.0) {
      setError('EPSS probability must be between 0.0 and 1.0.');
      return;
    }

    try {
      if (isEdit) {
        const updatePayload: VulnerabilityExposureUpdate = {
          title: title.trim(),
          description: description.trim() || null,
          cwe_id: cweId.trim() || null,
          cvss_score: cvssScore,
          cvss_vector: cvssVector.trim() || null,
          epss_score: epssScore,
          cisa_kev: cisaKev,
          severity,
        };
        await onSubmit(updatePayload);
      } else {
        const createPayload: VulnerabilityExposureCreate = {
          cve_id: cveId.trim().toUpperCase(),
          cwe_id: cweId.trim() || null,
          title: title.trim(),
          description: description.trim() || null,
          cvss_score: cvssScore,
          cvss_vector: cvssVector.trim() || null,
          epss_score: epssScore,
          cisa_kev: cisaKev,
          severity,
        };
        await onSubmit(createPayload);
      }
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to save vulnerability exposure.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Exposure: ${initialData?.cve_id}` : 'Ingest Vulnerability Exposure'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              CVE Identifier <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              disabled={isEdit}
              value={cveId}
              onChange={(e) => setCveId(e.target.value)}
              placeholder="e.g. CVE-2026-1001"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono disabled:opacity-60"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              CWE Identifier
            </label>
            <input
              type="text"
              value={cweId}
              onChange={(e) => setCweId(e.target.value)}
              placeholder="e.g. CWE-89"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Vulnerability Title <span className="text-rose-400">*</span>
          </label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Remote Code Execution in API Gateway"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">
            Description & Impact Notes
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Detailed description of vulnerability mechanics, attack preconditions, and impacted versions..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              CVSS Base (0.0 - 10.0)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="10"
              required
              value={cvssScore}
              onChange={(e) => setCvssScore(parseFloat(e.target.value) || 0.0)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              EPSS (0.0 - 1.0)
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              required
              value={epssScore}
              onChange={(e) => setEpssScore(parseFloat(e.target.value) || 0.0)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Severity
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as ExposureSeverity)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
              <option value="INFORMATIONAL">INFORMATIONAL</option>
            </select>
          </div>
        </div>

        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/80 border border-slate-800">
          <div className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
              <ShieldAlert className="h-4 w-4 text-rose-400" />
              <span>CISA KEV Known Exploited Vulnerability</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Active in-the-wild exploitation adds +25 pts and accelerates SLA to 7 days.
            </p>
          </div>
          <input
            type="checkbox"
            checked={cisaKev}
            onChange={(e) => setCisaKev(e.target.checked)}
            className="h-5 w-5 rounded-md border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900 cursor-pointer"
          />
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button variant="outline" type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : isEdit ? 'Update Exposure' : 'Ingest Exposure'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
