import React, { useEffect, useState } from 'react';
import {
  Building,
  Users,
  ScrollText,
  Lock,
  CheckCircle2,
  Server,
  Database,
  ArrowRight,
  Sparkles,
  Layers,
  KeyRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Card, CardHeader } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import type { AuditLog } from '../types';

export const DashboardPage: React.FC = () => {
  const { user, organization, hasPermission } = useAuth();
  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  useEffect(() => {
    if (hasPermission('audit_log:read')) {
      setLogsLoading(true);
      api
        .get<AuditLog[]>('/api/v1/audit-logs?limit=6')
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
                Phase 1: Foundation Active
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </div>
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">
              Welcome back, {user?.full_name}
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Operating within the <span className="text-slate-200 font-semibold">{organization?.name}</span> security tenant.
              ControlSphere enforces server-side tenant isolation, RBAC role boundaries, and deterministic audit trails.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            {hasPermission('user:create') && (
              <Link to="/users">
                <Button size="sm" variant="primary">
                  <Users size={14} />
                  Manage Users
                </Button>
              </Link>
            )}
            {hasPermission('audit_log:read') && (
              <Link to="/audit-logs">
                <Button size="sm" variant="secondary">
                  <ScrollText size={14} />
                  Audit Logs
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Core Foundation Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-l-2 border-l-indigo-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Tenant Context</span>
            <Building size={16} className="text-indigo-400" />
          </div>
          <div className="text-base font-bold text-slate-100 truncate">
            {organization?.name}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">
            Slug: {organization?.slug} (ID: #{organization?.id})
          </div>
        </Card>

        <Card className="border-l-2 border-l-purple-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Active Security Role</span>
            <Lock size={16} className="text-purple-400" />
          </div>
          <div className="text-base font-bold text-slate-100">
            {user?.role}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {user?.permissions?.length || 0} permissions authorized
          </div>
        </Card>

        <Card className="border-l-2 border-l-emerald-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Database Layer</span>
            <Database size={16} className="text-emerald-400" />
          </div>
          <div className="text-base font-bold text-slate-100">
            PostgreSQL 15
          </div>
          <div className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1 font-mono">
            <CheckCircle2 size={12} /> Strict Isolation Enforced
          </div>
        </Card>

        <Card className="border-l-2 border-l-sky-500">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium">Backend Service</span>
            <Server size={16} className="text-sky-400" />
          </div>
          <div className="text-base font-bold text-slate-100">
            FastAPI Layered
          </div>
          <div className="text-[11px] text-sky-400 mt-1 flex items-center gap-1 font-mono">
            <CheckCircle2 size={12} /> REST + OpenAPI v1
          </div>
        </Card>
      </div>

      {/* Main Content: Security Architecture & Recent Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Architecture Status Card */}
        <Card className="lg:col-span-2">
          <CardHeader
            title="ControlSphere Foundation Architecture"
            subtitle="Phase 1 Verification and GRC Engine Foundations"
          />

          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5">
                <div className="flex items-center gap-2">
                  <Layers size={15} className="text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200">Layered Clean Architecture</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Route handlers delegate to authentication, permission checks, service layers, and data access repositories. Business logic is strictly backend-governed.
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5">
                <div className="flex items-center gap-2">
                  <KeyRound size={15} className="text-emerald-400" />
                  <span className="text-xs font-semibold text-slate-200">Multi-Tenancy &amp; Isolation</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Every authenticated identity is cryptographically bound to an Organization ID in the JWT. Database queries explicitly filter by tenant context to block IDOR.
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5">
                <div className="flex items-center gap-2">
                  <Lock size={15} className="text-purple-400" />
                  <span className="text-xs font-semibold text-slate-200">Server-Enforced RBAC</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Roles (ADMIN, GRC_ANALYST, AUDITOR, VIEWER) are validated server-side on every request. Frontend route guards complement server-side security.
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800/80 space-y-1.5">
                <div className="flex items-center gap-2">
                  <ScrollText size={15} className="text-amber-400" />
                  <span className="text-xs font-semibold text-slate-200">Immutable Audit Logging</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Authentication events, user modifications, and unauthorized access attempts generate persistent, immutable audit records in the database.
                </p>
              </div>
            </div>

            {/* Workflow Pipeline preview */}
            <div className="p-4 rounded-lg bg-indigo-950/20 border border-indigo-800/40 mt-4">
              <div className="text-xs font-semibold text-indigo-300 mb-2 flex items-center gap-1.5">
                <Sparkles size={14} />
                <span>Authoritative GRC Traceability Pipeline (Phases 2–8 Roadmap)</span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-300">
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Framework</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Control</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Evidence</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Assessment</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Finding</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Risk</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Remediation</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-slate-900 rounded border border-slate-800">Verification</span>
                <ArrowRight size={12} className="text-indigo-400" />
                <span className="px-2 py-1 bg-indigo-600/30 text-indigo-300 rounded border border-indigo-500/50">Audit Readiness</span>
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