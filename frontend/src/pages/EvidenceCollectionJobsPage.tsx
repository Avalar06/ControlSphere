import React, { useState, useEffect } from 'react';
import {
  FileCheck2,
  Play,
  RefreshCw,
} from 'lucide-react';
import { integrationService } from '../lib/integrationService';
import type {
  EvidenceCollectionJob,
  EvidenceCollectionRun,
} from '../types';

export const EvidenceCollectionJobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<EvidenceCollectionJob[]>([]);
  const [runs, setRuns] = useState<EvidenceCollectionRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggeringJobId, setTriggeringJobId] = useState<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [jobsRes, runsRes] = await Promise.all([
        integrationService.listJobs(),
        integrationService.listRuns(),
      ]);
      setJobs(jobsRes);
      setRuns(runsRes);
    } catch (err) {
      console.error('Failed to load collection jobs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunJob = async (jobId: number) => {
    setTriggeringJobId(jobId);
    try {
      await integrationService.triggerJobRun(jobId);
      fetchData();
    } catch (err) {
      console.error('Failed to execute collection job', err);
    } finally {
      setTriggeringJobId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'RUNNING':
      case 'QUEUED':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'PARTIAL_FAILURE':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'FAILED':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
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
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <FileCheck2 className="h-7 w-7 text-primary-500" />
            Automated Evidence Collection Pipelines
          </h1>
          <p className="text-sm text-slate-400">
            Orchestrates continuous technical evidence extraction jobs, produces cryptographic provenance manifests, and deposits evidence in review queues.
          </p>
        </div>
      </div>

      {/* Jobs Overview */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-lg font-bold text-white mb-4">Configured Collection Jobs ({jobs.length})</h2>

        {jobs.length === 0 ? (
          <div className="text-xs text-slate-500">No automated collection jobs configured.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="pb-3 font-semibold">Job Code</th>
                  <th className="pb-3 font-semibold">Title</th>
                  <th className="pb-3 font-semibold">Collector Type</th>
                  <th className="pb-3 font-semibold">Cadence</th>
                  <th className="pb-3 font-semibold">Last Run</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans text-slate-300">
                {jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-slate-800/30">
                    <td className="py-3 font-mono font-bold text-primary-400">{j.job_code}</td>
                    <td className="py-3 font-medium text-white">{j.title}</td>
                    <td className="py-3 font-mono text-slate-400">{j.collector_type}</td>
                    <td className="py-3 text-slate-400">Every {j.frequency_hours}h</td>
                    <td className="py-3">
                      {j.last_run_at ? (
                        <span className="text-slate-400">{new Date(j.last_run_at).toLocaleTimeString()}</span>
                      ) : (
                        <span className="text-slate-600">Never run</span>
                      )}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleRunJob(j.id)}
                        disabled={triggeringJobId === j.id}
                        className="inline-flex items-center gap-1 rounded bg-primary-600 px-3 py-1 text-xs font-semibold text-white hover:bg-primary-500 disabled:opacity-50 transition"
                      >
                        <Play className={`h-3 w-3 ${triggeringJobId === j.id ? 'animate-spin' : ''}`} />
                        Run Now
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Execution Run History & Provenance */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="text-lg font-bold text-white mb-4">Run History & Provenance Manifests ({runs.length})</h2>

        {runs.length === 0 ? (
          <div className="text-xs text-slate-500">No collection runs recorded yet.</div>
        ) : (
          <div className="divide-y divide-slate-800 overflow-hidden rounded-lg border border-slate-800 bg-slate-950/40">
            {runs.map((r) => (
              <div key={r.id} className="p-4 space-y-2 hover:bg-slate-900/40 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-white">{r.run_code}</span>
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${getStatusBadge(r.status)}`}>
                      {r.status}
                    </span>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300">
                      {r.source_system} ({r.source_identifier})
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">{new Date(r.started_at).toLocaleString()}</span>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-400">
                  <div>Records Collected: <strong className="text-slate-200">{r.records_collected_count}</strong></div>
                  <div>Validation: <strong className="text-slate-200">{r.validation_status}</strong></div>
                  {r.evidence_item_id && (
                    <div>Evidence Item: <strong className="text-primary-400 font-mono">#{r.evidence_item_id} (UPLOADED)</strong></div>
                  )}
                </div>

                <div className="text-[11px] font-mono text-slate-500 truncate">
                  SHA-256: {r.payload_sha256}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
