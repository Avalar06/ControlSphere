import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  Layers,
  RefreshCw,
  ChevronRight,
} from 'lucide-react';
import { executiveService } from '../../lib/executiveService';
import { ExecutivePostureHero } from '../../components/executive/ExecutivePostureHero';
import { DomainMaturityRadar } from '../../components/executive/DomainMaturityRadar';
import { BoardKPICards } from '../../components/executive/BoardKPICards';
import { ExecutiveSnapshotModal } from '../../components/executive/ExecutiveSnapshotModal';
import { ExportArtifactCard } from '../../components/executive/ExportArtifactCard';
import type {
  ExecutiveTelemetryResponse,
  ExecutiveTrendsResponse,
  ExecutiveTrendDataPoint,
  ExecutiveExportArtifact,
} from '../../types';
import { useAuth } from '../../context/AuthContext';

export const ExecutiveDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [telemetry, setTelemetry] = useState<ExecutiveTelemetryResponse | null>(null);
  const [trends, setTrends] = useState<ExecutiveTrendsResponse | null>(null);
  const [exports, setExports] = useState<ExecutiveExportArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [isSnapshotModalOpen, setIsSnapshotModalOpen] = useState(false);
  const [trendWindow, setTrendWindow] = useState(90);

  const canManage = user?.role === 'ADMIN' || user?.role === 'MANAGER' || user?.role === 'GRC_ANALYST';

  const loadData = async () => {
    try {
      const [telData, trendData, expData] = await Promise.all([
        executiveService.getLiveTelemetry(),
        executiveService.getHistoricalTrends(trendWindow),
        executiveService.listExports(),
      ]);
      setTelemetry(telData);
      setTrends(trendData);
      setExports(expData.slice(0, 4));
    } catch (err) {
      console.error('Failed to load executive telemetry:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [trendWindow]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  if (!telemetry) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-500">Failed to load executive telemetry.</p>
        <button
          onClick={handleRefresh}
          className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-12">
      {/* Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-xs text-slate-500 mb-1">
            <span>Executive Governance</span>
            <ChevronRight className="h-3 w-3" />
            <span className="font-semibold text-slate-800 dark:text-slate-200">Board Telemetry</span>
          </nav>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Calculated as of: {new Date(telemetry.calculated_at).toLocaleString()}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 shadow-sm"
            title="Refresh Telemetry"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>

          <Link
            to="/executive/dossiers"
            className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold shadow-sm flex items-center gap-1.5"
          >
            <Layers className="h-4 w-4 text-indigo-500" />
            Regulatory Dossiers
          </Link>

          <Link
            to="/executive/briefings"
            className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold shadow-sm flex items-center gap-1.5"
          >
            <FileText className="h-4 w-4 text-indigo-500" />
            Board Briefings
          </Link>
        </div>
      </div>

      {/* 1. Hero Posture Scoreboard */}
      <ExecutivePostureHero
        telemetry={telemetry}
        onCaptureSnapshot={() => setIsSnapshotModalOpen(true)}
        canManage={canManage}
      />

      {/* 2. Main Analytics Grid: Radar Matrix & Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Domain Maturity Radar */}
        <DomainMaturityRadar domains={telemetry.domain_posture_breakdown} />

        {/* Posture Trendlines Card */}
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white">
                  Historical Governance Trends
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Calculated from cryptographically immutable posture snapshots.
                </p>
              </div>
              <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg text-xs font-medium">
                {[30, 90, 180].map((days) => (
                  <button
                    key={days}
                    onClick={() => setTrendWindow(days)}
                    className={`px-2.5 py-1 rounded-md transition-colors ${
                      trendWindow === days
                        ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm font-semibold'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    {days}d
                  </button>
                ))}
              </div>
            </div>

            {/* Trend Data Point List / Timeline */}
            <div className="space-y-3 mt-4">
              {trends?.data_points.map((pt: ExecutiveTrendDataPoint, idx: number) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="h-2 w-2 rounded-full bg-indigo-500" />
                    <div>
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                        {new Date(pt.timestamp).toLocaleDateString()}
                      </span>
                      <span className="text-[11px] text-slate-400 block">
                        ALE: ${(pt.financial_exposure_ale / 1000).toFixed(1)}k • Audit:{' '}
                        {pt.audit_readiness_index.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-extrabold text-indigo-600 dark:text-indigo-400">
                      {pt.overall_posture_score.toFixed(1)}%
                    </span>
                    <span className="text-[10px] text-slate-400 block">Posture</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-xs">
            <span className="text-slate-400">
              Total Snapshots in Window: {trends?.data_points.length || 0}
            </span>
            <Link
              to="/executive/snapshots"
              className="text-indigo-600 dark:text-indigo-400 font-semibold flex items-center gap-1 hover:underline"
            >
              View Snapshots <ChevronRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* 3. Board KPI Cards (Risks, Findings, FAIR Loss) */}
      <BoardKPICards
        topRisks={telemetry.top_risks}
        criticalFindings={telemetry.critical_findings}
        financialAle={telemetry.financial_exposure_ale}
        var95={telemetry.var_95_exposure}
        appetiteUtilization={telemetry.financial_appetite_utilization_pct}
      />

      {/* 4. Recent Forensic Exports */}
      {exports.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white">Recent Forensic Exports</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Deterministic PDF & JSON artifacts with verified SHA-256 integrity.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {exports.map((exp) => (
              <ExportArtifactCard key={exp.id} artifact={exp} />
            ))}
          </div>
        </div>
      )}

      {/* Snapshot Modal */}
      <ExecutiveSnapshotModal
        isOpen={isSnapshotModalOpen}
        onClose={() => setIsSnapshotModalOpen(false)}
        onSuccess={loadData}
      />
    </div>
  );
};
