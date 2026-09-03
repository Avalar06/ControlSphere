import React, { useState, useEffect } from 'react';
import {
  Activity,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Camera,
  Layers,
  FileCheck2,
  Scale,
  Wrench,
  Cloud,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { continuousComplianceService } from '../lib/continuousComplianceService';
import type {
  UnifiedAssurancePosture,
  ComplianceDriftRecord,
  ContinuousAssuranceSnapshot,
} from '../types';

export const ContinuousComplianceDashboardPage: React.FC = () => {
  const [posture, setPosture] = useState<UnifiedAssurancePosture | null>(null);
  const [drifts, setDrifts] = useState<ComplianceDriftRecord[]>([]);
  const [snapshots, setSnapshots] = useState<ContinuousAssuranceSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [snapshotCode, setSnapshotCode] = useState('');
  const [isSnapshotModalOpen, setIsSnapshotModalOpen] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [postureRes, driftRes, snapRes] = await Promise.all([
        continuousComplianceService.getPosture(),
        continuousComplianceService.listDrifts(),
        continuousComplianceService.listSnapshots(),
      ]);
      setPosture(postureRes);
      setDrifts(driftRes);
      setSnapshots(snapRes);
    } catch (err) {
      console.error('Failed to load continuous compliance data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleEvaluate = async () => {
    setEvaluating(true);
    try {
      const updatedPosture = await continuousComplianceService.evaluateCompliance();
      setPosture(updatedPosture);
      const updatedDrifts = await continuousComplianceService.listDrifts();
      setDrifts(updatedDrifts);
    } catch (err) {
      console.error('Failed to evaluate continuous compliance', err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleTriggerCAPA = async (driftId: number) => {
    try {
      await continuousComplianceService.triggerRemediation(driftId);
      const updatedDrifts = await continuousComplianceService.listDrifts();
      setDrifts(updatedDrifts);
    } catch (err) {
      console.error('Failed to trigger CAPA remediation for drift', err);
    }
  };

  const handleCaptureSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!snapshotCode.trim()) return;
    try {
      await continuousComplianceService.captureSnapshot({ snapshot_code: snapshotCode.trim() });
      setSnapshotCode('');
      setIsSnapshotModalOpen(false);
      const updatedSnaps = await continuousComplianceService.listSnapshots();
      setSnapshots(updatedSnaps);
    } catch (err) {
      console.error('Failed to capture continuous assurance snapshot', err);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-emerald-500 border-emerald-500/20 bg-emerald-500/10';
    if (score >= 75) return 'text-blue-500 border-blue-500/20 bg-blue-500/10';
    if (score >= 60) return 'text-amber-500 border-amber-500/20 bg-amber-500/10';
    return 'text-rose-500 border-rose-500/20 bg-rose-500/10';
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'MEDIUM':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="h-7 w-7 text-primary-500" />
            Continuous Compliance & Unified Assurance
          </h1>
          <p className="text-sm text-slate-400">
            Real-time cross-module telemetry aggregating controls, evidence pipelines, regulatory mandates, and multi-vector drift.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsSnapshotModalOpen(true)}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 transition"
          >
            <Camera className="h-4 w-4 text-slate-400" />
            Capture Snapshot
          </button>
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50 transition"
          >
            <RefreshCw className={`h-4 w-4 ${evaluating ? 'animate-spin' : ''}`} />
            Evaluate Compliance
          </button>
        </div>
      </div>

      {/* Main Composite Score Hero Card */}
      {posture && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="lg:col-span-1 rounded-xl border border-slate-800 bg-slate-900/50 p-6 flex flex-col items-center justify-center text-center backdrop-blur shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Enterprise Assurance Score</div>
            <div className={`flex h-32 w-32 items-center justify-center rounded-full border-4 text-4xl font-black ${getScoreColor(posture.overall_assurance_score)}`}>
              {posture.overall_assurance_score}%
            </div>
            <div className="mt-4 flex items-center gap-2 text-xs text-slate-400">
              <Clock className="h-3.5 w-3.5" />
              Evaluated {new Date(posture.last_evaluated_at).toLocaleTimeString()}
            </div>
            <div className="mt-2 text-xs font-medium text-slate-500">Engine Version: {posture.calculation_version}</div>
          </div>

          <div className="lg:col-span-3 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Controls Assurance</span>
                <Layers className="h-4 w-4 text-blue-400" />
              </div>
              <div className="mt-2 text-2xl font-bold text-white">{posture.controls_assurance_score}%</div>
              <div className="mt-1 text-xs text-slate-500">Weight: 25% | CCM Health Baseline</div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Evidence Pipeline</span>
                <FileCheck2 className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="mt-2 text-2xl font-bold text-white">{posture.evidence_pipeline_score}%</div>
              <div className="mt-1 text-xs text-slate-500">Weight: 20% | Auto-Collection Freshness</div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Regulatory Compliance</span>
                <Scale className="h-4 w-4 text-amber-400" />
              </div>
              <div className="mt-2 text-2xl font-bold text-white">{posture.regulatory_compliance_score}%</div>
              <div className="mt-1 text-xs text-slate-500">Weight: 15% | Mandates & Changes</div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Remediation SLA</span>
                <Wrench className="h-4 w-4 text-indigo-400" />
              </div>
              <div className="mt-2 text-2xl font-bold text-white">{posture.remediation_sla_score}%</div>
              <div className="mt-1 text-xs text-slate-500">Weight: 15% | Phase 11 CAPA On-Track</div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Cloud & Identity</span>
                <Cloud className="h-4 w-4 text-purple-400" />
              </div>
              <div className="mt-2 text-2xl font-bold text-white">{posture.cloud_identity_posture_score}%</div>
              <div className="mt-1 text-xs text-slate-500">Weight: 15% | CSPM & SoD Violations</div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">Harmonized Frameworks</span>
                <ShieldCheck className="h-4 w-4 text-teal-400" />
              </div>
              <div className="mt-2 text-2xl font-bold text-white">{posture.harmonized_frameworks_score}%</div>
              <div className="mt-1 text-xs text-slate-500">Weight: 10% | Common Control Coverage</div>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Vector Drift Stream */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Active Compliance Drift Stream ({drifts.length})
            </h2>
            <p className="text-xs text-slate-400">Multi-vector detection: CCM health, integration failures, regulatory exposures, and SLA breaches.</p>
          </div>
        </div>

        {drifts.length === 0 ? (
          <div className="rounded-lg border border-slate-800/80 bg-slate-950/40 p-8 text-center">
            <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500 mb-2" />
            <div className="text-sm font-semibold text-white">Zero Compliance Drift Detected</div>
            <div className="text-xs text-slate-400">All continuous monitoring telemetry and pipelines conform to authoritative governance baselines.</div>
          </div>
        ) : (
          <div className="divide-y divide-slate-800 overflow-hidden rounded-lg border border-slate-800 bg-slate-950/50">
            {drifts.map((d) => (
              <div key={d.id} className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between hover:bg-slate-900/40 transition">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${getSeverityBadge(d.severity)}`}>
                      {d.severity}
                    </span>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-mono text-slate-300">
                      {d.drift_vector}
                    </span>
                    <span className="text-xs font-mono text-slate-500">{d.drift_code}</span>
                  </div>
                  <div className="text-sm font-semibold text-white">{d.title}</div>
                  <div className="text-xs text-slate-400">{d.description}</div>
                </div>

                <div className="flex items-center gap-3">
                  {d.remediation_plan_id ? (
                    <span className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-semibold text-indigo-300">
                      <Wrench className="h-3.5 w-3.5" />
                      CAPA Active (#{d.remediation_plan_id})
                    </span>
                  ) : (
                    <button
                      onClick={() => handleTriggerCAPA(d.id)}
                      className="flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-500 transition"
                    >
                      <Wrench className="h-3.5 w-3.5" />
                      Trigger CAPA
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Point-in-Time Cryptographic Snapshots */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
          <Camera className="h-5 w-5 text-blue-400" />
          Cryptographic Continuous Assurance Snapshots ({snapshots.length})
        </h2>

        {snapshots.length === 0 ? (
          <div className="text-xs text-slate-500">No snapshots recorded yet. Capture a snapshot to preserve point-in-time proof.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="pb-3 font-semibold">Snapshot Code</th>
                  <th className="pb-3 font-semibold">Captured At</th>
                  <th className="pb-3 font-semibold">Overall Score</th>
                  <th className="pb-3 font-semibold">Active Drifts</th>
                  <th className="pb-3 font-semibold">SHA-256 Checksum</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {snapshots.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-800/30">
                    <td className="py-3 font-semibold text-white">{s.snapshot_code}</td>
                    <td className="py-3 font-sans text-slate-400">{new Date(s.captured_at).toLocaleString()}</td>
                    <td className="py-3">
                      <span className={`inline-block px-2 py-0.5 rounded font-bold ${getScoreColor(s.overall_assurance_score)}`}>
                        {s.overall_assurance_score}%
                      </span>
                    </td>
                    <td className="py-3 text-slate-400 font-sans">{s.active_drift_count}</td>
                    <td className="py-3 font-mono text-slate-500 text-[11px] truncate max-w-xs">{s.data_hash_sha256}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Snapshot Capture Modal */}
      {isSnapshotModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-2">Capture Assurance Snapshot</h3>
            <p className="text-xs text-slate-400 mb-4">
              Generates an immutable, point-in-time cryptographic summary signed with SHA-256 for audit and board dossier presentation.
            </p>
            <form onSubmit={handleCaptureSnapshot} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase mb-1">Snapshot Code</label>
                <input
                  type="text"
                  required
                  placeholder="SNAP-Q3-ASSURANCE-01"
                  value={snapshotCode}
                  onChange={(e) => setSnapshotCode(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-primary-500 focus:outline-none"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsSnapshotModalOpen(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-primary-600 px-4 py-2 text-xs font-medium text-white hover:bg-primary-500"
                >
                  Capture Now
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
