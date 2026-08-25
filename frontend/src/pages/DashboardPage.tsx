import React, { useEffect, useState } from 'react';
import {
  Building,
  Lock,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  BookOpen,
  FileCheck2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import type { AuditLog, FrameworkProgress, Policy } from '../types';

export const DashboardPage: React.FC = () => {
  const { user, organization, hasPermission } = useAuth();
  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([]);
  const [progress, setProgress] = useState<FrameworkProgress | null>(null);
  const [policiesCount, setPoliciesCount] = useState<number>(0);
  const [publishedPoliciesCount, setPublishedPoliciesCount] = useState<number>(0);
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

    // 2. Fetch policies count
    api
      .get<Policy[]>('/api/v1/policies')
      .then((res) => {
        setPoliciesCount(res.data.length);
        const published = res.data.filter((p) => p.status === 'PUBLISHED').length;
        setPublishedPoliciesCount(published);
      })
      .catch((err) => console.error('Failed to load policies in dashboard', err));

    // 3. Fetch audit logs if permitted
    if (hasPermission('audit_log:read')) {
      setLogsLoading(true);
      api
        .get<AuditLog[]>('/api/v1/audit-logs?limit=5')
        .then((res) => setRecentLogs(res.data))
        .catch((err) => console.error('Failed to load audit logs in dashboard', err))
        .finally(() => setLogsLoading(false));
    }
  }, [user]);

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-slate-800 rounded-xl p-6 relative overflow-hidden shadow-sm">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                Phase 2: Frameworks &amp; Controls Active
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </div>
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">
              Welcome back, {user?.full_name}
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Operating within <span className="text-slate-200 font-semibold">{organization?.name}</span>.
              Deterministic framework progress metrics, security controls matrix, and policy governance are active.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto flex-wrap">
            <Link to="/frameworks">
              <Button size="sm" variant="primary">
                <ShieldCheck size={14} />
                Frameworks
              </Button>
            </Link>
            <Link to="/controls">
              <Button size="sm" variant="secondary">
                <FileCheck2 size={14} />
                Controls
              </Button>
            </Link>
            <Link to="/policies">
              <Button size="sm" variant="secondary">
                <BookOpen size={14} />
                Policies
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Live Posture Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Compliance Posture Score */}
        <Card className="border-l-2 border-l-indigo-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">CSF 2.0 Compliance Score</span>
            <ShieldCheck size={16} className="text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {progress ? `${progress.compliance_score_pct}%` : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            {progress ? `${progress.implemented_count} of ${progress.total_controls} controls implemented` : 'Loading posture...'}
          </div>
        </Card>

        {/* Controls Implementation Breakdown */}
        <Card className="border-l-2 border-l-emerald-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Implemented Controls</span>
            <CheckCircle2 size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {progress ? progress.implemented_count : '...'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {progress ? `${progress.partially_implemented_count} partial · ${progress.in_progress_count} in progress` : 'Calculating...'}
          </div>
        </Card>

        {/* Policy Governance */}
        <Card className="border-l-2 border-l-purple-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Security Policies</span>
            <BookOpen size={16} className="text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-slate-100 font-mono">
            {policiesCount}
          </div>
          <div className="text-[11px] text-purple-300 mt-1 font-mono">
            {publishedPoliciesCount} Published &amp; Enforced
          </div>
        </Card>

        {/* Tenant Scope */}
        <Card className="border-l-2 border-l-sky-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Tenant Isolation</span>
            <Building size={16} className="text-sky-400" />
          </div>
          <div className="text-base font-bold text-slate-100 truncate">
            {organization?.name}
          </div>
          <div className="text-[11px] text-sky-400 mt-1 flex items-center gap-1 font-mono">
            <CheckCircle2 size={12} /> ID #{organization?.id} Isolated
          </div>
        </Card>
      </div>

      {/* Main Content: NIST CSF Functions & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                    className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-2"
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
            <div className="p-4 rounded-lg bg-indigo-950/20 border border-indigo-800/40 mt-4">
              <div className="text-xs font-semibold text-indigo-300 mb-2 flex items-center gap-1.5">
                <Sparkles size={14} />
                <span>Authoritative GRC Traceability Pipeline</span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-300">
                <span className="px-2 py-1 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Framework (CSF 2.0)</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Control Matrix</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Policies</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Evidence (P3)</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Assessment (P4)</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Risk (P5)</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Remediation (P6)</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Audit Readiness (P7)</span>
              </div>
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
            <div className="py-8 text-center text-xs text-slate-500">
              <Lock size={20} className="mx-auto mb-2 opacity-50" />
              Your role ({user?.role}) does not have permission to view audit logs.
            </div>
          ) : logsLoading ? (
            <div className="py-6 text-center text-xs text-slate-400">Loading audit trail...</div>
          ) : recentLogs.length === 0 ? (
            <div className="py-6 text-center text-xs text-slate-500">No recent audit logs recorded.</div>
          ) : (
            <div className="space-y-2.5">
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
                    {new Date(log.timestamp).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};