import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Database,
  Layers,
  Link2,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Split,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { harmonizationService } from '../lib/harmonizationService';
import { api } from '../lib/api';
import type {
  CommonControlCreate,
  CommonControlDomain,
  CrosswalkMappingCreate,
  Framework,
  FrameworkComplianceSnapshot,
  FrameworkCrosswalkMapping,
  MappingType,
  MultiFrameworkPostureResponse,
  RationalizedCommonControl,
  User,
} from '../types';

export const HarmonizationPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasRole } = useAuth();

  const canManage = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');
  const canExecute = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');
  const isCrosswalkAdmin = hasRole('ADMIN');

  const [activeTab, setActiveTab] = useState<'posture' | 'common-controls' | 'crosswalks' | 'snapshots'>('posture');
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [evalMessage, setEvalMessage] = useState<string | null>(null);

  // Data states
  const [posture, setPosture] = useState<MultiFrameworkPostureResponse | null>(null);
  const [commonControls, setCommonControls] = useState<RationalizedCommonControl[]>([]);
  const [crosswalks, setCrosswalks] = useState<FrameworkCrosswalkMapping[]>([]);
  const [snapshots, setSnapshots] = useState<FrameworkComplianceSnapshot[]>([]);
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  // Filter states
  const [domainFilter, setDomainFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchCC, setSearchCC] = useState('');
  const [snapshotFwFilter, setSnapshotFwFilter] = useState<string>('ALL');

  // Modal states
  const [showCreateCCModal, setShowCreateCCModal] = useState(false);
  const [createCCForm, setCreateCCForm] = useState<CommonControlCreate>({
    common_control_code: '',
    title: '',
    description: '',
    domain: 'GOVERNANCE_RISK',
    rationalization_status: 'ACTIVE',
  });
  const [createCCLoading, setCreateCCLoading] = useState(false);
  const [createCCError, setCreateCCError] = useState<string | null>(null);

  const [showCreateCrosswalkModal, setShowCreateCrosswalkModal] = useState(false);
  const [createCWForm, setCreateCWForm] = useState<CrosswalkMappingCreate>({
    source_subcategory_id: 0,
    target_subcategory_id: 0,
    mapping_type: 'EXACT',
    confidence_score: 1.0,
    bidirectional: true,
    rationale: '',
  });
  const [createCWLoading, setCreateCWLoading] = useState(false);
  const [createCWError, setCreateCWError] = useState<string | null>(null);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [postureRes, ccRes, cwRes, snapRes, fwRes] = await Promise.all([
        harmonizationService.getPosture().catch(() => null),
        harmonizationService.listCommonControls().catch(() => []),
        harmonizationService.listCrosswalks().catch(() => []),
        harmonizationService.listSnapshots().catch(() => []),
        api.get<Framework[]>('/frameworks').then((r) => r.data).catch(() => []),
      ]);

      if (postureRes) setPosture(postureRes);
      setCommonControls(ccRes);
      setCrosswalks(cwRes);
      setSnapshots(snapRes);
      setFrameworks(fwRes);

      // Load users for owner assignment if admin/manager
      if (canManage) {
        api.get<User[]>('/users').then((r) => setUsers(r.data)).catch(() => []);
      }
    } catch (err) {
      console.error('Failed to load harmonization data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const handleEvaluateAll = async () => {
    if (!canExecute) return;
    setEvaluating(true);
    setEvalMessage(null);
    try {
      const res = await harmonizationService.evaluateAll();
      setEvalMessage(`Evaluated ${res.evaluated_frameworks} frameworks and updated ${res.evaluated_common_controls} common controls.`);
      await fetchAllData();
    } catch (err: any) {
      setEvalMessage(err.response?.data?.detail || 'Evaluation failed.');
    } finally {
      setEvaluating(false);
    }
  };

  const handleCreateCommonControl = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateCCLoading(true);
    setCreateCCError(null);
    try {
      await harmonizationService.createCommonControl(createCCForm);
      setShowCreateCCModal(false);
      setCreateCCForm({
        common_control_code: '',
        title: '',
        description: '',
        domain: 'GOVERNANCE_RISK',
        rationalization_status: 'ACTIVE',
      });
      await fetchAllData();
    } catch (err: any) {
      setCreateCCError(err.response?.data?.detail || 'Failed to create common control.');
    } finally {
      setCreateCCLoading(false);
    }
  };

  const handleCreateCrosswalk = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateCWLoading(true);
    setCreateCWError(null);
    try {
      await harmonizationService.createCrosswalk({
        ...createCWForm,
        source_subcategory_id: Number(createCWForm.source_subcategory_id),
        target_subcategory_id: Number(createCWForm.target_subcategory_id),
        confidence_score: Number(createCWForm.confidence_score),
      });
      setShowCreateCrosswalkModal(false);
      setCreateCWForm({
        source_subcategory_id: 0,
        target_subcategory_id: 0,
        mapping_type: 'EXACT',
        confidence_score: 1.0,
        bidirectional: true,
        rationale: '',
      });
      await fetchAllData();
    } catch (err: any) {
      setCreateCWError(err.response?.data?.detail || 'Failed to create crosswalk mapping.');
    } finally {
      setCreateCWLoading(false);
    }
  };

  const handleDeleteCrosswalk = async (id: number) => {
    if (!isCrosswalkAdmin) return;
    if (!window.confirm('Are you sure you want to delete this normative crosswalk mapping?')) return;
    try {
      await harmonizationService.deleteCrosswalk(id);
      await fetchAllData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete crosswalk.');
    }
  };

  // Helper score badges
  const getHealthBadge = (score: number) => {
    if (score >= 80) {
      return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">HEALTHY ({score.toFixed(1)}%)</span>;
    }
    if (score >= 60) {
      return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-950/80 text-blue-300 border border-blue-800/80">DEGRADED ({score.toFixed(1)}%)</span>;
    }
    if (score >= 40) {
      return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-950/80 text-amber-300 border border-amber-800/80">AT RISK ({score.toFixed(1)}%)</span>;
    }
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-950/80 text-rose-300 border border-rose-800/80">FAILING ({score.toFixed(1)}%)</span>;
  };

  const filteredCC = commonControls.filter((cc) => {
    if (domainFilter !== 'ALL' && cc.domain !== domainFilter) return false;
    if (statusFilter !== 'ALL' && cc.rationalization_status !== statusFilter) return false;
    if (searchCC && !cc.common_control_code.toLowerCase().includes(searchCC.toLowerCase()) && !cc.title.toLowerCase().includes(searchCC.toLowerCase())) return false;
    return true;
  });

  const filteredSnapshots = snapshots.filter((s) => {
    if (snapshotFwFilter !== 'ALL' && s.framework_id !== Number(snapshotFwFilter)) return false;
    return true;
  });

  // Calculate executive KPI metrics
  const avgCoverage = posture?.frameworks.length
    ? (posture.frameworks.reduce((acc, f) => acc + f.coverage_percentage, 0) / posture.frameworks.length).toFixed(1)
    : '0.0';
  const avgHealth = posture?.frameworks.length
    ? (posture.frameworks.reduce((acc, f) => acc + f.compliance_health_score, 0) / posture.frameworks.length).toFixed(1)
    : '0.0';
  const attentionCount = posture?.frameworks.filter((f) => f.compliance_health_score < 60.0).length || 0;

  return (
    <div className="space-y-6 pb-12">
      {/* Workspace Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center text-indigo-400">
              <Split className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Multi-Framework Harmonization</h1>
              <p className="text-sm text-slate-400">
                Unified control rationalization, normative crosswalks, and automated compliance posture
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {canExecute && (
            <button
              onClick={handleEvaluateAll}
              disabled={evaluating}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`h-4 w-4 ${evaluating ? 'animate-spin' : ''}`} />
              {evaluating ? 'Evaluating Telemetry...' : 'Evaluate All Frameworks'}
            </button>
          )}
        </div>
      </div>

      {evalMessage && (
        <div className="p-4 rounded-lg bg-indigo-950/40 border border-indigo-800/60 text-indigo-200 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-indigo-400 shrink-0" />
            <span>{evalMessage}</span>
          </div>
          <button onClick={() => setEvalMessage(null)} className="text-slate-400 hover:text-slate-200">
            &times;
          </button>
        </div>
      )}

      {/* Executive KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Monitored Frameworks</span>
            <Layers className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{posture?.frameworks.length || 0}</span>
            <span className="text-xs text-slate-500">Active</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg Coverage</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">{avgCoverage}%</span>
            <span className="text-xs text-slate-500">Across catalog</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg Compliance</span>
            <Activity className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-blue-400">{avgHealth}%</span>
            <span className="text-xs text-slate-500">CCM weighted</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Common Controls</span>
            <Database className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{commonControls.length}</span>
            <span className="text-xs text-slate-500">Rationalized</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Attention Needed</span>
            <AlertCircle className="h-4 w-4 text-rose-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-400">{attentionCount}</span>
            <span className="text-xs text-slate-500">Score &lt; 60%</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-800/80">
        <nav className="flex space-x-6">
          <button
            onClick={() => setActiveTab('posture')}
            className={`pb-3 text-sm font-medium transition border-b-2 flex items-center gap-2 ${
              activeTab === 'posture'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="h-4 w-4" />
            Framework Posture Overview
          </button>
          <button
            onClick={() => setActiveTab('common-controls')}
            className={`pb-3 text-sm font-medium transition border-b-2 flex items-center gap-2 ${
              activeTab === 'common-controls'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="h-4 w-4" />
            Rationalized Common Controls ({commonControls.length})
          </button>
          <button
            onClick={() => setActiveTab('crosswalks')}
            className={`pb-3 text-sm font-medium transition border-b-2 flex items-center gap-2 ${
              activeTab === 'crosswalks'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Split className="h-4 w-4" />
            Normative Crosswalks ({crosswalks.length})
          </button>
          <button
            onClick={() => setActiveTab('snapshots')}
            className={`pb-3 text-sm font-medium transition border-b-2 flex items-center gap-2 ${
              activeTab === 'snapshots'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock className="h-4 w-4" />
            Historical Snapshots ({snapshots.length})
          </button>
        </nav>
      </div>

      {/* Tab 1: Framework Posture Overview */}
      {activeTab === 'posture' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {posture?.frameworks.map((fw) => (
              <div
                key={fw.framework_id}
                className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 hover:border-slate-700 transition flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                        {fw.framework_identifier}
                      </span>
                      <h3 className="text-lg font-bold text-slate-100 mt-0.5">{fw.framework_name}</h3>
                    </div>
                    {getHealthBadge(fw.compliance_health_score)}
                  </div>

                  <div className="grid grid-cols-2 gap-3 my-4 p-3 rounded-lg bg-slate-950/60 border border-slate-800/60">
                    <div>
                      <span className="text-xs text-slate-400">Coverage</span>
                      <p className="text-xl font-bold text-emerald-400">{fw.coverage_percentage.toFixed(1)}%</p>
                      <span className="text-[11px] text-slate-500">
                        {fw.total_covered_subcategories} / {fw.total_subcategories} outcomes
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400">Compliance Health</span>
                      <p className="text-xl font-bold text-blue-400">{fw.compliance_health_score.toFixed(1)}%</p>
                      <span className="text-[11px] text-slate-500">
                        Direct: {fw.directly_covered_subcategories} | Inh: {fw.crosswalk_covered_subcategories}
                      </span>
                    </div>
                  </div>

                  {fw.evaluated_at && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Clock className="h-3.5 w-3.5" />
                      <span>Evaluated {new Date(fw.evaluated_at).toLocaleString()}</span>
                    </div>
                  )}
                </div>

                <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between gap-3">
                  <button
                    onClick={() => navigate(`/harmonization/frameworks/${fw.framework_id}`)}
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition"
                  >
                    <span>Inspect Posture Matrix</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </button>

                  {canExecute && (
                    <button
                      onClick={async () => {
                        setEvaluating(true);
                        try {
                          await harmonizationService.evaluateFramework(fw.framework_id);
                          await fetchAllData();
                        } finally {
                          setEvaluating(false);
                        }
                      }}
                      disabled={evaluating}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
                    >
                      Evaluate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {(!posture || posture.frameworks.length === 0) && !loading && (
            <div className="text-center py-12 bg-slate-900/30 rounded-xl border border-slate-800/60">
              <Layers className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-300 font-medium">No framework postures available</p>
              <p className="text-slate-500 text-sm mt-1">Execute an evaluation to compute multi-framework posture.</p>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Rationalized Common Controls */}
      {activeTab === 'common-controls' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
            <div className="flex items-center gap-3 flex-1">
              <div className="relative flex-1 max-w-md">
                <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search code or title..."
                  value={searchCC}
                  onChange={(e) => setSearchCC(e.target.value)}
                  className="w-full pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Domains</option>
                <option value="IDENTITY_ACCESS">Identity & Access</option>
                <option value="CRYPTOGRAPHY">Cryptography</option>
                <option value="DATA_PROTECTION">Data Protection</option>
                <option value="INCIDENT_MANAGEMENT">Incident Management</option>
                <option value="VULNERABILITY_MANAGEMENT">Vulnerability Mgmt</option>
                <option value="BUSINESS_CONTINUITY">Business Continuity</option>
                <option value="GOVERNANCE_RISK">Governance & Risk</option>
                <option value="PHYSICAL_SECURITY">Physical Security</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="DRAFT">Draft</option>
                <option value="RETIRED">Retired</option>
              </select>
            </div>

            {canManage && (
              <button
                onClick={() => setShowCreateCCModal(true)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
              >
                <Plus className="h-4 w-4" />
                New Common Control
              </button>
            )}
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/80 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Code</th>
                  <th className="px-5 py-3.5">Objective Title</th>
                  <th className="px-5 py-3.5">Domain</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5">Inherited Health</th>
                  <th className="px-5 py-3.5">Mapped Controls</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredCC.map((cc) => (
                  <tr key={cc.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-5 py-3.5 font-mono text-xs text-indigo-400 font-semibold">
                      {cc.common_control_code}
                    </td>
                    <td className="px-5 py-3.5 font-medium text-slate-200">
                      <div>{cc.title}</div>
                      <div className="text-xs text-slate-500 truncate max-w-xs">{cc.description}</div>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">{cc.domain.replace('_', ' ')}</td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded ${
                        cc.rationalization_status === 'ACTIVE'
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/80'
                          : cc.rationalization_status === 'DRAFT'
                          ? 'bg-amber-950/80 text-amber-300 border border-amber-800/80'
                          : 'bg-slate-800 text-slate-400'
                      }`}>
                        {cc.rationalization_status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">{getHealthBadge(cc.inherited_health_score)}</td>
                    <td className="px-5 py-3.5 text-xs text-slate-300">
                      <span className="inline-flex items-center gap-1">
                        <Link2 className="h-3.5 w-3.5 text-slate-500" />
                        {cc.mapped_controls_count} linked
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => navigate(`/harmonization/common-controls/${cc.id}`)}
                        className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition"
                      >
                        Inspect &rarr;
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredCC.length === 0 && (
              <div className="text-center py-12">
                <Database className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-400 text-sm">No common controls match your filters.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Normative Crosswalks */}
      {activeTab === 'crosswalks' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Global Regulatory Crosswalk Catalog</h3>
              <p className="text-xs text-slate-400">Normative multi-framework equivalence mappings</p>
            </div>

            {isCrosswalkAdmin && (
              <button
                onClick={() => setShowCreateCrosswalkModal(true)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
              >
                <Plus className="h-4 w-4" />
                Add Normative Crosswalk
              </button>
            )}
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/80 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Source Outcome</th>
                  <th className="px-5 py-3.5">Target Outcome</th>
                  <th className="px-5 py-3.5">Mapping Type</th>
                  <th className="px-5 py-3.5">Confidence</th>
                  <th className="px-5 py-3.5">Rationale</th>
                  {isCrosswalkAdmin && <th className="px-5 py-3.5 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {crosswalks.map((cw) => (
                  <tr key={cw.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-5 py-3.5 font-mono text-xs text-slate-200">
                      {cw.source_identifier || `Subcat #${cw.source_subcategory_id}`}
                      {cw.source_title && <div className="text-[11px] text-slate-500 truncate max-w-xs">{cw.source_title}</div>}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs text-indigo-400">
                      {cw.target_identifier || `Subcat #${cw.target_subcategory_id}`}
                      {cw.target_title && <div className="text-[11px] text-slate-500 truncate max-w-xs">{cw.target_title}</div>}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/60">
                        {cw.mapping_type}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs text-slate-200">
                      {(cw.confidence_score * 100).toFixed(0)}%
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400 max-w-sm truncate">{cw.rationale}</td>
                    {isCrosswalkAdmin && (
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => handleDeleteCrosswalk(cw.id)}
                          className="text-rose-400 hover:text-rose-300 transition"
                          title="Delete Crosswalk"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>

            {crosswalks.length === 0 && (
              <div className="text-center py-12">
                <Split className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-400 text-sm">No crosswalk mappings registered.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Historical Snapshots */}
      {activeTab === 'snapshots' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400 uppercase font-semibold">Filter Framework:</span>
              <select
                value={snapshotFwFilter}
                onChange={(e) => setSnapshotFwFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-300 focus:outline-none"
              >
                <option value="ALL">All Frameworks</option>
                {frameworks.map((fw) => (
                  <option key={fw.id} value={fw.id}>
                    {fw.identifier} - {fw.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-3 py-1.5 rounded-lg">
              <ShieldCheck className="h-4 w-4" />
              <span>Immutable Audit Records (v1.0 Engine)</span>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/80 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Snapshot ID</th>
                  <th className="px-5 py-3.5">Framework</th>
                  <th className="px-5 py-3.5">Calculation Version</th>
                  <th className="px-5 py-3.5">Coverage %</th>
                  <th className="px-5 py-3.5">Compliance Score</th>
                  <th className="px-5 py-3.5">Covered Outcomes</th>
                  <th className="px-5 py-3.5">Evaluated At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredSnapshots.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-5 py-3.5 font-mono text-xs text-slate-400">SNAP-{s.id.toString().padStart(5, '0')}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-200">
                      {s.framework_identifier || `Framework #${s.framework_id}`}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex px-2 py-0.5 text-xs font-mono rounded bg-slate-800 text-slate-300">
                        {s.calculation_version}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-emerald-400 font-semibold">
                      {s.coverage_percentage.toFixed(1)}%
                    </td>
                    <td className="px-5 py-3.5 font-mono text-blue-400 font-semibold">
                      {s.compliance_health_score.toFixed(1)}%
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">
                      {s.covered_subcategories} / {s.total_subcategories} ({s.unmapped_subcategories} unmapped)
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400">
                      {new Date(s.evaluated_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredSnapshots.length === 0 && (
              <div className="text-center py-12">
                <Clock className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                <p className="text-slate-400 text-sm">No historical compliance snapshots found.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Create Common Control */}
      {showCreateCCModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100">Create Rationalized Common Control</h3>
              <button onClick={() => setShowCreateCCModal(false)} className="text-slate-400 hover:text-slate-200">
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateCommonControl} className="p-6 space-y-4">
              {createCCError && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
                  {createCCError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Common Control Code *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., CCF-IAM-01"
                  value={createCCForm.common_control_code}
                  onChange={(e) => setCreateCCForm({ ...createCCForm, common_control_code: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Centralized Identity & Access Management"
                  value={createCCForm.title}
                  onChange={(e) => setCreateCCForm({ ...createCCForm, title: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Domain *
                  </label>
                  <select
                    value={createCCForm.domain}
                    onChange={(e) => setCreateCCForm({ ...createCCForm, domain: e.target.value as CommonControlDomain })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="IDENTITY_ACCESS">Identity & Access</option>
                    <option value="CRYPTOGRAPHY">Cryptography</option>
                    <option value="DATA_PROTECTION">Data Protection</option>
                    <option value="INCIDENT_MANAGEMENT">Incident Management</option>
                    <option value="VULNERABILITY_MANAGEMENT">Vulnerability Mgmt</option>
                    <option value="BUSINESS_CONTINUITY">Business Continuity</option>
                    <option value="GOVERNANCE_RISK">Governance & Risk</option>
                    <option value="PHYSICAL_SECURITY">Physical Security</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Assigned Owner
                  </label>
                  <select
                    value={createCCForm.owner_id || ''}
                    onChange={(e) => setCreateCCForm({ ...createCCForm, owner_id: e.target.value ? Number(e.target.value) : undefined })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Unassigned</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Description *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Unified operational outcome requirements..."
                  value={createCCForm.description}
                  onChange={(e) => setCreateCCForm({ ...createCCForm, description: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateCCModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createCCLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                >
                  {createCCLoading ? 'Creating...' : 'Create Common Control'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create Crosswalk (Admin only) */}
      {showCreateCrosswalkModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100">Add Normative Crosswalk Mapping</h3>
              <button onClick={() => setShowCreateCrosswalkModal(false)} className="text-slate-400 hover:text-slate-200">
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateCrosswalk} className="p-6 space-y-4">
              {createCWError && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
                  {createCWError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Source Subcategory ID *
                  </label>
                  <input
                    type="number"
                    required
                    value={createCWForm.source_subcategory_id || ''}
                    onChange={(e) => setCreateCWForm({ ...createCWForm, source_subcategory_id: Number(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Target Subcategory ID *
                  </label>
                  <input
                    type="number"
                    required
                    value={createCWForm.target_subcategory_id || ''}
                    onChange={(e) => setCreateCWForm({ ...createCWForm, target_subcategory_id: Number(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Mapping Type *
                  </label>
                  <select
                    value={createCWForm.mapping_type}
                    onChange={(e) => setCreateCWForm({ ...createCWForm, mapping_type: e.target.value as MappingType })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="EXACT">EXACT (100%)</option>
                    <option value="SUPERSET">SUPERSET (100%)</option>
                    <option value="SUBSET">SUBSET (90%)</option>
                    <option value="PARTIAL">PARTIAL (60%)</option>
                    <option value="CORRELATED">CORRELATED (50%)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Confidence Score (0.0 - 1.0) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    required
                    value={createCWForm.confidence_score}
                    onChange={(e) => setCreateCWForm({ ...createCWForm, confidence_score: parseFloat(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Equivalence Rationale *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Justification for cross-framework equivalence..."
                  value={createCWForm.rationale}
                  onChange={(e) => setCreateCWForm({ ...createCWForm, rationale: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateCrosswalkModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createCWLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                >
                  {createCWLoading ? 'Saving...' : 'Save Mapping'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
