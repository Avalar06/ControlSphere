import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { quantRiskService } from '../../lib/quantRiskService';
import type { QuantitativeSimulationRun } from '../../types';
import { AlertTriangle, CheckCircle2, Cpu, Play, RotateCw } from 'lucide-react';

interface SimulationRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  scenarioId: number;
  scenarioCode: string;
}

const TRIAL_PRESETS = [1000, 5000, 10000, 25000, 50000];

export const SimulationRunModal: React.FC<SimulationRunModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  scenarioId,
  scenarioCode,
}) => {
  const [trialCount, setTrialCount] = useState<number>(10000);
  const [simulationSeed, setSimulationSeed] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<QuantitativeSimulationRun | null>(null);

  const handleRun = async () => {
    if (trialCount < 100 || trialCount > 50000) {
      setErrorMsg('Trial count must be between 100 and 50,000.');
      return;
    }

    setIsRunning(true);
    setErrorMsg(null);
    try {
      const payload = {
        trial_count: trialCount,
        simulation_seed: simulationSeed ? parseInt(simulationSeed, 10) : undefined,
      };
      const runResult = await quantRiskService.executeSimulation(scenarioId, payload);
      setResult(runResult);
      onSuccess();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMsg(typeof detail === 'string' ? detail : 'Simulation run failed.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setErrorMsg(null);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Monte Carlo Simulation Engine: ${scenarioCode}`}
    >
      <div className="space-y-6">
        {!result ? (
          <>
            <div className="flex items-start gap-3 p-3.5 bg-indigo-950/40 border border-indigo-800/60 rounded-lg text-xs text-indigo-200">
              <Cpu className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-indigo-100">Empirical Monte Carlo Loss Modeling:</span> Executes stochastic PERT-distributed trials combining threat frequency events and financial loss distributions. Calculates empirical annual loss percentiles (P10 to P99) and updates the scenario's authoritative 95% VaR and 99% VaR.
              </div>
            </div>

            {errorMsg && (
              <div className="flex items-center gap-2 p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-xs text-rose-300">
                <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Trial Count Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Simulation Trial Count (100 to 50,000)
              </label>
              <div className="flex gap-2 mb-3">
                {TRIAL_PRESETS.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setTrialCount(preset)}
                    className={`px-3 py-1.5 rounded text-xs font-mono font-medium transition-all ${
                      trialCount === preset
                        ? 'bg-indigo-600 text-white shadow-xs border border-indigo-500'
                        : 'bg-slate-900 text-slate-300 border border-slate-700 hover:bg-slate-800'
                    }`}
                  >
                    {preset.toLocaleString()} trials
                  </button>
                ))}
              </div>
              <input
                type="number"
                min={100}
                max={50000}
                value={trialCount}
                onChange={(e) => setTrialCount(parseInt(e.target.value, 10) || 10000)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Optional Simulation Seed */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Deterministic Simulation Seed (Optional for Audit Reproducibility)
              </label>
              <input
                type="number"
                placeholder="Leave blank for cryptographic random seed"
                value={simulationSeed}
                onChange={(e) => setSimulationSeed(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Specifying a fixed integer seed allows auditors to recreate identical Monte Carlo trial runs.
              </span>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
              <Button type="button" variant="outline" onClick={onClose} disabled={isRunning}>
                Cancel
              </Button>
              <Button type="button" variant="primary" onClick={handleRun} disabled={isRunning}>
                <Play className="h-4 w-4 mr-1.5" />
                {isRunning ? 'Running Monte Carlo Engine...' : `Execute ${trialCount.toLocaleString()} Trials`}
              </Button>
            </div>
          </>
        ) : (
          /* Simulation Results View */
          <div className="space-y-5">
            <div className="flex items-center gap-2 p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-lg text-xs text-emerald-200">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>
                Monte Carlo Simulation Run #<strong>{result.id}</strong> completed successfully ({result.trial_count.toLocaleString()} trials, Seed: {result.simulation_seed}).
              </span>
            </div>

            {/* Summary Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block mb-1">
                  Mean Annual Loss (Mean)
                </span>
                <span className="text-lg font-bold text-slate-100 font-mono">
                  ${result.mean_loss.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg">
                <span className="text-[11px] text-slate-400 uppercase tracking-wider block mb-1">
                  Std Deviation (StdDev)
                </span>
                <span className="text-lg font-bold text-slate-100 font-mono">
                  ${result.std_dev_loss.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="p-3.5 bg-slate-950 border border-indigo-900/60 bg-indigo-950/20 rounded-lg">
                <span className="text-[11px] text-indigo-300 uppercase tracking-wider block mb-1">
                  Empirical 95% VaR (Tail)
                </span>
                <span className="text-lg font-bold text-indigo-400 font-mono">
                  ${result.percentile_95.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            {/* Empirical Percentile Distribution Table */}
            <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-lg space-y-3">
              <div className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Empirical Loss Percentile Curve
              </div>
              <div className="grid grid-cols-5 gap-2 text-center">
                <div className="p-2.5 bg-slate-900 border border-slate-800 rounded">
                  <span className="text-[10px] text-slate-400 block font-mono">P10 (Low)</span>
                  <span className="text-xs font-bold text-slate-200 font-mono block mt-1">
                    ${result.percentile_10.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="p-2.5 bg-slate-900 border border-slate-800 rounded">
                  <span className="text-[10px] text-slate-400 block font-mono">P50 (Median)</span>
                  <span className="text-xs font-bold text-slate-200 font-mono block mt-1">
                    ${result.percentile_50.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="p-2.5 bg-slate-900 border border-slate-800 rounded">
                  <span className="text-[10px] text-slate-400 block font-mono">P90</span>
                  <span className="text-xs font-bold text-amber-400 font-mono block mt-1">
                    ${result.percentile_90.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="p-2.5 bg-indigo-950/50 border border-indigo-800 rounded">
                  <span className="text-[10px] text-indigo-300 block font-mono">P95 (95% VaR)</span>
                  <span className="text-xs font-bold text-indigo-300 font-mono block mt-1">
                    ${result.percentile_95.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="p-2.5 bg-rose-950/50 border border-rose-800 rounded">
                  <span className="text-[10px] text-rose-300 block font-mono">P99 (99% VaR)</span>
                  <span className="text-xs font-bold text-rose-400 font-mono block mt-1">
                    ${result.percentile_99.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </span>
                </div>
              </div>
            </div>


            <div className="flex justify-between items-center pt-4 border-t border-slate-800">
              <span className="text-xs text-slate-500 font-mono">
                Algorithm: {result.algorithm_version}
              </span>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={handleReset}>
                  <RotateCw className="h-4 w-4 mr-1" />
                  New Run
                </Button>
                <Button type="button" variant="primary" onClick={onClose}>
                  Done
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};