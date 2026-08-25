import React, { useEffect, useState } from 'react';
import { ShieldCheck, Layers, AlertCircle, ArrowRight, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import type { Framework, FrameworkProgress } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

export const FrameworksPage: React.FC = () => {
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [progress, setProgress] = useState<FrameworkProgress | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFrameworkData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data: fwList } = await api.get<Framework[]>('/api/v1/frameworks');
        setFrameworks(fwList);

        if (fwList.length > 0) {
          const { data: progData } = await api.get<FrameworkProgress>(
            `/api/v1/frameworks/${fwList[0].id}/progress`
          );
          setProgress(progData);
        }
      } catch (err: any) {
        console.error(err);
        setError(err.response?.data?.detail || 'Failed to load framework data.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchFrameworkData();
  }, []);

  if (isLoading) {
    return <LoadingSpinner text="Loading compliance framework catalog..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-indigo-400" size={22} />
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Compliance Frameworks</h1>
            <Badge variant="purple">Authoritative Catalog</Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Global cybersecurity frameworks and real-time organizational implementation posture.
          </p>
        </div>

        <Link to="/controls">
          <Button size="sm" variant="primary">
            <span>Explore Controls Library</span>
            <ArrowRight size={14} />
          </Button>
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800/70 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle size={16} className="shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Framework Showcase Card */}
      {frameworks.map((fw) => (
        <Card key={fw.id} className="border-l-4 border-l-indigo-500 overflow-hidden">
          <div className="p-6 space-y-6">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-bold text-slate-100">{fw.name}</h2>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-700/60 text-indigo-300">
                    v{fw.version}
                  </span>
                  <Badge variant="success">Active Baseline</Badge>
                </div>
                <p className="text-xs text-slate-400 mt-1.5 max-w-3xl leading-relaxed">
                  {fw.description}
                </p>
              </div>

              {progress && (
                <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 flex items-center gap-6 shrink-0">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-indigo-400 font-mono">
                      {progress.compliance_score_pct}%
                    </div>
                    <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                      Compliance Score
                    </div>
                  </div>
                  <div className="h-10 w-px bg-slate-800" />
                  <div className="space-y-1 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 font-mono font-semibold">
                        {progress.implemented_count}
                      </span>
                      <span className="text-slate-400">Implemented</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-amber-400 font-mono font-semibold">
                        {progress.partially_implemented_count}
                      </span>
                      <span className="text-slate-400">In Progress / Partial</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* NIST CSF 2.0 Functions Breakdown */}
            {progress && (
              <div>
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Layers size={14} className="text-indigo-400" />
                  <span>NIST CSF 2.0 Functions &amp; Progress Posture</span>
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(progress.by_function).map(([fnKey, fnStats]) => (
                    <div
                      key={fnKey}
                      className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-indigo-300">
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

                      {/* Progress Bar */}
                      <div className="w-full bg-slate-800 rounded-full h-1.5 mb-3 overflow-hidden">
                        <div
                          className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
                          style={{ width: `${fnStats.score_pct}%` }}
                        />
                      </div>

                      <div className="grid grid-cols-3 text-[11px] text-slate-400 pt-1 border-t border-slate-900">
                        <div>
                          Total: <span className="font-mono text-slate-200">{fnStats.total}</span>
                        </div>
                        <div>
                          Impl: <span className="font-mono text-emerald-400">{fnStats.implemented}</span>
                        </div>
                        <div>
                          Open: <span className="font-mono text-slate-400">{fnStats.not_started}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Bar */}
            <div className="pt-2 flex justify-between items-center border-t border-slate-800/80">
              <span className="text-[11px] text-slate-400 font-mono">
                Taxonomy: 6 Functions · 22 Categories · 69 Subcategories
              </span>

              <Link to="/controls">
                <Button size="sm" variant="secondary">
                  <span>View All Controls in Matrix</span>
                  <ExternalLink size={13} />
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};