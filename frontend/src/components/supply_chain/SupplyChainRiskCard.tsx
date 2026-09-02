import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardHeader } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { supplyChainService } from '../../lib/supplyChainService';
import type {
  ComponentCalculatePreviewResponse,
  LicenseRiskCategory,
  ProductCalculatePreviewResponse,
  SupplyChainRiskBand,
} from '../../types';
import { Calculator, RefreshCw, Cpu, Sparkles } from 'lucide-react';

export const SupplyChainRiskCard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'component' | 'product'>('component');

  // Component Preview Inputs
  const [cvssScoresInput, setCvssScoresInput] = useState('9.8, 7.5');
  const [epssInput, setEpssInput] = useState('0.85, 0.40');
  const [isExploitable, setIsExploitable] = useState(true);
  const [isCisaKev, setIsCisaKev] = useState(true);
  const [licenseRisk, setLicenseRisk] = useState<LicenseRiskCategory>('PERMISSIVE');
  const [depth, setDepth] = useState<number>(2);
  const [isExempted, setIsExempted] = useState(false);
  const [componentResult, setComponentResult] = useState<ComponentCalculatePreviewResponse | null>(null);

  // Product Preview Inputs
  const [criScoresInput, setCriScoresInput] = useState('85.5, 45.0, 30.0, 15.0');
  const [productResult, setProductResult] = useState<ProductCalculatePreviewResponse | null>(null);

  const componentMutation = useMutation({
    mutationFn: async () => {
      const cvss = cvssScoresInput
        .split(',')
        .map((s) => parseFloat(s.trim()))
        .filter((n) => !isNaN(n));
      const epss = epssInput
        .split(',')
        .map((s) => parseFloat(s.trim()))
        .filter((n) => !isNaN(n));

      return supplyChainService.calculateComponentPreview({
        cvss_scores: cvss,
        epss_scores: epss,
        exploitability_flags: [isExploitable],
        is_cisa_kev: isCisaKev,
        license_risk: licenseRisk,
        dependency_depth: depth,
        is_exempted: isExempted,
      });
    },
    onSuccess: (data) => {
      setComponentResult(data);
    },
  });

  const productMutation = useMutation({
    mutationFn: async () => {
      const cris = criScoresInput
        .split(',')
        .map((s) => parseFloat(s.trim()))
        .filter((n) => !isNaN(n));

      return supplyChainService.calculateProductPreview({
        component_risk_indices: cris,
      });
    },
    onSuccess: (data) => {
      setProductResult(data);
    },
  });

  const getRiskBandBadge = (band: SupplyChainRiskBand) => {
    switch (band) {
      case 'CRITICAL':
        return <Badge variant="danger">CRITICAL</Badge>;
      case 'HIGH':
        return <Badge variant="warning">HIGH</Badge>;
      case 'MODERATE':
        return <Badge variant="purple">MODERATE</Badge>;
      case 'LOW':
      default:
        return <Badge variant="success">LOW</Badge>;
    }
  };

  return (
    <Card className="border-l-4 border-l-indigo-500">
      <CardHeader
        title="Server-Authoritative Supply Chain Risk Engine"
        subtitle="Live calculation preview using deterministic formulas (Zero Client Authority)."
      />

      <div className="space-y-4">
        {/* Toggle Mode */}
        <div className="flex border-b border-slate-800">
          <button
            onClick={() => setActiveTab('component')}
            className={`px-4 py-2 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'component'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu size={14} />
            <span>Component Risk Index (CRI) Preview</span>
          </button>
          <button
            onClick={() => setActiveTab('product')}
            className={`px-4 py-2 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition-colors ${
              activeTab === 'product'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calculator size={14} />
            <span>Product Exposure Index (SCEI) Preview</span>
          </button>
        </div>

        {activeTab === 'component' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  CVSS Base Scores (comma-separated, 0.0 – 10.0)
                </label>
                <input
                  type="text"
                  value={cvssScoresInput}
                  onChange={(e) => setCvssScoresInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 font-mono focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  EPSS Probability Scores (0.0 – 1.0)
                </label>
                <input
                  type="text"
                  value={epssInput}
                  onChange={(e) => setEpssInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 font-mono focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                    License Risk
                  </label>
                  <select
                    value={licenseRisk}
                    onChange={(e) => setLicenseRisk(e.target.value as LicenseRiskCategory)}
                    className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
                  >
                    <option value="PERMISSIVE">Permissive (+0)</option>
                    <option value="WEAK_COPYLEFT">Weak Copyleft (+10)</option>
                    <option value="STRONG_COPYLEFT">Strong Copyleft (+25)</option>
                    <option value="PROHIBITED">Prohibited (+30)</option>
                    <option value="UNCLASSIFIED">Unclassified (+15)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">
                    Tree Depth (1=Direct)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={depth}
                    onChange={(e) => setDepth(Number(e.target.value))}
                    className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 focus:outline-hidden focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex items-center gap-4 pt-1">
                <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isExploitable}
                    onChange={(e) => setIsExploitable(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-indigo-600"
                  />
                  <span>Exploitable</span>
                </label>

                <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isCisaKev}
                    onChange={(e) => setIsCisaKev(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-indigo-600"
                  />
                  <span>CISA KEV</span>
                </label>

                <label className="flex items-center gap-1.5 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isExempted}
                    onChange={(e) => setIsExempted(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-indigo-600"
                  />
                  <span>Exempted (50% Relief)</span>
                </label>
              </div>

              <Button
                size="sm"
                variant="outline"
                onClick={() => componentMutation.mutate()}
                disabled={componentMutation.isPending}
                className="w-full flex items-center justify-center gap-1.5"
              >
                {componentMutation.isPending ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <Sparkles size={14} className="text-indigo-400" />
                )}
                <span>Compute Component CRI</span>
              </Button>
            </div>

            {/* Results Display */}
            <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-lg flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Calculated Component Index
                  </span>
                  {componentResult && getRiskBandBadge(componentResult.risk_band)}
                </div>

                {componentResult ? (
                  <div className="space-y-2 text-xs">
                    <div className="text-3xl font-bold font-mono text-indigo-400">
                      {componentResult.component_risk_index.toFixed(2)}{' '}
                      <span className="text-xs font-normal text-slate-400">/ 100.0</span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                      <div>
                        Inherent Vuln: <span className="font-mono text-slate-200">{componentResult.inherent_vulnerability_score.toFixed(2)}</span>
                      </div>
                      <div>
                        Depth Mult: <span className="font-mono text-slate-200">{componentResult.depth_multiplier.toFixed(2)}x</span>
                      </div>
                      <div>
                        License Penalty: <span className="font-mono text-slate-200">+{componentResult.license_penalty.toFixed(1)}</span>
                      </div>
                      <div>
                        Exemption Applied: <span className="font-mono text-slate-200">{isExempted ? 'Yes (0.50x)' : 'No (1.00x)'}</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic py-6 text-center">
                    Enter parameters and click "Compute Component CRI" to preview server-authoritative results.
                  </p>
                )}
              </div>

              <div className="text-[10px] text-slate-500 pt-3 border-t border-slate-800">
                Formula: <code className="text-indigo-300">CRI = min(100, (V_score + L_risk) * depth_mult * exemption_factor)</code>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  Cataloged Component Risk Indices (comma-separated, 0.0 – 100.0)
                </label>
                <textarea
                  rows={3}
                  value={criScoresInput}
                  onChange={(e) => setCriScoresInput(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-100 font-mono focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <Button
                size="sm"
                variant="outline"
                onClick={() => productMutation.mutate()}
                disabled={productMutation.isPending}
                className="w-full flex items-center justify-center gap-1.5"
              >
                {productMutation.isPending ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <Sparkles size={14} className="text-indigo-400" />
                )}
                <span>Compute Product SCEI</span>
              </Button>
            </div>

            {/* Results Display */}
            <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-lg flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Calculated Product SCEI
                  </span>
                  {productResult && getRiskBandBadge(productResult.risk_band)}
                </div>

                {productResult ? (
                  <div className="space-y-2 text-xs">
                    <div className="text-3xl font-bold font-mono text-indigo-400">
                      {productResult.supply_chain_exposure_index.toFixed(2)}{' '}
                      <span className="text-xs font-normal text-slate-400">/ 100.0</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic py-6 text-center">
                    Enter CRIs and click "Compute Product SCEI" to preview composite risk index.
                  </p>
                )}
              </div>

              <div className="text-[10px] text-slate-500 pt-3 border-t border-slate-800">
                Formula: <code className="text-indigo-300">SCEI = min(100, max(CRI) * 0.60 + mean(CRI) * 0.40)</code>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
