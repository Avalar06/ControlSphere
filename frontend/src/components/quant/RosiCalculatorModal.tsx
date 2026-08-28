import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { quantRiskService } from '../../lib/quantRiskService';
import { remediationService } from '../../lib/remediationService';
import type { RemediationPlan, RosiAnalysis } from '../../types';
import { AlertTriangle, CheckCircle2, DollarSign, TrendingUp } from 'lucide-react';

interface RosiCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  scenarioId: number;
  scenarioCode: string;
  currentAle: number;
}

export const RosiCalculatorModal: React.FC<RosiCalculatorModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  scenarioId,
  scenarioCode,
  currentAle,
}) => {
  const [plans, setPlans] = useState<RemediationPlan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>('');
  const [remediationCost, setRemediationCost] = useState<number>(25000);
  const [customDelta, setCustomDelta] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<RosiAnalysis | null>(null);

  useEffect(() => {
    if (isOpen) {
      setResult(null);
      setErrorMsg(null);
      // Fetch active remediation plans for linkage
      remediationService
        .listPlans({ limit: 50 })
        .then((data) => {
          setPlans(data);
          if (data.length > 0) {
            setSelectedPlanId(String(data[0].id));
          }
        })
        .catch(() => {
          // Fallback to manual ID entry if plans list fails
        });
    }
  }, [isOpen]);

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanId) {
      setErrorMsg('Please select or specify a Phase 11 Remediation Plan ID.');
      return;
    }
    if (remediationCost <= 0) {
      setErrorMsg('Remediation cost must be strictly greater than $0.00.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const deltaVal = customDelta ? parseFloat(customDelta) : undefined;
      if (deltaVal !== undefined && (deltaVal < 0 || deltaVal > 1.0)) {
        setErrorMsg('Projected Control Strength Delta must be between 0.0 and 1.0.');
        setIsSubmitting(false);
        return;
      }

      const res = await quantRiskService.calculateRosi(scenarioId, {
        remediation_plan_id: parseInt(selectedPlanId, 10),
        remediation_cost: remediationCost,
        projected_control_strength_delta: deltaVal,
      });

      setResult(res);
      onSuccess();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMsg(typeof detail === 'string' ? detail : 'ROSI calculation failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Return on Security Investment (ROSI): ${scenarioCode}`}
    >
      <div className="space-y-6">
        {!result ? (
          <form onSubmit={handleCalculate} className="space-y-5">
            <div className="flex items-start gap-3 p-3.5 bg-indigo-950/40 border border-indigo-800/60 rounded-lg text-xs text-indigo-200">
              <TrendingUp className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-indigo-100">Financial Investment Appraisal:</span> Quantifies the monetary return of executing a Phase 11 Remediation Plan against this scenario.
                Formula: ROSI = ((Risk Reduction - Cost) / Cost) * 100%
              </div>
            </div>

            {errorMsg && (
              <div className="flex items-center gap-2 p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-xs text-rose-300">
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg flex justify-between items-center">
              <div>
                <span className="text-xs text-slate-400 block font-medium">Current Scenario ALE Baseline</span>
                <span className="text-xs text-slate-500 font-mono">Unmitigated annual risk exposure</span>
              </div>
              <span className="text-lg font-bold text-slate-100 font-mono">
                ${currentAle.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Phase 11 Remediation Plan (CAPA) *
              </label>
              {plans.length > 0 ? (
                <select
                  required
                  value={selectedPlanId}
                  onChange={(e) => setSelectedPlanId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select a Phase 11 Remediation Plan...</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      [{p.plan_code}] {p.title} (REI: {p.rei_score ?? 'N/A'}, Status: {p.status})
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="number"
                  required
                  placeholder="Enter Phase 11 Remediation Plan ID"
                  value={selectedPlanId}
                  onChange={(e) => setSelectedPlanId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Total Remediation Investment Cost ($ USD) *
              </label>
              <input
                type="number"
                required
                min="1"
                step="100"
                value={remediationCost}
                onChange={(e) => setRemediationCost(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Includes vendor tooling, engineering hours, and operational migration expenses.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Custom Control Strength Delta (Delta CS: Optional override)
              </label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1.0"
                placeholder="Leave blank to auto-derive from Phase 11 REI score"
                value={customDelta}
                onChange={(e) => setCustomDelta(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                If omitted, the engine calibrates Delta CS = REI / 200.0.
              </span>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                <DollarSign className="h-4 w-4 mr-1.5" />
                {isSubmitting ? 'Calculating Financial Return...' : 'Calculate & Record ROSI'}
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-5">
            <div className="flex items-center gap-2 p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg text-xs text-emerald-200">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>ROSI Analysis recorded successfully under Analysis Record #{result.id}.</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
                <span className="text-xs text-slate-400 uppercase tracking-wider block mb-1">
                  Annual Risk Reduction (Delta ALE)
                </span>
                <span className="text-xl font-bold text-emerald-400 font-mono">
                  +${result.risk_reduction_ale.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / yr
                </span>
                <div className="flex justify-between text-[11px] text-slate-400 mt-2 font-mono">
                  <span>Current: ${result.current_ale.toLocaleString('en-US', { maximumFractionDigits: 0 })}</span>
                  <span>→ Projected: ${result.projected_ale.toLocaleString('en-US', { maximumFractionDigits: 0 })}</span>
                </div>
              </div>

              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
                <span className="text-xs text-slate-400 uppercase tracking-wider block mb-1">
                  Net Economic Benefit
                </span>
                <span
                  className={`text-xl font-bold font-mono ${
                    result.net_economic_benefit >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {result.net_economic_benefit >= 0 ? '+' : ''}$
                  {result.net_economic_benefit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <span className="text-[11px] text-slate-500 block mt-2 font-mono">
                  Cost: ${result.remediation_cost.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                </span>
              </div>
            </div>

            {/* Big ROSI Percentage Callout */}
            <div
              className={`p-5 rounded-lg border text-center ${
                result.rosi_percentage >= 0
                  ? 'bg-emerald-950/30 border-emerald-800/80 text-emerald-200'
                  : 'bg-rose-950/30 border-rose-800/80 text-rose-200'
              }`}
            >
              <span className="text-xs uppercase tracking-widest font-bold block mb-1">
                Return on Security Investment
              </span>
              <span className="text-4xl font-extrabold font-mono tracking-tight block">
                {result.rosi_percentage >= 0 ? '+' : ''}
                {result.rosi_percentage.toFixed(1)}%
              </span>
              <span className="text-xs text-slate-400 block mt-2">
                {result.rosi_percentage >= 0
                  ? 'Positive Economic Justification: Risk reduction exceeds remediation expenditure.'
                  : 'Negative Economic Justification: Remediation cost outweighs immediate annualized risk savings.'}
              </span>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <Button type="button" variant="primary" onClick={onClose}>
                Done
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};