import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import type { AIModelCardCreate } from '../../types';
import { AlertTriangle, BookOpen, ShieldCheck } from 'lucide-react';

interface AIModelCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  systemId: number;
  systemCode: string;
  onSubmit: (data: AIModelCardCreate) => Promise<void>;
  isSubmitting?: boolean;
}

export const AIModelCardModal: React.FC<AIModelCardModalProps> = ({
  isOpen,
  onClose,
  systemId: _systemId,
  systemCode,
  onSubmit,
  isSubmitting = false,
}) => {
  const [version, setVersion] = useState('');
  const [intendedUse, setIntendedUse] = useState('');
  const [outOfScopeUses, setOutOfScopeUses] = useState('');
  const [biasMitigationNotes, setBiasMitigationNotes] = useState('');
  const [trainingDataProvenance, setTrainingDataProvenance] = useState('');
  const [syntheticDataPercentage, setSyntheticDataPercentage] = useState<number>(0.0);
  const [hallucinationRatePercent, setHallucinationRatePercent] = useState<number>(0.0);
  const [promptInjectionResistanceScore, setPromptInjectionResistanceScore] = useState<number>(100.0);
  const [toxicityFilterEfficiencyScore, setToxicityFilterEfficiencyScore] = useState<number>(100.0);
  const [benchmarkEvalDataset, setBenchmarkEvalDataset] = useState('');
  const [benchmarkScore, setBenchmarkScore] = useState<string>('');

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setVersion('1.0.0');
      setIntendedUse('');
      setOutOfScopeUses('');
      setBiasMitigationNotes('');
      setTrainingDataProvenance('');
      setSyntheticDataPercentage(0.0);
      setHallucinationRatePercent(2.5);
      setPromptInjectionResistanceScore(98.0);
      setToxicityFilterEfficiencyScore(99.0);
      setBenchmarkEvalDataset('MMLU / HaluEval Benchmark Suite');
      setBenchmarkScore('88.5');
      setError(null);
    }
  }, [isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!version.trim()) {
      setError('Version identifier is required (e.g. 1.0.0).');
      return;
    }
    if (!intendedUse.trim() || intendedUse.trim().length < 3) {
      setError('Intended use description must be at least 3 characters.');
      return;
    }

    try {
      const payload: AIModelCardCreate = {
        version: version.trim(),
        intended_use: intendedUse.trim(),
        out_of_scope_uses: outOfScopeUses.trim() || null,
        bias_mitigation_notes: biasMitigationNotes.trim() || null,
        training_data_provenance: trainingDataProvenance.trim() || null,
        synthetic_data_percentage: Number(syntheticDataPercentage),
        hallucination_rate_percent: Number(hallucinationRatePercent),
        prompt_injection_resistance_score: Number(promptInjectionResistanceScore),
        toxicity_filter_efficiency_score: Number(toxicityFilterEfficiencyScore),
        benchmark_eval_dataset: benchmarkEvalDataset.trim() || null,
        benchmark_score: benchmarkScore ? parseFloat(benchmarkScore) : null,
      };
      await onSubmit(payload);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          'Failed to publish model card. Please verify parameters.'
      );
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Publish Model Card: ${systemCode}`}
    >
      <form onSubmit={handleSubmit} className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
        {error && (
          <div className="p-3 bg-rose-950/80 border border-rose-800 rounded-md flex items-start gap-2.5 text-xs text-rose-200">
            <AlertTriangle size={16} className="text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="p-3 bg-indigo-950/40 border border-indigo-800/60 rounded-md flex items-start gap-2.5 text-xs text-indigo-200">
          <BookOpen size={16} className="text-indigo-400 shrink-0 mt-0.5" />
          <span>
            Publishing a new Model Card recalculates the server-authoritative Algorithmic Risk Index (ARI) and EU AI Act conformity assessment scores based on safety benchmark telemetry.
          </span>
        </div>

        {/* Version & Intended Use */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Card Version <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="e.g. 1.0.0"
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Benchmark Dataset
            </label>
            <input
              type="text"
              value={benchmarkEvalDataset}
              onChange={(e) => setBenchmarkEvalDataset(e.target.value)}
              placeholder="e.g. MMLU, GSM8K, HELM, HaluEval"
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Intended Use Cases <span className="text-rose-400">*</span>
          </label>
          <textarea
            rows={2}
            required
            value={intendedUse}
            onChange={(e) => setIntendedUse(e.target.value)}
            placeholder="Operational scope, authorized tasks, domain boundaries..."
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Out-of-Scope &amp; Prohibited Uses
          </label>
          <textarea
            rows={2}
            value={outOfScopeUses}
            onChange={(e) => setOutOfScopeUses(e.target.value)}
            placeholder="Explicitly prohibited use cases, edge scenarios, unsafe operating conditions..."
            className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
          />
        </div>

        {/* Provenance & Bias Mitigation */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Training Data Provenance
            </label>
            <textarea
              rows={2}
              value={trainingDataProvenance}
              onChange={(e) => setTrainingDataProvenance(e.target.value)}
              placeholder="Data sources, curation pipeline, licensing, anonymization..."
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Bias &amp; Fairness Mitigations
            </label>
            <textarea
              rows={2}
              value={biasMitigationNotes}
              onChange={(e) => setBiasMitigationNotes(e.target.value)}
              placeholder="Demographic parity checks, red-teaming mitigations, alignment tuning..."
              className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Safety & Accuracy Telemetry Section */}
        <div className="pt-2 border-t border-slate-800">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-emerald-400" />
            Safety, Robustness &amp; Accuracy Telemetry (0.00 – 100.00%)
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Hallucination Rate (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                required
                value={hallucinationRatePercent}
                onChange={(e) => setHallucinationRatePercent(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Injection Resistance (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                required
                value={promptInjectionResistanceScore}
                onChange={(e) =>
                  setPromptInjectionResistanceScore(parseFloat(e.target.value) || 0)
                }
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Toxicity Filter (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                required
                value={toxicityFilterEfficiencyScore}
                onChange={(e) =>
                  setToxicityFilterEfficiencyScore(parseFloat(e.target.value) || 0)
                }
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Synthetic Data (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                required
                value={syntheticDataPercentage}
                onChange={(e) => setSyntheticDataPercentage(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-[11px] font-medium text-slate-400 mb-1">
                Overall Benchmark Score (0–100)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                value={benchmarkScore}
                onChange={(e) => setBenchmarkScore(e.target.value)}
                placeholder="e.g. 88.50"
                className="w-full bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-indigo-500 font-mono"
              />
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={isSubmitting}>
            Publish Model Card
          </Button>
        </div>
      </form>
    </Modal>
  );
};
