import React, { useEffect, useState } from 'react';
import { ScrollText, Filter, RefreshCw, Eye, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import type { AuditLog } from '../types';
import { Card, CardHeader } from '../components/ui/Card';
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from '../components/ui/Table';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const AuditLogsPage: React.FC = () => {
  const { organization } = useAuth();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [actorFilter, setActorFilter] = useState('');

  // Details Modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (actionFilter) params.append('action', actionFilter);
      if (statusFilter) params.append('status', statusFilter);
      if (actorFilter) params.append('actor_email', actorFilter);
      params.append('limit', '100');

      const { data } = await api.get<AuditLog[]>(`/api/v1/audit-logs?${params.toString()}`);
      setLogs(data);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load audit logs.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return <Badge variant="success">SUCCESS</Badge>;
      case 'UNAUTHORIZED':
        return <Badge variant="warning">UNAUTHORIZED</Badge>;
      case 'FAILURE':
        return <Badge variant="danger">FAILURE</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ScrollText className="text-amber-400" size={20} />
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Security Audit Log Explorer</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Immutable system and security event audit trail for <span className="text-slate-200 font-medium">{organization?.name}</span>.
          </p>
        </div>

        <Button size="sm" variant="secondary" onClick={fetchLogs} isLoading={isLoading}>
          <RefreshCw size={13} />
          Refresh Log Trail
        </Button>
      </div>

      {error && (
        <div className="p-3 rounded bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle size={14} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Bar */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
            <Filter size={14} className="text-indigo-400" />
            <span>Filter Trail:</span>
          </div>

          <input
            type="text"
            placeholder="Search Actor Email..."
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
          />

          <input
            type="text"
            placeholder="Filter Action (e.g. auth.login)..."
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="SUCCESS">SUCCESS</option>
            <option value="UNAUTHORIZED">UNAUTHORIZED</option>
            <option value="FAILURE">FAILURE</option>
          </select>

          <Button size="sm" variant="primary" onClick={fetchLogs}>
            Apply Filters
          </Button>
        </div>
      </Card>

      {/* Audit Logs Table */}
      <Card>
        <CardHeader
          title={`Recorded Audit Events (${logs.length})`}
          subtitle="Audit logs cannot be modified or deleted through application APIs."
        />

        {isLoading ? (
          <LoadingSpinner text="Querying immutable audit logs..." />
        ) : logs.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No audit records matching criteria.
          </div>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Timestamp (UTC)</TableHeaderCell>
                <TableHeaderCell>Action</TableHeaderCell>
                <TableHeaderCell>Actor</TableHeaderCell>
                <TableHeaderCell>Resource</TableHeaderCell>
                <TableHeaderCell>Status</TableHeaderCell>
                <TableHeaderCell>Details</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs text-slate-400">
                    {new Date(log.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs text-indigo-400 font-medium">
                      {log.action}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-slate-300">
                    {log.actor_email}
                  </TableCell>
                  <TableCell>
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-slate-300">
                      {log.resource_type}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(log.status)}</TableCell>
                  <TableCell>
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="text-indigo-400 hover:text-indigo-300 text-xs flex items-center gap-1 font-medium cursor-pointer"
                    >
                      <Eye size={13} />
                      <span>Inspect</span>
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Inspect Modal */}
      <Modal
        isOpen={!!selectedLog}
        onClose={() => setSelectedLog(null)}
        title={`Audit Record #${selectedLog?.id} Details`}
      >
        {selectedLog && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 rounded bg-slate-950 border border-slate-800 font-mono">
              <div>
                <span className="text-slate-500 block text-[10px]">TIMESTAMP</span>
                <span className="text-slate-200">{new Date(selectedLog.timestamp).toISOString()}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">TENANT ORG</span>
                <span className="text-slate-200">ID #{selectedLog.organization_id}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">ACTOR</span>
                <span className="text-slate-200">{selectedLog.actor_email}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px]">STATUS</span>
                <span className="text-slate-200">{selectedLog.status}</span>
              </div>
            </div>

            <div>
              <span className="text-[11px] font-semibold uppercase text-slate-400 block mb-1">
                Metadata &amp; Parameters
              </span>
              <pre className="p-3 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-indigo-300 overflow-x-auto">
                {JSON.stringify(selectedLog.details || {}, null, 2)}
              </pre>
            </div>

            <div className="pt-2 flex justify-end">
              <Button size="sm" variant="secondary" onClick={() => setSelectedLog(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};