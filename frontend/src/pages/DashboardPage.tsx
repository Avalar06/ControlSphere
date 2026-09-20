import React, { useEffect, useState } from 'react';
import {
  Lock,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  FileCheck2,
  FileCheck,
  ShieldAlert,
  FileWarning,
  TrendingDown,
  CalendarCheck,
  Activity,
  Flame,
  AlertOctagon,
  AlertTriangle,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { evidenceService } from '../lib/evidenceService';
import { findingService } from '../lib/findingService';
import { riskService } from '../lib/riskService';
import { exceptionService } from '../lib/exceptionService';
import { auditService } from '../lib/auditService';
import { monitoringService } from '../lib/monitoringService';
import { harmonizationService } from '../lib/harmonizationService';
import { incidentService } from '../lib/incidentService';
import type {
  AuditLog,
  AuditStats,
  ExceptionStats,
  FindingStats,
  FrameworkProgress,
  HeatmapCell,
  IncidentOverviewResponse,
  MonitoringOverview,
  MultiFrameworkPostureResponse,
  OrganizationEvidenceStats,
  PendingAttestationItem,
  RiskStats,
} from '../types';

export const DashboardPage: React.FC = () => {
  const { user, organization, hasPermission } = useAuth();
  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([]);
  const [progress, setProgress] = useState<FrameworkProgress | null>(null);
  const [evidenceStats, setEvidenceStats] = useState<OrganizationEvidenceStats | null>(null);
  const [findingStats, setFindingStats] = useState<FindingStats | null>(null);
  const [riskStats, setRiskStats] = useState<RiskStats | null>(null);
  const [exceptionStats, setExceptionStats] = useState<ExceptionStats | null>(null);
  const [auditStats, setAuditStats] = useState<AuditStats | null>(null);
  const [monitoringOverview, setMonitoringOverview] = useState<MonitoringOverview | null>(null);
  const [harmonizationPosture, setHarmonizationPosture] = useState<MultiFrameworkPostureResponse | null>(null);
  const [incidentOverview, setIncidentOverview] = useState<IncidentOverviewResponse | null>(null);
  const [heatmapCells, setHeatmapCells] = useState<HeatmapCell[]>([]);
  const [pendingAttestations, setPendingAttestations] = useState<PendingAttestationItem[]>([]);
  const [isAttestModalOpen, setIsAttestModalOpen] = useState(false);
  const [activeAttestation, setActiveAttestation] = useState<PendingAttestationItem | null>(null);
  const [acknowledgementText, setAcknowledgementText] = useState('');
  const [isSubmittingAttest, setIsSubmittingAttest] = useState(false);
  const [attestSuccessReceipt, setAttestSuccessReceipt] = useState<string | null>(null);
  const [attestError, setAttestError] = useState<string | null>(null);

  const [logsLoading, setLogsLoading] = useState(false);

  useEffect(() => {
    // 1. Fetch framework progress for NIST CSF 2.0
    api
      .get<any[]>('/api/v1/frameworks')
      .then((res) => {
        if (res.data && res.data.length > 0) {
          api
            .get<FrameworkProgress>(`/api/v1/frameworks/${res.data[0].id}/progress`)
            .then((pRes) => setProgress(pRes.data))
            .catch((err) => console.error('Failed to load framework progress in dashboard', err));
        }
      })
      .catch((err) => console.error('Failed to load frameworks in dashboard', err));

    // 2. Fetch evidence assurance stats
    evidenceService
      .getEvidenceStats()
      .then((stats) => setEvidenceStats(stats))
      .catch((err) => console.error('Failed to load evidence stats in dashboard', err));

    // 3. Fetch finding stats
    findingService
      .getFindingStats()
      .then((stats) => setFindingStats(stats))
      .catch((err) => console.error('Failed to load finding stats in dashboard', err));

    // 4. Fetch risk stats & heatmap
    riskService
      .getStats()
      .then((stats) => setRiskStats(stats))
      .catch((err) => console.error('Failed to load risk stats in dashboard', err));

    riskService
      .getHeatmap()
      .then((cells) => setHeatmapCells(cells))
      .catch((err) => console.error('Failed to load heatmap in dashboard', err));

    // 5. Fetch exception stats
    exceptionService
      .getStats()
      .then((stats) => setExceptionStats(stats))
      .catch((err) => console.error('Failed to load exception stats in dashboard', err));

    // 6. Fetch audit stats
    auditService
      .getStats()
      .then((stats) => setAuditStats(stats))
      .catch((err) => console.error('Failed to load audit stats in dashboard', err));

    // 7. Fetch continuous monitoring overview
    monitoringService
      .getOverview()
      .then((overview) => setMonitoringOverview(overview))
      .catch((err) => console.error('Failed to load monitoring overview in dashboard', err));

    // 8. Fetch multi-framework harmonization posture
    harmonizationService
      .getPosture()
      .then((posture) => setHarmonizationPosture(posture))
      .catch((err) => console.error('Failed to load harmonization posture in dashboard', err));

    // 9. Fetch incident response overview
    incidentService
      .getOverview()
      .then((ov) => setIncidentOverview(ov))
      .catch((err) => console.error('Failed to load incident overview in dashboard', err));

    // 9. Fetch audit logs if permitted
    if (hasPermission('audit_log:read')) {
      setLogsLoading(true);
      api
        .get<AuditLog[]>('/api/v1/audit-logs?limit=5')
        .then((res) => setRecentLogs(res.data))
        .catch((err) => console.error('Failed to load audit logs in dashboard', err))
        .finally(() => setLogsLoading(false));
    }
    // 10. Fetch pending policy workforce attestations
    api
      .get<PendingAttestationItem[]>('/api/v1/policies/my-pending-attestations')
      .then((res) => setPendingAttestations(res.data))
      .catch((err) => console.error('Failed to load pending attestations in dashboard', err));
  }, [user]);

  const handleAttestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeAttestation) return;
    setIsSubmittingAttest(true);
    setAttestError(null);
    try {
      const { data } = await api.post(`/api/v1/policies/campaigns/${activeAttestation.campaign_id}/attest`, {
        policy_version_hash: activeAttestation.policy_version_hash,
        acknowledgement_text: acknowledgementText,
      });
      setAttestSuccessReceipt(data.attestation_receipt_hash);
      setPendingAttestations((prev) => prev.filter((p) => p.campaign_id !== activeAttestation.campaign_id));
    } catch (err: any) {
      console.error(err);
      setAttestError(err.response?.data?.detail || 'Failed to submit policy attestation.');
    } finally {
      setIsSubmittingAttest(false);
    }
  };

  const getHeatmapColor = (band: string, count: number) => {
    if (count === 0) {
      return 'bg-slate-950/60 border-slate-800/80 text-slate-600';
    }
    switch (band) {
      case 'CRITICAL':
        return 'bg-red-950/90 border-red-700 text-red-300 font-bold';
      case 'HIGH':
        return 'bg-amber-950/90 border-amber-700 text-amber-300 font-bold';
      case 'MODERATE':
        return 'bg-yellow-950/90 border-yellow-700 text-yellow-300 font-bold';
      default:
        return 'bg-emerald-950/90 border-emerald-700 text-emerald-300 font-bold';
    }
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 rounded-xl p-6 relative overflow-hidden shadow-sm">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                Enterprise GRC &amp; Executive Risk Governance Active
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </div>
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">
              Welcome back, {user?.full_name}
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Operating within <span className="text-slate-200 font-semibold">{organization?.name}</span>.
              Deterministic framework progress metrics, security controls matrix, policy governance, evidence assurance, risk appetite evaluations, and active exceptions are online.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto flex-wrap">
            <Link to="/risks">
              <Button size="sm" variant="primary">
                <ShieldAlert size={14} />
                Risk Register
              </Button>
            </Link>
            <Link to="/exceptions">
              <Button size="sm" variant="secondary">
                <FileWarning size={14} />
                Exceptions
              </Button>
            </Link>
            <Link to="/assessments">
              <Button size="sm" variant="secondary">
                <FileCheck2 size={14} />
                Assessments
              </Button>
            </Link>
            <Link to="/audits">
              <Button size="sm" variant="secondary">
                <CalendarCheck size={14} />
                Audits
              </Button>
            </Link>
            <Link to="/monitoring">
              <Button size="sm" variant="primary">
                <Activity size={14} />
                Monitoring ({monitoringOverview ? `${monitoringOverview.average_health_score}%` : '...'})
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Pending Policy Workforce Attestations Action Banner */}
      {pendingAttestations.length > 0 && (
        <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-950/60 to-purple-950/40 border border-indigo-700/60 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-md">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-indigo-900/60 border border-indigo-700/60 text-indigo-300">
              <FileCheck2 size={22} />
            </div>
            <div>
              <span className="text-xs font-bold text-slate-100 flex items-center gap-2">
                Mandatory Workforce Attestation Required ({pendingAttestations.length} Pending)
                <Badge variant="warning" className="text-[10px] py-0">Action Required</Badge>
              </span>
              <p className="text-[11px] text-slate-300 mt-0.5">
                Next required review: <span className="text-indigo-300 font-semibold">{pendingAttestations[0].policy_title}</span> (Due {new Date(pendingAttestations[0].due_date).toLocaleDateString()})
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="primary"
            onClick={() => {
              setActiveAttestation(pendingAttestations[0]);
              setAcknowledgementText(
                `I hereby confirm and attest that I have read, understood, and agree to abide by the provisions set forth in the ${pendingAttestations[0].policy_title}.`
              );
              setAttestSuccessReceipt(null);
              setAttestError(null);
              setIsAttestModalOpen(true);
            }}
          >
            Review & Attest Now
          </Button>
        </div>
      )}

      {/* Live Executive Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Compliance Posture Score */}
        <Card className="border-l-2 border-l-indigo-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">CSF 2.0 Posture</span>
            <ShieldCheck size={16} className="text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {progress ? `${progress.compliance_score_pct}%` : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            {progress ? `${progress.implemented_count} / ${progress.total_controls} controls` : 'Loading...'}
          </div>
        </Card>

        {/* Executive Risk Posture */}
        <Card className="border-l-2 border-l-red-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Risks Above Appetite</span>
            <ShieldAlert size={16} className="text-red-400" />
          </div>
          <div className="text-2xl font-bold text-red-400 font-mono">
            {riskStats ? riskStats.above_appetite_count : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {riskStats ? `${riskStats.near_limit_count} near limit · ${riskStats.total_risks} total` : 'Calculating...'}
          </div>
        </Card>

        {/* Risk Reduction Gauge */}
        <Card className="border-l-2 border-l-emerald-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Risk Reduction</span>
            <TrendingDown size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {riskStats ? `${riskStats.inherent_vs_residual_reduction}%` : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Inherent vs residual delta
          </div>
        </Card>

        {/* Security Exceptions */}
        <Card className="border-l-2 border-l-amber-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Active Exceptions</span>
            <FileWarning size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 font-mono">
            {exceptionStats ? exceptionStats.active_count : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {exceptionStats ? `${exceptionStats.expiring_soon_count} expiring soon (≤14d)` : 'Calculating...'}
          </div>
        </Card>

        {/* Open Findings */}
        <Card className="border-l-2 border-l-rose-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Open Findings</span>
            <span className="text-rose-400 text-xs font-bold font-mono">
              {findingStats ? `${findingStats.critical_count + findingStats.high_count} Crit/High` : ''}
            </span>
          </div>
          <div className="text-2xl font-bold text-rose-400 font-mono">
            {findingStats ? findingStats.open_count + findingStats.in_remediation_count + findingStats.pending_validation_count : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {findingStats ? `${findingStats.overdue_count} overdue · ${findingStats.pending_validation_count} pending val` : 'Calculating...'}
          </div>
        </Card>

        {/* Evidence Assurance */}
        <Card className="border-l-2 border-l-blue-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Evidence Coverage</span>
            <FileCheck size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 font-mono">
            {evidenceStats ? `${evidenceStats.overall_coverage_pct}%` : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            {evidenceStats ? `${evidenceStats.accepted_count} accepted` : 'Calculating...'}
          </div>
        </Card>
      </div>

      {/* 5x5 Inherent Risk Heatmap & Functions Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Heatmap Widget */}
        <Card className="lg:col-span-1">
          <CardHeader
            title="5x5 Inherent Risk Heatmap"
            subtitle="Likelihood (Y) vs Impact (X) distribution"
            action={
              <Link to="/risks" className="text-xs text-indigo-400 hover:text-indigo-300">
                Manage Risks
              </Link>
            }
          />
          <div className="space-y-2">
            <div className="grid grid-cols-5 gap-1.5">
              {heatmapCells.map((cell, idx) => (
                <div
                  key={idx}
                  title={`Likelihood: ${cell.likelihood}, Impact: ${cell.impact}, Score: ${cell.score} (${cell.band}), Risks: ${cell.count}`}
                  className={`h-10 rounded border flex flex-col items-center justify-center text-[10px] transition-transform hover:scale-105 cursor-pointer ${getHeatmapColor(
                    cell.band,
                    cell.count
                  )}`}
                >
                  <span className="text-xs font-bold">{cell.count > 0 ? cell.count : '·'}</span>
                  <span className="text-[8px] opacity-70">{cell.score}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono pt-2 border-t border-slate-800">
              <span>← Low Impact</span>
              <span>High Impact →</span>
            </div>
          </div>
        </Card>

        {/* NIST CSF 2.0 Functions Posture Breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="NIST Cybersecurity Framework 2.0 Posture"
            subtitle="Deterministic posture calculated from organization subcategory assessments"
            action={
              <Link to="/frameworks" className="text-xs text-indigo-400 hover:text-indigo-300">
                View Framework
              </Link>
            }
          />

          <div className="space-y-4">
            {progress && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(progress.by_function).map(([fnKey, fnStats]) => (
                  <div
                    key={fnKey}
                    className="p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300">
                          {fnKey}
                        </span>
                        <span className="text-xs font-semibold text-slate-200">
                          {fnStats.name}
                        </span>
                      </div>
                      <span className="text-xs font-mono font-bold text-slate-100">
                        {fnStats.score_pct}%
                      </span>
                    </div>

                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full"
                        style={{ width: `${fnStats.score_pct}%` }}
                      />
                    </div>

                    <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                      <span>{fnStats.implemented}/{fnStats.total} Implemented</span>
                      <span>{fnStats.in_progress + fnStats.partially_implemented} In Progress</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Traceability Roadmap */}
            <div className="p-3 rounded-lg bg-indigo-950/20 border border-indigo-800/40 mt-3">
              <div className="text-xs font-semibold text-indigo-300 mb-1.5 flex items-center gap-1.5">
                <Sparkles size={14} />
                <span>Enterprise GRC Traceability Chain</span>
              </div>
              <div className="flex flex-wrap items-center gap-1 text-[10px] font-mono text-slate-300">
                <span className="px-1.5 py-0.5 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Framework</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Controls</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Policies</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Evidence</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Assessment</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Findings</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Risk &amp; Exceptions</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-purple-600/30 text-purple-300 rounded border border-purple-500/50 font-bold">Audit Assurance ({auditStats ? auditStats.total_audits : 0})</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-blue-600/30 text-blue-300 rounded border border-blue-500/50 font-bold">Continuous Monitoring (Phase 7)</span>
                <ArrowRight size={10} className="text-indigo-400" />
                <span className="px-1.5 py-0.5 bg-emerald-600/30 text-emerald-300 rounded border border-emerald-500/50 font-bold">Harmonization &amp; Posture (Phase 8)</span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Multi-Framework Compliance Posture (Phase 8 Widget) */}
      <Card>
        <CardHeader
          title="Multi-Framework Compliance Posture"
          subtitle="Harmonized crosswalk coverage and continuous compliance health"
          action={
            <Link to="/harmonization" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              Harmonization Workspace <ArrowRight size={12} />
            </Link>
          }
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Frameworks Monitored</span>
            <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">
              {harmonizationPosture?.frameworks.length || 0}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Active compliance catalogs</div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Average Coverage</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1 font-mono">
              {harmonizationPosture && harmonizationPosture.frameworks.length > 0
                ? `${(harmonizationPosture.frameworks.reduce((acc, f) => acc + f.coverage_percentage, 0) / harmonizationPosture.frameworks.length).toFixed(1)}%`
                : '...'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Direct + Crosswalk</div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Average Compliance Health</span>
            <div className="text-2xl font-bold text-blue-400 mt-1 font-mono">
              {harmonizationPosture && harmonizationPosture.frameworks.length > 0
                ? `${(harmonizationPosture.frameworks.reduce((acc, f) => acc + f.compliance_health_score, 0) / harmonizationPosture.frameworks.length).toFixed(1)}%`
                : '...'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">CCM health weighted</div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Common Controls</span>
            <div className="text-2xl font-bold text-indigo-400 mt-1 font-mono">
              {harmonizationPosture ? harmonizationPosture.total_common_controls : '...'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              Avg Health: {harmonizationPosture ? `${harmonizationPosture.average_common_control_health}%` : '...'}
            </div>
          </div>
        </div>
      </Card>

      {/* Security Incident & Breach Posture (Phase 10) */}
      <Card>
        <CardHeader
          title="Security Incident Posture & Breach Governance"
          subtitle="Reactive security telemetry, statutory regulatory countdowns, and forensic lifecycle governance"
          action={
            <Link to="/incidents" className="text-xs text-red-400 hover:text-red-300 font-semibold inline-flex items-center gap-1">
              Incident Command <ArrowRight size={13} />
            </Link>
          }
        />

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Open Incidents</span>
              <Flame size={14} className="text-red-400" />
            </div>
            <div className="text-2xl font-bold text-slate-100 mt-1 font-mono">
              {incidentOverview ? incidentOverview.open_incidents : '...'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">
              {incidentOverview ? `${incidentOverview.total_incidents} lifetime declared` : '...'}
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-red-400 uppercase tracking-wider">Crit / High Severity</span>
              <ShieldAlert size={14} className="text-red-400" />
            </div>
            <div className="text-2xl font-bold text-red-400 mt-1 font-mono">
              {incidentOverview ? incidentOverview.critical_or_high_incidents : '...'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">High priority response</div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">SEC Material (8-K)</span>
              <AlertOctagon size={14} className="text-purple-400" />
            </div>
            <div className="text-2xl font-bold text-purple-400 mt-1 font-mono">
              {incidentOverview ? incidentOverview.material_incidents : '...'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Item 1.05 disclosures</div>
          </div>

          <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Overdue Disclosures</span>
              <AlertTriangle size={14} className="text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-amber-400 mt-1 font-mono">
              {incidentOverview ? incidentOverview.overdue_disclosures : '...'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Statutory breach clock</div>
          </div>
        </div>
      </Card>

      {/* Live Audit Log Stream */}
      <Card>
        <CardHeader
          title="Recent Audit Events"
          subtitle={hasPermission('audit_log:read') ? 'Live tenant activity log' : 'Restricted to Auditor/Admin'}
          action={
            hasPermission('audit_log:read') && (
              <Link to="/audit-logs" className="text-xs text-indigo-400 hover:text-indigo-300">
                View All
              </Link>
            )
          }
        />

        {!hasPermission('audit_log:read') ? (
          <div className="py-6 text-center text-xs text-slate-500">
            <Lock size={18} className="mx-auto mb-1.5 opacity-50" />
            Your role ({user?.role}) does not have permission to view audit logs.
          </div>
        ) : logsLoading ? (
          <div className="py-4 text-center text-xs text-slate-400">Loading audit trail...</div>
        ) : recentLogs.length === 0 ? (
          <div className="py-4 text-center text-xs text-slate-500">No recent audit logs recorded.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2">
            {recentLogs.map((log) => (
              <div
                key={log.id}
                className="p-2.5 rounded bg-slate-950/60 border border-slate-800/80 text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] text-indigo-400 font-medium">
                    {log.action}
                  </span>
                  <Badge
                    variant={
                      log.status === 'SUCCESS'
                        ? 'success'
                        : log.status === 'UNAUTHORIZED'
                        ? 'warning'
                        : 'danger'
                    }
                    className="text-[9px] px-1 py-0"
                  >
                    {log.status}
                  </Badge>
                </div>
                <div className="text-[11px] text-slate-400 truncate">
                  Actor: <span className="text-slate-300">{log.actor_email}</span>
                </div>
                <div className="text-[10px] text-slate-500 font-mono">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Self-Service Workforce Policy Attestation Modal */}
      <Modal
        isOpen={isAttestModalOpen}
        onClose={() => setIsAttestModalOpen(false)}
        title={`Workforce Attestation: ${activeAttestation?.policy_title || 'Policy Review'}`}
      >
        {activeAttestation && (
          <div className="space-y-4 text-xs">
            {attestSuccessReceipt ? (
              <div className="p-4 bg-emerald-950/60 border border-emerald-800 rounded-lg space-y-3">
                <div className="flex items-center gap-2 text-emerald-300 font-semibold">
                  <FileCheck2 size={18} />
                  <span>Attestation Successfully Recorded!</span>
                </div>
                <p className="text-slate-300 text-[11px]">
                  Your compliance attestation has been cryptographically hashed and entered into the immutable audit ledger.
                </p>
                <div>
                  <span className="text-[10px] font-mono text-slate-400 block mb-0.5">Tamper-Evident Attestation Receipt Hash (SHA-256):</span>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800 font-mono text-[11px] text-emerald-400 break-all select-all">
                    {attestSuccessReceipt}
                  </div>
                </div>
                <div className="pt-2 flex justify-end">
                  <Button size="sm" variant="outline" onClick={() => setIsAttestModalOpen(false)}>
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleAttestSubmit} className="space-y-4">
                {attestError && (
                  <div className="p-3 bg-rose-950/60 border border-rose-800/70 text-rose-300 rounded flex items-center gap-2">
                    <AlertCircle size={14} className="shrink-0" />
                    <span>{attestError}</span>
                  </div>
                )}

                <div className="p-3 bg-slate-950 rounded border border-slate-800 space-y-1">
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Campaign: <strong className="text-slate-200">{activeAttestation.campaign_code}</strong></span>
                    <span>Version: <strong className="text-indigo-400">v{activeAttestation.version_number}</strong></span>
                  </div>
                  <div className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                    <Lock size={10} />
                    <span>Bound Version SHA-256: {activeAttestation.policy_version_hash}</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Policy Content Review</label>
                  <div className="bg-slate-950 p-3.5 rounded border border-slate-800 font-mono text-xs text-slate-300 max-h-56 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                    {activeAttestation.policy_content || 'No content provided.'}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Legal & Compliance Acknowledgement
                  </label>
                  <textarea
                    required
                    rows={3}
                    value={acknowledgementText}
                    onChange={(e) => setAcknowledgementText(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[10px] text-slate-500 block mt-1">
                    Submitting records your user ID, client IP address, and timestamp into a deterministic SHA-256 cryptographic receipt.
                  </span>
                </div>

                <div className="pt-3 flex justify-end gap-2 border-t border-slate-800">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsAttestModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={isSubmittingAttest}
                  >
                    Submit Attestation
                  </Button>
                </div>
              </form>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};