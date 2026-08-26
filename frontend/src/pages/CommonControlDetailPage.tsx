import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Database,
  Edit,
  Link2,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { harmonizationService } from '../lib/harmonizationService';
import { api } from '../lib/api';
import type {
  CommonControlDomain,
  CommonControlMappingCreate,
  CommonControlUpdate,
  OrganizationControl,
  RationalizationStatus,
  RationalizedCommonControl,
  User,
} from '../types';

export const CommonControlDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const commonControlId = Number(id);
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const canManage = hasRole('ADMIN', 'GRC_ANALYST', 'SECURITY_ANALYST', 'MANAGER');

  const [control, setControl] = useState<RationalizedCommonControl | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Available controls to link
  const [availableControls, setAvailableControls] = useState<OrganizationControl[]>([]);
  const [users, setUsers] = useState<User[]>([]);

  // Modals
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkForm, setLinkForm] = useState<CommonControlMappingCreate>({
    organization_control_id: 0,
    weight: 1.0,
  });
  const [linkLoading, setLinkLoading] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  const [showEditModal, setShowEditModal] = useState(false);
  const [editForm, setEditForm] = useState<CommonControlUpdate>({});
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!commonControlId) return;
    setLoading(true);
    setError(null);
    try {
      const [ccData, orgControlsRes, usersRes] = await Promise.all([
        harmonizationService.getCommonControl(commonControlId),
        api.get<OrganizationControl[]>('/controls').then((r) => r.data).catch(() => []),
        api.get<User[]>('/users').then((r) => r.data).catch(() => []),
      ]);

      setControl(ccData);
      setAvailableControls(orgControlsRes);
      setUsers(usersRes);
      setEditForm({
        title: ccData.title,
        description: ccData.description,
        domain: ccData.domain,
        rationalization_status: ccData.rationalization_status,
        owner_id: ccData.owner_id,
        deprecation_reason: ccData.deprecation_reason,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load common control details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [commonControlId]);

  const handleAddMapping = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canManage || !control) return;
    setLinkLoading(true);
    setLinkError(null);
    try {
      await harmonizationService.addMapping(control.id, {
        organization_control_id: Number(linkForm.organization_control_id),
        weight: Number(linkForm.weight),
      });
      setShowLinkModal(false);
      setLinkForm({ organization_control_id: 0, weight: 1.0 });
      await fetchDetail();
    } catch (err: any) {
      setLinkError(err.response?.data?.detail || 'Failed to link organization control.');
    } finally {
      setLinkLoading(false);
    }
  };

  const handleRemoveMapping = async (organizationControlId: number) => {
    if (!canManage || !control) return;
    if (!window.confirm('Are you sure you want to unlink this organization control?')) return;
    try {
      await harmonizationService.removeMapping(control.id, organizationControlId);
      await fetchDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to unlink control.');
    }
  };

  const handleEditControl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canManage || !control) return;
    setEditLoading(true);
    setEditError(null);
    try {
      await harmonizationService.updateCommonControl(control.id, editForm);
      setShowEditModal(false);
      await fetchDetail();
    } catch (err: any) {
      setEditError(err.response?.data?.detail || 'Failed to update common control.');
    } finally {
      setEditLoading(false);
    }
  };

  const getHealthBadge = (score: number) => {
    if (score >= 80) {
      return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">HEALTHY ({score.toFixed(1)}%)</span>;
    }
    if (score >= 60) {
      return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-300 border border-blue-800/80">DEGRADED ({score.toFixed(1)}%)</span>;
    }
    if (score >= 40) {
      return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-800/80">AT RISK ({score.toFixed(1)}%)</span>;
    }
    return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-300 border border-rose-800/80">FAILING ({score.toFixed(1)}%)</span>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-8 w-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (error || !control) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-bold text-slate-100">Common Control Not Found</h2>
        <p className="text-slate-400 text-sm mt-1">{error}</p>
        <Link to="/harmonization" className="mt-4 inline-flex items-center gap-2 text-indigo-400 text-sm">
          <ArrowLeft className="h-4 w-4" /> Back to Harmonization Register
        </Link>
      </div>
    );
  }

  const assignedOwner = users.find((u) => u.id === control.owner_id);

  return (
    <div className="space-y-6 pb-12">
      {/* Header Breadcrumbs */}
      <div>
        <button
          onClick={() => navigate('/harmonization')}
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition mb-2"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Harmonization Register
        </button>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800/80 pb-5">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-lg bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center text-indigo-400">
              <Database className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-indigo-400 uppercase tracking-wider">
                  {control.common_control_code}
                </span>
                <span className="text-xs text-slate-500">•</span>
                <span className="text-xs text-slate-400">{control.domain.replace('_', ' ')}</span>
              </div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{control.title}</h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {canManage && (
              <button
                onClick={() => setShowEditModal(true)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition"
              >
                <Edit className="h-4 w-4" />
                Edit Metadata
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Top Metadata Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Telemetry Card */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Inherited Telemetry</span>
            <div className="mt-3 flex items-center justify-between">
              <div>
                <span className="text-3xl font-bold text-slate-100">{control.inherited_health_score.toFixed(1)}%</span>
                <p className="text-xs text-slate-500 mt-0.5">Authoritative Weighted Score</p>
              </div>
              {getHealthBadge(control.inherited_health_score)}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400">
            Computed from {control.mappings?.length || 0} mapped organization controls
          </div>
        </div>

        {/* Identity & Status Card */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Control Governance</span>
            <div className="mt-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Rationalization Status:</span>
                <span className="font-semibold text-emerald-400">{control.rationalization_status}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Assigned Owner:</span>
                <span className="text-slate-200 font-medium">{assignedOwner?.full_name || 'Unassigned'}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Created:</span>
                <span className="text-slate-400">{new Date(control.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {control.deprecation_reason && (
            <div className="mt-4 p-2.5 rounded bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300">
              <span className="font-semibold">Deprecation: </span> {control.deprecation_reason}
            </div>
          )}
        </div>

        {/* Lineage Card */}
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Lineage Derivation</span>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              This Common Control aggregates live Continuous Compliance Monitoring (CCM) telemetry from linked underlying controls:
            </p>
            <div className="mt-3 p-2.5 rounded bg-slate-950/80 border border-slate-800 font-mono text-[11px] text-indigo-300">
              Score = &sum;(Weight &times; CCMHealth) / &sum;Weight
            </div>
          </div>
          <div className="text-[11px] text-slate-500 mt-3">
            Zero mapped controls evaluates to 100.0% (HEALTHY)
          </div>
        </div>
      </div>

      {/* Description Section */}
      <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Objective Requirements</h3>
        <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">{control.description}</p>
      </div>

      {/* Linked Controls Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between bg-slate-900/40 p-4 rounded-xl border border-slate-800/80">
          <div>
            <h3 className="text-base font-semibold text-slate-100">Mapped Organization Controls</h3>
            <p className="text-xs text-slate-400">Specific controls providing operational evidence and CCM telemetry</p>
          </div>

          {canManage && (
            <button
              onClick={() => setShowLinkModal(true)}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
            >
              <Plus className="h-4 w-4" />
              Link Organization Control
            </button>
          )}
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/80 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="px-5 py-3.5">Control Identifier</th>
                <th className="px-5 py-3.5">Control Title</th>
                <th className="px-5 py-3.5">Implementation Status</th>
                <th className="px-5 py-3.5">Mapping Weight</th>
                {canManage && <th className="px-5 py-3.5 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {control.mappings?.map((m) => (
                <tr key={m.id} className="hover:bg-slate-800/30 transition">
                  <td className="px-5 py-3.5 font-mono text-xs text-indigo-400 font-semibold">
                    {m.control_subcategory_identifier || `Control #${m.organization_control_id}`}
                  </td>
                  <td className="px-5 py-3.5 font-medium text-slate-200">
                    {m.control_subcategory_title || 'Organization Control'}
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded bg-slate-800 text-slate-300">
                      {m.control_status || 'IMPLEMENTED'}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-200">
                    {m.weight.toFixed(1)}x
                  </td>
                  {canManage && (
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => handleRemoveMapping(m.organization_control_id)}
                        className="text-rose-400 hover:text-rose-300 transition"
                        title="Unlink Control"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>

          {(!control.mappings || control.mappings.length === 0) && (
            <div className="text-center py-12">
              <Link2 className="h-8 w-8 text-slate-600 mx-auto mb-2" />
              <p className="text-slate-400 text-sm">No organization controls mapped to this common control.</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Link Organization Control */}
      {showLinkModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100">Link Organization Control</h3>
              <button onClick={() => setShowLinkModal(false)} className="text-slate-400 hover:text-slate-200">
                &times;
              </button>
            </div>

            <form onSubmit={handleAddMapping} className="p-6 space-y-4">
              {linkError && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
                  {linkError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Select Organization Control *
                </label>
                <select
                  required
                  value={linkForm.organization_control_id || ''}
                  onChange={(e) => setLinkForm({ ...linkForm, organization_control_id: Number(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Choose a control...</option>
                  {availableControls.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.subcategory?.identifier} - {c.subcategory?.title} ({c.status})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Relative Mapping Weight (0.1 - 10.0) *
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10.0"
                  required
                  value={linkForm.weight}
                  onChange={(e) => setLinkForm({ ...linkForm, weight: parseFloat(e.target.value) })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowLinkModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={linkLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                >
                  {linkLoading ? 'Linking...' : 'Confirm Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit Common Control */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100">Edit Common Control Metadata</h3>
              <button onClick={() => setShowEditModal(false)} className="text-slate-400 hover:text-slate-200">
                &times;
              </button>
            </div>

            <form onSubmit={handleEditControl} className="p-6 space-y-4">
              {editError && (
                <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
                  {editError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  value={editForm.title || ''}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Domain *
                  </label>
                  <select
                    value={editForm.domain || 'GOVERNANCE_RISK'}
                    onChange={(e) => setEditForm({ ...editForm, domain: e.target.value as CommonControlDomain })}
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
                    Status *
                  </label>
                  <select
                    value={editForm.rationalization_status || 'ACTIVE'}
                    onChange={(e) => setEditForm({ ...editForm, rationalization_status: e.target.value as RationalizationStatus })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ACTIVE">Active</option>
                    <option value="DRAFT">Draft</option>
                    <option value="RETIRED">Retired</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Assigned Owner
                </label>
                <select
                  value={editForm.owner_id || ''}
                  onChange={(e) => setEditForm({ ...editForm, owner_id: e.target.value ? Number(e.target.value) : undefined })}
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

              {editForm.rationalization_status === 'RETIRED' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Deprecation Reason (Mandatory when retired) *
                  </label>
                  <input
                    type="text"
                    required
                    value={editForm.deprecation_reason || ''}
                    onChange={(e) => setEditForm({ ...editForm, deprecation_reason: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Description *
                </label>
                <textarea
                  required
                  rows={3}
                  value={editForm.description || ''}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                >
                  {editLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
