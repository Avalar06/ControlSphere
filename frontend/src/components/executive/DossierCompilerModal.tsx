import React, { useState } from 'react';
import { X, AlertCircle, Layers } from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import type { DossierType } from '../../types';

interface DossierCompilerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const DossierCompilerModal: React.FC<DossierCompilerModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [dossierCode, setDossierCode] = useState(
    `DOS-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`
  );
  const [title, setTitle] = useState('');
  const [dossierType, setDossierType] = useState<DossierType>('BOARD_SUMMARY');
  const [executiveSummary, setExecutiveSummary] = useState('');
  const [regulatoryCommentary, setRegulatoryCommentary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await executiveService.createDossier({
        dossier_code: dossierCode.trim(),
        title: title.trim(),
        dossier_type: dossierType,
        executive_summary: executiveSummary.trim() || undefined,
        regulatory_commentary: regulatoryCommentary.trim() || undefined,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create regulatory dossier');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 p-6 shadow-2xl border border-slate-200 dark:border-slate-800 my-8">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-500" />
            <h3 className="font-bold text-slate-900 dark:text-white">Create Regulatory Dossier</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800/80 flex items-center gap-2 text-xs text-rose-600 dark:text-rose-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Dossier Code *
              </label>
              <input
                type="text"
                required
                value={dossierCode}
                onChange={(e) => setDossierCode(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Dossier Type *
              </label>
              <select
                value={dossierType}
                onChange={(e) => setDossierType(e.target.value as DossierType)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="BOARD_SUMMARY">Board Summary</option>
                <option value="REGULATORY_SUBMISSION">Regulatory Submission</option>
                <option value="ANNUAL_COMPLIANCE">Annual Compliance</option>
                <option value="FORENSIC_AUDIT">Forensic Audit</option>
                <option value="CYBER_INSURANCE">Cyber Insurance</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Dossier Title *
            </label>
            <input
              type="text"
              required
              placeholder="e.g., Annual SOC2 & NIST CSF Compliance Dossier"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Executive Statement / Summary
            </label>
            <textarea
              rows={3}
              value={executiveSummary}
              onChange={(e) => setExecutiveSummary(e.target.value)}
              placeholder="Summary of organizational governance posture and control effectiveness..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Regulatory Commentary (Optional)
            </label>
            <textarea
              rows={2}
              value={regulatoryCommentary}
              onChange={(e) => setRegulatoryCommentary(e.target.value)}
              placeholder="Notes on regulatory exceptions, harmonized controls, or jurisdiction compliance..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-sm disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Draft Dossier'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
