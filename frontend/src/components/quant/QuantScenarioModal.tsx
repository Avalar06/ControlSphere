import React, { useState, useEffect } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { quantRiskService } from '../../lib/quantRiskService';
import type {
  QuantitativeRiskScenario,
  QuantitativeRiskScenarioCreate,
  QuantitativeRiskScenarioUpdate,
  ThreatActorCategory,
} from '../../types';
import { AlertTriangle, Info, ShieldAlert, Sparkles } from 'lucide-react';

interface QuantScenarioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  scenario?: QuantitativeRiskScenario | null; // If provided, edit mode
}

const THREAT_CATEGORIES: { label: string; value: ThreatActorCategory }[] = [
  { label: 'Cybercriminal (Financial Motivation)', value: 'CYBERCRIMINAL' },
  { label: 'Nation-State / Advanced Persistent Threat', value: 'NATION_STATE' },
  { label: 'Malicious Insider', value: 'INSIDER' },
  { label: 'Hacktivist / Ideological', value: 'HACKTIVIST' },
  { label: 'Accidental / System Error', value: 'ACCIDENTAL' },
];

export const QuantScenarioModal: React.FC<QuantScenarioModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  scenario,
}) => {
  const isEdit = !!scenario;

  const [scenarioCode, setScenarioCode] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [threatCategory, setThreatCategory] = useState<ThreatActorCategory>('CYBERCRIMINAL');

  const [riskId, setRiskId] = useState<string>('');
  const [controlId, setControlId] = useState<string>('');
  const [vendorId, setVendorId] = useState<string>('');

  // Three-Point PERT & Threat Parameters
  const [tefMin, setTefMin] = useState<number>(0.5);
  const [tefMode, setTefMode] = useState<number>(1.0);
  const [tefMax, setTefMax] = useState<number>(3.0);
  const [tcap, setTcap] = useState<number>(0.75);

  const [plMin, setPlMin] = useState<number>(10000);
  const [plMode, setPlMode] = useState<number>(50000);
  const [plMax, setPlMax] = useState<number>(200000);

  const [slMin, setSlMin] = useState<number>(5000);
  const [slMode, setSlMode] = useState<number>(20000);
  const [slMax, setSlMax] = useState<number>(100000);
  const [slop, setSlop] = useState<number>(0.4);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (scenario) {
      setScenarioCode(scenario.scenario_code);
      setTitle(scenario.title);
      setDescription(scenario.description);
      setThreatCategory(scenario.threat_actor_category);
      setRiskId(scenario.risk_id ? String(scenario.risk_id) : '');
      setControlId(scenario.organization_control_id ? String(scenario.organization_control_id) : '');
      setVendorId(scenario.vendor_id ? String(scenario.vendor_id) : '');

      setTefMin(scenario.tef_min);
      setTefMode(scenario.tef_mode);
      setTefMax(scenario.tef_max);
      setTcap(scenario.tcap);

      setPlMin(scenario.pl_min);
      setPlMode(scenario.pl_mode);
      setPlMax(scenario.pl_max);

      setSlMin(scenario.sl_min);
      setSlMode(scenario.sl_mode);
      setSlMax(scenario.sl_max);
      setSlop(scenario.slop);
    } else {
      setScenarioCode('');
      setTitle('');
      setDescription('');
      setThreatCategory('CYBERCRIMINAL');
      setRiskId('');
      setControlId('');
      setVendorId('');

      setTefMin(0.5);
      setTefMode(1.0);
      setTefMax(3.0);
      setTcap(0.75);

      setPlMin(10000);
      setPlMode(50000);
      setPlMax(200000);

      setSlMin(5000);
      setSlMode(20000);
      setSlMax(100000);
      setSlop(0.4);
    }
    setErrorMsg(null);
  }, [scenario, isOpen]);

  // Client-Side Range Validation for UX
  const validateInputs = (): string | null => {
    if (!title.trim() || title.length < 3) {
      return 'Scenario title must be at least 3 characters.';
    }
    if (!description.trim() || description.length < 5) {
      return 'Description must be at least 5 characters.';
    }
    if (!isEdit && (!scenarioCode.trim() || scenarioCode.length < 3)) {
      return 'Scenario code is required (min 3 chars).';
    }

    // PERT ordering check: min <= mode <= max
    if (tefMin < 0 || tefMin > tefMode || tefMode > tefMax) {
      return `Invalid Threat Event Frequency: Must satisfy Min (${tefMin}) <= Mode (${tefMode}) <= Max (${tefMax}) and >= 0.`;
    }
    if (plMin < 0 || plMin > plMode || plMode > plMax) {
      return `Invalid Primary Loss: Must satisfy Min ($${plMin.toLocaleString()}) <= Mode ($${plMode.toLocaleString()}) <= Max ($${plMax.toLocaleString()}) and >= 0.`;
    }
    if (slMin < 0 || slMin > slMode || slMode > slMax) {
      return `Invalid Secondary Loss: Must satisfy Min ($${slMin.toLocaleString()}) <= Mode ($${slMode.toLocaleString()}) <= Max ($${slMax.toLocaleString()}) and >= 0.`;
    }
    if (tcap < 0 || tcap > 1.0) {
      return 'Threat Capability Factor (TCAP) must be between 0.0 and 1.0.';
    }
    if (slop < 0 || slop > 1.0) {
      return 'Secondary Loss Event Probability (SLoP) must be between 0.0 and 1.0.';
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationErr = validateInputs();
    if (validationErr) {
      setErrorMsg(validationErr);
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      if (isEdit && scenario) {
        const updatePayload: QuantitativeRiskScenarioUpdate = {
          title: title.trim(),
          description: description.trim(),
          threat_actor_category: threatCategory,
          risk_id: riskId ? parseInt(riskId, 10) : undefined,
          organization_control_id: controlId ? parseInt(controlId, 10) : undefined,
          vendor_id: vendorId ? parseInt(vendorId, 10) : undefined,
          tef_min: tefMin,
          tef_mode: tefMode,
          tef_max: tefMax,
          tcap: tcap,
          pl_min: plMin,
          pl_mode: plMode,
          pl_max: plMax,
          sl_min: slMin,
          sl_mode: slMode,
          sl_max: slMax,
          slop: slop,
        };
        await quantRiskService.updateScenario(scenario.id, updatePayload);
      } else {
        const createPayload: QuantitativeRiskScenarioCreate = {
          scenario_code: scenarioCode.trim().toUpperCase(),
          title: title.trim(),
          description: description.trim(),
          threat_actor_category: threatCategory,
          risk_id: riskId ? parseInt(riskId, 10) : undefined,
          organization_control_id: controlId ? parseInt(controlId, 10) : undefined,
          vendor_id: vendorId ? parseInt(vendorId, 10) : undefined,
          tef_min: tefMin,
          tef_mode: tefMode,
          tef_max: tefMax,
          tcap: tcap,
          pl_min: plMin,
          pl_mode: plMode,
          pl_max: plMax,
          sl_min: slMin,
          sl_mode: slMode,
          sl_max: slMax,
          slop: slop,
        };
        await quantRiskService.createScenario(createPayload);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setErrorMsg(typeof detail === 'string' ? detail : 'Failed to save quantitative scenario.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Scenario: ${scenario?.scenario_code}` : 'New Quantitative Cyber Risk Scenario'}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Notice on Server Authority */}
        <div className="flex items-start gap-3 p-3 bg-indigo-950/40 border border-indigo-800/60 rounded-lg text-xs text-indigo-200">
          <Info className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-indigo-100">Deterministic Server Authority:</span> Enter your 3-point range estimates (Min, Mode, Max) and threat capability assumptions below.
            Control Strength (CS), Vulnerability (VULN), Loss Event Frequency (LEF), Single Loss Expectancy (SLE), and Annualized Loss Expectancy (ALE) will be derived server-side.
          </div>
        </div>

        {errorMsg && (
          <div className="flex items-center gap-2 p-3 bg-rose-950/50 border border-rose-800 rounded-lg text-xs text-rose-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Section 1: Scenario Metadata */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {!isEdit && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Scenario Code *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. QRS-RANSOM-01"
                value={scenarioCode}
                onChange={(e) => setScenarioCode(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>
          )}

          <div className={isEdit ? 'md:col-span-2' : ''}>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Scenario Title *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Enterprise Cloud Ransomware Data Exfiltration"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Threat Actor Category *
            </label>
            <select
              value={threatCategory}
              onChange={(e) => setThreatCategory(e.target.value as ThreatActorCategory)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              {THREAT_CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Problem Description & Scope *
            </label>
            <textarea
              required
              rows={3}
              placeholder="Describe threat mechanism, impacted assets, and operational risk narrative..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Section 2: Upstream GRC Linkages */}
        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg space-y-3">
          <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-indigo-400" />
            Upstream GRC Entity Linkages (Optional)
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Phase 2 Control ID</label>
              <input
                type="number"
                placeholder="e.g. 1"
                value={controlId}
                onChange={(e) => setControlId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">Ingests Phase 7 CCM score</span>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Phase 5 Risk ID</label>
              <input
                type="number"
                placeholder="e.g. 1"
                value={riskId}
                onChange={(e) => setRiskId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">Qualitative register link</span>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Phase 9 Vendor ID</label>
              <input
                type="number"
                placeholder="e.g. 1"
                value={vendorId}
                onChange={(e) => setVendorId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">TPRM tier association</span>
            </div>
          </div>
        </div>

        {/* Section 3: Threat Event Frequency (TEF) & Capability */}
        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              1. Threat Event Frequency (TEF) — Beta-PERT Distribution (events/year)
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Expected TEF: {((tefMin + 4 * tefMode + tefMax) / 6).toFixed(2)}/yr
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Min (Optimistic)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={tefMin}
                onChange={(e) => setTefMin(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Mode (Most Likely)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={tefMode}
                onChange={(e) => setTefMode(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Max (Pessimistic)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={tefMax}
                onChange={(e) => setTefMax(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Threat Capability (TCAP: 0.0 - 1.0)</label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1.0"
                value={tcap}
                onChange={(e) => setTcap(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
              />
            </div>
          </div>
        </div>

        {/* Section 4: Primary Loss (PL) & Secondary Loss (SL) in USD */}
        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg space-y-4">
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                2. Primary Loss (PL) — Direct Outage & Response Costs (USD)
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Mean Primary: ${((plMin + 4 * plMode + plMax) / 6).toLocaleString('en-US', { maximumFractionDigits: 2 })}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Min Loss ($)</label>
                <input
                  type="number"
                  min="0"
                  value={plMin}
                  onChange={(e) => setPlMin(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Mode Loss ($)</label>
                <input
                  type="number"
                  min="0"
                  value={plMode}
                  onChange={(e) => setPlMode(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Max Loss ($)</label>
                <input
                  type="number"
                  min="0"
                  value={plMax}
                  onChange={(e) => setPlMax(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                3. Secondary Loss (SL) & Event Probability (SLoP) (USD)
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Expected Secondary: ${(((slMin + 4 * slMode + slMax) / 6) * slop).toLocaleString('en-US', { maximumFractionDigits: 2 })}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Min Loss ($)</label>
                <input
                  type="number"
                  min="0"
                  value={slMin}
                  onChange={(e) => setSlMin(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Mode Loss ($)</label>
                <input
                  type="number"
                  min="0"
                  value={slMode}
                  onChange={(e) => setSlMode(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Max Loss ($)</label>
                <input
                  type="number"
                  min="0"
                  value={slMax}
                  onChange={(e) => setSlMax(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Secondary Prob (SLoP: 0.0 - 1.0)</label>
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1.0"
                  value={slop}
                  onChange={(e) => setSlop(parseFloat(e.target.value) || 0)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            <Sparkles className="h-4 w-4 mr-1.5" />
            {isSubmitting ? 'Calculating & Saving...' : isEdit ? 'Update Scenario' : 'Create & Quantify Scenario'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};